"""Bridge: collector JSONL -> super_crawler inbox JSON.

Closes the loop between the two systems: the Reddit collector executes a search
plan's queries live and writes JSONL; this converts those records into the
Reddit-like JSON array format super_crawler's discovery agent ingests, and drops
the file into its inbox so the always-on agent picks it up on the next cycle.

Usage:
    python src/bridge_to_inbox.py --input data/raw/<crawl>.jsonl \
        --inbox _reference_super_crawler/data/reddit_inbox [--name <file-stem>]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def to_inbox_item(record: dict[str, Any]) -> dict[str, Any] | None:
    url = record.get("url") or record.get("post_url") or ""
    title = record.get("title") or record.get("post_title") or ""
    body = record.get("body") or record.get("text") or record.get("comment_text") or ""
    if not url or not (title or body):
        return None

    subreddit = record.get("subreddit") or ""
    created = record.get("created_utc")
    created_at = (
        datetime.fromtimestamp(float(created), UTC).replace(microsecond=0).isoformat()
        if created
        else datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    return {
        "source_url": url,
        "subreddit": f"r/{subreddit}" if subreddit and not subreddit.startswith("r/") else (subreddit or "unknown"),
        "post_id": record.get("post_id"),
        "comment_id": record.get("comment_id"),
        "title": title,
        "body": body,
        "score": int(record.get("score") or 0),
        "comment_count": int(record.get("comment_count") or 0),
        "created_at": created_at,
        "language": "en",
        "author_metadata_allowed": False,
    }


def convert(input_path: str, inbox_dir: str, name: str | None = None) -> Path:
    records = []
    with Path(input_path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))

    items = [item for item in (to_inbox_item(record) for record in records) if item is not None]
    # Dedupe by source_url; keep the richest (longest body) version of each.
    by_url: dict[str, dict[str, Any]] = {}
    for item in items:
        existing = by_url.get(item["source_url"])
        if existing is None or len(item["body"]) > len(existing["body"]):
            by_url[item["source_url"]] = item

    stem = name or (Path(input_path).stem + "_inbox")
    output = Path(inbox_dir) / f"{stem}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(by_url.values()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert collector JSONL into a super_crawler inbox JSON array.")
    parser.add_argument("--input", required=True, help="Collector JSONL file")
    parser.add_argument("--inbox", default="_reference_super_crawler/data/reddit_inbox", help="super_crawler inbox dir")
    parser.add_argument("--name", help="Output file stem (default: input stem + _inbox)")
    args = parser.parse_args()

    output = convert(args.input, args.inbox, args.name)
    count = len(json.loads(output.read_text(encoding="utf-8")))
    print(f"Wrote {count} item(s) to {output}")


if __name__ == "__main__":
    main()
