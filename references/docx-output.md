# DOCX-first output and matching PDF

## Mature components, one layout source

The default deliverable is an editable `.docx`, produced by python-docx 1.2.0.
Apply the delivery-format policy in `SKILL.md` when choosing published formats
and final handoff links; the same-source QA PDF is an internal artifact unless
PDF delivery is explicitly required.
`templates/docx_resume_template.py` is a small adapter from the compiled display
resume and design tokens to Word paragraphs, tab stops and borders. It does
not implement pagination, a PDF writer, or a screenshot-based Word document.

Every published PDF is exported from that exact DOCX by LibreOffice Writer.
Even DOCX-only delivery requires LibreOffice: the exported QA PDF must
pass measured one-page A4, text, bounds and readable-font QA before publishing.
The name occupies its own line, followed by exactly one contact-information line
before Experience. The `contact_single_line` physical check counts actual rendered
lines in this header using PDF word coordinates; two or more contact lines, a
missing contact line or an unidentifiable header block publication. Preparation
reports this check and publication reruns it, including for DOCX-only delivery.
Shorten redundant display labels or visible link text while preserving supported
contact facts and link destinations, then reprepare and review. Keep readable
fonts and permitted margins; unresolved wrapping leaves a candidate unpublished.
Confirm the same single-line contact row by directly opening the exact DOCX;
a passing PDF measurement alone does not establish another reader's layout.
The compiler validates traceability, not semantic entailment. Complete independent
content and actual visual review are required before acceptance. The required
writing/wrapping rules in `resume-language-quality.md` also apply; other section,
keyword and whitespace preferences are advisory. Auto-fit changes layout only
and measures the DOCX-derived PDF. There is no old-runtime compatibility contract.

Install LibreOffice, Poppler and Arial in addition to requirements.txt.
Only `professional-v3` is supported. Arial is installed separately under its
applicable license and is not bundled in this package. A compatible substitute
is not Arial. For Ubuntu/Debian, `apt-get install libreoffice-writer poppler-utils`
provides the renderer and tools; install licensed Arial separately. Keep Regular, Bold, Italic and BoldItalic available. Use the
same LibreOffice version and font files when comparing outputs. Font discovery
and any converter Fontconfig settings are local to the conversion process; no
global font configuration is required. No network service receives resume content;
conversion is local to the executor.

For native Windows setup, read `docs/guide/installation.md`. Standard LibreOffice
installations are discovered without changing PATH; `soffice.com` keeps conversion
waitable without launching the GUI bootstrapper. Poppler's `pdftoppm.exe` and
`pdfinfo.exe` must be on PATH. Use the project virtual environment's Python.

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
It defaults to DOCX and the frozen name's stem. Select `both` for a requested PDF
alongside DOCX, or `pdf` for PDF-only delivery. Optional publish `--output-file`
explicitly renames delivery without altering reviewed artifact bytes. There are
no old manifest/Source Snapshot arguments or inferred PDF-only filename behavior.

The only supported style is `professional-v3`: black text and rules, Arial, one A4
page, 15.24 mm top/bottom margins and 16.51 mm side margins. Actual Word sizes
are 19 pt for the name, 12 pt for section headings, 11.5 pt for company/project
headings, and 11 pt for body, contact, dates and details. Body paragraphs are
left aligned; name/contact remain centered. Dates use standard right-aligned
tab stops; a long heading/date pair may place the complete date on a separate
right-aligned line to prevent overlap. Ordinary text, styles and hyperlinks have
explicit font settings. Short headings are Experience, Skills and Education; no
Summary is added.

`templates/style_profiles.py` supplies the current design tokens and layout
settings. `--compact` resolves to bounded settings. All actual text must stay
at least 10.5 pt and configured
page margins at least 12.7 mm. Explicit overrides below these limits fail before
rendering. Auto-fit preserves a passing first render, including overrides and
bottom whitespace. If needed, it reduces spacing before font size, preserves
caller margins and never edits text. A failing bounded search remains a candidate;
revise selection/wording rather than violating readability limits.

Candidate records freeze style name/version, tokens, final layout, actual
half-point font sizes and available renderer/font hashes. The converter checks
actual rendered text fonts, including regular and bold faces: font installation
alone does not prove that LibreOffice used them. Missing Arial or substituted
rendered fonts block preparation from passing. Publication rechecks font evidence
and the current candidate contract; physical QA uses the frozen readable-font
threshold. Old candidates and missing current style metadata are unsupported.
Record and artifact bindings protect reviewed output. Environment metadata
describes this run, not rendering equality in other readers.

For a wholly fictional current-style design preview, run:

```bash
python3 "$MONKEY_RESUME_DIR/scripts/preview_resume_styles.py" \
  --output-dir /absolute/external/new-preview-directory
```

This development preview uses `examples/synthetic_resume.json`, renders the
current Arial style, retains PDF reference images, and records
physical QA and repeated PDF-render pixel comparison in `preview.json`. Its
direct DOCX visual status remains pending until the file is opened and inspected.
It bypasses
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

## Direct DOCX visual inspection

Open the frozen candidate `.docx` itself in an available document reader, such as
Microsoft Word, LibreOffice Writer or Pages. Use its paginated/print-layout view
at a readable zoom. Inspect the actual view or screenshots captured from it,
including page boundaries and every page; text extraction, a thumbnail of only
the first page, HTML reconstruction and DOCX-to-PDF images are insufficient.

For example, on macOS use `open -a "LibreOffice" /absolute/path/target.docx`, or
choose Microsoft Word/Pages if that is the intended reader. On Linux use
`libreoffice --view /absolute/path/target.docx`. Opening the file alone is not
inspection. Use available host document/UI tools to view and capture the pages;
otherwise an independent human can perform the same review. Do not save changes
to the frozen candidate. If the reader changes the DOCX, reprepare and review the
new bytes. Never treat launching a reader as visual PASS.

Record `visual.method: direct_docx`, the reader's actual name/version, observed
page numbers and concrete `visual.observations` in the bound review. Check
pagination, wrapping, contact lines, bullet endings, fonts, borders, margins,
date alignment and clipping. Keep screenshots outside the Skill repository and
include their paths in observations when captures are available. If direct
viewing, page coverage or reader metadata is unavailable, keep visual review
pending and report the missing check. A local PDF measurement cannot replace it.

The tested reader defines the scope of the result: a LibreOffice or Pages
inspection does not certify Word. Prefer the intended recipient's reader when
available; report the actual reader and limitations at handoff.

DOCX-only delivery requires this direct DOCX inspection; internal QA PDF visual
inspection is optional. For `--format pdf` or `both`, also inspect every delivered
PDF page and set `visual.pdf_preview_inspected: true` only after doing so.

## PDF reference rendering

The Apache-2.0 public OpenAI doc visual QA script is vendored with local
Windows/process-lifetime fixes at
`vendor/openai_doc/render_docx.py`; provenance, source links, fixed commit and
hashes are in `vendor/openai_doc/PROVENANCE.md`. No current private host skill is copied into this repository. The public skill recommends python-docx authoring and the
DOCX → LibreOffice PDF → PNG loop retained for internal PDF reference checks.
This loop does not inspect a DOCX reader's live view.

Optional repeated PDF rendering and PDF page images:

```
python3 "$MONKEY_RESUME_DIR/scripts/render_pdf_reference.py" /absolute/path/target.docx --output_dir /absolute/path/pdf-repeat-preview --style professional-v3 --dpi 144
pdftoppm -r 144 -png /absolute/path/target.pdf /absolute/path/pdf-preview
```

These images can check the fixed PDF reference and repeatability in the same
engine. They cannot set `docx_preview_inspected` to true. The vendored OpenAI
renderer may attempt an ODT fallback on failure; that fallback is not strict
DOCX/PDF equivalence evidence. Publication uses bounded direct LibreOffice
conversion with errors instead. Both paths encode profile paths as absolute file
URIs and stop the converter process tree on timeout; previews also bound Poppler
calls. A conversion timeout leaves review pending, not accepted.

Check every bullet ending using the actual rendered text width defined in
`resume-language-quality.md`. Existing physical QA's sparse-ending diagnostic is
not a complete check of that rule: a programmatic PASS still requires the host
and independent reviewer to verify every bullet in the direct DOCX view (and
the PDF when delivering it). Revise prose
and reprepare when an ending fails; preserve the accepted files until the new
candidate's complete content and visual review passes.

## What identical means

The PDF is the fixed-layout rendering of the exact delivered DOCX in the tested
LibreOffice/font environment. Independent rendering with the same engine and
fonts must match page pixels. Editable DOCX can reflow in Microsoft Word, Google
Docs or other readers, especially when fonts are absent, page settings change or
a reader applies different layout rules. Do not claim pixel equality in every
reader or after edits. Preserve the PDF as the fixed visual reference.

The current style uses A4 dimensions and centered contact information, with
explicit colors, typography, alignment and spacing. A PDF from another
typography engine is not a pixel-identical reference.

## Supported validation environment

Local automated PDF measurements use LibreOffice Writer, actual Arial and Poppler.
Direct visual inspection additionally requires an available document reader and
access to its paginated view, through host tools or an independent human.
See `docs/validation/professional-v3.md` for recorded local Arial evidence.
A rendering test skipped because Arial is absent
is recorded as unavailable coverage, not an Arial pass.

Record direct-view software name, version and observed page count, alignment,
wrapping and clipping separately from automated PDF measurements. Additional
reader results supplied by the user stay attributed to that reader.
A local LibreOffice pass does not certify Microsoft Word, Google
Docs or other readers. Font embedding and pixel equality across readers are not
part of this contract. English resume typography and Chinese filenames are the
scope; Chinese resume typography is not certified.

Line-height scaling changes paragraph leading independently of font size.
A minimum of 1.1 times the font size prevents excessive compression; once this
floor is reached, lower scales intentionally have no further effect. Auto-fit
reduces section and item spacing before trying the bounded font reduction.

Dependencies: python-docx 1.2.0 (MIT), pdf2image 1.17.0 (MIT), LibreOffice
(MPL-2.0), Poppler (GPL-2.0-or-later), and Arial
(separate licensed installation). Only the Apache-2.0
OpenAI QA script and its license are vendored. System executables and fonts are
installed separately.
