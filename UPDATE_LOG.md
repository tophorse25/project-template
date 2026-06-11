# Update Log

> Record significant milestones, completed features, and key decisions.
> Each entry: date, title, and bullet points of what was achieved.

## YYYY-MM-DD: Repository Initialized

- Created project-butler template
- Set up directory structure
- Configured commit message template

## 2026-05-22: First Merchant Report Workflow

- Added normalized Reddit record handling for browser and API data.
- Added rule-based demand signal, pain point, and location clue detection.
- Added Markdown report generation for merchant-facing product research.
- Generated the first sample report for cold brew coffee makers.

## 2026-05-26: Adjustable Crawl Jobs and Stronger Demand Report

- Added JSON config support for adjustable Reddit product research jobs.
- Updated the browser collector to run multi-query jobs from config.
- Updated report generation to separate demand volume evidence, location coverage, and inventory stance.
- Recorded `super_crawler` as a mentor reference pending repository access.

## 2026-06-11: Intern Task B — LLM Search Planner (Ollama) with Feedback Loop

- Added `SearchPlannerAgent` + stdlib Ollama client on branch `intern/task-b-llm-planner`:
  the LLM turns a research goal into dimensions, user-voice queries, sources, noise filters,
  and validation hypotheses — and reads deep-research feedback so each round converges.
- Flag-gated with a deterministic heuristic fallback: no Ollama → system runs exactly as before.
- `cli plan --export-config` bridges plans to the project Reddit collector's crawl-config format.
- Verified live with qwen2.5:3b on the deployed agent's DB: the model's negative keywords
  reproduced the deep researcher's rejected noise (lunchbox/meal-prep) — feedback loop proven.
- Plan renders on the live dashboard; 6 new fake-client tests; full suite 23/23 green.

## 2026-06-11: Deployed the super_crawler Agent (always-on, this machine)

- Deployed the agent with the Task A+C improvements as an always-on process: dashboard + runtime
  loop on http://127.0.0.1:8400 (port 8000 is reserved by HTTP.sys here), 300 s cycles.
- Added `serve --autostart` (branch `intern/deployment`) so the loop resumes after reboot without
  a human clicking Start; `deploy/start_super_crawler.ps1` watchdog restarts on crash and guards
  against double-starts; `deploy/register_startup.ps1` registers logon auto-start (user-run).
- Verified live: `/api/runtime` running with completed cycle + research run; dashboard renders
  "Deep Workers (real state)" with actual heartbeats. Docs: `docs/DEPLOYMENT.md`.

## 2026-06-02: Intern Task A — Real Worker State + Heartbeat Status Panel

- Built on Task C, branch `intern/task-a-observability` of the super_crawler clone.
- Added a `workers` table + lifecycle methods; every stage write doubles as a heartbeat.
- DeepResearchAgent now reports real stage transitions (claiming → analyzing_evidence → scoring →
  synthesizing → writing_conclusion → idle); failures record `last_error`.
- Made the Task C reaper **heartbeat-aware**: it skips requirements held by live fresh workers and
  reclaims only missing/stale holders — recovery is safe beside concurrent workers.
- Dashboard: new "Deep Workers (real state)" panel (stage, requirement, heartbeat age, stale warning);
  slot counts now from live workers, not locked queue rows; queue rows relabeled "Waiting in queue".
- 6 new tests; full reference suite 17/17 green. Writeup: `docs/TASK_A_WORKERS.md` + diff.

## 2026-06-02: Intern Task C — Failure Recovery on super_crawler

- Reframed by the mentor's training deck: Super Crawler is an agent-systems engineering case
  study (state, queue, workers, logs, recovery), graded on traceable / verifiable / recoverable.
- Implemented Task C on `_reference_super_crawler`: SQLite **WAL** + busy timeout; **atomic claim**
  (compare-and-set in `lock_next_research`); a **reaper** (`requeue_orphaned_research`) wired into
  the cycle so a restart re-queues stuck `researching`; **failure recovery** in `DeepResearchAgent.run_next`.
- Added `tests/test_recovery.py` (5 reproducible tests) and made the existing suite Windows-runnable;
  full reference suite now green (11 tests).
- Wrote `docs/TASK_C_RECOVERY.md` (gaps → fixes → state machine → verification) and
  `docs/INTERN_TASKS_PLAN.md` (codebase routing + sequenced plan for tasks A–E).

## 2026-06-02: Demand Intelligence Engine (closes + surpasses super_crawler)

- Added `src/store/` SQLite knowledge base with cross-run accumulation (evidence keyed by canonical
  URL; `score_history`), a queryable `theme_evidence` link table, and taxonomy versioning.
- Hardened the analysis core: word-boundary + negation-aware signal detection with provenance and
  confidence; data-driven geo distribution (subreddit→region, currency, spelling).
- Added confidence-aware scoring (`signal_strength` × `confidence` → `adjusted_score`, plus an
  evidence-sufficiency label) so thin data is never over-claimed — the central improvement over the
  reference's hard-score-from-one-item.
- Added a narrow-role agent pipeline (discovery, pool manager, deep research, change detection,
  report agent) and `pipeline/runner.run_cycle` orchestration.
- Added KB-based Markdown + self-contained static HTML reports with full evidence provenance.
- Added `src/main_pipeline.py` (offline-first entry point) and a committed sample dataset; extended
  the crawl config; wrote `docs/ARCHITECTURE.md` with the head-to-head comparison matrix.
- Test suite grew from 13 to 34 passing tests; all pre-existing behavior preserved.

## 2026-05-26: Agent Memory and Crawl Error Handling

- Added durable research memory for context-window management.
- Added structured crawl run logs with per-query success and failure metadata.
- Updated browser crawling so failed queries can be logged and skipped without stopping the full job.
- Added `--fail-fast` for debugging query failures.

