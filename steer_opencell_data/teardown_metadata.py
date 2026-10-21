# SPDX-FileCopyrightText: 2024-2026 Stanford University
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Teardown metadata and URL slugs.

Each teardown script in ``cell_teardowns/`` defines a ``METADATA`` dict (shown
in OpenCell's info modal for the cell) and an optional ``SLUG`` (the cell's
URL: ``/cell-loader/teardowns/<slug>``; ``None`` derives it from the name).
The script stores both in the ``teardowns`` table's ``metadata`` (JSON text)
and ``slug`` columns, and ``cli/migrate_record.py`` uploads them — keeping or
overriding what admins have edited in the app (``--metadata keep|override``).

METADATA fields (all optional; ``None`` or ``""`` means "not given"):

=================  ==============================================================
``description``    free text, up to 2000 characters (line breaks are kept)
``manufacturer``   up to 120 characters
``model``          up to 120 characters
``year``           release year, an int from 1900 to 2100
``source_type``    one of :data:`SOURCE_TYPES`
``performed_by``   who did the teardown, up to 120 characters
``teardown_date``  free text such as ``"March 2025"``, up to 120 characters
``citation``       up to 1000 characters
``notes``          free text, up to 2000 characters
``links``          up to 10 ``{"label", "url", "kind"}``; http(s) URLs only;
                   ``kind`` is one of :data:`LINK_KINDS` (default ``"other"``)
=================  ==============================================================

The same rules are enforced by the OpenCell data API (steer-data-infrastructure
``lambda/functions/utils/teardowns.py``) and the app's metadata editor; keep
the three in step.
"""

from __future__ import annotations

import ast
import json
import re
import unicodedata
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

TEARDOWN_TABLE = "teardowns"

# SQLite columns the teardown scripts add to the ``teardowns`` table.
TEARDOWN_COLUMNS = {"metadata": "TEXT", "slug": "TEXT"}

SLUG_MAX_LENGTH = 80
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SOURCE_TYPES = frozenset(
    {"in_house_teardown", "literature", "partner", "vendor_datasheet", "other"}
)
LINK_KINDS = frozenset({"glimpse", "drive", "paper", "datasheet", "other"})

TEXT_LIMITS = {
    "description": 2000,
    "manufacturer": 120,
    "model": 120,
    "performed_by": 120,
    "teardown_date": 120,
    "citation": 1000,
    "notes": 2000,
}
YEAR_RANGE = (1900, 2100)
MAX_LINKS = 10
LINK_LABEL_MAX = 80
LINK_URL_MAX = 2048

METADATA_FIELDS = frozenset(TEXT_LIMITS) | {"year", "source_type", "links"}

_CONTROL = re.compile(r"[\x00-\x1f\x7f\s]")


class MetadataError(ValueError):
    """A METADATA dict or SLUG breaks a rule."""


# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    """``"TESLA 4680"`` → ``"tesla-4680"`` (ASCII, lowercase, hyphens)."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug[:SLUG_MAX_LENGTH].rstrip("-") or "teardown"


def is_valid_slug(slug: Any) -> bool:
    return (
        isinstance(slug, str)
        and 0 < len(slug) <= SLUG_MAX_LENGTH
        and SLUG_RE.match(slug) is not None
    )


def unique_slug(base: str, taken: set[str] | dict[str, Any]) -> str:
    """``base``, or ``base-2``, ``base-3`` … — the first not in ``taken``."""
    if base not in taken:
        return base
    n = 2
    while True:
        suffix = f"-{n}"
        candidate = base[: SLUG_MAX_LENGTH - len(suffix)].rstrip("-") + suffix
        if candidate not in taken:
            return candidate
        n += 1


def next_slugs(
    current: str | None, aliases: list[str], requested: str
) -> tuple[str, list[str]]:
    """The ``(slug, aliases)`` after changing ``current`` to ``requested``.

    The old slug becomes an alias (links to it keep redirecting); a
    requested slug that was one of the item's own aliases is reclaimed.
    """
    kept = [a for a in aliases if a != requested]
    if current and current != requested and current not in kept:
        kept.append(current)
    return requested, kept


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_url(url: Any, where: str) -> str:
    if not isinstance(url, str) or not url:
        raise MetadataError(f"{where}: url is required")
    if len(url) > LINK_URL_MAX:
        raise MetadataError(f"{where}: url is longer than {LINK_URL_MAX} characters")
    if _CONTROL.search(url):
        raise MetadataError(
            f"{where}: url must not contain spaces or control characters"
        )
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"}:
        raise MetadataError(f"{where}: url must start with http:// or https://")
    if not parts.netloc or not parts.hostname:
        raise MetadataError(f"{where}: url has no host")
    return url


def _validate_links(links: Any) -> list[dict[str, str]]:
    if not isinstance(links, list):
        raise MetadataError("links must be a list")
    if len(links) > MAX_LINKS:
        raise MetadataError(f"at most {MAX_LINKS} links")
    cleaned = []
    for i, link in enumerate(links, start=1):
        where = f"link {i}"
        if not isinstance(link, dict):
            raise MetadataError(f"{where} must be a dict")
        unknown = set(link) - {"label", "url", "kind"}
        if unknown:
            raise MetadataError(f"{where}: unknown field(s) {sorted(unknown)}")
        label = link.get("label")
        if not isinstance(label, str) or not label.strip():
            raise MetadataError(f"{where}: label is required")
        label = label.strip()
        if len(label) > LINK_LABEL_MAX:
            raise MetadataError(
                f"{where}: label is longer than {LINK_LABEL_MAX} characters"
            )
        kind = link.get("kind") or "other"
        if kind not in LINK_KINDS:
            raise MetadataError(f"{where}: kind must be one of {sorted(LINK_KINDS)}")
        url = _validate_url(link.get("url"), where)
        cleaned.append({"label": label, "url": url, "kind": kind})
    return cleaned


def validate_metadata(metadata: Any) -> dict[str, Any]:
    """Return the cleaned metadata (stripped, empties dropped) or raise."""
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise MetadataError("METADATA must be a dict")
    unknown = set(metadata) - METADATA_FIELDS
    if unknown:
        raise MetadataError(f"unknown METADATA field(s) {sorted(unknown)}")

    cleaned: dict[str, Any] = {}
    for field, limit in TEXT_LIMITS.items():
        value = metadata.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise MetadataError(f"{field} must be text")
        value = value.strip()
        if len(value) > limit:
            raise MetadataError(f"{field} is longer than {limit} characters")
        if value:
            cleaned[field] = value

    year = metadata.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            raise MetadataError("year must be a whole number")
        if not YEAR_RANGE[0] <= year <= YEAR_RANGE[1]:
            raise MetadataError(
                f"year must be between {YEAR_RANGE[0]} and {YEAR_RANGE[1]}"
            )
        cleaned["year"] = year

    source_type = metadata.get("source_type")
    if source_type is not None:
        if source_type not in SOURCE_TYPES:
            raise MetadataError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
        cleaned["source_type"] = source_type

    links = metadata.get("links")
    if links is not None:
        cleaned_links = _validate_links(links)
        if cleaned_links:
            cleaned["links"] = cleaned_links

    return cleaned


def validate_slug(slug: Any) -> str | None:
    if slug is None:
        return None
    if not is_valid_slug(slug):
        raise MetadataError(
            f"SLUG {slug!r} must be 1-80 lowercase letters, digits and single "
            "hyphens (e.g. 'tesla-4680')"
        )
    return slug


# ---------------------------------------------------------------------------
# SQLite columns
# ---------------------------------------------------------------------------


def teardown_columns(
    metadata: dict[str, Any] | None, slug: str | None, cell_name: str
) -> dict[str, list[str]]:
    """The ``metadata`` / ``slug`` DataFrame columns for a script's insert."""
    return {
        "metadata": [metadata_json(metadata)],
        "slug": [validate_slug(slug) or slugify(cell_name)],
    }


def metadata_json(metadata: dict[str, Any] | None) -> str:
    """Validated METADATA as the canonical JSON text stored in SQLite."""
    return json.dumps(validate_metadata(metadata), sort_keys=True, ensure_ascii=False)


def parse_metadata_column(value: Any) -> dict[str, Any] | None:
    """The SQLite ``metadata`` column back to a dict (``None`` if absent)."""
    if value is None or value == "":
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise MetadataError("metadata column is not a JSON object")
    return parsed


# ---------------------------------------------------------------------------
# Reading a script's METADATA without running it
# ---------------------------------------------------------------------------

_SCRIPT_NAMES = ("METADATA", "SLUG", "cell_name", "table_name")


def parse_script(path: str | Path) -> dict[str, Any]:
    """Read ``METADATA``, ``SLUG``, ``cell_name`` and ``table_name`` from a
    teardown script without executing it (they must be literals).

    Returns a dict with those keys; a missing assignment is ``None``.
    """
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    found: dict[str, Any] = {name: None for name in _SCRIPT_NAMES}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in _SCRIPT_NAMES:
            try:
                found[target.id] = ast.literal_eval(node.value)
            except ValueError as exc:
                raise MetadataError(
                    f"{path}: {target.id} must be a literal (no variables or calls)"
                ) from exc
    return found


# ---------------------------------------------------------------------------
# Upload: keep or override what admins edited in the app
# ---------------------------------------------------------------------------

METADATA_MODES = ("keep", "override")


@dataclass
class MetadataPlan:
    """What an upload writes for one teardown's metadata attributes."""

    attrs: dict[str, Any]
    summary: str
    warnings: list[str] = dataclass_field(default_factory=list)


def slug_index(
    items: list[dict[str, Any]], exclude: set[str] | None = None
) -> dict[str, str]:
    """Map the slugs and aliases of live ``items`` to their names.

    Items named in ``exclude`` (the one being written, and a ``--carry-from``
    source) are left out; soft-deleted items never reserve a slug.
    """
    exclude = exclude or set()
    index: dict[str, str] = {}
    for item in items:
        name = item.get("name")
        if name is None or name in exclude or item.get("deleted"):
            continue
        for slug in [item.get("slug"), *(item.get("slug_aliases") or [])]:
            if isinstance(slug, str) and slug:
                index[slug] = name
    return index


def merge_metadata(
    *,
    name: str,
    existing: dict[str, Any] | None,
    repo_metadata: dict[str, Any] | None,
    repo_slug: str | None,
    mode: str,
    taken: dict[str, str],
    now: str,
    editor: str,
) -> MetadataPlan:
    """Decide the metadata attributes to write for teardown ``name``.

    ``existing`` is the teardown's current DynamoDB item (or, with
    ``--carry-from``, the item being renamed), ``None`` when new.
    ``repo_metadata`` / ``repo_slug`` come from the SQLite row (``None`` when
    the row predates the columns). ``taken`` maps the slugs and aliases of
    every *other* live teardown to its name.

    * ``keep`` — anything already on the item stays (admins' edits win); the
      repo only seeds what is missing.
    * ``override`` — the repo's metadata and slug replace the item's; a
      changed slug keeps the old one as an alias. A slug another teardown
      uses is an error.
    """
    if mode not in METADATA_MODES:
        raise ValueError(f"mode must be one of {METADATA_MODES}")

    existing = existing or {}
    warnings: list[str] = []
    attrs: dict[str, Any] = {}
    has_db_metadata = isinstance(existing.get("metadata"), dict)
    db_slug = existing.get("slug") if isinstance(existing.get("slug"), str) else None
    db_aliases = [a for a in (existing.get("slug_aliases") or []) if isinstance(a, str)]

    def carry_audit() -> None:
        for attr in ("metadata_updated_at", "metadata_updated_by"):
            if existing.get(attr) is not None:
                attrs[attr] = existing[attr]

    def stamp() -> None:
        attrs["metadata_updated_at"] = now
        attrs["metadata_updated_by"] = editor

    if mode == "keep":
        if has_db_metadata:
            attrs["metadata"] = existing["metadata"]
            carry_audit()
            meta_summary = "metadata kept"
        elif repo_metadata is not None:
            attrs["metadata"] = validate_metadata(repo_metadata)
            stamp()
            meta_summary = "metadata seeded from repo"
        else:
            meta_summary = "no metadata"

        if db_slug:
            slug, aliases = db_slug, db_aliases
            slug_summary = f"slug '{slug}' kept"
        else:
            base = repo_slug or slugify(name)
            slug = unique_slug(base, taken)
            if slug != base:
                warnings.append(
                    f"slug '{base}' is used by '{taken[base]}'; using '{slug}'"
                )
            aliases = db_aliases
            slug_summary = f"slug '{slug}' seeded"
    else:  # override
        if repo_metadata is not None:
            attrs["metadata"] = validate_metadata(repo_metadata)
            stamp()
            meta_summary = "metadata overridden from repo"
        elif has_db_metadata:
            attrs["metadata"] = existing["metadata"]
            carry_audit()
            warnings.append("the repo has no METADATA for this cell; keeping the DB's")
            meta_summary = "metadata kept (none in repo)"
        else:
            meta_summary = "no metadata"

        requested = repo_slug or db_slug or slugify(name)
        if requested in taken:
            raise MetadataError(
                f"slug '{requested}' is already used by teardown '{taken[requested]}'"
            )
        slug, aliases = next_slugs(db_slug, db_aliases, requested)
        if db_slug and db_slug != slug:
            slug_summary = f"slug '{db_slug}' -> '{slug}' (old kept as alias)"
        else:
            slug_summary = f"slug '{slug}'"

    attrs["slug"] = slug
    attrs["slug_aliases"] = aliases
    return MetadataPlan(
        attrs=attrs, summary=f"{meta_summary}; {slug_summary}", warnings=warnings
    )
