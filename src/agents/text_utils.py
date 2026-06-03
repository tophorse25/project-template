"""Shared text helpers for the agent layer."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

# Generic stopwords only — never domain words, so product-name similarity stays meaningful.
_STOPWORDS = {"the", "a", "an", "for", "and", "of", "to", "in", "is", "it", "my", "with", "on", "at"}


def normalize_product(product: str) -> str:
    return re.sub(r"\s+", " ", product.strip().lower())


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS and len(token) > 1
    }


def token_set_similarity(left: str, right: str) -> float:
    """Stopword-aware Jaccard over token sets. Cleaner than the reference's keyword overlap."""

    left_tokens, right_tokens = _tokenize(left), _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def subreddit_from_url(url: str) -> str:
    match = re.search(r"/r/([A-Za-z0-9_]+)", url or "")
    return match.group(1) if match else ""


def breakdowns(evidence: Iterable[Any]) -> tuple[dict[str, int], dict[str, int]]:
    """Count non-negated demand(+wtp) and pain labels across a theme's evidence."""

    demand: Counter[str] = Counter()
    pain: Counter[str] = Counter()
    for item in evidence:
        for match in item.matched_signals or []:
            if match.get("negated"):
                continue
            group, label = match.get("group"), match.get("label")
            if group in {"demand", "wtp"}:
                demand[label] += 1
            elif group == "pain":
                pain[label] += 1
    return dict(demand), dict(pain)
