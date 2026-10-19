# Arial professional-v3 validation (2026-10-19)

Specification: [Issue #13](https://github.com/Zhangyinglun/monkey-resume/issues/13).

## Local environment and checks

The configured project environment uses Python 3.12, python-docx 1.2.0,
LibreOffice Writer 26.8.1.1, Poppler 26.09.0 and installed macOS Arial faces.
Fonts are resolved locally and provided only to the conversion process; this
package does not distribute Arial or change global font configuration.

- Full unittest discovery: **151 tests passed, zero skips**.
- Ruff, Python compilation, dependency consistency, Skill validation and
  `git diff --check`: passed.
- Regression tests reject missing required fonts and actual converter font
  substitution. A new publication font failure preserves accepted files and the
  previous generation's history.
- The real cache/render/review-gate/history integration tests also passed with
  `MONKEY_RESUME_TEST_STYLE=professional-v2`, covering the CI rendering selection.

The initial Arial regression reproduced an actual Liberation Sans substitution
despite installed Arial. The passing run supplies process-local font paths and
checks the rendered characters' font names against the selected font family.

## Synthetic document evidence

Run the reproducible preview outside the repository:

```bash
source .venv/bin/activate
python scripts/preview_resume_styles.py --output-dir /absolute/external/new-directory
```

| Style | Actual rendered text fonts | Pages | Physical QA | Independent DOCX preview |
|---|---|---|---|---|
| professional-v3 | ArialMT, Arial-BoldMT | 1 A4 | PASS | Pixel-identical |
| professional-v2 | Carlito-Regular, Carlito-Bold | 1 A4 | PASS | Pixel-identical |
| legacy-v1 | Carlito-Regular, Carlito-Bold | 1 A4 | PASS | Pixel-identical |

The v3 page was visually inspected: company/date alignment, heading hierarchy,
links, indentation and all text are readable without clipping or overlap. All
11 bullet final lines exceed half their available text width; the shortest is
76.2%. The new independent-preview wrapper uses the same actual font family as
the main conversion while keeping the vendored renderer unchanged.

A second actual v3 sample used a long company name and
`September 2020 - September 2026`. The complete date moves to its own
right-aligned line below the company. Measured coordinates show no overlap;
the sample remains one A4 page and passes physical QA. Its page was also
visually inspected. No personal candidate cache or Accepted Resume was changed.

The preview's DOCX, internal QA PDF, page images, font hashes and comparison
report remain outside the Skill repository. These fictional examples are design
previews, not Accepted Resumes or evidence of an actual independent resume review.

## Coverage boundaries

The user owns cross-software testing. Microsoft Word, Google Docs, Apple Pages
and other readers have **not** been certified by these local checks. Record
software/version and observed pagination, alignment, wrapping and clipping when
the user supplies those results; do not infer them from local preview equality.

The Linux CI configuration intentionally uses the installed Carlito profile for
real rendering and explicitly reports unavailable actual-Arial coverage as a
skip. Missing-font failure and portable DOCX structure tests still run. Arial
is separately installed where licensed; a replacement font is not an Arial pass.
The edited remote CI workflow has not been run as part of this local validation.
