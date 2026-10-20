"""Shared real-rendering gate: optional locally, mandatory in Windows CI."""

from __future__ import annotations

import os
import shutil
import subprocess

from templates.document_fonts import resolve_font_files
from templates.office_tools import find_soffice


def rendering_available() -> bool:
    try:
        if not find_soffice() or not all(shutil.which(tool) for tool in ("pdftoppm", "pdfinfo")):
            raise RuntimeError("LibreOffice and both Poppler tools are required")
        resolve_font_files("Arial")
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        if os.environ.get("MONKEY_RESUME_REQUIRE_RENDERING") == "1":
            raise RuntimeError(f"Required real rendering unavailable: {error}") from error
        return False
    return True
