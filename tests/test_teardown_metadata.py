# SPDX-FileCopyrightText: 2024-2026 Stanford University
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for teardown metadata: the scripts' METADATA/SLUG, the SQLite columns,
and the upload's keep / override / metadata-only / carry-from behaviour.

The upload is exercised against an in-memory stand-in for the DynamoDB table
(conditional writes included), so nothing here reaches AWS or needs the
engine installed.
"""

from __future__ import annotations

import copy
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from steer_opencell_data.cli import migrate_record as mr
from steer_opencell_data.cli import sync_metadata
from steer_opencell_data.teardown_metadata import (
    MetadataError,
    merge_metadata,
    metadata_json,
    next_slugs,
    parse_metadata_column,
    parse_script,
    slug_index,
    slugify,
    teardown_columns,
    unique_slug,
    validate_metadata,
)

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((REPO / "cell_teardowns").glob("*.py"))
NOW = "2026-10-21T12:00:00+00:00"


# -- the scripts -----------------------------------------------------------


def test_there_are_teardown_scripts() -> None:
    assert len(SCRIPTS) >= 10


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_every_teardown_script_has_valid_metadata(path: Path) -> None:
    values = parse_script(path)
    assert values["table_name"] == "teardowns"
    assert isinstance(values["cell_name"], str)
    assert isinstance(values["METADATA"], dict)
    validate_metadata(values["METADATA"])
    source = path.read_text()
    assert "TEARDOWN ATTRIBUTION" not in source  # replaced by METADATA
    assert "**teardown_columns(METADATA, SLUG, cell_name)" in source
    assert "db.ensure_columns(table_name, TEARDOWN_COLUMNS)" in source


def test_script_slugs_are_unique() -> None:
    scripts = sync_metadata.read_scripts(REPO / "cell_teardowns")
    slugs = [s.slug for s in scripts]
    assert len(slugs) == len(set(slugs)) == len(SCRIPTS)
    assert "tesla-4680" in slugs


def test_tesla_carries_its_citation_and_paper_link() -> None:
    values = parse_script(REPO / "cell_teardowns" / "TESLA_4680.py")
    meta = validate_metadata(values["METADATA"])
    assert meta["source_type"] == "literature"
    assert meta["citation"].startswith("Ank, M. et al. (2023)")
    assert meta["links"][0]["url"].startswith("https://iopscience.iop.org/")


def test_parse_script_refuses_non_literals(tmp_path: Path) -> None:
    script = tmp_path / "x.py"
    script.write_text("table_name = 'teardowns'\nMETADATA = dict(a=1)\n")
    with pytest.raises(MetadataError):
        parse_script(script)


# -- helpers ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("TESLA 4680", "tesla-4680"),
        ("Vendor G10 NFM", "vendor-g10-nfm"),
        ("  --Weird__Name.v2!! ", "weird-name-v2"),
        ("Ünïcödé Çell", "unicode-cell"),
        ("日本語", "teardown"),
        ("x" * 100, "x" * 80),
    ],
)
def test_slugify_matches_the_data_api(name: str, slug: str) -> None:
    # The same vectors as steer-data-infrastructure tests/unit/test_teardown_metadata.py
    assert slugify(name) == slug


def test_unique_and_next_slugs() -> None:
    assert unique_slug("a", {"a", "a-2"}) == "a-3"
    assert next_slugs("b", ["a"], "c") == ("c", ["a", "b"])
    assert next_slugs("b", ["a"], "a") == ("a", ["b"])


@pytest.mark.parametrize(
    "metadata",
    [
        {"colour": "red"},
        {"year": "2022"},
        {"year": 1800},
        {"source_type": "rumour"},
        {"links": [{"label": "x", "url": "javascript:alert(1)"}]},
        {"links": [{"label": "", "url": "https://e.com"}]},
        {"links": [{"label": "x", "url": "https://e.com", "kind": "video"}]},
        {"description": "x" * 2001},
    ],
)
def test_invalid_metadata_is_refused(metadata: dict[str, Any]) -> None:
    with pytest.raises(MetadataError):
        validate_metadata(metadata)


def test_metadata_json_drops_empties_and_round_trips() -> None:
    text = metadata_json(
        {"description": " A ", "notes": None, "model": "", "links": []}
    )
    assert json.loads(text) == {"description": "A"}
    assert parse_metadata_column(text) == {"description": "A"}
    assert parse_metadata_column(None) is None


def test_teardown_columns_derive_the_slug() -> None:
    cols = teardown_columns({"model": "4680"}, None, "TESLA 4680")
    assert cols["slug"] == ["tesla-4680"]
    assert json.loads(cols["metadata"][0]) == {"model": "4680"}
    with pytest.raises(MetadataError):
        teardown_columns({}, "Not A Slug", "x")


def test_slug_index_skips_excluded_and_deleted() -> None:
    items = [
        {"name": "A", "slug": "a", "slug_aliases": ["old-a"]},
        {"name": "B", "slug": "b"},
        {"name": "C", "slug": "c", "deleted": True},
    ]
    assert slug_index(items, exclude={"B"}) == {"a": "A", "old-a": "A"}


# -- merge: keep / override -------------------------------------------------


def merge(existing, repo_metadata, repo_slug, mode, taken=None, name="TESLA 4680"):
    return merge_metadata(
        name=name,
        existing=existing,
        repo_metadata=repo_metadata,
        repo_slug=repo_slug,
        mode=mode,
        taken=taken or {},
        now=NOW,
        editor="upload",
    )


EDITED = {
    "name": "TESLA 4680",
    "metadata": {"description": "edited in the app"},
    "slug": "tesla-4680-2022",
    "slug_aliases": ["tesla-4680"],
    "metadata_updated_at": "2026-10-20T09:00:00+00:00",
    "metadata_updated_by": "admin@example.com",
}
REPO_META = {"description": "from the repo"}


def test_keep_preserves_admin_edits() -> None:
    plan = merge(EDITED, REPO_META, "tesla-4680", "keep")
    assert plan.attrs["metadata"] == {"description": "edited in the app"}
    assert plan.attrs["slug"] == "tesla-4680-2022"
    assert plan.attrs["slug_aliases"] == ["tesla-4680"]
    assert plan.attrs["metadata_updated_by"] == "admin@example.com"


def test_keep_seeds_a_new_teardown() -> None:
    plan = merge(None, REPO_META, "tesla-4680", "keep")
    assert plan.attrs["metadata"] == REPO_META
    assert plan.attrs["slug"] == "tesla-4680"
    assert plan.attrs["slug_aliases"] == []
    assert plan.attrs["metadata_updated_at"] == NOW
    assert plan.attrs["metadata_updated_by"] == "upload"


def test_keep_seeds_an_item_uploaded_before_metadata_existed() -> None:
    plan = merge({"name": "TESLA 4680"}, REPO_META, None, "keep")
    assert plan.attrs["metadata"] == REPO_META
    assert plan.attrs["slug"] == "tesla-4680"


def test_keep_without_repo_metadata_writes_none() -> None:
    plan = merge(None, None, None, "keep")
    assert "metadata" not in plan.attrs
    assert plan.attrs["slug"] == "tesla-4680"


def test_keep_makes_a_seeded_slug_unique_and_warns() -> None:
    plan = merge(None, None, "tesla-4680", "keep", taken={"tesla-4680": "Other"})
    assert plan.attrs["slug"] == "tesla-4680-2"
    assert plan.warnings


def test_override_replaces_and_keeps_the_old_slug_as_an_alias() -> None:
    plan = merge(EDITED, REPO_META, "tesla-4680", "override")
    assert plan.attrs["metadata"] == REPO_META
    assert plan.attrs["metadata_updated_at"] == NOW
    # the repo's slug was an alias: reclaimed; the app's slug becomes the alias
    assert plan.attrs["slug"] == "tesla-4680"
    assert plan.attrs["slug_aliases"] == ["tesla-4680-2022"]


def test_override_without_repo_metadata_keeps_the_dbs() -> None:
    plan = merge(EDITED, None, None, "override")
    assert plan.attrs["metadata"] == EDITED["metadata"]
    assert plan.attrs["slug"] == "tesla-4680-2022"
    assert plan.warnings


def test_override_refuses_a_slug_another_teardown_uses() -> None:
    with pytest.raises(MetadataError):
        merge(
            EDITED, REPO_META, "byd-46120", "override", taken={"byd-46120": "BYD 46120"}
        )


def test_an_unknown_mode_is_refused() -> None:
    with pytest.raises(ValueError):
        merge(None, None, None, "replace")


# -- the upload, against an in-memory table --------------------------------


class FakeWriter:
    """``AWSWriter`` for the teardowns partition, with conditional writes."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.uploaded: list[str] = []
        self.deleted_objects: list[str] = []
        self.before_write = None  # hook: simulate a concurrent admin edit

    def _check(self, key, expect) -> None:
        if expect is None:
            return
        item = self.items.get(key)
        if expect.new:
            if item is not None:
                raise mr.ConditionFailed("exists")
        elif item is None or item.get("metadata_updated_at") != expect.updated_at:
            raise mr.ConditionFailed("changed")

    def upload_object(self, key: str, blob: bytes) -> None:
        self.uploaded.append(key)

    def delete_object(self, key: str) -> None:
        self.deleted_objects.append(key)

    def get_item(self, table_name: str, name: str):
        item = self.items.get((table_name, name))
        return copy.deepcopy(item) if item else None

    def query_table(self, table_name: str):
        return [
            copy.deepcopy(i) for (t, _n), i in self.items.items() if t == table_name
        ]

    def put_item(self, item, expect=None) -> None:
        if self.before_write:
            hook, self.before_write = self.before_write, None
            hook()
        key = (item["table_name"], item["name"])
        self._check(key, expect)
        assert not any(
            isinstance(v, float) for v in _walk(item)
        ), "floats reach DynamoDB"
        self.items[key] = copy.deepcopy(
            {k: v for k, v in item.items() if v is not None}
        )

    def update_attrs(self, table_name, name, set_attrs, remove_attrs=(), expect=None):
        if self.before_write:
            hook, self.before_write = self.before_write, None
            hook()
        key = (table_name, name)
        item = self.items.get(key)
        if item is None or item.get("deleted"):
            raise mr.ConditionFailed("gone")
        self._check(key, expect)
        item.update(copy.deepcopy(set_attrs))
        for attr in remove_attrs:
            item.pop(attr, None)


def _walk(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)
    else:
        yield value


def row(name="TESLA 4680", metadata=REPO_META, slug="tesla-4680") -> dict[str, Any]:
    return {
        "name": name,
        "object": b"blob",
        "form_factor": "cylindrical",
        "internal_construction": "wound",
        "chemistry": "Li/Li+",
        "date_created": "2026-10-14 16:00:00",
        "version": "1.3.3",
        "metadata": metadata_json(metadata) if metadata is not None else None,
        "slug": slug,
    }


def upload(writer, r, mode="keep", metadata_only=False, carry_from=None, dry_run=False):
    sync = mr.TeardownMetadataSync(writer, mode, carry_from=carry_from)
    return mr.migrate_single_record(
        r,
        "teardowns",
        writer,
        dry_run=dry_run,
        quiet=True,
        teardown_sync=sync,
        metadata_only=metadata_only,
    )


def stored(writer, name="TESLA 4680") -> dict[str, Any]:
    return writer.items[("teardowns", name)]


def test_a_first_upload_seeds_metadata_and_slug() -> None:
    writer = FakeWriter()
    upload(writer, row())
    item = stored(writer)
    assert item["metadata"] == REPO_META
    assert item["slug"] == "tesla-4680"
    assert item["slug_aliases"] == []
    assert item["metadata_updated_by"] == mr.UPLOAD_EDITOR
    assert item["visibility"] == "public"
    assert "object" not in item and item["s3_key"].startswith("teardowns/TESLA 4680/")


def test_a_keep_upload_preserves_admin_edits() -> None:
    writer = FakeWriter()
    writer.items[("teardowns", "TESLA 4680")] = {
        "table_name": "teardowns",
        **copy.deepcopy(EDITED),
        "s3_key": "old",
    }
    upload(writer, row(metadata={"description": "repo changed"}))
    item = stored(writer)
    assert item["metadata"] == {"description": "edited in the app"}
    assert item["slug"] == "tesla-4680-2022"
    assert item["s3_key"] != "old"  # the cell itself was re-uploaded


def test_an_override_upload_replaces_admin_edits() -> None:
    writer = FakeWriter()
    writer.items[("teardowns", "TESLA 4680")] = {
        "table_name": "teardowns",
        **copy.deepcopy(EDITED),
    }
    upload(writer, row(), mode="override")
    item = stored(writer)
    assert item["metadata"] == REPO_META
    assert (item["slug"], item["slug_aliases"]) == ("tesla-4680", ["tesla-4680-2022"])


def test_a_concurrent_admin_edit_is_not_lost() -> None:
    writer = FakeWriter()
    writer.items[("teardowns", "TESLA 4680")] = {
        "table_name": "teardowns",
        "name": "TESLA 4680",
    }

    def admin_edits() -> None:
        writer.items[("teardowns", "TESLA 4680")].update(
            metadata={"description": "admin, mid-upload"},
            metadata_updated_at="2026-10-21T11:59:59+00:00",
            slug="tesla",
        )

    writer.before_write = admin_edits
    upload(writer, row())
    item = stored(writer)
    assert item["metadata"] == {"description": "admin, mid-upload"}  # re-read and kept
    assert item["slug"] == "tesla"


def test_metadata_only_touches_nothing_but_the_metadata() -> None:
    writer = FakeWriter()
    writer.items[("teardowns", "TESLA 4680")] = {
        "table_name": "teardowns",
        "name": "TESLA 4680",
        "s3_key": "keep-me",
        "version": "1.3.3",
    }
    upload(writer, row(), metadata_only=True)
    item = stored(writer)
    assert writer.uploaded == []
    assert item["s3_key"] == "keep-me"
    assert item["metadata"] == REPO_META
    assert item["slug"] == "tesla-4680"


def test_metadata_only_needs_an_uploaded_teardown() -> None:
    with pytest.raises(ValueError):
        upload(FakeWriter(), row(), metadata_only=True)


def test_carry_from_moves_slug_aliases_and_metadata() -> None:
    writer = FakeWriter()
    writer.items[("teardowns", "Tesla 4680 (old)")] = {
        "table_name": "teardowns",
        **copy.deepcopy(EDITED),
        "name": "Tesla 4680 (old)",
    }
    upload(writer, row(), carry_from="Tesla 4680 (old)")
    new = stored(writer)
    assert new["slug"] == "tesla-4680-2022"
    assert new["slug_aliases"] == ["tesla-4680"]
    assert new["metadata"] == {"description": "edited in the app"}
    old = stored(writer, "Tesla 4680 (old)")
    assert "slug" not in old and "slug_aliases" not in old  # released


def test_seeded_slugs_avoid_each_other_within_a_batch() -> None:
    writer = FakeWriter()
    sync = mr.TeardownMetadataSync(writer, "keep")
    for name in ("Cell A", "Cell-A"):
        mr.migrate_single_record(
            row(name=name, slug="cell-a"),
            "teardowns",
            writer,
            quiet=True,
            teardown_sync=sync,
        )
    assert stored(writer, "Cell A")["slug"] == "cell-a"
    assert stored(writer, "Cell-A")["slug"] == "cell-a-2"


def test_a_dry_run_writes_nothing() -> None:
    writer = FakeWriter()
    summary = upload(writer, row(), dry_run=True)
    assert writer.items == {} and writer.uploaded == []
    assert "seeded" in summary


def test_decimal_round_trip() -> None:
    assert mr.to_dynamo({"year": 2022, "x": 1.5}) == {"year": 2022, "x": Decimal("1.5")}
    assert mr.from_dynamo({"year": Decimal("2022")}) == {"year": 2022}


# -- sync_metadata against a throwaway SQLite ------------------------------


def test_sync_metadata_updates_only_the_metadata_columns(tmp_path: Path) -> None:
    db = tmp_path / "database.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE teardowns (name TEXT, object TEXT, date_created TEXT)")
    conn.execute("INSERT INTO teardowns VALUES ('TESLA 4680', 'blob', '2026-10-14')")
    conn.commit()
    conn.close()

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "tesla.py").write_text(
        "METADATA = {'model': '4680'}\nSLUG = None\n"
        "table_name = 'teardowns'\ncell_name = 'TESLA 4680'\n"
    )
    args = ["--sqlite-path", str(db), "--scripts-dir", str(scripts)]
    assert sync_metadata.main(args + ["--check"]) == 1
    assert sync_metadata.main(args) == 0
    assert sync_metadata.main(args + ["--check"]) == 0

    conn = sqlite3.connect(db)
    name, obj, date, meta, slug = conn.execute("SELECT * FROM teardowns").fetchone()
    conn.close()
    assert (obj, date) == ("blob", "2026-10-14")
    assert json.loads(meta) == {"model": "4680"} and slug == "tesla-4680"


def test_sync_metadata_reports_duplicate_slugs(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for i in (1, 2):
        (scripts / f"c{i}.py").write_text(
            f"METADATA = {{}}\nSLUG = 'same'\ntable_name = 'teardowns'\ncell_name = 'C{i}'\n"
        )
    with pytest.raises(MetadataError):
        sync_metadata.read_scripts(scripts)
