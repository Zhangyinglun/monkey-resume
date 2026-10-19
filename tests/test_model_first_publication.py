"""Publication contract tests with external rendering/QA seams mocked."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from scripts import generate_final_resume as publication


class PublicationTests(unittest.TestCase):
    def test_no_jd_scope_quote_works_without_invented_job_requirements(self) -> None:
        self.compiled["target"]["original_jd"] = "Please send a general recruiter resume."
        prepared = self.prepare()
        review = self.review(prepared)
        review["blind_reading"]["requirements"] = [{
            "kind": "scope_only",
            "original_quote": self.compiled["target"]["original_jd"],
            "assessment": "No job-specific requirements were provided.",
        }]
        record = json.loads(Path(prepared["record"]).read_text(encoding="utf-8"))
        self.assertEqual(record["target"]["requirements"], [])
        publication._validate_review(review, record)
        review["blind_reading"]["requirements"][0]["original_quote"] = "Invented qualification"
        with self.assertRaises(publication.ReviewNotReady):
            publication._validate_review(review, record)

    def test_status_flags_without_actual_review_results_are_not_ready(self) -> None:
        prepared = self.prepare()
        for missing in ("blind_reading", "evidence_review", "review_context"):
            review = self.review(prepared)
            review.pop(missing, None)
            with self.subTest(missing=missing), self.assertRaises(publication.ReviewNotReady):
                publication.publish_candidate(self.workspace, prepared["candidate_id"], review)
        review = self.review(prepared)
        review["evidence_review"] = {
            "status": "complete",
            "context_id": prepared["review_template"]["context_id"],
            "assertion_review": "",
            "omission_review": "",
        }
        with self.assertRaises(publication.ReviewNotReady):
            publication.publish_candidate(self.workspace, prepared["candidate_id"], review)

    def test_publish_cli_keeps_frozen_custom_filename(self) -> None:
        prepared = publication.prepare_candidate(
            self.workspace,
            self.draft,
            output_name="target.docx",
            author_id="writer",
        )
        output = self.workspace / "resume_output"
        output.mkdir()
        (output / "resume.docx").write_bytes(b"another accepted resume")
        review_file = self.workspace / "review.json"
        review_file.write_text(json.dumps(self.review(prepared)), encoding="utf-8")
        with patch.object(
            sys,
            "argv",
            [
                "generate_final_resume.py",
                "publish",
                "--workspace",
                str(self.workspace),
                "--candidate-id",
                prepared["candidate_id"],
                "--review",
                str(review_file),
            ],
        ):
            self.assertEqual(publication.main(), 0)
        self.assertTrue((output / "target.docx").is_file())
        self.assertEqual((output / "resume.docx").read_bytes(), b"another accepted resume")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.draft = self.workspace / "draft.json"
        self.draft.write_text('{"text": "model prose"}', encoding="utf-8")
        self.context = {"context_id": "context-1", "candidate_id": "person-1"}
        self.compiled = {
            "schema_version": 2,
            **self.context,
            "draft_fingerprint": "draft-1",
            "resume_fingerprint": "resume-1",
            "resume": {"experience": [{"bullets": ["model prose"]}]},
            "target": {
                "original_jd": "JD",
                "requirements": [],
                "company": "Acme",
                "role": "Engineer",
                "job_url": "https://example.com/job",
            },
            "manifest": {},
            "omissions": [],
        }
        self.qa = {
            "verdict": "PASS",
            "checks": [
                {
                    "name": name,
                    "passed": True,
                    "detail": {"count": 1}
                    if name == "page_count"
                    else ({"measured": True} if name == "font_readability" else {}),
                }
                for name in (
                    "page_count",
                    "page_size",
                    "text_layer",
                    "page_bounds",
                    "font_readability",
                    "text_geometry",
                )
            ],
        }
        for name, replacement in (
            ("validate_workspace", lambda p: Path(p).resolve()),
            ("workspace_lock", lambda p: nullcontext()),
            ("load_candidate_context", lambda p: copy.deepcopy(self.context)),
            ("compile_draft", lambda d, c: {**copy.deepcopy(self.compiled), **c}),
            ("generate_resume", self.render),
            ("check_pdf_file", lambda p, **kwargs: copy.deepcopy(self.qa)),
            ("rendering_environment", lambda **kwargs: {"renderer_version": "synthetic test environment"}),
            ("validate_pdf_fonts", lambda *args: {"verified": True, "font_family": "Arial", "actual_fonts": ["synthetic-font-check"]}),
        ):
            mock = patch.object(publication, name, replacement, create=True)
            mock.start()
            self.addCleanup(mock.stop)

    def render(self, name: str, content: dict, base_dir: str, layout: object, *, style: str) -> str:
        pdf = Path(base_dir) / name
        pdf.write_bytes(b"%PDF mock actual artifact")
        pdf.with_suffix(".docx").write_bytes(b"DOCX mock actual artifact")
        return str(pdf)

    def test_default_compact_cli_and_auto_fit_remain_usable(self) -> None:
        from dataclasses import replace

        from scripts.layout_auto_tuner import AutoFitResult
        from templates.style_profiles import get_style

        for auto in (False, True):
            args = ["generate_final_resume.py", "prepare", "--workspace", str(self.workspace),
                    "--draft", str(self.draft), "--compact"]
            if auto:
                args.append("--auto-fit")
            compact = get_style().resolve_layout(replace(get_style().layout, compact_mode=True))
            with self.subTest(auto=auto), patch.object(sys, "argv", args), patch.object(
                publication, "auto_fit_layout", return_value=AutoFitResult(compact, self.qa, 1)
            ), patch("builtins.print"):
                self.assertEqual(publication.main(), 0)

    def test_style_and_final_auto_fit_layout_are_frozen(self) -> None:
        from dataclasses import replace

        from scripts.layout_auto_tuner import AutoFitResult
        from templates.style_profiles import get_style

        selected = replace(get_style().layout, item_spacing_scale=0.8)
        with patch.object(publication, "auto_fit_layout", return_value=AutoFitResult(selected, self.qa, 2)):
            prepared = publication.prepare_candidate(self.workspace, self.draft, auto_fit=True, author_id="writer")
        self.assertTrue(prepared["qa_passed"], prepared["render_error"])
        record = json.loads(Path(prepared["record"]).read_text(encoding="utf-8"))
        self.assertEqual(record["style"]["name"], "professional-v3")
        self.assertEqual(record["style"]["layout"]["item_spacing_scale"], 0.8)
        self.assertEqual(record["rendering_environment"]["renderer_version"], "synthetic test environment")
        with patch.object(publication, "check_pdf_file", return_value=self.qa) as check:
            publication.publish_candidate(self.workspace, prepared["candidate_id"], self.review(prepared))
        self.assertEqual(check.call_args.kwargs["minimum_font_pt"], 10.5)

    def prepare(self) -> dict:
        return publication.prepare_candidate(self.workspace, self.draft, author_id="writer")

    def review(self, prepared: dict) -> dict:
        review = copy.deepcopy(prepared["review_template"])
        review.update(
            blind_reading={
                "hiring_problem": "Synthetic service need",
                "positioning": "Synthetic writer",
                "requirements": [{"original_quote": "JD"}],
            },
            evidence_review={
                "status": "complete",
                "context_id": review["context_id"],
                "assertion_review": "Synthetic review record for gate-mechanics test only.",
                "omission_review": "No factual completeness claim; test fixture only.",
            },
            review_context={"mode": "independent_subagent", "identifier": "synthetic-review-test"},
        )
        review["content"].update(
            status="complete", verdict="pass", reviewer_id="reviewer", independent=True
        )
        review["visual"].update(
            status="pass", pages=[1], docx_preview_inspected=True, pdf_preview_inspected=True
        )
        return review

    def test_prepare_never_accepts_or_registers(self) -> None:
        prepared = self.prepare()
        self.assertEqual(prepared["status"], "prepared")
        self.assertFalse((self.workspace / "resume_output").exists())
        self.assertFalse((self.workspace / "resume_history").exists())
        self.assertEqual(prepared["review_template"]["content"]["status"], "pending")

    def test_valid_publish_has_target_history_and_preserves_candidate(self) -> None:
        prepared = self.prepare()
        result = publication.publish_candidate(
            self.workspace, prepared["candidate_id"], self.review(prepared)
        )
        self.assertEqual(result["status"], "published")
        historical = Path(result["historical_pdf"])
        metadata = json.loads((historical.parent / "record.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["company"], "Acme")
        self.assertEqual(metadata["job_title"], "Engineer")
        self.assertTrue(Path(prepared["pdf"]).is_file())

    def test_invalid_review_denials(self) -> None:
        prepared = self.prepare()
        for change in (
            lambda r: r.clear(),
            lambda r: r["content"].update(status="incomplete"),
            lambda r: r["content"].update(reviewer_id="writer"),
            lambda r: r.update(candidate_id="foreign"),
            lambda r: r.update(context_id="old"),
            lambda r: r.update(pdf_sha256="forged"),
            lambda r: r["visual"].update(pdf_preview_inspected=False),
            lambda r: r["visual"].update(pages=[]),
            lambda r: r["content"].update(findings=[{"severity": "blocking"}]),
        ):
            with self.subTest(change=change):
                review = self.review(prepared)
                change(review)
                with self.assertRaises(ValueError):
                    publication.publish_candidate(self.workspace, prepared["candidate_id"], review)
                self.assertFalse((self.workspace / "resume_history").exists())

    def test_stale_cache_and_changed_artifact_rejected(self) -> None:
        prepared = self.prepare()
        review = self.review(prepared)
        self.context["context_id"] = "changed-cache-conflict"
        with self.assertRaises(ValueError):
            publication.publish_candidate(self.workspace, prepared["candidate_id"], review)
        self.context["context_id"] = "context-1"
        Path(prepared["pdf"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            publication.publish_candidate(self.workspace, prepared["candidate_id"], review)

    def test_failed_qa_keeps_candidate_and_accepted(self) -> None:
        output = self.workspace / "resume_output"
        output.mkdir()
        (output / "resume.docx").write_bytes(b"accepted")
        self.qa["checks"][0]["passed"] = False
        self.qa["checks"][0]["detail"]["count"] = 2
        self.qa["verdict"] = "NEED-ADJUSTMENT"
        prepared = self.prepare()
        with self.assertRaises(ValueError):
            publication.publish_candidate(
                self.workspace, prepared["candidate_id"], self.review(prepared)
            )
        self.assertEqual((output / "resume.docx").read_bytes(), b"accepted")
        self.assertTrue(Path(prepared["pdf"]).exists())
        self.assertFalse((self.workspace / "resume_history").exists())

    def test_font_substitution_at_publication_preserves_accepted_generation(self) -> None:
        prepared = self.prepare()
        publication.publish_candidate(self.workspace, prepared["candidate_id"], self.review(prepared))
        old_files = {
            path: path.read_bytes()
            for folder in ("resume_output", "resume_history")
            for path in (self.workspace / folder).rglob("*") if path.is_file()
        }
        replacement = self.prepare()
        for message in ("Arial was substituted", "Arial Bold face missing"):
            with self.subTest(message=message), patch.object(
                publication, "validate_pdf_fonts", side_effect=RuntimeError(message)
            ):
                with self.assertRaisesRegex(publication.ReviewNotReady, message):
                    publication.publish_candidate(
                        self.workspace, replacement["candidate_id"], self.review(replacement)
                    )
        self.assertEqual({path: path.read_bytes() for path in old_files}, old_files)
        self.assertEqual(len(list((self.workspace / "resume_history").glob("generation-*"))), 1)

    def test_publication_move_failure_rolls_back_history_and_accepted(self) -> None:
        prepared = self.prepare()
        publication.publish_candidate(
            self.workspace, prepared["candidate_id"], self.review(prepared)
        )
        index = self.workspace / "resume_history" / "index.html"
        old_index = index.read_bytes()
        output = self.workspace / "resume_output"
        (output / "resume.docx").write_bytes(b"old docx")
        (output / "resume.pdf").write_bytes(b"old pdf")
        original = Path.replace

        def fail_new(source: Path, target: Path) -> Path:
            if source.parent.name.startswith(".publication-") and source.suffix == ".pdf":
                raise OSError("injected move failure")
            return original(source, target)

        with patch.object(Path, "replace", fail_new), self.assertRaises(OSError):
            publication.publish_candidate(
                self.workspace,
                prepared["candidate_id"],
                self.review(prepared),
                output_format="both",
            )
        self.assertEqual((output / "resume.docx").read_bytes(), b"old docx")
        self.assertEqual((output / "resume.pdf").read_bytes(), b"old pdf")
        self.assertEqual(index.read_bytes(), old_index)
        self.assertEqual(len(list(index.parent.glob("generation-*"))), 1)

    def test_counterpart_retired(self) -> None:
        prepared = self.prepare()
        output = self.workspace / "resume_output"
        output.mkdir()
        (output / "resume.pdf").write_bytes(b"old pdf")
        publication.publish_candidate(
            self.workspace, prepared["candidate_id"], self.review(prepared)
        )
        self.assertFalse((output / "resume.pdf").exists())
        self.assertEqual(next((output / "backup").rglob("*.pdf")).read_bytes(), b"old pdf")

    def test_renderer_failure_retains_inputs_without_history(self) -> None:
        with patch.object(
            publication, "generate_resume", side_effect=RuntimeError("office unavailable")
        ):
            prepared = self.prepare()
        self.assertIn("office unavailable", prepared["render_error"])
        self.assertTrue(Path(prepared["draft"]).exists())
        self.assertTrue(Path(prepared["record"]).exists())
        with self.assertRaises(ValueError):
            publication.publish_candidate(
                self.workspace, prepared["candidate_id"], self.review(prepared)
            )
        self.assertFalse((self.workspace / "resume_history").exists())

    def test_rechecks_physical_qa_not_review_verdict(self) -> None:
        prepared = self.prepare()
        self.qa["checks"].append({"name": "clipping", "passed": False})
        with self.assertRaises(ValueError):
            publication.publish_candidate(
                self.workspace, prepared["candidate_id"], self.review(prepared)
            )
        self.assertFalse((self.workspace / "resume_history").exists())

    def test_style_advisories_do_not_need_dispositions(self) -> None:
        self.qa["checks"].extend(
            [
                {"name": name, "passed": False}
                for name in (
                    "contact_info",
                    "section_completeness",
                    "keyword_coverage",
                    "layout_warnings",
                    "text_geometry",
                )
            ]
        )
        self.qa["verdict"] = "NEED-ADJUSTMENT"
        prepared = self.prepare()
        self.assertTrue(prepared["qa_passed"])
        result = publication.publish_candidate(
            self.workspace, prepared["candidate_id"], self.review(prepared)
        )
        self.assertEqual(result["status"], "published")

    def test_frozen_draft_compilation_and_record_tampering_rejected(self) -> None:
        for filename in ("draft.json", "compiled.json", "candidate-record.json"):
            with self.subTest(filename=filename):
                prepared = self.prepare()
                path = Path(prepared["candidate_dir"]) / filename
                path.write_text("{}", encoding="utf-8")
                with self.assertRaises(ValueError):
                    publication.publish_candidate(
                        self.workspace, prepared["candidate_id"], self.review(prepared)
                    )
                self.assertFalse((self.workspace / "resume_history").exists())

    def test_safe_paths_and_ids(self) -> None:
        for name in ("../resume.docx", "a/b.docx", "a\\b.docx", "resume.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.prepare_candidate(self.workspace, self.draft, output_name=name)
        for candidate_id in ("../other", "", "not-a-uuid"):
            with self.subTest(candidate_id=candidate_id), self.assertRaises(ValueError):
                publication.publish_candidate(self.workspace, candidate_id, {})


if __name__ == "__main__":
    unittest.main()
