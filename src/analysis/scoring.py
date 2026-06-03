"""Confidence-aware demand scoring.

The central improvement over ``super_crawler``: the reference emits a hard 0-100
score even from a single evidence item, which over-claims on thin data. Here every
theme produces:

- ``signal_strength`` (0-100): how strong the signal *looks*.
- ``confidence`` (0-1): how much we trust it given evidence count and subreddit spread.
- ``adjusted_score`` = ``signal_strength * confidence``: the cautious number we rank
  and queue on. A theme seen once stays low no matter how loud it looks.
- ``sufficiency``: insufficient -> directional -> supported -> strong.

This keeps the system honest about thin data instead of inventing certainty.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from statistics import mean
from typing import Any, Sequence

DAY = 86400.0

WEIGHTS: dict[str, float] = {
    "frequency": 0.15,
    "velocity": 0.12,
    "subreddit_spread": 0.13,
    "pain_intensity": 0.15,
    "demand_intent": 0.15,
    "engagement": 0.10,
    "willingness_to_pay": 0.10,
    "geo_confidence": 0.05,
    "recency": 0.05,
}

# Damping constants for the confidence factor: evidence needs to accumulate
# before a theme is trusted (n/(n+K)).
_EVIDENCE_K = 4.0
_SPREAD_K = 1.0


def sufficiency_label(evidence_count: int, subreddit_count: int) -> str:
    if evidence_count < 2:
        return "insufficient"
    if evidence_count < 4 or subreddit_count < 2:
        return "directional"
    if evidence_count >= 8 and subreddit_count >= 3:
        return "strong"
    return "supported"


def _has_group(evidence: Any, group: str) -> bool:
    return any(
        match.get("group") == group and not match.get("negated")
        for match in (evidence.matched_signals or [])
    )


def _fraction(items: Sequence[Any], predicate) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if predicate(item)) / len(items)


def _geo_confidence(evidence: Sequence[Any]) -> float:
    counts: Counter[str] = Counter()
    geo_bearing = 0
    for item in evidence:
        hints = item.geo_hints or []
        if hints:
            geo_bearing += 1
        counts.update(hints)
    if geo_bearing == 0:
        return 0.0
    return counts.most_common(1)[0][1] / geo_bearing


def _empty_score() -> dict[str, Any]:
    dims = {key: 0.0 for key in WEIGHTS}
    return {
        "dimensions": dims,
        "signal_strength": 0.0,
        "confidence": 0.0,
        "adjusted_score": 0.0,
        "sufficiency": "insufficient",
        "evidence_count": 0,
        "subreddit_count": 0,
        "band": {"cautious": 0.0, "optimistic": 0.0},
    }


def score_theme(evidence: Sequence[Any], now_epoch: float | None = None) -> dict[str, Any]:
    """Score a theme from its evidence. ``now_epoch`` injectable for deterministic tests."""

    count = len(evidence)
    if count == 0:
        return _empty_score()
    if now_epoch is None:
        now_epoch = datetime.now(UTC).timestamp()

    subreddits = {item.subreddit for item in evidence if item.subreddit}
    spread_count = len(subreddits)
    created = [item.created_utc for item in evidence if item.created_utc]

    frequency = min(count * 12.0, 100.0)
    subreddit_spread = min(spread_count * 25.0, 100.0)
    demand_intent = _fraction(evidence, lambda e: _has_group(e, "demand")) * 100.0
    pain_intensity = _fraction(evidence, lambda e: _has_group(e, "pain")) * 100.0
    willingness_to_pay = min(_fraction(evidence, lambda e: _has_group(e, "wtp")) * 150.0, 100.0)

    engagement_values = [(item.score or 0) + (item.comment_count or 0) for item in evidence]
    engagement = min(mean(engagement_values), 100.0) if engagement_values else 0.0

    if created:
        newest = max(created)
        recent_fraction = _fraction(created, lambda c: (now_epoch - c) <= 21 * DAY)
        velocity = min(recent_fraction * 120.0, 100.0)
        days_since_newest = max(0.0, (now_epoch - newest) / DAY)
        recency = max(0.0, 100.0 - days_since_newest * 2.0)
    else:
        velocity = 0.0
        recency = 0.0

    geo_confidence = _geo_confidence(evidence) * 100.0

    dimensions = {
        "frequency": round(frequency, 1),
        "velocity": round(velocity, 1),
        "subreddit_spread": round(subreddit_spread, 1),
        "pain_intensity": round(pain_intensity, 1),
        "demand_intent": round(demand_intent, 1),
        "engagement": round(engagement, 1),
        "willingness_to_pay": round(willingness_to_pay, 1),
        "geo_confidence": round(geo_confidence, 1),
        "recency": round(recency, 1),
    }

    signal_strength = round(sum(dimensions[key] * weight for key, weight in WEIGHTS.items()), 1)
    evidence_conf = count / (count + _EVIDENCE_K)
    spread_conf = spread_count / (spread_count + _SPREAD_K)
    confidence_factor = round(0.6 * evidence_conf + 0.4 * spread_conf, 3)
    adjusted = round(signal_strength * confidence_factor, 1)

    return {
        "dimensions": dimensions,
        "signal_strength": signal_strength,
        "confidence": confidence_factor,
        "adjusted_score": adjusted,
        "sufficiency": sufficiency_label(count, spread_count),
        "evidence_count": count,
        "subreddit_count": spread_count,
        "band": {"cautious": adjusted, "optimistic": signal_strength},
    }


def recommendation(scores: dict[str, Any]) -> str:
    """Plain-language inventory stance, honest about evidence sufficiency."""

    sufficiency = scores.get("sufficiency", "insufficient")
    adjusted = scores.get("adjusted_score", 0.0)
    if sufficiency == "insufficient":
        return "Sample is too thin to call. Collect more evidence before any stocking decision."
    if adjusted >= 55 and sufficiency in {"supported", "strong"}:
        return "Demand looks real and well-evidenced. Worth deeper validation or a small stocking test."
    if adjusted >= 30:
        return "Directional demand signal. Keep tracking and validate before stocking."
    return "Weak signal on current evidence. Do not stock on this alone."
