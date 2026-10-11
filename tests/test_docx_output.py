from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from scripts import generate_final_resume as cli
from scripts.extract_resume_text import extract_docx_text
from templates.docx_resume_template import export_pdf, generate_docx, require_carlito
from tests.test_pdf_pipeline import prepare_audited_workspace, sample_resume


class DocxTemplateTests(unittest.TestCase):
    def test_body_alignment_preserves_original_style(self) -> None:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        resume = sample_resume()
        resume['projects'] = [{'name': 'Example Tool', 'tech': 'Python',
                               'bullets': ['Built a synthetic tool for monitoring service health.']}]
        with tempfile.TemporaryDirectory() as temp:
            doc = Document(generate_docx('alignment.docx', resume, temp))
            for paragraph in doc.paragraphs:
                if paragraph.text.startswith(('Backend engineer', '• ', 'Software Engineer', 'B.S.')):
                    self.assertEqual(paragraph.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY, paragraph.text)

    def test_line_height_candidates_reduce_spacing_without_changing_text(self) -> None:
        from docx import Document

        from templates.layout_settings import LayoutSettings

        with tempfile.TemporaryDirectory() as temp:
            spacings = []
            texts = []
            for scale in (1.0, 0.95, 0.92, 0.90, 0.88, 0.70):
                path = Path(generate_docx(f'{scale}.docx', sample_resume(), temp,
                                         LayoutSettings(line_height_scale=scale)))
                doc = Document(path)
                summary = next(p for p in doc.paragraphs if p.text.startswith('Backend engineer'))
                spacings.append(summary.paragraph_format.line_spacing.pt)
                texts.append(extract_docx_text(path))
            self.assertTrue(all(a > b for a, b in zip(spacings[:4], spacings[1:5])), spacings)
            self.assertLess(spacings[-1], spacings[0])
            self.assertEqual(len(set(texts)), 1)

    def test_editable_markup_escaping_links_and_round_trip(self) -> None:
        from docx import Document
        from docx.oxml.ns import qn
        resume = sample_resume()
        resume['summary'] = 'Built Map<K,V> & R&D systems.'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(generate_docx('test.docx', resume, temp))
            text = extract_docx_text(path)
            self.assertIn('Map<K,V> & R&D', text)
            self.assertIn('Example Corp\t2020 - Present', text)
            with zipfile.ZipFile(path) as archive:
                self.assertIn('mailto:alex@example.com', archive.read('word/_rels/document.xml.rels').decode())
                self.assertFalse(any(name.startswith('word/media/') for name in archive.namelist()))
            doc = Document(path)
            header = doc.paragraphs[0]
            self.assertGreaterEqual(header.paragraph_format.line_spacing.pt, 18.75)
            contact = doc.paragraphs[1]
            for size in contact._p.iter(qn('w:sz')):
                self.assertEqual(size.get(qn('w:val')), '21')

    def test_missing_converter_is_clear_error(self) -> None:
        with mock.patch('templates.docx_resume_template.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'LibreOffice is required'):
                export_pdf(Path('unpublished.docx'))

    def test_missing_font_is_clear_error(self) -> None:
        with mock.patch('templates.docx_resume_template.shutil.which', return_value='fc-match'), mock.patch(
            'templates.docx_resume_template.subprocess.run', return_value=mock.Mock(returncode=0, stdout='Other Font')
        ):
            with self.assertRaisesRegex(RuntimeError, 'Refusing silent font substitution'):
                require_carlito()

    def test_converter_timeout_does_not_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(generate_docx('test.docx', sample_resume(), temp))
            converter_reached = []

            def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
                if command[0] == 'fc-match':
                    return subprocess.CompletedProcess(command, 0, 'Carlito', '')
                self.assertEqual(command[0], 'soffice')
                self.assertIn('pdf:writer_pdf_Export', command)
                self.assertEqual(kwargs['timeout'], 120)
                converter_reached.append(command)
                raise subprocess.TimeoutExpired(command, 120)

            with mock.patch('shutil.which', side_effect=lambda name: name), mock.patch(
                'subprocess.run', side_effect=run
            ):
                with self.assertRaises(subprocess.TimeoutExpired):
                    export_pdf(path)
            self.assertEqual(len(converter_reached), 1)
            self.assertFalse(path.with_suffix('.pdf').exists())


@unittest.skipUnless(shutil.which('soffice') or shutil.which('libreoffice'), 'LibreOffice required')
class DocxPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            require_carlito()
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            raise unittest.SkipTest(f'Render integration requires Carlito: {exc}') from exc
        if not shutil.which('pdftoppm'):
            raise unittest.SkipTest('Render integration requires Poppler')

    def invoke(self, root: Path, *args: str) -> int:
        source = root / "cache/resume-working.json"
        if not source.exists():
            source = prepare_audited_workspace(root, sample_resume())
        argv = ['generate_final_resume.py', '--input-json', str(source), '--output-dir', str(root / 'output'), *args]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            return cli.main()

    def test_default_is_docx_and_pdf_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(self.invoke(root), 0)
            self.assertTrue((root / 'output/resume.docx').exists())
            self.assertFalse((root / 'output/resume.pdf').exists())
            self.assertEqual(self.invoke(root, '--format', 'pdf'), 0)
            self.assertTrue((root / 'output/resume.pdf').exists())

    def test_both_exact_docx_source_is_exported(self) -> None:
        from pdf2image import convert_from_path
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(self.invoke(root, '--format', 'both'), 0)
            actual = root / 'output/resume.pdf'
            copydir = root / 'independent'
            copydir.mkdir()
            copied = copydir / 'resume.docx'
            shutil.copy2(root / 'output/resume.docx', copied)
            renderer = Path(__file__).resolve().parents[1] / 'vendor/openai_doc/render_docx.py'
            subprocess.run([sys.executable, str(renderer), str(copied),
                            '--output_dir', str(copydir / 'preview'), '--dpi', '96'],
                           check=True, capture_output=True, timeout=120)
            a = convert_from_path(actual, dpi=96)
            pages = sorted((copydir / 'preview').glob('page-*.png'))
            self.assertEqual(len(a), len(pages))
            for expected, page in zip(a, pages):
                with Image.open(page) as actual_page:
                    self.assertEqual(expected.size, actual_page.size)
                    self.assertEqual(expected.tobytes(), actual_page.tobytes())

    def test_line_height_changes_rendered_geometry(self) -> None:
        import pdfplumber

        from templates.docx_resume_template import generate_resume
        from templates.layout_settings import LayoutSettings

        with tempfile.TemporaryDirectory() as temp:
            baselines = []
            texts = []
            for scale in (1.0, 0.95, 0.92, 0.90, 0.88):
                pdf_path = generate_resume(f'{scale}.pdf', sample_resume(), temp,
                                           LayoutSettings(line_height_scale=scale))
                with pdfplumber.open(pdf_path) as pdf:
                    words = pdf.pages[0].extract_words()
                    baselines.append(next(w['top'] for w in words if w['text'] == 'EDUCATION'))
                    texts.append(' '.join(w['text'] for w in words))
            self.assertTrue(all(a > b for a, b in zip(baselines, baselines[1:])), baselines)
            self.assertEqual(len(set(texts)), 1)

    def test_chinese_space_paths_and_legacy_pdf_filename(self) -> None:
        with tempfile.TemporaryDirectory(prefix='简历 space ') as temp:
            root = Path(temp)
            self.assertEqual(self.invoke(root, '--format', 'both', '--output-file', '候选 Resume.docx'), 0)
            for ext in ('docx', 'pdf'):
                self.assertTrue((root / 'output' / f'候选 Resume.{ext}').is_file())
            self.assertEqual(self.invoke(root, '--output-file', 'legacy.pdf'), 0)
            self.assertTrue((root / 'output/legacy.pdf').is_file())
            self.assertFalse((root / 'output/legacy.docx').exists())

    def test_explicit_filename_case_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, options in [('Resume.PDF', []), ('Resume.DOCX', ['--format', 'both'])]:
                self.assertEqual(self.invoke(root, '--output-file', name, *options), 0)
                self.assertTrue((root / 'output' / name).is_file())
            self.assertTrue((root / 'output/Resume.pdf').is_file())
            self.assertFalse((root / 'output/Resume.docx').exists())
            self.assertFalse((root / 'output/Resume.PDF').exists())

    def test_conversion_failures_preserve_accepted_pair(self) -> None:
        for failure in ('converter_missing', 'font_missing', 'timeout', 'failed_export'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                out = root / 'output'
                out.mkdir()
                for ext in ('docx', 'pdf'):
                    (out / f'resume.{ext}').write_bytes(f'accepted-{ext}'.encode())
                reached = []

                def which(name: str) -> str | None:
                    if failure == 'converter_missing' and name in ('soffice', 'libreoffice'):
                        return None
                    return name

                def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
                    reached.append(command[0])
                    if command[0] == 'fc-match':
                        font = 'Other Font' if failure == 'font_missing' else 'Carlito'
                        return subprocess.CompletedProcess(command, 0, font, '')
                    self.assertEqual(command[0], 'soffice')
                    if failure == 'timeout':
                        raise subprocess.TimeoutExpired(command, 120)
                    return subprocess.CompletedProcess(command, 1, '', 'simulated export failure')

                with mock.patch('shutil.which', side_effect=which), mock.patch('subprocess.run', side_effect=run):
                    self.assertEqual(self.invoke(root, '--format', 'both'), 1)
                expected = [] if failure == 'converter_missing' else ['fc-match']
                if failure in ('timeout', 'failed_export'):
                    expected.append('soffice')
                self.assertEqual(reached, expected)
                for ext in ('docx', 'pdf'):
                    self.assertEqual((out / f'resume.{ext}').read_bytes(), f'accepted-{ext}'.encode())
                self.assertFalse(list(out.glob('.resume-staging-*')))

    def test_failure_preserves_both_accepted_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            for ext in ('docx', 'pdf'):
                (out / ('resume.' + ext)).write_bytes(b'accepted')
            resume = sample_resume()
            resume['experience'] = [dict(copy.deepcopy(resume['experience'][0]),
                                         company=f'Example Division {i}') for i in range(8)]
            prepare_audited_workspace(root, resume)
            manifest_path = root / 'cache/resume-changes.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest['warning_dispositions'] = [{
                'finding': 'duplicate_phrases', 'status': 'accepted',
                'reason': 'Synthetic repeated text intentionally exercises physical overflow.',
            }]
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            self.assertEqual(self.invoke(root, '--format', 'both'), 2)
            for ext in ('docx', 'pdf'):
                self.assertEqual((out / ('resume.' + ext)).read_bytes(), b'accepted')
                self.assertTrue(list((out / 'rejected').glob('*.' + ext)))
            from scripts.check_pdf_quality import check_pdf_file

            report = check_pdf_file(next((out / 'rejected').glob('*.pdf')))
            self.assertFalse(next(c for c in report['checks'] if c['name'] == 'page_count')['passed'])

    def test_publish_failure_rolls_back_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            for ext in ('docx', 'pdf'):
                (out / ('resume.' + ext)).write_bytes(b'accepted-' + ext.encode())
            original = Path.replace
            publication_attempts = []

            def fail_second(source: Path, target: Path) -> Path:
                if source.parent.name.startswith('.resume-staging-') and target.parent == out:
                    publication_attempts.append(target.suffix)
                    if target.suffix == '.pdf':
                        self.assertNotEqual((out / 'resume.docx').read_bytes(), b'accepted-docx')
                        raise OSError('simulated publication failure')
                return original(source, target)
            with mock.patch.object(Path, 'replace', autospec=True, side_effect=fail_second):
                self.assertEqual(self.invoke(root, '--format', 'both'), 1)
            self.assertEqual(publication_attempts, ['.docx', '.pdf'])
            for ext in ('docx', 'pdf'):
                self.assertEqual((out / ('resume.' + ext)).read_bytes(), b'accepted-' + ext.encode())

    def test_overflow_is_rejected_without_content_mutation(self) -> None:
        import copy

        from scripts.check_pdf_quality import check_pdf_file
        from templates.docx_resume_template import generate_resume
        resume = sample_resume()
        resume['experience'][0]['bullets'] *= 30
        before = copy.deepcopy(resume)
        with tempfile.TemporaryDirectory() as temp:
            pdf = Path(generate_resume('overflow.pdf', resume, temp))
            report = check_pdf_file(pdf)
            page_check = next(c for c in report['checks'] if c['name'] == 'page_count')
            self.assertFalse(page_check['passed'])
        self.assertEqual(resume, before)

    def test_extension_conflict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.invoke(Path(temp), '--format', 'pdf', '--output-file', 'x.docx'), 1)
