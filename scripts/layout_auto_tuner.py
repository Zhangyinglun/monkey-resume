#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic layout tuning for one-page resume generation."""

from __future__ import annotations

import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from scripts.check_pdf_quality import check_pdf_file
from templates.docx_resume_template import generate_resume
from templates.layout_settings import LayoutSettings
from templates.style_profiles import DEFAULT_STYLE, bounded_layouts, get_style

# Checks that layout tuning can potentially fix (margins, page overflow).
LAYOUT_FIXABLE_CHECKS = {
    "page_count", "bottom_margin", "top_margin", "side_margins", "text_geometry"
}


@dataclass(frozen=True)
class AutoFitTrial:
    """Single trial result for a layout candidate."""
    layout: LayoutSettings
    report: dict[str, Any]


@dataclass(frozen=True)
class AutoFitResult:
    """Best result selected from auto-fit trials."""
    best_layout: LayoutSettings
    best_report: dict[str, Any]
    trials_run: int


def _scales(layout: LayoutSettings) -> tuple[float, float, float, float]:
    """Extract the four effective scale values."""
    return (
        layout.effective_font_size_scale,
        layout.effective_line_height_scale,
        layout.effective_section_spacing_scale,
        layout.effective_item_spacing_scale,
    )


def _failed_checks(report: dict[str, Any]) -> set[str]:
    return {
        c["name"] for c in report.get("checks", [])
        if isinstance(c.get("name"), str) and c.get("passed") is False
    }


def _readability_score(layout: LayoutSettings) -> float:
    fs, lh, ss, it = _scales(layout)
    return fs * 0.45 + lh * 0.30 + ss * 0.15 + it * 0.10


def _compression_distance(layout: LayoutSettings) -> float:
    return sum(abs(1.0 - v) for v in _scales(layout))


def score_trial(trial: AutoFitTrial) -> tuple[int, int, int, float, float]:
    """Score trial; higher tuple is better.

    Priority: pass > fewer layout failures > fewer total > closer to default > higher readability.
    """
    failed = _failed_checks(trial.report)
    return (
        1 if trial.report.get("verdict") == "PASS" else 0,
        -len(failed & LAYOUT_FIXABLE_CHECKS),
        -len(failed),
        -_compression_distance(trial.layout),
        _readability_score(trial.layout),
    )


def _run_trial(content: dict[str, Any], output_file: str, layout: LayoutSettings, trial_dir: Path, *, style: str = DEFAULT_STYLE) -> AutoFitTrial:
    """Generate PDF and run quality check for a single layout candidate."""
    trial_dir.mkdir(parents=True, exist_ok=True)
    with redirect_stdout(StringIO()):
        generated = generate_resume(output_file, content, base_dir=str(trial_dir), layout=layout, style=style)
    return AutoFitTrial(layout=layout, report=check_pdf_file(Path(generated), minimum_font_pt=get_style(style).minimum_font_pt))


def auto_fit_layout(
    content: dict[str, Any],
    *, output_file: str, max_trials: int,
    hint_layout: LayoutSettings | None = None,
    style: str = DEFAULT_STYLE,
) -> AutoFitResult:
    """Try multiple layout presets and return the best trial."""
    if max_trials <= 0:
        raise ValueError("max_trials must be positive.")
    profile = get_style(style)
    with tempfile.TemporaryDirectory(prefix="resume-autofit-") as temp_dir:
        base_temp = Path(temp_dir)

        # Phase 1: Diagnostic pass
        first_layout = profile.resolve_layout(hint_layout)
        first_trial = _run_trial(content, output_file, first_layout, base_temp / "trial-1", style=style)

        if first_trial.report.get("verdict") == "PASS":
            return AutoFitResult(first_trial.layout, first_trial.report, 1)
        trials = [first_trial]
        for candidate in bounded_layouts(profile, first_layout)[:max_trials - 1]:
            trial = _run_trial(content, output_file, candidate, base_temp / f"trial-{len(trials) + 1}", style=style)
            trials.append(trial)
            if trial.report.get("verdict") == "PASS":
                return AutoFitResult(trial.layout, trial.report, len(trials))
        best = max(trials, key=score_trial)
        return AutoFitResult(best.layout, best.report, len(trials))
