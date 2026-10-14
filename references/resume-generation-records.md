# Resume Generation Records

Only successful `generate_final_resume.py publish` creates accepted history.
`prepare` leaves frozen candidates, not records of acceptance. Each publication
retains its own same-source PDF, bound review and candidate record, including
DOCX-only delivery. Repeated generations for a role remain separate; this is not
application or interview tracking. A stored review is host provenance, not proof
of semantic accuracy or reviewer independence.

## Publish and find

Put known metadata in draft `target.company`, `target.role`, `target.job_url`.
Unknown values can be omitted; metadata describes the target, not employment.
After preparing and completing independent content/visual review:

```bash
python3 "$MONKEY_RESUME_DIR/scripts/generate_final_resume.py" publish \
  --workspace "$USER_WORKSPACE" --candidate-id "$CANDIDATE_ID" \
  --review "$REVIEW_FILE" --format docx
```

Use `--format both` for matching current-output DOCX/PDF. The frozen prepare
filename supplies the default output stem; optional publish `--output-file`
explicitly renames delivery. Outputs are under `USER_WORKSPACE/resume_output`;
no legacy external `--output-dir` or target-metadata flags exist.

Open `$USER_WORKSPACE/resume_history/index.html`. Each row includes record ID,
company, role, optional posting URL, UTC generation time and a relative historical
PDF link. Missing company/role appear as 未填写. No server or cloud upload is
needed; clicking a job link opens the external posting.

The publish JSON returns `outputs`, `historical_pdf`, `history_index` and physical
QA. The historical PDF is independent of later output backups. Review occurs
before publication using candidate paths, not an already accepted historical PDF.
Always use the same external `--workspace`; default is `~/Documents/MonkeyResume`,
never inferred from filenames. Repository workspaces are rejected.

## Correct a posting URL

Copy the record ID from the directory:

```bash
python3 "$MONKEY_RESUME_DIR/scripts/resume_history_manager.py" set-url \
  --workspace "$USER_WORKSPACE" \
  --record-id "generation-REPLACE_WITH_ID_FROM_DIRECTORY" \
  --job-url "https://example.com/jobs/backend"
```

`--job-url ""` clears it. Only absolute HTTP(S) links without credentials or
whitespace are accepted. This rebuilds the directory without changing the PDF,
company, role or generation time; it does not rewrite the frozen candidate review.

## Storage and recovery

- `resume_history/generation-<uuid>/record.json`: record ID, target metadata and
  UTC `generated_at`.
- `resume_history/generation-<uuid>/resume.pdf`: independent read-only PDF copy.
- `resume_history/generation-<uuid>/review.json`: supplied bound review, including
  retained blind-reading/evidence detail when provided.
- `resume_history/generation-<uuid>/candidate-record.json`: frozen candidate bindings.
- `resume_history/index.html`: escaped offline directory.

Back up the entire `resume_history` directory to preserve relative links. History
is outside cache cleanup and same-stem output backups. Filesystem owners can
override read-only permissions; history is not a tamper-proof archive.

Rebuild a missing/stale directory from existing records (no old-PDF import):

```bash
python3 "$MONKEY_RESUME_DIR/scripts/resume_history_manager.py" rebuild \
  --workspace "$USER_WORKSPACE"
```

History uses a fail-fast `.lock` directory. After interruption, stop all writers
before removing `resume_history/.lock` and rebuilding. Handled history/publication
failures roll back the new record and preserve previously accepted outputs and
records. Abrupt termination or disk failure may need manual recovery. Legacy
candidate caches require a new workspace or separately authorized migration;
neither this history CLI nor the new workflow ships a cache migration command.
