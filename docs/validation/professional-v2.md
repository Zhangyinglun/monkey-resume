# Professional-v2 style implementation

## Scope and baseline

The new managed worktree starts at feb989a with the calling checkout's existing
uncommitted changes copied in as its baseline. Those include Summary removal and
writing-rule refinements; they are not new style work. The source checkout is not
modified. No candidate cache, accepted output or shared Skill link is replaced.

This change adds a named professional-v2 default and an explicit legacy-v1 option,
retaining the DOCX -> LibreOffice PDF path, A4 and one-page publication contract.
Letter, two-page output and industry-specific visual templates are deferred.

## Behavior

- Versioned profiles resolve tokens, font, heading labels, alignment and defaults.
- V2 uses black ink, 19 pt name, 12 pt sections and 11 pt body; employer boundaries
  gain spacing. Text uses half-point Word sizes, checked before render.
- V2 auto-fit preserves caller margins and passing first renders. It reduces
  spacing before font size; all text remains >=10.5 pt and margins >=12.7 mm.
  Tight caller spacing is clamped to its floor rather than eliminating font trials.
- Compact resolves per style. Content is never changed by layout tuning.
- Candidate records bind the final style/tokens/layout/font sizes and available
  rendering environment/font file hashes. Publish reruns QA with the frozen floor.
- Existing candidates without style metadata retain their previous QA threshold.

## Validation evidence

Run the repository metadata validator, Ruff, unittest suite and git diff check.
`preview_resume_styles.py` uses wholly fictional reusable data and writes outside
the package. Its comparison.json records artifact hashes, selected styles,
physical QA, page count and independent DOCX/PDF preview pixel comparison.
Inspect the actual images as well; extraction/pixel equality does not certify
factual accuracy or ATS behavior. Sample documents are design previews only,
not independently evidence-reviewed Accepted Resumes.

Behavioral tests cover legacy rendering defaults, new black/left-aligned text,
invalid overrides before file creation, compact mode, caller margins, bounded
search including tight spacing, non-fit results, frozen final parameters and
publish-time font thresholds. Existing tests continue to verify accepted-output
rollback and independent rendering.

## Observed local run

- 132 unit/integration tests passed, including actual LibreOffice rendering.
- Ruff, absolute-path skills-ref validation and git diff --check passed.
- Both final synthetic previews: one A4 page, physical QA PASS and independent
  DOCX/PDF page pixels identical with LibreOffice 26.8.1.1 and installed Carlito.
- Visual inspection found no clipping; final bullet line fills were 68.4%-85.7%
  for legacy-v1 and 81.9%-93.0% for professional-v2.
- An actually overflowing 17-bullet stress fixture fit in four bounded trials,
  retaining 11 pt text and unchanged content. Long company/contact fields also
  passed one-page QA with all bullets preserved and two hyperlink annotations.
- Independent code review identified spacing/line-height floor search gaps;
  clamping and boundary behavior coverage were added.

These observations apply to this macOS run only; they do not certify all Word
readers, ATS systems or the factual content of any real resume.
