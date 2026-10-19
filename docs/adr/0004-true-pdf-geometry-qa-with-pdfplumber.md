# 0004. Measured PDF geometry QA

## Decision

Measure the actual DOCX-derived PDF using `pdfplumber`. Publication requires a
single A4 page, in-page text bounds and readable font sizes from the frozen
current style. Use actual text positions for wrapping diagnostics rather than
character-count estimates.

Physical QA does not establish factual correctness or writing quality. The host
and independent reviewer inspect every actual DOCX/PDF page and check the
required writing rules in `references/resume-language-quality.md`.
Metric quotas and verb/structure scores do not determine publication.

## Consequences

The PDF is evidence of layout in the tested LibreOffice/font environment.
Editable DOCX may reflow in other readers. The review and publication lifecycle
is defined by [ADR 0005](0005-model-led-draft-and-review-gated-publication.md).
