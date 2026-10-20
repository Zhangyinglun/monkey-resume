# MonkeyResume

[简体中文](README.zh-CN.md)

An Agent Skill for importing candidate documents into a reusable local evidence
cache and writing JD-specific, one-page English resumes. The host model reads
full sources and writes the prose; local scripts preserve provenance, validate
bindings and render editable DOCX. Delivery defaults to DOCX; PDF is delivered
only when the user requests it or an application entrance explicitly requires it.
A same-source PDF is retained internally for QA and history.

Traceability is not proof of truth. Publication requires a complete independent
content review and direct DOCX visual inspection in a named/versioned document
reader, plus measured one-page A4 QA. PDF images cannot replace the DOCX check.
Unsupported requirements remain gaps, not invented experience. Professional
positioning appears in experience and skills; generated resumes have no Summary
section.

The only supported style, `professional-v3`, uses Arial, black text, left-aligned
11 pt body, short headings, standard right-aligned date tabs and bounded auto-fit.
The current model-led draft workflow is the only supported runtime contract.
Older styles, input formats and candidates cannot be used to generate or publish
new output. Existing personal evidence and accepted artifacts remain preserved
in the external workspace.
To preview the current style with fictional content, run
`python3 scripts/preview_resume_styles.py --output-dir /absolute/external/new-directory`.
Design previews are not Accepted Resumes.

## Install

Linux / macOS (Bash):

```bash
git clone https://github.com/Zhangyinglun/monkey-resume.git ~/Projects/monkey-resume
cd ~/Projects/monkey-resume
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
mkdir -p ~/.agents/skills
ln -s ~/Projects/monkey-resume ~/.agents/skills/monkey-resume
```

For native Windows, use the [PowerShell installation and validation commands](docs/guide/installation.md#windows-powershell-no-wsl-required).
WSL is not required. Use `.venv\Scripts\python.exe`; LibreOffice's bundled Python
is not the project interpreter.

Rendering also needs LibreOffice, Poppler and Arial. Install Arial separately under its
license; font files are not bundled. Missing fonts or actual rendered substitution
block a candidate from passing, even if a replacement looks similar. See
[output and QA](references/docx-output.md) for setup and environment limitations.
Automated PDF measurements and direct DOCX reader results are reported separately;
identical display across software is not guaranteed. Direct inspection requires
host access to the reader's paginated view or an independent human review.
Restart OpenCode after installing/updating the Skill or agent instructions.

For development, use Python 3.11 or newer, activate `.venv` and install
`requirements-dev.txt`.
This includes PyYAML, Ruff and the pinned Skill validator used in CI. Run checks
with that environment active; dependencies remain in the project environment.

## Use with your agent

**Import only:** provide a resume, work notes or candidate information document:

```text
Use $monkey-resume to import this document into my candidate cache. No JD or output resume yet.
```

**Tailor and deliver:** provide the original JD and existing candidate sources:

```text
Use $monkey-resume to tailor my resume for this role. Independently review the content and directly inspect the one-page DOCX in a document reader before publishing. Deliver DOCX, and inspect/deliver PDF if requested.
```

1. Preserve original bytes and ordered text blocks; the model reads the full
   source and proposes facts with exact excerpts. Commit validated imports.
2. Analyze the original JD and match against the complete current cache,
   including corrections, project ownership and important older experience.
3. Write one draft: `target`, `resume`, `evidence_links`, `omissions`.
   Programs compute manifests and fingerprints; there is no separate writing plan.
4. `prepare` freezes the draft, artifact hashes, output name and review template.
   Review first JD/visible resume blind, then full evidence and omissions; inspect
   every DOCX page directly in a reader and record its name/version and
   observations. Inspect PDF pages additionally when delivering PDF.
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
preserve history. Only the current cache schema is supported. For an unsupported
cache, use a deliberately new external workspace and retain the original data.
Migration is outside the runtime contract; no migration CLI is shipped.

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
