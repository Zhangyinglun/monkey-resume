from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.extract_resume_text import extract_resume_blocks, extract_resume_text


class ExtractResumeTextTests(unittest.TestCase):
    def test_docx_header_and_footer_text_are_not_silently_lost(self) -> None:
        ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    f"<w:document {ns}><w:body><w:p><w:r><w:t>Project</w:t></w:r></w:p></w:body></w:document>",
                )
                archive.writestr(
                    "word/header1.xml",
                    f"<w:hdr {ns}><w:p><w:r><w:t>Alex Chen</w:t></w:r></w:p></w:hdr>",
                )
                archive.writestr(
                    "word/footer1.xml",
                    f"<w:ftr {ns}><w:p><w:r><w:t>alex@example.org</w:t></w:r></w:p></w:ftr>",
                )
            blocks = extract_resume_blocks(path)
            self.assertEqual(
                [b["text"] for b in blocks], ["Alex Chen", "Project", "alex@example.org"]
            )
            self.assertEqual(blocks[0]["location"]["part"], "word/header1.xml")

    def test_docx_embedded_unreadable_part_requires_explicit_conversion(self) -> None:
        xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:p><w:r><w:t>Readable section</w:t></w:r></w:p><w:altChunk/></w:body></w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            with self.assertRaisesRegex(ValueError, "unsupported embedded"):
                extract_resume_blocks(path)

    def test_docx_content_control_paragraphs_keep_reading_order(self) -> None:
        xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:p><w:r><w:t>Company A</w:t></w:r></w:p>
        <w:sdt><w:sdtContent><w:p><w:r><w:t>Important project</w:t></w:r></w:p></w:sdtContent></w:sdt>
        <w:p><w:r><w:t>Company B</w:t></w:r></w:p></w:body></w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            blocks = extract_resume_blocks(path)
            self.assertEqual(
                [b["text"] for b in blocks], ["Company A", "Important project", "Company B"]
            )
            self.assertIn("xml_path", blocks[1]["location"])

    def test_docx_blocks_keep_table_cells_and_order(self) -> None:
        xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:p><w:r><w:t>Company A</w:t></w:r></w:p><w:tbl><w:tr>
        <w:tc><w:p><w:r><w:t>Project B</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>20 users</w:t></w:r></w:p></w:tc>
        </w:tr></w:tbl><w:p><w:r><w:t>Next company</w:t></w:r></w:p></w:body></w:document>"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "notes.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            blocks = extract_resume_blocks(path)
            self.assertEqual(
                [b["text"] for b in blocks], ["Company A", "Project B", "20 users", "Next company"]
            )
            self.assertEqual(blocks[2]["location"]["cell"], 2)
            self.assertEqual(blocks[1]["location"]["row"], 1)

    def test_blocks_have_original_line_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "notes.md"
            path.write_text("工作笔记\n\n姓名：陈明\n项目：检索", encoding="utf-8")
            blocks = extract_resume_blocks(path)
            self.assertEqual(blocks[1]["location"]["line"], 3)
            self.assertEqual(blocks[2]["text"], "项目：检索")

    def test_empty_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.txt"
            path.write_text(" \n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "text"):
                extract_resume_blocks(path)

    def test_extracts_utf8_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "resume.txt"
            path.write_text("Résumé\nExperience", encoding="utf-8")
            self.assertEqual(extract_resume_text(path), "Résumé\nExperience")

    def test_extracts_docx_paragraphs(self) -> None:
        document_xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Alex Chen</w:t></w:r></w:p>
  <w:p><w:r><w:t>Experience</w:t></w:r></w:p></w:body>
</w:document>"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "resume.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
            self.assertEqual(extract_resume_text(path), "Alex Chen\nExperience")

    def test_rejects_unsupported_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "resume.rtf"
            path.write_text("resume", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                extract_resume_text(path)


if __name__ == "__main__":
    unittest.main()
