#!/usr/bin/env python3
"""Extract resume text from TXT, Markdown, PDF, or DOCX input."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def extract_resume_blocks(path: Path) -> list[dict]:
    """Extract ordered, locatable blocks without interpreting candidate facts."""
    suffix = path.suffix.casefold()
    blocks: list[dict] = []

    def append(text: str, location: dict) -> None:
        if text.strip():
            blocks.append(
                {"block_id": f"block-{len(blocks) + 1}", "text": text, "location": location}
            )

    if suffix in {".txt", ".md", ".markdown"}:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            append(line, {"format": "text", "line": number})
    elif suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("PDF extraction requires pdfplumber.") from None
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    raise ValueError(f"PDF page {number} has no extractable text; OCR required.")
                append(text, {"format": "pdf", "page": number})
    elif suffix == ".docx":
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        try:
            with zipfile.ZipFile(path) as archive:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
                extra_parts = {
                    name: ElementTree.fromstring(archive.read(name))
                    for name in sorted(archive.namelist())
                    if name.startswith(("word/header", "word/footer"))
                    and name.endswith(".xml")
                    or name in {"word/footnotes.xml", "word/endnotes.xml"}
                }
            body = root.find(f"{namespace}body")
            if body is None:
                raise ValueError("DOCX has no document body")

            def visit(element: ElementTree.Element, location: dict) -> None:
                if element.tag == f"{namespace}altChunk":
                    raise ValueError("DOCX contains an unsupported embedded text part (altChunk).")
                if element.tag == f"{namespace}p":
                    text = "".join(
                        (node.text or "")
                        if node.tag == f"{namespace}t"
                        else "\t"
                        if node.tag == f"{namespace}tab"
                        else "\n"
                        if node.tag in (f"{namespace}br", f"{namespace}cr")
                        else ""
                        for node in element.iter()
                    )
                    append(text, {"format": "docx", **location})
                    return
                # Transparent containers (content controls, custom XML, row/cell
                # wrappers) retain document order rather than dropping their text.
                counts: dict[str, int] = {}
                for index, child in enumerate(element, 1):
                    kind = child.tag.rsplit("}", 1)[-1]
                    counts[kind] = counts.get(kind, 0) + 1
                    child_location = {
                        **location,
                        "xml_path": f"{location['xml_path']}/{kind}[{index}]",
                    }
                    if kind in {"p", "tbl", "tr", "tc"}:
                        label = {"p": "paragraph", "tbl": "table", "tr": "row", "tc": "cell"}[kind]
                        child_location[label] = counts[kind]
                    visit(child, child_location)

            for name, part in extra_parts.items():
                if name.startswith("word/header"):
                    visit(part, {"part": name, "xml_path": "header"})
            visit(body, {"part": "word/document.xml", "xml_path": "body"})
            for name, part in extra_parts.items():
                if not name.startswith("word/header"):
                    visit(part, {"part": name, "xml_path": "footer-or-notes"})
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise ValueError(f"Invalid DOCX file: {path}") from exc
    else:
        raise ValueError(f"Unsupported resume format '{suffix}'.")
    if not blocks:
        raise ValueError(f"No extractable text found: {path}")
    return blocks


def extract_pdf_text(path: Path) -> str:
    """Extract text from a text-based PDF."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "PDF extraction requires pdfplumber; install requirements.txt first."
        ) from None

    with pdfplumber.open(path) as pdf:
        pages = [(page.extract_text() or "").strip() for page in pdf.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text:
        raise ValueError("No extractable text found in PDF. OCR the source before continuing.")
    return text


def extract_docx_text(path: Path) -> str:
    """Extract paragraph text from a DOCX file using the standard library."""
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(f"Invalid DOCX file: {path}") from exc

    root = ElementTree.fromstring(document_xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    lines: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(
            (node.text or "")
            if node.tag == f"{namespace}t"
            else "\t"
            if node.tag == f"{namespace}tab"
            else "\n"
            if node.tag in (f"{namespace}br", f"{namespace}cr")
            else ""
            for node in paragraph.iter()
        ).strip()
        if text:
            lines.append(text)
    if not lines:
        raise ValueError(f"No text found in DOCX file: {path}")
    return "\n".join(lines)


def extract_resume_text(path: Path) -> str:
    """Extract normalized text from a supported resume source."""
    suffix = path.suffix.casefold()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".docx":
        return extract_docx_text(path)
    raise ValueError(f"Unsupported resume format '{path.suffix}'. Use .txt, .md, .pdf, or .docx.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text from a resume source file")
    parser.add_argument("input_file", help="Path to .txt, .md, .pdf, or .docx input")
    parser.add_argument("--output", help="Optional UTF-8 text output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        return 1

    try:
        text = extract_resume_text(input_path)
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text.rstrip() + "\n", encoding="utf-8")
            print(f"Extracted resume text: {output_path}")
        else:
            print(text)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
