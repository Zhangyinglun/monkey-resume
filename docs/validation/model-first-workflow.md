# Model-first workflow: implementation validation

Implementation for Issue #12, based on the decisions under `docs/design/`.
Baseline: `14a05af714986d7f9afef311a8099c5633997427`.
All candidate inputs and outputs used below are synthetic and external to the
Skill package. The personal default workspace was not read, migrated or cleared.

## Checks

| Check | Observed result |
|---|---|
| Python 3.9.6, complete unittest discovery | 114 passed; no skipped tests |
| Python 3.12.14, complete unittest discovery | 114 passed; no skipped tests |
| Python 3.14.7, complete unittest discovery | 114 passed; no skipped tests |
| `ruff check scripts templates tests` | PASS |
| `skills-ref validate "$PWD"` | PASS |
| `git diff --check` | PASS |

Commands use isolated development environments under the ignored
`.local/agent-work/` directory. Python 3.9/3.12 output is retained there in
`tests-py39.log` and `tests-py312.log`. No standalone static typechecker is
configured; passing these checks is not a static typing guarantee.

Public-interface regression coverage includes incremental and duplicate source
imports, answer-event retries, source mutation, atomic state replacement failure,
partial notes, identity corrections and explicit historical-value restoration,
negative claims, unresolved conflicts/resolution, project relationship correction,
stale draft/review bindings, entity/field ownership, multi-entity synthesis,
computed text comparisons, missing review records, artifact changes, physical
overflow and publication/history rollback. DOCX extraction covers content controls,
header/footer text and explicit rejection of embedded unreadable text.

Tests exercise actual source→cache→compile→render→publication/history seams.
Synthetic approval JSON in automated tests verifies gate mechanics only; it is
explicitly not a genuine independent review or visual-inspection result.

## Held-out synthetic host-model run

A fresh writer received an invented candidate and original JD, without the earlier
pilot drafts. The source contained two employers, six current-employer projects,
education, explicit capability denials, and a separate display-name correction.
The workflow was actual source preparation/commit, model interpretation/writing,
draft compilation/audit and default-layout DOCX/PDF preparation—without mocks,
auto-fit or layout compression.

The first candidate fit one A4 page with a measured minimum font size of 10.5 pt.
It retained queue recovery, authentication, cooling telemetry/technical leadership,
diagnosis, RAG support tooling and reviewed AI-assisted engineering. Older React
frontend work had a specific, lower-relevance omission reason. Unsupported
Terraform/Helm/broker-administration capabilities were not added.

- Render candidate: `b3ed4dfc-b6df-4835-84c3-e6df0d0d0a49`.
- Context: `sha256:fb072efa9d407727b8feb1b8e92d9ff6d5734727f3c1790125f1e2c0deac434e`.
- DOCX SHA-256: `7c5f9d3fee150ab53d32e4e76a2675adab321e8cfef5dd96ba8eaea89b37497b`.
- PDF SHA-256: `7d26cfdc8b372ba7535afd153f5045e3aee7ab982221b55b60fe1075b7bbec00`.

The external workspace is named `monkey-resume-e2e-op3hjyg8` below the executor's
approved OpenCode temporary directory. It retains original sources, proposals,
context, frozen draft, command log, candidate, previews, blind reading, evidence
review, final bound review and publication/verification results. Generated
DOCX/PDF and personalized cache files are not versioned in this repository.

### Independent review and actual visuals

Reviewer session `ses_ec6eb0050ffeGbyjQGF5wq87pw` first read only the original JD
and visible candidate. That reading was frozen before full evidence/corrections
and omission reasons were supplied. The same reviewer then independently checked
all visible assertions, 12 skill items, source project ownership and important
unused evidence. It reported no established blocking defect and one suggestion:
clarify the supported stuck-message denominator if more source evidence exists.
The bounded source wording was not expanded to invent that detail.

The independent DOCX and same-source PDF previews at 144 dpi were 1191×1684 and
pixel-identical in the tested environment. An initially blank-looking duplicate
PNG tool presentation prevented the reviewer from claiming PDF visual PASS.
The original blind record preserves that limitation. A JPEG exported directly
from the same frozen PDF resolved the presentation problem; the reviewer then
personally inspected the readable PDF and DOCX previews. It found no clipping,
overlap, missing glyphs or off-page text. Expanded justified spacing, bottom
whitespace and two short trailing lines remained nonblocking observations.

Only after complete bound content and visual results did the actual `publish`
CLI accept both formats and register history. Published bytes and the historical
PDF were verified identical to the frozen candidates. Source originals and
candidate files remain intact. Target company/role persisted; unknown job URL
remained empty. This acceptance occurred only in the synthetic workspace.

## Standards

Independent standards review inspected the complete change inventory, new
implementation files, relevant baseline hunks, callers and documented rules.
An unhashable requirement priority previously escaped descriptive validation;
its reproduced regression now produces a field-specific error and audit FAIL.
Focused re-review found no sufficiently evidenced remaining actionable standards
violation or lifecycle-maintainability defect.

## Spec

Independent spec review found two concrete gaps: DOCX content controls were skipped
and publication could accept status flags without actual review results. Both
were reproduced and fixed. Source traversal now preserves the text containers;
publication requires populated blind-reading results, original-JD quotations,
context-bound assertion/omission results and reviewer execution provenance.
Focused re-review found no sufficiently evidenced remaining spec defect in the
inspected paths. Neither review was an exhaustive line-by-line review of every
removed legacy body; final test execution was verified by the main thread.

## Limits and activation

- One held-out synthetic writing run and earlier reviewer pilots do not establish
  universal generation quality, recruiter outcomes or zero semantic errors.
- Source bindings and review record completeness do not prove entailment,
  real-world metric accuracy, human attention or cryptographic independence.
- Actual conversion/inspection used macOS, LibreOffice 26.8.1.1, Carlito and
  Poppler. Word/Google Docs/other fonts or readers can reflow editable DOCX.
- Existing personal caches and Accepted history remain untouched. New runtime
  refuses legacy schemas; migration requires a separate explicit operation or
  a deliberately new external workspace. No migration CLI was introduced.
- Restart OpenCode after the Skill/instruction changes. No push or automatic PR
  creation is part of this implementation.
