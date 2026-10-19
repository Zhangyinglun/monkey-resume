#!/usr/bin/env python3
"""Prepare immutable candidates, then publish only a bound host review.

Review v2: schema_version, candidate_id (render UUID), context_id,
draft_fingerprint, resume_fingerprint, docx_sha256, pdf_sha256; content:
{status: complete, verdict: pass, reviewer_id: nonempty, independent: true,
findings: [{severity: blocking|suggestion, ...}]}; visual: {status: pass,
pages: [1], docx_preview_inspected: true, pdf_preview_inspected: true}.
Independence is host provenance, not cryptographic proof. Extra review evidence
(blind reading, evidence checks, source locations) is retained unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.accepted_resume_publication import (  # noqa: E402
    commit_accepted_resume,
    validate_output_name,
)
from scripts.check_pdf_quality import check_pdf_file  # noqa: E402
from scripts.layout_auto_tuner import auto_fit_layout  # noqa: E402
from scripts.resume_history_manager import validate_job_url  # noqa: E402
from scripts.resume_shared import add_workspace_argument, load_json_file  # noqa: E402
from templates.document_fonts import validate_pdf_fonts  # noqa: E402
from templates.docx_resume_template import generate_resume, rendering_environment  # noqa: E402
from templates.layout_settings import LayoutSettings
from templates.style_profiles import DEFAULT_STYLE, STYLES, get_style  # noqa: E402


def validate_workspace(workspace: Path) -> Path:
    from scripts.candidate_cache import validate_workspace as validate

    return validate(workspace)


def workspace_lock(workspace: Path) -> Any:
    from scripts.candidate_cache import workspace_lock as lock

    return lock(workspace)


def load_candidate_context(workspace: Path) -> dict:
    from scripts.candidate_cache import load_candidate_context as load

    return load(workspace)


def compile_draft(draft: dict, context: dict) -> dict:
    from scripts.draft_compiler import compile_draft as compile_current

    return compile_current(draft, context)


class ReviewNotReady(ValueError):
    """Valid inputs lack passing review or physical QA (CLI exit 2)."""


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or unsafe candidate file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _directory(workspace: Path, name: str) -> Path:
    path = workspace / name
    if path.resolve() != path:
        raise ValueError(f"Workspace output must not contain symlinks: {path}")
    return path


def _qa_passes(report: dict) -> bool:
    checks = report.get("checks", [])
    by_name = {c.get("name"): c for c in checks if isinstance(c, dict)}
    if any(
        by_name.get(name, {}).get("passed") is not True
        for name in ("page_count", "page_size", "text_layer", "page_bounds", "font_readability")
    ):
        return False
    if by_name["page_count"].get("detail", {}).get("count") != 1:
        return False
    if by_name["font_readability"].get("detail", {}).get("measured") is not True:
        return False
    # Fixed contact/section/keyword rules and whitespace preferences are advisory.
    advisory = {
        "contact_info",
        "section_completeness",
        "keyword_coverage",
        "layout_warnings",
        "text_geometry",
    }
    return all(c.get("passed") is True for c in checks if c.get("name") not in advisory)


def prepare_candidate(
    workspace: Path,
    draft_path: Path,
    *,
    output_name: str = "resume.docx",
    layout: LayoutSettings | None = None,
    auto_fit: bool = False,
    max_trials: int = 12,
    author_id: str = "",
    style: str = DEFAULT_STYLE,
) -> dict:
    """Freeze model text and render; never change Accepted or accepted history."""
    profile = get_style(style)
    layout = profile.resolve_layout(layout)
    workspace = validate_workspace(workspace)
    validate_output_name(output_name)
    if max_trials <= 0:
        raise ValueError("max_trials must be positive.")
    if not isinstance(author_id, str):
        raise ValueError("author_id must be a string.")
    source = Path(draft_path).expanduser().resolve()
    if source == PROJECT_ROOT or PROJECT_ROOT in source.parents:
        raise ValueError("Personal draft must live outside the Skill package.")
    with workspace_lock(workspace):
        context = load_candidate_context(workspace)
        draft_bytes = source.read_bytes()
        draft = json.loads(draft_bytes)
        compiled = compile_draft(draft, context)
        if compiled.get("schema_version") != 2:
            raise ValueError("Compiler must return schema_version 2.")
        validate_job_url(compiled["target"].get("job_url", ""))
        root = _directory(workspace, "candidates")
        root.mkdir(parents=True, exist_ok=True)
        candidate_id = str(uuid4())
        directory = root / candidate_id
        directory.mkdir()
        (directory / "draft.json").write_bytes(draft_bytes)
        _write(directory / "compiled.json", compiled)
        pdf = directory / Path(output_name).with_suffix(".pdf")
        docx = pdf.with_suffix(".docx")
        qa: dict = {"verdict": "unavailable", "checks": []}
        error = ""
        font_verification: dict[str, object] = {"verified": False}
        try:
            if auto_fit:
                layout = auto_fit_layout(
                    compiled["resume"],
                    output_file=pdf.name,
                    max_trials=max_trials,
                    hint_layout=layout,
                    style=style,
                ).best_layout
            rendered = Path(
                generate_resume(
                    pdf.name,
                    compiled["resume"],
                    base_dir=str(directory),
                    layout=layout,
                    style=style,
                )
            ).resolve()
            if rendered != pdf:
                raise ValueError("Renderer returned an unexpected artifact path.")
            font_verification = validate_pdf_fonts(pdf, profile.font_family)
            qa = check_pdf_file(pdf, minimum_font_pt=profile.minimum_font_pt)
        except Exception as exc:  # Preserve failed candidates for host feedback.
            error = str(exc)
        record = {
            "schema_version": 2,
            "candidate_id": candidate_id,
            "candidate_identity": context["candidate_id"],
            "context_id": compiled["context_id"],
            "draft_fingerprint": compiled["draft_fingerprint"],
            "resume_fingerprint": compiled["resume_fingerprint"],
            "draft_sha256": _sha(directory / "draft.json"),
            "compiled_sha256": _sha(directory / "compiled.json"),
            "pdf_sha256": _sha(pdf) if pdf.is_file() else None,
            "docx_sha256": _sha(docx) if docx.is_file() else None,
            "output_name": output_name,
            "author_id": author_id.strip(),
            "target": compiled["target"],
            "physical_qa": qa,
            "style": profile.snapshot(layout),
            "rendering_environment": rendering_environment(style=style),
            "font_verification": font_verification,
            "render_error": error,
        }
        _write(directory / "candidate-record.json", record)
        # Separate program binding detects a replaced record, not malicious workspace owners.
        bindings = root / ".bindings"
        if bindings.resolve() != bindings:
            raise ValueError("Unsafe candidate binding directory.")
        bindings.mkdir(exist_ok=True)
        _write(
            bindings / f"{candidate_id}.json",
            {"record_sha256": _sha(directory / "candidate-record.json")},
        )
        template = {
            key: record[key]
            for key in (
                "schema_version",
                "candidate_id",
                "context_id",
                "draft_fingerprint",
                "resume_fingerprint",
                "pdf_sha256",
                "docx_sha256",
            )
        }
        template.update(
            blind_reading={"hiring_problem": "", "positioning": "", "requirements": []},
            evidence_review={
                "status": "pending",
                "context_id": record["context_id"],
                "assertion_review": "",
                "omission_review": "",
            },
            review_context={"mode": "unavailable", "identifier": "", "model": None},
            content={
                "status": "pending",
                "verdict": "not_ready",
                "reviewer_id": "",
                "independent": False,
                "findings": [],
            },
            visual={
                "status": "pending",
                "pages": [],
                "docx_preview_inspected": False,
                "pdf_preview_inspected": False,
            },
        )
        _write(directory / "review-template.json", template)
        return {
            "status": "prepared",
            "candidate_id": candidate_id,
            "candidate_dir": str(directory),
            "draft": str(directory / "draft.json"),
            "compiled": str(directory / "compiled.json"),
            "record": str(directory / "candidate-record.json"),
            "docx": str(docx),
            "pdf": str(pdf),
            "physical_qa": qa,
            "qa_passed": not error and _qa_passes(qa),
            "style": record["style"],
            "render_error": error,
            "review_template": template,
            "review_template_path": str(directory / "review-template.json"),
        }


def _validate_review(review: dict, record: dict) -> None:
    if not isinstance(review, dict):
        raise ReviewNotReady("Review must be an object.")
    for key in (
        "schema_version",
        "candidate_id",
        "context_id",
        "draft_fingerprint",
        "resume_fingerprint",
        "pdf_sha256",
        "docx_sha256",
    ):
        if review.get(key) != record[key]:
            raise ReviewNotReady(f"Review binding mismatch: {key}")
    if type(review.get("schema_version")) is not int:
        raise ReviewNotReady("Review schema_version must be an integer.")
    blind = review.get("blind_reading")
    evidence = review.get("evidence_review")
    execution = review.get("review_context")

    def populated(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    if (
        not isinstance(blind, dict)
        or not populated(blind.get("hiring_problem"))
        or not populated(blind.get("positioning"))
        or not isinstance(blind.get("requirements"), list)
        or not blind["requirements"]
        or any(
            not isinstance(r, dict)
            or not populated(r.get("original_quote"))
            or r["original_quote"] not in record["target"]["original_jd"]
            for r in blind["requirements"]
        )
    ):
        raise ReviewNotReady(
            "Frozen blind-reading results and original requirement quotes required."
        )
    if (
        not isinstance(evidence, dict)
        or evidence.get("status") != "complete"
        or evidence.get("context_id") != record["context_id"]
        or not populated(evidence.get("assertion_review"))
        or not populated(evidence.get("omission_review"))
    ):
        raise ReviewNotReady(
            "Complete bound assertion and important-omission review results required."
        )
    if (
        not isinstance(execution, dict)
        or execution.get("mode") not in ("independent_subagent", "independent_human")
        or not populated(execution.get("identifier"))
    ):
        raise ReviewNotReady("Actual independent reviewer execution context required.")
    content, visual = review.get("content"), review.get("visual")
    if not isinstance(content, dict) or not isinstance(visual, dict):
        raise ReviewNotReady("Complete content and visual review required.")
    reviewer = content.get("reviewer_id")
    findings = content.get("findings")
    if (
        content.get("status") != "complete"
        or content.get("verdict") != "pass"
        or content.get("independent") is not True
        or not isinstance(reviewer, str)
        or not reviewer.strip()
        or reviewer.strip() == record.get("author_id")
        or not isinstance(findings, list)
        or any(not isinstance(f, dict) or f.get("severity") != "suggestion" for f in findings)
    ):
        raise ReviewNotReady(
            "Independent, complete content review without blocking findings required."
        )
    if (
        visual.get("status") != "pass"
        or visual.get("pages") != [1]
        or any(type(p) is not int for p in visual.get("pages", []))
        or visual.get("docx_preview_inspected") is not True
        or visual.get("pdf_preview_inspected") is not True
    ):
        raise ReviewNotReady("Every actual DOCX/PDF page must have completed visual inspection.")


def publish_candidate(
    workspace: Path,
    candidate_id: str,
    review: dict,
    *,
    output_name: str | None = None,
    output_format: str = "docx",
) -> dict:
    """Recompile against current cache under lock and transactionally accept artifacts."""
    workspace = validate_workspace(workspace)
    if output_name is not None:
        validate_output_name(output_name)
    if output_format not in {"docx", "pdf", "both"}:
        raise ValueError("output_format must be docx, pdf or both.")
    try:
        if str(UUID(candidate_id)) != candidate_id:
            raise ValueError("Noncanonical candidate UUID.")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Candidate ID must be a canonical UUID.") from exc
    with workspace_lock(workspace):
        root = _directory(workspace, "candidates")
        directory = root / candidate_id
        if directory.resolve() != directory:
            raise ValueError("Unsafe candidate directory.")
        record_path = directory / "candidate-record.json"
        binding_path = _directory(root, ".bindings") / f"{candidate_id}.json"
        _sha(binding_path)
        binding = load_json_file(binding_path)
        if _sha(record_path) != binding.get("record_sha256"):
            raise ValueError("Candidate record changed after preparation.")
        record = load_json_file(record_path)
        if record.get("schema_version") != 2 or record.get("candidate_id") != candidate_id:
            raise ValueError("Invalid candidate record version or ID.")
        output_name = validate_output_name(output_name or record["output_name"])
        for name, field in (("draft.json", "draft_sha256"), ("compiled.json", "compiled_sha256")):
            if _sha(directory / name) != record[field]:
                raise ValueError(f"Frozen candidate changed: {name}")
        context = load_candidate_context(workspace)
        if (
            context["context_id"] != record["context_id"]
            or context["candidate_id"] != record["candidate_identity"]
        ):
            raise ValueError("Candidate context is stale; prepare a new candidate.")
        compiled = compile_draft(load_json_file(directory / "draft.json"), context)
        if compiled != load_json_file(directory / "compiled.json"):
            raise ValueError("Frozen draft compilation no longer matches current evidence.")
        for key in ("context_id", "draft_fingerprint", "resume_fingerprint", "target"):
            if compiled.get(key) != record[key]:
                raise ValueError(f"Candidate compilation binding mismatch: {key}")
        pdf = directory / Path(validate_output_name(record["output_name"])).with_suffix(".pdf")
        docx = pdf.with_suffix(".docx")
        if (
            record.get("render_error")
            or not record.get("pdf_sha256")
            or not record.get("docx_sha256")
        ):
            raise ReviewNotReady("Rendering unavailable; prepare a new candidate.")
        for artifact in (pdf, docx):
            if _sha(artifact) != record[artifact.suffix[1:] + "_sha256"]:
                raise ValueError("Actual candidate artifact changed after review.")
        _validate_review(review, record)
        profile = get_style()
        try:
            stored_style = record["style"]
            layout = profile.resolve_layout(LayoutSettings(**stored_style["layout"]))
            current_style = json.loads(json.dumps(profile.snapshot(layout)))
        except (KeyError, TypeError, ValueError) as exc:
            raise ReviewNotReady("Unsupported candidate style; prepare a new candidate.") from exc
        if stored_style != current_style:
            raise ReviewNotReady("Unsupported candidate style; prepare a new candidate.")
        try:
            validate_pdf_fonts(pdf, profile.font_family)
        except (OSError, RuntimeError) as exc:
            raise ReviewNotReady(str(exc)) from exc
        qa = check_pdf_file(pdf, minimum_font_pt=profile.minimum_font_pt)
        if not _qa_passes(qa):
            raise ReviewNotReady("Actual PDF must pass one-page A4 and readable geometry QA.")
        committed = commit_accepted_resume(
            workspace,
            pdf,
            record,
            review,
            output_name=output_name,
            output_format=output_format,
        )
        return {
            "status": "published",
            "candidate_id": candidate_id,
            **committed,
            "physical_qa": qa,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Freeze draft and render without accepting")
    publish = commands.add_parser("publish", help="Publish candidate after bound host review")
    for command in (prepare, publish):
        add_workspace_argument(command)
    prepare.add_argument("--draft", required=True)
    prepare.add_argument("--output-file", default="resume.docx")
    prepare.add_argument("--author-id", default="")
    prepare.add_argument("--style", choices=tuple(STYLES), default=DEFAULT_STYLE)
    prepare.add_argument("--auto-fit", action="store_true")
    prepare.add_argument("--auto-fit-max-trials", type=int, default=12)
    prepare.add_argument("--compact", action="store_true")
    for name in (
        "font-size-scale",
        "line-height-scale",
        "section-spacing-scale",
        "item-spacing-scale",
        "margin-top-mm",
        "margin-bottom-mm",
        "margin-side-inch",
    ):
        prepare.add_argument("--" + name, type=float)
    publish.add_argument("--candidate-id", required=True)
    publish.add_argument("--review", required=True)
    publish.add_argument(
        "--output-file", help="Optional explicit rename; defaults to frozen candidate name"
    )
    publish.add_argument("--format", choices=("docx", "pdf", "both"), default="docx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        workspace = validate_workspace(args.workspace)
        if args.command == "prepare":
            overrides = {}
            for name in (
                "font_size_scale",
                "line_height_scale",
                "section_spacing_scale",
                "item_spacing_scale",
                "margin_top_mm",
                "margin_bottom_mm",
                "margin_side_inch",
            ):
                value = getattr(args, name)
                if value is not None:
                    if (
                        name.endswith("scale")
                        and not 0.7 <= value <= 1.3
                        or not name.endswith("scale")
                        and value <= 0
                    ):
                        raise ValueError(f"Invalid layout override: {name}")
                    overrides[name] = value
            layout = replace(get_style(args.style).layout, **overrides, compact_mode=args.compact)
            result = prepare_candidate(
                workspace,
                Path(args.draft),
                output_name=args.output_file,
                layout=layout,
                style=args.style,
                auto_fit=args.auto_fit,
                max_trials=args.auto_fit_max_trials,
                author_id=args.author_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result["render_error"] else (0 if result["qa_passed"] else 2)
        result = publish_candidate(
            workspace,
            args.candidate_id,
            load_json_file(Path(args.review)),
            output_name=args.output_file,
            output_format=args.format,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ReviewNotReady as exc:
        print(f"Not ready: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
