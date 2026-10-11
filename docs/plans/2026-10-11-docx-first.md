# DOCX-first output: approved scope

Baseline: `38e2fede8092c2d176bc4346daba150620018fa9`.
The user confirmed the shared understanding and test seams on 2026-10-11.

Use python-docx to produce editable DOCX and LibreOffice to export the same
source to PDF. Default to DOCX; retain explicit PDF filenames, `--format pdf`
and `--format both`. Preserve factual/content/geometry gates, links, text
extraction, A4 design, and accepted artifacts on failure. Never modify personal
cache or resume content in auto-fit. Reuse pinned public OpenAI DOCX QA code.

Test seams: publication CLI; document generation and local conversion;
auto-fit; text extraction; filesystem publication/rollback. Exercise absent
fonts/converter, actual conversion timeout, second-file publication failure,
multi-page overflow, and Chinese/space paths. Verify editable text and links,
independent DOCX rendering, every PDF page, and searchable text. Run full old
and new tests, lint, skill validation, and independent Standards/Spec reviews.
Pixel equivalence applies only to the recorded renderer/font environment.

The actual /ask-matt route was read at mattpocock/skills commit
`49dd158d1076134a641b33efb035946536778336` (MIT): existing setup checked;
grill-with-docs (grilling + domain-modeling) shared understanding confirmed;
implement with tdd; code-review with separate Standards and Spec agents.
Existing tracker/domain configuration is retained; no external tracker writes,
push, PR, merge, or publication is authorized.
