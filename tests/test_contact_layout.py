from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from scripts.check_pdf_quality import check_pdf_file


class ContactLayoutTests(unittest.TestCase):
    def render_header(self, path: Path, contact_lines: int, *, boundary: str = "Experience") -> None:
        """Create synthetic rendered geometry, including separate link-like runs."""
        canvas = Canvas(str(path), pagesize=A4)
        canvas.setFont("Helvetica", 19)
        canvas.drawString(50, 790, "Alex Chen")
        canvas.setFont("Helvetica", 11)
        if contact_lines:
            canvas.drawString(50, 765, "Seattle | alex@example.org")
            canvas.drawString(300, 765, "linkedin.com/in/example")
        for index in range(1, contact_lines):
            canvas.drawString(50, 765 - index * 14, "github.com/example")
        for y, text in ((700, boundary), (680, "Example Corp"), (600, "Skills"), (500, "Education")):
            canvas.drawString(50, y, text)
        canvas.save()

    def test_actual_rendered_contact_lines_determine_quality_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for count in (0, 1, 2, 3):
                with self.subTest(contact_lines=count):
                    path = Path(directory) / f"contact-{count}.pdf"
                    self.render_header(path, count)
                    report = check_pdf_file(path)
                    check = next(c for c in report["checks"] if c["name"] == "contact_single_line")
                    self.assertEqual(check["detail"]["line_count"], count)
                    self.assertTrue(check["detail"]["measured"])
                    self.assertEqual(check["passed"], count == 1)
                    self.assertEqual(report["verdict"], "PASS" if count == 1 else "NEED-ADJUSTMENT")
                    # Diagnostics contain measurements, not personal contact text.
                    self.assertNotIn("alex@example.org", str(check))

    def test_unidentifiable_header_cannot_pass_contact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown-header.pdf"
            self.render_header(path, 1, boundary="Unrecognized heading")
            report = check_pdf_file(path)
        check = next(c for c in report["checks"] if c["name"] == "contact_single_line")
        self.assertFalse(check["detail"]["measured"])
        self.assertFalse(check["passed"])
        self.assertEqual(report["verdict"], "NEED-ADJUSTMENT")


if __name__ == "__main__":
    unittest.main()
