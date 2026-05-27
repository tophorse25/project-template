# Session Handoff

> Updated at the end of each session. Provides context for the next session.

## Progress Summary

- Repository contains two Reddit data collection paths:
  - Playwright browser search in `src/main_reddit_browser.py`
  - PRAW API collection in `src/main_reddit.py`
- Browser search now accepts command-line options for query, sort, limit, output path, screenshot path, headless mode, slow motion, and wait time.
- `requirements.txt` documents the direct runtime dependencies.
- `tests/test_reddit_workflow.py` covers URL generation, JSONL writing, and CLI parsing.
- `src/main_report.py` generates a merchant-facing Markdown report from Reddit JSONL.
- `src/analysis/` normalizes Reddit records and detects simple demand, pain point, and location signals.
- `configs/cold_brew_reddit.json` defines an adjustable product research crawl job.
- `src/main_reddit_browser.py` can run multi-query browser collection from a config file.
- `memory/research_learnings.md` stores durable lessons that should survive context-window compression.
- Browser crawls now write structured run logs and continue after individual query failures.
- `reports/cold-brew-coffee-maker.md` is the first sample demand report.
- Project tracking docs now describe the actual Reddit research collector instead of the starter template.

## Next Steps

- Run the browser collector across a small list of cold brew and coffee maker pain-point queries.
- Run a larger adjustable crawl to improve confidence in demand and region signals.
- Improve location detection with better region dictionaries and comment/body context.
- Add logged-in browser session support for small batch collection.
- Wrap the existing collector/report code into explicit SearchAgent and DeepAnalysisAgent classes.
- Add an LLM-assisted analysis layer after the rule-based report format stabilizes.

## Decisions Made

- Keep the browser workflow as the low-friction path because it works without Reddit API credentials.
- Keep the PRAW workflow for richer comment-level data when credentials are configured.
- Store raw outputs under `data/raw/`, which remains ignored by git.
- Build the report layer with deterministic rules first so agent/LLM output can be compared against a stable baseline.
- Treat mentor's `super_crawler` as a reference implementation once repository access is available.
- Keep durable findings in `memory/research_learnings.md` instead of relying on chat history.

## Blockers

- Network/browser access may be required to re-run live Reddit collection.
- `ShuhangGe/super_crawler` currently returns 404 through GitHub access, likely because it is private or not authorized.
