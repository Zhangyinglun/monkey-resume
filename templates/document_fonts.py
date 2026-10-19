"""Resolve licensed local fonts and verify the converter's actual text fonts."""
from __future__ import annotations

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pdfplumber
from reportlab.pdfbase.ttfonts import TTFontFile


def resolve_font_files(family: str) -> tuple[Path, ...]:
    """Require actual Regular and Bold faces, rejecting Fontconfig aliases."""
    candidates: set[Path] = set()
    matcher = shutil.which("fc-match")
    if matcher:
        for variant in ("Regular", "Bold", "Italic", "Bold Italic"):
            result = subprocess.run(
                [matcher, "--format=%{file}", f"{family}:style={variant}"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.add(Path(result.stdout.strip()))
    directories = [
        Path("/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"),
        Path.home() / "Library/Fonts", Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"), Path.home() / ".local/share/fonts",
        Path.home() / ".fonts",
    ]
    if os.name == "nt":
        directories.extend([
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
        ])
    for directory in directories:
        if directory.is_dir():
            candidates.update(
                path for path in directory.rglob("*")
                if path.suffix.lower() == ".ttf" and path.name.lower().startswith(family.lower())
            )
    matched: list[Path] = []
    faces: set[str] = set()
    for path in sorted(candidates):
        if not path.is_file():
            continue
        try:
            font = TTFontFile(str(path), charInfo=False)
        except (OSError, ValueError, RuntimeError):
            continue
        if font.familyName.decode("utf-8").casefold() != family.casefold():
            continue
        matched.append(path)
        faces.add(font.styleName.decode("utf-8").casefold())
    if not any("bold" not in face and "italic" not in face for face in faces) or not any(
        "bold" in face and "italic" not in face for face in faces
    ):
        raise RuntimeError(
            f"{family} Regular and Bold fonts are required. Install the licensed font "
            "separately; font files are not bundled. Refusing font substitution."
        )
    return tuple(matched)


def conversion_environment(family: str, directory: Path) -> dict[str, str]:
    """Give one conversion process a font directory list and writable cache."""
    paths = resolve_font_files(family)
    directory.mkdir(parents=True, exist_ok=True)
    config = ET.Element("fontconfig")
    parents = sorted({path.parent for path in paths})
    for parent in parents:
        ET.SubElement(config, "dir").text = str(parent)
    ET.SubElement(config, "cachedir").text = str(directory / "cache")
    config_path = directory / "fonts.conf"
    ET.ElementTree(config).write(config_path, encoding="utf-8", xml_declaration=True)
    return {
        **os.environ,
        "FONTCONFIG_FILE": str(config_path),
        "SAL_FONTPATH": os.pathsep.join(str(parent) for parent in parents),
    }


def validate_pdf_fonts(pdf: Path, family: str) -> dict[str, object]:
    """Check rendered characters against the actual installed family's names."""
    fonts = [TTFontFile(str(path), charInfo=False) for path in resolve_font_files(family)]
    allowed = {font.name.decode("utf-8") for font in fonts}
    faces = {
        role: {
            font.name.decode("utf-8") for font in fonts
            if ("bold" in font.styleName.decode("utf-8").casefold()) == (role == "bold")
            and "italic" not in font.styleName.decode("utf-8").casefold()
        }
        for role in ("regular", "bold")
    }
    with pdfplumber.open(pdf) as document:
        actual = {
            str(char["fontname"]).split("+")[-1]
            for page in document.pages for char in page.chars
            if str(char.get("text", "")).strip()
        }
    missing_faces = [role for role, names in faces.items() if not actual.intersection(names)]
    if not actual or actual - allowed or missing_faces:
        raise RuntimeError(
            f"Rendered fonts do not match {family}: {', '.join(sorted(actual)) or 'no text'}. "
            f"Missing required faces: {', '.join(missing_faces) or 'none'}. "
            "Refusing font substitution; this candidate cannot be published."
        )
    return {"font_family": family, "actual_fonts": sorted(actual),
            "actual_faces": sorted(faces), "verified": True}
