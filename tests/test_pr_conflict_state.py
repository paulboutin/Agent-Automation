import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from agent_factory_profile import resolve_labels, resolve_policy  # noqa: E402
from pr_conflict_state import classify_pr_conflict  # noqa: E402


class ResolveLabelsTest(unittest.TestCase):
    def test_merge_conflict_label_defaults(self) -> None:
        labels = resolve_labels({})
        self.assertEqual(labels["mergeConflict"], "merge-conflict")

    def test_merge_conflict_label_flows_into_policy(self) -> None:
        policy = resolve_policy({"labels": {"mergeConflict": "pr-conflicted"}})
        self.assertEqual(policy["mergeConflictLabel"], "pr-conflicted")


class PrConflictStateTest(unittest.TestCase):
    def test_conflict_when_dirty(self) -> None:
        result = classify_pr_conflict(False, "dirty")
        self.assertEqual(result["classification"], "conflict")
        self.assertTrue(result["has_conflict"])

    def test_clean_when_mergeable(self) -> None:
        result = classify_pr_conflict(True, "clean")
        self.assertEqual(result["classification"], "clean")
        self.assertFalse(result["has_conflict"])

    def test_pending_when_github_has_not_computed_state(self) -> None:
        result = classify_pr_conflict(None, "unknown")
        self.assertEqual(result["classification"], "pending")
        self.assertFalse(result["has_conflict"])

    def test_blocked_non_conflict_state(self) -> None:
        result = classify_pr_conflict(True, "behind")
        self.assertEqual(result["classification"], "blocked")
        self.assertFalse(result["has_conflict"])

    def test_draft_prs_are_not_marked_as_conflicts(self) -> None:
        result = classify_pr_conflict(False, "dirty", draft=True)
        self.assertEqual(result["classification"], "blocked")
        self.assertFalse(result["has_conflict"])


if __name__ == "__main__":
    unittest.main()
