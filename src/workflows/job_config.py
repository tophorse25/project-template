from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RedditCrawlJob:
    product: str
    queries: list[str]
    sort: str = "relevance"
    limit_per_query: int = 20
    output_path: str = "data/raw/reddit_browser_posts.jsonl"
    report_path: str = "reports/reddit-product-report.md"


def load_reddit_crawl_job(config_path: str) -> RedditCrawlJob:
    path = Path(config_path)

    with path.open("r", encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)

    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("Config must include a non-empty 'queries' list.")

    product = data.get("product")
    if not isinstance(product, str) or not product.strip():
        raise ValueError("Config must include a non-empty 'product' string.")

    return RedditCrawlJob(
        product=product,
        queries=[str(query) for query in queries],
        sort=str(data.get("sort", "relevance")),
        limit_per_query=int(data.get("limit_per_query", 20)),
        output_path=str(data.get("output_path", "data/raw/reddit_browser_posts.jsonl")),
        report_path=str(data.get("report_path", "reports/reddit-product-report.md")),
    )
