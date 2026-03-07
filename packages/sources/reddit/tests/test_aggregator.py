"""Tests for the Reddit aggregator."""

from datetime import date

from hypex_core.types import AliasEntry, Title
from hypex_reddit.aggregator import MetricRow, aggregate_posts
from hypex_reddit.fetcher import RedditPost


def _make_titles() -> list[Title]:
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
            aliases=["SL", "나 혼자만 레벨업"],
        ),
    ]


def _make_aliases() -> list[AliasEntry]:
    return [
        AliasEntry(alias="OP", canonical_id="one-piece"),
        AliasEntry(alias="SL", canonical_id="solo-leveling"),
    ]


def _make_post(
    id: str = "p1",
    title: str = "One Piece Chapter 1000",
    selftext: str = "",
    subreddit: str = "manga",
    score: int = 100,
    num_comments: int = 50,
) -> RedditPost:
    return RedditPost(
        id=id,
        title=title,
        selftext=selftext,
        subreddit=subreddit,
        score=score,
        num_comments=num_comments,
        created_utc=1700000000.0,
    )


class TestAggregator:
    def test_single_post_match(self):
        """A single matching post should produce 2 metric rows."""
        posts = [_make_post()]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))

        assert len(metrics) == 2
        mentions = [m for m in metrics if m.metric_name == "mentions_count"]
        engagement = [m for m in metrics if m.metric_name == "engagement_score"]
        assert len(mentions) == 1
        assert len(engagement) == 1
        assert mentions[0].value == 1.0
        assert mentions[0].canonical_id == "one-piece"
        # engagement = score + 2 * num_comments = 100 + 2 * 50 = 200
        assert engagement[0].value == 200.0

    def test_no_match(self):
        """Posts with unrecognizable titles produce no metrics."""
        posts = [_make_post(title="Random unrelated cooking recipe")]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))
        assert len(metrics) == 0

    def test_multiple_posts_same_title(self):
        """Multiple posts for the same title should aggregate."""
        posts = [
            _make_post(id="p1", title="One Piece 1000", score=100, num_comments=50),
            _make_post(id="p2", title="One Piece 1001", score=200, num_comments=100),
        ]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))

        mentions = [m for m in metrics if m.metric_name == "mentions_count" and m.canonical_id == "one-piece"]
        engagement = [m for m in metrics if m.metric_name == "engagement_score" and m.canonical_id == "one-piece"]
        assert mentions[0].value == 2.0
        # (100 + 100) + (200 + 200) = 600
        assert engagement[0].value == 600.0

    def test_multiple_titles(self):
        """Posts for different titles produce separate metric rows."""
        posts = [
            _make_post(id="p1", title="One Piece 1000"),
            _make_post(id="p2", title="Solo Leveling chapter 200"),
        ]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))

        cids = {m.canonical_id for m in metrics}
        assert "one-piece" in cids
        assert "solo-leveling" in cids

    def test_below_threshold_ignored(self):
        """Posts below match threshold are ignored."""
        posts = [_make_post(title="I enjoy reading comics about adventures")]
        metrics = aggregate_posts(
            posts, _make_titles(), _make_aliases(), date(2026, 3, 2), threshold=0.95
        )
        # With a very high threshold and vague text, nothing should match
        assert len(metrics) == 0

    def test_confidence_clipped(self):
        """Confidence should be in [0.5, 1.0]."""
        posts = [_make_post()]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))
        for m in metrics:
            assert 0.5 <= m.confidence <= 1.0

    def test_raw_ref_contains_source(self):
        """Raw reference should contain source metadata."""
        posts = [_make_post()]
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), date(2026, 3, 2))
        for m in metrics:
            assert m.raw_ref["source"] == "reddit"
            assert "subreddits" in m.raw_ref
            assert "post_ids" in m.raw_ref

    def test_empty_posts(self):
        """No posts means no metrics."""
        metrics = aggregate_posts([], _make_titles(), _make_aliases(), date(2026, 3, 2))
        assert len(metrics) == 0

    def test_metric_date_matches(self):
        """All metric rows should have the target date."""
        posts = [_make_post()]
        target = date(2026, 3, 2)
        metrics = aggregate_posts(posts, _make_titles(), _make_aliases(), target)
        for m in metrics:
            assert m.metric_date == target
