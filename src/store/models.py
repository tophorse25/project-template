"""Dataclasses for the demand-intelligence knowledge base.

These are the durable entities the engine accumulates across runs. They mirror
(and improve on) the reference ``super_crawler`` models, but are framed for the
merchant product-research domain (demand themes, not generic requirements) and
carry confidence / evidence-sufficiency information so the system never
over-claims on thin data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> str:
    """ISO-8601 UTC timestamp at second precision (engine-wide source of truth)."""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


class ThemeStatus(StrEnum):
    """Lifecycle of a canonical demand theme."""

    NEW = "new_candidate"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    WATCHING = "watching"
    QUEUED_FOR_RESEARCH = "queued_for_research"
    RESEARCHING = "researching"
    VALIDATED = "validated"
    REJECTED = "rejected"
    REOPENED = "reopened"
    ARCHIVED = "archived"


class SufficiencyLabel(StrEnum):
    """How much evidence backs a score. Keeps thin data honest."""

    INSUFFICIENT = "insufficient"
    DIRECTIONAL = "directional"
    SUPPORTED = "supported"
    STRONG = "strong"


@dataclass(slots=True)
class Evidence:
    """A single Reddit post or comment, saved before any summarization.

    ``score_history`` accumulates metric snapshots across runs so velocity and
    change detection can work from real deltas instead of a single observation.
    """

    evidence_id: str
    platform: str
    source: str  # browser | api | deep
    source_type: str  # post | comment
    subreddit: str
    post_id: str | None
    comment_id: str | None
    url: str
    title: str
    body: str
    score: int | None
    comment_count: int | None
    created_utc: float | None
    query: str
    first_seen: str
    last_seen: str
    fetched_at: str
    language: str = "en"
    matched_signals: list[dict[str, Any]] = field(default_factory=list)
    geo_hints: list[str] = field(default_factory=list)
    score_history: list[dict[str, Any]] = field(default_factory=list)
    taxonomy_version: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateTheme:
    """A transient theme proposed by discovery before pool-manager reconciliation."""

    candidate_id: str
    product: str
    category: str
    label: str
    description: str
    evidence_ids: list[str]
    demand_signals: list[str]
    pain_points: list[str]
    geo_hints: list[str]
    confidence: float
    created_at: str


@dataclass(slots=True)
class DemandTheme:
    """A canonical, accumulating demand theme. The core product asset."""

    theme_id: str
    product: str
    category: str
    canonical_label: str
    description: str
    status: ThemeStatus
    sufficiency: str
    first_seen: str
    last_seen: str
    times_seen: int
    evidence_count: int
    subreddit_count: int
    demand_breakdown: dict[str, int]
    pain_breakdown: dict[str, int]
    geo_distribution: list[dict[str, Any]]
    current_scores: dict[str, Any]
    previous_scores: dict[str, Any]
    confidence: dict[str, Any]
    aliases: list[str]
    evidence_ids: list[str]
    history: list[dict[str, Any]]
    research_history: list[str]
    latest_recommendation: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ResearchRun:
    """A single deterministic deep-research pass over one theme."""

    run_id: str
    theme_id: str
    started_at: str
    completed_at: str | None
    input_evidence_ids: list[str]
    findings: dict[str, Any]
    scores: dict[str, Any]
    geo_analysis: list[dict[str, Any]]
    recommendation: str
    sufficiency: str
    limitations: list[str]
    changed_since_last_run: dict[str, Any]


@dataclass(slots=True)
class PipelineRun:
    """Operational record of one full engine cycle."""

    pipeline_run_id: str
    product: str
    started_at: str
    completed_at: str | None
    evidence_ingested: int
    new_evidence: int
    themes_touched: int
    themes_queued: int
    research_runs: int
    summary: str
