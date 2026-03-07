"""Aggregate Reddit posts into normalized HypeX metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from hypex_core.types import AliasEntry, Title
from hypex_core.resolver import resolve_mention

from hypex_reddit.fetcher import RedditPost


@dataclass
class MetricRow:
    """A single normalized metric ready for DB insertion."""

    metric_date: date
    canonical_id: str
    metric_name: str
    value: float
    confidence: float
    raw_ref: dict = field(default_factory=dict)


# Minimum resolver score to accept a match
MATCH_THRESHOLD = 0.80


def aggregate_posts(
    posts: list[RedditPost],
    titles: list[Title],
    aliases: list[AliasEntry],
    target_date: date,
    threshold: float = MATCH_THRESHOLD,
) -> list[MetricRow]:
    """Aggregate Reddit posts into per-title daily metrics.

    For each post, resolve its title against the registry. For matches above
    the threshold, accumulate:
      - mentions_count: number of matched posts
      - engagement_score: sum of (score + 2 * num_comments)

    Returns a list of MetricRow objects (two per matched title: one for
    mentions_count, one for engagement_score).
    """
    # Accumulators per canonical_id
    mentions: dict[str, int] = {}
    engagement: dict[str, float] = {}
    confidences: dict[str, list[float]] = {}
    post_ids: dict[str, list[str]] = {}
    subreddits: dict[str, set[str]] = {}

    for post in posts:
        # Resolve post title against registry
        text = post.title
        candidates = resolve_mention(text, titles, aliases)
        if not candidates:
            continue

        top = candidates[0]
        if top.score < threshold:
            continue

        cid = top.canonical_id
        mentions[cid] = mentions.get(cid, 0) + 1
        engagement[cid] = engagement.get(cid, 0.0) + (post.score + 2 * post.num_comments)
        confidences.setdefault(cid, []).append(top.score)
        post_ids.setdefault(cid, []).append(post.id)
        subreddits.setdefault(cid, set()).add(post.subreddit)

    # Build output metric rows
    rows: list[MetricRow] = []
    for cid in mentions:
        # Average confidence, clipped to [0.5, 1.0]
        avg_conf = sum(confidences[cid]) / len(confidences[cid])
        conf = max(0.5, min(1.0, avg_conf))

        raw = {
            "source": "reddit",
            "subreddits": sorted(subreddits[cid]),
            "post_ids": post_ids[cid],
        }

        rows.append(
            MetricRow(
                metric_date=target_date,
                canonical_id=cid,
                metric_name="mentions_count",
                value=float(mentions[cid]),
                confidence=conf,
                raw_ref=raw,
            )
        )
        rows.append(
            MetricRow(
                metric_date=target_date,
                canonical_id=cid,
                metric_name="engagement_score",
                value=engagement[cid],
                confidence=conf,
                raw_ref=raw,
            )
        )

    return rows
