# 0005. Model-led draft and review-gated publication

Issue #12 replaces the old render-shaped source cache, separate writing plans
and heuristic semantic guarantees with model-led full-source understanding and
one draft. Programs preserve immutable source bytes/located blocks, commit
Ledger/Profile/source registry atomically, and compute evidence bindings and
fingerprints. They check traceability, versions and physical output, not semantic
entailment or important-experience coverage. ADR 0004 defines the measured
physical QA boundary.

The alternative was to keep regex/keyword/metric gates and compatibility adapters.
Those obscure scope errors and encourage maintaining multiple authoring artifacts.
We instead accept host-model judgment and independent review as necessary, without
claiming zero hallucinations. One draft contains `target`, `resume`, `evidence_links`
and `omissions`; the pure display projection remains separate from evidence IDs.

`prepare` freezes candidate context, draft, compiled result, DOCX/PDF hashes,
author identity and output filename, then supplies a pending review template.
Review first freezes blind JD/visible-resume reading, then checks all original
evidence, corrections, assertion scope and important omissions. Actual DOCX and
same-source PDF previews join this content review stage. `publish` requires a
complete current independent review, no blocking findings, actual visual checks
and measured readable single-page A4 QA. Reviewer independence is declared host
provenance, not cryptographic proof; self-review cannot approve publication.

Incomplete rendering or review leaves candidates only. Handled publication/history
failures preserve previous accepted artifacts and history. Output names survive
preparation unless explicitly renamed on publication; every accepted generation
retains its fixed PDF and review. Layout auto-fit changes format only.

Document imports are idempotent. Candidate responses are distinct source events
with optional stable event IDs for retry deduplication; explicit source-backed
reactivation/supersession preserves correction history. Only the current
cache/draft/candidate contracts and professional-v3 Arial style are supported.
Unsupported caches require a deliberately new external workspace while retaining
original data. Migration and publication of old candidates are outside the runtime
contract. Existing accepted artifacts remain preserved externally.
