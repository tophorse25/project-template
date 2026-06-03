import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from extractors.reddit_extractor import normalize_card, parse_count, parse_timestamp, subreddit_from


class ParseHelpersTests(unittest.TestCase):
    def test_parse_count_handles_reddit_formats(self) -> None:
        self.assertEqual(parse_count(1234), 1234)
        self.assertEqual(parse_count("1,234"), 1234)
        self.assertEqual(parse_count("1.2k"), 1200)
        self.assertEqual(parse_count("3m"), 3_000_000)
        self.assertEqual(parse_count("42"), 42)
        self.assertIsNone(parse_count(""))
        self.assertIsNone(parse_count(None))
        self.assertIsNone(parse_count("n/a"))

    def test_parse_timestamp_iso_and_epoch(self) -> None:
        expected = datetime(2026, 6, 1, tzinfo=UTC).timestamp()
        self.assertEqual(parse_timestamp("2026-06-01T00:00:00+00:00"), expected)
        self.assertEqual(parse_timestamp("2026-06-01T00:00:00Z"), expected)
        self.assertEqual(parse_timestamp(1780000000), 1780000000.0)
        self.assertEqual(parse_timestamp(1780000000000), 1780000000.0)  # ms -> s
        self.assertIsNone(parse_timestamp(""))
        self.assertIsNone(parse_timestamp(None))

    def test_subreddit_from(self) -> None:
        self.assertEqual(subreddit_from("r/coldbrew", ""), "coldbrew")
        self.assertEqual(subreddit_from(None, "https://www.reddit.com/r/Coffee/comments/x/"), "Coffee")
        self.assertEqual(subreddit_from(None, "https://example.com/no-subreddit"), "")


class NormalizeCardTests(unittest.TestCase):
    def test_rich_card_is_normalized(self) -> None:
        raw = {
            "permalink": "/r/coldbrew/comments/abc/best_maker/",
            "post-title": "Best cold brew maker?",
            "subreddit-prefixed-name": "r/coldbrew",
            "score": "1.2k",
            "comment-count": "64",
            "created-timestamp": "2026-06-01T00:00:00+00:00",
            "post_id": "t3_abc",
        }
        record = normalize_card(raw, query="cold brew maker")
        self.assertEqual(record["url"], "https://www.reddit.com/r/coldbrew/comments/abc/best_maker/")
        self.assertEqual(record["subreddit"], "coldbrew")
        self.assertEqual(record["title"], "Best cold brew maker?")
        self.assertEqual(record["score"], 1200)
        self.assertEqual(record["comment_count"], 64)
        self.assertEqual(record["source_type"], "post")

    def test_missing_fields_are_none_not_invented(self) -> None:
        record = normalize_card({"url": "https://www.reddit.com/r/Coffee/comments/x/y/", "title": "Hi"}, "q")
        self.assertIsNone(record["score"])
        self.assertIsNone(record["comment_count"])
        self.assertIsNone(record["created_utc"])
        self.assertEqual(record["subreddit"], "Coffee")

    def test_comment_permalink_is_typed_as_comment(self) -> None:
        record = normalize_card(
            {"permalink": "/r/coldbrew/comments/x/y/comment/c1/", "post-title": "re"}, "q"
        )
        self.assertEqual(record["source_type"], "comment")


if __name__ == "__main__":
    unittest.main()
