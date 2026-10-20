from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExternalEntrypointTests(unittest.TestCase):
    def invoke(self, script: str, directory: Path, *arguments: str) -> subprocess.CompletedProcess:
        environment = {**os.environ, "HOME": str(directory), "USERPROFILE": str(directory)}
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *arguments],
            cwd=directory,
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_public_help_works_outside_repository(self) -> None:
        scripts = (
            "evidence_ledger_manager.py",
            "draft_compiler.py",
            "audit_factual_integrity.py",
            "generate_final_resume.py",
            "generate_quality_report.py",
            "extract_resume_text.py",
            "check_content_quality.py",
            "check_pdf_quality.py",
            "check_pdf_geometry.py",
            "resume_history_manager.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            for script in scripts:
                with self.subTest(script=script):
                    result = self.invoke(script, Path(directory), "--help")
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_cache_prepare_defaults_to_external_documents_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "notes.md"
            source.write_text("工程师资料\n姓名：Alex Chen\n开发消息队列。", encoding="utf-8")
            result = self.invoke(
                "evidence_ledger_manager.py", root, "prepare", "--input", str(source)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            prepared = json.loads(result.stdout)
            self.assertTrue(prepared["source_id"])
            self.assertTrue(prepared["blocks"])
            workspace = root / "Documents" / "MonkeyResume"
            self.assertTrue(workspace.is_dir())
            self.assertFalse((workspace / "cache" / "candidate-state.json").exists())

    def test_cache_prepare_explicit_workspace_overrides_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "notes.txt"
            source.write_text("Alex Chen\nWorked on telemetry.", encoding="utf-8")
            workspace = root / "different-candidate"
            result = self.invoke(
                "evidence_ledger_manager.py",
                root,
                "prepare",
                "--input",
                str(source),
                "--workspace",
                str(workspace),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(workspace.exists())
            self.assertFalse((root / "Documents" / "MonkeyResume").exists())

    def test_repository_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.invoke(
                "evidence_ledger_manager.py", Path(directory), "context", "--workspace", str(ROOT)
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside", result.stderr.lower())

    def test_old_regex_cache_and_planning_entrypoints_are_removed(self) -> None:
        for script in ("resume_cache_manager.py", "projection_plan_manager.py"):
            self.assertFalse((ROOT / "scripts" / script).exists(), script)


if __name__ == "__main__":
    unittest.main()
