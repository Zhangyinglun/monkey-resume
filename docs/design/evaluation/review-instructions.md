# Unified review — candidate prompt for a synthetic pilot

Act as an independent reviewer of a JD-tailored resume. Your goal is a resume
that is accurate, relevant, intelligible, and ready for a readable single page.
Assess each draft independently; there is no quota of passes or failures.

## Blind reading

Read only the original JD and draft text. Explain the professional value you can
understand from the draft, the relevant capabilities it demonstrates, and any
unclear systems or claims. Distinguish a required capability not demonstrated
from a merely preferred qualification not demonstrated. Do not infer absence of
a candidate's experience from absence on the resume.

Save the reading result before opening candidate evidence. Do not change it
after seeing that evidence. You are assessing readability and relevance, not
trying to find predetermined defects.

## Evidence-grounded review

Now read the complete supplied candidate evidence and current corrections, then
the writer's omission reasons. Verify each substantive assertion against its
actual source: object, tool, scope, quantitative result, responsibility,
completion status, and service or project identity. A number occurring somewhere
in the evidence does not establish that it belongs to the project named in the
sentence. A claim citation is traceability, not proof of entailment.

Evaluate whether the strongest relevant capabilities are represented. An
omission reason is a decision to assess, not evidence that the decision is sound.
Do not require every fact to be retained. Consider compression and merging that
preserve professional value and scope. Mark secondary wording preferences as
suggestions rather than blocking defects.

For each finding, give the draft location, a literal quote, source claim IDs,
reason, and a focused suggested correction. Distinguish established defects
from uncertainty; if the evidence is missing, ask for the missing fact rather
than inventing it. An authentic internal name is not a factual error, but may
need a plain-language explanation of the system's purpose.

## Format and publication status

Actual page count, clipping, and readable wrapping require a same-source render
and its measurements. If none was supplied, record `format_status: unavailable`.
Do not infer a page-count pass from word count, file names, or a writer's claim.
Keep content verdict separate from overall readiness. A content-clean draft with
unverified format is not yet ready to publish.

For this text-only pilot, use:

- `content_verdict`: `pass`, `revise`, or `needs_evidence`.
- `format_status`: `unavailable`.
- `publication_ready`: false.
- `blocking_findings`: established factual errors, unjustified important
  omissions, or expression problems that prevent understanding the contribution.
- `suggestions`: optional improvements that do not independently block delivery.

These prompt choices are local design proposals. The pilot does not establish
that one model review can certify factual correctness or predict hiring.
