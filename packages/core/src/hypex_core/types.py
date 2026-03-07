"""HypeX core types."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Title:
    """Canonical title in the registry."""

    canonical_id: str
    canonical_name: str
    medium: str  # manga | manhwa | manhua | webtoon
    language: str
    aliases: list[str]
    platform: Optional[str] = None
    year: Optional[int] = None


@dataclass
class ResolveCandidate:
    """Result of resolving a mention to a candidate title."""

    canonical_id: str
    score: float
    match_type: str  # exact_alias | normalized | fuzzy | token_overlap


@dataclass
class AliasEntry:
    """Alias mapping for resolution."""

    alias: str
    canonical_id: str
