# AGENTS.md

Repository development instructions for the portable `monkey-resume` Skill package.

## Repository Boundary

- Treat this repository as the Skill package, not a personal resume workspace.
- Keep versioned files limited to reusable Skill resources and generic development artifacts.
- Write personal cache and generated PDFs only to the external user workspace resolved by the scripts.
- Preserve accepted PDFs when a new candidate fails QA.
- Keep `--auto-fit` limited to layout parameters.

## Start Here

1. Read `SKILL.md`.
2. Resolve the repository directory as `MONKEY_RESUME_DIR`. Use `~/Documents/MonkeyResume` as the default `USER_WORKSPACE`; pass an explicit external `--workspace` for another candidate workspace.
3. For source import, read `references/source-ingestion.md`; use `scripts/evidence_ledger_manager.py prepare/commit`. The model reads complete sources and proposes meaning; extraction only preserves located text. Use the same external `USER_WORKSPACE` throughout.
4. For tailoring, read `references/resume-working-schema.md`; initialize and write one draft with `scripts/draft_compiler.py`. Programs compute manifests. Audit checks traceability, not semantic entailment.
5. For delivery, read `references/docx-output.md` and `references/recruiter-review-protocol.md`; use `scripts/generate_final_resume.py prepare`, then independent content and actual visual review, then `publish`. Incomplete review/rendering leaves a candidate, not an Accepted Resume.

Read `CONTEXT.md` before changing domain terms or evidence/review behavior. Support only the current cache/draft/candidate contracts and professional-v3 Arial style; remove obsolete paths rather than adding compatibility adapters. Preserve existing external data and accepted artifacts; use a new external workspace for unsupported caches. Migration and old-candidate publication are outside the runtime contract. Restart OpenCode after Skill or agent-instruction updates.

## Development Checks

Use Python 3.11 or newer for development and the project-local `.venv`.

```bash
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

## Editing Rules

- Use `pathlib.Path` and UTF-8 text I/O.
- Keep imports ordered as standard library, third-party, then local modules.
- Add type annotations to changed functions and use `main() -> int` for CLI entry points.
- Raise descriptive validation or missing-path errors.
- Avoid unrelated formatting.

## Agent skills

### Issue tracker

Issues and specs are tracked in this repository's GitHub Issues using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the five canonical labels with their default names. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain documentation layout. See `docs/agents/domain.md`.
