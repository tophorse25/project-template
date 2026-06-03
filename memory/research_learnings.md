# Research Learnings

Durable memory for lessons that should survive context-window compression and future sessions.

## Current Product Direction

- Target user: e-commerce sellers doing product research before stocking inventory.
- Current platform scope: Reddit first.
- Core report questions: how much demand exists, where demand appears, what pain points users mention, and what inventory stance is reasonable.
- Current output: merchant-facing Markdown reports with source evidence links.

## Query Lessons

- `worth it`, `best`, `recommendations`, and `buy` queries tend to find purchase-intent evidence.
- Region-specific queries can improve location coverage, but they can also bias the apparent region distribution.
- Pain-point queries such as `leaking`, `hard to clean`, `mold`, and `sediment` are useful for product positioning.

## Report Lessons

- Evidence URLs must be deduplicated before report generation.
- Browser search records are useful for fast discovery, but API/comment-rich records are needed for score, comment count, timestamps, and stronger location signals.
- Location coverage should be reported separately from demand coverage because weak location data should not block a demand read.

## Architecture Lessons

- Save raw evidence before summarizing.
- Keep long-running facts in files, not only in chat context.
- Use deterministic rule-based summaries as a baseline before adding LLM or agent analysis.
- Failed queries should be logged and skipped so a multi-query crawl can finish.
- **Memory is the real answer to thin data.** Key evidence by canonical URL and accumulate across
  runs (`score_history`, preserved `first_seen`) so individual thin crawls compound. This is what
  makes velocity and change detection possible at all.
- **Never over-claim on thin data.** Separate `signal_strength` (how loud) from `confidence`
  (`0.6·n/(n+4)+0.4·s/(s+1)`); rank/report on `adjusted_score = strength × confidence` and attach an
  evidence-sufficiency label. A theme seen once must read "directional/insufficient", never "validated".
- **Provenance over assertion.** Every label/score should trace back to evidence ids + matched terms;
  render that in the report so a human can verify.
- **Negation matters.** Word-boundary matching plus a small negation window ("no mold", "never leaked")
  removes a whole class of false positives the substring matcher produced.
- **Subreddit is the strongest geo signal** (e.g. r/IndiaCoffee → India), stronger than free-text;
  parse it even out of a URL. Report geo as a confidence-weighted distribution, separate from demand.
- Deterministic + no external API keeps results reproducible and auditable — a feature, not a limitation.

## super_crawler Comparison (durable)

- The reference cannot collect live data (ingests pre-saved JSON only); it scores hard 0–100 from a
  single item; its dedup is crude keyword Jaccard. We beat it on live collection, confidence-aware
  scoring, cross-run accumulation, dedup, geo, provenance, and negation. We deliberately traded its
  served dashboard for a static HTML report. Full matrix in `docs/ARCHITECTURE.md`.
