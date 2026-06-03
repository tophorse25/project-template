import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from analysis.geo import aggregate_geo, detect_regions
from analysis.scoring import DAY, recommendation, score_theme, sufficiency_label
from analysis.signals import (
    TAXONOMY_VERSION,
    detect_demand_signals,
    detect_pain_points,
    detect_willingness_to_pay,
    extract_signals,
)
from store.models import Evidence


def make_evidence(**overrides) -> Evidence:
    base = dict(
        evidence_id="e",
        platform="reddit",
        source="browser",
        source_type="post",
        subreddit="coldbrew",
        post_id=None,
        comment_id=None,
        url="https://example.com",
        title="",
        body="",
        score=0,
        comment_count=0,
        created_utc=1780000000.0,
        query="q",
        first_seen="t",
        last_seen="t",
        fetched_at="t",
        matched_signals=[],
        geo_hints=[],
    )
    base.update(overrides)
    return Evidence(**base)


def signal(group: str) -> dict:
    return {"group": group, "label": f"{group}_label", "negated": False}


class SignalTests(unittest.TestCase):
    def test_negation_suppresses_false_positives(self) -> None:
        clean = extract_signals("", "Mine has never leaked and there is no mold at all.")
        self.assertNotIn("leaking", clean["pain_points"])
        self.assertNotIn("hard_to_clean", clean["pain_points"])

        dirty = extract_signals("", "It leaks every time and there is mold in the gasket.")
        self.assertIn("leaking", dirty["pain_points"])
        self.assertIn("hard_to_clean", dirty["pain_points"])

    def test_word_boundary_no_false_us(self) -> None:
        # bare "us" must not be read as the United States
        self.assertNotIn("United States", detect_regions("this works for us all"))

    def test_provenance_and_confidence(self) -> None:
        result = extract_signals("Best cold brew maker?", "Looking to buy one, is it worth it?")
        self.assertIn("purchase_intent", result["demand_signals"])
        self.assertIn("willingness_to_pay", result["willingness_to_pay"])
        self.assertEqual(result["taxonomy_version"], TAXONOMY_VERSION)
        self.assertTrue(result["matches"])
        for match in result["matches"]:
            self.assertIn("group", match)
            self.assertIn("label", match)
            self.assertIn("terms", match)
            self.assertIn("negated", match)
        self.assertIn("demand:purchase_intent", result["confidence"])
        # a title hit should score higher than the same label found only in the body
        body_only = extract_signals("", "looking to buy the best one")
        self.assertGreater(
            result["confidence"]["demand:purchase_intent"],
            body_only["confidence"]["demand:purchase_intent"],
        )

    def test_backward_compatible_helpers(self) -> None:
        self.assertIn("purchase_intent", detect_demand_signals("looking to buy the best one"))
        pains = detect_pain_points("every cheap one is hard to clean")
        self.assertIn("price_sensitive", pains)
        self.assertIn("hard_to_clean", pains)
        self.assertIn("willingness_to_pay", detect_willingness_to_pay("honestly it is worth it"))


class GeoTests(unittest.TestCase):
    def test_subreddit_from_url_is_strongest_signal(self) -> None:
        self.assertIn("India", detect_regions("https://www.reddit.com/r/IndiaCoffee/comments/x/"))

    def test_currency_and_subreddit_param(self) -> None:
        self.assertIn("United Kingdom", detect_regions("priced at 40 GBP", "CoffeeUK"))
        self.assertIn("Canada", detect_regions("it costs 40 CAD here"))

    def test_commonwealth_spelling(self) -> None:
        self.assertIn("United Kingdom", detect_regions("Colour me sceptical about the litre size"))

    def test_aggregate_distribution(self) -> None:
        distribution = aggregate_geo([["India"], ["India"], ["United Kingdom"], []])
        top = distribution[0]
        self.assertEqual(top["region"], "India")
        self.assertEqual(top["evidence_count"], 2)
        self.assertEqual(top["confidence"], round(2 / 3, 2))


class ScoringTests(unittest.TestCase):
    def test_thin_data_is_never_validated(self) -> None:
        loud_single = make_evidence(
            score=500,
            comment_count=400,
            matched_signals=[signal("demand"), signal("pain"), signal("wtp")],
            geo_hints=["United States"],
        )
        scores = score_theme([loud_single], now_epoch=1780000000.0)
        self.assertEqual(scores["sufficiency"], "insufficient")
        self.assertLess(scores["confidence"], 0.5)
        self.assertLess(scores["adjusted_score"], scores["signal_strength"])

    def test_accumulated_evidence_raises_confidence(self) -> None:
        evidence = [
            make_evidence(
                evidence_id=f"e{i}",
                subreddit=["coldbrew", "Coffee", "IndiaCoffee"][i % 3],
                score=40,
                comment_count=20,
                matched_signals=[signal("demand"), signal("pain")],
                geo_hints=["India"] if i % 3 == 2 else [],
            )
            for i in range(8)
        ]
        scores = score_theme(evidence, now_epoch=1780000000.0)
        self.assertEqual(scores["sufficiency"], "strong")
        self.assertGreater(scores["confidence"], 0.6)
        self.assertGreater(scores["adjusted_score"], 30)

    def test_velocity_and_recency_use_timestamps(self) -> None:
        now = 1780000000.0 + 100 * DAY
        recent = make_evidence(created_utc=now - 2 * DAY)
        old = make_evidence(created_utc=now - 200 * DAY)
        recent_scores = score_theme([recent], now_epoch=now)
        old_scores = score_theme([old], now_epoch=now)
        self.assertGreater(recent_scores["dimensions"]["recency"], old_scores["dimensions"]["recency"])
        self.assertGreater(recent_scores["dimensions"]["velocity"], old_scores["dimensions"]["velocity"])

    def test_sufficiency_label_thresholds(self) -> None:
        self.assertEqual(sufficiency_label(1, 1), "insufficient")
        self.assertEqual(sufficiency_label(3, 1), "directional")
        self.assertEqual(sufficiency_label(5, 2), "supported")
        self.assertEqual(sufficiency_label(9, 3), "strong")

    def test_recommendation_is_honest_on_thin_data(self) -> None:
        thin = score_theme([make_evidence()], now_epoch=1780000000.0)
        self.assertIn("thin", recommendation(thin).lower())


class HardeningTests(unittest.TestCase):
    def test_uppercase_us_detected_without_lowercase_false_positive(self) -> None:
        self.assertIn("United States", detect_regions("Does it ship to the US quickly?"))
        self.assertIn("United States", detect_regions("Available in the U.S. only"))
        self.assertNotIn("United States", detect_regions("works great for us at home"))

    def test_resolution_words_suppress_active_pain(self) -> None:
        self.assertNotIn("leaking", extract_signals("", "I fixed the leak with a new gasket")["pain_points"])
        self.assertNotIn("leaking", extract_signals("", "it finally stopped leaking")["pain_points"])
        # an unresolved complaint still counts
        self.assertIn("leaking", extract_signals("", "it still leaks every morning")["pain_points"])


if __name__ == "__main__":
    unittest.main()
