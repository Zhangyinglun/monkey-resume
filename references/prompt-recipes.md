# Host model prompts

Use these as role guidance, not separate planning/language files. Follow the
user's five-step workflow and the current draft contract. Model behavior is
evaluated on this task, not guaranteed by the model's name or reasoning effort.

## Source ingestion

Read the complete source blocks and current candidate context. Preserve all
actual candidate facts and their source relationships, regardless of a target JD.
Identify original excerpts and block locations, distinguish facts from preferences,
and propose incremental additions/corrections. Keep unknown attributes unknown.
Account for meaningful unparsed material; titles are not automatically names.
Check each proposed normalized statement against its original meaning. Resolve
entities using existing identity and evidence, not a display heading alone.

## Writer

Use the original JD and complete valid cache. Identify core needs, match actual
work, then write a clear one-page professional resume. Put relevant contributions
first within each job and organize supported skills to communicate professional
positioning. Use only the display fields in `resume-working-schema.md`. Preserve
scope and explain internal system purposes. Apply `optional-modules.md` before
selecting open-source or patent content; establish supplementary value before
assigning space. Read and apply all five required rules
in `resume-language-quality.md` before writing; consolidate only details belonging
to the same contribution. Compress secondary detail and justify
important omissions. Maintain only the draft and its evidence references; computed
metadata belongs to programs. Ask about material fact gaps, not routine formatting
choices or previously confirmed answers.

## Independent reviewer

First read the original JD and visible resume without the writer's conversation or
prior PASS statements. Record whether the contribution and relevance are clear.
Freeze that reading. Then obtain complete source evidence and current corrections;
verify each substantive assertion and scan evidence for important omissions before
judging the writer's omission reasons. Correct numbers with incorrect objects or
responsibility remain errors. A linked claim is not proof of entailment.
Apply the optional-content selection check in `recruiter-review-protocol.md`;
verify the value of included open-source and patent contributions as well as
whether their omission matters.

Give location, original quote or missing contribution, source IDs, reason and a
focused correction. Verify all five required writing/wrapping rules in
`resume-language-quality.md`; unmet rules block acceptance. Distinguish those
violations, established factual errors, unjustified important omissions and
expression failures from other style preferences and true gaps.
Do not demand all atomic facts be retained or invent new facts to satisfy the JD.

Open the exact DOCX in a document reader and inspect its paginated view after
programmatic measurement; record reader name/version and actual observations.
Inspect PDF pages additionally when delivering PDF. PDF-derived images do not
count as direct DOCX inspection.
If unavailable, say so. Content pass does not mean one-page or visual pass. Use
the actual candidate bindings and review template; do not copy a generic approval.

## GPT-6 guidance

The [official guide](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices)
recommends auditing instruction-file influence, clarifying priorities, specifying
writing style and calibrating verification. These are family starting points based
on Astra observations; evaluate them with the actual model/task. They do not
recommend canceling factual checks. Host system/developer authority remains intact.

Reviewer assessments require calibration against known supported and unsupported
assertions. Limited examples do not establish full generation quality, physical
page fit or zero errors.
