"""Reusable, wholly synthetic display data for renderer tests."""

from __future__ import annotations

from typing import Any


def sample_resume(*, invalid: bool = False) -> dict[str, Any]:
    return {
        "name": "[Company]" if invalid else "Alex Chen",
        "contact": "missing" if invalid else "Seattle | alex@example.org",
        "skills": [{"category": "Development", "items": ["Python", "Go"]}],
        "experience": [
            {
                "company": "Example Corp",
                "title": "Software Engineer",
                "location": "Seattle",
                "dates": "2020–Present",
                "bullets": [
                    "Built distributed APIs using Python, reducing latency by 20%.",
                    "Automated deployment validation, preventing invalid releases.",
                    "Designed recovery workflows across cloud services.",
                    "Implemented request tracing for production incident diagnosis.",
                ],
            }
        ],
        "education": [
            {
                "school": "Example University",
                "degree": "B.S. Computer Science",
                "dates": "2016–2020",
            }
        ],
    }
