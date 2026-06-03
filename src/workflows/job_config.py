from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    run_log_path: str | None = None
    # Engine extensions (all optional, backward compatible).
    subreddits: list[str] = field(default_factory=list)
    deep_fetch: bool = False
    deep_fetch_limit: int = 10
    db_path: str = "data/demand_kb.sqlite3"
    html_report_path: str = "reports/reddit-product-report.html"
    dedup_threshold: float = 0.5
    min_evidence_for_validation: int = 4


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
        run_log_path=str(data["run_log_path"]) if data.get("run_log_path") else None,
        subreddits=[str(item) for item in data.get("subreddits", [])],
        deep_fetch=bool(data.get("deep_fetch", False)),
        deep_fetch_limit=int(data.get("deep_fetch_limit", 10)),
        db_path=str(data.get("db_path", "data/demand_kb.sqlite3")),
        html_report_path=str(data.get("html_report_path", "reports/reddit-product-report.html")),
        dedup_threshold=float(data.get("dedup_threshold", 0.5)),
        min_evidence_for_validation=int(data.get("min_evidence_for_validation", 4)),
    )
