"""Contract regressions for the model-authored draft / context seam."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.draft_compiler import compile_draft, main


def fixture() -> tuple[dict, dict]:
    def entity(eid: str, kind: str, fields: dict) -> dict:
        return {
            "entity_id": eid,
            "entity_type": kind,
            "label": eid,
            "state": "active",
            "claims": [
                {
                    "claim_id": f"{eid}-{field}",
                    "claim_text": text,
                    "field": field,
                    "polarity": "positive",
                    "status": "active",
                    "evidence_state": "candidate_confirmed",
                    "provenance": [
                        {
                            "source_id": "answer",
                            "block_ids": [],
                            "original_excerpt": text,
                            "source_type": "candidate_answer",
                        }
                    ],
                    "supersedes": [],
                }
                for field, text in fields.items()
            ],
        }

    entities = [
        entity("person", "profile", {"name": "Correct Name", "contact": "a@example.test"}),
        entity(
            "job1",
            "employment",
            {
                "company": "Same Corp",
                "title": "Engineer",
                "dates": "2020–2022",
                "work": "Built services",
            },
        ),
        entity(
            "job2",
            "employment",
            {"company": "Same Corp", "title": "Lead", "dates": "2023–2025", "work": "Led platform"},
        ),
        entity("proj", "project", {"name": "Platform", "work": "Reduced latency"}),
        entity("edu", "education", {"school": "University", "degree": "BSc", "dates": "2019"}),
        entity("skill", "skill", {"tool": "Python"}),
    ]
    context = {
        "schema_version": 2,
        "candidate_id": "candidate",
        "context_id": "sha256:current",
        "ledger": {
            "entities": entities,
            "relationships": [
                {
                    "relationship_id": "owns",
                    "project_id": "proj",
                    "employment_id": "job2",
                    "state": "active",
                    "provenance": [{"original_excerpt": "Project at second job"}],
                }
            ],
            "conflicts": [],
        },
        "profile": {"preferences": {}, "display_name_claim_id": "person-name"},
        "display_name": "Correct Name",
        "sources": [],
        "active_claim_ids": [c["claim_id"] for e in entities for c in e["claims"]],
    }
    draft = {
        "schema_version": 2,
        "context_id": context["context_id"],
        "target": {"original_jd": "Original JD\n需求", "requirements": []},
        "resume": {
            "name": "Correct Name",
            "contact": "a@example.test",
            "skills": [
                {"category": "Development", "items": ["Python", "Service development"]}
            ],
            "experience": [
                {
                    "company": "Same Corp",
                    "title": "Lead",
                    "dates": "2023–2025",
                    "bullets": ["Improved response time"],
                }
            ],
            "education": [{"school": "University", "degree": "BSc", "dates": "2019"}],
            "projects": [{"name": "Platform", "bullets": ["Reduced latency"]}],
        },
        "evidence_links": {
            "name": {"claim_ids": ["person-name"]},
            "contact": {"claim_ids": ["person-contact"]},
            "skills[0].items[0]": {"claim_ids": ["skill-tool"]},
            "skills[0].items[1]": {"claim_ids": ["job1-work", "job2-work"]},
            "experience[0]": {"entity_id": "job2"},
            "experience[0].bullets[0]": {"claim_ids": ["proj-work"]},
            "education[0]": {"entity_id": "edu"},
            "projects[0]": {"entity_id": "proj"},
            "projects[0].bullets[0]": {"claim_ids": ["proj-work"]},
        },
        "omissions": [],
    }
    return draft, context


class DraftCompilerTests(unittest.TestCase):
    def test_project_heading_is_grouped_presentation_and_changes_fingerprints(self) -> None:
        draft, context = fixture()
        original = compile_draft(draft, context)
        draft["resume"]["project_heading"] = "Open Source Projects"
        result = compile_draft(draft, context)
        heading = next(e for e in result["manifest"]["entries"] if e["projection_path"] == "project_heading")
        self.assertEqual(heading["binding_mode"], "presentation")
        self.assertIn("projects[0].bullets[0]", heading["grouped_item_paths"])
        self.assertNotEqual(original["resume_fingerprint"], result["resume_fingerprint"])
        self.assertFalse(any(c["projection_path"] == "project_heading" for c in result["text_changes"]))
        draft["evidence_links"]["project_heading"] = {"claim_ids": ["proj-work"]}
        with self.assertRaisesRegex(ValueError, "unknown display paths"):
            compile_draft(draft, context)

    def test_project_heading_rejects_unsupported_or_empty_sections(self) -> None:
        for value in ("Summary", "Major Contributor", [], None):
            draft, context = fixture()
            draft["resume"]["project_heading"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "project_heading"):
                compile_draft(draft, context)
        draft, context = fixture()
        draft["resume"]["project_heading"] = "Open Source Projects"
        draft["resume"]["projects"] = []
        with self.assertRaisesRegex(ValueError, "non-empty projects"):
            compile_draft(draft, context)

    def test_removed_summary_field_and_dangling_binding_are_rejected(self) -> None:
        for value in ("Old profile", "", None):
            draft, context = fixture()
            draft["resume"]["summary"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "summary"):
                compile_draft(draft, context)
        draft, context = fixture()
        draft["evidence_links"]["summary"] = {"claim_ids": ["job1-work"]}
        with self.assertRaisesRegex(ValueError, "unknown display paths.*summary"):
            compile_draft(draft, context)

    def test_facts_previously_used_in_summary_remain_available_for_review(self) -> None:
        draft, context = fixture()
        draft["resume"]["skills"][0]["items"].pop()
        draft["evidence_links"].pop("skills[0].items[1]")
        before = copy.deepcopy(context)
        result = compile_draft(draft, context)
        self.assertEqual(context, before)
        self.assertNotIn("summary", result["resume"])
        self.assertIn("job1-work", result["manifest"]["unused_claim_ids"])
        self.assertIn("job2-work", result["manifest"]["unused_claim_ids"])

    def test_malformed_requirement_priority_has_a_descriptive_validation_error(self) -> None:
        from scripts.audit_factual_integrity import audit_draft

        for priority in ([], {}):
            draft, context = fixture()
            draft["target"]["requirements"] = [
                {"id": "r1", "text": "Build services", "priority": priority}
            ]
            with self.subTest(priority=priority), self.assertRaisesRegex(ValueError, "priority"):
                compile_draft(draft, context)
            self.assertEqual(audit_draft(draft, context)["verdict"], "FAIL")

    def test_original_jd_must_not_be_empty_or_replaced_by_missing_data(self) -> None:
        for text in ("", "  \n", None):
            draft, context = fixture()
            draft["target"]["original_jd"] = text
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "original_jd"):
                compile_draft(draft, context)

    def test_compiler_generates_text_comparisons_without_model_change_annotations(self) -> None:
        draft, context = fixture()
        result = compile_draft(draft, context)
        comparison = next(
            row for row in result["text_changes"]
            if row["projection_path"] == "experience[0].bullets[0]"
        )
        self.assertEqual(comparison["rendered_text"], draft["resume"]["experience"][0]["bullets"][0])
        self.assertTrue(comparison["comparisons"])
        self.assertTrue(
            all("source_claim_id" in item and "diff" in item for item in comparison["comparisons"])
        )
        self.assertNotIn("text_changes", draft)

    def test_null_target_metadata_is_normalized_without_changing_input(self) -> None:
        draft, context = fixture()
        draft["target"].update(company=None, role=None, job_url=None)
        result = compile_draft(draft, context)
        self.assertEqual(
            [result["target"][key] for key in ("company", "role", "job_url")], ["", "", ""]
        )
        self.assertIsNone(draft["target"]["company"])

    def test_compile_pure_full_context_without_snapshot(self) -> None:
        draft, context = fixture()
        before = copy.deepcopy((draft, context))
        result = compile_draft(draft, context)
        self.assertEqual((draft, context), before)
        self.assertEqual(result["resume"], draft["resume"])
        self.assertEqual(result["audit_scope"], "traceability_only")
        self.assertTrue(result["semantic_review_required"])
        entries = {e["projection_path"]: e for e in result["manifest"]["entries"]}
        self.assertEqual(entries["skills[0].items[1]"]["entity_ids"], ["job1", "job2"])
        self.assertEqual(entries["experience[0].bullets[0]"]["relationship_ids"], ["owns"])
        self.assertEqual(entries["education[0].school"]["source_claim_ids"], ["edu-school"])
        self.assertEqual(entries["skills[0].category"]["binding_mode"], "presentation")
        result["resume"]["name"] = "Mutated output"
        self.assertEqual(draft["resume"]["name"], "Correct Name")

    def test_name_correction_and_wrong_field_identity_rejected(self) -> None:
        draft, context = fixture()
        draft["resume"]["name"] = "Old Name"
        with self.assertRaisesRegex(ValueError, "display_name"):
            compile_draft(draft, context)
        draft["resume"]["name"] = "Correct Name"
        draft["evidence_links"]["experience[0].company"] = {"claim_ids": ["job2-work"]}
        with self.assertRaisesRegex(ValueError, "field"):
            compile_draft(draft, context)

    def test_same_employer_different_employment_not_project_owner(self) -> None:
        draft, context = fixture()
        draft["evidence_links"]["experience[0]"]["entity_id"] = "job1"
        draft["resume"]["experience"][0].update(title="Engineer", dates="2020–2022")
        with self.assertRaisesRegex(ValueError, "relationship"):
            compile_draft(draft, context)

    def test_project_own_claims_and_relationship_state(self) -> None:
        draft, context = fixture()
        draft["evidence_links"]["projects[0].bullets[0]"] = {"claim_ids": ["job2-work"]}
        with self.assertRaisesRegex(ValueError, "entity"):
            compile_draft(draft, context)
        draft, context = fixture()
        context["ledger"]["relationships"][0]["state"] = "revoked"
        with self.assertRaisesRegex(ValueError, "relationship"):
            compile_draft(draft, context)

    def test_stale_unknown_version_unbound_and_unusable_claims(self) -> None:
        for mutation, message in [
            (lambda d, c: d.update(context_id="sha256:old"), "stale"),
            (lambda d, c: d.update(schema_version=1), "schema_version"),
            (lambda d, c: c.update(schema_version=1), "schema_version"),
            (lambda d, c: d["evidence_links"].pop("skills[0].items[1]"), "unbound"),
            (
                lambda d, c: d["evidence_links"]["skills[0].items[1]"].update(claim_ids=["unknown"]),
                "unknown",
            ),
            (
                lambda d, c: c["ledger"]["entities"][1]["claims"][-1].update(status="revoked"),
                "inactive",
            ),
            (
                lambda d, c: c["ledger"]["entities"][1]["claims"][-1].update(polarity="negative"),
                "negative",
            ),
            (lambda d, c: c["active_claim_ids"].remove("job1-work"), "unresolved"),
        ]:
            with self.subTest(message=message):
                draft, context = fixture()
                mutation(draft, context)
                with self.assertRaisesRegex(ValueError, message):
                    compile_draft(draft, context)

    def test_modified_structural_requires_explicit_relevant_claim(self) -> None:
        draft, context = fixture()
        draft["resume"]["education"][0]["degree"] = "Bachelor of Science"
        with self.assertRaisesRegex(ValueError, "unbound"):
            compile_draft(draft, context)
        draft["evidence_links"]["education[0].degree"] = {"claim_ids": ["edu-degree"]}
        compile_draft(draft, context)

    def test_unlimited_skills_aggregate_and_omissions(self) -> None:
        draft, context = fixture()
        for i in range(1, 9):
            draft["resume"]["skills"].append({"category": f"Group {i}", "items": ["Platform work"]})
            draft["evidence_links"][f"skills[{i}].items[0]"] = {
                "claim_ids": ["job1-work", "job2-work"]
            }
        draft["omissions"] = [
            {"claim_ids": ["job1-title"], "reason": "Earlier title is not relevant to this role"}
        ]
        result = compile_draft(draft, context)
        self.assertIn("job1-title", result["manifest"]["unused_claim_ids"])
        for omission in [
            {"claim_ids": ["job2-work"], "reason": "Already used"},
            {"claim_ids": ["job1-title"], "reason": " "},
            {"claim_ids": ["unknown"], "reason": "Not needed"},
        ]:
            draft["omissions"] = [omission]
            with self.assertRaises(ValueError):
                compile_draft(draft, context)

    def test_cli_external_init_compile_and_audit(self) -> None:
        draft, context = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jd = root / "jd.txt"
            jd.write_text("Original JD\n需求", encoding="utf-8")
            output = root / "draft.json"
            with patch("scripts.draft_compiler.load_candidate_context", return_value=context):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "draft_compiler",
                        "init",
                        "--workspace",
                        str(root),
                        "--jd",
                        str(jd),
                        "--output",
                        str(output),
                    ],
                ):
                    self.assertEqual(main(), 0)
                initialized = json.loads(output.read_text(encoding="utf-8"))
                self.assertNotIn("summary", initialized["resume"])
                self.assertEqual(
                    initialized["target"]["original_jd"], jd.read_text(encoding="utf-8")
                )
                output.write_text(json.dumps(draft), encoding="utf-8")
                with patch.object(
                    sys,
                    "argv",
                    [
                        "draft_compiler",
                        "compile",
                        "--workspace",
                        str(root),
                        "--draft",
                        str(output),
                        "--output-dir",
                        str(root / "out"),
                    ],
                ):
                    self.assertEqual(main(), 0)
                self.assertTrue((root / "out" / "compiled-draft.json").is_file())
            from scripts.audit_factual_integrity import audit_draft

            self.assertEqual(audit_draft(draft, context)["verdict"], "PASS")
            draft["context_id"] = "sha256:old"
            self.assertEqual(audit_draft(draft, context)["verdict"], "FAIL")
        command = [sys.executable, "scripts/audit_factual_integrity.py", "--help"]
        help_result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--draft", help_result.stdout)
        self.assertNotIn("--manifest", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
