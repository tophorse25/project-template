from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class QueryRunResult:
    query: str
    status: str
    records_collected: int
    started_at: str
    completed_at: str
    error: str | None = None


@dataclass(frozen=True)
class CrawlRunLog:
    product: str
    output_path: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    total_records: int
    started_at: str
    completed_at: str
    query_results: list[QueryRunResult] = field(default_factory=list)


def default_crawl_log_path(output_path: str, completed_at: str) -> str:
    safe_time = completed_at.replace(":", "").replace("+", "Z")
    stem = Path(output_path).stem or "crawl"
    return str(Path("log") / "crawl-runs" / f"{stem}-{safe_time}.json")


def write_crawl_log(run_log: CrawlRunLog, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = asdict(run_log)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
