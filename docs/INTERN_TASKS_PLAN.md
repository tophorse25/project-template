# Intern Tasks Plan — Agent System Engineering (Super Crawler)

> Plan only. No code is changed by this document. It maps the mentor's training deck
> (`agent-system-intern-training.pptx`) to concrete, sequenced work and decides which
> codebase each task should land in.

## 1. What the deck reframed

Super Crawler is **not a crawler exercise** — it is a **multi-agent system engineering**
case study. The LLM is only the decision module; the real system also needs **state,
tools, memory, queue, logs, and recovery**.

Mentor's grading bar (every deliverable must satisfy all three):

- **Traceable** — the process is visible (current stage, evidence chain).
- **Verifiable** — conclusions trace back to evidence; behavior is testable.
- **Recoverable** — failures, restarts, and concurrency never lose or corrupt state.

The five intern tasks (deck slide 10):

- **A — Status panel:** each deep worker's current stage, current requirement, recent **heartbeat**.
- **B — Search quality:** improve the **LLM search-planner prompt + source router**; reduce noise.
- **C — Failure recovery:** reproducible tests + recovery for OpenCLI / LLM-timeout / DB-lock; re-queue stuck `researching`.
- **D — Explain results:** evidence + noise + conclusion + next-step as a **customer-readable page**.
- **E — Metrics:** monitor **speed, cost, relevance, validated-rate**.

## 2. The two codebases

| | `_reference_super_crawler` (the system the deck describes) | Our engine (`src/`, the Demand Intelligence Engine we built) |
|---|---|---|
| Queue + worker slots | ✅ `research_queue`, `lock_next_research`, `locked_by`, `resource_config` (`max_deep_research_agents`…) | ❌ synchronous; a `queued` status processed in one cycle |
| Activity logs / dashboard / daemon | ✅ `agent_activity_logs`, web dashboard, daemon loop | ❌ none (static HTML report only) |
| Real worker heartbeat / recovery | ⚠️ "running" inferred from queue, no heartbeat, no stuck-task recovery | ❌ n/a (synchronous can't get stuck) |
| Analysis quality | ⚠️ basic heuristics, hard scores | ✅ confidence-aware scoring, negation, geo distribution, provenance |
| Explainable report | ⚠️ plain text + dev dashboard | ✅ self-contained HTML: evidence → why-real/why-noise → conclusion |
| Tests / idempotency | ⚠️ limited | ✅ 43 tests, deterministic ids, cross-run accumulation |

**Conclusion:** the deck's center of gravity (queue + real workers + heartbeat + recovery +
observability + LLM planning) lives in **super_crawler**. Our engine's strengths are
**explainability (Task D)** and **analysis/test discipline**.

## 3. Codebase routing decision (per task)

| Task | Lands in | Rationale |
|---|---|---|
| **A** Status panel + heartbeat | **super_crawler** | Has the dashboard + activity logs to extend; the task is about *its* deep workers. |
| **B** Search quality (LLM planner) | **super_crawler** | It is the system meant to host OpenCLI/LLM. **Blocked** on LLM key + OpenCLI access. |
| **C** Failure recovery | **super_crawler** | Recovery only means something with real async workers + a `researching` state to get stuck. |
| **D** Explainable page | **our engine → ported in** | We already built the best version; port `analysis/html_report.py` + confidence scoring into super_crawler. |
| **E** Metrics | **super_crawler** (edge) | It already has `agent_activity_logs.cost_estimate` + slots; our engine contributes relevance/validated scoring. |

**Overall:** do the agent-engineering tasks (A, C, E, then B) **on super_crawler**, and
**harvest our engine** for Task D (report) and for test/idempotency patterns. We stop
*extending* our engine and start treating it as a reference implementation to graft from.

## 4. Sequenced execution plan

Ordered by leverage and by what is **unblocked** (no live OpenCLI/LLM needed for ①–④).

### ① Task C — Failure recovery & state-machine integrity  *(start here)*
- **Have:** `research_queue`, `locked_by`, `researching` status.
- **Gap:** no recovery of stuck `researching` after restart; no WAL; no idempotency guards; no reproducible failure tests.
- **Steps:** enable `PRAGMA journal_mode=WAL`; add a startup/periodic **reaper** that re-queues `researching` rows with a stale worker heartbeat; make enqueue/claim/write **idempotent**; write **reproducible tests** simulating OpenCLI failure, LLM timeout, DB-lock (using fakes — no live deps).
- **Verify (recoverable):** per-failure-path unit tests; a kill-and-restart test proving no task is lost or permanently stuck.

### ② Task A — Status panel with real worker state  *(pairs with C)*
- **Gap:** "running" is inferred from the queue, not real workers; no heartbeat.
- **Steps:** add a `workers` table (`worker_id, stage, current_requirement, heartbeat_ts, slot`); deep workers write stage transitions (Planning→Searching→Analyzing→Synthesizing→Writing) + heartbeat; dashboard reads **real worker state**, not queue inference.
- **Verify (traceable):** run N workers, watch live stages + heartbeats; stop one → panel shows stale → C's reaper re-queues its task.

### ③ Task E — Evaluation metrics  *(small; builds on A/C instrumentation)*
- **Steps:** derive **speed** (stage durations), **cost** (token/call estimates), **relevance** (supporting-vs-noise evidence ratio), **validated-rate** (validated / researched) → a metrics view + JSON export.
- **Verify (verifiable):** metrics computed from a recorded run and cross-checked against `agent_activity_logs`.

### ④ Task D — Explainable customer page  *(mostly done in our engine — port it)*
- **Steps:** port our `analysis/html_report.py` + confidence-aware scoring into super_crawler's report layer so each requirement renders evidence → noise → conclusion → next-step for a non-technical client.
- **Verify (traceable):** generate the page for a real requirement; confirm every claim links back to evidence.

### ⑤ Task B — Search quality (LLM planner + source router)  *(last; blocked)*
- **Steps:** an LLM search-planner (dimensions/sources/queries/hypotheses) that **reads deep-research feedback** to converge; a source router across Reddit/forums/video/reviews.
- **Blocked on:** OpenCLI access + an LLM/API key, and reversing the current "fully deterministic" choice.

## 5. What's doable now vs needs access

- **Doable offline now:** C (recovery/WAL/idempotency/tests with fakes), A (worker/heartbeat model + status), E (metrics), D (port report).
- **Needs team access / keys:** B (LLM planner + OpenCLI source router); the OpenCLI/LLM-timeout *live* halves of C (simulated with fakes until then).

## 6. Open dependency to confirm before execution

The deck describes the **team's live runtime** (OpenCLI + LLM wired; slide-6 fixes already
shipped). The local `_reference_super_crawler` is a **deterministic snapshot that likely
predates those fixes**. Confirm which repo is the real target:

- **If the team's live repo:** A/C may be partly done already — scope to the remaining gaps; B becomes real work.
- **If only the local snapshot:** ①–④ above are all greenfield and fully doable offline; B stays blocked on keys.

Until confirmed, ①–④ on the local snapshot are safe, unblocked, and demonstrate the deck's
core thesis (queue + real workers + recovery + observability + explainability).
