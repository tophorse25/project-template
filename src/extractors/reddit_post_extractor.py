"""Deep-fetch a Reddit post page: full body + top comments.

This is the depth half of the data strategy — visiting individual posts yields the
body and comment text that search cards lack, which is where most pain/demand language
actually lives. Best-effort against Reddit's ``shreddit-*`` components; every field is
optional and defaults to empty/None rather than being fabricated.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from extractors.reddit_extractor import parse_count, parse_timestamp, subreddit_from


def extract_post_detail(page: Page) -> dict[str, Any]:
    """Read body text and metrics from a single open post page."""

    detail: dict[str, Any] = {"body": "", "score": None, "comment_count": None, "created_utc": None, "subreddit": ""}
    post = page.locator("shreddit-post").first
    try:
        detail["score"] = parse_count(post.get_attribute("score"))
        detail["comment_count"] = parse_count(post.get_attribute("comment-count"))
        detail["created_utc"] = parse_timestamp(post.get_attribute("created-timestamp"))
        detail["subreddit"] = subreddit_from(post.get_attribute("subreddit-prefixed-name"), "")
    except Exception:
        pass

    for selector in ("shreddit-post [slot='text-body']", "shreddit-post [slot='post-rtjson-content']"):
        try:
            element = page.locator(selector).first
            if element.count():
                detail["body"] = element.inner_text(timeout=2_000).strip()
                if detail["body"]:
                    break
        except Exception:
            continue
    return detail


def extract_top_comments(page: Page, limit: int = 10) -> list[dict[str, Any]]:
    """Read up to ``limit`` top-level comment bodies from an open post page."""

    comments: list[dict[str, Any]] = []
    nodes = page.locator("shreddit-comment")
    try:
        total = nodes.count()
    except Exception:
        return comments

    for index in range(min(total, limit)):
        node = nodes.nth(index)
        try:
            comment_id = node.get_attribute("thingid") or node.get_attribute("comment-id")
            author = node.get_attribute("author")
            score = parse_count(node.get_attribute("score"))
            body_node = node.locator("[slot='comment']").first
            body = body_node.inner_text(timeout=2_000).strip() if body_node.count() else ""
        except Exception:
            continue
        if body:
            comments.append({"comment_id": comment_id, "author": author, "score": score, "body": body})
    return comments


def deep_fetch_records(
    session: Any,
    post_records: list[dict[str, Any]],
    limit: int,
    comment_limit: int = 10,
    wait_ms: int = 3_000,
) -> list[dict[str, Any]]:
    """Visit the top ``limit`` post records, enrich each, and emit comment records.

    ``session`` is a ``BrowserSession``. Returns the new comment records discovered;
    the passed-in post records are enriched in place (body/score/comment_count).
    """

    new_records: list[dict[str, Any]] = []
    targets = [r for r in post_records if r.get("source_type", "post") == "post"][:limit]

    for record in targets:
        url = record.get("url")
        if not url:
            continue
        try:
            session.goto(url)
            if session.page is not None:
                session.page.wait_for_timeout(wait_ms)
                detail = extract_post_detail(session.page)
                if detail.get("body") and not record.get("body"):
                    record["body"] = detail["body"]
                for key in ("score", "comment_count", "created_utc", "subreddit"):
                    if record.get(key) in (None, "") and detail.get(key) not in (None, ""):
                        record[key] = detail[key]

                for comment in extract_top_comments(session.page, comment_limit):
                    comment_url = f"{url.rstrip('/')}/comment/{comment['comment_id']}/" if comment.get("comment_id") else url
                    new_records.append(
                        {
                            "platform": "reddit",
                            "source": "deep",
                            "source_type": "comment",
                            "query": record.get("query", ""),
                            "subreddit": record.get("subreddit", ""),
                            "post_id": record.get("post_id"),
                            "comment_id": comment.get("comment_id"),
                            "url": comment_url,
                            "title": "",
                            "body": comment["body"],
                            "score": comment.get("score"),
                            "comment_count": 0,
                            "created_utc": record.get("created_utc"),
                        }
                    )
        except Exception as exc:  # best-effort: one bad post must not kill the crawl
            print(f"Deep-fetch failed for {url}: {type(exc).__name__}: {exc}")
            continue

    return new_records
