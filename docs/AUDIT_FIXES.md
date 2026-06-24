# Audit-Driven Hardening

A multi-agent audit of the deployed `super_crawler` flagged improvements; this batch implements
them, then an adversarial multi-agent verification pass re-checked the fixes (and found a real
regression in one of them, now also fixed). Branch `intern/audit-fixes`; exact code in
[`audit-fixes-super_crawler.diff`](audit-fixes-super_crawler.diff).
**110 tests green (67 super_crawler + 43 engine).** Verified live on the deployed agent.

## How it was done

1. **Audit** — 3 agents reviewed scoring, concurrency/recovery, and LLM/UX, returning prioritized findings.
2. **Fix** — implemented every substantive finding with a regression test.
3. **Adversarially verify** — 5 agents independently re-checked the fixes (a security sweep for *any
   other* unsafe sink, scoring, hardening, LLM, and a completeness critic vs the original audit).
   Verdict: all "minor_issues", zero high-severity. It caught a genuine regression in the recovery
   fix (below), which was then corrected + tested.

## What changed

**Security**
- `urls.safe_url()` — links render only for `http(s)` (and reject embedded control chars/whitespace).
  `javascript:`/`data:` URLs from ingested Reddit data no longer become clickable script on the
  dashboard or in emailed/shared client reports. Top-level 500 barrier, escaped a dead `href`,
  truncated `last_result`, defensive `findings.get`.

**Scoring correctness**
- Velocity no longer self-inflates each idle cycle (promoted candidates are marked consumed).
- Change-detection measures a real new-evidence delta (scores carry `evidence_count`; `research()`
  stamps the baseline).
- Engagement is `log1p(total)·14` — a single viral post can't saturate it.
- Buildability is informative (80/60/0) instead of a constant 70.

**Recovery / concurrency** (incl. the regression the verifier caught)
- The reaper now uses the **freshest** worker heartbeat and the claim path **detaches stale worker
  rows**, closing a double-claim window where a crashed worker's lingering row could make the reaper
  falsely requeue a requirement a live worker was researching.

**Production**
- `migrate()` gated on `PRAGMA user_version` (no per-request DDL) — verified live: the deployed DB
  migrated 0→1 cleanly. `prune()` retention wired into the cycle. Per-file inbox parsing. Unknown
  requirement / merge-target / task-group ids return 404, not 500. Runtime failure path logs instead
  of swallowing.

**LLM / quality**
- Bounded retry in the Ollama client; prompt-injection delimiting now strips injected `<data>`
  markers so the fence can't be broken; hallucinated/None subreddits dropped; empty planner fields
  backfilled; varied signal-typed titles; stemmed-bigram dedup at 0.5 (real dupes merge, coincidental
  word overlap doesn't); client titles strip all template prefixes; removed the always-zero cost metric.

## Why this is the interesting part for the mentor

The deck's grading bar is *verifiable*. This batch shows the loop in practice: audit → fix → **adversarially
verify the fixes themselves**, where the verification found a bug the implementation introduced
(the reaper double-claim) — exactly the boundary-condition failure mode slide 9 warns about. Caught
before it shipped, by agents, with a regression test now guarding it.
