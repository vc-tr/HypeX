"""Resolve text mentions to canonical titles."""

import re
from typing import Optional

from rapidfuzz import fuzz

from hypex_core.types import Title, ResolveCandidate, AliasEntry


def _normalize(text: str) -> str:
    """Normalize for matching: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokenize(text: str) -> set[str]:
    """Tokenize into words for overlap fallback."""
    return set(re.findall(r"\w+", _normalize(text)))


def _token_overlap_score(a: str, b: str) -> float:
    """Jaccard-like token overlap score."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / max(len(ta), len(tb))


def resolve_mention(
    text: str,
    titles: list[Title],
    aliases: list[AliasEntry],
    fuzzy_threshold: float = 80.0,
    max_candidates: int = 10,
) -> list[ResolveCandidate]:
    """
    Resolve a text mention to candidate titles.
    Matching: exact alias, normalized string, fuzzy (rapidfuzz), token-based overlap.
    """
    if not text or not text.strip():
        return []

    candidates: dict[str, tuple[float, str]] = {}  # canonical_id -> (best_score, match_type)

    def _add(cid: str, score: float, match_type: str):
        if cid in candidates:
            if score > candidates[cid][0]:
                candidates[cid] = (score, match_type)
        else:
            candidates[cid] = (score, match_type)

    normalized = _normalize(text)

    # 1. Exact alias match
    for a in aliases:
        if _normalize(a.alias) == normalized:
            _add(a.canonical_id, 1.0, "exact_alias")

    # 2. Exact canonical name match
    for t in titles:
        if _normalize(t.canonical_name) == normalized:
            _add(t.canonical_id, 1.0, "normalized")

    # 3. Exact alias in titles
    for t in titles:
        for alias in t.aliases:
            if _normalize(alias) == normalized:
                _add(t.canonical_id, 1.0, "exact_alias")

    # 4. Fuzzy match (rapidfuzz) - use ratio and partial_ratio for substring matches
    for t in titles:
        t_norm = _normalize(t.canonical_name)
        score = max(
            fuzz.ratio(normalized, t_norm) / 100.0,
            fuzz.partial_ratio(normalized, t_norm) / 100.0,
        )
        if score >= fuzzy_threshold / 100.0:
            _add(t.canonical_id, score, "fuzzy")
        for alias in t.aliases:
            a_norm = _normalize(alias)
            score = max(
                fuzz.ratio(normalized, a_norm) / 100.0,
                fuzz.partial_ratio(normalized, a_norm) / 100.0,
            )
            if score >= fuzzy_threshold / 100.0:
                _add(t.canonical_id, score, "fuzzy")

    for a in aliases:
        a_norm = _normalize(a.alias)
        score = max(
            fuzz.ratio(normalized, a_norm) / 100.0,
            fuzz.partial_ratio(normalized, a_norm) / 100.0,
        )
        if score >= fuzzy_threshold / 100.0:
            _add(a.canonical_id, score, "fuzzy")

    # 5. Token overlap fallback (when no fuzzy hit)
    for t in titles:
        s = _token_overlap_score(text, t.canonical_name)
        if s >= 0.5 and t.canonical_id not in candidates:
            _add(t.canonical_id, s, "token_overlap")
        for alias in t.aliases:
            s = _token_overlap_score(text, alias)
            if s >= 0.5 and t.canonical_id not in candidates:
                _add(t.canonical_id, s, "token_overlap")

    result = [
        ResolveCandidate(canonical_id=cid, score=score, match_type=match_type)
        for cid, (score, match_type) in candidates.items()
    ]
    result.sort(key=lambda x: (-x.score, x.canonical_id))
    return result[:max_candidates]
