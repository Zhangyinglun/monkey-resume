# Source ingestion and local cache

Use this branch for an original resume, information document, work/project notes,
or candidate answers. It does not need a JD or a renderable/full resume.

## Prepare source

```bash
python3 "$MONKEY_RESUME_DIR/scripts/evidence_ledger_manager.py" prepare \
  --workspace "$USER_WORKSPACE" --input "$INPUT_FILE"
```

Text-based PDF, DOCX, Markdown and TXT are supported. The program returns
`source_id`, current `context_id`, `blocks` with `block_id`, text and location,
and immutable original/blocks paths. PDF page and DOCX paragraph/table locations
are preserved. A scanned/empty page or unsupported format is an explicit error,
not an empty successful import. No macros or embedded commands are executed.

DOCX content controls, paragraphs/tables, header/footer and note parts are
located separately rather than silently skipped. Unsupported embedded text
(`altChunk`) requires explicit conversion to a readable source. Text extraction
does not establish page layout, tracked-change intent or factual meaning.

Read the current context when updating a candidate. The only authoritative state
is `cache/candidate-state.json`; its Ledger/Profile/source registry commits
atomically. Original bytes and text blocks are immutable source records under
`cache/sources/`. A failed import can leave a pending source, not half-updated facts.

For a real candidate answer, write the exact answer to a `.txt` file and prepare
with `--source-type candidate_response`. Document extraction is `sourced`;
candidate answers are `candidate_confirmed`. Your inference is neither.

Each preparation of a candidate answer is a new answer event, including identical
words spoken later after a correction. For retries of that same event, reuse the
returned `event_id` with `--event-id`; this avoids duplicate ingestion. Document
imports deduplicate by content and source type.

## Model import proposal

Write one external proposal with these fields; optional arrays default empty:

```json
{
  "context_id": "COPY THE PREPARED CONTEXT ID",
  "entities": [{"ref": "person", "entity_type": "profile", "label": "Candidate"}],
  "claims": [{
    "ref": "name", "entity_ref": "person", "field": "name",
    "claim_text": "Alex Chen", "polarity": "positive",
    "block_ids": ["block-2"], "original_excerpt": "Alex Chen"
  }],
  "relationships": [],
  "preferences": {},
  "display_name_ref": "name"
}
```

This is an illustrative synthetic proposal, not input to run unchanged. Use actual
returned context/block IDs and actual source excerpts. `ref` is a proposal-local
handle; the program assigns stable UUIDs and returns actual IDs. To reuse an
existing entity, include its `entity_id` in its declaration. Claims refer to an
entity's local ref or known ID. Entity kinds are `profile`, `employment`, `project`,
`education`, `skill`, `certification`, `award`. Unknown dates/contact/education
are absent facts, not placeholder facts.

Use `field` for structural attributes (`name`, `contact`, `company`, `title`,
`dates`, `school`, `degree`, etc.), and `claim_text` for the supported normalized
meaning. Exact original excerpts remain separate. Every claim has nonempty
`block_ids` whose joined original text contains its `original_excerpt`.

Project ownership records have `project_ref`, `employment_ref`, `block_ids` and
`original_excerpt`. Evidence must establish that relationship. A name prefix
alone is not authority to associate two experiences.

## Incremental changes

- Exact repeated facts on the same entity keep their claim IDs and accumulate
  source provenance. Same committed file/content/type is `unchanged`.
- Shorter documents and partial notes do not remove existing facts. Reuse the
  correct entities; do not reinitialize the workspace for every document.
- `supersedes` lists existing same-entity claim IDs explicitly corrected by the
  new source. Old history stays. Select a supported profile name with
  `display_name_ref`; display preference does not create a name fact.
- To explicitly restore a historical value, set `reactivate: true` on its new
  source-backed claim proposal; ordinary repeated documents do not revive it.
  A changed project owner may `supersedes` existing same-project relationship IDs;
  `revoke_relationships` accepts `{relationship_id, block_ids, original_excerpt}`.
  Relations retain their superseded/revoked history. Restoring an old relation
  similarly requires explicit `reactivate: true` and source evidence.
- A negative assertion such as no Terraform uses `polarity: negative`; it is
  preserved but excluded from positive supporting IDs.
- A different apparent identity needs explicit same-candidate association or
  clarification, not automatic merge. Existing-workspace proposals may include
  its `candidate_id` when that association is actually known.

Unresolved conflicts are supplied as
`conflicts: [{claim_refs: [old_claim_id, new_local_ref], reason: "specific conflict"}]`.
Both sides are withheld from support. Do not report different objects or periods
as contradictions. Resolve with a source-backed answer:

```json
{
  "context_id": "COPY THE NEW PREPARED CONTEXT ID",
  "resolve_conflicts": [{
    "conflict_id": "ACTUAL CONFLICT ID",
    "selected_claim_ids": ["ACTUAL SUPPORTED CLAIM ID"],
    "block_ids": ["ACTUAL ANSWER BLOCK ID"],
    "original_excerpt": "EXACT CANDIDATE ANSWER"
  }]
}
```

Conflict creation/resolution changes context even without a new usable fact;
previous draft/review bindings become stale. Repeated historical wrong facts do
not revive superseded or revoked claims. The host model must detect semantic
conflicts and compare proposed meaning to the original; quote validation alone
cannot establish entailment.

## Resume feedback preferences

For user-requested resume changes, store feedback in the existing
`profile.preferences.resume_feedback` array inside `cache/candidate-state.json`.
Use the import proposal's `preferences` object and a real `candidate_response`
source; this is a host-authored preference convention under the current schema,
not a separate cache file or a program-enforced feedback schema.

Each entry contains:

- `source_id` and `block_ids`: the actual prepared answer source and located blocks.
- `original_excerpt`: the exact user request from those blocks.
- `instruction`: the actionable change, preserving the user's meaning.
- `scope`: `target` by default, or `candidate` when the user explicitly requests
  reuse across resumes, such as "use this wording style from now on".
- `target`: required for target scope. Retain the known job URL and target metadata;
  without a unique job URL, retain literal `original_jd` to identify the target,
  including the preserved outreach purpose when no JD exists. A mutable draft
  path or company name alone does not identify a target.

Append to the existing array while preserving all earlier entries. The cache
merges preferences at the top level only: when submitting `resume_feedback`,
include the complete existing array plus the new entry, not just the new entry.
Keep unrelated preference keys intact. Reusing a committed answer event is a
no-op; a new user request is a new event even if its wording repeats an older one.

At use time, apply only matching target entries and candidate-wide entries.
An explicit target instruction takes precedence over a general preference for
that target; a later explicit change supersedes an earlier conflicting instruction
within the same scope. Keep old requests as history. Do not generalize a one-job
deletion or shortening request into a permanent ban on that experience. Clarify
genuinely ambiguous conflicts rather than silently choosing a meaning.

Pure wording, selection and layout preferences need no achievement claims.
Factual corrections in the same request must also update the Ledger through the
source-backed correction rules above. Approval of phrasing alone does not verify
the facts it expresses. The original request is preserved as a source even when
it creates no claims; its blocks may therefore appear in `unparsed_blocks`.
Account for them as preference feedback in the report, without fabricating claims
to clear that diagnostic. Reload and verify the committed preference and new
context before continuing `resume-revisions.md`.

## Commit and report

```bash
python3 "$MONKEY_RESUME_DIR/scripts/evidence_ledger_manager.py" commit \
  --workspace "$USER_WORKSPACE" --source-id "$SOURCE_ID" \
  --proposal "$PROPOSAL_FILE"
```

The command checks source integrity and context before committing. Stale proposals
must be prepared/rebased again; never substitute the new context ID without
checking intervening facts. It returns status, source/state paths, entity/claim
IDs, added/existing/superseded counts, unresolved conflicts and unparsed blocks.
`committed` describes a transaction, not perfect semantic coverage. Inspect
important unparsed text and account for it before claiming the cache is complete.

Old-schema caches are not loaded by this workflow. Use a deliberately new external
workspace; migration is outside the runtime contract. Never delete the old
candidate cache or accepted history to silence a schema error.
