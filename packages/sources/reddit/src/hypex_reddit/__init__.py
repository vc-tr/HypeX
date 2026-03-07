"""HypeX Reddit source plugin."""

from hypex_reddit.fetcher import RedditPost, get_fetcher
from hypex_reddit.aggregator import MetricRow, aggregate_posts

__all__ = [
    "RedditPost",
    "MetricRow",
    "get_fetcher",
    "aggregate_posts",
]
