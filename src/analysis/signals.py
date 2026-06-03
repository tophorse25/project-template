"""Deterministic signal detection for Reddit product-research text.

Hardened over the original substring matcher:
- **Word-boundary regex** instead of fragile substrings (no more ``"us "`` traps).
- **Negation handling**: a term preceded by a negator within a short window
  ("no mold", "never leaked", "doesn't break") is *not* counted as a positive signal.
- **Per-label confidence** (distinct terms matched x source weight; title > body).
- **Provenance**: every match records which terms fired, where, and whether negated.
- **Versioned taxonomy** (``TAXONOMY_VERSION``) so stored labels remain auditable.

Backward compatibility: ``detect_demand_signals`` / ``detect_pain_points`` /
``detect_location_clues`` keep their original list-returning signatures so existing
report code and tests continue to work — now with the hardened matching underneath.
"""

from __future__ import annotations

import re
from typing import Any

from analysis.geo import detect_regions

TAXONOMY_VERSION = "2026.06.02"

DEMAND_PATTERNS: dict[str, list[str]] = {
    "purchase_intent": [
        "buy", "bought", "buying", "purchase", "purchasing", "looking for",
        "looking to buy", "where can i find", "where to buy", "want to buy",
        "in the market for", "pull the trigger", "about to buy", "best", "recommend",
        "recommendation", "recommendations",
    ],
    "comparison": ["vs", "versus", "better than", "alternative", "alternatives", "compare", "comparing", "which one"],
    "availability": ["in stock", "available", "availability", "ships", "ship", "shipping", "delivery", "restock", "sold out"],
}

PAIN_PATTERNS: dict[str, list[str]] = {
    "hard_to_clean": ["hard to clean", "difficult to clean", "pain to clean", "mold", "mould", "residue", "gunk", "crevices", "scrub"],
    "leaking": ["leak", "leaks", "leaking", "leaked", "dripping", "drips"],
    "quality_issue": ["broke", "broken", "break", "cracked", "crack", "flimsy", "fell apart", "durable", "durability", "build quality", "quality"],
    "price_sensitive": ["expensive", "overpriced", "too much", "price", "pricey", "cost", "budget", "cheap", "waste of money"],
    "taste_or_performance": ["bitter", "weak", "watery", "sediment", "grit", "gritty", "sour", "slow", "clog", "clogs"],
}

# A separate group: positive willingness-to-pay / monetization signal.
WILLINGNESS_TO_PAY_PATTERNS: dict[str, list[str]] = {
    "willingness_to_pay": ["worth it", "worth the", "would pay", "happily pay", "happy to pay", "pay more", "invest in", "splurge", "treat myself"],
}

_GROUPS: tuple[tuple[str, dict[str, list[str]]], ...] = (
    ("demand", DEMAND_PATTERNS),
    ("pain", PAIN_PATTERNS),
    ("wtp", WILLINGNESS_TO_PAY_PATTERNS),
)

# Human-readable labels for each ``group:label`` category key. Used to name themes
# and section reports consistently across the engine.
CATEGORY_LABELS: dict[str, str] = {
    "demand:purchase_intent": "Purchase intent",
    "demand:comparison": "Product comparison",
    "demand:availability": "Availability & shipping",
    "wtp:willingness_to_pay": "Willingness to pay",
    "pain:leaking": "Leaking complaints",
    "pain:hard_to_clean": "Cleaning difficulty",
    "pain:quality_issue": "Durability / quality issues",
    "pain:price_sensitive": "Price sensitivity",
    "pain:taste_or_performance": "Taste / performance issues",
}


def category_label(category: str) -> str:
    """Human label for a ``group:label`` category key (falls back to the raw key)."""

    return CATEGORY_LABELS.get(category, category.replace("_", " ").replace(":", ": "))

NEGATORS = {
    # plain negation
    "not", "no", "never", "without", "hardly", "barely", "cant", "cannot", "dont",
    "doesnt", "didnt", "isnt", "arent", "wasnt", "werent", "wont", "hasnt", "havent",
    "none", "nor", "neither",
    # resolution: a complaint that was fixed is not an *active* pain signal
    "fixed", "solved", "resolved", "stopped",
}

_NEGATION_WINDOW = 3


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _term_regex(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def _is_negated(text: str, start: int) -> bool:
    prefix = text[:start].lower()
    tokens = re.findall(r"[a-z']+", prefix)
    window = [token.replace("'", "") for token in tokens[-_NEGATION_WINDOW:]]
    return any(token in NEGATORS for token in window)


def extract_signals(title: str, body: str, subreddit: str = "") -> dict[str, Any]:
    """Full structured extraction with provenance and confidence.

    Returns demand/pain/willingness-to-pay labels (negation-aware), geo hints, a
    list of provenance ``matches``, and per-label ``confidence``.
    """

    sources = {"title": normalize_text(title), "body": normalize_text(body)}
    labels: dict[str, set[str]] = {"demand": set(), "pain": set(), "wtp": set()}
    confidence: dict[str, float] = {}
    matches: list[dict[str, Any]] = []

    for group, patterns in _GROUPS:
        for label, terms in patterns.items():
            hits: list[dict[str, Any]] = []
            for source, text in sources.items():
                if not text:
                    continue
                for term in terms:
                    for match in _term_regex(term).finditer(text):
                        hits.append(
                            {"term": term, "source": source, "negated": _is_negated(text, match.start())}
                        )
            if not hits:
                continue

            positive_terms = sorted({hit["term"] for hit in hits if not hit["negated"]})
            in_title = any(hit["source"] == "title" and not hit["negated"] for hit in hits)
            is_positive = bool(positive_terms)

            if is_positive:
                labels[group].add(label)
                confidence[f"{group}:{label}"] = round(
                    min(0.4 + 0.18 * len(positive_terms) + (0.15 if in_title else 0.0), 0.97), 2
                )

            matches.append(
                {
                    "group": group,
                    "label": label,
                    "terms": sorted({hit["term"] for hit in hits}),
                    "source": "title" if in_title else "body",
                    "negated": not is_positive,
                }
            )

    return {
        "demand_signals": sorted(labels["demand"]),
        "pain_points": sorted(labels["pain"]),
        "willingness_to_pay": sorted(labels["wtp"]),
        "geo_hints": detect_regions(f"{title} {body}", subreddit),
        "matches": matches,
        "confidence": confidence,
        "taxonomy_version": TAXONOMY_VERSION,
    }


# ----------------------------------------------------------- backward-compatible API

def detect_demand_signals(text: str) -> list[str]:
    return extract_signals("", text)["demand_signals"]


def detect_pain_points(text: str) -> list[str]:
    return extract_signals("", text)["pain_points"]


def detect_willingness_to_pay(text: str) -> list[str]:
    return extract_signals("", text)["willingness_to_pay"]


def detect_location_clues(text: str) -> list[str]:
    return detect_regions(text)
