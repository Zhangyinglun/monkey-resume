# Current-only Arial workflow validation (2026-10-19)

## Supported contract

Only the current model-led cache, draft, review and publication contracts and
`professional-v3` Arial style are supported. Retired styles, comma-delimited
skills, independent ReportLab output and old candidate metadata are rejected or
removed. Prior implementation documents and fixtures are available in Git history,
not shipped as supported examples. External personal evidence and accepted
artifacts were not modified by this cleanup.

## Local checks

Environment: Python 3.12.14, python-docx 1.2.0, LibreOffice Writer 26.8.1.1,
Poppler 26.09.0 and actual installed macOS Arial faces. Arial is separately
licensed and is not distributed by this package. Font paths and Fontconfig
settings are local to each conversion process.

- Full unittest discovery: **146 tests passed, zero skips**.
- After simplifying the content bullet collector, all six content-check tests
  passed again.
- Ruff, Skill validation and `git diff --check`: passed.
- Independent read-only review: no blocking findings.
- Tests reject retired styles and old/missing style metadata at publication,
  preserve accepted artifacts on failure, and reject missing fonts, substitution
  and converter output containing only the regular face.

Real LibreOffice conversion fails inside the local execution sandbox. The
complete passing suite and rendering comparisons were run outside that sandbox;
no rendering failure was suppressed or converted into a passing test.

## Reproducible synthetic rendering

```bash
source .venv/bin/activate
python scripts/preview_resume_styles.py --output-dir /absolute/external/new-directory
```

The preview uses wholly fictional `examples/synthetic_resume.json`. Its DOCX,
internal QA PDF, repeated PDF reference images and `preview.json` remain
outside the Skill repository. It is not an Accepted Resume or an independent
review of actual candidate claims.

| Check | Result |
|---|---|
| Actual rendered text fonts | ArialMT and Arial-BoldMT |
| Pages | One A4 page |
| Physical QA | PASS |
| Repeated DOCX-to-PDF render versus same-source PDF | Pixel-identical; not direct DOCX inspection |
| Current page versus pre-cleanup `526c71b` professional-v3 | Pixel-identical at 144 DPI (1191 x 1684 pixels) |
| Actual page visual inspection | Readable; no clipping, overlap or company/date misalignment |

Long heading/date handling, actual Arial faces, true overflow and the real
cache-to-render-to-publication/history path are covered by passing integration
tests. A passing layout is preserved; auto-fit changes formatting only and keeps
the current readability floor and caller margins.

The current workflow requires direct DOCX viewing in a named/versioned reader
before acceptance. The synthetic preview script leaves this review pending;
the historical PDF comparisons above do not establish a direct DOCX visual pass.

## Coverage boundaries

The edited remote CI workflow has not been run. It uses Python 3.11/3.12 and
only the current Arial workflow. Actual rendering explicitly skips where
separately licensed Arial is unavailable; portable DOCX structure and missing-font
failure checks still run. Such skips are unavailable coverage, not an Arial pass.

Microsoft Word, Google Docs and Apple Pages were not tested in this cleanup.
Local LibreOffice/font comparisons do not certify those readers. Record their
software versions and observed page count, alignment, wrapping and clipping
separately when the user supplies results.
