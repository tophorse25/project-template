"""Pool manager: reconcile candidate themes into canonical, accumulating DemandThemes.

Improvements over the reference's crude keyword-Jaccard dedup:
- Themes have a **deterministic id** keyed by (normalized product, category), so the
  same theme accumulates across runs automatically — no fuzzy matching needed for the
  common case.
- A **category-aware + token-set-similarity** merge (``merge_near_duplicates``) collapses
  themes that differ only by product wording, which is where similarity actually helps.
- Scores are **confidence-aware** (see ``analysis.scoring``); status is derived from both
  the adjusted score and evidence sufficiency, so thin themes are never auto-validated.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Iterable

from agents.text_utils import breakdowns, normalize_product, token_set_similarity
from analysis.geo import aggregate_geo
from analysis.scoring import recommendation, score_theme
from analysis.signals import category_label
from store.knowledge_base import KnowledgeBase
from store.models import CandidateTheme, DemandTheme, ThemeStatus, utc_now

_TERMINAL = {ThemeStatus.VALIDATED, ThemeStatus.REJECTED, ThemeStatus.ARCHIVED}


def theme_id_for(product: str, category: str) -> str:
    key = f"{normalize_product(product)}|{category}"
    return "theme_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


class PoolManager:
    def __init__(self, kb: KnowledgeBase, similarity_threshold: float = 0.5) -> None:
        self.kb = kb
        self.similarity_threshold = similarity_threshold

    def reconcile(
        self,
        candidates: Iterable[CandidateTheme],
        product: str,
        now: str | None = None,
        now_epoch: float | None = None,
    ) -> list[DemandTheme]:
        now = now or utc_now()
        grouped: dict[str, list[CandidateTheme]] = defaultdict(list)
        for candidate in candidates:
            grouped[candidate.category].append(candidate)

        touched: list[DemandTheme] = []
        for category, group in grouped.items():
            touched.append(self._reconcile_category(product, category, group, now, now_epoch))
        return touched

    def _reconcile_category(
        self,
        product: str,
        category: str,
        candidates: list[CandidateTheme],
        now: str,
        now_epoch: float | None,
    ) -> DemandTheme:
        theme_id = theme_id_for(product, category)
        existing = self.kb.get_theme(theme_id)
        new_evidence_ids = sorted({eid for c in candidates for eid in c.evidence_ids})

        if existing is None:
            theme = DemandTheme(
                theme_id=theme_id,
                product=product,
                category=category,
                canonical_label=f"{category_label(category)} — {product}",
                description=candidates[0].description,
                status=ThemeStatus.NEW,
                sufficiency="insufficient",
                first_seen=now,
                last_seen=now,
                times_seen=0,
                evidence_count=0,
                subreddit_count=0,
                demand_breakdown={},
                pain_breakdown={},
                geo_distribution=[],
                current_scores={},
                previous_scores={},
                confidence={},
                aliases=[],
                evidence_ids=[],
                history=[],
                research_history=[],
                latest_recommendation=None,
                created_at=now,
                updated_at=now,
            )
        else:
            theme = existing

        # Ensure the row exists, then attach this round's evidence (FK needs the row first).
        self.kb.upsert_theme(theme)
        self.kb.link_evidence(theme_id, new_evidence_ids)

        evidence = self.kb.evidence_for_theme(theme_id)
        demand_breakdown, pain_breakdown = breakdowns(evidence)
        scores = score_theme(evidence, now_epoch=now_epoch)

        theme.previous_scores = theme.current_scores
        theme.current_scores = scores
        theme.confidence = {
            "factor": scores["confidence"],
            "sufficiency": scores["sufficiency"],
            "band": scores["band"],
        }
        theme.sufficiency = scores["sufficiency"]
        theme.evidence_ids = [item.evidence_id for item in evidence]
        theme.evidence_count = scores["evidence_count"]
        theme.subreddit_count = scores["subreddit_count"]
        theme.demand_breakdown = demand_breakdown
        theme.pain_breakdown = pain_breakdown
        theme.geo_distribution = aggregate_geo(item.geo_hints for item in evidence)
        theme.times_seen += len(candidates)
        theme.last_seen = now
        theme.aliases = sorted({*theme.aliases, *(c.label for c in candidates)})
        theme.latest_recommendation = recommendation(scores)
        theme.updated_at = now
        theme.history.append(
            {
                "at": now,
                "event": "reconciled",
                "candidates": len(candidates),
                "evidence_count": theme.evidence_count,
                "adjusted_score": scores["adjusted_score"],
            }
        )

        if theme.status not in _TERMINAL:
            theme.status = self._status_from_scores(scores, bool(theme.research_history))

        self.kb.upsert_theme(theme)
        return theme

    def _status_from_scores(self, scores: dict[str, Any], already_researched: bool) -> ThemeStatus:
        count = scores["evidence_count"]
        sufficiency = scores["sufficiency"]
        adjusted = scores["adjusted_score"]
        if count < 2:
            return ThemeStatus.NEEDS_MORE_EVIDENCE
        if sufficiency == "directional":
            return ThemeStatus.WATCHING
        if adjusted >= 45 and sufficiency in {"supported", "strong"}:
            # Defer re-research of already-studied themes to change detection, so we
            # don't spam a fresh research run on every cycle when nothing changed.
            return ThemeStatus.WATCHING if already_researched else ThemeStatus.QUEUED_FOR_RESEARCH
        return ThemeStatus.WATCHING

    def merge_near_duplicates(self, product: str | None = None) -> list[tuple[str, str]]:
        """Collapse same-category themes whose product wording is near-identical.

        Returns (source_id, target_id) pairs that were merged. This is where token-set
        similarity earns its keep — across runs with slightly different product strings.
        """

        themes = self.kb.list_themes(product=product)
        by_category: dict[str, list[DemandTheme]] = defaultdict(list)
        for theme in themes:
            by_category[theme.category].append(theme)

        merged: list[tuple[str, str]] = []
        for group in by_category.values():
            group.sort(key=lambda t: t.evidence_count, reverse=True)
            for index, target in enumerate(group):
                for source in group[index + 1 :]:
                    if source.theme_id == target.theme_id:
                        continue
                    if token_set_similarity(target.product, source.product) >= self.similarity_threshold:
                        self._merge(source, target)
                        merged.append((source.theme_id, target.theme_id))
        return merged

    def _merge(self, source: DemandTheme, target: DemandTheme) -> None:
        self.kb.link_evidence(target.theme_id, source.evidence_ids)
        target.aliases = sorted({*target.aliases, *source.aliases, source.canonical_label})
        target.times_seen += source.times_seen
        target.history.append({"at": utc_now(), "event": "merged_theme", "source": source.theme_id})
        evidence = self.kb.evidence_for_theme(target.theme_id)
        scores = score_theme(evidence)
        target.current_scores = scores
        target.evidence_ids = [item.evidence_id for item in evidence]
        target.evidence_count = scores["evidence_count"]
        target.subreddit_count = scores["subreddit_count"]
        target.sufficiency = scores["sufficiency"]
        self.kb.upsert_theme(target)

        source.status = ThemeStatus.ARCHIVED
        source.history.append({"at": utc_now(), "event": "merged_into", "target": target.theme_id})
        self.kb.upsert_theme(source)
