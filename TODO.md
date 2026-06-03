# TODO

## Stats

Total: 13 | Done: 9 | Pending: 4

## Tasks

### [Done] Set up project environment
- Owner: project team
- Due: 2026-05-13
- Dependencies: None

### [Done] Add initial Reddit collection workflows
- Owner: project team
- Due: 2026-05-13
- Dependencies: Project setup complete

### [Done] Make browser search workflow reusable from the command line
- Owner: project team
- Due: 2026-05-19
- Dependencies: Browser workflow prototype

### [In Progress] Add validation and tests for saved JSONL records
- Owner: project team
- Due: TBD
- Dependencies: Stable record schema

### [Done] Build a first-pass analysis workflow for product pain points
- Owner: project team
- Due: 2026-05-22
- Dependencies: Collected Reddit dataset

### [Done] Add adjustable crawl configuration
- Owner: project team
- Due: 2026-05-26
- Dependencies: Browser workflow prototype

### [Done] Improve location detection for merchant demand mapping
- Owner: project team
- Due: 2026-06-02
- Dependencies: More Reddit records with subreddit, title, body, and comment context
- Note: `analysis/geo.py` — subreddit→region map (strongest signal) + currency + spelling, confidence-weighted distribution

### [Pending] Add logged-in browser session support for small-batch crawling
- Owner: project team
- Due: TBD
- Dependencies: Browser profile/session strategy

### [Done] Compare with mentor's super_crawler reference
- Owner: project team
- Due: 2026-06-02
- Dependencies: Local copy of super_crawler
- Note: Local copy studied; gap closed and surpassed on data/analysis/memory/auditability. See docs/ARCHITECTURE.md.

### [Done] Build accumulating multi-agent demand intelligence engine
- Owner: project team
- Due: 2026-06-02
- Dependencies: super_crawler comparison
- Note: SQLite KB, hardened analysis, agent pipeline, confidence-aware scoring, Markdown + static HTML

### [Pending] Enrich browser collection (rich card fields + deep-fetch of post body/comments)
- Owner: project team
- Due: TBD
- Dependencies: Live browser/network access; defensive DOM extraction (Phase D)

### [Pending] Final analysis hardening pass
- Owner: project team
- Due: TBD
- Dependencies: Engine in place; expand taxonomy + subreddit→region map, deepen negation/weights, edge-case tests

### [Done] Add durable research memory
- Owner: project team
- Due: 2026-05-26
- Dependencies: Mentor feedback on context window management

### [Done] Add crawl run error logging
- Owner: project team
- Due: 2026-05-26
- Dependencies: Config-driven browser crawl
