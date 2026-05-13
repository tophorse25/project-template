from typing import Any

from playwright.sync_api import Page


def extract_visible_reddit_posts(page: Page, query: str, limit: int = 20) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []

    anchors = page.locator("a[href*='/comments/']")
    count = min(anchors.count(), limit * 3)

    seen_urls: set[str] = set()

    for idx in range(count):
        anchor = anchors.nth(idx)

        try:
            href = anchor.get_attribute("href")
            title = anchor.inner_text(timeout=2_000).strip()
        except Exception:
            continue

        if not href or not title:
            continue

        if "/comments/" not in href:
            continue

        if href.startswith("/"):
            url = f"https://www.reddit.com{href}"
        else:
            url = href

        clean_url = url.split("?")[0]

        if clean_url in seen_urls:
            continue

        seen_urls.add(clean_url)

        posts.append(
            {
                "platform": "reddit",
                "source": "browser",
                "query": query,
                "title": title,
                "url": clean_url,
            }
        )

        if len(posts) >= limit:
            break

    return posts