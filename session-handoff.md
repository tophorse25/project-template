# Session Handoff

> Updated at the end of each session. Provides context for the next session.

## Progress Summary

- The project evolved from a Reddit collector into a **Demand Intelligence Engine** that closes the
  gap with the mentor's `super_crawler` reference and surpasses it on data/analysis/memory/auditability.
- Persistent memory: `src/store/` SQLite knowledge base. Evidence is keyed by canonical URL and
  **accumulates across runs** (`score_history`, preserved `first_seen`); a queryable `theme_evidence`
  link table replaces the reference's JSON blob.
- Hardened analysis (`src/analysis/`): `signals.py` (word-boundary + negation-aware, provenance,
  per-label confidence, versioned taxonomy), `geo.py` (subreddit→region + currency + spelling,
  confidence-weighted distribution), `scoring.py` (confidence-aware: `signal_strength × confidence
  → adjusted_score`, evidence-sufficiency labels — thin data never over-claimed).
- Agent pipeline (`src/agents/`): discovery → pool_manager → change_detection → deep_research →
  report_agent, orchestrated by `src/pipeline/runner.run_cycle`.
- Reporting: KB-based Markdown (`analysis/report.py`) + self-contained static HTML
  (`analysis/html_report.py`), both with full evidence provenance and confidence.
- Entry point: `src/main_pipeline.py` (offline-first; `--ingest` / `--config`). Committed sample
  dataset `data/samples/cold_brew_sample.jsonl` makes the whole thing runnable with no network.
- Tests: 34 passing (`python -m unittest discover -s tests`); all pre-existing tests preserved.
- Docs: `docs/ARCHITECTURE.md` holds the head-to-head comparison matrix; README/PROJECT updated.

## Next Steps

- **Phase D (collection enrichment):** enhance `extractors/reddit_extractor.py` to pull rich
  search-card fields (subreddit, score, comments, age, snippet) defensively (null, never invented);
  add `extractors/reddit_post_extractor.py` to deep-fetch post body + top comments; feed enriched
  records into the pipeline. Network/browser dependent.
- **Final hardening pass:** expand taxonomy + subreddit→region map, deepen negation/weights/calibration,
  add edge-case tests.
- Optionally wire a `--collect` front stage into `main_pipeline.py` once Phase D lands.

## Decisions Made

- Fully **deterministic** — no LLM / no API key (reproducible, auditable, "never hallucinate").
- **SQLite** knowledge base (stdlib, no new dependency) to match/beat the reference's memory.
- **Static HTML** report instead of a served dashboard (chosen UI scope); the "better" claim is on
  data/analysis/memory/auditability, stated honestly in `docs/ARCHITECTURE.md`.
- Evolve the existing repo in place, reusing current modules; keep old record-based report + tests.
- Confidence-aware scoring is the core answer to thin data: accumulate across runs, report honestly.

## Blockers

- Live Reddit collection still needs browser/network access; Phase D enrichment is unverified offline
  by design (the engine itself is fully exercised on the committed sample dataset).
