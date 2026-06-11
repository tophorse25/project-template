# Task E — Evaluation Metrics: Speed, Cost, Relevance, Validated Rate

Intern task E from the training deck (slide 10): *define monitoring metrics for speed, cost,
relevance, and validated rate.* Branch `intern/task-e-metrics` in the super_crawler clone
(on top of Task B); exact code change in [`task-e-super_crawler.diff`](task-e-super_crawler.diff).
Full suite **32/32 green**.

## Design principle

Every metric derives from data the system **already records** (pipeline runs, research runs,
requirement statuses, search plans, activity logs) — there is no separate metrics bookkeeping
that can drift out of sync with reality.

| Metric | Definition | Source |
|---|---|---|
| **Speed** | avg/last cycle duration; avg research-run duration; counts | `pipeline_runs` / `research_runs` timestamps |
| **Cost** | LLM plan calls + **compute seconds** (the honest unit for a local model — not dollars); heuristic-call count; agent cost estimates | `search_plans.llm_seconds` (planner times its call), `agent_activity_logs` |
| **Relevance** | discovery yield (candidates ÷ items ingested, recent cycles); signal rate (validated+watching ÷ researched); noise rate (rejected ÷ researched); per-cycle series | `pipeline_runs.result`, requirement statuses |
| **Validated rate** | validated ÷ researched | requirement statuses + `research_history` |

## Where to see it

- **Dashboard:** "Evaluation Metrics" panel on the home page — four headline cards
  (avg cycle, LLM compute, signal rate, validated rate) + discovery yield.
- **API:** `GET /api/metrics` — full JSON, ready for any external monitor.
- **CLI:** `python -m super_crawler.cli metrics`

## Live values at delivery (2026-06-11, deployed agent's real DB)

```
speed:      20 cycles, 18 research runs (deterministic cycles complete sub-second)
cost:       4 LLM plan calls, 3.68 s LLM compute (fresh plan; earlier plans predate the field)
relevance:  discovery yield 0.318 | signal rate 0.4 | noise rate 0.6 over 5 researched
validated:  0.2  (1 validated / 5 researched — the dog-medication requirement)
```

Honest readings these numbers already give you:
- **Noise rate 0.6** says most researched requirements die — expected for a discovery system,
  and the trend to watch as the planner converges.
- **Validated rate 0.2** is the system's bottom-line yield; it moved from 0.0 to 0.2 the moment
  the live loop closed.
- **avg cycle 0.0 s** is honest, not broken: research is deterministic today, and timestamps are
  second-precision. When LLM deep research lands, this number becomes the latency budget.

## Tests — `tests/test_metrics.py` (5)

Outcome-derived rates sum to 1 over researched; speed from pipeline timestamps (60 s fixture);
`llm_seconds` aggregation across plans; heuristic plans record zero; dashboard panel renders.
