from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.candidate_cache import (
    commit_import,
    load_candidate_context,
    prepare_import,
    validate_workspace,
)


class CandidateCacheTests(unittest.TestCase):
    def test_answer_event_retry_deduplicates_but_new_event_preserves_history(self) -> None:
        first = self.prepare("Alex", "candidate_response")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        before = load_candidate_context(self.workspace)
        retry = prepare_import(
            self.workspace,
            self.root / "input.txt",
            source_type="candidate_response",
            event_id=first["event_id"],
        )
        self.assertEqual(retry["status"], "unchanged")
        self.assertEqual(retry["source_id"], first["source_id"])
        self.assertEqual(load_candidate_context(self.workspace), before)
        new_event = prepare_import(
            self.workspace, self.root / "input.txt", source_type="candidate_response"
        )
        self.assertNotEqual(new_event["source_id"], first["source_id"])

    def test_repeated_answer_text_can_be_a_new_explicit_correction(self) -> None:
        first = self.prepare("Use Alex", "candidate_response")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        before = load_candidate_context(self.workspace)
        entity = before["ledger"]["entities"][0]
        original_id = entity["claims"][0]["claim_id"]
        second = self.prepare("Use Alex Chen", "candidate_response")
        change = self.proposal(second, "Alex Chen", candidate_id=before["candidate_id"])
        change["entities"][0]["entity_id"] = entity["entity_id"]
        change["claims"][0]["supersedes"] = [original_id]
        commit_import(self.workspace, second["source_id"], change)
        current = load_candidate_context(self.workspace)
        third = self.prepare("Use Alex", "candidate_response")
        change = self.proposal(third, "Alex", candidate_id=current["candidate_id"])
        change["entities"][0]["entity_id"] = entity["entity_id"]
        change["claims"][0].update(
            supersedes=[current["profile"]["display_name_claim_id"]],
            reactivate=True,
        )
        commit_import(self.workspace, third["source_id"], change)
        self.assertEqual(load_candidate_context(self.workspace)["display_name"], "Alex")

    def test_explicit_name_correction_can_return_to_historical_value(self) -> None:
        first = self.prepare("Alex")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        before = load_candidate_context(self.workspace)
        entity = before["ledger"]["entities"][0]
        original_id = entity["claims"][0]["claim_id"]
        second = self.prepare("Use Alex Chen", "candidate_response")
        change = self.proposal(second, "Alex Chen", candidate_id=before["candidate_id"])
        change["entities"][0]["entity_id"] = entity["entity_id"]
        change["claims"][0]["supersedes"] = [original_id]
        commit_import(self.workspace, second["source_id"], change)
        current = load_candidate_context(self.workspace)
        third = self.prepare("Actually use Alex again", "candidate_response")
        change = self.proposal(third, "Alex", candidate_id=current["candidate_id"])
        change["entities"][0]["entity_id"] = entity["entity_id"]
        change["claims"][0].update(
            supersedes=[current["profile"]["display_name_claim_id"]],
            reactivate=True,
        )
        commit_import(self.workspace, third["source_id"], change)
        after = load_candidate_context(self.workspace)
        self.assertEqual(after["display_name"], "Alex")
        self.assertEqual(after["profile"]["display_name_claim_id"], original_id)
        self.assertEqual(after["candidate_id"], before["candidate_id"])

    def test_relationship_correction_supersedes_old_owner(self) -> None:
        first = self.prepare("Project P belongs to Job A. Job B is another employment.")
        proposal = {
            "context_id": first["context_id"],
            "entities": [
                {"ref": "p", "entity_type": "project", "label": "P"},
                {"ref": "a", "entity_type": "employment", "label": "A"},
                {"ref": "b", "entity_type": "employment", "label": "B"},
            ],
            "relationships": [
                {
                    "project_ref": "p",
                    "employment_ref": "a",
                    "block_ids": ["block-1"],
                    "original_excerpt": "Project P belongs to Job A.",
                }
            ],
        }
        report = commit_import(self.workspace, first["source_id"], proposal)
        before = load_candidate_context(self.workspace)
        old = before["ledger"]["relationships"][0]["relationship_id"]
        second = self.prepare("Correction: Project P belongs to Job B.", "candidate_response")
        proposal = {
            "context_id": second["context_id"],
            "relationships": [
                {
                    "project_ref": report["entity_ids"]["p"],
                    "employment_ref": report["entity_ids"]["b"],
                    "block_ids": ["block-1"],
                    "original_excerpt": "Project P belongs to Job B.",
                    "supersedes": [old],
                }
            ],
        }
        commit_import(self.workspace, second["source_id"], proposal)
        after = load_candidate_context(self.workspace)
        active = [r for r in after["ledger"]["relationships"] if r["state"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["employment_id"], report["entity_ids"]["b"])
        self.assertNotEqual(after["context_id"], before["context_id"])

    def test_existing_state_survives_authoritative_replace_failure(self) -> None:
        import os

        first = self.prepare("Alex")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        before = load_candidate_context(self.workspace)
        state_path = self.workspace / "cache/candidate-state.json"
        before_bytes = state_path.read_bytes()
        prepared = self.prepare("Extra note")
        replace = os.replace

        def fail_state(source: object, target: object) -> None:
            if Path(target) == state_path:
                raise OSError("authoritative replacement failed")
            replace(source, target)

        with patch("scripts.candidate_cache.os.replace", side_effect=fail_state):
            with self.assertRaisesRegex(OSError, "authoritative replacement failed"):
                commit_import(
                    self.workspace,
                    prepared["source_id"],
                    {"context_id": prepared["context_id"], "preferences": {"language": "en"}},
                )
        self.assertEqual(state_path.read_bytes(), before_bytes)
        self.assertEqual(load_candidate_context(self.workspace)["context_id"], before["context_id"])

    def test_committed_source_mutation_blocks_context(self) -> None:
        prepared = self.prepare("Alex")
        commit_import(self.workspace, prepared["source_id"], self.proposal(prepared, "Alex"))
        Path(prepared["original_path"]).write_text("Other", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Source mutation"):
            load_candidate_context(self.workspace)

    def test_rejects_pending_block_mutation(self) -> None:
        prepared = self.prepare("Alex")
        path = self.workspace / "cache/imports" / f"{prepared['source_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["blocks"][0]["text"] = "Fake"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "mutation"):
            commit_import(self.workspace, prepared["source_id"], self.proposal(prepared, "Fake"))

    def test_duplicate_claim_provenance_and_omissions(self) -> None:
        first = self.prepare("Alex")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        context = load_candidate_context(self.workspace)
        entity = context["ledger"]["entities"][0]
        prepared = self.prepare("Name: Alex\nNo Terraform")
        proposal = self.proposal(prepared, "Alex")
        proposal["entities"][0]["entity_id"] = entity["entity_id"]
        proposal["claims"].append(
            {
                "ref": "negative",
                "entity_ref": "p",
                "claim_text": "No Terraform",
                "polarity": "negative",
                "block_ids": ["block-2"],
                "original_excerpt": "No Terraform",
            }
        )
        commit_import(self.workspace, prepared["source_id"], proposal)
        context = load_candidate_context(self.workspace)
        claims = context["ledger"]["entities"][0]["claims"]
        self.assertEqual(claims[0]["claim_id"], entity["claims"][0]["claim_id"])
        self.assertEqual(len(claims[0]["provenance"]), 2)
        self.assertNotIn(claims[1]["claim_id"], context["active_claim_ids"])
        prepared = self.prepare("A shorter note with no name")
        commit_import(self.workspace, prepared["source_id"], {"context_id": prepared["context_id"]})
        self.assertEqual(load_candidate_context(self.workspace)["display_name"], "Alex")

    def test_relationship_and_partial_import(self) -> None:
        prepared = self.prepare("Company A\nProject B\n10 and 20 users")
        proposal = {
            "context_id": prepared["context_id"],
            "entities": [
                {"ref": "e", "entity_type": "employment", "label": "A"},
                {"ref": "p", "entity_type": "project", "label": "B"},
            ],
            "claims": [
                {
                    "ref": "a",
                    "entity_ref": "e",
                    "claim_text": "Company A",
                    "block_ids": ["block-1"],
                    "original_excerpt": "Company A",
                },
                {
                    "ref": "b",
                    "entity_ref": "p",
                    "claim_text": "10 users",
                    "block_ids": ["block-3"],
                    "original_excerpt": "10 and 20 users",
                },
                {
                    "ref": "c",
                    "entity_ref": "p",
                    "claim_text": "20 users",
                    "block_ids": ["block-3"],
                    "original_excerpt": "10 and 20 users",
                },
            ],
            "relationships": [
                {
                    "project_ref": "e",
                    "employment_ref": "p",
                    "block_ids": ["block-2"],
                    "original_excerpt": "Project B",
                }
            ],
            "conflicts": [{"claim_refs": ["b", "c"], "reason": "uncertain metric"}],
        }
        with self.assertRaisesRegex(ValueError, "project to employment"):
            commit_import(self.workspace, prepared["source_id"], proposal)
        proposal["relationships"][0].update(project_ref="p", employment_ref="e")
        result = commit_import(self.workspace, prepared["source_id"], proposal)
        self.assertEqual(result["status"], "partial")
        context = load_candidate_context(self.workspace)
        self.assertEqual(len(context["active_claim_ids"]), 1)
        self.assertEqual(len(context["ledger"]["relationships"]), 1)

    def test_identity_and_symlink_and_unsupported_schema(self) -> None:
        prepared = self.prepare("Alex")
        commit_import(self.workspace, prepared["source_id"], self.proposal(prepared, "Alex"))
        prepared = self.prepare("Other Person")
        with self.assertRaisesRegex(ValueError, "Identity conflict"):
            commit_import(
                self.workspace, prepared["source_id"], self.proposal(prepared, "Other Person")
            )
        path = self.workspace / "cache/candidate-state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["schema_version"] = 999
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            load_candidate_context(self.workspace)
        unsafe = self.root / "unsafe"
        unsafe.mkdir()
        (unsafe / "cache").symlink_to(self.workspace / "cache", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            validate_workspace(unsafe)

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.workspace = self.root / "workspace"

    def prepare(self, text: str, source_type: str = "document") -> dict:
        path = self.root / "input.txt"
        path.write_text(text, encoding="utf-8")
        return prepare_import(self.workspace, path, source_type=source_type)

    def proposal(self, prepared: dict, text: str, **kwargs: object) -> dict:
        return {
            "context_id": prepared["context_id"],
            "entities": [{"ref": "p", "entity_type": "profile", "label": "Person"}],
            "claims": [
                {
                    "ref": "n",
                    "entity_ref": "p",
                    "field": "name",
                    "claim_text": text,
                    "block_ids": [b["block_id"] for b in prepared["blocks"] if text in b["text"]]
                    or ["block-1"],
                    "original_excerpt": text,
                }
            ],
            "display_name_ref": "n",
            **kwargs,
        }

    def test_prepare_commit_duplicate_and_original(self) -> None:
        prepared = self.prepare("工作笔记\n姓名：陈明")
        self.assertIsNone(load_candidate_context(self.workspace)["candidate_id"])
        result = commit_import(
            self.workspace, prepared["source_id"], self.proposal(prepared, "陈明")
        )
        self.assertEqual(result["status"], "committed")
        context = load_candidate_context(self.workspace)
        self.assertEqual(context["display_name"], "陈明")
        duplicate = self.prepare("工作笔记\n姓名：陈明")
        self.assertEqual(duplicate["status"], "unchanged")
        self.assertEqual(context["context_id"], duplicate["context_id"])

    def test_invalid_quote_and_atomic_failure(self) -> None:
        prepared = self.prepare("Alex")
        with self.assertRaisesRegex(ValueError, "excerpt"):
            commit_import(self.workspace, prepared["source_id"], self.proposal(prepared, "Fake"))
        with patch("scripts.candidate_cache.os.replace", side_effect=OSError("injected")):
            with self.assertRaisesRegex(OSError, "injected"):
                commit_import(
                    self.workspace, prepared["source_id"], self.proposal(prepared, "Alex")
                )
        self.assertIsNone(load_candidate_context(self.workspace)["candidate_id"])
        commit_import(self.workspace, prepared["source_id"], self.proposal(prepared, "Alex"))

    def test_stale_proposal_and_legacy(self) -> None:
        first = self.prepare("Alex")
        second = self.prepare("Other")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        with self.assertRaisesRegex(ValueError, "stale"):
            commit_import(self.workspace, second["source_id"], self.proposal(second, "Other"))
        legacy = self.root / "legacy" / "cache"
        legacy.mkdir(parents=True)
        (legacy / "candidate-evidence.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "migration"):
            load_candidate_context(legacy.parent)

    def test_named_correction_preserves_history(self) -> None:
        first = self.prepare("Alex")
        commit_import(self.workspace, first["source_id"], self.proposal(first, "Alex"))
        before = load_candidate_context(self.workspace)
        entity = before["ledger"]["entities"][0]
        old_id = entity["claims"][0]["claim_id"]
        prepared = self.prepare("My corrected name is Alice", "candidate_response")
        proposal = self.proposal(prepared, "Alice", candidate_id=before["candidate_id"])
        proposal["entities"][0]["entity_id"] = entity["entity_id"]
        proposal["claims"][0]["supersedes"] = [old_id]
        commit_import(self.workspace, prepared["source_id"], proposal)
        after = load_candidate_context(self.workspace)
        self.assertEqual(after["display_name"], "Alice")
        self.assertEqual(after["candidate_id"], before["candidate_id"])
        self.assertNotIn(old_id, after["active_claim_ids"])
        self.assertEqual(len(after["ledger"]["entities"][0]["claims"]), 2)

    def test_conflict_suspends_both_and_resolution(self) -> None:
        prepared = self.prepare("Built 10 services")
        proposal = self.proposal(prepared, "10 services")
        proposal.pop("display_name_ref")
        proposal["entities"][0]["entity_type"] = "employment"
        proposal["claims"][0]["field"] = "metric"
        commit_import(self.workspace, prepared["source_id"], proposal)
        before = load_candidate_context(self.workspace)
        entity = before["ledger"]["entities"][0]
        old = entity["claims"][0]["claim_id"]
        prepared = self.prepare("Built 20 services")
        proposal = self.proposal(prepared, "20 services")
        proposal.pop("display_name_ref")
        proposal["entities"][0].update(entity_type="employment", entity_id=entity["entity_id"])
        proposal["claims"][0]["field"] = "metric"
        proposal["conflicts"] = [{"claim_refs": [old, "n"], "reason": "different count"}]
        result = commit_import(self.workspace, prepared["source_id"], proposal)
        self.assertEqual(result["status"], "needs_clarification")
        after = load_candidate_context(self.workspace)
        self.assertEqual(after["active_claim_ids"], [])
        self.assertNotEqual(after["context_id"], before["context_id"])
        prepared = self.prepare("I confirm 20 services", "candidate_response")
        conflict = after["ledger"]["conflicts"][0]
        new = entity["claims"][0]["claim_id"]
        new = next(
            c["claim_id"]
            for c in after["ledger"]["entities"][0]["claims"]
            if c["claim_text"] == "20 services"
        )
        proposal = {
            "context_id": prepared["context_id"],
            "resolve_conflicts": [
                {
                    "conflict_id": conflict["conflict_id"],
                    "selected_claim_ids": [new],
                    "block_ids": [prepared["blocks"][0]["block_id"]],
                    "original_excerpt": "I confirm 20 services",
                }
            ],
        }
        commit_import(self.workspace, prepared["source_id"], proposal)
        self.assertEqual(load_candidate_context(self.workspace)["active_claim_ids"], [new])
        prepared = self.prepare("An archived note: Built 10 services")
        proposal = {
            "context_id": prepared["context_id"],
            "entities": [
                {
                    "ref": "e",
                    "entity_id": entity["entity_id"],
                    "entity_type": "employment",
                    "label": "Work",
                }
            ],
            "claims": [
                {
                    "ref": "old",
                    "entity_ref": "e",
                    "claim_text": "10 services",
                    "field": "metric",
                    "block_ids": ["block-1"],
                    "original_excerpt": "10 services",
                }
            ],
            "conflicts": [{"claim_refs": ["old", new], "reason": "old count repeated"}],
        }
        commit_import(self.workspace, prepared["source_id"], proposal)
        repeated = load_candidate_context(self.workspace)
        self.assertEqual(repeated["active_claim_ids"], [new])
        self.assertEqual(len(repeated["ledger"]["conflicts"]), 1)
