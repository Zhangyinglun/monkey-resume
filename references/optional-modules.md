# Optional modules and feedback reuse

## Select by evidence value

Keep professional experience dominant for an experienced engineer. Omit open-source
and patent content by default, whether in a standalone module or under an employer.
Include a selected contribution only when all of these conditions hold:

- It demonstrates a specific capability or responsibility important to the target
  role, supported by the original JD. Without a JD, use the candidate's stated
  outreach purpose rather than inventing job requirements.
- It adds meaningful evidence beyond the selected work history, such as a
  complementary capability, ownership, technical depth or a verifiable outcome.
- Its value justifies the space it occupies; retain stronger relevant professional
  evidence when the two compete for the one-page limit.

The JD need not mention open source or patents: judge the actual contribution's
relevance. Their presence in the cache or a previous resume, general technical
interest, patent status alone, or spare page space does not establish supplementary
value. When the value is unclear, omit the content. Apply the same evidence-value
principle to other optional modules and avoid duplicating achievements.

Decide inclusion before assigning space. For included contributions only, use
these as editable starting points, not minimum allocations, industry standards
or acceptance gates. Count rendered body lines separately from names and headings:

| Evidence | Starting space | Placement |
| --- | --- | --- |
| Open source filling a specific evidence gap | Start with one concise contribution; expand only for additional value | After experience |
| Strongly relevant open source | Roughly 4–8 body lines | Increase only when it displaces weaker evidence |
| Sustained maintainer or substantial project leadership | Treat as major experience when supported | Give space proportional to actual responsibility |
| One patent meeting the inclusion criteria | Usually one bullet, roughly 1–2 lines | Under the employer where the invention was developed |
| Several relevant patents or publications | Select a short list | Use a supported dedicated representation; avoid a full CV bibliography |
| Awards or certifications | Usually one concise line each | Include only current or material differentiators |

Let actual wrapping, readability, candidate preferences and the one-page limit
determine final space. Do not impose percentages, fixed module counts or quotas.

## Write open-source contributions

Use **action + contribution area + engineering or user value**. Retain enough
substance to distinguish the work from generic participation. Explain an obscure
project by purpose. Prefer capability-level areas such as model compatibility,
workspace recovery or data protection over request headers, internal function
names, retry counts and individual regression cases in a general recruiter resume.

Keep PR numbers, links, counts, test inventories and detailed mechanisms in the
evidence cache and master document. Include a concise link/count on the resume
only when useful to that audience or requested. Preserve completion state through
the shortest accurate verb: an implemented and submitted change is not an adopted
upstream feature. Verify current status when it affects wording.

Show importance through the supported problem, responsibility and outcome; do
not replace evidence with "major contributor", "core maintainer" or "led".
Do not claim a project's stars, downloads, users or overall performance as the
candidate's personal impact. Do not invent numerical improvements.

Fictional contrasts:

- Too vague: "Contributed to an AI project."
- Too detailed for a general resume: "Changed a provider header and added six retry tests."
- Useful level: "Improved model compatibility and integration reliability in an AI coding assistant."
- Pending upstream: "Implemented and submitted workspace recovery improvements to strengthen reliability and protect user data."

Use `projects` with `project_heading: "Open Source Projects"` when all displayed
projects are open source. Use `Projects` for a mixed selection. Keep the title in
the draft so fingerprints, review and render all describe the same artifact.

## Write patents and other distinctions

Apply the inclusion criteria above before adding patent content, including a
patent bullet under an employer. Lead an included patent bullet with the
candidate's engineering contribution, application and supported benefit. Follow
with the patent status/identifier and inventor role when those establish useful
credibility. An opaque patent title or number alone
does not communicate engineering ability. Distinguish pending from granted,
inventor from assignee, and first-listed inventor from sole inventor.

Explain an ML invention's real business application when supported. Preserve the
difference between model integration/deployment and model training; do not turn
case-assignment improvement into faster inference or higher accuracy without
evidence. Use the development employment period to show earlier experience;
do not imply the later grant date is the invention's development date.

For publications, retain authorship, venue, status and a short topic/result when
relevant. For awards, retain issuer and what was recognized. For certifications,
retain canonical name, issuer and validity when material. Do not invent unsupported
top-level display fields: the current contract supports projects, certifications
and awards; a lone patent can remain under its job. Extend schema, bindings,
renderer and review together before introducing a new standalone module type.

## Route feedback to the right durable layer

| Layer | Save | Do not confuse it with |
| --- | --- | --- |
| Skill repository | General selection/writing rules, supported rendering options, fictional examples | Personal achievements or a single candidate's mandatory wording |
| Candidate cache | Exact corrections with provenance; preferred name/contact; user-requested wording, selection and layout changes as scoped profile preferences | New evidence created merely by paraphrasing a draft |
| Master document | Complete source facts, technical mechanisms, dated statuses/links and optional concise resume formulations | A one-page resume that deletes less relevant history |
| Target draft | Selected wording, evidence bindings, important omissions and known target context | Universal preferences or the complete evidence ledger |

Ingest real user corrections through `candidate_response`; keep document facts
`sourced`. Store preference wording separately from substantive claims. Approval
of wording does not verify every underlying claim or satisfy visual QA. Preserve
the existing file identity when updating a connected master document, read it
first, add only missing material, and verify the completed write. Keep personal
files outside the skill repository and preserve original detailed sources.

For user-requested resume changes, follow `resume-revisions.md` and the
`source-ingestion.md` resume-feedback convention. Persist each request, including
target-only feedback, before regenerating; apply its recorded scope on reuse.
