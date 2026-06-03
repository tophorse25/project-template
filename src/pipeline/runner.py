"""Engine orchestration: one full discovery -> reconcile -> reopen -> research cycle.

The cycle is offline-first: it operates on already-collected records (from the KB,
saved JSONL, or the bundled sample). Live collection is an optional front stage added
by the entry point, never a requirement.
"""

from __future__ import annotations

from typing import Any, Iterable

from agents.change_detection import ChangeDetectionAgent
from agents.deep_research import DeepResearchAgent
from agents.discovery import DiscoveryAgent
from agents.pool_manager import PoolManager
from store.knowledge_base import KnowledgeBase
from store.models import PipelineRun, ThemeStatus, utc_now


def run_cycle(
    kb: KnowledgeBase,
    records: Iterable[dict[str, Any]],
    product: str,
    now: str | None = None,
    now_epoch: float | None = None,
    deep_research_limit: int = 8,
    merge_near_duplicates: bool = False,
) -> dict[str, Any]:
    now = now or utc_now()
    started_at = now

    discovery = DiscoveryAgent(kb)
    pool = PoolManager(kb)
    change = ChangeDetectionAgent(kb)
    research = DeepResearchAgent(kb)

    ingestion = discovery.ingest(records, product, now)
    touched = pool.reconcile(ingestion["candidates"], product, now=now, now_epoch=now_epoch)
    if merge_near_duplicates:
        pool.merge_near_duplicates(product)
    reopened = change.evaluate(now)
    runs = research.run_queued(limit=deep_research_limit, now=now, now_epoch=now_epoch)

    queued = len(
        kb.list_themes(
            statuses=[ThemeStatus.QUEUED_FOR_RESEARCH.value, ThemeStatus.REOPENED.value],
            product=product,
        )
    )
    summary = (
        f"ingested {ingestion['ingested']} ({ingestion['new_evidence']} new); "
        f"themes touched {len(touched)}; reopened {len(reopened)}; research runs {len(runs)}"
    )
    # Sequence-based id: unique and ordered even when two cycles land in the same second.
    sequence = kb.counts()["pipeline_runs"] + 1
    pipeline_run = PipelineRun(
        pipeline_run_id=f"cycle_{sequence:06d}",
        product=product,
        started_at=started_at,
        completed_at=utc_now(),
        evidence_ingested=ingestion["ingested"],
        new_evidence=ingestion["new_evidence"],
        themes_touched=len(touched),
        themes_queued=queued,
        research_runs=len(runs),
        summary=summary,
    )
    kb.save_pipeline_run(pipeline_run)

    return {
        "pipeline_run": pipeline_run,
        "ingestion": ingestion,
        "themes": touched,
        "reopened": reopened,
        "runs": runs,
    }
