# Model-led resume evaluation pilot

These are wholly synthetic design assets, not candidate records or a production
resume-generation flow. No personal workspace may be read or modified for this
pilot. All reviewers receive the same synthetic JD and drafts.

## Procedure

1. Start two independent review contexts. In the first phase, supply only
   `job-description.md`, `drafts.json`, and `review-instructions.md`.
2. Each reviewer saves a blind reading assessment before opening the evidence.
3. Continue that same review context with `candidate-evidence.md` and
   `writer-decisions.json`. Preserve the blind assessment and save an
   evidence-grounded content review separately.
4. Compare those findings to the host's private expectations. Those expectations
   and the other reviewer's findings are not reviewer inputs.
5. Record misses and unwarranted blockers as well as correct findings. A claimed
   format pass without an actual document is an evaluation error.

The first phase tests whether the resume communicates its value; the second
tests factual support and whether valuable evidence was omitted. Both are parts
of one proposed review stage. This pilot measures reviewer behavior, not the
quality of a complete generated DOCX, hiring outcomes, or a failure rate.

## Files

- `job-description.md`: synthetic original JD.
- `drafts.json`: anonymous draft variants, using the existing display shape.
- `candidate-evidence.md`: source facts, corrections, and scope qualifications.
- `writer-decisions.json`: omission reasons to verify, not answers to trust.
- `review-instructions.md`: proposed review prompt.
- `reviewer-*-blind.json`: frozen blind reading results.
- `reviewer-*-content.json`: independently grounded review results.

The repository's official facts and artifact gates are not bypassed or changed.
These drafts must not be published as Accepted Resumes.
