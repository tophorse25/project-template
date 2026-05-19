import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from main_reddit_browser import parse_args
from storage.json_writer import write_jsonl
from workflows.reddit_search import build_reddit_search_url


class RedditWorkflowTests(unittest.TestCase):
    def test_build_reddit_search_url_encodes_query_and_sort(self) -> None:
        url = build_reddit_search_url(query="coffee maker leaking", sort="new")

        self.assertEqual(
            url,
            "https://www.reddit.com/search/?q=coffee+maker+leaking&sort=new",
        )

    def test_write_jsonl_creates_parent_directory_and_writes_records(self) -> None:
        records = [
            {"platform": "reddit", "title": "First"},
            {"platform": "reddit", "title": "Second"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "records.jsonl"
            write_jsonl(records=records, output_path=str(output_path))

            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual([json.loads(line) for line in lines], records)

    def test_parse_args_accepts_browser_workflow_options(self) -> None:
        args = parse_args(
            [
                "--query",
                "cold brew filter",
                "--sort",
                "top",
                "--limit",
                "5",
                "--output",
                "data/raw/test.jsonl",
                "--screenshot",
                "",
                "--headless",
                "--slow-mo-ms",
                "0",
                "--wait-ms",
                "100",
            ]
        )

        self.assertEqual(args.query, "cold brew filter")
        self.assertEqual(args.sort, "top")
        self.assertEqual(args.limit, 5)
        self.assertEqual(args.output, "data/raw/test.jsonl")
        self.assertEqual(args.screenshot, "")
        self.assertTrue(args.headless)
        self.assertEqual(args.slow_mo_ms, 0)
        self.assertEqual(args.wait_ms, 100)


if __name__ == "__main__":
    unittest.main()
