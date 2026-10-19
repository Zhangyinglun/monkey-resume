#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized design tokens for current DOCX resume template."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    """Immutable design constants for the resume template.

    All font sizes, leading values, and spacing are BASE values before
    LayoutSettings scaling is applied.
    """

    # -- Colors (RGB 0-255) --
    accent_color: tuple[int, int, int] = (0, 0, 0)
    body_ink_color: tuple[int, int, int] = (0, 0, 0)

    # -- Font sizes (pt) --
    header_font_size: float = 19.0
    contact_font_size: float = 11.0
    section_font_size: float = 12.0
    body_font_size: float = 11.0
    company_font_size: float = 11.5
    dates_font_size: float = 11.0
    job_detail_font_size: float = 11.0
    bullet_font_size: float = 11.0
    education_font_size: float = 11.0

    # -- Leading (pt) --
    header_leading: float = 22.0
    section_leading: float = 14.0
    body_leading: float = 12.65
    company_leading: float = 13.25
    job_detail_leading: float = 12.65
    bullet_leading: float = 12.65
    education_leading: float = 12.65

    # -- Spacing (pt, before LayoutSettings scaling) --
    header_space_after: float = 3.0
    contact_space_after: float = 2.0
    section_space_before: float = 9.0
    section_space_after: float = 4.0
    body_space_after: float = 6.2
    company_space_before: float = 6.0
    company_space_after: float = 2.0
    job_detail_space_after: float = 3.0
    bullet_space_after: float = 3.0
    education_space_after: float = 2.0

    # -- Bullet indentation (pt) --
    bullet_left_indent: float = 15.0

    # -- Horizontal rules --
    section_hr_thickness: float = 0.4


DEFAULT_TOKENS = DesignTokens()
