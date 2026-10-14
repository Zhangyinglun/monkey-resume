"""Read-only validation of host-produced Recruiter Review Reports.

No model invocation or publication takes place here. Quotes are checked against
the original JD and text extracted from the bound PDF, never hidden evidence.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.resume_shared import canonical_json_fingerprint, load_json_file

PROTOCOL_VERSION = "1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_NAMES = {"resume", "pdf", "jd", "manifest"}


class ReviewValidationError(ValueError):
    """An invalid or stale artifact must not appear as a current review."""

    def __init__(self, message: str, *, stale: bool = False) -> None:
        self.status = "stale" if stale else "invalid"
        super().__init__(f"Recruiter Review {self.status}: {message}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewValidationError(message)


def _object(value: Any, name: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{name} must be an object")
    return value


def _text(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} must be non-empty text")
    return value


def _items(value: Any, name: str, maximum: int | None = None) -> list[Any]:
    _require(isinstance(value, list), f"{name} must be an array")
    if maximum is not None:
        _require(len(value) <= maximum, f"{name} allows at most {maximum} items")
    return value


def _strings(value: Any, name: str, maximum: int | None = None) -> list[str]:
    values = _items(value, name, maximum)
    for item in values:
        _text(item, name)
    return values


def _choice(value: Any, choices: set[str], name: str) -> str:
    _require(isinstance(value, str) and value in choices, f"invalid {name}")
    return value


def _integer(value: Any, name: str, minimum: int = 1) -> int:
    _require(type(value) is int and value >= minimum, f"invalid {name}")
    return value


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name)
    _require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value)), f"invalid {name}")
    return value


def file_fingerprint(path: Path) -> str:
    """Hash the exact file bytes, including layout changes to a PDF."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _external(path: Path) -> Path:
    path = path.expanduser().resolve()
    _require(path != PROJECT_ROOT and PROJECT_ROOT not in path.parents,
             "personal review inputs must be outside the Skill package")
    return path


def pdf_page_texts(path: Path) -> list[str]:
    """Use the same PDF text backend as existing QA, retaining page boundaries."""
    import pdfplumber

    try:
        with pdfplumber.open(path) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise ReviewValidationError(f"cannot extract review PDF: {exc}") from exc


def capture_review_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    """Host helper: fingerprint supplied inputs and PDF page text before dispatch.

    Persist this snapshot before Phase A; use it in the final artifact unchanged.
    No artifact-provided paths are opened by the validator.
    """
    _require("resume" in paths and set(paths) <= TARGET_NAMES, "invalid target names")
    resolved = {name: _external(path) for name, path in paths.items()}
    targets = {name: file_fingerprint(path) for name, path in resolved.items()}
    pages = []
    if "pdf" in resolved:
        pages = [
            {"page": number, "text_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest()}
            for number, text in enumerate(pdf_page_texts(resolved["pdf"]), start=1)
        ]
    return {"targets": targets, "pages": pages}


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _phase(value: Any, jd: str) -> set[str]:
    phase = _object(value, "phase_a")
    _text(phase.get("role_problem"), "phase_a.role_problem")
    _text(phase.get("positioning"), "phase_a.positioning")
    _strings(phase.get("signals"), "phase_a.signals", 3)
    _strings(phase.get("questions"), "phase_a.questions", 3)
    requirements = _items(phase.get("requirements"), "phase_a.requirements")
    _require(bool(requirements), "phase_a.requirements must not be empty")
    lines = jd.splitlines()
    identifiers: set[str] = set()
    for value in requirements:
        item = _object(value, "requirement")
        identifier = _identifier(item.get("id"), "requirement.id")
        _require(identifier not in identifiers, "duplicate requirement id")
        identifiers.add(identifier)
        _choice(item.get("kind"), {"required", "preferred", "responsibility", "unclear"}, "requirement.kind")
        _text(item.get("alternatives"), "requirement.alternatives")
        quote = _text(item.get("quote"), "requirement.quote")
        start = _integer(item.get("start_line"), "requirement.start_line")
        end = _integer(item.get("end_line"), "requirement.end_line")
        _require(start <= end <= len(lines), "JD quote line range is invalid")
        _require(_normalized(quote) in _normalized("\n".join(lines[start - 1:end])),
                 "JD quote not found at specified lines")
    priorities = _strings(phase.get("priorities"), "phase_a.priorities", 3)
    _require(len(set(priorities)) == len(priorities) and set(priorities) <= identifiers,
             "priorities must reference unique requirement IDs")
    return identifiers


def _page_numbers(value: Any, name: str, page_count: int) -> set[int]:
    numbers = _items(value, name)
    for number in numbers:
        _integer(number, name)
        _require(number <= page_count, f"{name} contains an unknown page")
    _require(len(set(numbers)) == len(numbers), f"duplicate page in {name}")
    return set(numbers)


def validate_review(
    report: dict[str, Any],
    *,
    paths: dict[str, Path],
    phase_a_path: Path | None = None,
) -> dict[str, Any]:
    """Validate a host artifact against explicit current inputs without writing.

    Returns the original payload; validation status is computed, not model input.
    """
    _object(report, "review")
    _require(type(report.get("schema_version")) is int and report["schema_version"] == 1,
             "unsupported schema_version")
    _require(report.get("protocol_version") == PROTOCOL_VERSION, "unsupported protocol_version")
    _identifier(report.get("review_id"), "review_id")
    _require(_integer(report.get("attempt"), "attempt") <= 2, "attempt exceeds review budget")
    created = _text(report.get("created_at"), "created_at")
    try:
        timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewValidationError("created_at must be an ISO timestamp") from exc
    _require(timestamp.tzinfo is not None, "created_at must include a timezone")
    mode = _choice(report.get("review_mode"), {"independent_subagent", "self_review"}, "review_mode")
    status = _choice(report.get("execution_status"), {"complete", "incomplete", "unavailable"}, "execution_status")
    _require("model" in report, "model must be supplied (null when unknown)")
    if report["model"] is not None:
        _text(report["model"], "model")
    if mode == "independent_subagent" and status == "complete":
        _text(report.get("reviewer_id"), "reviewer_id")
    if mode == "self_review":
        attempt = _object(report.get("independent_attempt"), "independent_attempt")
        _choice(attempt.get("status"), {"unavailable", "incomplete"}, "independent_attempt.status")
        _text(attempt.get("reason"), "independent_attempt.reason")
        _identifier(attempt.get("review_id"), "independent_attempt.review_id")
    _strings(report.get("limitations"), "limitations")
    _strings(report.get("host_notes", []), "host_notes")
    if status != "complete":
        _text(report.get("reason"), "reason")

    targets = _object(report.get("targets"), "targets")
    _require(set(targets) == set(paths), "targets must exactly match supplied current inputs")
    for digest in targets.values():
        _require(isinstance(digest, str) and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", digest)),
                 "target fingerprints must be SHA-256 digests")
    if status == "complete":
        _require(set(paths) == TARGET_NAMES, "complete review requires resume, PDF, original JD and manifest")
    snapshot = capture_review_inputs(paths)
    if targets != snapshot["targets"]:
        raise ReviewValidationError("target fingerprints changed; re-review current files", stale=True)
    _require(report.get("pages") == snapshot["pages"], "page text binding differs from current PDF")
    for page in report["pages"]:
        _integer(page["page"], "pages.page")
    page_count = len(snapshot["pages"])
    modality = _choice(report.get("modality"), {"image_and_text", "text_only"}, "modality")
    available = _page_numbers(report.get("available_image_pages"), "available_image_pages", page_count)
    inspected = _page_numbers(report.get("inspected_image_pages"), "inspected_image_pages", page_count)
    _require(inspected <= available, "inspected image pages were not available")
    if modality == "text_only":
        _require(not inspected, "text_only cannot claim image inspection")
    elif status == "complete":
        _require(page_count > 0 and inspected == set(range(1, page_count + 1)),
                 "complete image review must inspect every PDF page")

    phase = report.get("phase_a")
    if phase is not None:
        _require("jd" in paths, "phase_a requires original JD")
        identifiers = _phase(phase, paths["jd"].read_text(encoding="utf-8"))
        _require(phase_a_path is not None, "provide --review-phase-a to verify the frozen snapshot")
        frozen = load_json_file(_external(phase_a_path))
        fingerprint = canonical_json_fingerprint(frozen)
        _require(report.get("phase_a_sha256") == fingerprint
                 and canonical_json_fingerprint(phase) == fingerprint,
                 "phase_a changed from the independently saved snapshot")
    else:
        identifiers = set()
        _require(phase_a_path is None and report.get("phase_a_sha256") is None,
                 "phase_a snapshot supplied without phase_a")
    if status != "complete":
        _require(report.get("recommendation") is None and not report.get("findings")
                 and not report.get("recommendations"), "unfinished review cannot carry a final verdict/findings")
        return report
    _require(phase is not None, "complete review requires phase_a")
    recommendation = _choice(report.get("recommendation"), {"yes", "maybe", "no"}, "recommendation")
    _text(report.get("rationale"), "rationale")
    _strings(report.get("doubts"), "doubts")
    page_text = pdf_page_texts(paths["pdf"])
    seen: set[str] = set()
    for value in _items(report.get("findings"), "findings"):
        finding = _object(value, "finding")
        identifier = _text(finding.get("requirement_id"), "finding.requirement_id")
        _require(identifier in identifiers and identifier not in seen, "unknown or duplicate finding requirement")
        seen.add(identifier)
        support = _choice(finding.get("support"), {"demonstrated", "partial", "not_shown", "contradicted"}, "finding.support")
        _choice(finding.get("visibility"), {"clear", "buried", "ambiguous", "absent"}, "finding.visibility")
        _text(finding.get("reason"), "finding.reason")
        if finding.get("question") is not None:
            _text(finding["question"], "finding.question")
        evidence = _items(finding.get("evidence"), "finding.evidence")
        if support != "not_shown":
            _require(bool(evidence), f"{support} requires resume evidence")
        for value in evidence:
            citation = _object(value, "resume citation")
            page = _integer(citation.get("page"), "citation.page")
            quote = _text(citation.get("quote"), "citation.quote")
            _require(page <= len(page_text), "resume citation references an unknown page")
            _require(_normalized(quote) in _normalized(page_text[page - 1]),
                     "resume quote not found on specified PDF page")
    _require(seen == identifiers, "missing requirement findings")
    # This check catches a contradictory contract, not semantic match quality.
    if recommendation == "yes":
        required = {r["id"] for r in phase["requirements"] if r["kind"] == "required"}
        _require(all(f["support"] == "demonstrated" for f in report["findings"]
                     if f["requirement_id"] in required),
                 "yes requires demonstrated support for each required item (preserve OR as one item)")
    advice_ids: set[str] = set()
    for value in _items(report.get("recommendations"), "recommendations", 3):
        advice = _object(value, "recommendation item")
        identifier = _identifier(advice.get("id"), "advice.id")
        _require(identifier not in advice_ids, "duplicate advice id")
        advice_ids.add(identifier)
        _choice(advice.get("kind"), {"presentation_fix", "needs_candidate_evidence", "genuine_gap"}, "advice.kind")
        _text(advice.get("text"), "advice.text")
        linked = _strings(advice.get("requirement_ids"), "advice.requirement_ids")
        _require(bool(linked) and set(linked) <= identifiers, "advice must reference known requirements")
        disposition = advice.get("disposition")
        if disposition is not None:
            disposition = _object(disposition, "disposition")
            _choice(disposition.get("status"), {"applied", "declined_with_reason", "needs_candidate_evidence"}, "disposition.status")
            _text(disposition.get("reason"), "disposition.reason")
    return report


def read_review(path: Path, *, paths: dict[str, Path], phase_a_path: Path | None = None) -> dict[str, Any]:
    """Load only explicitly supplied external files and validate before formatting."""
    return validate_review(load_json_file(_external(path)), paths=paths, phase_a_path=phase_a_path)


def _cell(value: Any) -> str:
    # Render untrusted JD/PDF/model text as text, not Markdown links or HTML.
    text = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_{}\[\]|#])", r"\\\1", text)


def format_review(report: dict[str, Any]) -> str:
    """Format a validated record; opinions never use the factual-audit PASS label."""
    lines = ["### Recruiter Review", "", "Simulation only; not a hiring decision or ATS score.", "",
             f"- Review: {_cell(report['review_id'])}; validation: valid",
             f"- Execution: {_cell(report['execution_status'])}; mode: {_cell(report['review_mode'])}",
             f"- Modality: {_cell(report['modality'])}"]
    if report["review_mode"] == "self_review":
        attempt = report["independent_attempt"]
        lines.append(f"- Independent review: {_cell(attempt['status'])} — {_cell(attempt['reason'])}")
    if report.get("reason"):
        lines.append(f"- Limitation reason: {_cell(report['reason'])}")
    phase = report.get("phase_a")
    if phase:
        lines.extend(["", "#### Frozen first impression", "", _cell(phase["positioning"]),
                      "", f"Role problem: {_cell(phase['role_problem'])}"])
        for key in ("signals", "questions"):
            for item in phase[key]:
                lines.append(f"- {key}: {_cell(item)}")
    if report["execution_status"] == "complete":
        lines.extend(["", f"Simulated screening: **{report['recommendation'].upper()}**", "",
                      _cell(report["rationale"]), "",
                      "| JD requirement / type / alternatives | Visible support | Visibility | PDF evidence | Reason / question |",
                      "|---|---|---|---|---|"])
        requirements = {r["id"]: r for r in phase["requirements"]}
        for finding in report["findings"]:
            requirement = requirements[finding["requirement_id"]]
            evidence = "; ".join(f"p.{c['page']}: {c['quote']}" for c in finding["evidence"]) or "Not shown"
            label = f"{requirement['quote']} (JD lines {requirement['start_line']}-{requirement['end_line']}; {requirement['kind']}; {requirement['alternatives']})"
            reason = finding["reason"] + (" / " + finding["question"] if finding.get("question") else "")
            lines.append("| " + " | ".join(_cell(x) for x in (label, finding["support"], finding["visibility"], evidence, reason)) + " |")
        lines.extend(["", "#### Doubts and prioritized recommendations", ""])
        for doubt in report["doubts"]:
            lines.append(f"- {_cell(doubt)}")
        for advice in report["recommendations"]:
            disposition = advice.get("disposition")
            resolution = f"{disposition['status']}: {disposition['reason']}" if disposition else "pending host disposition"
            lines.append(f"- {_cell(advice['kind'])}: {_cell(advice['text'])} — {_cell(resolution)}")
    lines.extend(["", "#### Scope and host notes", ""])
    for item in report["limitations"] + report.get("host_notes", []):
        lines.append(f"- {_cell(item)}")
    if report["modality"] == "text_only":
        lines.append("- Text only: no visual inspection is claimed by this review.")
    lines.extend(["- Quote and fingerprint validation does not prove semantic entailment or recruiting accuracy.", ""])
    return "\n".join(lines)
