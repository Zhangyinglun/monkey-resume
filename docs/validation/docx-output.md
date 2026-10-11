# DOCX-first validation (2026-10-11)

Baseline main: `38e2fede8092c2d176bc4346daba150620018fa9`.
This is a fresh cloud-environment run, not the earlier candidate's 128-pass claim.
Only synthetic candidate data was used. No personal cache was read or changed.

## Toolchain and source verification

- Python 3.12; python-docx 1.2.0; pdf2image 1.17.0; pdfplumber 0.11.10.
- LibreOfficeDev 26.8.0.0.alpha0, build
  `2c87e51eeaa2b413ff4ae097b2705eea1995d8e5` (development build).
- Carlito at googlefonts/carlito commit
  `3a810cab78ebd6e2e4eed42af9e8453c4f9b850a` (OFL), configured outside the
  repository through a task-local Fontconfig file. Regular, Bold, Italic and
  BoldItalic are available. No global font or plugin configuration was changed.
- Public OpenAI script and license fetched from the pinned sources in
  `vendor/openai_doc/PROVENANCE.md`; both match the recorded SHA256 hashes.
- Initial environment lacked Carlito. Candidate tests failed (3 failures,
  1 error); that run is not reported as success.

## Regression and failure evidence

A new line-height regression first failed on the candidate: scales
1, .95, .92, .90, .88, .70 all serialized as 12.3pt. After repair the first
four compression candidates differ, and independently extracted PDF positions
move upwards while text remains identical. Extreme compression stops at the
explicit glyph-clearance floor.

Timeout tests allow font preflight to succeed, then assert the LibreOffice
export invocation and 120-second timeout were reached. The rollback test
asserts DOCX was installed before the second PDF installation failed, and both
accepted byte sequences were restored. CLI tests cover missing converter,
missing font, timeout, nonzero converter exit, default DOCX, explicit PDF,
both formats, legacy PDF filename (including uppercase extensions), Chinese/space
paths and real multi-page QA. Explicit filenames retain their original spelling.
Paragraph alignment retains the original justified body and bullet styles.

The complete final test suite passed: 134 tests, zero skips (22.698 seconds). Ruff and skills-ref
validation passed. Commands (after installing requirements-dev.txt and system
renderer/font dependencies):

```bash
python -m unittest discover -s tests -v
ruff check scripts templates tests
skills-ref validate "$PWD"
```

## Independent visual and text verification

Synthetic sample: two employers, one project, three skill groups, education,
email/LinkedIn links, and a Chinese/space output path. The CLI completed factual,
content and PDF gates with `--format both --auto-fit` (10 layout trials).
The unchanged public OpenAI script reopened the delivered DOCX and rendered
its own PDF/PNG. Poppler rendered the published PDF separately at 144 DPI.
Both outputs have one page, 1191 x 1684 pixels, and zero differing pixels.
Both page images were opened and inspected: no clipping, overlap, broken
rules, or missing glyphs. The design retains navy section rules, a centered
contact header and right-aligned dates.

A second synthetic sample with eight employers and a multi-line justified
summary rendered to two pages. The actual page-count gate rejected it and
retained both rejected files for review. Both pages were independently rendered
from DOCX and compared with the rejected PDF: zero differing pixels on each.
All three final page images (one accepted, two rejected) were opened for visual
inspection after the alignment repair. The regression test confirms overflow
leaves the previously accepted DOCX/PDF unchanged.

Both DOCX and PDF text extraction produced 1142 characters. Expected candidate,
employer, project and education text was found; PDF has two clickable links
and embedded Carlito Regular/Bold fonts. DOCX contains editable text, not
page images. This verifies text-based ATS prerequisites, not every ATS product.

Cloud evidence is under `/workspace/monkey-resume-validation/` (full-tests.log,
generate.log, extracted.txt, docx-preview-final/, pdf-final-1.png,
overflow-preview/, overflow-pdf-*.png and the synthetic
DOCX/PDF in `中文 QA workspace/output/`). These files are not committed.

The real `/ask-matt` route was read at mattpocock/skills commit
`49dd158d1076134a641b33efb035946536778336`: scoped grilling/domain modeling,
approved shared understanding and TDD test seams, implementation, then separate
spec and standards reviews. Both review axes finished with zero outstanding
findings. Review repairs were covered by failing-then-passing regressions.

This certifies the recorded development renderer and fonts only; released
LibreOffice, Microsoft Word, Google Docs, and Chinese resume typography were
not validated. Chinese filenames were validated. PDF is the fixed visual
reference; DOCX may reflow in other environments or after edits.
