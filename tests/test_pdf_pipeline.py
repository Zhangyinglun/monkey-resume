from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_pdf_quality import build_quality_report
from templates.docx_resume_template import generate_docx
from tests.sample_data import sample_resume


def quality_report(**changes: object) -> dict:
    arguments = {
        "page_count": 1,
        "width_mm": 210.0,
        "height_mm": 297.0,
        "has_text": True,
        "html_leak_count": 0,
        "placeholders": [],
        "margins": {"top": 25.0, "bottom": 40.0, "left": 30.0, "right": 30.0},
        "missing_sections": [],
        "contact": {"email": True, "phone": False, "linkedin": False},
        "missing_keywords": [],
        "provided_keywords": [],
        "layout_warnings": [],
        "margin_thresholds": {
            "min_bottom_mm": 3.0,
            "max_bottom_mm": 8.0,
            "min_top_mm": 3.0,
            "max_top_mm": 20.0,
            "min_side_mm": 10.0,
            "max_side_mm": 25.0,
        },
    }
    arguments.update(changes)
    return build_quality_report(**arguments)


class PdfQualityPolicyTests(unittest.TestCase):
    def test_email_only_does_not_invent_required_phone_or_linkedin(self) -> None:
        self.assertEqual(quality_report()["verdict"], "PASS")

    def test_sparse_tail_and_unmatched_keywords_are_advisories(self) -> None:
        report = quality_report(
            geometry_findings=[{"text": "reliability.", "word_count": 1}],
            missing_keywords=["Terraform"],
            provided_keywords=["Terraform"],
        )
        self.assertEqual(report["verdict"], "PASS")

    def test_physical_overflow_and_placeholders_still_block(self) -> None:
        for changes in (
            {"page_count": 2},
            {"placeholders": ["[Company]"]},
            {"has_text": False},
            {"width_mm": 180.0},
            {"min_font_pt": 6.0},
            {"bounds_findings": [{"page": 1, "text": "clipped"}]},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(quality_report(**changes)["verdict"], "NEED-ADJUSTMENT")

    def test_excess_whitespace_is_warning_not_failure(self) -> None:
        report = quality_report()
        self.assertEqual(report["verdict"], "PASS")
        warnings = next(c for c in report["checks"] if c["name"] == "layout_warnings")
        self.assertTrue(warnings["detail"]["warnings"])


class PdfRendererTests(unittest.TestCase):
    def test_old_summary_input_is_rejected_before_creating_artifacts(self) -> None:
        resume = sample_resume()
        resume["summary"] = ""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "summary"):
                generate_docx("resume.docx", resume, directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_renderer_rejects_skill_package_output(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError, "outside the Skill package"):
            generate_docx("resume.docx", sample_resume(), base_dir=root / "resume_output")

if __name__ == "__main__":
    unittest.main()
