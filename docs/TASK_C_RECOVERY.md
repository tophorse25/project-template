# Task C — Failure Recovery & State-Machine Integrity

Intern task C from the training deck (slide 10): *reproducible tests + recovery for
OpenCLI / LLM-timeout / DB-lock failures; re-queue stuck `researching`.* Implemented against
`_reference_super_crawler` (the system the deck describes). Hits the mentor's grading
criterion **"failures recoverable"** directly.

> **The exact code change** is in [`task-c-super_crawler.diff`](task-c-super_crawler.diff) —
> a unified diff against `ShuhangGe/super_crawler@main` (5 files). It's committed locally on the
> `intern/task-c-recovery` branch of that clone; apply with `git apply` or open as a PR once fork/push
> access is available.

## The three failure modes found (slide-6 problems, confirmed in code)

1. **Stuck `researching` (the headline bug).**
   `DeepResearchAgent.research()` flips a requirement to `researching` and sets the queue
   row's `locked_by`, but only `dequeue`s at the *end*. If the process dies (or `research()`
   raises) mid-run, the requirement is stuck `researching` forever and its queue row stays
   locked — `lock_next_research` only picks `locked_by IS NULL`, so it is never retried.
   There was **no reaper**.

2. **Non-atomic claim (double-assignment race).**
   `lock_next_research` did a `SELECT` then a separate `UPDATE` with no `WHERE locked_by IS NULL`
   guard, so two workers could claim the same requirement.

3. **No WAL.** `Storage.__init__` set `foreign_keys` but not `journal_mode`, so the dashboard
   reading while the runtime writes could raise "database is locked".

## The fixes

| Fix | Where | What |
|---|---|---|
| WAL + busy timeout | `storage.py` `__init__` | `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000` — readers and a writer coexist. |
| Atomic claim | `storage.py` `lock_next_research` | Conditional `UPDATE ... WHERE locked_by IS NULL` + `rowcount` check, retry on lost race. Compare-and-set, so no double-claim. |
| Reaper | `storage.py` `requeue_orphaned_research()` | Resets every `researching` requirement to `queued_for_research`, clears the assignee, unlocks/re-enqueues its queue row. |
| Failure recovery | `storage.py` `recover_failed_research()` + `agents.py` `run_next` | `run_next` wraps `research()`; on any exception the task is re-queued instead of stranded. |
| Recover on restart | `runner.py` `AlwaysOnRunner.run_once` | Calls `requeue_orphaned_research()` at the **start** of each cycle — safe, since anything still `researching` then has no live worker. |

## State machine (now enforced end-to-end)

```
queued_for_research --claim--> researching --success--> validated / watching / rejected
        ^                          |
        |  (crash / exception)     |
        +------ reaper / recover ---+
```

A requirement can never be permanently lost: a crash or a failed attempt always routes it
back to `queued_for_research`.

## Reproducible tests — `tests/test_recovery.py` (5, all green)

- `test_wal_is_enabled` — `PRAGMA journal_mode` is `wal`.
- `test_atomic_claim_prevents_double_lock` — two workers never get the same requirement.
- `test_reaper_requeues_orphaned_researching` — a simulated crash mid-research is recovered and re-claimable.
- `test_failed_research_is_requeued_not_stuck` — a raising `research()` (simulated LLM timeout) re-queues, leaves nothing `researching`.
- `test_recovery_is_idempotent` — running the reaper twice does not duplicate queue rows or dirty state.

Tests are **Windows-safe**: connections are closed (LIFO `addCleanup`) before the temp dir
is removed.

## Verify

```bash
cd _reference_super_crawler
python -m unittest tests.test_recovery -v     # the 5 recovery tests
python -m unittest discover -s tests          # full suite: 11 tests, all green
```

## Note on the existing suite (Windows portability)

The reference's pre-existing tests were written for Linux and never closed their SQLite
connection, so on Windows the open file handle made `TemporaryDirectory` cleanup raise
(`PermissionError [WinError 32]`) — the test *logic* passed; only teardown failed. Fixed
non-invasively with `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` (Python's
built-in flag for exactly this case). The suite now runs green on Windows.

## Next (depends on Task A)

The reaper currently reclaims *all* `researching` at cycle start (correct for the current
single-process, synchronous worker model). Once Task A adds a real `workers` table with
**heartbeats**, the reaper should reclaim only requirements whose worker heartbeat is stale —
enabling true concurrent multi-worker recovery.
