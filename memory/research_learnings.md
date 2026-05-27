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
