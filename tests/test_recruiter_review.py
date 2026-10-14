from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.recruiter_review import capture_review_inputs
from scripts.resume_shared import canonical_json_fingerprint, write_json_file
from templates.modern_resume_template import generate_resume
from tests.test_pdf_pipeline import prepare_audited_workspace, sample_resume

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "generate_quality_report.py"


class RecruiterReviewCliTests(unittest.TestCase):
    """Exercise the public report entrypoint with actual external PDF/audit inputs."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        resume = sample_resume()
        self.resume = prepare_audited_workspace(self.root, resume)
        self.pdf = Path(generate_resume("accepted.pdf", resume, base_dir=str(self.root)))
        self.manifest = self.root / "cache/resume-changes.json"
        self.jd = self.root / "job.txt"
        self.jd.write_text(
            "Required: Python backend development.\nPreferred: Kafka.\n", encoding="utf-8"
        )
        self.phase_path = self.root / "review/phase-a.json"
        self.report_path = self.root / "review/report.json"
        self.paths = {
            "resume": self.resume,
            "pdf": self.pdf,
            "manifest": self.manifest,
            "jd": self.jd,
        }
        self.phase = {
            "role_problem": "Build backend services.",
            "positioning": "Backend engineer with cloud experience.",
            "signals": ["Python listed in skills."],
            "questions": ["Where is the Python production work?"],
            "priorities": ["python"],
            "requirements": [
                {
                    "id": "python",
                    "kind": "required",
                    "quote": "Required: Python backend development.",
                    "start_line": 1,
                    "end_line": 1,
                    "alternatives": "Python required; no alternative specified.",
                },
                {
                    "id": "kafka",
                    "kind": "preferred",
                    "quote": "Preferred: Kafka.",
                    "start_line": 2,
                    "end_line": 2,
                    "alternatives": "Optional.",
                },
            ],
        }
        self.report = {
            "schema_version": 1,
            "protocol_version": "1",
            "review_id": "test-review-1",
            "attempt": 1,
            "created_at": "2026-09-18T01:00:00Z",
            "model": None,
            "reviewer_id": "synthetic-reviewer",
            "review_mode": "independent_subagent",
            "execution_status": "complete",
            "modality": "text_only",
            "available_image_pages": [],
            "inspected_image_pages": [],
            **capture_review_inputs(self.paths),
            "phase_a": copy.deepcopy(self.phase),
            "phase_a_sha256": canonical_json_fingerprint(self.phase),
            "findings": [
                {
                    "requirement_id": "python",
                    "support": "demonstrated",
                    "visibility": "clear",
                    "evidence": [
                        {"page": 1, "quote": "Built distributed APIs using Python and AWS"}
                    ],
                    "reason": "Actual Python API development is described.",
                    "question": None,
                },
                {
                    "requirement_id": "kafka",
                    "support": "not_shown",
                    "visibility": "absent",
                    "evidence": [],
                    "reason": "Kafka is not shown; it is only preferred.",
                    "question": None,
                },
            ],
            "recommendation": "yes",
            "rationale": "Required Python practice is visible.",
            "doubts": ["Kafka experience is unknown."],
            "recommendations": [
                {
                    "id": "advice-1",
                    "kind": "needs_candidate_evidence",
                    "text": "Confirm Kafka only if relevant.",
                    "requirement_ids": ["kafka"],
                    "disposition": {
                        "status": "declined_with_reason",
                        "reason": "Not essential to this target.",
                    },
                }
            ],
            "limitations": ["Fictional text-only test, not human recruiting validation."],
            "host_notes": [],
        }
        write_json_file(self.phase_path, self.phase)

    def command(self, *, review: bool = True, phase: bool = True, full: bool = True) -> list[str]:
        args = [sys.executable, str(CLI), "--resume", str(self.resume)]
        if full:
            args += [
                "--pdf",
                str(self.pdf),
                "--manifest",
                str(self.manifest),
                "--base",
                str(self.root / "cache/base-resume.json"),
                "--evidence",
                str(self.root / "cache/candidate-evidence.json"),
            ]
        if review:
            args += ["--recruiter-review", str(self.report_path)]
            if full:
                args += ["--original-jd", str(self.jd)]
            if phase:
                args += ["--review-phase-a", str(self.phase_path)]
        return args

    def run_report(
        self, report: dict[str, Any] | None = None, **options: bool
    ) -> subprocess.CompletedProcess[str]:
        write_json_file(self.report_path, self.report if report is None else report)
        return subprocess.run(
            self.command(**options),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_valid_complete_report_and_legacy_call_are_read_only(self) -> None:
        before = {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Frozen first impression", result.stdout)
        self.assertIn("Simulated screening: **YES**", result.stdout)
        self.assertIn("Preferred: Kafka", result.stdout)
        self.assertIn("p.1", result.stdout)
        self.assertIn("Text only: no visual inspection", result.stdout)
        legacy = self.run_report(review=False)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertNotIn("Recruiter Review", legacy.stdout)
        for path, digest in before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_complete_maybe_and_no_do_not_fail_qa(self) -> None:
        for verdict in ("maybe", "no"):
            with self.subTest(verdict=verdict):
                report = copy.deepcopy(self.report)
                report["recommendation"] = verdict
                report["rationale"] = "Synthetic opinion; no deterministic QA failure."
                result = self.run_report(report)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"**{verdict.upper()}**", result.stdout)

    def test_review_uses_durable_qa_pdf_without_current_output_pdf(self) -> None:
        from scripts.resume_history_manager import register_generation

        with register_generation(self.root, self.pdf, "Target", "Engineer", "") as historical:
            pass
        self.pdf.unlink()
        self.pdf = historical
        self.paths["pdf"] = historical
        self.report.update(capture_review_inputs(self.paths))
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Simulated screening: **YES**", result.stdout)

    def test_missing_subagent_jd_timeout_and_failure_are_honest_statuses(self) -> None:
        for status, reason in (
            ("unavailable", "Host has no subagent support"),
            ("unavailable", "Original JD is missing"),
            ("incomplete", "Reviewer timeout"),
            ("incomplete", "Reviewer cannot resume"),
        ):
            with self.subTest(reason=reason):
                report = copy.deepcopy(self.report)
                report.update(
                    execution_status=status,
                    reason=reason,
                    phase_a=None,
                    phase_a_sha256=None,
                    recommendation=None,
                    findings=[],
                    recommendations=[],
                )
                report.update(capture_review_inputs({"resume": self.resume}))
                result = self.run_report(report, full=False, phase=False)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(reason, result.stdout)
                self.assertNotIn("Simulated screening:", result.stdout)

    def test_incomplete_preserves_frozen_phase_and_self_review_is_not_independent(self) -> None:
        report = copy.deepcopy(self.report)
        report.update(
            execution_status="incomplete",
            reason="Phase B failed",
            recommendation=None,
            findings=[],
            recommendations=[],
        )
        result = self.run_report(report)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(self.phase["positioning"], result.stdout)
        report = copy.deepcopy(self.report)
        report["review_mode"] = "self_review"
        report["independent_attempt"] = {
            "status": "unavailable",
            "reason": "No subagent tool",
            "review_id": "independent-1",
        }
        result = self.run_report(report)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("No subagent tool", result.stdout)
        report.pop("independent_attempt")
        self.assertEqual(self.run_report(report).returncode, 1)

    def test_stale_inputs_are_not_displayed_as_current(self) -> None:
        for name, path in self.paths.items():
            with self.subTest(target=name):
                old = path.read_bytes()
                # Whitespace changes are valid input syntax but change exact artifact bytes.
                path.write_bytes(old + b"\n")
                try:
                    result = self.run_report()
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("stale", result.stderr)
                    self.assertNotIn("Simulated screening:", result.stdout)
                finally:
                    path.write_bytes(old)

    def test_phase_snapshot_cannot_be_changed_or_omitted(self) -> None:
        report = copy.deepcopy(self.report)
        report["phase_a"]["positioning"] = "Already proven expert"
        # Rehashing the embedded payload alone cannot bypass the separately frozen file.
        report["phase_a_sha256"] = canonical_json_fingerprint(report["phase_a"])
        result = self.run_report(report)
        self.assertEqual(result.returncode, 1)
        self.assertIn("phase_a changed", result.stderr)
        self.assertEqual(self.run_report(phase=False).returncode, 1)

    def test_requirement_coverage_quotes_and_enumerations(self) -> None:
        cases = []
        for field, value in (
            ("schema_version", 9),
            ("protocol_version", "future"),
            ("execution_status", "passed"),
            ("recommendation", "87%"),
            ("attempt", 3),
            ("created_at", "yesterday"),
        ):
            report = copy.deepcopy(self.report)
            report[field] = value
            cases.append((field, report))
        report = copy.deepcopy(self.report)
        report["findings"].pop()
        cases.append(("missing finding", report))
        report = copy.deepcopy(self.report)
        report["findings"].append(copy.deepcopy(report["findings"][0]))
        cases.append(("duplicate finding", report))
        for field, value in (("page", 2), ("quote", "Invented Kubernetes leadership")):
            report = copy.deepcopy(self.report)
            report["findings"][0]["evidence"][0][field] = value
            cases.append((field, report))
        report = copy.deepcopy(self.report)
        report["findings"][0]["support"] = "maybe"
        cases.append(("support enum", report))
        report = copy.deepcopy(self.report)
        report["findings"][0]["evidence"] = []
        cases.append(("unsupported demonstration", report))
        report = copy.deepcopy(self.report)
        report["pages"][0]["text_sha256"] = "sha256:wrong"
        cases.append(("page binding", report))
        for name, report in cases:
            with self.subTest(case=name):
                result = self.run_report(report)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_jd_quotes_checked_even_when_phase_hash_matches(self) -> None:
        report = copy.deepcopy(self.report)
        report["phase_a"]["requirements"][0]["quote"] = "Required: ten years of Kafka."
        write_json_file(self.phase_path, report["phase_a"])
        report["phase_a_sha256"] = canonical_json_fingerprint(report["phase_a"])
        result = self.run_report(report)
        self.assertEqual(result.returncode, 1)
        self.assertIn("JD quote not found", result.stderr)

    def test_partial_required_item_cannot_be_yes_but_preferred_gap_can(self) -> None:
        report = copy.deepcopy(self.report)
        report["findings"][0]["support"] = "partial"
        result = self.run_report(report)
        self.assertEqual(result.returncode, 1)
        self.assertIn("yes requires demonstrated", result.stderr)
        report["recommendation"] = "maybe"
        self.assertEqual(self.run_report(report).returncode, 0)

    def test_modality_and_image_page_claims_are_consistent(self) -> None:
        report = copy.deepcopy(self.report)
        report.update(available_image_pages=[1], inspected_image_pages=[1])
        self.assertEqual(self.run_report(report).returncode, 1)
        report["modality"] = "image_and_text"
        self.assertEqual(self.run_report(report).returncode, 0)
        report["inspected_image_pages"] = []
        self.assertEqual(self.run_report(report).returncode, 1)

    def test_existing_factual_failure_cannot_be_overridden(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["resume_fingerprint"] = "sha256:" + "0" * 64
        write_json_file(self.manifest, manifest)
        report = copy.deepcopy(self.report)
        report.update(capture_review_inputs(self.paths))
        result = self.run_report(report)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("FAIL", result.stdout)

    def test_existing_pdf_failure_cannot_be_overridden(self) -> None:
        from reportlab.pdfgen import canvas

        pdf = canvas.Canvas(str(self.pdf))
        pdf.drawString(40, 760, "Built distributed APIs using Python and AWS")
        pdf.showPage()
        pdf.drawString(40, 760, "A second page violates the existing one-page policy.")
        pdf.save()
        report = copy.deepcopy(self.report)
        report.update(capture_review_inputs(self.paths))
        result = self.run_report(report)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("page_count | ✗ FAIL", result.stdout)
        self.assertIn("Simulated screening: **YES**", result.stdout)

    def test_external_artifact_path_cannot_resolve_inside_package(self) -> None:
        link = self.root / "package-review.json"
        link.symlink_to(ROOT / "tests/fixtures/projection/jd-applied-ai.json")
        args = self.command()
        args[args.index("--recruiter-review") + 1] = str(link)
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the Skill package", result.stderr)

    def test_malformed_nested_payloads_do_not_raise_tracebacks(self) -> None:
        for field, value in (
            ("limitations", None),
            ("findings", [None]),
            ("phase_a", []),
            ("available_image_pages", [True]),
            ("recommendations", [{}]),
            ("targets", []),
        ):
            with self.subTest(field=field):
                report = copy.deepcopy(self.report)
                report[field] = value
                result = self.run_report(report)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_file_and_incomplete_target_bundle_fail_closed(self) -> None:
        result = self.run_report(full=False)
        self.assertEqual(result.returncode, 1)
        self.report_path.unlink()
        result = subprocess.run(self.command(), cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)

    def test_untrusted_model_text_is_not_active_markdown(self) -> None:
        report = copy.deepcopy(self.report)
        report["rationale"] = (
            "<script>alert(1)</script> [click](https://example.invalid) | injected"
        )
        result = self.run_report(report)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("<script>", result.stdout)
        self.assertNotIn("[click](https://", result.stdout)


if __name__ == "__main__":
    unittest.main()
