import argparse
from collections.abc import Sequence

from browser.session import BrowserSession
from extractors.reddit_extractor import extract_visible_reddit_posts
from storage.json_writer import write_jsonl
from workflows.reddit_search import build_reddit_search_url


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect visible Reddit search results with a Playwright browser session."
    )
    parser.add_argument(
        "--query",
        default="cold brew coffee maker",
        help="Search query to run on Reddit.",
    )
    parser.add_argument(
        "--sort",
        default="relevance",
        choices=["relevance", "hot", "top", "new", "comments"],
        help="Reddit search sort order.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of unique post records to save.",
    )
    parser.add_argument(
        "--output",
        default="data/raw/reddit_browser_posts.jsonl",
        help="JSONL output path.",
    )
    parser.add_argument(
        "--screenshot",
        default="data/raw/reddit_search_debug.png",
        help="Debug screenshot path. Use an empty string to skip.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a visible browser window.",
    )
    parser.add_argument(
        "--slow-mo-ms",
        type=int,
        default=200,
        help="Delay Playwright actions by this many milliseconds.",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=5_000,
        help="Additional wait time after page load before extraction.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    search_url = build_reddit_search_url(query=args.query, sort=args.sort)

    with BrowserSession(headless=args.headless, slow_mo_ms=args.slow_mo_ms) as session:
        session.goto(search_url)
        print(f"Page title: {session.title()}")

        if session.page is None:
            raise RuntimeError("Browser page was not initialized.")

        session.page.wait_for_timeout(args.wait_ms)

        if args.screenshot:
            session.screenshot(args.screenshot)

        posts = extract_visible_reddit_posts(
            page=session.page,
            query=args.query,
            limit=args.limit,
        )

    write_jsonl(
        records=posts,
        output_path=args.output,
    )

    print(f"Saved {len(posts)} Reddit post records.")


if __name__ == "__main__":
    main()
