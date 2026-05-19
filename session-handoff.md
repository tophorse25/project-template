# Session Handoff

> Updated at the end of each session. Provides context for the next session.

## Progress Summary

- Repository contains two Reddit data collection paths:
  - Playwright browser search in `src/main_reddit_browser.py`
  - PRAW API collection in `src/main_reddit.py`
- Browser search now accepts command-line options for query, sort, limit, output path, screenshot path, headless mode, slow motion, and wait time.
- `requirements.txt` documents the direct runtime dependencies.
- `tests/test_reddit_workflow.py` covers URL generation, JSONL writing, and CLI parsing.
- Project tracking docs now describe the actual Reddit research collector instead of the starter template.

## Next Steps

- Run the browser collector across a small list of cold brew and coffee maker pain-point queries.
- Decide on the canonical JSONL schema shared by browser and API records.
- Expand tests once the shared record schema is finalized.
- Start a simple analysis script that groups posts by pain point, recommendation, and purchase intent.

## Decisions Made

- Keep the browser workflow as the low-friction path because it works without Reddit API credentials.
- Keep the PRAW workflow for richer comment-level data when credentials are configured.
- Store raw outputs under `data/raw/`, which remains ignored by git.

## Blockers

- Network/browser access may be required to re-run live Reddit collection.
