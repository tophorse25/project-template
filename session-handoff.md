# Session Handoff

> Updated at the end of each session. Provides context for the next session.

## Progress Summary

**All five intern tasks from the mentor's training deck are complete (C, A, B, E, D), plus
deployment and the closed live loop.** Work targets the `_reference_super_crawler` clone
(a real clone of `ShuhangGe/super_crawler`) on stacked branches:

```
main → intern/task-c-recovery → intern/task-a-observability → intern/deployment
     → intern/task-b-llm-planner → intern/task-e-metrics → intern/task-d-client-report
```

- **Task C** — failure recovery: WAL, atomic queue claim, orphaned-research reaper, failure requeue.
- **Task A** — real worker state: workers table + heartbeats, stage transitions, "Deep Workers"
  panel, heartbeat-aware reaper.
- **Deployed** — always-on agent on this machine: http://127.0.0.1:8400 (port 8000 is reserved by
  HTTP.sys), watchdog launcher (`deploy/start_super_crawler.ps1`), `serve --autostart`, 300 s cycles.
  Reboot persistence requires the user to run `deploy/register_startup.ps1` once.
- **Task B** — LLM search planner: local Ollama (qwen2.5:3b pulled), feedback loop from deep-research
  outcomes, heuristic fallback, `cli plan --export-config` bridge to collector configs.
- **Closed loop** — plan → live Reddit crawl (`src/bridge_to_inbox.py`) → inbox → research:
  `REQ-2026-000001` (dog medication tracking) reached **validated** (score 84, 9 evidence, 6 subreddits).
  Real data exposed + fixed two reference bugs: Windows UTF-8 ingestion crash; ~0% discovery recall
  (patterns broadened evidence-first, `builder_activity` signal added).
- **Task E** — metrics: speed/cost/relevance/validated-rate from recorded data; dashboard panel,
  `/api/metrics`, `cli metrics`.
- **Task D** — customer briefs: `/client-report` (+ nav), `cli client-report` export; sample at
  `reports/client-brief-dog-medication.html`.
- Reference suite: **37/37 tests green** on Windows. Per-task writeups + exact diffs in `docs/`
  (TASK_C/A/B/E/D + DEPLOYMENT + INTERN_TASKS_PLAN), all pushed to
  `tophorse25/project-template` branch `feature/reddit-browser-workflow`.
- Earlier phase (also complete): the Demand Intelligence Engine in `src/` — accumulating SQLite KB,
  confidence-aware scoring, 43 tests. Its HTML-report design fed Task D.

## Next Steps

- Open PRs from the clone branches to `ShuhangGe/super_crawler` once fork/push access exists
  (direct push is 403 for `tophorse25`).
- User runs `deploy/register_startup.ps1` once for reboot persistence.
- Optional improvements logged in task docs: validate planner-suggested subreddits, try a 7B model,
  deep-fetch crawls for engagement metrics, LLM-assisted candidate titling.

## Decisions Made

- Intern-task code lives in the super_crawler clone (the system the deck describes); the engine in
  `src/` remains the analysis/reporting reference implementation.
- LLM strictly optional by contract (`LLMUnavailable` → deterministic fallback); local Ollama, no API key.
- Cost metric for a local model is compute seconds, not dollars.
- Delivery to mentor: per-task diffs + writeups in `docs/` (clone can't be pushed without access).

## Blockers

- No push/fork access to `ShuhangGe/super_crawler` (403). Mentor can review via the diffs in `docs/`.
