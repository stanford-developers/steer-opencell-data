#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024-2026 Stanford University
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Migrate individual records from local SQLite to AWS DynamoDB + S3.

Interactive usage:
    python -m steer_opencell_data.cli.migrate_record

Non-interactive usage:
    python -m steer_opencell_data.cli.migrate_record --table cathode_materials --name LFP --yes

Batch usage:
    python -m steer_opencell_data.cli.migrate_record --table cathode_materials --name all --yes
    python -m steer_opencell_data.cli.migrate_record --table all --section materials --yes

Teardown metadata (the scripts' METADATA / SLUG; see teardown_metadata.py):
    --metadata keep       (default) keep what admins edited in the app; the
                          repo only seeds teardowns that have no metadata/slug
    --metadata override   replace the app's metadata and slug with the repo's
                          (a changed slug stays as an alias, so links work)
    --metadata-only       update just the teardowns' metadata/slug — no cell
                          objects are uploaded
    --carry-from "<old>"  a teardown renamed in the repo: move the old item's
                          slug, aliases and metadata to the new name

Environment variables:
    DYNAMODB_TABLE  Target DynamoDB table (required)
    S3_BUCKET       Target S3 bucket (required)
    AWS_REGION      AWS region (default: us-east-2)

Requires: pip install steer-opencell-data[cli]
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import logging
import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
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

from steer_opencell_data.teardown_metadata import (
    METADATA_MODES,
    TEARDOWN_TABLE,
    MetadataError,
    MetadataPlan,
    merge_metadata,
    parse_metadata_column,
    slug_index,
)

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

_ALL_SENTINEL = "__ALL__"

# Recorded as metadata_updated_by when an upload writes the repo's metadata.
UPLOAD_EDITOR = "steer-opencell-data upload"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of migrating records from a table."""

    table_name: str
    total: int = 0
    migrated: int = 0
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


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

    def put_item(self, item: dict[str, Any], expect: Expectation | None = None) -> None:
        """Put item to DynamoDB (upsert), optionally conditional on ``expect``."""
        table = self._get_dynamodb_table()
        clean_item = {k: v for k, v in item.items() if v is not None}
        kwargs = expect.put_kwargs() if expect else {}
        try:
            table.put_item(Item=clean_item, **kwargs)
        except ClientError as exc:
            _raise_if_condition_failed(exc)
            raise

    def get_item(self, table_name: str, name: str) -> dict[str, Any] | None:
        """Read one item (strongly consistent), including soft-deleted ones."""
        table = self._get_dynamodb_table()
        response = table.get_item(
            Key={"table_name": table_name, "name": name}, ConsistentRead=True
        )
        return response.get("Item")

    def query_table(self, table_name: str) -> list[dict[str, Any]]:
        """Every item in one table partition (paginated)."""
        from boto3.dynamodb.conditions import Key

        table = self._get_dynamodb_table()
        params: dict[str, Any] = {"KeyConditionExpression": Key("table_name").eq(table_name)}
        items: list[dict[str, Any]] = []
        while True:
            response = table.query(**params)
            items.extend(response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                return items
            params["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    def update_attrs(
        self,
        table_name: str,
        name: str,
        set_attrs: dict[str, Any],
        remove_attrs: tuple[str, ...] = (),
        expect: Expectation | None = None,
    ) -> None:
        """UpdateItem: SET/REMOVE attributes on an existing, live item."""
        table = self._get_dynamodb_table()
        names: dict[str, str] = {"#n": "name", "#d": "deleted"}
        values: dict[str, Any] = {":f": False}
        clauses = []
        if set_attrs:
            sets = []
            for i, (attr, value) in enumerate(set_attrs.items()):
                names[f"#s{i}"] = attr
                values[f":s{i}"] = value
                sets.append(f"#s{i} = :s{i}")
            clauses.append("SET " + ", ".join(sets))
        if remove_attrs:
            removes = []
            for i, attr in enumerate(remove_attrs):
                names[f"#r{i}"] = attr
                removes.append(f"#r{i}")
            clauses.append("REMOVE " + ", ".join(removes))
        condition = "attribute_exists(#n) AND (attribute_not_exists(#d) OR #d = :f)"
        if expect:
            extra, extra_names, extra_values = expect.condition()
            if extra:
                condition = f"{condition} AND {extra}"
                names.update(extra_names)
                values.update(extra_values)
        try:
            table.update_item(
                Key={"table_name": table_name, "name": name},
                UpdateExpression=" ".join(clauses),
                ConditionExpression=condition,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
        except ClientError as exc:
            _raise_if_condition_failed(exc)
            raise


class ConditionFailed(Exception):
    """A conditional DynamoDB write found the item changed since it was read."""


def _raise_if_condition_failed(exc: ClientError) -> None:
    if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
        raise ConditionFailed(str(exc)) from exc


@dataclass
class Expectation:
    """The state a conditional write expects to find (optimistic concurrency).

    ``new``: the item must not exist. Otherwise its ``metadata_updated_at``
    must still be ``updated_at`` (``None``: still unset) — i.e. no admin has
    edited the metadata since the upload read it.
    """

    new: bool = False
    updated_at: str | None = None

    def condition(self) -> tuple[str, dict[str, str], dict[str, Any]]:
        if self.new:
            return "attribute_not_exists(#xn)", {"#xn": "name"}, {}
        if self.updated_at is None:
            return "attribute_not_exists(#xu)", {"#xu": "metadata_updated_at"}, {}
        return "#xu = :xu", {"#xu": "metadata_updated_at"}, {":xu": self.updated_at}

    def put_kwargs(self) -> dict[str, Any]:
        expression, names, values = self.condition()
        kwargs: dict[str, Any] = {
            "ConditionExpression": expression,
            "ExpressionAttributeNames": names,
        }
        if values:
            kwargs["ExpressionAttributeValues"] = values
        return kwargs

    @classmethod
    def of(cls, item: dict[str, Any] | None) -> Expectation:
        if item is None:
            return cls(new=True)
        return cls(updated_at=item.get("metadata_updated_at"))


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


def to_dynamo(value: Any) -> Any:
    """JSON-compatible data → DynamoDB-safe (floats become Decimal)."""
    return json.loads(json.dumps(value), parse_float=Decimal)


def from_dynamo(value: Any) -> Any:
    """DynamoDB data → plain JSON types (Decimal → int/float), for comparison."""
    def default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return int(obj) if obj == obj.to_integral_value() else float(obj)
        if isinstance(obj, set):
            return sorted(obj)
        raise TypeError(type(obj))

    return json.loads(json.dumps(value, default=default))


class TeardownMetadataSync:
    """Decides and tracks the metadata attributes an upload writes.

    Reads the live teardowns once to know which slugs are taken, reads each
    teardown's current item before writing it, and writes conditionally so
    an admin edit made in the app in the meantime is never lost (one retry).
    """

    def __init__(
        self,
        writer: AWSWriter,
        mode: str,
        carry_from: str | None = None,
        can_read: bool = True,
    ):
        self.writer = writer
        self.mode = mode
        self.carry_from = carry_from
        self.can_read = can_read
        self._items: dict[str, dict[str, Any]] | None = None
        self.now = datetime.now(timezone.utc).isoformat()

    def _live_items(self) -> dict[str, dict[str, Any]]:
        if self._items is None:
            self._items = {}
            if self.can_read:
                for item in self.writer.query_table(TEARDOWN_TABLE):
                    self._items[item["name"]] = from_dynamo(item)
        return self._items

    def read(self, name: str) -> dict[str, Any] | None:
        if not self.can_read:
            return None
        item = self.writer.get_item(TEARDOWN_TABLE, name)
        return from_dynamo(item) if item is not None else None

    def plan(self, row: dict[str, Any]) -> tuple[MetadataPlan, dict[str, Any] | None]:
        """``(plan, item as read)`` for a SQLite teardown row."""
        name = row["name"]
        current = self.read(name)
        source = current
        if self.carry_from:
            source = self.read(self.carry_from)
            if source is None or source.get("deleted"):
                raise MetadataError(f"--carry-from: no live teardown '{self.carry_from}'")
        if source is not None and source.get("deleted"):
            source = None  # a soft-deleted item's slugs were released
        exclude = {name} | ({self.carry_from} if self.carry_from else set())
        plan = merge_metadata(
            name=name,
            existing=source,
            repo_metadata=parse_metadata_column(row.get("metadata")),
            repo_slug=row.get("slug") or None,
            mode=self.mode,
            taken=slug_index(list(self._live_items().values()), exclude=exclude),
            now=self.now,
            editor=UPLOAD_EDITOR,
        )
        if self.carry_from:
            plan.summary = f"carried from '{self.carry_from}': {plan.summary}"
        return plan, current

    def record(self, name: str, attrs: dict[str, Any]) -> None:
        """Remember a written item so later slugs in the batch avoid it."""
        items = self._live_items()
        items[name] = {**items.get(name, {"name": name}), **from_dynamo(attrs)}
        if self.carry_from and self.carry_from in items:
            for attr in ("slug", "slug_aliases"):
                items[self.carry_from].pop(attr, None)

    def release_carried_slugs(self) -> None:
        """Remove the slug and aliases from the ``--carry-from`` source item."""
        if self.carry_from:
            self.writer.update_attrs(
                TEARDOWN_TABLE, self.carry_from, {}, remove_attrs=("slug", "slug_aliases")
            )


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

def prompt_choice(
    prompt_text: str,
    options: list[str],
    label_fn=None,
    allow_all: bool = False,
    all_label: str = "All",
) -> str:
    """Display numbered options and return the selected value.

    When *allow_all* is True, option ``0`` is prepended for selecting all items
    and the sentinel ``_ALL_SENTINEL`` is returned if chosen.
    """
    print(f"\n{prompt_text}")
    if allow_all:
        print(f"  0. {all_label}")
    for i, opt in enumerate(options, 1):
        label = label_fn(opt) if label_fn else opt
        print(f"  {i}. {label}")

    min_val = 0 if allow_all else 1
    while True:
        try:
            raw = input("> ").strip()
            if allow_all and raw.lower() == "all":
                return _ALL_SENTINEL
            idx = int(raw)
            if allow_all and idx == 0:
                return _ALL_SENTINEL
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except (ValueError, EOFError):
            pass
        print(f"  Please enter a number between {min_val} and {len(options)}.")


def select_table_interactive(reader: SQLiteReader) -> str | list[str]:
    """Interactively select a table type, then a specific table.

    Returns a single table name, or a list of table names when the user
    chooses "All tables" for the selected section.
    """
    table_type = prompt_choice(
        "Select table type:",
        ["materials", "cells"],
        label_fn=lambda t: f"Materials ({len(MATERIAL_TABLES)} tables)"
        if t == "materials"
        else f"Cells ({len(CELL_TABLES)} tables)",
    )

    tables = MATERIAL_TABLES if table_type == "materials" else CELL_TABLES

    total_records = sum(reader.get_row_count(t) for t in tables)

    def table_label(t):
        count = reader.get_row_count(t)
        return f"{t} ({count} records)"

    selected = prompt_choice(
        "Select table:",
        tables,
        label_fn=table_label,
        allow_all=True,
        all_label=f"All {table_type} tables ({len(tables)} tables, {total_records} records)",
    )

    if selected == _ALL_SENTINEL:
        return list(tables)
    return selected


def select_record_interactive(
    reader: SQLiteReader, table_name: str,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Interactively select a record from a table.

    Returns a single row dict, or a list of all row dicts when the user
    chooses "All records".
    """
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
        f"Records in {table_name}:",
        names,
        label_fn=record_label,
        allow_all=True,
        all_label=f"All records ({len(names)} records)",
    )

    if selected_name == _ALL_SENTINEL:
        return list(reader.iter_rows(table_name))

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
    quiet: bool = False,
    teardown_sync: TeardownMetadataSync | None = None,
    metadata_only: bool = False,
) -> str | None:
    """Upload a single record to S3 + DynamoDB with cleanup on partial failure.

    For a teardown (with ``teardown_sync``) the metadata attributes are
    merged per ``--metadata keep|override`` and the write is conditional on
    the item not having changed since it was read (one retry). With
    ``metadata_only`` only those attributes are updated and nothing goes to
    S3. Returns a one-line summary of the metadata decision, if any.
    """
    is_teardown = table_name == TEARDOWN_TABLE and teardown_sync is not None
    if metadata_only:
        if not is_teardown:
            raise ValueError("--metadata-only applies to teardowns only")
        return _sync_metadata_only(row, writer, teardown_sync, dry_run, quiet)

    blob = extract_object_blob(row)
    s3_key = generate_s3_key(table_name, row["name"])

    if dry_run:
        logger.info(
            f"[DRY-RUN] Would upload {len(blob):,} bytes to s3://{s3_key}"
        )
        item = build_dynamodb_item(row, table_name, s3_key)
        summary = None
        if is_teardown:
            plan, _current = teardown_sync.plan(row)
            item.update(plan.attrs)
            summary = _report_plan(plan, quiet)
        logger.info(f"[DRY-RUN] Would write DynamoDB item: {item}")
        if not quiet:
            print(f"\n[DRY-RUN] Would migrate {table_name}/{row['name']}")
        return summary

    # Step 1: Upload to S3
    if not quiet:
        print(f"\nUploading to S3... ", end="", flush=True)
    writer.upload_object(s3_key, blob)
    if not quiet:
        print("done")

    # Step 2: Write to DynamoDB (with S3 cleanup on failure)
    if not quiet:
        print(f"Writing to DynamoDB... ", end="", flush=True)
    summary = None
    try:
        if is_teardown:
            for attempt in (1, 2):
                plan, current = teardown_sync.plan(row)
                item = build_dynamodb_item(row, table_name, s3_key)
                item.update(to_dynamo(plan.attrs))
                try:
                    writer.put_item(item, expect=Expectation.of(current))
                    break
                except ConditionFailed:
                    if attempt == 2:
                        raise RuntimeError(
                            "the teardown changed in DynamoDB while uploading "
                            "(an admin edit?); run the upload again"
                        )
            teardown_sync.record(row["name"], plan.attrs)
            teardown_sync.release_carried_slugs()
            summary = _report_plan(plan, quiet=True)
        else:
            item = build_dynamodb_item(row, table_name, s3_key)
            writer.put_item(item)
        if not quiet:
            print("done")
    except Exception:
        if not quiet:
            print("FAILED")
            print("Cleaning up S3 object... ", end="", flush=True)
        try:
            writer.delete_object(s3_key)
            if not quiet:
                print("done")
        except Exception:
            if not quiet:
                print(f"FAILED (orphaned object: s3://{s3_key})")
        raise

    if not quiet:
        # Determine verification endpoint
        if table_name in set(MATERIAL_TABLES):
            endpoint = f"GET /materials/{table_name}/{row['name']}"
        else:
            endpoint = f"GET /cells/{table_name}/{row['name']}"

        print(f"\nMigrated {table_name}/{row['name']}")
        if summary:
            print(f"  Metadata: {summary}")
        print(f"  Verify: {endpoint}")
    return summary


def _report_plan(plan: MetadataPlan, quiet: bool) -> str:
    for warning in plan.warnings:
        logger.warning(warning)
    if not quiet:
        print(f"  Metadata: {plan.summary}")
    return plan.summary


def _sync_metadata_only(
    row: dict[str, Any],
    writer: AWSWriter,
    teardown_sync: TeardownMetadataSync,
    dry_run: bool,
    quiet: bool,
) -> str:
    """Update one teardown's metadata attributes only (UpdateItem, no S3)."""
    name = row["name"]
    for attempt in (1, 2):
        plan, current = teardown_sync.plan(row)
        if current is None or current.get("deleted"):
            raise ValueError(
                "not in DynamoDB (or soft-deleted); upload it without --metadata-only"
            )
        if dry_run:
            if not quiet:
                print(f"\n[DRY-RUN] Would update metadata of {TEARDOWN_TABLE}/{name}")
            return _report_plan(plan, quiet)
        try:
            writer.update_attrs(
                TEARDOWN_TABLE, name, to_dynamo(plan.attrs), expect=Expectation.of(current)
            )
            break
        except ConditionFailed:
            if attempt == 2:
                raise RuntimeError(
                    "the teardown changed in DynamoDB while updating "
                    "(an admin edit?); run the upload again"
                )
    teardown_sync.record(name, plan.attrs)
    teardown_sync.release_carried_slugs()
    if not quiet:
        print(f"\nUpdated metadata of {TEARDOWN_TABLE}/{name}")
    return _report_plan(plan, quiet)


def preview_batch(
    rows_by_table: dict[str, list[dict[str, Any]]],
) -> None:
    """Print a summary preview of a batch migration."""
    total_records = sum(len(rows) for rows in rows_by_table.values())

    print(f"\nBatch Migration Preview")
    print("=" * 40)
    for tbl in sorted(rows_by_table):
        print(f"  {tbl:<40s} {len(rows_by_table[tbl]):>3d} records")
    print(f"  {'-' * 40}")
    print(
        f"  Total: {total_records} records across "
        f"{len(rows_by_table)} table(s)"
    )


def migrate_batch(
    rows_by_table: dict[str, list[dict[str, Any]]],
    writer: AWSWriter,
    dry_run: bool = False,
    teardown_sync: TeardownMetadataSync | None = None,
    metadata_only: bool = False,
) -> list[MigrationResult]:
    """Migrate multiple records across one or more tables.

    Continues on individual record failure and collects errors.
    """
    results: list[MigrationResult] = []
    total_records = sum(len(rows) for rows in rows_by_table.values())
    counter = 0

    for table_name in sorted(rows_by_table):
        rows = rows_by_table[table_name]
        result = MigrationResult(table_name=table_name, total=len(rows))

        print(f"\n{table_name} ({len(rows)} records)")
        for row in rows:
            counter += 1
            name = row.get("name", "<unknown>")
            print(
                f"  [{counter}/{total_records}] {table_name}/{name} ... ",
                end="",
                flush=True,
            )
            try:
                summary = migrate_single_record(
                    row, table_name, writer, dry_run=dry_run, quiet=True,
                    teardown_sync=teardown_sync, metadata_only=metadata_only,
                )
                result.migrated += 1
                status = "done" if not dry_run else "dry-run ok"
                print(f"{status} ({summary})" if summary else status)
            except Exception as e:
                result.errors += 1
                result.error_details.append((name, str(e)))
                print(f"FAILED: {e}")

        results.append(result)

    return results


def print_batch_summary(results: list[MigrationResult]) -> None:
    """Print a summary table after batch migration."""
    total_migrated = sum(r.migrated for r in results)
    total_errors = sum(r.errors for r in results)
    total_records = sum(r.total for r in results)

    print(f"\nMigration Summary")
    print("=" * 60)
    for r in results:
        status = "OK" if r.errors == 0 else "ERRORS"
        print(f"  {r.table_name:<40s} {r.migrated:>3d}/{r.total:>3d}  [{status}]")
    print("-" * 60)
    print(
        f"  Total: {total_migrated} migrated, {total_errors} errors "
        f"out of {total_records} records"
    )

    if total_errors > 0:
        print(f"\n  Failed records:")
        for r in results:
            for name, err in r.error_details:
                print(f"    - {r.table_name}/{name}: {err}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate records from local SQLite to AWS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--table",
        help=(
            "Table name, or 'all' to migrate all tables in a section "
            "(skip interactive table selection)"
        ),
    )
    parser.add_argument(
        "--section",
        choices=["materials", "cells"],
        help="Table section (required when --table all)",
    )
    parser.add_argument(
        "--name",
        help=(
            "Record name, or 'all' to migrate every record in the table(s) "
            "(skip interactive record selection)"
        ),
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
        "--metadata",
        choices=METADATA_MODES,
        help=(
            "Teardown metadata: 'keep' (default) keeps what admins edited in the "
            "app and only seeds what is missing; 'override' replaces it with the "
            "repo's. Prompted for when omitted without --yes."
        ),
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Update only the teardowns' metadata and slug (no cell objects uploaded)",
    )
    parser.add_argument(
        "--carry-from",
        metavar="OLD_NAME",
        help=(
            "For one teardown renamed in the repo: move the old item's slug, "
            "aliases and metadata to the new name (so external links follow it)"
        ),
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

    # ------------------------------------------------------------------
    # Validate CLI argument combinations
    # ------------------------------------------------------------------
    if args.table and args.table.lower() == "all":
        if not args.section:
            print("Error: --section (materials|cells) is required when --table all")
            return 1
        args.table = "all"
    elif args.table and args.table not in ALL_TABLES:
        print(f"Error: Unknown table '{args.table}'.")
        print(f"  Valid tables: {', '.join(sorted(ALL_TABLES))}")
        print(f"  Or use --table all --section materials|cells")
        return 1

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

    # Build AWS config — targets must be set explicitly so a stray invocation
    # can never write to an unintended deployment.
    dynamodb_table = os.environ.get("DYNAMODB_TABLE")
    s3_bucket = os.environ.get("S3_BUCKET")
    if not dynamodb_table or not s3_bucket:
        print(
            "Error: DYNAMODB_TABLE and S3_BUCKET environment variables must be "
            "set to the migration target (e.g. export DYNAMODB_TABLE=my-table "
            "S3_BUCKET=my-bucket)."
        )
        return 1
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
        db_tables = set(reader.get_table_names())

        # ------------------------------------------------------------------
        # Resolve tables → rows_by_table: dict[str, list[dict]]
        # ------------------------------------------------------------------
        rows_by_table: dict[str, list[dict[str, Any]]] = {}

        if args.table == "all":
            # --table all --section materials|cells
            tables = (
                MATERIAL_TABLES if args.section == "materials" else CELL_TABLES
            )
            for t in tables:
                if t not in db_tables:
                    print(f"Warning: Table '{t}' not in database, skipping.")
                    continue
                rows_by_table[t] = list(reader.iter_rows(t))

        elif args.table:
            # Specific table via CLI
            if args.table not in db_tables:
                print(f"Error: Table '{args.table}' not found in database.")
                return 1

            if args.name and args.name.lower() == "all":
                rows_by_table[args.table] = list(reader.iter_rows(args.table))
            elif args.name:
                row = reader.get_row_by_name(args.table, args.name)
                if row is None:
                    print(
                        f"Error: Record '{args.name}' not found "
                        f"in {args.table}."
                    )
                    return 1
                rows_by_table[args.table] = [row]
            else:
                # Interactive record selection
                selection = select_record_interactive(reader, args.table)
                if isinstance(selection, list):
                    rows_by_table[args.table] = selection
                else:
                    rows_by_table[args.table] = [selection]

        else:
            # Fully interactive: pick table (or all tables), then records
            table_selection = select_table_interactive(reader)
            if isinstance(table_selection, list):
                # "All tables" chosen — migrate all records in each
                for t in table_selection:
                    rows_by_table[t] = list(reader.iter_rows(t))
            else:
                # Single table — pick record(s)
                if args.name and args.name.lower() == "all":
                    rows_by_table[table_selection] = list(
                        reader.iter_rows(table_selection)
                    )
                elif args.name:
                    row = reader.get_row_by_name(table_selection, args.name)
                    if row is None:
                        print(
                            f"Error: Record '{args.name}' not found "
                            f"in {table_selection}."
                        )
                        return 1
                    rows_by_table[table_selection] = [row]
                else:
                    selection = select_record_interactive(
                        reader, table_selection,
                    )
                    if isinstance(selection, list):
                        rows_by_table[table_selection] = selection
                    else:
                        rows_by_table[table_selection] = [selection]

        # ------------------------------------------------------------------
        # Determine single vs batch mode
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Teardown metadata options
        # ------------------------------------------------------------------
        if args.metadata_only:
            skipped = sorted(t for t in rows_by_table if t != TEARDOWN_TABLE)
            if skipped:
                print(f"--metadata-only: skipping {', '.join(skipped)} (teardowns only).")
            rows_by_table = {
                t: rows for t, rows in rows_by_table.items() if t == TEARDOWN_TABLE
            }
        if args.carry_from:
            teardown_rows = rows_by_table.get(TEARDOWN_TABLE, [])
            if len(teardown_rows) != 1 or len(rows_by_table) != 1:
                print("Error: --carry-from needs exactly one teardown "
                      "(--table teardowns --name <new name>).")
                return 1
            if teardown_rows[0]["name"] == args.carry_from:
                print("Error: --carry-from names the teardown being uploaded.")
                return 1

        total_records = sum(len(rows) for rows in rows_by_table.values())
        if total_records == 0:
            print("No records to migrate.")
            return 0

        teardown_sync = None
        if TEARDOWN_TABLE in rows_by_table:
            mode = args.metadata
            if mode is None and not args.yes:
                mode = prompt_choice(
                    "Teardown metadata — what admins edited in the app:",
                    list(METADATA_MODES),
                    label_fn=lambda m: (
                        "Keep it (only seed teardowns that have none)"
                        if m == "keep"
                        else "Override it with this repo's METADATA / SLUG"
                    ),
                )
            mode = mode or "keep"
            can_read = True
            if args.dry_run:
                try:
                    writer.validate_access()
                except RuntimeError as e:
                    can_read = False
                    print(f"Warning: cannot read DynamoDB ({e}); the dry run "
                          "assumes no teardown exists yet.")
            teardown_sync = TeardownMetadataSync(
                writer, mode, carry_from=args.carry_from, can_read=can_read
            )
            print(f"\nTeardown metadata mode: {mode}"
                  + (" (metadata only)" if args.metadata_only else "")
                  + (f", carried from '{args.carry_from}'" if args.carry_from else ""))

        is_batch = total_records > 1 or args.metadata_only

        # ------------------------------------------------------------------
        # Preview
        # ------------------------------------------------------------------
        if is_batch:
            preview_batch(rows_by_table)
        else:
            table_name = next(iter(rows_by_table))
            row = rows_by_table[table_name][0]
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

        # ------------------------------------------------------------------
        # Confirm
        # ------------------------------------------------------------------
        if not args.yes:
            try:
                answer = input("\nProceed? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1
            if answer not in ("y", "yes"):
                print("Aborted.")
                return 0

        # ------------------------------------------------------------------
        # Migrate
        # ------------------------------------------------------------------
        if is_batch:
            results = migrate_batch(
                rows_by_table, writer, dry_run=args.dry_run,
                teardown_sync=teardown_sync, metadata_only=args.metadata_only,
            )
            print_batch_summary(results)
            total_errors = sum(r.errors for r in results)
            return 1 if total_errors > 0 else 0
        else:
            table_name = next(iter(rows_by_table))
            row = rows_by_table[table_name][0]
            try:
                migrate_single_record(
                    row, table_name, writer, dry_run=args.dry_run,
                    teardown_sync=teardown_sync,
                )
            except Exception as e:
                print(f"\nError during migration: {e}")
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
