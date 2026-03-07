"""Reddit post fetcher with mock and real PRAW implementations."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Protocol


@dataclass
class RedditPost:
    """A Reddit post with engagement metrics."""

    id: str
    title: str
    selftext: str
    subreddit: str
    score: int
    num_comments: int
    created_utc: float


DEFAULT_SUBREDDITS = [
    "manga",
    "manhwa",
    "manhua",
    "webtoons",
    "SoloLeveling",
    "OnePiece",
    "ChainsawMan",
    "JuJutsuKaisen",
]

# Title names used by mock fetcher to generate realistic posts
_MOCK_TITLE_POOL = [
    "One Piece",
    "Solo Leveling",
    "Chainsaw Man",
    "Jujutsu Kaisen",
    "Tower of God",
    "Demon Slayer: Kimetsu no Yaiba",
    "Naruto",
    "Bleach",
    "Spy x Family",
    "My Hero Academia",
    "Dragon Ball Super",
    "The Beginning After the End",
    "Omniscient Reader's Viewpoint",
    "Lookism",
    "Vinland Saga",
    "Blue Lock",
    "Mashle",
    "Kaiju No. 8",
    "Dandadan",
    "Sakamoto Days",
]

# Realistic post title templates
_POST_TEMPLATES = [
    "[DISC] {title} - Chapter {ch}",
    "{title} Chapter {ch} Discussion",
    "Just finished {title} and WOW",
    "{title} is peak fiction, change my mind",
    "Weekly {title} discussion thread",
    "New {title} chapter was insane!",
    "{title} - anyone else hyped for the next arc?",
    "Unpopular opinion: {title} has the best art",
    "[Art] {title} fanart I drew",
    "My top 10 moments from {title}",
]


class RedditFetcherProtocol(Protocol):
    """Protocol for Reddit post fetchers."""

    def fetch_posts_by_date(self, subreddit: str, target_date: date) -> list[RedditPost]:
        """Fetch posts from a subreddit for a given date."""
        ...


class MockRedditFetcher:
    """Deterministic mock fetcher for development without Reddit API credentials."""

    def fetch_posts_by_date(self, subreddit: str, target_date: date) -> list[RedditPost]:
        """Generate deterministic mock posts for a subreddit on a date."""
        date_str = target_date.isoformat()
        seed = f"{subreddit}:{date_str}"
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)

        # 5-15 posts per subreddit per day
        num_posts = 5 + (h % 11)
        posts: list[RedditPost] = []

        for i in range(num_posts):
            post_seed = f"{seed}:{i}"
            ph = int(hashlib.sha256(post_seed.encode()).hexdigest(), 16)

            # Pick a title from the pool
            title_name = _MOCK_TITLE_POOL[ph % len(_MOCK_TITLE_POOL)]
            template = _POST_TEMPLATES[(ph >> 8) % len(_POST_TEMPLATES)]
            chapter_num = 100 + (ph % 300)
            post_title = template.format(title=title_name, ch=chapter_num)

            # Generate engagement metrics
            score = 10 + (ph % 5000)
            num_comments = 5 + (ph % 500)

            # Generate a timestamp within the target date
            hour = ph % 24
            minute = (ph >> 5) % 60
            ts = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                minute,
                tzinfo=timezone.utc,
            ).timestamp()

            posts.append(
                RedditPost(
                    id=f"mock_{subreddit}_{date_str}_{i}",
                    title=post_title,
                    selftext=f"Discussion about {title_name}.",
                    subreddit=subreddit,
                    score=score,
                    num_comments=num_comments,
                    created_utc=ts,
                )
            )

        return posts


class PrawRedditFetcher:
    """Real Reddit fetcher using PRAW. Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."""

    def __init__(self) -> None:
        import praw

        self._reddit = praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.getenv("REDDIT_USER_AGENT", "HypeX/0.1.0"),
        )

    def fetch_posts_by_date(self, subreddit: str, target_date: date) -> list[RedditPost]:
        """Fetch posts from a subreddit for a given date using PRAW."""
        sub = self._reddit.subreddit(subreddit)

        # Define the date range (midnight to midnight UTC)
        start_ts = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
        ).timestamp()
        end_ts = start_ts + 86400  # +24h

        posts: list[RedditPost] = []
        # Fetch recent posts and filter by date
        for submission in sub.new(limit=1000):
            if submission.created_utc < start_ts:
                break  # Posts are sorted newest first; stop when we pass the date
            if submission.created_utc >= end_ts:
                continue  # Skip posts from after the target date
            posts.append(
                RedditPost(
                    id=submission.id,
                    title=submission.title,
                    selftext=submission.selftext or "",
                    subreddit=subreddit,
                    score=submission.score,
                    num_comments=submission.num_comments,
                    created_utc=submission.created_utc,
                )
            )

        return posts


def get_fetcher() -> RedditFetcherProtocol:
    """Return the appropriate fetcher based on available credentials."""
    if os.getenv("REDDIT_CLIENT_ID"):
        return PrawRedditFetcher()
    return MockRedditFetcher()
