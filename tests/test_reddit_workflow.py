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
from workflows.crawl_log import CrawlRunLog, QueryRunResult, default_crawl_log_path, write_crawl_log
from workflows.job_config import load_reddit_crawl_job
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
                "--config",
                "configs/cold_brew_reddit.json",
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

        self.assertEqual(args.config, "configs/cold_brew_reddit.json")
        self.assertEqual(args.query, "cold brew filter")
        self.assertEqual(args.sort, "top")
        self.assertEqual(args.limit, 5)
        self.assertEqual(args.output, "data/raw/test.jsonl")
        self.assertEqual(args.screenshot, "")
        self.assertTrue(args.headless)
        self.assertEqual(args.slow_mo_ms, 0)
        self.assertEqual(args.wait_ms, 100)
        self.assertFalse(args.fail_fast)

    def test_load_reddit_crawl_job_reads_adjustable_config(self) -> None:
        job = load_reddit_crawl_job("configs/cold_brew_reddit.json")

        self.assertEqual(job.product, "cold brew coffee maker")
        self.assertIn("best cold brew maker", job.queries)
        self.assertEqual(job.limit_per_query, 20)
        self.assertEqual(job.output_path, "data/raw/cold_brew_reddit_browser.jsonl")
        self.assertEqual(job.run_log_path, "log/crawl-runs/cold_brew_reddit.json")

    def test_write_crawl_log_saves_success_and_error_metadata(self) -> None:
        run_log = CrawlRunLog(
            product="cold brew maker",
            output_path="data/raw/sample.jsonl",
            total_queries=2,
            successful_queries=1,
            failed_queries=1,
            total_records=3,
            started_at="2026-05-26T00:00:00+00:00",
            completed_at="2026-05-26T00:01:00+00:00",
            query_results=[
                QueryRunResult(
                    query="best cold brew maker",
                    status="success",
                    records_collected=3,
                    started_at="2026-05-26T00:00:00+00:00",
                    completed_at="2026-05-26T00:00:30+00:00",
                ),
                QueryRunResult(
                    query="cold brew maker failed query",
                    status="failed",
                    records_collected=0,
                    started_at="2026-05-26T00:00:30+00:00",
                    completed_at="2026-05-26T00:01:00+00:00",
                    error="TimeoutError: page load timed out",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "logs" / "crawl.json"
            write_crawl_log(run_log, str(output_path))
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["successful_queries"], 1)
        self.assertEqual(saved["failed_queries"], 1)
        self.assertEqual(saved["query_results"][1]["error"], "TimeoutError: page load timed out")

    def test_default_crawl_log_path_uses_output_stem_and_timestamp(self) -> None:
        path = default_crawl_log_path(
            output_path="data/raw/cold_brew.jsonl",
            completed_at="2026-05-26T00:01:00+00:00",
        )

        self.assertEqual(path, "log\\crawl-runs\\cold_brew-2026-05-26T000100Z0000.json")


if __name__ == "__main__":
    unittest.main()
