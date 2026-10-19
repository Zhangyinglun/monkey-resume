"""Current presentation defaults and bounds for the DOCX renderer."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any

from templates.design_tokens import DEFAULT_TOKENS, DesignTokens
from templates.layout_settings import LayoutSettings

DEFAULT_STYLE = "professional-v3"


@dataclass(frozen=True)
class StyleProfile:
    name: str
    version: int
    tokens: DesignTokens
    layout: LayoutSettings
    font_family: str = "Arial"
    minimum_font_pt: float = 10.5
    minimum_margin_mm: float = 12.7

    def heading(self, title: str) -> str:
        return {"PROFESSIONAL EXPERIENCE": "Experience", "TECHNICAL SKILLS": "Skills"}.get(
            title, title.title()
        )

    def resolve_layout(self, layout: LayoutSettings | None = None) -> LayoutSettings:
        resolved = layout or self.layout
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
            "minimum_font_pt": self.minimum_font_pt, "minimum_margin_mm": self.minimum_margin_mm,
            "tokens": asdict(self.tokens), "layout": asdict(layout),
            "effective_scales": {
                name: getattr(layout, f"effective_{name}_scale")
                for name in ("font_size", "line_height", "section_spacing", "item_spacing")
            },
            "actual_font_sizes_pt": self.font_sizes(layout),
        }


STYLES = {
    DEFAULT_STYLE: StyleProfile(
        DEFAULT_STYLE, 3, DEFAULT_TOKENS,
        LayoutSettings(),
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
