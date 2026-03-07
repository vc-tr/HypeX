"""Unit tests for slugify and merge_aliases."""

import pytest
from hypex_core.utils import merge_aliases, slugify


def test_slugify_basic() -> None:
    assert slugify("One Piece") == "one-piece"
    assert slugify("Solo Leveling") == "solo-leveling"


def test_slugify_special_chars() -> None:
    assert slugify("Spy x Family") == "spy-x-family"
    assert slugify("Demon Slayer: Kimetsu no Yaiba") == "demon-slayer-kimetsu-no-yaiba"


def test_slugify_empty() -> None:
    assert slugify("") == ""
    assert slugify("   ") == ""


def test_slugify_preserves_hyphens() -> None:
    assert slugify("One-Punch Man") == "one-punch-man"


def test_merge_aliases_dedup() -> None:
    assert merge_aliases(["OP", "OP", "OP"]) == ["OP"]


def test_merge_aliases_multiple_sources() -> None:
    csv_aliases = ["OP", "ワンピース"]
    json_aliases = ["OP", "One Piece"]
    # Result is sorted case-insensitively; OP deduped
    got = merge_aliases(csv_aliases, json_aliases)
    assert set(got) == {"OP", "One Piece", "ワンピース"}
    assert len(got) == 3


def test_merge_aliases_case_insensitive_dedup() -> None:
    # First occurrence wins; case-insensitive dedup
    assert merge_aliases(["OP"], ["op"]) == ["OP"]


def test_merge_aliases_empty() -> None:
    assert merge_aliases([]) == []
    assert merge_aliases([], []) == []
