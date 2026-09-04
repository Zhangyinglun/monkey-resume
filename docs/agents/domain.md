# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root.
- **`CONTEXT-MAP.md`** at the repo root if it exists: it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area about to be changed. In multi-context repositories, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files do not exist, **proceed silently**. Do not flag their absence or suggest creating them upfront. The `/domain-modeling` skill, reached through `/grill-with-docs` and `/improve-codebase-architecture`, creates them lazily when terms or decisions are resolved.

## File structure

MonkeyResume currently uses the single-context layout:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-evidence-ledger-and-projection-architecture.md
│       ├── 0002-silent-conversational-fact-ingestion-and-auto-reuse.md
│       ├── 0003-mandatory-pre-render-factual-audit-gate.md
│       └── 0004-true-pdf-geometry-qa-with-pdfplumber.md
├── references/
├── scripts/
├── templates/
└── tests/
```

A future multi-context repository would be identified by a root `CONTEXT-MAP.md`:

```text
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/
└── src/
    ├── context-one/
    │   ├── CONTEXT.md
    │   └── docs/
    │       └── adr/
    └── context-two/
        ├── CONTEXT.md
        └── docs/
            └── adr/
```

## Use the glossary's vocabulary

When output names a domain concept in an issue title, refactor proposal, hypothesis, or test name, use the term defined in `CONTEXT.md`. Do not drift to synonyms that the glossary explicitly marks with `_Avoid_`.

If a needed concept is not in the glossary, reconsider whether the proposed language belongs to the project. If it represents a genuine domain gap, record it for `/domain-modeling`.

## Flag ADR conflicts

If output contradicts an existing ADR, surface the conflict explicitly instead of silently overriding it:

> _Contradicts ADR-0003 (mandatory pre-render factual audit gate), but worth reopening because…_
