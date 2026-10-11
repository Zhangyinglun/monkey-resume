#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish editable DOCX by default, with same-source PDF export and QA."""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_factual_integrity import audit_resume  # noqa: E402
from scripts.check_content_quality import run_all_checks  # noqa: E402
from scripts.check_pdf_quality import check_pdf_file  # noqa: E402
from scripts.layout_auto_tuner import (  # noqa: E402
    CONTENT_CHECKS,
    LAYOUT_FIXABLE_CHECKS,
    auto_fit_layout,
)
from scripts.resume_shared import load_json_file, validate_resume_content  # noqa: E402
from templates.docx_resume_template import generate_resume  # noqa: E402
from templates.layout_settings import DOCX_DEFAULT_SETTINGS, LayoutSettings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render final resume DOCX (default), PDF, or both with A4 layout QA."
    )
    parser.add_argument("--input-json", required=True, help="Resume content JSON file path")
    parser.add_argument(
        "--output-file",
        default=None,
        help="Filename only; defaults to resume.docx. Explicit .pdf remains backward compatible.",
    )
    parser.add_argument("--format", choices=("docx", "pdf", "both"),
                        help="Default DOCX; an explicit .pdf filename selects PDF for compatibility.")
    parser.add_argument(
        "--output-dir", default="resume_output", help="Output directory (default: resume_output)"
    )
    parser.add_argument(
        "--manifest-json",
        help="Tailoring Manifest path (default: resume-changes.json beside input)",
    )
    parser.add_argument(
        "--evidence-json",
        help="Candidate Evidence Ledger path (default: candidate-evidence.json beside input)",
    )
    parser.add_argument(
        "--base-json",
        help="Source Snapshot path (default: base-resume.json beside input)",
    )
    parser.add_argument(
        "--font-size-scale", type=float, default=None, help="Font size scale (0.7-1.3; default: 1.1)"
    )
    parser.add_argument(
        "--line-height-scale", type=float, default=None, help="Line height scale (0.7-1.3)"
    )
    parser.add_argument(
        "--section-spacing-scale", type=float, default=None, help="Section spacing scale (0.7-1.3)"
    )
    parser.add_argument(
        "--item-spacing-scale", type=float, default=None, help="Item spacing scale (0.7-1.3)"
    )
    parser.add_argument(
        "--margin-top-mm", type=float, default=None, help="Top margin in mm (default: 12.7)"
    )
    parser.add_argument(
        "--margin-bottom-mm", type=float, default=None, help="Bottom margin in mm (default: 12.7)"
    )
    parser.add_argument(
        "--margin-side-inch",
        type=float,
        default=None,
        help="Left/right margin in inches (default: 0.6)",
    )
    parser.add_argument("--compact", action="store_true", help="Enable compact mode")
    parser.add_argument("--auto-fit", action="store_true", help="Auto-search layout parameters")
    parser.add_argument(
        "--auto-fit-max-trials", type=int, default=12, help="Max layout candidates (default: 12)"
    )
    return parser.parse_args()


def _build_layout(args: argparse.Namespace) -> LayoutSettings:
    """Build LayoutSettings from CLI args."""
    overrides = {
        name: getattr(args, name)
        for name in ('font_size_scale', 'line_height_scale', 'section_spacing_scale',
                     'item_spacing_scale', 'margin_top_mm', 'margin_bottom_mm', 'margin_side_inch')
        if getattr(args, name) is not None
    }
    if args.compact and args.font_size_scale is None:
        overrides['font_size_scale'] = 1.0  # Retain the existing compact-mode preset.
    return replace(DOCX_DEFAULT_SETTINGS, **overrides, compact_mode=args.compact)


def _next_rejected_path(output_dir: Path, output_name: str) -> Path:
    """Return a non-conflicting path for a generated PDF that failed QA."""
    rejected_dir = output_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(output_name).stem
    candidate = rejected_dir / f"{stem}_rejected.pdf"
    sequence = 2
    while candidate.exists() or candidate.with_suffix(".docx").exists():
        candidate = rejected_dir / f"{stem}_rejected_{sequence}.pdf"
        sequence += 1
    return candidate


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    requested_name = args.output_file or ("resume.pdf" if args.format == "pdf" else "resume.docx")
    output_name = Path(requested_name).name
    if output_name != requested_name:
        print("Error: --output-file must contain filename only, no path.", file=sys.stderr)
        return 1
    suffix = Path(output_name).suffix.casefold()
    if suffix not in (".docx", ".pdf"):
        print("Error: --output-file must use a .docx or .pdf extension.", file=sys.stderr)
        return 1
    output_format = args.format or suffix[1:]
    if output_format != "both" and args.format and suffix != "." + output_format:
        print("Error: --format and --output-file extension must agree.", file=sys.stderr)
        return 1
    qa_name = str(Path(output_name).with_suffix(".pdf"))

    source_path = Path(args.input_json).expanduser().resolve()
    if not source_path.exists():
        print(f"Error: Input file does not exist: {source_path}", file=sys.stderr)
        return 1

    if output_dir == PROJECT_ROOT or PROJECT_ROOT in output_dir.parents:
        print(
            "Error: Output must live in a workspace outside the Skill package.",
            file=sys.stderr,
        )
        return 1

    if args.auto_fit_max_trials <= 0:
        print("Error: --auto-fit-max-trials must be positive.", file=sys.stderr)
        return 1
    for name in (
        "font_size_scale",
        "line_height_scale",
        "section_spacing_scale",
        "item_spacing_scale",
    ):
        value = getattr(args, name)
        if value is not None and not 0.7 <= value <= 1.3:
            print(
                f"Error: --{name.replace('_', '-')} must be between 0.7 and 1.3.", file=sys.stderr
            )
            return 1
    for name in ("margin_top_mm", "margin_bottom_mm", "margin_side_inch"):
        value = getattr(args, name)
        if value is not None and value <= 0:
            print(f"Error: --{name.replace('_', '-')} must be positive.", file=sys.stderr)
            return 1

    manifest_path = (
        Path(args.manifest_json).expanduser().resolve()
        if args.manifest_json
        else source_path.parent / "resume-changes.json"
    )
    evidence_path = (
        Path(args.evidence_json).expanduser().resolve()
        if args.evidence_json
        else source_path.parent / "candidate-evidence.json"
    )
    base_path = (
        Path(args.base_json).expanduser().resolve()
        if args.base_json
        else source_path.parent / "base-resume.json"
    )

    try:
        content = load_json_file(source_path)
        validate_resume_content(content, require_non_empty=True)
        manifest = load_json_file(manifest_path)
        audit_report = audit_resume(
            content,
            manifest,
            load_json_file(evidence_path),
            base_resume=load_json_file(base_path),
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Error: mandatory factual audit could not run: {exc}", file=sys.stderr)
        return 1
    if audit_report["verdict"] != "PASS":
        codes = ", ".join(sorted({finding["code"] for finding in audit_report["findings"]}))
        print(
            f"Error: mandatory factual audit failed: {codes}",
            file=sys.stderr,
        )
        return 1

    content_findings = [check for check in run_all_checks(content) if check["status"] != "PASS"]
    dispositions = {
        str(item.get("finding")): item
        for item in manifest.get("warning_dispositions", [])
        if isinstance(item, dict)
        and item.get("status") == "accepted"
        and str(item.get("reason", "")).strip()
    }
    unresolved_content = [
        finding for finding in content_findings if finding["name"] not in dispositions
    ]
    for finding in content_findings:
        resolution = dispositions.get(finding["name"])
        suffix = (
            f"; disposition: {resolution['reason']}" if resolution is not None else "; unresolved"
        )
        print(
            f"Content QA advisory [{finding['name']}]: {finding['detail']}{suffix}",
            file=sys.stderr,
        )
    if unresolved_content:
        print(
            "Error: unresolved content QA warnings block publication. "
            "Correct the text/evidence or add a reasoned warning disposition.",
            file=sys.stderr,
        )
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.auto_fit:
            has_custom = any(
                getattr(args, attr) is not None
                for attr in (
                    "font_size_scale",
                    "line_height_scale",
                    "section_spacing_scale",
                    "item_spacing_scale",
                    "margin_top_mm",
                    "margin_bottom_mm",
                    "margin_side_inch",
                )
            )
            hint_layout = _build_layout(args) if has_custom or args.compact else None

            fit_result = auto_fit_layout(
                content,
                output_file=qa_name,
                max_trials=args.auto_fit_max_trials,
                hint_layout=hint_layout,
            )
            layout = fit_result.best_layout
            failed_checks = [
                c.get("name")
                for c in fit_result.best_report.get("checks", [])
                if not c.get("passed")
            ]
            print(
                f"Auto-fit finished: trials={fit_result.trials_run}, "
                f"best_verdict={fit_result.best_report.get('verdict')}"
            )
            if failed_checks:
                layout_unresolved = [c for c in failed_checks if c in LAYOUT_FIXABLE_CHECKS]
                content_unresolved = [c for c in failed_checks if c in CONTENT_CHECKS]
                if layout_unresolved:
                    print(f"Auto-fit unresolved layout checks: {', '.join(layout_unresolved)}")
                if content_unresolved:
                    print(
                        f"Content issues (cannot fix by layout tuning): {', '.join(content_unresolved)}"
                    )
        else:
            layout = _build_layout(args)

        with tempfile.TemporaryDirectory(
            prefix=".resume-staging-", dir=str(output_dir)
        ) as staging_dir:
            candidate_path = Path(
                generate_resume(
                    qa_name,
                    content,
                    base_dir=staging_dir,
                    layout=layout,
                )
            )
            qa_report = check_pdf_file(candidate_path)
            qa_passed = qa_report.get("verdict") == "PASS"

            if not qa_passed:
                failed = [
                    check["name"]
                    for check in qa_report.get("checks", [])
                    if not check.get("passed")
                ]
                rejected_path = _next_rejected_path(output_dir, qa_name)
                candidate_path.replace(rejected_path)
                candidate_docx = candidate_path.with_suffix(".docx")
                if candidate_docx.exists():
                    candidate_docx.replace(rejected_path.with_suffix(".docx"))
                print(
                    f"\u2717 QA not passed ({', '.join(failed)}); "
                    "previous resume files were preserved."
                )
                print(f"Rejected candidate retained for review: {rejected_path}")
                return 2

            extensions = (".docx", ".pdf") if output_format == "both" else ("." + output_format,)
            candidates = [candidate_path.with_suffix(ext) for ext in extensions]
            destinations = {
                ext: output_dir / (output_name if Path(output_name).suffix.casefold() == ext
                                   else str(Path(output_name).with_suffix(ext)))
                for ext in (".docx", ".pdf")
            }
            if not all(path.is_file() for path in candidates):
                raise RuntimeError("Missing candidate output; accepted versions preserved.")
            # Archive only after every requested output has passed the shared PDF gate.
            # Keep a rollback journal so a filesystem error cannot destroy an accepted pair.
            journal: list[tuple[Path, Path]] = []
            published: list[Path] = []
            try:
                backup_dir = output_dir / "backup" / "Uncategorized"
                # Retire a same-stem counterpart too: leaving an old PDF beside
                # a new DOCX would falsely present them as a matching pair.
                archive_targets = [path for path in output_dir.iterdir()
                                   if path.stem == Path(output_name).stem
                                   and path.suffix.casefold() in (".docx", ".pdf")]
                for target in archive_targets:
                    if target.exists():
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        n = 1
                        backup = backup_dir / f"{target.stem}_old_{n}{target.suffix}"
                        while backup.exists():
                            n += 1
                            backup = backup_dir / f"{target.stem}_old_{n}{target.suffix}"
                        target.replace(backup)
                        journal.append((backup, target))
                for source in candidates:
                    target = destinations[source.suffix]
                    source.replace(target)
                    published.append(target)
            except OSError:
                for target in published:
                    target.unlink(missing_ok=True)
                for backup, target in reversed(journal):
                    backup.replace(target)
                raise
            final_path = destinations[candidates[0].suffix]
    except Exception as exc:  # noqa: BLE001 - CLI must convert renderer/parser errors into a stable exit code.
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1

    print("\u2713 QA passed; previous version(s) archived to backup/")
    print(f"Generated successfully: {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
