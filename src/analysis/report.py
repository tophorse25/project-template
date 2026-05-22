from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.signals import (
    detect_demand_signals,
    detect_location_clues,
    detect_pain_points,
)


def read_jsonl(input_path: str) -> list[dict[str, Any]]:
    path = Path(input_path)
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))

    return records


def normalize_reddit_record(record: dict[str, Any]) -> dict[str, Any]:
    title = record.get("title") or record.get("post_title") or ""
    body_text = record.get("text") or record.get("comment_text") or record.get("post_text") or ""
    subreddit = record.get("subreddit", "")
    url = record.get("url") or record.get("post_url") or ""
    combined_text = " ".join(part for part in [title, body_text, subreddit, url] if part)

    source_type = "comment" if record.get("comment_id") or "/comment/" in url else "post"
    source = record.get("source")
    if not source:
        source = "api" if any(key.startswith("post_") or key.startswith("comment_") for key in record) else "browser"

    normalized = {
        "platform": record.get("platform", "reddit"),
        "query": record.get("query", ""),
        "source": source,
        "source_type": source_type,
        "subreddit": subreddit,
        "title": title,
        "text": body_text,
        "url": url,
        "score": record.get("score") or record.get("post_score") or 0,
        "comment_count": record.get("comment_count") or record.get("post_num_comments") or 0,
        "created_utc": record.get("created_utc"),
        "location_clues": detect_location_clues(combined_text),
        "demand_signals": detect_demand_signals(combined_text),
        "pain_points": detect_pain_points(combined_text),
    }

    return normalized


def normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_reddit_record(record) for record in records]


def count_labels(records: list[dict[str, Any]], field: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get(field, []))
    return counter


def top_records(records: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            len(record.get("demand_signals", [])),
            len(record.get("pain_points", [])),
            int(record.get("score") or 0),
            int(record.get("comment_count") or 0),
        ),
        reverse=True,
    )[:limit]


def demand_strength(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No data"

    signal_count = sum(len(record.get("demand_signals", [])) for record in records)
    ratio = signal_count / len(records)

    if ratio >= 1.0:
        return "High"
    if ratio >= 0.4:
        return "Medium"
    return "Low"


def format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "- None detected"
    return "\n".join(f"- {label}: {count}" for label, count in counter.most_common())


def generate_markdown_report(
    records: list[dict[str, Any]],
    product: str,
    evidence_limit: int = 10,
) -> str:
    normalized_records = normalize_records(records)
    demand_counter = count_labels(normalized_records, "demand_signals")
    pain_counter = count_labels(normalized_records, "pain_points")
    location_counter = count_labels(normalized_records, "location_clues")
    evidence = top_records(normalized_records, limit=evidence_limit)

    lines = [
        f"# Product Demand Report: {product}",
        "",
        "## Summary",
        "",
        f"- Total Reddit records reviewed: {len(normalized_records)}",
        f"- Estimated demand strength: {demand_strength(normalized_records)}",
        f"- Records with demand signals: {sum(1 for record in normalized_records if record['demand_signals'])}",
        f"- Records with pain points: {sum(1 for record in normalized_records if record['pain_points'])}",
        f"- Records with location clues: {sum(1 for record in normalized_records if record['location_clues'])}",
        "",
        "## Demand Signals",
        "",
        format_counter(demand_counter),
        "",
        "## Pain Points",
        "",
        format_counter(pain_counter),
        "",
        "## Location Clues",
        "",
        format_counter(location_counter),
        "",
        "## Merchant Takeaway",
        "",
        merchant_takeaway(demand_counter, pain_counter, location_counter),
        "",
        "## Evidence",
        "",
    ]

    if not evidence:
        lines.append("- No evidence records available.")
    else:
        for index, record in enumerate(evidence, start=1):
            labels = ", ".join(record["demand_signals"] + record["pain_points"] + record["location_clues"])
            if not labels:
                labels = "no labels"
            title = record["title"] or record["text"][:100] or "Untitled record"
            url = record["url"] or "No URL"
            lines.append(f"{index}. [{title}]({url})")
            lines.append(f"   - Labels: {labels}")
            if record["subreddit"]:
                lines.append(f"   - Subreddit: r/{record['subreddit']}")

    lines.append("")
    return "\n".join(lines)


def merchant_takeaway(
    demand_counter: Counter[str],
    pain_counter: Counter[str],
    location_counter: Counter[str],
) -> str:
    if not demand_counter:
        return "Current sample has weak demand evidence. Collect more records before making stocking decisions."

    strongest_demand = demand_counter.most_common(1)[0][0]
    takeaway = [
        f"- Main demand signal: `{strongest_demand}`.",
    ]

    if pain_counter:
        strongest_pain = pain_counter.most_common(1)[0][0]
        takeaway.append(f"- Product positioning opportunity: address `{strongest_pain}` in product selection or listing copy.")
    else:
        takeaway.append("- No repeated product pain point was detected in this sample.")

    if location_counter:
        strongest_location = location_counter.most_common(1)[0][0]
        takeaway.append(f"- Region to investigate first: `{strongest_location}`.")
    else:
        takeaway.append("- Location demand is unclear. Future collection should prioritize comments/posts with region clues.")

    takeaway.append("- Treat this as directional evidence, not an inventory forecast, until the crawl size is increased.")

    return "\n".join(takeaway)


def write_report(markdown: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
