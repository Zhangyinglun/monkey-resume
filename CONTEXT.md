# MonkeyResume Domain

Domain language for model-led source ingestion, evidence-grounded tailoring and
review-gated delivery. Data contracts live in
`references/source-ingestion.md` and `references/resume-working-schema.md`.

## Candidate evidence

**Source Document**: original candidate material with preserved bytes and ordered,
located text blocks. It is not a render-shaped resume or an automatic semantic parse.

**Candidate Response**: the candidate's actual answer or correction, preserved
verbatim as its own source event. Document extraction and model inference are not
candidate confirmation. Retry identity is distinct from identical answer wording.

**Candidate Evidence Ledger**: durable candidate entities, claims, relationships,
conflicts and correction history, reusable across JDs.

**Candidate Profile**: supported display-name selection and presentation preferences,
not an independent source of candidate facts. Candidate identity remains stable
when the display name changes.

**Evidence Entity**: a bounded person, employment, project, education, skill,
certification or award to which claims belong; not a displayed section.

**Atomic Claim**: a source-backed assertion bound to one entity. Its polarity,
current status and evidence state determine whether it can support output.
`sourced` and `candidate_confirmed` describe origins, not semantic-certainty scores.

**Provenance**: the original source, located blocks and exact excerpt supporting
a claim or relationship. Excerpt presence alone does not establish entailment.

**Project Ownership**: a source-backed relationship between a specific project
and employment. Tools, metrics, responsibility, timing and completion scope stay
with their evidenced objects, even when several claims support one bullet.

**Correction / Conflict**: an explicit source-backed change preserving prior
history / an unresolved disagreement withholding affected claims from support.
Repetition does not silently revive superseded or revoked facts; reactivation is
an explicit supported correction.

## Tailoring

**JD Requirement**: a responsibility, required capability or preference in the
original job description. Required/preferred and AND/OR meaning survive analysis.

**Gap**: a requirement not supported by current candidate evidence. A visible
resume's omission is not by itself a candidate Gap.

**Semantic Normalization**: meaning-preserving translation into standard industry
language, without expanding tools, scope, outcomes or personal ownership.

**Draft**: the model's single target-specific writing artifact: original JD and
requirements, complete display resume, evidence links and important omissions.

**Tailored Resume**: the draft's recruiter-facing display content, without internal
IDs. Professional positioning is expressed through experience and skills; skills
may aggregate evidence and project assertions retain scope. Summary is not a
supported display section or field.

**Omission**: an important unused contribution with a specific editorial reason.
Unlisted unused facts remain available to independent review.

**Tailoring Manifest**: a program-computed mapping of display positions to claims,
entities and relationships, bound to the draft and evidence context. It is not a
model-authored plan or proof that the selected prose is true or complete.

**Traceability Audit**: deterministic reference, version, usability and structural
ownership checks. PASS means traceability only, not semantic entailment.

## Review and delivery

**Candidate**: a frozen draft and rendered artifacts awaiting publication. Its
render UUID is distinct from the stable candidate-person identity. Failed or
unverified candidates are not Accepted Resumes.

**Recruiter Review**: independent pre-publication content review: first a frozen
blind reading of JD and visible resume, then full original evidence, corrections,
assertions and important omissions. It evaluates clarity and support, not hiring
probability, protected attributes or arbitrary style quotas.

**Review Record**: actual review results bound to the current context, draft,
display and DOCX/PDF bytes, including content findings and visual inspection.
Reviewer identity and independence are host provenance declarations, not
cryptographic proof or a substitute for real review.

**Physical QA**: measurements of actual rendered one-page A4 output, text,
bounds and readable fonts. Visual review additionally inspects wrapping,
clipping, hierarchy and both artifact previews.

**Accepted Resume**: requested DOCX/PDF deliverables published after complete
current independent content review, actual visual inspection and physical QA.
This is workflow acceptance, not a guarantee of factual perfection or universal
DOCX rendering equivalence.

**Resume Generation Record (简历生成记录)**: an accepted generation's historical
PDF, review and candidate record, associated with target metadata and time.
Repeated generations remain separate; records do not imply applications or interviews.
