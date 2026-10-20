from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.rendering_support import rendering_available


class RenderingRequirementsTests(unittest.TestCase):
    def test_real_suites_fail_import_when_required_office_is_missing(self) -> None:
        code = (
            "import importlib, sys; from unittest.mock import patch; "
            "guard = patch('templates.office_tools.find_soffice', return_value=None); "
            "guard.start(); importlib.import_module(sys.argv[1])"
        )
        for module in ("tests.test_docx_output", "tests.test_model_first_end_to_end"):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-c", code, module],
                    cwd=Path(__file__).resolve().parents[1],
                    env={**os.environ, "MONKEY_RESUME_REQUIRE_RENDERING": "1"},
                    capture_output=True, text=True, timeout=10, check=False,
                )
                self.assertNotEqual(result.returncode, 0, "Real rendering was silently skipped")
                self.assertIn("Required real rendering unavailable", result.stderr)

    def test_required_rendering_fails_instead_of_skipping_when_office_is_missing(self) -> None:
        with (
            patch.dict("os.environ", {"MONKEY_RESUME_REQUIRE_RENDERING": "1"}),
            patch("tests.rendering_support.find_soffice", return_value=None),
        ):
            with self.assertRaisesRegex(RuntimeError, "Required real rendering unavailable"):
                rendering_available()

    def test_required_rendering_fails_when_fonts_are_missing(self) -> None:
        with (
            patch.dict("os.environ", {"MONKEY_RESUME_REQUIRE_RENDERING": "1"}),
            patch("tests.rendering_support.find_soffice", return_value="office"),
            patch("tests.rendering_support.shutil.which", return_value="poppler"),
            patch("tests.rendering_support.resolve_font_files", side_effect=RuntimeError("Arial missing")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Arial missing"):
                rendering_available()

    def test_optional_rendering_can_skip_missing_dependencies(self) -> None:
        with (
            patch.dict("os.environ", {"MONKEY_RESUME_REQUIRE_RENDERING": "0"}),
            patch("tests.rendering_support.find_soffice", return_value=None),
        ):
            self.assertFalse(rendering_available())
