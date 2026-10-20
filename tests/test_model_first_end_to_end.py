"""Public cache-to-draft regression using a synthetic, non-resume notes document."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.candidate_cache import commit_import, load_candidate_context, prepare_import
from scripts.draft_compiler import compile_draft
from scripts.generate_final_resume import ReviewNotReady, prepare_candidate, publish_candidate
from templates.style_profiles import DEFAULT_STYLE
from tests.rendering_support import rendering_available


def ingest_notes(root: Path) -> tuple[Path, dict, dict]:
    workspace = root / "candidate"
    source = root / "notes.md"
    source.write_text(
        "工程师资料笔记\nName: Alex Chen\nContact: alex@example.org\n"
        "Employer: Northstar Cloud\nRole: Software Engineer\nDates: 2022–Present\n"
        "Project: Queue Tools\nBuilt queue recovery using Python.\n"
        "School: Example University\nDegree: B.S. Computer Science\n"
        "Education dates: 2018\nProject Queue Tools belongs to Northstar Cloud.\n"
        "Work location: Seattle\n",
        encoding="utf-8",
    )
    prepared = prepare_import(workspace, source)
    entities = [
        {"ref": "person", "entity_type": "profile", "label": "Candidate"},
        {"ref": "job", "entity_type": "employment", "label": "Northstar Cloud"},
        {"ref": "queue", "entity_type": "project", "label": "Queue Tools"},
        {"ref": "edu", "entity_type": "education", "label": "Example University"},
    ]
    facts = [
        ("name", "person", "name", "Alex Chen", 2),
        ("contact", "person", "contact", "alex@example.org", 3),
        ("company", "job", "company", "Northstar Cloud", 4),
        ("title", "job", "title", "Software Engineer", 5),
        ("dates", "job", "dates", "2022–Present", 6),
        ("location", "job", "location", "Seattle", 13),
        ("work", "queue", "work", "Built queue recovery using Python.", 8),
        ("school", "edu", "school", "Example University", 9),
        ("degree", "edu", "degree", "B.S. Computer Science", 10),
        ("edu_dates", "edu", "dates", "2018", 11),
    ]
    proposal = {
        "context_id": prepared["context_id"],
        "entities": entities,
        "claims": [
            {
                "ref": ref,
                "entity_ref": entity,
                "field": field,
                "claim_text": text,
                "block_ids": [f"block-{line}"],
                "original_excerpt": text,
            }
            for ref, entity, field, text, line in facts
        ],
        "relationships": [
            {
                "project_ref": "queue",
                "employment_ref": "job",
                "block_ids": ["block-12"],
                "original_excerpt": "Project Queue Tools belongs to Northstar Cloud.",
            }
        ],
        "display_name_ref": "name",
    }
    report = commit_import(workspace, prepared["source_id"], proposal)
    context = load_candidate_context(workspace)
    ids = {e["entity_type"]: e["entity_id"] for e in context["ledger"]["entities"]}
    claims = {
        c["field"]: c["claim_id"]
        for e in context["ledger"]["entities"]
        for c in e["claims"]
        if c["field"] not in {"dates"}
    }
    draft = {
        "schema_version": 2,
        "context_id": context["context_id"],
        "target": {
            "original_jd": "Develop Python cloud infrastructure and queue recovery.",
            "requirements": [{"id": "reliability", "text": "Queue recovery", "priority": "P1"}],
            "company": "Example Target",
            "role": "Infrastructure Engineer",
        },
        "resume": {
            "name": "Alex Chen",
            "contact": "alex@example.org",
            "skills": [{"category": "Development", "items": ["Python"]}],
            "experience": [
                {
                    "company": "Northstar Cloud",
                    "title": "Software Engineer",
                    "dates": "2022–Present",
                    "location": "Seattle",
                    "bullets": ["Built queue recovery using Python."],
                }
            ],
            "education": [
                {"school": "Example University", "degree": "B.S. Computer Science", "dates": "2018"}
            ],
        },
        "evidence_links": {
            "name": {"claim_ids": [claims["name"]]},
            "contact": {"claim_ids": [claims["contact"]]},
            "skills[0].items[0]": {"claim_ids": [claims["work"]]},
            "experience[0]": {"entity_id": ids["employment"]},
            "experience[0].bullets[0]": {"claim_ids": [claims["work"]]},
            "education[0]": {"entity_id": ids["education"]},
        },
        "omissions": [],
    }
    return workspace, draft, report


class ModelFirstIntegrationTests(unittest.TestCase):
    def test_missing_required_fact_blocks_prepare_before_render_and_preserves_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, draft, _ = ingest_notes(Path(directory))
            draft["resume"]["experience"][0].pop("location")
            path = workspace / "draft.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            output = workspace / "resume_output"
            output.mkdir()
            prior = output / "resume.docx"
            prior.write_bytes(b"previously accepted")
            with patch("scripts.generate_final_resume.generate_resume") as render:
                with self.assertRaisesRegex(ValueError, r"experience\[0\].*location"):
                    prepare_candidate(workspace, path)
                render.assert_not_called()
            self.assertEqual(prior.read_bytes(), b"previously accepted")
            self.assertFalse((workspace / "resume_history").exists())

    def test_information_notes_can_compile_without_regex_resume_or_source_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, draft, _ = ingest_notes(Path(directory))
            context = load_candidate_context(workspace)
            compiled = compile_draft(draft, context)
            self.assertEqual(compiled["resume"]["name"], "Alex Chen")
            entry = next(
                e
                for e in compiled["manifest"]["entries"]
                if e["projection_path"] == "experience[0].bullets[0]"
            )
            self.assertEqual(len(entry["relationship_ids"]), 1)
            self.assertTrue(compiled["semantic_review_required"])
            self.assertFalse((workspace / "cache/base-resume.json").exists())


@unittest.skipUnless(
    rendering_available(), "LibreOffice, Poppler and Arial required"
)
class RealCandidateIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.render_style = DEFAULT_STYLE
        if not rendering_available():
            raise unittest.SkipTest("LibreOffice, Poppler and Arial required")

    def test_real_cache_render_review_gate_and_history_use_identical_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, draft, _ = ingest_notes(Path(directory))
            path = workspace / "draft.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            prepared = prepare_candidate(workspace, path, author_id="synthetic-test-writer", style=self.render_style)
            self.assertTrue(prepared["qa_passed"], prepared["physical_qa"])
            self.assertFalse((workspace / "resume_output").exists())
            self.assertFalse((workspace / "resume_history").exists())
            with self.assertRaises(ReviewNotReady):
                publish_candidate(workspace, prepared["candidate_id"], prepared["review_template"])
            # Synthetic approval tests gate mechanics only; this is not an actual
            # independent content review or a claim of visual inspection.
            review = prepared["review_template"]
            review.update(
                blind_reading={
                    "hiring_problem": "Synthetic cloud test",
                    "positioning": "Queue engineer",
                    "requirements": [{"original_quote": draft["target"]["original_jd"]}],
                },
                evidence_review={
                    **review["evidence_review"],
                    "status": "complete",
                    "context_id": review["context_id"],
                    "assertion_review": "Synthetic test fixture; not real review.",
                    "omission_review": "Synthetic test fixture; not real review.",
                },
                review_context={
                    "mode": "independent_subagent",
                    "identifier": "synthetic-test-reviewer",
                },
            )
            for result in review["evidence_review"]["fact_review"].values():
                result.update(
                    status="pass",
                    checked_paths=list(result["expected_paths"]),
                    accuracy_review="Synthetic test fixture; not real review.",
                    completeness_review="Synthetic test fixture; not real review.",
                )
            review["content"].update(
                status="complete",
                verdict="pass",
                independent=True,
                reviewer_id="synthetic-test-reviewer",
            )
            review["visual"].update(
                status="pass", method="direct_docx", pages=[1],
                reader={"name": "Synthetic reader", "version": "test-only"},
                observations="Synthetic direct-DOCX observation; tests gate mechanics only.",
                docx_preview_inspected=True, pdf_preview_inspected=True,
            )
            accepted = publish_candidate(
                workspace, prepared["candidate_id"], review, output_format="both"
            )
            self.assertEqual(accepted["status"], "published")
            self.assertEqual(
                Path(accepted["historical_pdf"]).read_bytes(), Path(prepared["pdf"]).read_bytes()
            )
            for output in accepted["outputs"]:
                key = Path(output).suffix[1:]
                self.assertEqual(Path(output).read_bytes(), Path(prepared[key]).read_bytes())
            from scripts.extract_resume_text import extract_resume_blocks

            extracted = extract_resume_blocks(Path(prepared["pdf"]))
            self.assertTrue(all(b["location"]["page"] == 1 for b in extracted))
            self.assertIn("Alex Chen", "\n".join(b["text"] for b in extracted))

    def test_real_source_conflict_invalidates_frozen_candidate_without_losing_accepted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, draft, report = ingest_notes(Path(directory))
            path = workspace / "draft.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            prepared = prepare_candidate(workspace, path, style=self.render_style)
            output = workspace / "resume_output"
            output.mkdir()
            prior = output / "resume.docx"
            prior.write_bytes(b"previously accepted")
            source = Path(directory) / "conflicting-note.txt"
            source.write_text("Conflicting note: did not build queue recovery.", encoding="utf-8")
            pending = prepare_import(workspace, source, source_type="candidate_response")
            proposal = {
                "context_id": pending["context_id"],
                "claims": [
                    {
                        "ref": "denial",
                        "entity_ref": report["entity_ids"]["queue"],
                        "claim_text": "Did not build queue recovery.",
                        "polarity": "negative",
                        "block_ids": ["block-1"],
                        "original_excerpt": "did not build queue recovery.",
                    }
                ],
                "conflicts": [
                    {
                        "claim_refs": [report["claim_ids"]["work"], "denial"],
                        "reason": "Work ownership is disputed.",
                    }
                ],
            }
            commit_import(workspace, pending["source_id"], proposal)
            with self.assertRaisesRegex(ValueError, "stale"):
                publish_candidate(workspace, prepared["candidate_id"], prepared["review_template"])
            self.assertEqual(prior.read_bytes(), b"previously accepted")
            self.assertFalse((workspace / "resume_history").exists())


if __name__ == "__main__":
    unittest.main()
