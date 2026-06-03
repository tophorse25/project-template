"""Deep research agent: validate one theme at a time, deterministically.

Produces a structured research run (why-real / why-noise / geo / breakdowns /
existing solutions / willingness-to-pay / opportunities / recommendation /
limitations) and updates the theme's status from confidence-aware scores. A theme
is never marked ``validated`` unless its evidence is actually sufficient.
"""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from analysis.scoring import recommendation, score_theme
from analysis.signals import category_label
from store.knowledge_base import KnowledgeBase
from store.models import DemandTheme, Evidence, ResearchRun, ThemeStatus, utc_now

RESEARCH_QUESTIONS = [
    "How often does this theme appear and is it growing?",
    "How many subreddits discuss it?",
    "How strong is the pain or purchase intent?",
    "Is there willingness-to-pay language?",
    "What existing products or workarounds are mentioned?",
    "Where (geographically) does the demand appear?",
    "Is this a stocking opportunity, a positioning angle, or noise?",
]

# Cold-brew specific solution/brand vocabulary (extend per product line).
KNOWN_SOLUTIONS = [
    "toddy", "oxo", "hario", "mizudashi", "french press", "mason jar",
    "nut milk bag", "cold brew bags", "filtron", "takeya", "coffee sock", "county line",
]

LIMITATIONS = [
    "Reddit evidence is a demand *signal*, not a total market-size estimate.",
    "Geography is inferred from subreddit, text mentions, currency, and spelling.",
    "Analysis is fully deterministic (rules + heuristics); no model is used.",
]


def _signal_size(adjusted: float) -> str:
    if adjusted >= 55:
        return "notable"
    if adjusted >= 30:
        return "modest"
    return "small"


class DeepResearchAgent:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def run_queued(
        self,
        limit: int = 5,
        now: str | None = None,
        now_epoch: float | None = None,
    ) -> list[ResearchRun]:
        now = now or utc_now()
        themes = self.kb.list_themes(
            statuses=[ThemeStatus.QUEUED_FOR_RESEARCH.value, ThemeStatus.REOPENED.value]
        )
        themes.sort(key=lambda t: t.current_scores.get("adjusted_score", 0), reverse=True)
        return [self.research(theme, now, now_epoch) for theme in themes[:limit]]

    def research(
        self, theme: DemandTheme, now: str | None = None, now_epoch: float | None = None
    ) -> ResearchRun:
        now = now or utc_now()
        theme.status = ThemeStatus.RESEARCHING
        self.kb.upsert_theme(theme)

        evidence = self.kb.evidence_for_theme(theme.theme_id)
        scores = score_theme(evidence, now_epoch=now_epoch)
        previous = self.kb.latest_research_run(theme.theme_id)
        run_id = "run_" + hashlib.sha1(f"{theme.theme_id}|{now}".encode("utf-8")).hexdigest()[:12]

        findings = {
            "summary": theme.canonical_label,
            "why_real": self._why_real(theme, evidence),
            "why_noise": self._why_noise(theme, scores, evidence),
            "demand_size": _signal_size(scores["adjusted_score"]),
            "demand_breakdown": theme.demand_breakdown,
            "pain_breakdown": theme.pain_breakdown,
            "existing_solutions": self._existing_solutions(evidence),
            "willingness_to_pay_signals": self._wtp_signals(evidence),
            "opportunities": self._opportunities(theme),
            "recommendation": recommendation(scores),
        }

        run = ResearchRun(
            run_id=run_id,
            theme_id=theme.theme_id,
            started_at=now,
            completed_at=utc_now(),
            input_evidence_ids=theme.evidence_ids,
            findings=findings,
            scores=scores,
            geo_analysis=theme.geo_distribution,
            recommendation=findings["recommendation"],
            sufficiency=scores["sufficiency"],
            limitations=LIMITATIONS,
            changed_since_last_run=self._changed(theme, previous),
        )
        self.kb.add_research_run(run)

        theme.previous_scores = theme.current_scores
        theme.current_scores = scores
        theme.sufficiency = scores["sufficiency"]
        theme.research_history = sorted({*theme.research_history, run_id})
        theme.latest_recommendation = findings["recommendation"]
        theme.status = self._status_from_scores(scores)
        theme.updated_at = utc_now()
        theme.history.append(
            {"at": now, "event": "researched", "status": theme.status.value, "run": run_id}
        )
        self.kb.upsert_theme(theme)
        return run

    def _status_from_scores(self, scores: dict[str, Any]) -> ThemeStatus:
        adjusted = scores["adjusted_score"]
        sufficiency = scores["sufficiency"]
        if sufficiency in {"supported", "strong"} and adjusted >= 55:
            return ThemeStatus.VALIDATED
        if adjusted >= 30:
            return ThemeStatus.WATCHING
        return ThemeStatus.REJECTED

    def _why_real(self, theme: DemandTheme, evidence: Sequence[Evidence]) -> str:
        subs = sorted({item.subreddit for item in evidence if item.subreddit})
        sub_text = ", ".join(f"r/{s}" for s in subs) or "no subreddit data"
        return (
            f"{theme.evidence_count} evidence item(s) across {theme.subreddit_count} "
            f"subreddit(s) ({sub_text}). Demand: {theme.demand_breakdown or 'none'}; "
            f"pain: {theme.pain_breakdown or 'none'}."
        )

    def _why_noise(
        self, theme: DemandTheme, scores: dict[str, Any], evidence: Sequence[Evidence]
    ) -> list[str]:
        risks: list[str] = []
        if theme.evidence_count < 4:
            risks.append("low evidence count")
        if theme.subreddit_count < 2:
            risks.append("single-subreddit concentration")
        negated = sum(
            1
            for item in evidence
            for match in (item.matched_signals or [])
            if match.get("negated")
        )
        if negated:
            risks.append(f"{negated} negated mention(s) present")
        if not self._wtp_signals(evidence):
            risks.append("no explicit willingness-to-pay language")
        if scores["sufficiency"] in {"insufficient", "directional"}:
            risks.append("evidence is not yet sufficient for a confident read")
        return risks or ["Main risk is Reddit sampling bias rather than a specific contradiction."]

    def _existing_solutions(self, evidence: Sequence[Evidence]) -> list[str]:
        haystack = " ".join((item.body or "").lower() for item in evidence)
        return sorted({solution for solution in KNOWN_SOLUTIONS if solution in haystack})

    def _wtp_signals(self, evidence: Sequence[Evidence]) -> list[str]:
        return sorted(
            {
                term
                for item in evidence
                for match in (item.matched_signals or [])
                if match.get("group") == "wtp" and not match.get("negated")
                for term in match.get("terms", [])
            }
        )

    def _opportunities(self, theme: DemandTheme) -> dict[str, list[str]]:
        label = category_label(theme.category).lower()
        product = theme.product
        if theme.category.startswith("pain:"):
            return {
                "product": [
                    f"Source or design a {product} that fixes '{label}'",
                    f"Lead listing copy with how this {product} avoids '{label}'",
                ],
                "content": [f"How to avoid '{label}' when buying a {product}"],
            }
        return {
            "product": [f"Stock {product} variants that match '{label}'"],
            "content": [f"Buyer's guide: choosing a {product} for '{label}'"],
        }

    def _changed(self, theme: DemandTheme, previous: ResearchRun | None) -> dict[str, Any]:
        if previous is None:
            return {"first_research": True}
        previous_count = len(previous.input_evidence_ids)
        current_adjusted = theme.current_scores.get("adjusted_score", 0)
        previous_adjusted = previous.scores.get("adjusted_score", 0)
        return {
            "first_research": False,
            "evidence_delta": theme.evidence_count - previous_count,
            "adjusted_delta": round(current_adjusted - previous_adjusted, 1),
        }
