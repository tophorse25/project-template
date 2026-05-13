import os
from dataclasses import asdict, dataclass
from typing import Any

import praw
from dotenv import load_dotenv


@dataclass
class RedditRecord:
    platform: str
    query: str
    subreddit: str
    post_id: str
    post_title: str
    post_text: str
    post_url: str
    post_score: int
    post_num_comments: int
    created_utc: float
    comment_id: str | None
    comment_text: str | None
    comment_score: int | None


class RedditCollector:
    def __init__(self) -> None:
        load_dotenv()

        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )

    def search_subreddit(
        self,
        subreddit_name: str,
        query: str,
        limit: int = 10,
        comment_limit: int = 10,
    ) -> list[dict[str, Any]]:
        subreddit = self.reddit.subreddit(subreddit_name)
        records: list[dict[str, Any]] = []

        for submission in subreddit.search(query, limit=limit, sort="relevance"):
            submission.comments.replace_more(limit=0)

            base = {
                "platform": "reddit",
                "query": query,
                "subreddit": subreddit_name,
                "post_id": submission.id,
                "post_title": submission.title,
                "post_text": submission.selftext or "",
                "post_url": submission.url,
                "post_score": submission.score,
                "post_num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
            }

            comments = submission.comments.list()[:comment_limit]

            if not comments:
                records.append(
                    asdict(
                        RedditRecord(
                            **base,
                            comment_id=None,
                            comment_text=None,
                            comment_score=None,
                        )
                    )
                )
                continue

            for comment in comments:
                records.append(
                    asdict(
                        RedditRecord(
                            **base,
                            comment_id=comment.id,
                            comment_text=comment.body,
                            comment_score=comment.score,
                        )
                    )
                )

        return records