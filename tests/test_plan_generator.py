"""Tests for the goal-driven plan generator (Week 1, Inspectable Plans).

Run:  python3 -m unittest discover -s tests -v
Every test asserts the InspectablePlan contract: a plan a human can
approve or reject in under a minute, with no black-box step.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plan_generator import detect_intents, human_review_summary, make_plan, validate_plan


class TestIntents(unittest.TestCase):
    def test_summarise_and_send_both_detected(self):
        self.assertEqual(
            detect_intents("Summarise this paper and email the summary to me"),
            ["summarise", "send"],
        )

    def test_unknown_goal_has_no_intent(self):
        self.assertEqual(detect_intents("Water the plants on the balcony"), [])


class TestMakePlan(unittest.TestCase):
    def test_example_goal_produces_valid_plan(self):
        plan = make_plan("Summarise this paper and email the summary to me")
        self.assertEqual(validate_plan(plan), [])

    def test_every_step_explains_itself(self):
        plan = make_plan("Compare the two drafts and send the better one to me")
        for step in plan["steps"]:
            self.assertTrue(step["why"].strip(), step["id"])
            self.assertGreaterEqual(len(step["alternatives_considered"]), 1, step["id"])
            self.assertGreaterEqual(len(step["failure_points"]), 1, step["id"])

    def test_send_steps_need_permission(self):
        plan = make_plan("Summarise this paper and email the summary to me")
        send_steps = [s for s in plan["steps"] if "Send the approved message" in s["action"]]
        self.assertEqual(len(send_steps), 1)
        self.assertTrue(send_steps[0]["needs_permission"])

    def test_unknown_goal_still_valid(self):
        plan = make_plan("Water the plants on the balcony")
        self.assertEqual(validate_plan(plan), [])
        self.assertEqual(plan["human_decision"]["status"], "pending")

    def test_empty_goal_rejected(self):
        with self.assertRaises(ValueError):
            make_plan("   ")

    def test_step_ids_unique(self):
        plan = make_plan("Find the paper, summarise it, and email it to me")
        ids = [s["id"] for s in plan["steps"]]
        self.assertEqual(len(ids), len(set(ids)))


class TestValidatePlan(unittest.TestCase):
    def test_catches_missing_why(self):
        plan = make_plan("Summarise this paper")
        plan["steps"][0]["why"] = "  "
        self.assertTrue(any("why" in p for p in validate_plan(plan)))

    def test_catches_missing_alternative(self):
        plan = make_plan("Summarise this paper")
        plan["steps"][0]["alternatives_considered"] = []
        self.assertTrue(any("alternative" in p for p in validate_plan(plan)))

    def test_catches_bad_decision_status(self):
        plan = make_plan("Summarise this paper")
        plan["human_decision"]["status"] = "maybe"
        self.assertTrue(any("human_decision" in p for p in validate_plan(plan)))


class TestReviewSummary(unittest.TestCase):
    def test_summary_names_goal_steps_and_decision(self):
        plan = make_plan("Summarise this paper and email the summary to me")
        summary = human_review_summary(plan)
        self.assertIn("Summarise this paper", summary)
        self.assertIn("needs permission", summary)
        self.assertIn("Decision: pending", summary)


if __name__ == "__main__":
    unittest.main()
