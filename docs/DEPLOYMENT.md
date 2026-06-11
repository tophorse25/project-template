# Deployment — super_crawler Agent (this week's deliverable)

The always-on super_crawler agent (with the Task A worker observability + Task C failure
recovery improvements) is **deployed and running** on this machine.

- **Dashboard:** http://127.0.0.1:8400 — "Deep Workers (real state)" panel, queue, lineage, reports
- **Runtime API:** http://127.0.0.1:8400/api/runtime — `running`, cycle count, last result/error
- **Port note:** 8000 is reserved by Windows HTTP.sys on this machine, so the agent uses **8400**.

## What is running

One process: `python -m super_crawler.cli serve --port 8400 --interval-seconds 300 --autostart`

- `--autostart` (added on branch `intern/deployment`, see
  [`task-deploy-super_crawler.diff`](task-deploy-super_crawler.diff)) starts the processing loop
  immediately — after a reboot no human has to click **Start**.
- Every **300 s** the runtime runs a full cycle: recover orphaned research (Task C reaper) →
  ingest `data/reddit_inbox` → reconcile pool → change detection → deep research by slots
  (workers heartbeat their stage, Task A) → pipeline snapshot.
- The launcher (`deploy/start_super_crawler.ps1`) is a watchdog: if the agent process dies it
  restarts it after 5 s and writes logs to `deploy/logs/`. It also refuses to start a second
  copy if the dashboard already answers.

## Operating it

```powershell
# start now (also used by the watchdog at logon)
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\start_super_crawler.ps1

# register auto-start at logon (run once, survives reboots)
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\register_startup.ps1

# stop everything
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*start_super_crawler*" -or $_.CommandLine -like "*super_crawler.cli*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# feed it work: drop JSON arrays of Reddit-like items into
_reference_super_crawler\data\reddit_inbox\
```

## Verification performed (2026-06-11)

1. `GET /api/runtime` → `"running": true`, cycle 1 completed: 4 requirements reconciled,
   research run `run_9559f0bb45c0` produced, `"recovered": 0` (reaper reporting).
2. Dashboard HTML contains **Deep Workers (real state)** with `research-agent-1`'s actual
   stage and heartbeat age.
3. Watchdog proven by the port-8000 incident: bind failures were logged and retried every 5 s,
   and after the port fix the agent came up cleanly.

## How this meets the deck's bar (slide 12)

- **能运行 (runs):** continuous cycles on an interval, watchdog restart, single-instance guard.
- **能解释 (explains):** dashboard lineage + worker stages + pipeline snapshots per cycle.
- **能恢复 (recovers):** crash → watchdog restart → `--autostart` resumes the loop →
  Task C reaper requeues anything left `researching`. No state lost, end to end.

## Limitations / next steps

- Local deployment: live only while this PC is on; dashboard reachable from this machine only
  (bind is 127.0.0.1). Move to a team server for a shared URL.
- The inbox is not yet auto-fed; wiring the project's Reddit collector to drop JSONL→JSON into
  `reddit_inbox` on a schedule is the natural next increment ("Both, bridged").
- Auto-start registration (`deploy/register_startup.ps1`) must be run once by the user.
