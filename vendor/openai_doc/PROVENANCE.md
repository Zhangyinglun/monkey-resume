# OpenAI public DOCX visual QA tool

Public `openai/skills` source, pinned to commit
`45d05d75363abf13f99d09e899d61e07b8010685`:

- https://github.com/openai/skills/blob/45d05d75363abf13f99d09e899d61e07b8010685/skills/.curated/doc/scripts/render_docx.py
- https://github.com/openai/skills/blob/45d05d75363abf13f99d09e899d61e07b8010685/skills/.curated/doc/LICENSE.txt

Apache-2.0; see LICENSE.txt. No NOTICE file existed in that skill tree.
This historical public script is pinned, not represented as the latest
maintained OpenAI skill.
No private host skill instructions are redistributed.

Upstream SHA-256 render_docx.py: 52b3c3158913ebcad2ada7b8193970b70453239e255054aa2d60c1683af08751
Local SHA-256 render_docx.py: 7e5049d662aa4e8228b333bd95e999c7b482ba1efa55bf07eae7a0ad3a4683c8
SHA-256 LICENSE.txt: 4dd13869245e356246a5b770723247bbb80a8f07a181d1d3d873a1734297cdb9

Source hashes use UTF-8 with LF line endings (normalize CRLF at checkout before
hashing). The upstream script already used LF, so its original hash is preserved.

## Local portability changes

`LICENSE.txt` is unchanged. `render_docx.py` has only local execution-boundary
adaptations; it is no longer byte-identical to the upstream script:

- Build escaped absolute profile URIs with `Path.resolve().as_uri()` instead of
  concatenating `file://` with a native Windows path (which can trigger a
  LibreOffice bootstrap error).
- Use the package's `templates.office_tools` discovery and bounded process
  runner, shared with primary PDF export: PATH installations take precedence,
  Windows prefers `soffice.com`, and standard installation paths are fallbacks.
  Pass absolute executable paths without modifying PATH or selecting an office
  installation's bundled Python. Windows starts the launcher suspended, assigns
  it to a private Job Object with `KILL_ON_JOB_CLOSE`, then resumes its initial
  thread. Every exit path terminates and closes that job before reaping the
  launcher, including setup failures and descendants whose launcher has exited.
  POSIX isolates a new process group and kills the group on every exit path.
- Accept an optional conversion environment for in-process reference rendering,
  avoiding an outer Python timeout that can orphan LibreOffice children.
- Bound conversion calls to 30 seconds, Poppler metadata to 15 seconds and
  rasterization to 30 seconds. Report OS/subprocess errors through the CLI's
  nonzero exit status; verify both required Poppler tools.

The script produces PDF reference images, not direct DOCX-reader visual review.
Its optional ODT fallback is retained for previews only and is not strict
DOCX/PDF equivalence evidence. Publication uses the package's bounded direct
LibreOffice export and refuses failed/stale exports; it never uses this fallback.
