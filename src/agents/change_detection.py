"""Change detection agent: reopen previously-researched themes when the world moves.

Only themes that already have a research run are candidates for reopening — themes
that have never been researched are handled by the pool manager's queue. Reopen
reasons are driven by accumulated deltas (new evidence, score jump, new region),
which is only possible because evidence accumulates across runs.
"""

from __future__ import annotations

from store.knowledge_base import KnowledgeBase
from store.models import DemandTheme, ThemeStatus, utc_now

_NEW_EVIDENCE_TRIGGER = 2
_SCORE_JUMP_TRIGGER = 12.0


class ChangeDetectionAgent:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def evaluate(self, now: str | None = None) -> list[DemandTheme]:
        now = now or utc_now()
        reopened: list[DemandTheme] = []
        watched = self.kb.list_themes(
            statuses=[
                ThemeStatus.WATCHING.value,
                ThemeStatus.VALIDATED.value,
                ThemeStatus.REJECTED.value,
            ]
        )
        for theme in watched:
            reason = self._reopen_reason(theme)
            if reason is None:
                continue
            theme.status = ThemeStatus.REOPENED
            theme.updated_at = now
            theme.history.append({"at": now, "event": "reopened", "reason": reason})
            self.kb.upsert_theme(theme)
            reopened.append(theme)
        return reopened

    def _reopen_reason(self, theme: DemandTheme) -> str | None:
        previous = self.kb.latest_research_run(theme.theme_id)
        if previous is None:
            return None

        new_evidence = theme.evidence_count - len(previous.input_evidence_ids)
        if new_evidence >= _NEW_EVIDENCE_TRIGGER:
            return f"{new_evidence} new evidence item(s) since last research"

        current = theme.current_scores.get("adjusted_score", 0)
        prior = previous.scores.get("adjusted_score", 0)
        if current - prior >= _SCORE_JUMP_TRIGGER:
            return "adjusted demand score increased materially"

        previous_regions = {row["region"] for row in previous.geo_analysis}
        current_regions = {row["region"] for row in theme.geo_distribution}
        new_regions = current_regions - previous_regions
        if new_regions:
            return f"new region(s) appeared: {', '.join(sorted(new_regions))}"

        return None
