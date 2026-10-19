"""Render a resume DOCX independently with the selected style's local fonts."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from templates.document_fonts import conversion_environment  # noqa: E402
from templates.style_profiles import DEFAULT_STYLE, STYLES, get_style  # noqa: E402


def render_preview(docx: Path, output: Path, *, style: str = DEFAULT_STYLE, dpi: int = 144) -> None:
    """Keep font configuration local while leaving the vendored renderer intact."""
    docx, output = docx.expanduser().resolve(), output.expanduser().resolve()
    if not docx.is_file() or docx.suffix.lower() != ".docx":
        raise ValueError(f"Missing DOCX input: {docx}")
    if output == PROJECT_ROOT or PROJECT_ROOT in output.parents:
        raise ValueError("Preview output must live outside the Skill package.")
    if dpi <= 0:
        raise ValueError("Preview DPI must be positive.")
    with tempfile.TemporaryDirectory(prefix="resume-preview-fonts-") as directory:
        env = conversion_environment(get_style(style).font_family, Path(directory))
        subprocess.run([
            sys.executable, str(PROJECT_ROOT / "vendor/openai_doc/render_docx.py"),
            str(docx), "--output_dir", str(output), "--dpi", str(dpi),
        ], env=env, check=True, capture_output=True, text=True, timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--style", choices=tuple(STYLES), default=DEFAULT_STYLE)
    parser.add_argument("--dpi", type=int, default=144)
    args = parser.parse_args()
    render_preview(args.docx, args.output_dir, style=args.style, dpi=args.dpi)
    print(f"Pages rendered to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
