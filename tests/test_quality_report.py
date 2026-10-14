from __future__ import annotations

import unittest

from scripts.generate_quality_report import format_quality_report


class QualityReportTests(unittest.TestCase):
    def test_missing_review_never_looks_accepted(self) -> None:
        text = format_quality_report({"candidate_id": "sample", "context_id": "context"})
        self.assertIn("not approved", text)
        self.assertIn("unavailable", text)
        self.assertIn("not semantic correctness", text)
        self.assertNotIn("100%", text)

    def test_stale_review_keeps_stale_status(self) -> None:
        record = {"candidate_id": "sample", "context_id": "new", "draft_fingerprint": "draft"}
        review = {
            "candidate_id": "sample",
            "context_id": "old",
            "draft_fingerprint": "draft",
            "content": {"status": "complete", "verdict": "pass"},
            "visual": {"status": "unavailable"},
        }
        text = format_quality_report(record, review)
        self.assertIn("invalid or stale", text)
        self.assertIn("Visual: unavailable", text)


if __name__ == "__main__":
    unittest.main()
