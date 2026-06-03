"""Extract rich records from Reddit search results.

Upgraded from title+URL only to capture subreddit, score, comment count, post age,
and a body snippet from each result card. Extraction is **defensive**: it reads
``shreddit-post`` web-component attributes when present and falls back to the anchor
scan otherwise. Missing fields are ``None`` — never invented — so downstream scoring
stays honest.

The parsing helpers (``parse_count`` / ``parse_timestamp`` / ``normalize_card``) are
pure and unit-tested; the Playwright DOM reading is best-effort against a volatile UI.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from playwright.sync_api import Page


def parse_count(value: Any) -> int | None:
    """Parse Reddit-style counts: 1234, '1,234', '1.2k', '3m'. Returns None if unknown."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower().replace(",", "")
    if not text:
        return None
    match = re.match(r"^([0-9]*\.?[0-9]+)\s*([km]?)$", text)
    if match:
        number = float(match.group(1))
        multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2)]
        return int(number * multiplier)
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else None


def parse_timestamp(value: Any) -> float | None:
    """Parse an ISO-8601 string or epoch (s/ms) into epoch seconds. None if unknown."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 1000.0 if number > 1e12 else number
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        if text.isdigit():
            number = float(text)
            return number / 1000.0 if number > 1e12 else number
        return None


def subreddit_from(prefixed: str | None, url: str) -> str:
    if prefixed:
        return re.sub(r"^/?r/", "", str(prefixed)).strip()
    match = re.search(r"/r/([A-Za-z0-9_]+)", url or "")
    return match.group(1) if match else ""


def normalize_card(raw: dict[str, Any], query: str) -> dict[str, Any]:
    """Turn loosely-shaped attributes into a clean engine record (missing -> None)."""

    url = (raw.get("permalink") or raw.get("url") or "").strip()
    if url.startswith("/"):
        url = f"https://www.reddit.com{url}"
    url = url.split("?")[0].split("#")[0]

    title = (raw.get("post-title") or raw.get("title") or "").strip()
    subreddit = subreddit_from(raw.get("subreddit-prefixed-name"), url)

    return {
        "platform": "reddit",
        "source": "browser",
        "source_type": "comment" if "/comment/" in url else "post",
        "query": query,
        "subreddit": subreddit,
        "post_id": raw.get("post_id"),
        "comment_id": raw.get("comment_id"),
        "url": url,
        "title": title,
        "body": (raw.get("body") or "").strip(),
        "score": parse_count(raw.get("score")),
        "comment_count": parse_count(raw.get("comment-count") or raw.get("comment_count")),
        "created_utc": parse_timestamp(raw.get("created-timestamp") or raw.get("created_utc")),
    }


def _card_posts(page: Page, query: str, limit: int, seen: set[str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    cards = page.locator("shreddit-post")
    try:
        total = cards.count()
    except Exception:
        return posts

    for index in range(min(total, limit * 3)):
        card = cards.nth(index)
        try:
            raw = {
                "permalink": card.get_attribute("permalink"),
                "post-title": card.get_attribute("post-title"),
                "subreddit-prefixed-name": card.get_attribute("subreddit-prefixed-name"),
                "score": card.get_attribute("score"),
                "comment-count": card.get_attribute("comment-count"),
                "created-timestamp": card.get_attribute("created-timestamp"),
                "post_id": card.get_attribute("id"),
            }
        except Exception:
            continue

        record = normalize_card(raw, query)
        if not record["url"] or not record["title"]:
            continue
        if record["url"] in seen:
            continue
        seen.add(record["url"])
        posts.append(record)
        if len(posts) >= limit:
            break
    return posts


def _anchor_posts(page: Page, query: str, limit: int, seen: set[str]) -> list[dict[str, Any]]:
    """Fallback: scan comment-thread anchors (also catches comment permalinks)."""

    posts: list[dict[str, Any]] = []
    anchors = page.locator("a[href*='/comments/']")
    try:
        total = anchors.count()
    except Exception:
        return posts

    for index in range(min(total, limit * 3)):
        anchor = anchors.nth(index)
        try:
            href = anchor.get_attribute("href")
            title = anchor.inner_text(timeout=2_000).strip()
        except Exception:
            continue
        if not href or not title or "/comments/" not in href:
            continue
        url = href if href.startswith("http") else f"https://www.reddit.com{href}"
        url = url.split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        posts.append(normalize_card({"url": url, "title": title}, query))
        if len(posts) >= limit:
            break
    return posts


def extract_visible_reddit_posts(page: Page, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Collect up to ``limit`` unique result records, richest source first."""

    seen: set[str] = set()
    posts = _card_posts(page, query, limit, seen)
    if len(posts) < limit:
        posts += _anchor_posts(page, query, limit - len(posts), seen)
    return posts[:limit]
