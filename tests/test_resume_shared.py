from __future__ import annotations

import unittest
from typing import Any

from scripts.resume_shared import (
    iter_resume_text_fields,
    normalize_skill_items,
    term_matches,
    validate_resume_content,
)


def sample_resume() -> dict[str, Any]:
    return {
        "name": "Alex Chen",
        "contact": "alex@example.com | +1 206-555-0100",
        "skills": [{"category": "Languages", "items": ["Python", "Go", "C++"]}],
        "experience": [
            {
                "company": "Example Corp",
                "title": "Software Engineer",
                "dates": "2020 - Present",
                "location": "Seattle",
                "bullets": ["Built distributed APIs using Python."],
            }
        ],
        "education": [
            {
                "school": "Example University",
                "degree": "B.S. Computer Science",
                "dates": "2016 - 2020",
            }
        ],
    }


class ResumeSharedTests(unittest.TestCase):
    def test_required_facts_reject_missing_null_and_blank_values(self) -> None:
        fields = [
            (None, field) for field in ("name", "contact")
        ] + [
            ("experience", field) for field in ("company", "title", "dates", "location")
        ] + [
            ("education", field) for field in ("school", "degree", "dates")
        ]
        for section, field in fields:
            for value in (None, "", " \t\n", 123):
                resume = sample_resume()
                entry = resume if section is None else resume[section][0]
                entry[field] = value
                with self.subTest(section=section, field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field):
                        validate_resume_content(resume, require_non_empty=True)
            resume = sample_resume()
            entry = resume if section is None else resume[section][0]
            entry.pop(field)
            with self.subTest(section=section, field=field, missing=True):
                with self.assertRaisesRegex(ValueError, field):
                    validate_resume_content(resume, require_non_empty=True)

    def test_education_location_remains_optional(self) -> None:
        validate_resume_content(sample_resume(), require_non_empty=True)

    def test_resume_without_summary_passes_strict_validation(self) -> None:
        resume = sample_resume()
        validate_resume_content(resume, require_non_empty=True)
        self.assertNotIn("summary", {path for path, *_ in iter_resume_text_fields(resume)})

    def test_removed_summary_field_is_rejected_even_when_empty(self) -> None:
        for value in ("Old profile", "", "  ", None, [], {}):
            for strict in (False, True):
                resume = sample_resume()
                resume["summary"] = value
                with self.subTest(value=value, strict=strict), self.assertRaisesRegex(
                    ValueError, "summary.*no longer.*supported"
                ):
                    validate_resume_content(resume, require_non_empty=strict)

    def test_short_keywords_require_boundaries(self) -> None:
        self.assertFalse(term_matches("Maintained negotiation services", "AI"))
        self.assertFalse(term_matches("Negotiated vendor contracts", "Go"))
        self.assertTrue(term_matches("Built services in Go", "Go"))
        self.assertTrue(term_matches("Developed with C++ and C#", "C++"))

    def test_validator_rejects_non_string_fields(self) -> None:
        payload = {
            "name": 123,
            "contact": "a@example.com",
            "skills": [{"category": "Languages", "items": ["Python"]}],
            "experience": [
                {
                    "company": "Example",
                    "title": "Engineer",
                    "dates": "2020 - Present",
                    "bullets": ["Built services."],
                }
            ],
            "education": [{"school": "Example", "degree": "B.S.", "dates": "2020"}],
        }
        with self.assertRaisesRegex(ValueError, "name"):
            validate_resume_content(payload)

    def test_validator_skills_rejects_empty_array(self) -> None:
        resume = sample_resume()
        resume["skills"] = [{"category": "Languages", "items": []}]
        with self.assertRaisesRegex(ValueError, "empty array"):
            validate_resume_content(resume)

    def test_validator_skills_rejects_invalid_elements(self) -> None:
        resume = sample_resume()
        resume["skills"] = [{"category": "Languages", "items": ["Python", ""]}]
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            validate_resume_content(resume)

        resume["skills"] = [{"category": "Languages", "items": ["Python", 123]}]
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            validate_resume_content(resume)

    def test_validator_skills_requires_array(self) -> None:
        resume = sample_resume()
        resume["skills"] = [{"category": "Languages", "items": 123}]
        with self.assertRaisesRegex(ValueError, "array of strings"):
            validate_resume_content(resume)

    def test_normalize_skill_items_accepts_array_and_rejects_comma_string(self) -> None:
        self.assertEqual(
            normalize_skill_items(["Azure OpenAI", "MCP", "RAG"]),
            ["Azure OpenAI", "MCP", "RAG"],
        )
        with self.assertRaisesRegex(ValueError, "array of strings"):
            normalize_skill_items("Azure OpenAI, MCP, RAG")
        resume = sample_resume()
        resume["skills"][0]["items"] = "Python, Go"
        with self.assertRaisesRegex(ValueError, "array of strings"):
            validate_resume_content(resume)

    def test_iter_resume_text_fields_emits_item_level_skill_paths(self) -> None:
        resume = sample_resume()
        resume["skills"] = [
            {
                "category": "AI Platforms & Tooling",
                "items": ["Azure OpenAI", "MCP", "RAG"],
            }
        ]
        validate_resume_content(resume, require_non_empty=True)

        fields = {path: text for path, text, _, _ in iter_resume_text_fields(resume)}

        self.assertEqual(fields["skills[0].category"], "AI Platforms & Tooling")
        self.assertEqual(fields["skills[0].items[0]"], "Azure OpenAI")
        self.assertEqual(fields["skills[0].items[1]"], "MCP")
        self.assertEqual(fields["skills[0].items[2]"], "RAG")
        self.assertNotIn("skills[0].items", fields)

if __name__ == "__main__":
    unittest.main()
