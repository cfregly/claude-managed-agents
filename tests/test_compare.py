import unittest

from managed_agents.compare import EXPECTED_REPORT, fetch_ops_slice, run_compare, score_report


class CompareTests(unittest.TestCase):
    def test_fetch_ops_slice_is_deterministic(self):
        first = fetch_ops_slice("logs")
        second = fetch_ops_slice("logs")
        self.assertEqual(first, second)
        self.assertIn("log-auth-1", first)

    def test_score_report_accepts_expected_shape(self):
        ok, report, failures = score_report("", dict(EXPECTED_REPORT))
        self.assertTrue(ok)
        self.assertEqual(report["incident_id"], "inc-042")
        self.assertEqual(failures, [])

    def test_score_report_rejects_missing_evidence(self):
        broken = dict(EXPECTED_REPORT)
        broken["evidence_ids"] = ["dpl-17"]
        ok, _, failures = score_report("", broken)
        self.assertFalse(ok)
        self.assertTrue(any("evidence_ids" in failure for failure in failures))

    def test_dry_run_marks_provider_held(self):
        receipt = run_compare(providers=["managed"], live=False)
        self.assertEqual(receipt["status"], "held")
        self.assertEqual(receipt["arms"][0]["status"], "held")


if __name__ == "__main__":
    unittest.main()
