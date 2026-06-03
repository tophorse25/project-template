import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from agents.change_detection import ChangeDetectionAgent
from agents.pool_manager import PoolManager, theme_id_for
from pipeline.runner import run_cycle
from store.knowledge_base import KnowledgeBase
from store.models import ThemeStatus

PRODUCT = "cold brew coffee maker"
NOW = "2026-06-02T00:00:00+00:00"
NOW_EPOCH = 1780358400.0


def record(rid, subreddit, title, body, score=20, comments=10, created=1780000000.0, source_type="post"):
    return {
        "platform": "reddit",
        "source": "browser",
        "source_type": source_type,
        "query": "q",
        "subreddit": subreddit,
        "post_id": rid,
        "comment_id": None,
        "url": f"https://www.reddit.com/r/{subreddit}/comments/{rid}/x/",
        "title": title,
        "body": body,
        "score": score,
        "comment_count": comments,
        "created_utc": created,
    }


def purchase_records(n, subreddits=("coldbrew", "Coffee")):
    return [
        record(
            f"p{i}",
            subreddits[i % len(subreddits)],
            "Best cold brew maker to buy?",
            "Looking to buy the best one, is it worth it?",
            score=60,
            comments=30,
        )
        for i in range(n)
    ]


class PipelineTests(unittest.TestCase):
    def test_end_to_end_creates_themes_and_research(self) -> None:
        records = [
            record("a1", "coldbrew", "My cold brew maker keeps leaking", "It leaks every time, so frustrating."),
            record("a2", "coldbrew", "Two years in, no problems", "Mine has never leaked and there is no mold at all."),
            *purchase_records(4),
        ]
        kb = KnowledgeBase(":memory:")
        result = run_cycle(kb, records, PRODUCT, now=NOW, now_epoch=NOW_EPOCH)

        self.assertGreater(len(result["themes"]), 0)
        self.assertEqual(kb.counts()["evidence"], 6)

        # Negation: the "never leaked" post must not land in the leaking theme.
        leaking = kb.get_theme(theme_id_for(PRODUCT, "pain:leaking"))
        self.assertIsNotNone(leaking)
        self.assertEqual(leaking.evidence_count, 1)

        # Thin data is never validated.
        self.assertFalse(any(t.status == ThemeStatus.VALIDATED for t in kb.list_themes()))

    def test_accumulation_does_not_duplicate(self) -> None:
        records = purchase_records(4)
        kb = KnowledgeBase(":memory:")
        run_cycle(kb, records, PRODUCT, now=NOW, now_epoch=NOW_EPOCH)
        first = kb.counts()
        run_cycle(kb, records, PRODUCT, now="2026-06-03T00:00:00+00:00", now_epoch=NOW_EPOCH + 86400)
        second = kb.counts()

        self.assertEqual(first["evidence"], second["evidence"])
        self.assertEqual(first["themes"], second["themes"])
        self.assertEqual(first["theme_evidence"], second["theme_evidence"])

    def test_two_cycles_log_two_pipeline_runs_same_second(self) -> None:
        kb = KnowledgeBase(":memory:")
        # Identical timestamps on purpose: the run id must not collide.
        run_cycle(kb, purchase_records(3), PRODUCT, now=NOW, now_epoch=NOW_EPOCH)
        run_cycle(kb, purchase_records(3), PRODUCT, now=NOW, now_epoch=NOW_EPOCH)
        self.assertEqual(kb.counts()["pipeline_runs"], 2)

    def test_deterministic_theme_id_accumulates(self) -> None:
        self.assertEqual(
            theme_id_for(PRODUCT, "pain:leaking"),
            theme_id_for("Cold Brew Coffee Maker", "pain:leaking"),
        )

    def test_merge_near_duplicates_collapses_product_wording(self) -> None:
        kb = KnowledgeBase(":memory:")
        run_cycle(kb, purchase_records(3, ("coldbrew",)), "cold brew coffee maker", now=NOW, now_epoch=NOW_EPOCH)
        run_cycle(kb, purchase_records(3, ("Coffee",)), "cold brew maker", now=NOW, now_epoch=NOW_EPOCH)

        before = len(kb.list_themes())
        merged = PoolManager(kb).merge_near_duplicates()
        after_active = [t for t in kb.list_themes() if t.status != ThemeStatus.ARCHIVED]
        self.assertTrue(merged)
        self.assertLess(len(after_active), before)

    def test_change_detection_reopens_on_new_evidence(self) -> None:
        kb = KnowledgeBase(":memory:")
        # Cycle 1: enough accumulated evidence (9 items, 3 subreddits) to queue + research.
        run_cycle(
            kb,
            purchase_records(9, ("coldbrew", "Coffee", "espresso")),
            PRODUCT,
            now=NOW,
            now_epoch=NOW_EPOCH,
        )
        theme_id = theme_id_for(PRODUCT, "demand:purchase_intent")
        self.assertTrue(kb.list_research_runs(theme_id))  # was researched

        # Cycle 2: two brand-new evidence items for the same theme.
        more = [
            record(f"new{i}", "barista", "Where to buy the best cold brew maker?", "About to buy one, worth it?")
            for i in range(2)
        ]
        result = run_cycle(kb, more, PRODUCT, now="2026-06-05T00:00:00+00:00", now_epoch=NOW_EPOCH + 3 * 86400)

        reopened_ids = {t.theme_id for t in result["reopened"]}
        self.assertIn(theme_id, reopened_ids)


if __name__ == "__main__":
    unittest.main()
