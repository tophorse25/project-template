from __future__ import annotations

import re

DEMAND_PATTERNS = {
    "purchase_intent": [
        "buy",
        "bought",
        "purchase",
        "worth it",
        "looking for",
        "recommend",
        "recommendation",
        "best",
        "where can i find",
    ],
    "comparison": [
        "vs",
        "better than",
        "alternative",
        "compare",
        "which one",
    ],
    "availability": [
        "in stock",
        "available",
        "shipping",
        "ship",
        "delivery",
    ],
}

PAIN_PATTERNS = {
    "hard_to_clean": ["hard to clean", "cleaning", "mold", "residue"],
    "leaking": ["leak", "leaking", "drip"],
    "quality_issue": ["broken", "break", "cheap", "durable", "quality"],
    "price_sensitive": ["expensive", "price", "cost", "budget", "cheap"],
    "taste_or_performance": ["bitter", "weak", "filter", "sediment", "slow"],
}

LOCATION_PATTERNS = {
    "United States": ["united states", "usa", "u.s.", "us ", "california", "texas", "new york"],
    "Canada": ["canada", "toronto", "vancouver"],
    "United Kingdom": ["united kingdom", "uk ", "london"],
    "European Union": ["europe", "eu ", "germany", "france", "italy", "spain"],
    "Australia": ["australia", "sydney", "melbourne"],
    "India": ["india", "delhi", "mumbai", "bangalore"],
    "Japan": ["japan", "tokyo"],
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def detect_labels(text: str, patterns: dict[str, list[str]]) -> list[str]:
    normalized = normalize_text(text)
    labels: list[str] = []

    for label, terms in patterns.items():
        if any(term in normalized for term in terms):
            labels.append(label)

    return labels


def detect_demand_signals(text: str) -> list[str]:
    return detect_labels(text, DEMAND_PATTERNS)


def detect_pain_points(text: str) -> list[str]:
    return detect_labels(text, PAIN_PATTERNS)


def detect_location_clues(text: str) -> list[str]:
    return detect_labels(text, LOCATION_PATTERNS)
