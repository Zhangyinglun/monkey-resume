from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

import yaml


class SkillMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_skill_frontmatter_and_references(self) -> None:
        skill_path = self.repo_root / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
        self.assertGreaterEqual(len(parts), 3)
        frontmatter = yaml.safe_load(parts[1])
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "monkey-resume")
        self.assertLessEqual(len(content.splitlines()), 500)

        for relative_path in re.findall(r"`((?:references|scripts)/[^`]+)`", content):
            path_without_placeholder = relative_path.split(" ", 1)[0]
            self.assertTrue(
                (self.repo_root / path_without_placeholder).exists(),
                path_without_placeholder,
            )

    def test_package_has_no_client_specific_adapters(self) -> None:
        client_specific_paths = (
            "CLAUDE.md",
            ".claude",
            ".opencode",
            "agents/openai.yaml",
            "install/agent-install.yaml",
            "scripts/check_agent_platform_support.py",
        )
        present = [path for path in client_specific_paths if (self.repo_root / path).exists()]
        self.assertEqual(present, [])

    def test_restricted_vendor_content_is_not_bundled(self) -> None:
        vendor_root = self.repo_root / "vendor"
        bundled_files = (
            [path for path in vendor_root.rglob("*") if path.is_file()]
            if vendor_root.exists()
            else []
        )
        # Only reviewed Apache-2.0 PUBLIC OpenAI source is allowed; private
        # runtime skill content remains forbidden.
        allowed = {
            "openai_doc/render_docx.py",
            "openai_doc/LICENSE.txt",
            "openai_doc/PROVENANCE.md",
        }
        self.assertEqual(
            {
                path.relative_to(vendor_root).as_posix()
                for path in bundled_files
                if "__pycache__" not in path.parts
            },
            allowed,
        )
        provenance = (vendor_root / "openai_doc/PROVENANCE.md").read_text(encoding="utf-8")
        local_hash = re.search(r"Local SHA-256 render_docx.py: ([a-f0-9]{64})", provenance)
        self.assertIsNotNone(local_hash, "Local vendor changes must record their SHA-256.")
        self.assertEqual(
            hashlib.sha256(
                (vendor_root / "openai_doc/render_docx.py").read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest(),
            local_hash.group(1),
        )
        self.assertIn(
            "Upstream SHA-256 render_docx.py: 52b3c3158913ebcad2ada7b8193970b70453239e255054aa2d60c1683af08751",
            provenance,
        )

    def test_skill_contains_single_draft_and_independent_import_workflows(self) -> None:
        skill_path = self.repo_root / "SKILL.md"
        skill_text = skill_path.read_text(encoding="utf-8")
        for term in (
            "candidate-state.json",
            "draft_compiler.py",
            "evidence_links",
            "omissions",
            "prepare",
            "publish",
        ):
            self.assertIn(term, skill_text)
        self.assertNotIn("projection-plan.json", skill_text)
        self.assertNotIn("projection-language.json", skill_text)


if __name__ == "__main__":
    unittest.main()
