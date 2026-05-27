import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from analysis.report import demand_metrics, generate_markdown_report, normalize_reddit_record, top_records
from analysis.signals import detect_demand_signals, detect_location_clues, detect_pain_points
from main_report import parse_args


class ReportWorkflowTests(unittest.TestCase):
    def test_signal_detection_finds_business_relevant_labels(self) -> None:
        text = "Looking for the best cold brew maker in Canada but every cheap one is hard to clean."

        self.assertIn("purchase_intent", detect_demand_signals(text))
        self.assertIn("hard_to_clean", detect_pain_points(text))
        self.assertIn("price_sensitive", detect_pain_points(text))
        self.assertIn("Canada", detect_location_clues(text))

    def test_normalize_reddit_record_supports_browser_records(self) -> None:
        record = {
            "platform": "reddit",
            "source": "browser",
            "query": "cold brew coffee maker",
            "title": "Best cold brew maker for a small kitchen?",
            "url": "https://www.reddit.com/r/IndiaCoffee/example",
        }

        normalized = normalize_reddit_record(record)

        self.assertEqual(normalized["source_type"], "post")
        self.assertEqual(normalized["source"], "browser")
        self.assertEqual(normalized["title"], record["title"])
        self.assertIn("purchase_intent", normalized["demand_signals"])
        self.assertIn("India", normalized["location_clues"])

    def test_normalize_reddit_record_supports_api_comment_records(self) -> None:
        record = {
            "platform": "reddit",
            "query": "coffee maker leaking",
            "subreddit": "Coffee",
            "post_title": "Coffee maker leaking",
            "post_text": "Need a better model",
            "post_url": "https://www.reddit.com/r/Coffee/example",
            "post_score": 42,
            "post_num_comments": 9,
            "comment_id": "abc123",
            "comment_text": "Mine started leaking after one week.",
            "comment_score": 5,
        }

        normalized = normalize_reddit_record(record)

        self.assertEqual(normalized["source"], "api")
        self.assertEqual(normalized["source_type"], "comment")
        self.assertEqual(normalized["score"], 42)
        self.assertIn("leaking", normalized["pain_points"])

    def test_generate_markdown_report_includes_merchant_sections(self) -> None:
        records = [
            {
                "platform": "reddit",
                "source": "browser",
                "query": "cold brew maker",
                "title": "Best cold brew maker in Canada?",
                "url": "https://www.reddit.com/r/coldbrew/example",
            }
        ]

        report = generate_markdown_report(records, product="cold brew maker", evidence_limit=1)

        self.assertIn("# Product Demand Report: cold brew maker", report)
        self.assertIn("## Demand Volume Evidence", report)
        self.assertIn("## Demand Signals", report)
        self.assertIn("## Location Clues", report)
        self.assertIn("## Location Coverage Note", report)
        self.assertIn("## Merchant Takeaway", report)
        self.assertIn("Canada", report)

    def test_demand_metrics_calculates_signal_and_location_rates(self) -> None:
        records = [
            {
                "url": "https://example.com/1",
                "score": 10,
                "comment_count": 3,
                "demand_signals": ["purchase_intent"],
                "pain_points": [],
                "location_clues": ["Canada"],
            },
            {
                "url": "https://example.com/2",
                "score": 5,
                "comment_count": 1,
                "demand_signals": [],
                "pain_points": ["leaking"],
                "location_clues": [],
            },
        ]

        metrics = demand_metrics(records)

        self.assertEqual(metrics["total_records"], 2)
        self.assertEqual(metrics["unique_urls"], 2)
        self.assertEqual(metrics["records_with_signals"], 1)
        self.assertEqual(metrics["records_with_locations"], 1)
        self.assertEqual(metrics["total_score"], 15)
        self.assertEqual(metrics["total_comments"], 4)

    def test_top_records_deduplicates_evidence_urls(self) -> None:
        records = [
            {
                "title": "First",
                "url": "https://example.com/repeated",
                "score": 1,
                "comment_count": 1,
                "demand_signals": ["purchase_intent"],
                "pain_points": [],
            },
            {
                "title": "Duplicate",
                "url": "https://example.com/repeated",
                "score": 1,
                "comment_count": 1,
                "demand_signals": ["purchase_intent"],
                "pain_points": [],
            },
            {
                "title": "Second",
                "url": "https://example.com/second",
                "score": 1,
                "comment_count": 1,
                "demand_signals": [],
                "pain_points": [],
            },
        ]

        selected = top_records(records, limit=3)

        self.assertEqual([record["url"] for record in selected], ["https://example.com/repeated", "https://example.com/second"])

    def test_parse_args_accepts_report_options(self) -> None:
        args = parse_args(
            [
                "--input",
                "data/raw/reddit.jsonl",
                "--config",
                "configs/cold_brew_reddit.json",
                "--product",
                "cold brew maker",
                "--output",
                "reports/cold-brew-maker.md",
                "--evidence-limit",
                "3",
            ]
        )

        self.assertEqual(args.input, "data/raw/reddit.jsonl")
        self.assertEqual(args.config, "configs/cold_brew_reddit.json")
        self.assertEqual(args.product, "cold brew maker")
        self.assertEqual(args.output, "reports/cold-brew-maker.md")
        self.assertEqual(args.evidence_limit, 3)


if __name__ == "__main__":
    unittest.main()
