"""Versioned presentation defaults and bounds for the DOCX renderer."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any

from templates.design_tokens import DEFAULT_TOKENS, DesignTokens
from templates.layout_settings import DOCX_DEFAULT_SETTINGS, LayoutSettings

DEFAULT_STYLE = "professional-v3"


@dataclass(frozen=True)
class StyleProfile:
    name: str
    version: int
    tokens: DesignTokens
    layout: LayoutSettings
    font_family: str = "Carlito"
    justify_body: bool = False
    short_headings: bool = True
    minimum_font_pt: float = 10.5
    minimum_margin_mm: float = 12.7

    def heading(self, title: str) -> str:
        if not self.short_headings:
            return title
        return {"PROFESSIONAL EXPERIENCE": "Experience", "TECHNICAL SKILLS": "Skills"}.get(
            title, title.title()
        )

    def resolve_layout(self, layout: LayoutSettings | None = None) -> LayoutSettings:
        resolved = layout or self.layout
        if self.name != "legacy-v1" and resolved.compact_mode:
            resolved = replace(
                resolved,
                font_size_scale=10.5 / 11.0 if resolved.font_size_scale in (None, 1.0) else resolved.font_size_scale,
                line_height_scale=0.95 if resolved.line_height_scale in (None, 1.0) else resolved.line_height_scale,
                section_spacing_scale=0.85 if resolved.section_spacing_scale in (None, 1.0) else resolved.section_spacing_scale,
                item_spacing_scale=0.85 if resolved.item_spacing_scale in (None, 1.0) else resolved.item_spacing_scale,
            )
        self.validate(resolved)
        return resolved

    def validate(self, layout: LayoutSettings, tokens: DesignTokens | None = None) -> None:
        raw = asdict(layout)
        for name, value in raw.items():
            if name == "compact_mode" or value is None:
                continue
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid layout value: {name}={value}")
            if name.endswith("scale") and not 0.7 <= value <= 1.3:
                raise ValueError(f"Layout scale out of range: {name}={value}")
        if self.name == "legacy-v1":
            return
        sizes = self.font_sizes(layout, tokens)
        if min(sizes.values()) < self.minimum_font_pt:
            raise ValueError(f"{self.name} requires all text to be at least {self.minimum_font_pt} pt; revise content instead of shrinking further.")
        if min(layout.margin_top_mm, layout.margin_bottom_mm, layout.margin_side_inch * 25.4) < self.minimum_margin_mm:
            raise ValueError(f"{self.name} requires margins of at least {self.minimum_margin_mm} mm.")
        if min(layout.effective_section_spacing_scale, layout.effective_item_spacing_scale) < 0.75:
            raise ValueError(f"{self.name} requires section and item spacing scales of at least 0.75.")

    def font_sizes(self, layout: LayoutSettings, tokens: DesignTokens | None = None) -> dict[str, float]:
        # python-docx stores sizes in half-point units, truncating fractional halves.
        return {
            key: int(value * layout.effective_font_size_scale * 2) / 2
            for key, value in asdict(tokens or self.tokens).items()
            if key.endswith("font_size")
        }

    def snapshot(self, layout: LayoutSettings) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version, "font_family": self.font_family,
            "page_size": "A4", "page_width_mm": 210.0, "page_height_mm": 297.0,
            "justify_body": self.justify_body, "short_headings": self.short_headings,
            "minimum_font_pt": self.minimum_font_pt, "minimum_margin_mm": self.minimum_margin_mm,
            "tokens": asdict(self.tokens), "layout": asdict(layout),
            "effective_scales": {
                name: getattr(layout, f"effective_{name}_scale")
                for name in ("font_size", "line_height", "section_spacing", "item_spacing")
            },
            "actual_font_sizes_pt": self.font_sizes(layout),
        }


_PROFESSIONAL_TOKENS = replace(
    DEFAULT_TOKENS,
    accent_color=(0, 0, 0), body_ink_color=(0, 0, 0),
    header_font_size=19.0, contact_font_size=11.0, section_font_size=12.0,
    body_font_size=11.0, company_font_size=11.5, dates_font_size=11.0,
    job_detail_font_size=11.0, bullet_font_size=11.0, education_font_size=11.0,
    header_leading=22.0, section_leading=14.0, body_leading=12.65,
    company_leading=13.25, dates_leading=12.65, job_detail_leading=12.65,
    bullet_leading=12.65, education_leading=12.65,
    header_space_after=3.0, contact_space_after=2.0,
    section_space_before=9.0, section_space_after=4.0,
    company_space_after=2.0, job_detail_space_after=3.0,
    bullet_space_after=3.0, education_space_after=2.0,
    section_hr_thickness=0.4, company_space_before=6.0,
)

STYLES = {
    "legacy-v1": StyleProfile(
        "legacy-v1", 1, DEFAULT_TOKENS, DOCX_DEFAULT_SETTINGS,
        justify_body=True, short_headings=False, minimum_font_pt=8.5, minimum_margin_mm=0.0,
    ),
    "professional-v2": StyleProfile(
        "professional-v2", 2, _PROFESSIONAL_TOKENS,
        LayoutSettings(margin_top_mm=15.24, margin_bottom_mm=15.24, margin_side_inch=0.65),
    ),
    DEFAULT_STYLE: StyleProfile(
        DEFAULT_STYLE, 3, _PROFESSIONAL_TOKENS,
        LayoutSettings(margin_top_mm=15.24, margin_bottom_mm=15.24, margin_side_inch=0.65),
        font_family="Arial",
    ),
}


def get_style(name: str = DEFAULT_STYLE) -> StyleProfile:
    try:
        return STYLES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown resume style: {name}. Choose from {', '.join(STYLES)}.") from exc


def bounded_layouts(profile: StyleProfile, initial: LayoutSettings) -> list[LayoutSettings]:
    """Preserve caller margins; reduce whitespace before touching the font."""
    candidates = [
        replace(initial, section_spacing_scale=max(0.75, initial.effective_section_spacing_scale * section),
                item_spacing_scale=max(0.75, initial.effective_item_spacing_scale * item),
                line_height_scale=max(0.7, initial.effective_line_height_scale * line))
        for section, item, line in ((0.95, 0.9, 1.0), (0.9, 0.8, 1.0), (0.85, 0.75, 0.97), (0.8, 0.75, 0.95))
    ]
    candidates.append(replace(candidates[-1], font_size_scale=10.5 / 11.0, compact_mode=False))
    valid = []
    for candidate in candidates:
        try:
            profile.validate(candidate)
        except ValueError:
            continue
        if candidate != initial and candidate not in valid:
            valid.append(candidate)
    return valid
