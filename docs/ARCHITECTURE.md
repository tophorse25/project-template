# Demand Intelligence Engine — Architecture

This document describes the engine that evolved out of the Reddit research collector, and
explains, concretely, where it closes the gap with the mentor's `super_crawler` reference and
where it surpasses it.

## What it is

A deterministic, **accumulating** product-demand intelligence engine for e-commerce sellers.
It turns Reddit posts/comments about a product into a confidence-aware demand report: how much
demand exists, what pain points appear, where, and whether the evidence is strong enough to act on.

The design answer to *"the data is not enough"* is threefold:

1. **Richer + deeper collection** — capture more than title+URL (subreddit, score, comments, body,
   comments via deep-fetch). *(See Phase D / `extractors/`.)*
2. **Memory / accumulation** — evidence is keyed by canonical URL and **compounds across runs**, so
   thin individual crawls add up over time. This is `super_crawler`'s own stated differentiator,
   which the reference never implements for live data.
3. **Confidence-aware scoring** — every score is damped by evidence count and subreddit spread and
   carries an evidence-sufficiency label, so a theme seen once is *never* reported as validated.

## Data flow (one cycle)

```
collected records (browser / API / sample JSONL)
  -> DiscoveryAgent      save Evidence (with provenance) + propose CandidateThemes
  -> PoolManager         dedupe/merge into canonical DemandThemes; confidence-aware score + status
  -> ChangeDetection     reopen previously-researched themes on new evidence / score jump / new region
  -> DeepResearchAgent   deterministic research run per queued/reopened theme
  -> ReportAgent         Markdown + static HTML
        |
        v
  KnowledgeBase (SQLite)  evidence | themes | theme_evidence | research_runs | pipeline_runs | meta
```

Orchestrated by `pipeline/runner.run_cycle`. Offline-first: the cycle runs on already-collected
records; live collection is an optional front stage, never a requirement.

## Components

| Area | Module(s) | Responsibility |
|---|---|---|
| Memory | `src/store/` | SQLite KB, dataclass models, stable evidence ids, cross-run accumulation |
| Analysis | `src/analysis/signals.py`, `geo.py`, `scoring.py` | word-boundary + negation-aware signal detection; geo distribution; confidence-aware scoring |
| Agents | `src/agents/` | discovery, pool_manager, deep_research, change_detection, report_agent |
| Orchestration | `src/pipeline/runner.py` | one full cycle, logged as a `PipelineRun` |
| Collection | `src/browser/`, `src/extractors/`, `src/collectors/` | live browser + PRAW collection (enriched in Phase D) |
| Entry points | `src/main_pipeline.py`, `main_reddit_browser.py`, `main_report.py` | run the engine / collect / report |

## How this beats `super_crawler`

| Dimension | `super_crawler` | This engine |
|---|---|---|
| Live collection | None — ingests pre-saved JSON only | Live browser + API; card enrichment + deep-fetch of post body/comments |
| Thin-data handling | Hard 0–100 score from a single item | Confidence-aware scoring + evidence-sufficiency labels; never over-claims |
| Memory / accumulation | Per-run JSON ingest | Cross-run upsert keyed by canonical URL; `score_history`; velocity from deltas |
| Dedup | Jaccard on top-20 keywords @0.35 | Deterministic (product, category) id + stopword-aware token-set merge for wording drift |
| Geo | regex + 3 hardcoded subreddits | Data-driven subreddit→region map + currency + spelling; confidence-weighted distribution |
| Provenance | label lists only | Every label/score → evidence ids + matched terms, rendered in the report |
| False positives | none handled | Negation-aware matching ("no mold", "never leaked", "doesn't break") |
| Domain fit | generic "user requirements" | Merchant demand themes, willingness-to-pay, inventory stance |
| Reproducibility | heuristic | Fully deterministic, no external API, taxonomy-versioned labels |
| Offline | offline-only (a limitation) | Offline-capable **and** live-capable |
| UI | served web dashboard | Static HTML (no server) + Markdown |

### Honest scope note

We deliberately **trade** `super_crawler`'s served web dashboard, task groups, and research-queue
locking for a self-contained static HTML report (a chosen requirement). The "better" claim is on the
**data, analysis, memory, and auditability** axes — not UI breadth. Stated plainly so the comparison
is not overstated.

## Why the scores stay honest

`analysis/scoring.py` separates three numbers:

- **signal_strength** (0–100): how strong the signal looks (weighted dimensions).
- **confidence** (0–1): `0.6·n/(n+4) + 0.4·s/(s+1)` over evidence count `n` and subreddit count `s`.
- **adjusted_score** = `signal_strength × confidence`: the cautious number we rank, queue, and report.

A loud single post therefore stays low (`insufficient`) and is `needs_more_evidence`, while a theme
that accumulates across runs and subreddits climbs to `supported`/`strong`. Status can only reach
`validated` with sufficient evidence **and** a high adjusted score.

## Running it

```bash
# Offline demo on the committed sample dataset (zero args)
python src/main_pipeline.py

# Explicit
python src/main_pipeline.py --ingest data/raw/reddit_browser_posts.jsonl \
  --product "cold brew coffee maker" --db data/kb.sqlite3 \
  --report reports/cb.md --html reports/cb.html

# Config-driven
python src/main_pipeline.py --config configs/cold_brew_reddit.json

# Tests
python -m unittest discover -s tests
```

Run the pipeline twice to see accumulation: evidence/theme counts do not double, `last_seen`
advances, and velocity/change-detection begin to work from the deltas.
