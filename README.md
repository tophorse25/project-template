# Reddit Research Collector

This project collects Reddit search results for early product-research workflows. It currently supports two paths:

- `src/main_reddit_browser.py`: opens Reddit search in Playwright and saves visible post links.
- `src/main_reddit.py`: uses the Reddit API through PRAW to collect posts and comments from specific subreddits.

The current sample topic is cold brew coffee makers, but the browser workflow can run any query from the command line.

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

## Agent Memory

Durable research lessons are stored in `memory/research_learnings.md`. Use this file for facts that should survive context-window compression, such as useful query patterns, false positives, report rules, and architecture decisions.

## Project Workflow

The repo also uses the project-butler tracking files:

- `PROJECT.md` for stage and module progress.
- `TODO.md` for next work items.
- `session-handoff.md` for continuity between sessions.
- `UPDATE_LOG.md` for milestone notes.
