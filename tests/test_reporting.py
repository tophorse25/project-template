import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from agents.report_agent import ReportAgent
from pipeline.runner import run_cycle
from store.knowledge_base import KnowledgeBase

PRODUCT = "cold brew coffee maker"
NOW = "2026-06-02T00:00:00+00:00"
NOW_EPOCH = 1780358400.0


def _record(rid, subreddit, title, body):
    return {
        "platform": "reddit",
        "source": "browser",
        "source_type": "post",
        "query": "q",
        "subreddit": subreddit,
        "post_id": rid,
        "comment_id": None,
        "url": f"https://www.reddit.com/r/{subreddit}/comments/{rid}/x/",
        "title": title,
        "body": body,
        "score": 40,
        "comment_count": 20,
        "created_utc": 1780000000.0,
    }


def _seed_kb() -> KnowledgeBase:
    records = [
        _record("r1", "coldbrew", "Best cold brew maker to buy?", "Looking to buy the best one, is it worth it?"),
        _record("r2", "Coffee", "Cold brew maker keeps leaking", "It leaks every time, frustrating."),
        _record("r3", "IndiaCoffee", "Cold brew maker in India?", "Where to buy one in India, worth it?"),
    ]
    kb = KnowledgeBase(":memory:")
    run_cycle(kb, records, PRODUCT, now=NOW, now_epoch=NOW_EPOCH)
    return kb


class ReportingTests(unittest.TestCase):
    def test_markdown_has_sections_and_evidence_links(self) -> None:
        report = ReportAgent(_seed_kb()).markdown(PRODUCT)
        self.assertIn(f"# Product Demand Report: {PRODUCT}", report)
        self.assertIn("## Demand Themes", report)
        self.assertIn("## Theme Detail", report)
        self.assertIn("## Methodology & Limitations", report)
        self.assertIn("https://www.reddit.com/r/", report)  # evidence link present
        self.assertIn("adjusted", report.lower())

    def test_html_is_self_contained_and_renders_themes(self) -> None:
        html = ReportAgent(_seed_kb()).html(PRODUCT)
        self.assertTrue(html.lstrip().startswith("<!doctype html>"))
        self.assertIn("<style>", html)  # inline CSS, no external assets
        self.assertIn(PRODUCT, html)
        self.assertIn("Purchase intent", html)
        self.assertIn("href=", html)  # evidence links

    def test_write_emits_both_files(self) -> None:
        import tempfile

        kb = _seed_kb()
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "report.md"
            html = Path(tmp) / "report.html"
            written = ReportAgent(kb).write(PRODUCT, str(md), str(html))
            self.assertTrue(md.exists() and html.exists())
            self.assertEqual(set(written), {"markdown", "html"})


if __name__ == "__main__":
    unittest.main()
