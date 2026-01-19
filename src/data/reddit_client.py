"""Reddit API Client - Social sentiment signals via PRAW."""

import logging
import math
import os
from typing import Any, Dict, List, Optional

import praw

# TODO: Add integration tests for RedditClient once credentials are available.


class RedditClient:
    """Client for Reddit API (PRAW) to fetch ticker mentions and sentiment."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT", "FutureOracle/1.0")

        if not self.client_id or not self.client_secret:
            raise ValueError("REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not found")
        if not self.user_agent:
            raise ValueError("REDDIT_USER_AGENT not found")

        self.logger = logging.getLogger("futureoracle.reddit")
        self._reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
            check_for_async=False,
        )
        self._reddit.read_only = True

    def get_ticker_mentions(
        self, ticker: str, subreddit: str = "wallstreetbets", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search subreddit for ticker mentions."""
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            return []

        query = f'"{normalized_ticker}" OR "${normalized_ticker}"'
        results: List[Dict[str, Any]] = []
        try:
            submissions = self._reddit.subreddit(subreddit).search(
                query, sort="new", limit=limit
            )
            for submission in submissions:
                results.append(
                    {
                        "title": submission.title,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                        "url": submission.url,
                    }
                )
        except Exception as exc:
            self.logger.error("Reddit search failed: %s", exc)
            raise

        return results

    def calculate_sentiment_score(self, mentions: List[Dict[str, Any]]) -> float:
        """
        Calculate a 0-100 sentiment score using upvotes and comment volume.
        """
        if not mentions:
            return 0.0

        total = 0.0
        for mention in mentions:
            score = float(mention.get("score", 0) or 0)
            comments = float(mention.get("num_comments", 0) or 0)
            raw_signal = (score * 1.0) + (comments * 0.5)
            scaled = 50.0 + 50.0 * math.tanh(raw_signal / 50.0)
            total += max(0.0, min(100.0, scaled))

        return total / len(mentions)
