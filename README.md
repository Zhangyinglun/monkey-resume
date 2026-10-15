# MonkeyResume

[简体中文](README.zh-CN.md)

An Agent Skill for importing candidate documents into a reusable local evidence
cache and writing JD-specific, one-page English resumes. The host model reads
full sources and writes the prose; local scripts preserve provenance, validate
bindings and render editable DOCX with a same-source PDF.

Traceability is not proof of truth. Publication requires a complete independent
content review and actual visual inspection, plus measured one-page A4 QA.
Unsupported requirements remain gaps, not invented experience. Professional
positioning appears in experience and skills; generated resumes have no Summary
section.

## Install

```bash
git clone https://github.com/Zhangyinglun/monkey-resume.git ~/Projects/monkey-resume
cd ~/Projects/monkey-resume
python3 -m pip install -r requirements.txt
mkdir -p ~/.agents/skills
ln -s ~/Projects/monkey-resume ~/.agents/skills/monkey-resume
```

Rendering also needs LibreOffice, Poppler and Carlito fonts; see
[output and QA](references/docx-output.md) for environment limitations.
Restart OpenCode after installing/updating the Skill or agent instructions.

## Use with your agent

**Import only:** provide a resume, work notes or candidate information document:

```text
Use $monkey-resume to import this document into my candidate cache. No JD or output resume yet.
```

**Tailor and deliver:** provide the original JD and existing candidate sources:

```text
Use $monkey-resume to tailor my resume for this role. Independently review the content and actual one-page DOCX/PDF before publishing. Deliver DOCX, and PDF if requested.
```

1. Preserve original bytes and ordered text blocks; the model reads the full
   source and proposes facts with exact excerpts. Commit validated imports.
2. Analyze the original JD and match against the complete current cache,
   including corrections, project ownership and important older experience.
3. Write one draft: `target`, `resume`, `evidence_links`, `omissions`.
   Programs compute manifests and fingerprints; there is no separate writing plan.
4. `prepare` freezes the draft, artifact hashes, output name and review template.
   Review first JD/visible resume blind, then full evidence and omissions; inspect
   every page of the actual DOCX preview and same-source PDF.
5. `publish` requires passing current review and physical QA. Incomplete review or
   rendering leaves a candidate only; handled failures preserve accepted outputs
   and history. No automatic PASS or self-review approval.

Commands and contracts: [SKILL.md](SKILL.md),
[source ingestion](references/source-ingestion.md),
[draft schema](references/resume-working-schema.md),
[review protocol](references/recruiter-review-protocol.md).

## Personal workspace

Default: `~/Documents/MonkeyResume`. Use the same external `--workspace` for one
candidate throughout; personal data never belongs in this repository.

```text
USER_WORKSPACE/
├── cache/candidate-state.json   # Ledger, Profile and immutable source registry
├── cache/sources/              # Original bytes and located text blocks
├── cache/draft.json            # Model-authored draft (example location)
├── candidates/<uuid>/          # Frozen candidate, DOCX/PDF and review template
├── resume_output/              # Accepted requested deliverables
└── resume_history/index.html   # Offline directory of accepted generations
```

Document reimports are idempotent. Candidate answers support optional `--event-id`
for retry deduplication; explicit source-backed `reactivate`/`supersedes` corrections
preserve history. Old-schema caches are refused: choose a deliberately new external
workspace or separately authorize migration. No migration CLI is shipped.

Accepted history retains the same-source PDF even for DOCX-only delivery, together
with review and candidate records. Known company/role/job URL belong in draft
`target`; see [history maintenance](references/resume-generation-records.md).

## Development checks

```bash
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)
