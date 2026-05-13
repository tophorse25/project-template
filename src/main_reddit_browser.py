from browser.session import BrowserSession
from extractors.reddit_extractor import extract_visible_reddit_posts
from storage.json_writer import write_jsonl
from workflows.reddit_search import build_reddit_search_url


def main() -> None:
    query = "cold brew coffee maker"
    search_url = build_reddit_search_url(query=query)

    with BrowserSession(headless=False, slow_mo_ms=200) as session:
        session.goto(search_url)
        print(f"Page title: {session.title()}")

        if session.page is None:
            raise RuntimeError("Browser page was not initialized.")

        session.page.wait_for_timeout(5_000)
        session.screenshot("data/raw/reddit_search_debug.png")

        posts = extract_visible_reddit_posts(
            page=session.page,
            query=query,
            limit=20,
        )

    write_jsonl(
        records=posts,
        output_path="data/raw/reddit_browser_posts.jsonl",
    )

    print(f"Saved {len(posts)} Reddit post records.")


if __name__ == "__main__":
    main()