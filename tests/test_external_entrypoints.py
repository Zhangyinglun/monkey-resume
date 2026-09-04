from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ExternalEntrypointTests(unittest.TestCase):
    def write_valid_resume_json(self, path: Path) -> None:
        path.write_text(
            '{"name":"Yinglun Zhang","contact":"Seattle, WA","summary":"Engineer",'
            '"skills":[{"category":"Languages","items":["Python"]}],'
            '"experience":[{"company":"Example","title":"Engineer","dates":"2024",'
            '"bullets":["Built a service."]}],'
            '"education":[{"school":"Example University","degree":"BS","dates":"2020"}],'
            '"projects":[],"certifications":[],"awards":[]}',
            encoding="utf-8",
        )

    def run_with_temporary_home(
        self,
        script: str,
        *arguments: str,
        cwd: Path,
        home: Path,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["HOME"] = str(home)
        repo_root = Path(__file__).resolve().parent.parent
        return subprocess.run(
            [sys.executable, str(repo_root / "scripts" / script), *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_help_commands_work_outside_repository(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        scripts = (
            "resume_cache_manager.py",
            "projection_plan_manager.py",
            "check_content_quality.py",
            "generate_quality_report.py",
            "extract_resume_text.py",
            "generate_final_resume.py",
            "check_pdf_quality.py",
            "check_pdf_geometry.py",
            "evidence_ledger_manager.py",
            "audit_factual_integrity.py",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for script in scripts:
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, str(repo_root / "scripts" / script), "--help"],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_cache_manager_rejects_skill_directory_as_workspace(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "resume_cache_manager.py"),
                "reset",
                "--workspace",
                str(repo_root),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the Skill package", result.stderr)

    def test_resume_cache_defaults_to_documents_monkey_resume_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "resume.txt"
            source.write_text(
                "Yinglun Zhang\nSeattle, WA | yinglun@example.com\n\n"
                "SUMMARY\nSoftware engineer\n",
                encoding="utf-8",
            )

            result = self.run_with_temporary_home(
                "resume_cache_manager.py",
                "init",
                "--input",
                str(source),
                cwd=root,
                home=root,
            )

            expected_cache = root / "Documents" / "MonkeyResume" / "cache" / "resume-working.json"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(expected_cache.is_file())

    def test_evidence_ledger_defaults_to_documents_monkey_resume_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_json = root / "source.json"
            self.write_valid_resume_json(source_json)

            result = self.run_with_temporary_home(
                "evidence_ledger_manager.py",
                "init",
                "--source-json",
                str(source_json),
                cwd=root,
                home=root,
            )

            expected_ledger = root / "Documents" / "MonkeyResume" / "cache" / "candidate-evidence.json"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(expected_ledger.is_file())

    def test_projection_validation_defaults_to_documents_monkey_resume_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_plan = root / "Documents" / "MonkeyResume" / "cache" / "projection-plan.json"

            result = self.run_with_temporary_home(
                "projection_plan_manager.py",
                "validate",
                cwd=root,
                home=root,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                f"Projection plan file not found: {expected_plan.resolve()}",
                result.stderr,
            )

    def test_explicit_workspace_overrides_documents_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            custom_workspace = root / "custom-candidate"
            source = root / "resume.txt"
            source.write_text(
                "Yinglun Zhang\nSeattle, WA | yinglun@example.com\n\n"
                "SUMMARY\nSoftware engineer\n",
                encoding="utf-8",
            )

            result = self.run_with_temporary_home(
                "resume_cache_manager.py",
                "init",
                "--workspace",
                str(custom_workspace),
                "--input",
                str(source),
                cwd=root,
                home=root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((custom_workspace / "cache" / "resume-working.json").is_file())

            source_json = root / "source.json"
            self.write_valid_resume_json(source_json)
            ledger_result = self.run_with_temporary_home(
                "evidence_ledger_manager.py",
                "init",
                "--workspace",
                str(custom_workspace),
                "--source-json",
                str(source_json),
                cwd=root,
                home=root,
            )
            projection_result = self.run_with_temporary_home(
                "projection_plan_manager.py",
                "validate",
                "--workspace",
                str(custom_workspace),
                cwd=root,
                home=root,
            )

            self.assertEqual(ledger_result.returncode, 0, ledger_result.stderr)
            self.assertTrue((custom_workspace / "cache" / "candidate-evidence.json").is_file())
            self.assertEqual(projection_result.returncode, 1)
            self.assertIn(
                str((custom_workspace / "cache" / "projection-plan.json").resolve()),
                projection_result.stderr,
            )
            self.assertFalse((root / "Documents" / "MonkeyResume").exists())

    def test_projection_build_defaults_to_documents_monkey_resume_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = root / "plan.json"
            language = root / "language.json"
            plan.write_text("{}", encoding="utf-8")
            language.write_text("{}", encoding="utf-8")
            expected_jd = root / "Documents" / "MonkeyResume" / "cache" / "jd-analysis.json"

            result = self.run_with_temporary_home(
                "projection_plan_manager.py",
                "build",
                "--plan",
                str(plan),
                "--language",
                str(language),
                cwd=root,
                home=root,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                f"Build error: JD analysis file not found at {expected_jd.resolve()}",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
