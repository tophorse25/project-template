"""Report agent: gather accumulated theme data from the KB and render outputs.

Keeps storage access in the agent layer; the analysis renderers stay pure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.html_report import render_html_report
from analysis.report import render_markdown_report
from analysis.signals import TAXONOMY_VERSION
from store.knowledge_base import KnowledgeBase
from store.models import utc_now


class ReportAgent:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def _gather(self, product: str) -> dict[str, Any]:
        themes = self.kb.list_themes(product=product)
        evidence_by_theme = {t.theme_id: self.kb.evidence_for_theme(t.theme_id) for t in themes}
        latest_run_by_theme = {
            t.theme_id: self.kb.latest_research_run(t.theme_id) for t in themes
        }
        return {
            "product": product,
            "themes": themes,
            "evidence_by_theme": evidence_by_theme,
            "latest_run_by_theme": latest_run_by_theme,
            "pipeline_runs": self.kb.list_pipeline_runs(),
            "taxonomy_version": TAXONOMY_VERSION,
            "generated_at": utc_now(),
        }

    def markdown(self, product: str) -> str:
        return render_markdown_report(**self._gather(product))

    def html(self, product: str) -> str:
        return render_html_report(**self._gather(product))

    def write(
        self,
        product: str,
        markdown_path: str | None = None,
        html_path: str | None = None,
    ) -> dict[str, str]:
        data = self._gather(product)
        written: dict[str, str] = {}
        if markdown_path:
            path = Path(markdown_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_markdown_report(**data), encoding="utf-8")
            written["markdown"] = str(path)
        if html_path:
            path = Path(html_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_html_report(**data), encoding="utf-8")
            written["html"] = str(path)
        return written
