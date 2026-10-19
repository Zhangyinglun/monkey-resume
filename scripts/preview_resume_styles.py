"""Render a synthetic design preview; this does not publish an Accepted Resume."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_pdf_quality import check_pdf_file  # noqa: E402
from scripts.layout_auto_tuner import auto_fit_layout  # noqa: E402
from scripts.render_docx_preview import render_preview  # noqa: E402
from templates.docx_resume_template import generate_resume, rendering_environment  # noqa: E402
from templates.style_profiles import STYLES, get_style  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory outside the Skill package")
    parser.add_argument("--auto-fit", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    if output == PROJECT_ROOT or PROJECT_ROOT in output.parents:
        parser.error("Preview output must live outside the Skill package.")
    if output.exists():
        parser.error("Preview directory already exists; use a new directory.")
    fixture = PROJECT_ROOT / "examples/synthetic_resume.json"
    content = json.loads(fixture.read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    report = {
        "purpose": "Wholly fictional design preview; not an Accepted Resume or candidate evidence.",
        "sample_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "styles": {},
    }
    passed = True
    for name in STYLES:
        profile = get_style(name)
        layout = profile.layout
        if args.auto_fit:
            layout = auto_fit_layout(content, output_file="resume.pdf", max_trials=6, hint_layout=layout, style=name).best_layout
        pdf = Path(generate_resume("resume.pdf", content, str(output / name), layout, style=name))
        qa = check_pdf_file(pdf, minimum_font_pt=profile.minimum_font_pt)
        preview = pdf.parent / "docx-preview"
        render_preview(pdf.with_suffix(".docx"), preview, style=name)
        pages = convert_from_path(pdf, dpi=144)
        independent = sorted(preview.glob("page-*.png"))
        equal = len(pages) == len(independent)
        for number, page in enumerate(pages, 1):
            page.save(pdf.parent / f"page-{number}.png")
            if number <= len(independent):
                with Image.open(independent[number - 1]) as other:
                    equal = equal and page.size == other.size and page.convert("RGB").tobytes() == other.convert("RGB").tobytes()
        passed = passed and qa["verdict"] == "PASS" and equal
        report["styles"][name] = {
            "style": profile.snapshot(layout), "physical_qa": qa,
            "rendering_environment": rendering_environment(style=name),
            "docx_sha256": hashlib.sha256(pdf.with_suffix(".docx").read_bytes()).hexdigest(),
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "independent_preview_pixel_match": equal, "page_count": len(pages),
        }
    (output / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "physical_and_render_checks_passed": passed}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
