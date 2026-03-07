"""Load title registry from CSV and JSON."""

import csv
import json
from pathlib import Path
from typing import Optional

from hypex_core.types import Title, AliasEntry


def _normalize_path(path: Path) -> Path:
    """Resolve path relative to project root if needed."""
    if not path.is_absolute():
        # Assume data/registry is relative to workspace root (HypeX/)
        # __file__ = packages/core/src/hypex_core/loader.py -> 5 levels up
        root = Path(__file__).resolve().parent.parent.parent.parent.parent
        return root / path
    return path


def load_titles_csv(path: Path | str) -> list[Title]:
    """Load titles from CSV. Expected columns: canonical_id, canonical_name, medium, language, aliases, platform, year."""
    path = Path(path) if isinstance(path, str) else path
    path = _normalize_path(path)
    titles: list[Title] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aliases_str = row.get("aliases", "")
            aliases = [a.strip() for a in aliases_str.split("|") if a.strip()]
            year_str = row.get("year", "")
            year = int(year_str) if year_str and year_str.strip().isdigit() else None
            titles.append(
                Title(
                    canonical_id=row.get("canonical_id", "").strip(),
                    canonical_name=row.get("canonical_name", "").strip(),
                    medium=row.get("medium", "manga").strip().lower(),
                    language=row.get("language", "ja").strip(),
                    aliases=aliases,
                    platform=row.get("platform", "").strip() or None,
                    year=year,
                )
            )
    return titles


def load_aliases_json(path: Path | str) -> list[AliasEntry]:
    """Load aliases from JSON. Expected format: { "alias": "canonical_id", ... } or [{"alias":"...","canonical_id":"..."}, ...]."""
    path = Path(path) if isinstance(path, str) else path
    path = _normalize_path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    entries: list[AliasEntry] = []
    if isinstance(data, dict):
        for alias, cid in data.items():
            entries.append(AliasEntry(alias=str(alias).strip(), canonical_id=str(cid).strip()))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                entries.append(
                    AliasEntry(
                        alias=str(item.get("alias", "")).strip(),
                        canonical_id=str(item.get("canonical_id", "")).strip(),
                    )
                )
    return entries


def load_registry(
    titles_path: Path | str = "data/registry/titles.csv",
    aliases_path: Path | str = "data/registry/aliases.json",
) -> tuple[list[Title], list[AliasEntry]]:
    """Load full registry: titles from CSV and aliases from JSON."""
    titles = load_titles_csv(titles_path)
    aliases = load_aliases_json(aliases_path)
    return titles, aliases
