"""Utility functions for registry and sync."""

import re


def slugify(text: str) -> str:
    """Generate kebab-case slug from text."""
    if not text or not text.strip():
        return ""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-")


def merge_aliases(*alias_lists: list[str]) -> list[str]:
    """Merge alias lists into unique, sorted list (case-insensitive dedup)."""
    seen: set[str] = set()
    result: list[str] = []
    for lst in alias_lists:
        for a in lst:
            a = (a or "").strip()
            if not a:
                continue
            key = a.lower()
            if key not in seen:
                seen.add(key)
                result.append(a)
    return sorted(result, key=str.lower)
