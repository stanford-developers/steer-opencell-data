#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024-2026 Stanford University
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Copy each teardown script's METADATA and SLUG into the SQLite database
without rebuilding the cells.

A teardown script stores its METADATA/SLUG when it is run, but running it
rebuilds the cell too. After editing only the metadata (a link, a citation),
this updates just the ``metadata`` and ``slug`` columns of the ``teardowns``
table, reading the values from the scripts with ``ast`` (nothing is executed),
so the cell objects and their ``date_created`` are untouched.

Usage:
    python -m steer_opencell_data.cli.sync_metadata            # update SQLite
    python -m steer_opencell_data.cli.sync_metadata --dry-run  # show changes only
    python -m steer_opencell_data.cli.sync_metadata --check    # exit 1 if out of date

Every script's METADATA and SLUG are validated, and slugs must be unique.
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from steer_opencell_data.teardown_metadata import (
    TEARDOWN_COLUMNS,
    TEARDOWN_TABLE,
    MetadataError,
    metadata_json,
    parse_script,
    slugify,
    validate_slug,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPTS_DIR = REPO_ROOT / "cell_teardowns"


@dataclass
class ScriptMetadata:
    path: Path
    cell_name: str
    metadata: str  # canonical JSON text
    slug: str


def default_database() -> str:
    with importlib.resources.path("steer_opencell_data", "database.db") as db_path:
        return str(db_path)


def read_scripts(scripts_dir: Path) -> list[ScriptMetadata]:
    """Parse and validate every teardown script; raise on any problem."""
    found: list[ScriptMetadata] = []
    problems: list[str] = []
    for path in sorted(scripts_dir.glob("*.py")):
        try:
            values = parse_script(path)
            if values["table_name"] != TEARDOWN_TABLE:
                continue
            if values["METADATA"] is None:
                problems.append(f"{path.name}: no METADATA dict")
                continue
            if not isinstance(values["cell_name"], str):
                problems.append(f"{path.name}: no literal cell_name")
                continue
            found.append(
                ScriptMetadata(
                    path=path,
                    cell_name=values["cell_name"],
                    metadata=metadata_json(values["METADATA"]),
                    slug=validate_slug(values["SLUG"]) or slugify(values["cell_name"]),
                )
            )
        except (MetadataError, SyntaxError) as exc:
            problems.append(f"{path.name}: {exc}")

    by_slug: dict[str, str] = {}
    for script in found:
        other = by_slug.setdefault(script.slug, script.path.name)
        if other != script.path.name:
            problems.append(
                f"slug '{script.slug}' is used by {other} and {script.path.name}"
            )

    if problems:
        raise MetadataError("\n".join(problems))
    return found


def column_values(conn: sqlite3.Connection) -> dict[str, tuple[str | None, str | None]]:
    """``name -> (metadata, slug)`` as stored (``None`` for missing columns)."""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info([{TEARDOWN_TABLE}])")}
    meta_col = "metadata" if "metadata" in columns else "NULL"
    slug_col = "slug" if "slug" in columns else "NULL"
    rows = conn.execute(f"SELECT name, {meta_col}, {slug_col} FROM [{TEARDOWN_TABLE}]")
    return {name: (meta, slug) for name, meta, slug in rows}


def _same_metadata(stored: str | None, wanted: str) -> bool:
    if stored is None:
        return False
    try:
        return json.loads(stored) == json.loads(wanted)
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--sqlite-path", help="Database (default: the package database.db)"
    )
    parser.add_argument("--scripts-dir", default=str(DEFAULT_SCRIPTS_DIR))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="Show changes, write nothing"
    )
    mode.add_argument(
        "--check", action="store_true", help="Exit 1 if SQLite differs from the scripts"
    )
    args = parser.parse_args(argv)

    try:
        scripts = read_scripts(Path(args.scripts_dir))
    except MetadataError as exc:
        print(f"Invalid teardown metadata:\n{exc}")
        return 1

    conn = sqlite3.connect(args.sqlite_path or default_database())
    try:
        stored = column_values(conn)
        changes: list[ScriptMetadata] = []
        for script in scripts:
            if script.cell_name not in stored:
                print(
                    f"  ! {script.path.name}: no '{script.cell_name}' row in SQLite "
                    "(run the script to build the cell)"
                )
                continue
            meta, slug = stored[script.cell_name]
            if _same_metadata(meta, script.metadata) and slug == script.slug:
                continue
            changes.append(script)
            print(
                f"  ~ {script.cell_name}: slug {slug!r} -> {script.slug!r}"
                + (
                    ""
                    if _same_metadata(meta, script.metadata)
                    else ", metadata changed"
                )
            )

        if not changes:
            print("Teardown metadata in SQLite matches the scripts.")
            return 0
        if args.check:
            print(
                "SQLite is out of date: run python -m steer_opencell_data.cli.sync_metadata"
            )
            return 1
        if args.dry_run:
            print(f"[DRY-RUN] Would update {len(changes)} teardown(s).")
            return 0

        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{TEARDOWN_TABLE}])")
        existing = {row[1] for row in cursor.fetchall()}
        for name, column_type in TEARDOWN_COLUMNS.items():
            if name not in existing:
                cursor.execute(
                    f"ALTER TABLE [{TEARDOWN_TABLE}] ADD COLUMN {name} {column_type}"
                )
        cursor.executemany(
            f"UPDATE [{TEARDOWN_TABLE}] SET metadata = ?, slug = ? WHERE name = ?",
            [(s.metadata, s.slug, s.cell_name) for s in changes],
        )
        conn.commit()
        print(f"Updated {len(changes)} teardown(s).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
