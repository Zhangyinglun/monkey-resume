# Resume Generation Records

Every successful `generate_final_resume.py` generation automatically copies its same-source QA PDF into an independent Resume Generation Record, including default DOCX-only delivery. History stores the fixed PDF reference, not an editable DOCX archive. Repeated generations for the same role remain separate. Failed factual/content/PDF checks or handled history/publication errors create no record. Host visual inspection remains a separate required workflow step; the directory certifies automated gates, not a visual verdict or a submission.

## Generate and find

```bash
python3 "$MONKEY_RESUME_DIR/scripts/generate_final_resume.py" \
  --workspace "$USER_WORKSPACE" \
  --input-json "$USER_WORKSPACE/cache/resume-working.json" \
  --output-file "target_resume.docx" \
  --company "Northstar Systems" --job-title "Backend Engineer" \
  --job-url "https://example.com/jobs/backend" --auto-fit
```

The existing mandatory evidence, Source Snapshot, and manifest inputs default to files beside the input JSON. Omit unknown metadata flags; company and role appear as 未填写, and an absent URL never blocks generation. Metadata describes the target, not candidate employment history.

Open `USER_WORKSPACE/resume_history/index.html` in your browser. Use browser Find to locate a company or role. Each row includes its record ID, UTC generation time and a relative link to its historical PDF. No server, network assets, or cloud upload is needed. Job links open the external posting when clicked.

The generator prints the exact `Historical PDF` path. Use that persistent PDF for quality reporting, visual QA and Recruiter Review even when no PDF was requested in `resume_output`. Request `--format both` during generation when the user also needs a matching current-output PDF. Reuse the same PDF path in review snapshots and report commands.

Always pass the same external `--workspace` used for evidence/cache. If omitted, it defaults to `~/Documents/MonkeyResume`; it is never inferred from input or output names. Output defaults to `USER_WORKSPACE/resume_output`. Explicit external `--output-dir` remains supported for legacy commands, even outside the workspace, but history always belongs to the resolved workspace. Skill-managed workflows keep both in the same workspace. Repository output and history are rejected.

## Fill or correct a posting URL

Copy the record ID from the directory, then run:

```bash
python3 "$MONKEY_RESUME_DIR/scripts/resume_history_manager.py" set-url \
  --workspace "$USER_WORKSPACE" \
  --record-id "generation-REPLACE_WITH_ID_FROM_DIRECTORY" \
  --job-url "https://example.com/jobs/backend"
```

Use `--job-url ""` to clear it. Only absolute HTTP(S) links without credentials or whitespace are accepted. Updating a link rebuilds the directory and leaves the original PDF, company, role, and generation time unchanged.

## Storage and recovery

- `resume_history/generation-<uuid>/record.json`: `record_id`, `company`, `job_title`, `job_url`, `generated_at` (UTC ISO 8601).
- `resume_history/generation-<uuid>/resume.pdf`: independent read-only PDF copy, never rewritten by generation or URL updates.
- `resume_history/index.html`: generated offline directory; all metadata is escaped.

History is outside cache cleanup and unaffected by same-stem DOCX/PDF publication backups. Back up the entire `resume_history` directory to preserve relative links. Do not edit or replace historical PDFs; filesystem owners can still override read-only permissions.

Rebuild a missing/stale directory from existing records (this does not import old PDFs):

```bash
python3 "$MONKEY_RESUME_DIR/scripts/resume_history_manager.py" rebuild \
  --workspace "$USER_WORKSPACE"
```

History writes use a fail-fast `.lock` directory. After an interrupted process, stop all writers before removing `resume_history/.lock` and rebuilding the directory. Handled write/publication errors roll back the new record; abrupt termination or disk failure can require manual recovery. There is no old-PDF import, application status, or interview tracking.
