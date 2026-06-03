"""Run the demand-intelligence engine over collected Reddit evidence.

Offline-first: by default it ingests already-collected JSONL (or the bundled sample),
runs one full discovery -> reconcile -> reopen -> research cycle into the persistent
knowledge base, and writes a Markdown + static HTML report. No network required.

Examples
--------
    # zero-arg demo on the committed sample dataset
    python src/main_pipeline.py

    # explicit run
    python src/main_pipeline.py --ingest data/raw/reddit_browser_posts.jsonl \
        --product "cold brew coffee maker" --db data/kb.sqlite3 \
        --report reports/cb.md --html reports/cb.html

    # config-driven (reads output_path, db_path, report_path, html_report_path)
    python src/main_pipeline.py --config configs/cold_brew_reddit.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agents.report_agent import ReportAgent
from pipeline.runner import run_cycle
from store.knowledge_base import DEFAULT_DB_PATH, KnowledgeBase
from workflows.job_config import load_reddit_crawl_job

SAMPLE_DATASET = "data/samples/cold_brew_sample.jsonl"
SAMPLE_PRODUCT = "cold brew coffee maker"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the demand-intelligence engine over Reddit evidence.")
    parser.add_argument("--config", help="JSON crawl config; supplies product, ingest, db, and report paths.")
    parser.add_argument("--ingest", nargs="+", help="One or more JSONL files of collected records.")
    parser.add_argument("--product", help="Product or keyword being researched.")
    parser.add_argument("--db", help="SQLite knowledge-base path.")
    parser.add_argument("--report", help="Markdown report output path.")
    parser.add_argument("--html", help="Static HTML report output path.")
    parser.add_argument("--deep-research-limit", type=int, default=8, help="Max themes to deep-research per cycle.")
    parser.add_argument("--merge-near-duplicates", action="store_true", help="Collapse near-duplicate themes by product wording.")
    parser.add_argument("--no-report", action="store_true", help="Skip writing report files.")
    return parser.parse_args(argv)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "product"


def read_records(paths: Sequence[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"Warning: ingest file not found, skipping: {path}")
            continue
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
    return records


def resolve_settings(args: argparse.Namespace) -> dict[str, Any]:
    product = args.product
    ingest = args.ingest
    db = args.db
    report = args.report
    html = args.html

    if args.config:
        job = load_reddit_crawl_job(args.config)
        product = product or job.product
        ingest = ingest or [job.output_path]
        db = db or job.db_path
        report = report or job.report_path
        html = html or job.html_report_path

    # Zero-config offline default: the committed sample dataset.
    if not ingest:
        ingest = [SAMPLE_DATASET]
        product = product or SAMPLE_PRODUCT
    product = product or SAMPLE_PRODUCT

    slug = _slug(product)
    return {
        "product": product,
        "ingest": ingest,
        "db": db or DEFAULT_DB_PATH,
        "report": report or f"reports/{slug}.md",
        "html": html or f"reports/{slug}.html",
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    settings = resolve_settings(args)

    records = read_records(settings["ingest"])
    if not records:
        raise SystemExit(f"No records found in: {', '.join(settings['ingest'])}")

    kb = KnowledgeBase(settings["db"])
    try:
        result = run_cycle(
            kb,
            records,
            settings["product"],
            deep_research_limit=args.deep_research_limit,
            merge_near_duplicates=args.merge_near_duplicates,
        )
        print(f"Product: {settings['product']}")
        print(f"Cycle: {result['pipeline_run'].summary}")
        print(f"Knowledge base: {settings['db']} -> {kb.counts()}")

        if not args.no_report:
            written = ReportAgent(kb).write(settings["product"], settings["report"], settings["html"])
            for kind, path in written.items():
                print(f"Wrote {kind} report: {path}")
    finally:
        kb.close()


if __name__ == "__main__":
    main()
