import argparse
from collections.abc import Sequence

from browser.session import BrowserSession
from extractors.reddit_extractor import extract_visible_reddit_posts
from storage.json_writer import write_jsonl
from workflows.crawl_log import (
    CrawlRunLog,
    QueryRunResult,
    default_crawl_log_path,
    utc_now,
    write_crawl_log,
)
from workflows.job_config import RedditCrawlJob, load_reddit_crawl_job
from workflows.reddit_search import build_reddit_search_url


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect visible Reddit search results with a Playwright browser session."
    )
    parser.add_argument(
        "--config",
        help="Optional JSON crawl config. When set, queries and output path come from the config.",
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
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the crawl on the first query failure.",
    )
    return parser.parse_args(argv)


def job_from_args(args: argparse.Namespace) -> RedditCrawlJob:
    if args.config:
        return load_reddit_crawl_job(args.config)

    return RedditCrawlJob(
        product=args.query,
        queries=[args.query],
        sort=args.sort,
        limit_per_query=args.limit,
        output_path=args.output,
    )


def screenshot_path_for_query(base_path: str, query_index: int, total_queries: int) -> str:
    if not base_path:
        return ""

    if total_queries == 1:
        return base_path

    stem, dot, suffix = base_path.rpartition(".")
    if not dot:
        return f"{base_path}-{query_index + 1}"

    return f"{stem}-{query_index + 1}.{suffix}"


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    job = job_from_args(args)
    all_posts = []
    query_results: list[QueryRunResult] = []
    crawl_started_at = utc_now()

    with BrowserSession(headless=args.headless, slow_mo_ms=args.slow_mo_ms) as session:
        for query_index, query in enumerate(job.queries):
            query_started_at = utc_now()
            search_url = build_reddit_search_url(query=query, sort=job.sort)
            print(f"Searching Reddit for: {query}")

            try:
                session.goto(search_url)
                print(f"Page title: {session.title()}")

                if session.page is None:
                    raise RuntimeError("Browser page was not initialized.")

                session.page.wait_for_timeout(args.wait_ms)

                screenshot_path = screenshot_path_for_query(
                    base_path=args.screenshot,
                    query_index=query_index,
                    total_queries=len(job.queries),
                )
                if screenshot_path:
                    session.screenshot(screenshot_path)

                posts = extract_visible_reddit_posts(
                    page=session.page,
                    query=query,
                    limit=job.limit_per_query,
                )
                all_posts.extend(posts)
                query_results.append(
                    QueryRunResult(
                        query=query,
                        status="success",
                        records_collected=len(posts),
                        started_at=query_started_at,
                        completed_at=utc_now(),
                    )
                )
            except Exception as exc:
                error_message = f"{type(exc).__name__}: {exc}"
                print(f"Query failed: {query} | {error_message}")
                query_results.append(
                    QueryRunResult(
                        query=query,
                        status="failed",
                        records_collected=0,
                        started_at=query_started_at,
                        completed_at=utc_now(),
                        error=error_message,
                    )
                )
                if args.fail_fast:
                    raise

    write_jsonl(
        records=all_posts,
        output_path=job.output_path,
    )

    crawl_completed_at = utc_now()
    successful_queries = sum(1 for result in query_results if result.status == "success")
    run_log = CrawlRunLog(
        product=job.product,
        output_path=job.output_path,
        total_queries=len(job.queries),
        successful_queries=successful_queries,
        failed_queries=len(job.queries) - successful_queries,
        total_records=len(all_posts),
        started_at=crawl_started_at,
        completed_at=crawl_completed_at,
        query_results=query_results,
    )
    run_log_path = job.run_log_path or default_crawl_log_path(job.output_path, crawl_completed_at)
    write_crawl_log(run_log, run_log_path)

    print(f"Saved {len(all_posts)} Reddit post records to {job.output_path}.")
    print(f"Saved crawl run log to {run_log_path}.")


if __name__ == "__main__":
    main()
