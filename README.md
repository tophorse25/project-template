# Demand Intelligence Engine (Reddit)

A deterministic, **accumulating** product-demand intelligence engine for e-commerce sellers. It
collects Reddit discussion about a product and turns it into a confidence-aware demand report:
how much demand exists, what pain points appear, where, and whether the evidence is strong enough
to act on. It grew out of a simple Reddit collector and now closes the gap with — and surpasses —
the mentor's `super_crawler` reference on data, analysis, memory, and auditability. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and comparison.

Collection paths:

- `src/main_reddit_browser.py`: opens Reddit search in Playwright and saves visible post links.
- `src/main_reddit.py`: uses the Reddit API through PRAW to collect posts and comments from specific subreddits.

Analysis + memory + reporting:

- `src/main_pipeline.py`: runs the full engine cycle (discovery → reconcile → reopen → research →
  report) over collected evidence into a persistent SQLite knowledge base. **Offline-first** — runs
  on saved or sample data with no network.

The current sample topic is cold brew coffee makers, but everything is product-agnostic.

## Quick demo (offline, zero setup beyond install)

```bash
python src/main_pipeline.py
```

This ingests the committed `data/samples/cold_brew_sample.jsonl`, runs a full cycle, and writes a
Markdown + static HTML report under `reports/`. Run it twice to see cross-run **accumulation**
(evidence counts do not double; signal compounds).

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

For the API collector, copy `.env.example` to `.env` and fill in Reddit API credentials.

## Browser Search

```bash
.\.venv\Scripts\python.exe src\main_reddit_browser.py --query "cold brew coffee maker" --limit 20
```

Useful options:

```bash
.\.venv\Scripts\python.exe src\main_reddit_browser.py --query "coffee maker leaking" --sort new --headless --output data/raw/leaking_posts.jsonl
```

Adjustable multi-query crawl jobs can be stored in `configs/`:

```bash
.\.venv\Scripts\python.exe src\main_reddit_browser.py --config configs\cold_brew_reddit.json --headless
```

Each config-driven crawl writes a JSON run log under `log/crawl-runs/`. Failed queries are recorded and skipped so the rest of the crawl can finish. Use `--fail-fast` when debugging if you want the first query failure to stop the run.

Outputs are written as JSONL under `data/raw/`, which is ignored by git.

## API Collector

```bash
.\.venv\Scripts\python.exe src\main_reddit.py
```

This path searches the configured subreddits and saves post/comment records to `data/raw/reddit_cold_brew_sample.jsonl`.

## Tests

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Merchant Report

Generate a first-pass product demand report from collected Reddit JSONL:

```bash
.\.venv\Scripts\python.exe src\main_report.py --input data\raw\reddit_browser_posts.jsonl --product "cold brew coffee maker" --output reports\cold-brew-coffee-maker.md
```

Using the same crawl config:

```bash
.\.venv\Scripts\python.exe src\main_report.py --config configs\cold_brew_reddit.json --input data\raw\reddit_browser_posts.jsonl
```

The report summarizes demand volume evidence, demand signals, pain points, location clues, inventory stance, and evidence links. The current analyzer is rule-based so the workflow stays testable before adding an LLM or agent layer.

## Demand Intelligence Engine

The engine accumulates evidence across runs into a SQLite knowledge base, dedupes it into canonical
**demand themes**, scores them with a **confidence-aware** model (thin themes are never over-claimed),
runs deterministic deep research, and renders Markdown + static HTML.

```bash
# Offline, on already-collected JSONL
python src/main_pipeline.py --ingest data/raw/reddit_browser_posts.jsonl \
  --product "cold brew coffee maker" --db data/kb.sqlite3 \
  --report reports/cb.md --html reports/cb.html

# Config-driven (reads output_path, db_path, report_path, html_report_path from the config)
python src/main_pipeline.py --config configs/cold_brew_reddit.json
```

Live collection (browser/API) feeds JSONL into the same pipeline: run a collector, then point
`--ingest` at its output. Architecture and the `super_crawler` comparison live in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Agent Memory

Durable research lessons are stored in `memory/research_learnings.md`. Use this file for facts that should survive context-window compression, such as useful query patterns, false positives, report rules, and architecture decisions.

## Project Workflow

The repo also uses the project-butler tracking files:

- `PROJECT.md` for stage and module progress.
- `TODO.md` for next work items.
- `session-handoff.md` for continuity between sessions.
- `UPDATE_LOG.md` for milestone notes.
