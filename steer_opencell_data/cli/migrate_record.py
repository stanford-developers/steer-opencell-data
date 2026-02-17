#!/usr/bin/env python3
"""
Migrate individual records from local SQLite to AWS DynamoDB + S3.

Interactive usage:
    python -m steer_opencell_data.cli.migrate_record

Non-interactive usage:
    python -m steer_opencell_data.cli.migrate_record --table cathode_materials --name LFP --yes

Environment variables:
    DYNAMODB_TABLE  Target DynamoDB table (default: opencell-production)
    S3_BUCKET       Target S3 bucket (default: opencell-production-objects)
    AWS_REGION      AWS region (default: us-east-2)

Requires: pip install steer-opencell-data[cli]
"""

from __future__ import annotations

import argparse
import importlib.resources
import logging
import os
import sqlite3
import sys
import uuid
from typing import Any, Iterator

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
except ImportError:
    print(
        "Error: boto3 is required for the migration CLI.\n"
        "Install it with: pip install steer-opencell-data[cli]"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants (match lambda/functions/config.py and scripts/migration/migrate.py)
# ---------------------------------------------------------------------------

MATERIAL_TABLES = sorted([
    "anode_materials",
    "binder_materials",
    "cathode_materials",
    "conductive_additive_materials",
    "current_collector_materials",
    "insulation_materials",
    "separator_materials",
    "tape_materials",
    "prismatic_container_materials",
])

CELL_TABLES = sorted([
    "cell_references",
    "teardowns",
    "user_designs",
])

ALL_TABLES = set(MATERIAL_TABLES) | set(CELL_TABLES)

MATERIAL_METADATA_COLUMNS = ["name", "date", "version", "reference"]
CELL_METADATA_COLUMNS = [
    "name", "form_factor", "internal_construction",
    "date_created", "version", "chemistry",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLite reader (adapted from scripts/migration/migrate.py)
# ---------------------------------------------------------------------------

class SQLiteReader:
    """Read data from the local SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> SQLiteReader:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, *args) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_table_names(self) -> list[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]

    def get_row_count(self, table_name: str) -> int:
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        return cursor.fetchone()[0]

    def get_column_names(self, table_name: str) -> list[str]:
        cursor = self._conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        return [row[1] for row in cursor.fetchall()]

    def iter_rows(self, table_name: str) -> Iterator[dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}]")
        for row in cursor:
            yield dict(row)

    def get_row_by_name(self, table_name: str, name: str) -> dict[str, Any] | None:
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}] WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_records_summary(self, table_name: str) -> list[dict[str, str]]:
        """Get metadata (excluding object blob) for all records in a table."""
        if table_name in set(MATERIAL_TABLES):
            columns = [c for c in MATERIAL_METADATA_COLUMNS
                       if c in self.get_column_names(table_name)]
        else:
            columns = [c for c in CELL_METADATA_COLUMNS
                       if c in self.get_column_names(table_name)]

        cols_str = ", ".join(columns)
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT {cols_str} FROM [{table_name}] ORDER BY name")
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# AWS writer (adapted from scripts/migration/migrate.py)
# ---------------------------------------------------------------------------

class AWSWriter:
    """Write data to AWS DynamoDB and S3."""

    def __init__(self, dynamodb_table: str, s3_bucket: str, region: str):
        self.dynamodb_table = dynamodb_table
        self.s3_bucket = s3_bucket
        self.region = region
        self._dynamodb = None
        self._table = None
        self._s3 = None

    def _get_dynamodb_table(self):
        if self._table is None:
            self._dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self._table = self._dynamodb.Table(self.dynamodb_table)
        return self._table

    def _get_s3_client(self):
        if self._s3 is None:
            self._s3 = boto3.client("s3", region_name=self.region)
        return self._s3

    def validate_access(self) -> None:
        """Validate AWS credentials and resource access. Raises on failure."""
        table = self._get_dynamodb_table()
        try:
            table.table_status
        except (ClientError, NoCredentialsError, BotoCoreError) as e:
            raise RuntimeError(
                f"Cannot access DynamoDB table '{self.dynamodb_table}': {e}"
            )

        s3 = self._get_s3_client()
        try:
            s3.head_bucket(Bucket=self.s3_bucket)
        except (ClientError, NoCredentialsError, BotoCoreError) as e:
            raise RuntimeError(
                f"Cannot access S3 bucket '{self.s3_bucket}': {e}"
            )

    def item_exists(self, table_name: str, name: str) -> bool:
        """Check if an item already exists in DynamoDB."""
        table = self._get_dynamodb_table()
        response = table.get_item(
            Key={"table_name": table_name, "name": name},
            ProjectionExpression="table_name",
        )
        return "Item" in response

    def upload_object(self, s3_key: str, blob: bytes) -> None:
        """Upload object blob to S3."""
        s3 = self._get_s3_client()
        s3.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=blob,
            ContentType="application/octet-stream",
        )

    def delete_object(self, s3_key: str) -> None:
        """Delete an S3 object (for cleanup on partial failure)."""
        s3 = self._get_s3_client()
        s3.delete_object(Bucket=self.s3_bucket, Key=s3_key)

    def put_item(self, item: dict[str, Any]) -> None:
        """Put item to DynamoDB (upsert)."""
        table = self._get_dynamodb_table()
        clean_item = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=clean_item)


# ---------------------------------------------------------------------------
# Helpers (from scripts/migration/migrate.py)
# ---------------------------------------------------------------------------

def generate_s3_key(table_name: str, name: str) -> str:
    unique_id = str(uuid.uuid4())
    return f"{table_name}/{name}/{unique_id}.msgpack"


def extract_object_blob(row: dict[str, Any]) -> bytes:
    """Extract the serialized object blob from a SQLite row."""
    obj_data = row.get("object")
    if obj_data is None:
        raise ValueError("Row has no 'object' column")

    if isinstance(obj_data, bytes):
        return obj_data
    if isinstance(obj_data, str):
        return obj_data.encode("latin-1")

    raise ValueError(f"Unexpected object type: {type(obj_data)}")


def build_dynamodb_item(
    row: dict[str, Any], table_name: str, s3_key: str,
) -> dict[str, Any]:
    """Build DynamoDB item from a SQLite row."""
    if table_name in set(MATERIAL_TABLES):
        columns = MATERIAL_METADATA_COLUMNS
    else:
        columns = CELL_METADATA_COLUMNS

    item = {
        "table_name": table_name,
        "s3_key": s3_key,
        "visibility": "public",
    }
    for col in columns:
        if col in row and row[col] is not None:
            item[col] = row[col]

    return item


def find_default_database() -> str:
    """Find the package's bundled database.db."""
    with importlib.resources.path("steer_opencell_data", "database.db") as db_path:
        path = str(db_path)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"database.db not found at {path}. Specify --sqlite-path."
        )
    return path


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt_choice(prompt_text: str, options: list[str], label_fn=None) -> str:
    """Display numbered options and return the selected value."""
    print(f"\n{prompt_text}")
    for i, opt in enumerate(options, 1):
        label = label_fn(opt) if label_fn else opt
        print(f"  {i}. {label}")

    while True:
        try:
            raw = input("> ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, EOFError):
            pass
        print(f"  Please enter a number between 1 and {len(options)}.")


def select_table_interactive(reader: SQLiteReader) -> str:
    """Interactively select a table type, then a specific table."""
    table_type = prompt_choice(
        "Select table type:",
        ["materials", "cells"],
        label_fn=lambda t: f"Materials ({len(MATERIAL_TABLES)} tables)"
        if t == "materials"
        else f"Cells ({len(CELL_TABLES)} tables)",
    )

    tables = MATERIAL_TABLES if table_type == "materials" else CELL_TABLES

    def table_label(t):
        count = reader.get_row_count(t)
        return f"{t} ({count} records)"

    return prompt_choice("Select table:", tables, label_fn=table_label)


def select_record_interactive(
    reader: SQLiteReader, table_name: str,
) -> dict[str, Any]:
    """Interactively select a record from a table."""
    summaries = reader.get_records_summary(table_name)
    if not summaries:
        raise SystemExit(f"No records found in {table_name}.")

    is_material = table_name in set(MATERIAL_TABLES)
    names = [s["name"] for s in summaries]

    def record_label(name):
        s = next(r for r in summaries if r["name"] == name)
        version = s.get("version", "?")
        date = s.get("date" if is_material else "date_created", "?")
        return f"{name:<30s} (v{version}, {date})"

    selected_name = prompt_choice(
        f"Records in {table_name}:", names, label_fn=record_label,
    )

    row = reader.get_row_by_name(table_name, selected_name)
    if row is None:
        raise SystemExit(f"Record '{selected_name}' not found in {table_name}.")
    return row


def preview_record(
    row: dict[str, Any],
    table_name: str,
    blob_size: int,
    s3_key: str,
    exists_in_dynamo: bool,
) -> None:
    """Print a preview of what will be migrated."""
    is_material = table_name in set(MATERIAL_TABLES)

    print(f"\nPreview:")
    print(f"  Name:    {row['name']}")
    if is_material:
        print(f"  Date:    {row.get('date', '?')}")
    else:
        print(f"  Date:    {row.get('date_created', '?')}")
        print(f"  Form:    {row.get('form_factor', '?')}")
        print(f"  Chem:    {row.get('chemistry', '?')}")
    print(f"  Version: {row.get('version', '?')}")
    print(f"  Size:    {blob_size:,} bytes")
    print(f"  Target:  DynamoDB: {table_name}/{row['name']}")
    print(f"           S3: {s3_key}")

    if exists_in_dynamo:
        print(f"  Status:  EXISTS in DynamoDB - will overwrite")
    else:
        print(f"  Status:  New record")


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def migrate_single_record(
    row: dict[str, Any],
    table_name: str,
    writer: AWSWriter,
    dry_run: bool = False,
) -> None:
    """Upload a single record to S3 + DynamoDB with cleanup on partial failure."""
    blob = extract_object_blob(row)
    s3_key = generate_s3_key(table_name, row["name"])

    if dry_run:
        logger.info(
            f"[DRY-RUN] Would upload {len(blob):,} bytes to s3://{s3_key}"
        )
        item = build_dynamodb_item(row, table_name, s3_key)
        logger.info(f"[DRY-RUN] Would write DynamoDB item: {item}")
        print(f"\n[DRY-RUN] Would migrate {table_name}/{row['name']}")
        return

    # Step 1: Upload to S3
    print(f"\nUploading to S3... ", end="", flush=True)
    writer.upload_object(s3_key, blob)
    print("done")

    # Step 2: Write to DynamoDB (with S3 cleanup on failure)
    print(f"Writing to DynamoDB... ", end="", flush=True)
    try:
        item = build_dynamodb_item(row, table_name, s3_key)
        writer.put_item(item)
        print("done")
    except Exception:
        print("FAILED")
        print("Cleaning up S3 object... ", end="", flush=True)
        try:
            writer.delete_object(s3_key)
            print("done")
        except Exception:
            print(f"FAILED (orphaned object: s3://{s3_key})")
        raise

    # Determine verification endpoint
    if table_name in set(MATERIAL_TABLES):
        endpoint = f"GET /materials/{table_name}/{row['name']}"
    else:
        endpoint = f"GET /cells/{table_name}/{row['name']}"

    print(f"\nMigrated {table_name}/{row['name']}")
    print(f"  Verify: {endpoint}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate individual records from local SQLite to AWS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--table",
        choices=sorted(ALL_TABLES),
        help="Table name (skip interactive table selection)",
    )
    parser.add_argument(
        "--name",
        help="Record name (skip interactive record selection)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--sqlite-path",
        help="Path to SQLite database (default: package database.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing to AWS",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("\nOpenCell Record Migration")
    print("=" * 40)

    # Resolve database path
    if args.sqlite_path:
        db_path = args.sqlite_path
        if not os.path.exists(db_path):
            print(f"Error: Database not found at {db_path}")
            return 1
    else:
        try:
            db_path = find_default_database()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    logger.debug(f"Using database: {db_path}")

    # Build AWS config
    dynamodb_table = os.environ.get("DYNAMODB_TABLE", "opencell-production")
    s3_bucket = os.environ.get("S3_BUCKET", "opencell-production-objects")
    aws_region = os.environ.get("AWS_REGION", "us-east-2")

    writer = AWSWriter(dynamodb_table, s3_bucket, aws_region)

    # Validate AWS access before interactive prompts (fail fast)
    if not args.dry_run:
        print(f"\nValidating AWS access...")
        print(f"  DynamoDB: {dynamodb_table}")
        print(f"  S3:       {s3_bucket}")
        print(f"  Region:   {aws_region}")
        try:
            writer.validate_access()
            print("  Access validated.\n")
        except RuntimeError as e:
            print(f"\nError: {e}")
            print("\nEnsure AWS credentials are configured:")
            print("  aws configure")
            print("  # or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            return 1

    with SQLiteReader(db_path) as reader:
        # Validate requested table exists in SQLite
        db_tables = set(reader.get_table_names())

        # Select table
        if args.table:
            if args.table not in db_tables:
                print(f"Error: Table '{args.table}' not found in database.")
                return 1
            table_name = args.table
        else:
            table_name = select_table_interactive(reader)

        # Select record
        if args.name:
            row = reader.get_row_by_name(table_name, args.name)
            if row is None:
                print(
                    f"Error: Record '{args.name}' not found in {table_name}."
                )
                return 1
        else:
            row = select_record_interactive(reader, table_name)

        # Preview
        try:
            blob = extract_object_blob(row)
        except ValueError as e:
            print(f"Error: {e}")
            return 1

        s3_key = generate_s3_key(table_name, row["name"])
        exists = False
        if not args.dry_run:
            try:
                exists = writer.item_exists(table_name, row["name"])
            except Exception as e:
                print(f"Warning: Could not check if record exists: {e}")

        preview_record(row, table_name, len(blob), s3_key, exists)

        # Confirm
        if not args.yes:
            try:
                answer = input("\nProceed? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1
            if answer not in ("y", "yes"):
                print("Aborted.")
                return 0

        # Migrate
        try:
            migrate_single_record(row, table_name, writer, dry_run=args.dry_run)
        except Exception as e:
            print(f"\nError during migration: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
