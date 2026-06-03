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

## 2026-06-02: Demand Intelligence Engine (closes + surpasses super_crawler)

- Added `src/store/` SQLite knowledge base with cross-run accumulation (evidence keyed by canonical
  URL; `score_history`), a queryable `theme_evidence` link table, and taxonomy versioning.
- Hardened the analysis core: word-boundary + negation-aware signal detection with provenance and
  confidence; data-driven geo distribution (subreddit→region, currency, spelling).
- Added confidence-aware scoring (`signal_strength` × `confidence` → `adjusted_score`, plus an
  evidence-sufficiency label) so thin data is never over-claimed — the central improvement over the
  reference's hard-score-from-one-item.
- Added a narrow-role agent pipeline (discovery, pool manager, deep research, change detection,
  report agent) and `pipeline/runner.run_cycle` orchestration.
- Added KB-based Markdown + self-contained static HTML reports with full evidence provenance.
- Added `src/main_pipeline.py` (offline-first entry point) and a committed sample dataset; extended
  the crawl config; wrote `docs/ARCHITECTURE.md` with the head-to-head comparison matrix.
- Test suite grew from 13 to 34 passing tests; all pre-existing behavior preserved.

## 2026-05-26: Agent Memory and Crawl Error Handling

- Added durable research memory for context-window management.
- Added structured crawl run logs with per-query success and failure metadata.
- Updated browser crawling so failed queries can be logged and skipped without stopping the full job.
- Added `--fail-fast` for debugging query failures.

