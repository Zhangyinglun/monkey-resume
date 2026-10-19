# 0004. Measured PDF geometry QA

## Decision

Measure the actual DOCX-derived PDF using `pdfplumber`. Publication requires a
single A4 page, in-page text bounds and readable font sizes from the frozen
current style. Use actual text positions for wrapping diagnostics rather than
character-count estimates.

The current header has one name line followed by exactly one contact-information
line before Experience. Measure this boundary using rendered word coordinates.
The required `contact_single_line` check blocks preparation from passing and
publication when contact information wraps, is absent or cannot be measured.
Independent visual review confirms the contact row by directly opening the DOCX
in a document reader's paginated view.

Physical QA does not establish factual correctness or writing quality. The host
and independent reviewer inspect every DOCX page directly in a named/versioned
reader, plus every PDF page when delivering PDF, and check the
required writing rules in `references/resume-language-quality.md`.
Metric quotas and verb/structure scores do not determine publication.

## Consequences

The PDF is evidence of layout in the tested LibreOffice/font environment.
Editable DOCX may reflow in other readers. The review and publication lifecycle
is defined by [ADR 0005](0005-model-led-draft-and-review-gated-publication.md).
