"""Geographic inference for Reddit evidence.

Improvements over the reference ``super_crawler`` geo logic:
- The subreddit name is treated as the *strongest* signal (the reference's own
  insight), via a fragment map that also works when the subreddit is embedded in
  a URL (e.g. ``/r/IndiaCoffee/``).
- Word-boundary text matching (no fragile substrings), plus currency symbols/codes
  and Commonwealth spelling variants.
- Output is a confidence-weighted distribution with evidence counts, not a flat list.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

GEO_VERSION = "2026.06.02"

# Subreddit fragment -> region. Matched as a substring of the subreddit name.
SUBREDDIT_FRAGMENTS: dict[str, str] = {
    "india": "India",
    "uk": "United Kingdom",
    "britain": "United Kingdom",
    "canada": "Canada",
    "aus": "Australia",
    "australia": "Australia",
    "europe": "European Union",
    "germany": "European Union",
    "usa": "United States",
    "america": "United States",
    "japan": "Japan",
}

# Region -> word-boundary text terms.
TEXT_PATTERNS: dict[str, list[str]] = {
    "United States": ["usa", "u.s.", "u.s", "united states", "american", "americans", "california", "texas"],
    "United Kingdom": ["uk", "britain", "british", "england", "london", "scotland"],
    "Canada": ["canada", "canadian", "toronto", "vancouver"],
    "European Union": ["europe", "european", "germany", "france", "italy", "spain", "netherlands"],
    "Australia": ["australia", "australian", "aussie", "sydney", "melbourne"],
    "India": ["india", "indian", "delhi", "mumbai", "bangalore", "bengaluru"],
    "Japan": ["japan", "japanese", "tokyo"],
}

# Region -> currency regex fragments (symbols handled literally; codes are word-bounded).
CURRENCY_PATTERNS: dict[str, list[str]] = {
    "United States": [r"\busd\b"],
    "United Kingdom": [r"\bgbp\b", "£"],
    "European Union": [r"\beur\b", "€"],
    "Canada": [r"\bcad\b"],
    "Australia": [r"\baud\b"],
    "India": [r"\binr\b", "₹"],
}

# Commonwealth spelling variants -> a weak United Kingdom signal.
SPELLING_UK = ["colour", "favourite", "litre", "metre", "sceptical", "organisation", "apologise"]


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _term_regex(term: str) -> re.Pattern[str]:
    """Word-boundary regex where the boundary characters are word characters."""

    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def _subreddit_from(text: str, subreddit: str) -> str:
    if subreddit:
        return subreddit.lower()
    match = re.search(r"/?r/([A-Za-z0-9_]+)", text)
    return match.group(1).lower() if match else ""


def detect_regions(text: str, subreddit: str = "") -> list[str]:
    """Return the distinct regions implied by a piece of text (+ optional subreddit)."""

    regions: set[str] = set()
    normalized = _normalize(text)

    sr = _subreddit_from(normalized, subreddit)
    for fragment, region in SUBREDDIT_FRAGMENTS.items():
        if fragment in sr:
            regions.add(region)

    for region, terms in TEXT_PATTERNS.items():
        if any(_term_regex(term).search(normalized) for term in terms):
            regions.add(region)

    for region, patterns in CURRENCY_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            regions.add(region)

    # Case-sensitive standalone "US" / "U.S." (catches "ships to the US") without
    # matching the lowercase pronoun "us".
    if re.search(r"\bUS\b", normalized) or re.search(r"\bU\.S\.?\b", normalized):
        regions.add("United States")

    if any(_term_regex(term).search(normalized) for term in SPELLING_UK):
        regions.add("United Kingdom")

    return sorted(regions)


def aggregate_geo(geo_hint_lists: Iterable[Iterable[str]]) -> list[dict[str, Any]]:
    """Aggregate per-evidence region hints into a confidence-weighted distribution.

    Confidence for a region = share of geo-bearing evidence that mentions it.
    """

    counts: Counter[str] = Counter()
    geo_bearing = 0
    for hints in geo_hint_lists:
        hint_list = [region for region in hints]
        if hint_list:
            geo_bearing += 1
        counts.update(hint_list)

    denominator = max(geo_bearing, 1)
    return [
        {"region": region, "confidence": round(count / denominator, 2), "evidence_count": count}
        for region, count in counts.most_common()
    ]
