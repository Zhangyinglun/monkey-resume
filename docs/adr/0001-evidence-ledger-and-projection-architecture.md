# 0001. Evidence Ledger and Projection Architecture

## Context
Previous iterations attempted to store confirmations in separate files or attach database IDs directly into the active resume JSON. This caused path invalidation upon section reordering, schema pollution in the rendering layer, and ambiguity regarding the single source of truth for candidate facts across multiple job applications.

## Decision
We decouple candidate data into three distinct architectural tiers:
1. `base-resume.json` is an immutable **Source Snapshot** representing the raw parsed resume.
2. `candidate-evidence.json` is the durable, long-term **Candidate Evidence Ledger** storing entities and atomic claims with stable IDs, states, provenance, and metric bindings across all JDs. `candidate-profile.json` stores long-term global preferences.
3. `resume-working.json` is a pure **Tailored Resume** projection containing only display fields with no internal IDs, while `resume-changes.json` (**Tailoring Manifest**) maps every display element to its underlying Atomic Claim IDs.

## Consequences
- The rendering template remains completely clean of ledger metadata.
- Candidate evidence compounds and grows richer with each JD interaction without risking corruption of past applications.
- Reordering sections or bullets in the presentation layer never breaks claim references.

## Superseded in issue #12

[ADR 0005](0005-model-led-draft-and-review-gated-publication.md) replaces these
file contracts with atomic candidate state, immutable original source records
and one model-authored draft with program-computed manifest. The separation of
evidence from display remains; the historical decision above is not current
runtime guidance.
