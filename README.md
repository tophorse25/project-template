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

## Project Workflow

The repo also uses the project-butler tracking files:

- `PROJECT.md` for stage and module progress.
- `TODO.md` for next work items.
- `session-handoff.md` for continuity between sessions.
- `UPDATE_LOG.md` for milestone notes.
