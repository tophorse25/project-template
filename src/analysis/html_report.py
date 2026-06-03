"""Self-contained static HTML report (no web server).

Renders the same accumulated, confidence-aware theme data as the Markdown report
into a single browsable HTML file with inline CSS. This is the deliberate trade we
made instead of the reference's served dashboard: dashboard-like browsing, zero
infrastructure, trivial to hand to a mentor.
"""

from __future__ import annotations

import html
from typing import Any

from analysis.report import evidence_labels

_CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       margin: 0; padding: 2rem; line-height: 1.5; background: #fafafa; color: #1a1a1a; }
h1 { margin: 0 0 .25rem; }
.sub { color: #666; margin-bottom: 1.5rem; }
.cards { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }
.card { background: #fff; border: 1px solid #e3e3e3; border-radius: 10px; padding: .75rem 1rem; min-width: 130px; }
.card .n { font-size: 1.6rem; font-weight: 700; }
.card .l { color: #666; font-size: .8rem; text-transform: uppercase; letter-spacing: .03em; }
table { border-collapse: collapse; width: 100%; background: #fff; border: 1px solid #e3e3e3; border-radius: 10px; overflow: hidden; }
th, td { padding: .5rem .7rem; text-align: left; border-bottom: 1px solid #eee; font-size: .92rem; }
th { background: #f0f0f0; }
.bar { height: 8px; background: #e7e7e7; border-radius: 4px; position: relative; min-width: 80px; }
.bar > span { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; background: #3b7; }
.status { font-size: .75rem; padding: .1rem .45rem; border-radius: 999px; border: 1px solid #ccc; white-space: nowrap; }
.s-validated { background: #d8f5e0; border-color: #8d8; }
.s-watching { background: #fff3cf; border-color: #e2c977; }
.s-needs_more_evidence, .s-insufficient { background: #f1f1f1; }
.s-reopened, .s-queued_for_research { background: #dce8ff; border-color: #9bf; }
details { background: #fff; border: 1px solid #e3e3e3; border-radius: 10px; margin: .6rem 0; padding: .4rem .9rem; }
summary { cursor: pointer; font-weight: 600; }
.kv { color: #444; font-size: .9rem; margin: .2rem 0; }
.evidence a { color: #1758c4; text-decoration: none; }
.evidence li { margin: .25rem 0; }
.tag { font-size: .72rem; color: #555; background: #f0f0f0; border-radius: 4px; padding: 0 .35rem; }
footer { color: #777; font-size: .82rem; margin-top: 2rem; }
"""


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _scores(theme: Any) -> dict[str, Any]:
    return theme.current_scores or {}


def _status_class(status: Any) -> str:
    return f"s-{str(status)}"


def _bar(value: float, maximum: float = 100.0) -> str:
    pct = max(0.0, min(100.0, (value / maximum) * 100.0 if maximum else 0.0))
    return f'<div class="bar"><span style="width:{pct:.0f}%"></span></div>'


def render_html_report(
    product: str,
    themes: list[Any],
    evidence_by_theme: dict[str, list[Any]],
    latest_run_by_theme: dict[str, Any] | None = None,
    pipeline_runs: list[Any] | None = None,
    taxonomy_version: str = "",
    generated_at: str = "",
    evidence_per_theme: int = 6,
) -> str:
    latest_run_by_theme = latest_run_by_theme or {}
    pipeline_runs = pipeline_runs or []
    ranked = sorted(themes, key=lambda t: _scores(t).get("adjusted_score", 0), reverse=True)
    total_evidence = len({e.evidence_id for evs in evidence_by_theme.values() for e in evs})

    rows = []
    for theme in ranked:
        scores = _scores(theme)
        top_region = theme.geo_distribution[0]["region"] if theme.geo_distribution else "—"
        rows.append(
            "<tr>"
            f"<td>{_e(theme.canonical_label)}</td>"
            f'<td><span class="status {_status_class(theme.status)}">{_e(theme.status)}</span></td>'
            f"<td>{theme.evidence_count}</td>"
            f"<td>{scores.get('adjusted_score', 0)}<br>{_bar(scores.get('adjusted_score', 0))}</td>"
            f"<td>{scores.get('confidence', 0)}</td>"
            f"<td>{_e(theme.sufficiency)}</td>"
            f"<td>{_e(top_region)}</td>"
            "</tr>"
        )

    details = []
    for theme in ranked:
        scores = _scores(theme)
        block = [
            f"<details><summary>{_e(theme.canonical_label)} "
            f'<span class="status {_status_class(theme.status)}">{_e(theme.status)}</span></summary>'
        ]
        block.append(
            f'<p class="kv">Adjusted <b>{scores.get("adjusted_score", 0)}</b> · '
            f'strength {scores.get("signal_strength", 0)} · confidence {scores.get("confidence", 0)} · '
            f'sufficiency {_e(theme.sufficiency)} · evidence {theme.evidence_count} across '
            f"{theme.subreddit_count} subreddit(s)</p>"
        )
        if theme.latest_recommendation:
            block.append(f'<p class="kv"><b>Recommendation:</b> {_e(theme.latest_recommendation)}</p>')
        if theme.demand_breakdown:
            block.append(f'<p class="kv"><b>Demand:</b> {_e(theme.demand_breakdown)}</p>')
        if theme.pain_breakdown:
            block.append(f'<p class="kv"><b>Pain:</b> {_e(theme.pain_breakdown)}</p>')
        if theme.geo_distribution:
            geo = ", ".join(
                f"{_e(row['region'])} ({row['confidence']}, n={row['evidence_count']})"
                for row in theme.geo_distribution
            )
            block.append(f'<p class="kv"><b>Geography:</b> {geo}</p>')

        run = latest_run_by_theme.get(theme.theme_id)
        if run is not None:
            findings = run.findings or {}
            if findings.get("why_real"):
                block.append(f'<p class="kv"><b>Why real:</b> {_e(findings["why_real"])}</p>')
            if findings.get("why_noise"):
                block.append(f'<p class="kv"><b>Why noise:</b> {_e(", ".join(findings["why_noise"]))}</p>')
            if findings.get("existing_solutions"):
                block.append(
                    f'<p class="kv"><b>Existing solutions:</b> {_e(", ".join(findings["existing_solutions"]))}</p>'
                )

        evidence = sorted(
            evidence_by_theme.get(theme.theme_id, []),
            key=lambda e: (e.score or 0) + (e.comment_count or 0),
            reverse=True,
        )[:evidence_per_theme]
        if evidence:
            block.append('<ul class="evidence">')
            for item in evidence:
                labels = ", ".join(evidence_labels(item)) or "no labels"
                title = _e(item.title or item.body[:80] or "Untitled")
                block.append(
                    f'<li><a href="{_e(item.url)}" target="_blank" rel="noopener">{title}</a> '
                    f'<span class="tag">r/{_e(item.subreddit)}</span> '
                    f'<span class="tag">{_e(labels)}</span></li>'
                )
            block.append("</ul>")
        block.append("</details>")
        details.append("".join(block))

    cards = [
        ("Themes", len(ranked)),
        ("Evidence", total_evidence),
        ("Cycles", len(pipeline_runs)),
        ("Validated", sum(1 for t in ranked if str(t.status) == "validated")),
    ]
    cards_html = "".join(f'<div class="card"><div class="n">{n}</div><div class="l">{_e(label)}</div></div>' for label, n in cards)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demand Report: {_e(product)}</title>
<style>{_CSS}</style></head>
<body>
<h1>Product Demand Report: {_e(product)}</h1>
<div class="sub">Deterministic engine · taxonomy {_e(taxonomy_version)} · generated {_e(generated_at)}</div>
<div class="cards">{cards_html}</div>
<h2>Demand Themes</h2>
<table><thead><tr>
<th>Theme</th><th>Status</th><th>Evidence</th><th>Adjusted</th><th>Confidence</th><th>Sufficiency</th><th>Top region</th>
</tr></thead><tbody>{''.join(rows) or '<tr><td colspan="7">No themes yet.</td></tr>'}</tbody></table>
<h2>Theme Detail</h2>
{''.join(details)}
<footer>Adjusted score is the cautious, confidence-weighted read; strength is the optimistic ceiling.
Thin themes are never auto-validated. Reddit is a demand signal, not a market-size measurement.</footer>
</body></html>
"""
