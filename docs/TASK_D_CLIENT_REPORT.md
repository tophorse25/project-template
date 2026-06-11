# Task D — Customer-Readable Opportunity Briefs

Intern task D from the training deck (slide 10): *turn evidence, noise, conclusion, and the
next-step suggestion into a customer-readable page.* Branch `intern/task-d-client-report`
in the super_crawler clone (on top of Task E); exact code change in
[`task-d-super_crawler.diff`](task-d-super_crawler.diff). Full suite **37/37 green**.

## What it is

A second face for the same knowledge base. The dashboard is the *operator's* view (queues,
workers, lineage); the client report is the *customer's* view — plain language, no agent ids,
no queue states, every claim linked to its source evidence (the deck's slide-7 principle:
a good agent UI shows a process that can be trusted).

Each brief (deck slide 8.6 structure):

- **Verdict badge** in plain words: "Real demand — worth acting on" / "Promising — keep
  watching" / "Not enough evidence — likely noise"
- Headline stats: evidence count, communities, times detected, demand score
- **Why we believe this is real** / **Why it could still be noise**
- What people use today (workarounds + named products from the evidence)
- Willingness-to-pay language actually observed
- Where the demand appears (regions with confidence)
- Opportunities and the **suggested next step**
- **Source evidence** — every conclusion links back to the Reddit posts
- Limitations, stated plainly

The generator's boilerplate title prefix ("Users need a better way to handle …") is stripped —
clients read the substance.

## Where to see it

- **Live:** http://127.0.0.1:8400/client-report (overview, strongest first) — also in the
  dashboard nav as "Client Reports". Individual: `/client-report?id=REQ-2026-000001`.
- **Exported file:** `python -m super_crawler.cli client-report --requirement REQ-2026-000001
  --out brief.html` — fully self-contained HTML (inline CSS) that survives email/Slack with
  no server running. A real sample is committed at
  [`reports/client-brief-dog-medication.html`](../reports/client-brief-dog-medication.html) —
  the validated dog-medication requirement, end product of the closed loop.

## Tests — `tests/test_client_report.py` (5)

All customer sections present; **jargon-free assertion** (no `queued_for_research`,
`candidate_id`, `agent_id` on a client page); plain verdict language; overview links to each
researched brief; unknown-id renders not-found; boilerplate title stripping.

## Lineage note

This page is a port of the Demand Intelligence Engine's `analysis/html_report.py` approach
(self-contained HTML, evidence provenance, honest confidence) onto super_crawler's data
model — the engine work feeding back into the team system, as planned in
`INTERN_TASKS_PLAN.md`.
