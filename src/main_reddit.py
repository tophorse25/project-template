from collectors.reddit_collector import RedditCollector
from storage.json_writer import write_jsonl


def main() -> None:
    collector = RedditCollector()

    queries = [
        "cold brew coffee maker",
        "coffee maker hard to clean",
        "coffee maker leaking",
    ]

    subreddits = [
        "Coffee",
        "coldbrew",
        "BuyItForLife",
    ]

    all_records = []

    for subreddit in subreddits:
        for query in queries:
            print(f"Searching r/{subreddit}: {query}")
            records = collector.search_subreddit(
                subreddit_name=subreddit,
                query=query,
                limit=10,
                comment_limit=10,
            )
            all_records.extend(records)

    write_jsonl(
        records=all_records,
        output_path="data/raw/reddit_cold_brew_sample.jsonl",
    )

    print(f"Saved {len(all_records)} records.")


if __name__ == "__main__":
    main()