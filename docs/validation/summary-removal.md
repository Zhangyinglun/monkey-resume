# Summary removal validation

Validated on 2026-10-14 against the changes based on `feb989a16175d937f258a669f488bc4c0539da8e`.

## Behavior

Generated resumes start with professional experience after the contact header.
There is no Summary field, section, rendering option, required heading, or
section geometry. An older `resume.summary` field is rejected for every value,
including empty strings and null. An `evidence_links.summary` binding without a
display field is rejected as an unknown display path.

The candidate evidence cache and Accepted Resume history are unchanged. Facts
previously selected for an introduction remain available for selection and
important-omission review. Existing historical files are not rewritten.

## Checks

- Full unittest discovery: **121 tests passed, zero skips**, 6.313 seconds.
- Ruff over scripts, templates and tests: passed.
- Skill validation: passed using the `skills-ref` 0.1.1 package's
  `agentskills validate` entry point. Development dependencies were installed in
  a temporary directory; no system Python installation was changed.
- `git diff --check`: passed.
- Independent Standards and Spec code reviews: no blocking findings.

The initial sandbox run could not export LibreOffice PDFs and lacked PyYAML.
The final full run used the bundled Python 3.12 runtime, temporary development
dependencies and local execution outside the sandbox. Real rendering tests ran;
they were not skipped or replaced by mocks. Synthetic publication approvals in
tests verify gate mechanics, not an actual candidate's content review.

## Actual layout verification

Environment: macOS, LibreOffice **26.8.1.1**, Carlito Regular/Bold and Poppler.
Both wholly synthetic samples used the existing readable default layout. The
same-source PDF was compared with an independent DOCX preview at **144 DPI**.

| Sample | Content | Pages | Physical QA | DOCX/PDF pixels | Minimum bullet final-line fill |
|---|---|---|---|---|---|
| Minimal | One job, four bullets, skills and education | 1 A4 | PASS | Equal | 66.8% |
| Detailed | Three jobs, one project, sixteen bullets, three skill groups and education | 1 A4 | PASS | Equal | 57.5% |

The detailed sample contains seven wrapped bullets. Final-line fill was measured
against each paragraph's available text width, excluding the bullet marker;
every bullet exceeded 50%. Independent previews are pixel-identical to the
same-source PDF, so the measurements cover both preview sets in this environment.

Actual page images were inspected: contact leads directly into experience,
section borders and dates align, wrapped bullets retain hanging indentation,
and no empty Summary block, clipping or overlap is present. The minimal sample
intentionally retains substantial bottom whitespace; no content or layout was
expanded to fill it. Bottom whitespace is advisory.

Evidence was generated outside the Skill package under
`/tmp/monkey-resume-summary-qa/` and copied to the task's external artifact folder
`summary-removal/`: editable DOCX, same-source PDF, independent preview PNGs,
synthetic input JSON, QA measurements, reproduction scripts and full test log.
These samples are template validation artifacts, not Accepted Resumes.

This validates the tested LibreOffice/font environment. It does not certify
identical pagination in Microsoft Word, Google Docs, or a reader missing Carlito.
