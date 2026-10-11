# DOCX-first output and matching PDF

## Mature components, one layout source

The default deliverable is an editable `.docx`, produced by python-docx 1.2.0.
`templates/docx_resume_template.py` is a small adapter from the existing evidence
projection and design tokens to Word paragraphs, tab stops and borders. It does
not implement pagination, a PDF writer, or a screenshot-based Word document.

Every published PDF is exported from that exact DOCX by LibreOffice Writer.
Even DOCX-only delivery requires LibreOffice: the exported temporary PDF must
pass the existing one-page A4, text, geometry and content gates before publishing.
Factual audit and warning dispositions remain mandatory. Auto-fit changes layout
only and now measures the DOCX-derived PDF, never the separate legacy template.
The legacy ReportLab template remains importable for existing callers, but is
not used by the publication CLI and is not guaranteed to match DOCX.

Install LibreOffice, Poppler and Carlito fonts in addition to requirements.txt.
For Ubuntu/Debian: `apt-get install libreoffice-writer poppler-utils fonts-crosextra-carlito`.
Use the same LibreOffice version and font files when comparing outputs. No
network service receives resume content; conversion is local to the executor.

## CLI

The existing factual audit arguments are unchanged. Given those arguments:

- No format/filename: `resume.docx` (new default).
- `--output-file target.docx`: DOCX only.
- `--format pdf`: `resume.pdf`.
- `--output-file target.pdf`: PDF only (backward-compatible explicit filename).
- `--format both --output-file target.docx`: `target.docx` and `target.pdf`.
- A contradictory explicit format and suffix is rejected rather than silently renamed.

Without layout flags, DOCX generation uses the approved full-page sample's
settings: Carlito, A4, 12.7 mm top/bottom margins and 15.24 mm left/right
margins. Font scale is 1.1; the actual DOCX half-point sizes are 10.5 pt for
body/bullets, 16.5 pt for the name, 11.5 pt for contact/section headings,
11 pt for company/project headings, and 10.5 pt for dates/details. These sizes
were read from the generated DOCX, not inferred by multiplying the base tokens.
Explicit layout flags still override defaults. `--compact` retains its existing
compression preset, and `--auto-fit` starts from the approved defaults before
trying existing bounded presets if needed. Auto-fit may change the final layout;
it does not add content or guarantee the same fullness for different resumes.

Both formats are generated in a staging directory. QA failures retain rejected
DOCX/PDF candidates and preserve accepted files. Publication backs up only the
matching same-stem files (including a stale other-format counterpart), with a rollback journal if a filesystem move fails.
It does not archive unrelated resumes. Conversion errors never publish an
unchecked DOCX. There is no alternate-engine or DOCX-to-ODT fallback.

## OpenAI public skill reuse

The Apache-2.0 public OpenAI doc visual QA script is vendored unchanged at
`vendor/openai_doc/render_docx.py`; provenance, source links, fixed commit and
hashes are in `vendor/openai_doc/PROVENANCE.md`. No current private host skill is copied into this repository. The public skill recommends python-docx authoring and the
DOCX → LibreOffice PDF → PNG inspection loop used here.

Independent visual verification:

```
python vendor/openai_doc/render_docx.py /absolute/path/target.docx --output_dir /absolute/path/docx-preview --dpi 144
pdftoppm -r 144 -png /absolute/path/target.pdf /absolute/path/pdf-preview
```

Inspect every page in both sets. Compare page count, paragraph wrapping, borders,
fonts, hyperlinks, margins, page breaks, and extracted text. The independent
OpenAI preview may attempt an ODT fallback on failure; a fallback is not valid
proof of strict equivalence. Publication intentionally uses bounded direct
LibreOffice conversion with errors instead.

## What identical means

The PDF is the fixed-layout rendering of the exact delivered DOCX in the tested
LibreOffice/font environment. Independent rendering with the same engine and
fonts must match page pixels. Editable DOCX can reflow in Microsoft Word, Google
Docs or other readers, especially when fonts are absent, page settings change or
a reader applies different layout rules. Do not claim pixel equality in every
reader or after edits. Preserve the PDF as the fixed visual reference.

The design retains existing A4 dimensions, navy section rules, centered contact
header, and the existing design-token sizes and spacing. The legacy ReportLab
PDF is not a pixel-identical reference: typography engines differ.

## Supported validation environment

The verified rendering target is Linux with LibreOffice Writer and Fontconfig,
Carlito Regular/Bold/Italic/BoldItalic, and Poppler. See
`docs/validation/docx-output.md` for the actual tested versions. Other operating
systems and readers are not certified by this run. Carlito does not cover CJK
text; Chinese filenames are tested, not Chinese resume typography.

Line-height scaling changes paragraph leading independently of font size.
A minimum of 1.1 times the font size prevents excessive compression; once this
floor is reached, lower scales intentionally have no further effect. The first
four auto-fit compression presets retain distinct leading at their baseline sizes.

Dependencies: python-docx 1.2.0 (MIT), pdf2image 1.17.0 (MIT), LibreOffice
(MPL-2.0), Poppler (GPL-2.0-or-later), Carlito (SIL OFL-1.1). Only the
Apache-2.0 OpenAI QA script and its license are vendored. System executables
and fonts are installed separately.
