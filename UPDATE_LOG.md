# Update Log

> Record significant milestones, completed features, and key decisions.
> Each entry: date, title, and bullet points of what was achieved.

## YYYY-MM-DD: Repository Initialized

- Created project-butler template
- Set up directory structure
- Configured commit message template

## 2026-05-22: First Merchant Report Workflow

- Added normalized Reddit record handling for browser and API data.
- Added rule-based demand signal, pain point, and location clue detection.
- Added Markdown report generation for merchant-facing product research.
- Generated the first sample report for cold brew coffee makers.

## 2026-05-26: Adjustable Crawl Jobs and Stronger Demand Report

- Added JSON config support for adjustable Reddit product research jobs.
- Updated the browser collector to run multi-query jobs from config.
- Updated report generation to separate demand volume evidence, location coverage, and inventory stance.
- Recorded `super_crawler` as a mentor reference pending repository access.

## 2026-05-26: Agent Memory and Crawl Error Handling

- Added durable research memory for context-window management.
- Added structured crawl run logs with per-query success and failure metadata.
- Updated browser crawling so failed queries can be logged and skipped without stopping the full job.
- Added `--fail-fast` for debugging query failures.

