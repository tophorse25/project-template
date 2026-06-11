# Task B — LLM Search Planner with Feedback Loop

Intern task B from the training deck (slide 10): *analyze where noisy results come from;
improve the planner prompt and source-router strategy.* Implements slide 8's principle:
**the LLM plans the search instead of rescuing bad search.** Branch
`intern/task-b-llm-planner` in the super_crawler clone; exact code change in
[`task-b-super_crawler.diff`](task-b-super_crawler.diff) (7 files, 23/23 tests green).

## Design

```
research goal ──▶ SearchPlannerAgent ──▶ SearchPlan (persisted + on dashboard)
                       ▲                     │ dimensions, user-voice queries,
                       │                     │ sources, negative keywords,
            deep-research feedback           │ validation hypotheses
            (outcomes, noisy sources,        ▼
             rejection reasons)        --export-config ──▶ collector crawl config
```

- **Backend:** local **Ollama** (`super_crawler/llm.py`, stdlib urllib only — no new
  dependency, no API key). Model resolution: `--model` flag → `OLLAMA_MODEL` env → first
  pulled model.
- **Flag-gated, never required:** every LLM call path must catch `LLMUnavailable` and fall
  back to a deterministic template plan (`engine: "heuristic"`). No Ollama installed →
  system behaves exactly as before. This keeps the deck's reliability bar while adding the
  model.
- **The feedback loop (the actual Task B ask):** before planning, the agent summarizes the
  knowledge base — outcomes by status, which subreddits produced rejected requirements, and
  the deep researcher's `why_noise` reasons — and feeds that into the prompt so the next
  round avoids noisy sources and converges.
- **Actionable plans:** `plan --export-config` writes the queries as a crawl config in the
  project-template Reddit collector's format — the bridge from "plan" to "live search" to
  "inbox ingest".

## Verified live (2026-06-11, qwen2.5:3b on local Ollama)

Ran against the deployed agent's real database:

- Queries came back in genuine user voice: "need a better way to track my dog's meds",
  "dog meds reminder app missing features".
- The feedback summary it received: `outcomes so far: {'watching': 1, 'rejected': 3, ...};
  noisier sources: r/AskVet (2 rejected), r/Parenting, r/MealPrepSunday; rejection reasons:
  ... no clear willingness-to-pay language`.
- **The loop visibly worked:** the model's `negative_keywords` included "lunchbox planning"
  and "meal prep" — precisely the noise the deep researcher had rejected earlier. The
  planner learned from the system's own history.
- The plan renders on the live dashboard (engine badge, queries with rationale, noise
  filters, the feedback that was used) and exported
  `configs/plan_pet_medication.json` for the collector.

## Honest caveats (3B-model reality)

- `validation_hypotheses` came back empty on the live run (small-model lapse; the schema
  coercion tolerates it). A 7B model or a retry-on-empty would fix it.
- Suggested sources included plausible-but-unverified subreddits (e.g. r/PetLovers).
  Source suggestions should be validated against real subreddit existence before crawling —
  a good next increment for the source router.

## Usage

```bash
# plan for a free-form goal (model auto-resolves from Ollama)
python -m super_crawler.cli plan --goal "pet medication tracking for dog owners"

# plan for a task group, explicit model, and export a collector config
python -m super_crawler.cli plan --task-group tg_pet_care_search_0001 \
  --model qwen2.5:3b --export-config configs/plan_pet_care.json

# no Ollama? same command works - engine falls back to "heuristic"
```

## Tests — `tests/test_planner.py` (6, all green; full suite 27/27)

Fake LLM client, zero network: persistence + query coercion, feedback-reaches-prompt,
fallback on unavailable model, fallback with no client, crawl-config export, dashboard
rendering.

## The loop, closed (2026-06-11)

The full slide-3 pipeline ran end to end for the first time:

```
LLM plan (qwen2.5:3b) ─▶ live Reddit crawl (7 queries, 82 records)
      ▲                          │ src/bridge_to_inbox.py (project-template)
      │ feedback                 ▼
deep research ◀─ pool ◀─ discovery ◀─ reddit_inbox (64 unique items)
```

**Result:** `REQ-2026-000001` (dog medication tracking) went seed → rejected → reopened →
watching → **validated** (score 84.0, 9 evidence items, 6 subreddits), entirely through the
system's own machinery. Pool grew 5 → 17 requirements with real workaround evidence
(Gmail calendar, pill organizers) and named competitors (PupPlan, Medisafe, EveryDose).

Closing the loop with real data surfaced two genuine bugs, both fixed + regression-tested:

1. **UTF-8 ingestion crash** — `load_json_items` used the Windows locale codec and died on a
   curly apostrophe in a real title. All file IO now explicit UTF-8.
2. **Discovery recall was ~0%** — the original `SIGNAL_PATTERNS` missed all 64 real titles
   ("App for keeping track of dog meds?", "How do you keep track of…", "I built an app to…").
   Patterns were broadened evidence-first — every addition is pinned to a real crawled title
   in `tests/test_signal_patterns.py`, with neutral-title false-positive guards — and a new
   `builder_activity` signal counts "I built an app for this" posts as demand evidence.
   Same crawl after the fix: 4 → 27 candidates, 5 → 17 requirements.

This is Task B's mandate in action: *analyze where results are lost, improve the strategy,
verify with evidence.*
