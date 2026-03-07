"""Unit tests for the title resolver."""

import pytest
from hypex_core.types import Title, AliasEntry
from hypex_core.resolver import resolve_mention


@pytest.fixture
def sample_titles() -> list[Title]:
    return [
        Title(
            canonical_id="one-piece",
            canonical_name="One Piece",
            medium="manga",
            language="ja",
            aliases=["OP", "ワンピース"],
        ),
        Title(
            canonical_id="solo-leveling",
            canonical_name="Solo Leveling",
            medium="manhwa",
            language="ko",
            aliases=["나 혼자만 레벨업", "Only I Level Up"],
        ),
        Title(
            canonical_id="chainsaw-man",
            canonical_name="Chainsaw Man",
            medium="manga",
            language="ja",
            aliases=["CSM", "チェンソーマン"],
        ),
        Title(
            canonical_id="tower-of-god",
            canonical_name="Tower of God",
            medium="webtoon",
            language="ko",
            aliases=["TOG", "신의 탑"],
        ),
        Title(
            canonical_id="demon-slayer",
            canonical_name="Demon Slayer: Kimetsu no Yaiba",
            medium="manga",
            language="ja",
            aliases=["Kimetsu no Yaiba", "鬼滅の刃"],
        ),
    ]


@pytest.fixture
def sample_aliases() -> list[AliasEntry]:
    return [
        AliasEntry(alias="OP", canonical_id="one-piece"),
        AliasEntry(alias="ワンピース", canonical_id="one-piece"),
        AliasEntry(alias="CSM", canonical_id="chainsaw-man"),
        AliasEntry(alias="TOG", canonical_id="tower-of-god"),
    ]


def test_exact_alias_match(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Exact alias should return score 1.0 and match_type exact_alias."""
    r = resolve_mention("OP", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"
    assert r[0].score == 1.0
    assert r[0].match_type == "exact_alias"


def test_exact_canonical_name(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Exact canonical name match should return normalized match."""
    r = resolve_mention("One Piece", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"
    assert r[0].score == 1.0


def test_case_insensitive(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Matching should be case-insensitive."""
    r = resolve_mention("one piece", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"


def test_whitespace_normalized(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Extra whitespace should be normalized."""
    r = resolve_mention("  One   Piece  ", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"


def test_fuzzy_typo(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Fuzzy match should catch typos."""
    r = resolve_mention("One Pice", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"
    assert r[0].match_type in ("fuzzy", "normalized")


def test_alias_from_title(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Alias stored in title.aliases should resolve."""
    r = resolve_mention("Only I Level Up", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "solo-leveling"


def test_empty_input(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Empty or whitespace-only input should return empty list."""
    assert resolve_mention("", sample_titles, sample_aliases) == []
    assert resolve_mention("   ", sample_titles, sample_aliases) == []


def test_no_match(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Unrelated text should return empty or low-score candidates."""
    r = resolve_mention("xyz nonexistent title 123", sample_titles, sample_aliases)
    # May return token_overlap for partial matches; ensure no false exact matches
    for c in r:
        assert c.score < 1.0 or c.match_type != "exact_alias"


def test_multiple_candidates(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Ambiguous query may return multiple candidates sorted by score."""
    r = resolve_mention("Tower", sample_titles, sample_aliases)
    # Tower of God may match
    ids = [c.canonical_id for c in r]
    assert "tower-of-god" in ids or len(r) == 0


def test_solo_leveling_variants(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Solo Leveling should match various phrasings."""
    for q in ["Solo Leveling", "solo leveling", "Solo  Leveling"]:
        r = resolve_mention(q, sample_titles, sample_aliases)
        assert len(r) >= 1
        assert r[0].canonical_id == "solo-leveling"


def test_chainsaw_man_abbrev(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """CSM abbreviation should resolve to Chainsaw Man."""
    r = resolve_mention("CSM", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "chainsaw-man"


def test_demon_slayer_partial(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Partial match 'Demon Slayer' should match full title (fuzzy/partial_ratio)."""
    r = resolve_mention("Demon Slayer", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "demon-slayer"


def test_results_sorted_by_score(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Results should be sorted by score descending."""
    r = resolve_mention("OP", sample_titles, sample_aliases)
    scores = [c.score for c in r]
    assert scores == sorted(scores, reverse=True)


def test_japanese_alias_match(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Japanese alias ワンピース should resolve to One Piece."""
    r = resolve_mention("ワンピース", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "one-piece"
    assert r[0].score == 1.0


def test_korean_alias_match(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Korean alias should resolve to Solo Leveling."""
    r = resolve_mention("나 혼자만 레벨업", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "solo-leveling"


def test_japanese_alias_chainsaw(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Japanese alias チェンソーマン should resolve to Chainsaw Man."""
    r = resolve_mention("チェンソーマン", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "chainsaw-man"


def test_korean_tower_alias(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Korean alias 신의 탑 should resolve to Tower of God."""
    r = resolve_mention("신의 탑", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "tower-of-god"


def test_kimetsu_no_yaiba_alias(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Kimetsu no Yaiba alias should resolve to Demon Slayer."""
    r = resolve_mention("Kimetsu no Yaiba", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "demon-slayer"


def test_tog_abbreviation(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """TOG abbreviation should resolve to Tower of God."""
    r = resolve_mention("TOG", sample_titles, sample_aliases)
    assert len(r) >= 1
    assert r[0].canonical_id == "tower-of-god"


def test_title_with_no_matching_text(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Completely unrelated input returns no high-confidence matches."""
    r = resolve_mention("banana pancake recipe", sample_titles, sample_aliases)
    for c in r:
        assert c.score < 0.8


def test_single_character_input(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Very short input should not crash and returns low/no matches."""
    r = resolve_mention("a", sample_titles, sample_aliases)
    # Should not raise; may or may not return results
    assert isinstance(r, list)


def test_resolve_returns_list(sample_titles: list[Title], sample_aliases: list[AliasEntry]) -> None:
    """Resolve should always return a list."""
    r = resolve_mention("anything", sample_titles, sample_aliases)
    assert isinstance(r, list)
    for c in r:
        assert hasattr(c, "canonical_id")
        assert hasattr(c, "score")
        assert hasattr(c, "match_type")
