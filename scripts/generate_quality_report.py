#!/usr/bin/env python3
"""Summarize a version-bound candidate and host review; never publish or score ATS."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.resume_shared import load_json_file  # noqa: E402


def format_quality_report(record: dict[str, Any], review: dict[str, Any] | None = None) -> str:
    """Report facts and declarations separately, without upgrading pending checks."""
    lines = [
        "# Resume quality report",
        "",
        f"- Candidate: `{record.get('candidate_id', 'unknown')}`",
        f"- Context: `{record.get('context_id', 'unknown')}`",
        "- Evidence links establish traceability, not semantic correctness.",
        "",
    ]
    qa = record.get("physical_qa", {})
    lines.extend(
        ["## Programmatic format", "", f"- Recorded verdict: {qa.get('verdict', 'unavailable')}"]
    )
    for check in qa.get("checks", []):
        state = "PASS" if check.get("passed") else "check required"
        lines.append(f"- {check.get('name', 'unknown')}: {state}")
    lines.extend(["", "## Content and visual review", ""])
    if review is None:
        lines.append("Review not supplied. Candidate is not approved for publication.")
    else:
        bound = all(
            review.get(key) == record.get(key) and record.get(key)
            for key in (
                "candidate_id",
                "context_id",
                "draft_fingerprint",
                "resume_fingerprint",
                "docx_sha256",
                "pdf_sha256",
            )
        )
        lines.append(f"- Declared review bindings: {'matching' if bound else 'invalid or stale'}")
        content = review.get("content", {})
        visual = review.get("visual", {})
        lines.append(
            f"- Content: {content.get('status', 'unavailable')} / "
            f"{content.get('verdict', 'unavailable')}"
        )
        lines.append(f"- Visual: {visual.get('status', 'unavailable')}")
        for finding in content.get("findings", []):
            lines.append(
                f"- {finding.get('severity', 'unknown')}: "
                f"{finding.get('location', '')} — {finding.get('reason', '')}"
            )
    lines.extend(
        [
            "",
            "This summary is not a publication gate, hiring probability, or ATS score.",
            "Publication rechecks the current cache, artifacts and complete review.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    try:
        directory = args.candidate_dir.expanduser().resolve()
        if directory == PROJECT_ROOT or PROJECT_ROOT in directory.parents:
            raise ValueError("Candidate reports must live outside the Skill package.")
        record = load_json_file(directory / "candidate-record.json")
        review = load_json_file(args.review.expanduser().resolve()) if args.review else None
        print(format_quality_report(record, review))
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
