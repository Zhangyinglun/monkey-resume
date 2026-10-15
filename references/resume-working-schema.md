# Single-draft data contract (schema 2)

The model writes one draft; programs compute fingerprints, manifests and candidate
records. All personalized files are external to this Skill package.

## Cache context

`cache/candidate-state.json` atomically stores the stable `candidate_id`, Ledger,
Profile and immutable source registry. Ledger entities have stable IDs, kinds,
claims and project→employment relations. Claims carry normalized text, original
provenance, polarity, evidence state and correction history. Conflicts suspend
both sides. The context command returns complete evidence plus usable
`active_claim_ids`, resolved `display_name` and computed `context_id`.

Empty/incomplete source caches are valid; a cache is not a display resume. Source
documents are ingested through `references/source-ingestion.md`.

## Initialize

```bash
python3 "$MONKEY_RESUME_DIR/scripts/draft_compiler.py" init \
  --workspace "$USER_WORKSPACE" --jd "$ORIGINAL_JD_FILE" --output "$DRAFT_FILE"
```

The command freezes literal original JD text and current metadata into an editable
draft. It refuses to overwrite an existing draft. Complete the model fields;
empty scaffold content is not acceptable candidate content.

## Four core fields

- `target`: `original_jd` is the full original UTF-8 text, not a path or a writer's
  summary. `requirements` contains `{id, text, priority}` records with P1/P2/P3.
  Optional `company`, `role`, `job_url` are known target metadata.
- `resume`: pure display fields `name`, `contact`, `skills`,
  `experience`, `education`; optional projects/certifications/awards. Skills use
  `{category, items: [strings]}`. Internal IDs never appear inside display text.
- `evidence_links`: display positions map to supporting claim IDs. Structural
  sections also declare their exact entity anchors.
- `omissions`: important omitted claims and specific editorial reasons. Not every
  unused atomic fact needs a reason; the reviewer independently checks omissions.

`resume.summary` and `evidence_links.summary` are unsupported and rejected,
including empty values. Remove both from older editable drafts and place important
supported facts in the appropriate experience or skills fields. Original sources,
candidate evidence and accepted historical resumes remain intact. The displayed
resume starts with experience after the contact header; there is no optional
Summary section.

`schema_version: 2` and `context_id` are generated metadata. An optional
`candidate_id` must match the cache. Reload/rebind after facts, preferences or
conflicts change; replacing a fingerprint without checking evidence is not review.

## Evidence links

```json
{
  "name": {"claim_ids": ["SELECTED DISPLAY NAME CLAIM"]},
  "experience[0]": {"entity_id": "EXACT EMPLOYMENT ID"},
  "experience[0].bullets[0]": {"claim_ids": ["PROJECT CLAIM"]},
  "education[0]": {"entity_id": "EDUCATION ID"},
  "skills[0].items[0]": {"claim_ids": ["SUPPORTED TECHNOLOGY CLAIM"]}
}
```

Use actual IDs, not these illustrative labels. Name must equal the currently
selected positive profile name claim. Contact binds profile facts. Each
employment/education/project/etc. entry has the matching kind's entity anchor.
Exact unique structural attributes under that anchor can be automatically linked;
rewritten attributes need explicit claims on the correct field/entity.

Employment bullets can combine their own claims and sourced projects explicitly
owned by that employment ID, not merely a company-name match. Project bullets
remain on their project. Skills can aggregate different entities.
Grouping titles are presentation metadata supported by their bound items.
No fixed bullet count, skill-group count, content-fit revision count or language
self-report is required.

Metrics and responsibilities cannot migrate between projects even when all claim
IDs occur together. The compiler checks references and structural relationships;
independent review establishes whether each assertion is actually supported.

## Omissions

Each record is `{claim_ids: [actual IDs], reason: "specific selection reason"}`.
Claims must be usable, not already used or repeated in another omission. The
program lists all other unused usable claims for review, without inventing reasons.

## Compile / audit

```bash
python3 "$MONKEY_RESUME_DIR/scripts/draft_compiler.py" compile \
  --workspace "$USER_WORKSPACE" --draft "$DRAFT_FILE" --output-dir "$COMPILED_DIR"
python3 "$MONKEY_RESUME_DIR/scripts/audit_factual_integrity.py" \
  --workspace "$USER_WORKSPACE" --draft "$DRAFT_FILE"
```

Compilation creates `compiled-draft.json`, `resume.json` and `manifest.json`.
The manifest records display text, claim/entity/relationship IDs, computed input
and display fingerprints, and unused evidence. These are program outputs, not
additional model-authored plans. Audit PASS means **traceability_only** and
explicitly requires semantic review; it is not a factual accuracy or completeness
score. Unknown schema, stale context, negative/revoked/conflicting support and
wrong ownership are rejected. No old-schema runtime fallback exists.

`compiled-draft.json.text_changes` contains program-generated word comparisons
between each bound claim text and the rendered text. They help locate edits;
changed/equal text is not a semantic verdict, and multi-claim synthesis is not
automatically categorized as truthful paraphrase.
