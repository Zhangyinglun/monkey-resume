from __future__ import annotations

import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from docx import Document

from scripts.extract_resume_text import extract_docx_text
from scripts.layout_auto_tuner import auto_fit_layout
from templates.docx_resume_template import (
    export_pdf,
    generate_docx,
    generate_resume,
    require_carlito,
)
from templates.layout_settings import DOCX_DEFAULT_SETTINGS, LayoutSettings
from tests.sample_data import sample_resume


class DocxTemplateTests(unittest.TestCase):
    def test_approved_readable_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            doc = Document(generate_docx("default.docx", sample_resume(), directory))
            self.assertEqual(doc.styles["Normal"].font.name, "Carlito")
            self.assertEqual(doc.styles["Normal"].font.size.pt, 10.5)
            self.assertEqual(doc.paragraphs[0].runs[0].font.size.pt, 16.5)
            self.assertAlmostEqual(doc.sections[0].top_margin.mm, 12.7)
            self.assertAlmostEqual(doc.sections[0].bottom_margin.mm, 12.7)

    def test_explicit_layout_and_plain_text_roundtrip(self) -> None:
        resume = sample_resume()
        resume["summary"] = "Built R&D services with Java Map<K,V> and C++ & C#."
        before = copy.deepcopy(resume)
        layout = LayoutSettings(font_size_scale=1.0, margin_side_inch=0.75)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(generate_docx("resume.docx", resume, directory, layout))
            doc = Document(path)
            self.assertEqual(doc.styles["Normal"].font.size.pt, 9.5)
            self.assertAlmostEqual(doc.sections[0].left_margin.mm, 19.05)
            self.assertIn(resume["summary"], extract_docx_text(path))
        self.assertEqual(resume, before)

    def test_line_height_changes_spacing_not_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            texts, spacings = [], []
            for scale in (1.0, 0.95, 0.9, 0.88):
                path = Path(
                    generate_docx(
                        f"{scale}.docx",
                        sample_resume(),
                        directory,
                        LayoutSettings(line_height_scale=scale),
                    )
                )
                texts.append(extract_docx_text(path))
                paragraph = next(
                    p for p in Document(path).paragraphs if p.text.startswith("Backend engineer")
                )
                spacings.append(paragraph.paragraph_format.line_spacing.pt)
            self.assertEqual(len(set(texts)), 1)
            self.assertTrue(all(a > b for a, b in zip(spacings, spacings[1:])))

    def test_passing_default_is_not_squeezed_for_whitespace(self) -> None:
        before = sample_resume()
        with (
            mock.patch("scripts.layout_auto_tuner.generate_resume", return_value="fake.pdf"),
            mock.patch(
                "scripts.layout_auto_tuner.check_pdf_file",
                return_value={
                    "verdict": "PASS",
                    "checks": [
                        {"name": "bottom_margin", "passed": True, "detail": {"bottom_mm": 40}}
                    ],
                },
            ),
        ):
            result = auto_fit_layout(before, output_file="resume.pdf", max_trials=2)
        self.assertEqual(result.best_layout, DOCX_DEFAULT_SETTINGS)
        self.assertEqual(result.trials_run, 1)
        self.assertEqual(before, sample_resume())

    def test_missing_converter_has_descriptive_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(generate_docx("resume.docx", sample_resume(), directory))
            with mock.patch("shutil.which", return_value=None):
                with self.assertRaises(RuntimeError):
                    export_pdf(path)

    def test_converter_timeout_does_not_publish_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(generate_docx("resume.docx", sample_resume(), directory))
            with (
                mock.patch("templates.docx_resume_template.require_carlito"),
                mock.patch("shutil.which", return_value="soffice"),
                mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 120)),
            ):
                with self.assertRaises(subprocess.TimeoutExpired):
                    export_pdf(path)
            self.assertFalse(path.with_suffix(".pdf").exists())


@unittest.skipUnless(
    shutil.which("soffice") and shutil.which("pdftoppm"), "Office/Poppler required"
)
class DocxRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            require_carlito()
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_same_source_pdf_matches_independent_docx_render(self) -> None:
        from pdf2image import convert_from_path
        from PIL import Image

        with tempfile.TemporaryDirectory(prefix="resume space ") as directory:
            root = Path(directory)
            pdf = Path(generate_resume("候选 Resume.pdf", sample_resume(), root))
            copied = root / "independent.docx"
            shutil.copy2(pdf.with_suffix(".docx"), copied)
            script = Path(__file__).resolve().parents[1] / "vendor/openai_doc/render_docx.py"
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(copied),
                    "--output_dir",
                    str(root / "preview"),
                    "--dpi",
                    "96",
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            expected = convert_from_path(pdf, dpi=96)
            pages = sorted((root / "preview").glob("page-*.png"))
            self.assertEqual(len(expected), 1)
            self.assertEqual(len(pages), 1)
            with Image.open(pages[0]) as actual:
                self.assertEqual(expected[0].size, actual.size)
                self.assertEqual(expected[0].tobytes(), actual.tobytes())

    def test_real_overflow_detected_without_editing_content(self) -> None:
        from scripts.check_pdf_quality import check_pdf_file

        resume = sample_resume()
        resume["experience"][0]["bullets"] *= 15
        before = copy.deepcopy(resume)
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(generate_resume("overflow.pdf", resume, directory))
            report = check_pdf_file(pdf)
        count = next(c for c in report["checks"] if c["name"] == "page_count")
        self.assertGreater(count["detail"]["count"], 1)
        self.assertEqual(report["verdict"], "NEED-ADJUSTMENT")
        self.assertEqual(resume, before)


if __name__ == "__main__":
    unittest.main()
