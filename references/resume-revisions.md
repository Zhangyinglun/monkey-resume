# Revise an existing resume

Use this branch for user-requested wording, selection, ordering or layout changes
before or after delivery. Follow-up requests continue the Skill workflow; a small
edit still produces a new candidate requiring current review before acceptance.

## 1. Recover the corresponding draft

Use the same external `USER_WORKSPACE`. Read the requested resume's candidate or
history record, frozen draft, original JD and current cache context. Identify the
version the user means from conversation and recorded paths; ask only if competing
versions make the target ambiguous. Resume from that version rather than whichever
file happens to be newest or the draft used for another job.

Use its matching editable draft when available. Otherwise copy its frozen draft
to a new external editable draft, preserving the original snapshot. Restore the
original target and evidence bindings; validate them against current evidence.
If the source draft or cache cannot be recovered, report the missing input and
recover it before editing. A delivered DOCX alone does not recover evidence links.

Read `resume-language-quality.md`, the applicable cached preferences and the
requested change. Keep unrelated supported content stable unless applying the
change requires a specific factual, readability or one-page correction. Explain
any such consequential change rather than silently rewriting the whole resume.

## 2. Persist the user's feedback before applying it

Read `source-ingestion.md`, including its resume-feedback preference convention.
Preserve the exact user request in an external `.txt` source and use
`evidence_ledger_manager.py prepare --source-type candidate_response`, then
`commit` with a proposal containing the merged `preferences.resume_feedback`.
Record every requested resume change, including target-only changes; reuse the
answer event on retries. Save the user's request, not the writer's proposed
improvements or an inferred approval. A pure preference needs no new factual claim.

Separate presentation preferences from factual corrections in the same proposal.
New or corrected achievements, metrics, ownership, dates and other facts require
source-backed Ledger changes before use. Preferred wording never establishes
those facts. Apply target-only feedback to its recorded target; reuse a preference
across targets only when the user gives it candidate-wide scope. Preserve earlier
feedback and unrelated preferences when committing a new request.

Reload the committed context and verify the feedback's original request, scope
and source were saved. Report a failed write instead of claiming it was remembered;
retry or resolve it before completing the revision. Preference-only commits also
change `context_id`: reconcile current facts, conflicts and preferences before
rebinding the editable draft. Do not merely replace an old fingerprint.

## 3. Apply the change and regenerate

Edit the recovered draft's display text, evidence links and omission reasons as
needed for the request. Layout-only edits use supported renderer parameters.
Follow `docx-output.md`; `--auto-fit` remains layout-only. Generate a new frozen
candidate with `generate_final_resume.py prepare` using that editable draft.
Never patch a frozen candidate or delivered DOCX/PDF in place, or use a separate
document-generation path to bypass the draft, evidence or review workflow.

## 4. Review and deliver the new version

Follow `recruiter-review-protocol.md` for fresh independent content review and
direct DOCX visual inspection of the current candidate, plus PDF inspection when
delivering PDF. Explicitly verify
that the requested change was applied without factual, omission or layout
regressions. User approval of wording and the previous version's review cannot
stand in for the revised version's review or physical QA.

Publish only the current passing candidate through `generate_final_resume.py`
`publish`. Preserve previous Accepted Resumes and history until publication
succeeds. Failed or incomplete checks leave an unverified candidate; do not hand
it off as the updated Accepted Resume.

Report the requested changes made, any necessary related changes, the actual
feedback-cache write and its scope, current review/visual status, deliverable
paths and history link. Distinguish a saved target-only instruction from a
candidate-wide preference. This completes a revision only when both the feedback
is persisted and the new delivery meets the existing acceptance requirements.
