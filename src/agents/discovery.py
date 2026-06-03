"""Discovery agent: collected records -> saved evidence + candidate themes.

Saves raw evidence (with provenance) before any summarization, then proposes one
candidate theme per detected demand/pain/willingness-to-pay category. Unlike the
reference, candidate labels are taxonomy-driven (e.g. "Leaking complaints"), not a
generic "Users need a better way to handle ..." phrase.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from analysis.signals import TAXONOMY_VERSION, category_label, extract_signals
from agents.text_utils import subreddit_from_url
from store.knowledge_base import KnowledgeBase, make_evidence_id
from store.models import CandidateTheme, Evidence, utc_now


def _first(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


class DiscoveryAgent:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def ingest(
        self,
        records: Iterable[dict[str, Any]],
        product: str,
        now: str | None = None,
    ) -> dict[str, Any]:
        now = now or utc_now()
        candidates: list[CandidateTheme] = []
        ingested = 0
        new_evidence = 0

        for record in records:
            evidence, record_candidates, is_new = self._ingest_one(record, product, now)
            if evidence is None:
                continue
            ingested += 1
            if is_new:
                new_evidence += 1
            candidates.extend(record_candidates)

        return {"candidates": candidates, "ingested": ingested, "new_evidence": new_evidence}

    def _ingest_one(
        self, record: dict[str, Any], product: str, now: str
    ) -> tuple[Evidence | None, list[CandidateTheme], bool]:
        url = _first(record, "url", "post_url") or ""
        post_id = record.get("post_id")
        comment_id = record.get("comment_id")
        if not url and not (post_id or comment_id):
            return None, [], False

        title = _first(record, "title", "post_title") or ""
        body = _first(record, "body", "text", "comment_text", "post_text") or ""
        subreddit = record.get("subreddit") or subreddit_from_url(url)
        source = record.get("source") or (
            "api" if any(key.startswith(("post_", "comment_")) for key in record) else "browser"
        )
        source_type = record.get("source_type") or (
            "comment" if comment_id or "/comment/" in url else "post"
        )

        extraction = extract_signals(title, body, subreddit or "")
        evidence_id = make_evidence_id(url, post_id, comment_id)
        evidence = Evidence(
            evidence_id=evidence_id,
            platform=record.get("platform", "reddit"),
            source=source,
            source_type=source_type,
            subreddit=subreddit or "",
            post_id=post_id,
            comment_id=comment_id,
            url=url,
            title=title,
            body=body,
            score=_first(record, "score", "post_score"),
            comment_count=_first(record, "comment_count", "post_num_comments"),
            created_utc=record.get("created_utc"),
            query=record.get("query", ""),
            first_seen=now,
            last_seen=now,
            fetched_at=now,
            language=record.get("language", "en"),
            matched_signals=extraction["matches"],
            geo_hints=extraction["geo_hints"],
            taxonomy_version=TAXONOMY_VERSION,
            raw=record,
        )
        stored, is_new = self.kb.upsert_evidence(evidence)

        candidates = self._candidates(stored, product, extraction, now)
        return stored, candidates, is_new

    def _candidates(
        self, evidence: Evidence, product: str, extraction: dict[str, Any], now: str
    ) -> list[CandidateTheme]:
        categories: list[str] = []
        categories += [f"demand:{label}" for label in extraction["demand_signals"]]
        categories += [f"pain:{label}" for label in extraction["pain_points"]]
        categories += [f"wtp:{label}" for label in extraction["willingness_to_pay"]]

        candidates: list[CandidateTheme] = []
        for category in categories:
            candidate_id = "cand_" + hashlib.sha1(
                f"{evidence.evidence_id}|{category}".encode("utf-8")
            ).hexdigest()[:14]
            candidates.append(
                CandidateTheme(
                    candidate_id=candidate_id,
                    product=product,
                    category=category,
                    label=f"{category_label(category)} — {product}",
                    description=(evidence.title or evidence.body)[:300],
                    evidence_ids=[evidence.evidence_id],
                    demand_signals=extraction["demand_signals"],
                    pain_points=extraction["pain_points"],
                    geo_hints=extraction["geo_hints"],
                    confidence=extraction["confidence"].get(category, 0.4),
                    created_at=now,
                )
            )
        return candidates
