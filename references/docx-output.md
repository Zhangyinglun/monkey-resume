# DOCX-first output and matching PDF

## Mature components, one layout source

The default deliverable is an editable `.docx`, produced by python-docx 1.2.0.
`templates/docx_resume_template.py` is a small adapter from the compiled display
resume and design tokens to Word paragraphs, tab stops and borders. It does
not implement pagination, a PDF writer, or a screenshot-based Word document.

Every published PDF is exported from that exact DOCX by LibreOffice Writer.
Even DOCX-only delivery requires LibreOffice: the exported QA PDF must
pass measured one-page A4, text, bounds and readable-font QA before publishing.
The compiler validates traceability, not semantic entailment. Complete independent
content and actual visual review are required before acceptance. The required
writing/wrapping rules in `resume-language-quality.md` also apply; other section,
keyword and whitespace preferences are advisory. Auto-fit changes layout only
and measures the DOCX-derived PDF. There is no old-runtime compatibility contract.

Install LibreOffice, Poppler and Carlito fonts in addition to requirements.txt.
For Ubuntu/Debian: `apt-get install libreoffice-writer poppler-utils fonts-crosextra-carlito`.
Use the same LibreOffice version and font files when comparing outputs. No
network service receives resume content; conversion is local to the executor.

## CLI

```bash
python3 "$MONKEY_RESUME_DIR/scripts/generate_final_resume.py" prepare \
  --workspace "$USER_WORKSPACE" --draft "$DRAFT_FILE" \
  --output-file target.docx --author-id "$AUTHOR_ID"
# Complete the returned review template through actual independent review.
python3 "$MONKEY_RESUME_DIR/scripts/generate_final_resume.py" publish \
  --workspace "$USER_WORKSPACE" --candidate-id "$CANDIDATE_ID" \
  --review "$REVIEW_FILE" --format docx
```

`prepare` always attempts both artifacts and freezes the output filename (default
`resume.docx`); a safe `.docx` or `.pdf` filename is accepted, not a path.
`publish --format docx|pdf|both` controls delivery independently of that suffix.
It defaults to DOCX and the frozen name's stem. Optional publish `--output-file`
explicitly renames delivery without altering reviewed artifact bytes. There are
no old manifest/Source Snapshot arguments or inferred PDF-only filename behavior.

The default style is `professional-v2`: black text and rules, Carlito, one A4
page, 15.24 mm top/bottom margins and 16.51 mm side margins. Actual Word sizes
are 19 pt for the name, 12 pt for section headings, 11.5 pt for company/project
headings, and 11 pt for body, contact, dates and details. Body paragraphs are
left aligned; name/contact remain centered, dates use right-margin positional tabs with a plain-text word-boundary fallback.
Short headings are Experience, Skills and Education; no Summary is added.

Use `prepare --style legacy-v1` for the prior blue, justified-body layout:
12.7 mm top/bottom margins, 15.24 mm side margins, 10.5 pt body and 16.5 pt name.
The old ReportLab module is not the formal delivery renderer.

`templates/style_profiles.py` resolves the versioned defaults into existing
design tokens and layout settings. `--compact` resolves to style-specific bounded
settings. For v2, all actual text must stay at least 10.5 pt and configured page
margins at least 12.7 mm. Explicit overrides below these limits fail before
rendering. Auto-fit preserves a passing first render, including overrides and
bottom whitespace. If needed, it reduces spacing before font size, preserves
caller margins and never edits text. A failing bounded search remains a candidate;
revise selection/wording rather than violating readability limits.

Candidate records freeze style name/version, tokens, final layout, actual
half-point font sizes and available renderer/font hashes. Publication reruns
physical QA with the frozen font threshold; record and artifact bindings protect
reviewed output. Environment metadata describes this run, not rendering equality
in other readers. Existing candidates without style metadata retain the previous
8.5 pt QA floor; new legacy-v1 candidates also use that previous floor.

For a wholly fictional design comparison, run:

```bash
python3 "$MONKEY_RESUME_DIR/scripts/preview_resume_styles.py" \
  --output-dir /absolute/external/new-preview-directory
```

This development preview uses `examples/synthetic_resume.json`, renders both
styles from identical body content, retains independent DOCX and PDF page images,
and records physical QA and pixel comparison in `comparison.json`. It bypasses
candidate evidence/publication deliberately and is never an Accepted Resume.
Visually inspect the actual pages in addition to these mechanical checks.

Both formats are generated under `USER_WORKSPACE/candidates/<uuid>/`; preparation
does not publish. The response reports `physical_qa`, `qa_passed`, `render_error`
and `review_template_path`. CLI exit 0 means prepared physical QA passed, not
accepted content; 2 means physical QA not ready and 1 reports rendering/input
errors. Failed/incomplete candidates remain unpublished and accepted files stay
unchanged. Publication backs up only the
matching same-stem files (including a stale other-format counterpart), with a rollback journal if a filesystem move fails.
It does not archive unrelated resumes. Conversion errors never publish an
unchecked DOCX. There is no alternate-engine or DOCX-to-ODT fallback.

Each successful publication also retains the same-source QA PDF, review and
candidate record in durable history, even for DOCX-only delivery. Review the
candidate artifacts before publishing; the response's `historical_pdf` is the
accepted fixed reference. See `resume-generation-records.md` for storage/recovery.
Handled history failures preserve accepted outputs, and handled publication
failures roll back both the requested output pair and the new history record.

## OpenAI public skill reuse

The Apache-2.0 public OpenAI doc visual QA script is vendored unchanged at
`vendor/openai_doc/render_docx.py`; provenance, source links, fixed commit and
hashes are in `vendor/openai_doc/PROVENANCE.md`. No current private host skill is copied into this repository. The public skill recommends python-docx authoring and the
DOCX → LibreOffice PDF → PNG inspection loop used here.

Independent visual verification:

```
python3 "$MONKEY_RESUME_DIR/vendor/openai_doc/render_docx.py" /absolute/path/target.docx --output_dir /absolute/path/docx-preview --dpi 144
pdftoppm -r 144 -png /absolute/path/target.pdf /absolute/path/pdf-preview
```

Inspect every page in both sets. Compare page count, paragraph wrapping, borders,
fonts, hyperlinks, margins, page breaks, and extracted text. The independent
OpenAI preview may attempt an ODT fallback on failure; a fallback is not valid
proof of strict equivalence. Publication intentionally uses bounded direct
LibreOffice conversion with errors instead.

Check every bullet ending using the actual rendered text width defined in
`resume-language-quality.md`. Existing physical QA's sparse-ending diagnostic is
not a complete check of that rule: a programmatic PASS still requires the host
and independent reviewer to verify every bullet in both previews. Revise prose
and reprepare when an ending fails; preserve the accepted files until the new
candidate's complete content and visual review passes.

## What identical means

The PDF is the fixed-layout rendering of the exact delivered DOCX in the tested
LibreOffice/font environment. Independent rendering with the same engine and
fonts must match page pixels. Editable DOCX can reflow in Microsoft Word, Google
Docs or other readers, especially when fonts are absent, page settings change or
a reader applies different layout rules. Do not claim pixel equality in every
reader or after edits. Preserve the PDF as the fixed visual reference.

Both styles retain A4 dimensions and centered contact information. The selected
profile supplies colors, typography, alignment and spacing. A PDF from another
typography engine is not a pixel-identical reference.

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
