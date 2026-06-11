# Task A — Real Worker State, Heartbeats, and the Status Panel

Intern task A from the training deck (slide 10): *show each deep worker's current stage,
current requirement, and recent heartbeat.* Built on top of Task C
([TASK_C_RECOVERY.md](TASK_C_RECOVERY.md)), against the `super_crawler` clone, on branch
`intern/task-a-observability`.

> **The exact code change** is in [`task-a-super_crawler.diff`](task-a-super_crawler.diff)
> (4 files, on top of the Task C diff).

## The problem (the deck's slide 5/6 critique, confirmed in code)

The dashboard inferred "running agents" from things that are not agents:

- `deep_research_agents_panel` was titled **"Running Deep Research Agents"** but rendered
  **queue rows** ("Consuming queue: REQ-…") — queue items presented as running agents.
- `resource_allocation_panel` counted deep-research slots from `locked_by` on queue rows —
  but a locked row can belong to a **dead** worker.
- `agent_cards` showed the latest *historical activity log* with a hardcoded
  `status running` CSS class regardless of actual status — pretty status masking real state.

The deck's principle: **items in the queue are not agents; which agents are running must be
determined by real worker state.**

## The fix

| Change | Where | What |
|---|---|---|
| `workers` table | `storage.py` | worker_id, role, **stage**, current_requirement_id, started_at, **heartbeat_at**, last_error. |
| Lifecycle methods | `storage.py` | `update_worker_state` (every stage write **is** the heartbeat), `mark_worker_idle`, `list_workers` (returns heartbeat age). |
| Heartbeat-aware reaper | `storage.py` | `requeue_orphaned_research(stale_after_seconds=300)` now **skips** requirements held by a live fresh worker and reclaims only missing/stale holders — recovery is safe to run beside concurrent workers. (Closes the "Next" item from Task C.) |
| Real stage transitions | `agents.py` | DeepResearchAgent reports `claiming → analyzing_evidence → scoring → synthesizing → writing_conclusion → idle`; failure path records `last_error` and goes idle. |
| Truth panel | `dashboard.py` | New **"Deep Workers (real state)"** panel: stage badge, requirement link, heartbeat age, and a "STALE — recovery will requeue its task" warning. |
| Honest metrics | `dashboard.py` | Deep-research slot count = live busy workers (fresh heartbeat), not locked queue rows; queue rows relabeled "Waiting in queue". |

## How A and C compose

```
worker heartbeats (Task A)  ──feeds──▶  reaper staleness check (Task C)
        │                                        │
        ▼                                        ▼
 "Deep Workers" panel shows STALE   ──then──  stuck task auto-requeued
```

A dead worker is now *visible* (stale heartbeat on the panel) **and** *recoverable* (the
reaper requeues its requirement) — observability and recovery from the same source of truth.

## Tests — `tests/test_workers.py` (6, all green; full suite 17/17)

- `test_worker_state_records_stage_requirement_and_heartbeat` — lifecycle write + fresh age.
- `test_completed_research_leaves_worker_idle` — success path ends idle, no error.
- `test_failed_research_marks_worker_idle_with_error` — simulated LLM timeout records `last_error`.
- `test_reaper_skips_requirement_held_by_fresh_worker` — live worker is not robbed of its task.
- `test_reaper_reclaims_requirement_with_stale_heartbeat` — stale holder → requeued → reclaimable.
- `test_dashboard_panel_shows_real_worker_state` — panel renders worker id, stage, requirement, heartbeat.

## Verify

```bash
cd _reference_super_crawler
python -m unittest tests.test_workers -v     # the 6 worker tests
python -m unittest discover -s tests         # full suite: 17 tests green
python -m super_crawler.cli serve --port 8000  # open http://127.0.0.1:8000 → "Deep Workers (real state)"
```
