# 为简历交付增加基于招聘者实践的独立 Recruiter Review

## Problem Statement

候选人拿到通过事实审计、内容检查和 PDF QA 的简历后，仍不知道招聘者能否迅速理解自己的定位，以及是否能从最终简历中找到符合目标 JD 的证据。关键词出现、内部账本有证据和招聘者实际看得见证据，是三个不同的问题。

当前质量报告主要汇总已有 JD Capability 分析和程序检查。负责规划、写作的同一 agent 知道隐藏背景，容易替最终文档补全没有写出的信息。仅增加“扮演 recruiter”提示词也不够：研究演练中，独立模型曾把“工作流跨多个服务”直接判成完整的分布式服务开发经验。

用户需要在每次简历任务结束前，得到一份按真实招聘从业者流程执行、有可定位依据、能保留不确定性的独立审阅意见，并据此改善表达或了解差距。

## Solution

在现有程序 QA 和全页视觉检查完成后、向用户交付前，增加默认尝试执行的 Recruiter Review。宿主使用独立上下文 subagent，按“理解岗位问题 → 快速印象 → 完整证据核对 → 疑点复核 → 模拟初筛分流”的流程审阅。

reviewer 首先只获得原始 JD 和最终简历的可见材料。它不读取 Candidate Evidence Ledger、写作理由或作者此前的评级。第一阶段结果先返回并冻结，第二阶段再进行完整核对。最终输出逐项证据、Yes / Maybe / No 的模拟初筛意见，以及最多三条高价值建议。

首版是交付前的建议性审阅，不改变 Accepted Resume 的现有发布事务。审阅是否完成与候选人是否匹配分开表达：低匹配仍可交付；不可用、文字降级、失败或过期不得伪装成已通过。现有事实、内容和 PDF 门禁继续生效。

## User Stories

1. As a candidate, I want an independent reading before handoff, so that I can understand how my resume presents my fit without the writer filling in hidden context.
2. As a candidate, I want the reviewer to follow documented recruiter practices, so that feedback is grounded in a repeatable process rather than an improvised persona.
3. As a candidate, I want the reviewer to identify the problem the role is hiring for, so that my achievements are evaluated against the actual job.
4. As a candidate, I want required qualifications, preferred qualifications, responsibilities, and unclear wording separated, so that preferences do not become invented rejection criteria.
5. As a candidate, I want alternative qualifications preserved, so that Java or Go is not interpreted as requiring both.
6. As a candidate, I want every explicit job requirement considered, so that choosing three reading priorities does not hide other requirements.
7. As a candidate, I want my first impression recorded before detailed analysis, so that buried evidence remains visible as a presentation problem.
8. As a candidate, I want the reviewer to describe my apparent role and scope, so that I can see whether my positioning is understandable.
9. As a candidate, I want skills checked against work and project examples, so that keyword lists are not mistaken for demonstrated experience.
10. As a candidate, I want older relevant experience included in the detailed review, so that a recent role change does not erase my qualifications.
11. As a candidate, I want personal contribution distinguished from team outcomes, so that feedback does not inflate my ownership.
12. As a candidate, I want production experience distinguished from prototypes and internal tools, so that adjacent experience is described accurately.
13. As a candidate, I want related but inconclusive evidence marked partial, so that plausible architectural assumptions do not become confirmed qualifications.
14. As a candidate, I want absent information distinguished from explicit contradiction, so that silence is not treated as inability.
15. As a candidate, I want equivalent and transferable experience acknowledged without replacing explicit requirements, so that career transitions are evaluated honestly.
16. As a candidate, I want required years assessed without double-counting overlapping work, so that total tenure is not misrepresented as specialized experience.
17. As a candidate, I want each finding linked to JD and resume passages, so that I can verify and act on it.
18. As a candidate, I want matching evidence and visibility evaluated separately, so that I know whether the problem is qualification or presentation.
19. As a candidate, I want a Maybe outcome for unresolved requirements, so that uncertainty is not forced into acceptance or rejection.
20. As a candidate, I want employer prestige, school prestige, career gaps, and protected attributes excluded from implicit scoring, so that review follows job-relevant evidence.
21. As a candidate, I want at most three prioritized recommendations, so that I can focus on changes with the greatest value.
22. As a candidate, I want presentation fixes, evidence questions, and genuine Gaps separated, so that the system does not rewrite missing qualifications into my resume.
23. As a candidate, I want already confirmed evidence reused during follow-up, so that I do not answer the same questions again.
24. As a candidate, I want every accepted edit to pass the existing audit and QA workflow again, so that reviewer feedback cannot bypass factual integrity.
25. As a candidate, I want review results bound to the exact JD and resume version, so that feedback for another role or an older PDF is not presented as current.
26. As a candidate, I want bounded revision and re-review, so that the system finishes without repeatedly rewriting my resume to please a model.
27. As a candidate, I want text-only review clearly identified, so that I do not confuse content feedback with visual inspection.
28. As a candidate, I want missing subagent support, timeouts, and incomplete reviews reported honestly, so that delivery does not imply a review that never occurred.
29. As a candidate, I want self-review labeled separately from independent review, so that I can understand the strength of the feedback.
30. As a candidate, I want my resume and review artifacts kept in my external workspace, so that the reusable Skill package contains no personal application data.
31. As a candidate, I want low-match feedback without losing access to my Accepted Resume, so that I retain control over whether to apply.
32. As a maintainer, I want the existing quality-report interface to validate and display review artifacts, so that integration adds one main public testing boundary.
33. As a maintainer, I want existing callers to work without a review artifact, so that adding review support does not break current automation.
34. As a maintainer, I want model judgment evaluated separately from deterministic validation, so that mocked tests do not create false claims of recruiting accuracy.
35. As a maintainer, I want versioned review instructions and reproducible non-personal evaluation cases, so that changes to reviewer behavior can be assessed over time.

## Implementation Decisions

### 1. Scope, architecture, and domain language

- Define Recruiter Review as a reader-facing assessment of the Tailored Resume against an original JD. Define Recruiter Review Report as its version-bound result, separate from an Audit Finding and from the Candidate Evidence Ledger. Extend the domain glossary with these concepts during implementation.
- The host agent runs the reviewer. Packaged Python components validate data, fingerprints and report contracts without calling model APIs, embedding model SDKs or depending on a particular agent provider.
- Reuse the existing combined quality-report component as the public integration boundary. Add an internal review-artifact validator and formatter behind it. Avoid a second review service, daemon or independent orchestration CLI.
- Add one authoritative review protocol, referenced by the Skill workflow, execution checklist and prompt recipes. Retain source attribution and distinguish practitioner guidance from project-specific rules; do not duplicate the protocol across instructions.
- Respect the existing ADRs: preserve evidence/projection separation, candidate-answer ingestion and reuse, mandatory pre-render factual audit, and geometry-based PDF QA. Reviewer opinion never authorizes new Atomic Claims.

### 2. Entry conditions and publication semantics

- Attempt review after factual/content/programmatic PDF checks and host visual QA, before the final user handoff. Supply the same final PDF the user will receive, with stable references to its matching Tailored Resume and Tailoring Manifest.
- The current generator publishes an Accepted Resume before this host review. The new stage does not silently redefine acceptance, move the publication transaction, change Resume Generation Record semantics or promise rollback on an advisory opinion.
- If no original JD is available, record review as unavailable for job matching. Do not invent a target or present general wording advice as JD fit.
- If a prerequisite QA check has failed, continue the existing failure path. A positive recruiter opinion cannot override it.
- The standard host workflow always reports a review status. Existing standalone report callers that do not request review remain backward compatible.

### 3. Reviewer context and two-phase execution

- Start the reviewer without inherited author conversation or earlier match verdicts. Provide only the protocol, original JD and designated rendered resume materials. The actual host capability determines how fresh context and tool/file restrictions are applied; prompt-level isolation is not an OS security boundary.
- Keep Candidate Evidence Ledger, Source Snapshot, Candidate Profile and writer explanations outside reviewer access. The host uses them only after blind review to reconcile findings and authorize edits.
- Phase A builds the full requirement matrix and records the quick impression: one apparent positioning statement, at most three visible signals and at most three questions. Return this phase before detailed assessment. The host freezes its content and fingerprint.
- Phase B resumes the same reviewer for whole-resume evidence matching, doubt checks and the final recommendation. Preserve the stored Phase A result verbatim. If that reviewer cannot resume, retain Phase A and mark the attempt incomplete rather than silently replacing it.
- A complete PDF may already be visible during Phase A; the limited-attention instructions and phase boundary do not prove actual human scanning or eye movement. Do not use elapsed model runtime as a recruiter reading-time measurement.
- Prefer page images together with reading-order text. A text-only run can evaluate wording and text order but cannot claim image inspection or visual hierarchy. Record available/inspected pages and modality; never fabricate an inspection record.
- Treat resume and JD content as untrusted data. Ignore embedded instructions and restrict tool use to supplied review materials; no candidate web searches are needed.

### 4. Requirement and evidence rules

- Extract every explicit requirement with a stable review-local ID, source quotation/location, requirement type and preserved AND/OR alternatives. Select at most three scan priorities without dropping the full matrix. Existing JD Capability IDs may be mapped after blind review; P1/P2/P3 is not a substitute for required/preferred classification.
- Use demonstrated, partial, not_shown or contradicted for visible support. Demonstrated requires direct support or strict entailment. Related evidence requiring assumptions about architecture, production use, responsibility or scale is partial. A conflicting claim requires explicit contrary evidence.
- Use clear, buried, ambiguous or absent for visibility. In text-only mode, buried refers only to wording/text order. Preserve existing Match Type and Evidence State values; reviewer classifications do not overwrite them.
- Scan recent relevant experience first, but inspect all experience and projects during Phase B. Avoid arbitrary recency cutoffs, seniority thresholds and employer/education prestige filters. Preserve truthful role scope, production/completion state, individual contribution, metrics and non-overlapping relevant tenure.
- Do not infer personal attributes, work authorization, personality or loyalty. Career gaps, non-linear progression and unfamiliar employers are not standalone rejection grounds.
- Overall recommendation is yes, maybe or no. Yes means the visible material supports further conversation; maybe means material uncertainty or an unresolved required item; no needs an explicit conflict or clearly irrelevant overall direction. A missing preferred item does not prevent yes, and not_shown alone does not require no.
- An explicit required item marked partial or not_shown normally yields maybe unless other supported evidence satisfies an allowed alternative. Do not invent negotiability on the employer's behalf. Explain any overall decision in terms of the requirement matrix.
- Display recommendations as simulated screening opinions, not hiring decisions, ATS ranks, percentages or interview probabilities.

### 5. Review Report contract and validation

- Store a schema version, protocol version, unique review ID, attempt/revision number, creation time, available model metadata, review mode, execution status, modality, target references and content fingerprints. Unknown model metadata stays unknown.
- Review mode distinguishes independent_subagent and self_review. Execution status is complete, incomplete or unavailable with a reason where applicable. The validator independently reports valid, invalid or stale; these states are distinct from yes/maybe/no.
- A complete record contains the frozen Phase A, full requirement matrix, JD/resume citations, per-item support and visibility judgments, doubts, final recommendation, up to three prioritized recommendations, and review limits. Missing evidence has a reason rather than a fabricated citation.
- Bind complete reports to SHA-256 fingerprints of the original JD, final PDF, Tailored Resume and Tailoring Manifest. The host computes fingerprints from the actual inputs rather than accepting model-invented hashes. Bind extracted text/page material to that PDF as well.
- The deterministic validator checks structure, enumerations, required fields, identifiers, duplicate/missing requirement results, quote locations in supplied text, phase consistency and fingerprints. It does not claim to mechanically prove the truth or semantic entailment of all model judgments, nor that a model found every unstated nuance in the JD.
- Invalid input must not render as a valid completed review. Stale conclusions remain historical only; changing content, layout/PDF, manifest or JD invalidates reuse for the current handoff.
- Write personalized artifacts only in the external candidate workspace. Preserve distinct JD/PDF review versions rather than overwriting a global latest result. The host persists and reloads complete structured reports; the report component remains read-only. Reuse established workspace-isolation and safe-write conventions.

### 6. Combined report behavior and compatibility

- Extend the existing quality-report interface with optional review-artifact and original-JD inputs. A requested completed review also needs the corresponding PDF and existing factual-audit inputs to validate the exact target consistently.
- If review is not requested, retain existing behavior and return-code semantics. The host's standard end-to-end workflow explicitly requests a status; legacy standalone callers are not forced to create a review artifact.
- With a requested review, malformed or missing input and stale target bindings produce a clear diagnostic and exit 1, consistent with unusable report inputs. They must not be represented as a successful current review.
- A structurally valid incomplete/unavailable record is displayed with its limitation and produces the existing advisory/non-pass exit 2. This concerns report completeness, not removal or rejection of an already published Accepted Resume.
- A valid, complete report may contain yes, maybe or no without changing the exit code merely because of the fit opinion. Existing content, factual and PDF results still determine their own report outcome.
- Keep Recruiter Review distinct from deterministic findings and existing content-warning dispositions. Display the frozen first impression, evidence matrix, simulation result, top recommendations and limitations; never label the simulation a factual-audit PASS.

### 7. Feedback, bounded revision, and degradation

- Classify recommendations as presentation_fix, needs_candidate_evidence or genuine_gap. The host checks existing active claims before asking questions; only it can determine whether not_shown is merely omitted evidence or a true Gap.
- Record each disposition as applied, declined_with_reason or needs_candidate_evidence. Resolve a reviewer inference against the actual material rather than modifying facts to satisfy a rating. Any host correction is recorded alongside the original review, not silently substituted into frozen reviewer output.
- Apply changes through Projection Planning, Resume Language Optimization and deterministic build. Preserve unchanged Content Intent wording unless its intent/budget actually changes. Do not directly edit rendered PDFs.
- Allow at most one reviewer-driven consolidated content revision followed by one re-review. It consumes the remaining existing Content Fit revision budget; it does not create another three-round loop. Exhausted budget or genuine Gaps lead to a truthful handoff with remaining findings.
- After an edit, repeat factual/content/PDF checks and visual inspection, then review the new PDF. Do not reuse the old review because the wording change appears small. Subsequent candidate-requested changes start their own explicitly identified version.
- Reuse existing Clarification and Candidate Confirmation rules: no redundant question about an active confirmed claim, no second confirmation turn for an explicit answer, and no new independent question quota.
- If subagents or required inputs are unavailable, mark unavailable. Timeout/failure after work begins is incomplete. A text-only review remains labeled text_only; inability to complete visual QA remains governed by the existing visual-QA policy.
- A documented same-agent fallback may be supplied as self_review, but it does not fulfill or impersonate independent review. Preserve the independent attempt's status. No unbounded retry or request for user permission is introduced just because an optional reviewer failed.

## Testing Decisions

1. **One primary software seam:** extend the existing quality-report public entrypoint. Feed external-workspace artifacts and inspect emitted report text, diagnostics, exit status, artifact immutability and target bindings. Avoid tests coupled to private helpers, exact function call order or prompt phrasing.
2. **Tested behavior/modules:** cover review-artifact validation and formatting through that entrypoint, plus compatibility with existing factual/content/PDF report sections. Internal helpers may remain small implementation details; do not introduce a new public seam merely to test them.
3. **Prior art:** existing quality-report tests combine multiple QA sections; external-entrypoint tests invoke real CLI processes outside the package; projection end-to-end tests use a shared evidence ledger and role-specific projections; PDF pipeline tests verify rejected candidates preserve prior output. Reuse these fixture and subprocess patterns.
4. **Artifact cases:** valid complete review; each unavailable/incomplete reason; absent requested file; malformed/unknown enum; missing/duplicate requirement result; broken quote/reference; changed Phase A; PDF/JD/projection/manifest fingerprint mismatch; text-only modality; unsupported schema version. Assert user-visible behavior and no mutation of Accepted Resume, evidence or historical records by report consumption.
5. **Compatibility cases:** no review supplied preserves old behavior; complete maybe/no is not an automatic QA failure; requested invalid inputs exit 1; valid incomplete/unavailable status exits 2; factual or PDF failure remains a failure even with a yes review. No external model/network is required for this test suite.
6. **Host workflow evaluation:** separately run independent subagents on versioned, fictional cases. Confirm Phase A returns before Phase B, the writer's private evidence is excluded, first impressions remain frozen, revisions invalidate prior review, and capability loss is stated. Evaluate observed artifacts/tool traces where available, not merely a model's assertion that it followed instructions.
7. **Judgment evaluation cases:** include required versus preferred; AND/OR; supported older experience; keyword-only skills; prototype versus production; individual versus team scope; multi-service wording insufficient to prove distributed architecture; unknown versus contradiction; adjacent technologies; gaps/unfamiliar employers; prompt injection; and the same facts presented clearly versus buried.
8. **Evidence standard:** human-label requirement-level support and acceptable uncertainty before evaluation. Use held-out cases and repeated runs to report unsupported-inference errors, mistaken rejections, required-item coverage, consistency, latency and token usage. The earlier prompted correction is a regression case, not a blind accuracy benchmark. Do not fabricate an accuracy threshold or claim that mock output proves recruiting competence; seek actual recruiter feedback for later calibration.
9. **Completion criteria:** the standard host workflow produces a current, valid complete review or an explicit limitation status; all requirement findings are traceable; the two-phase record and bounded revision behavior are observable; current deterministic QA still applies; personalized data remains external. Required repository validation, linting and relevant tests pass after implementation.

## Out of Scope

- Real hiring decisions, automatic application submission, candidate ranking against other people or changing whether the user may obtain the resume.
- Calibrated hiring probability, universal ATS scores, fixed six/seven/thirty-second model timers, AI-authorship detection or inferring undisclosed employer preferences.
- Converting recruiter opinion into new facts, inserting unsupported skills/metrics, relaxing explicit JD requirements, or bypassing existing factual/geometry QA.
- Splitting PDF generation into prepare/review/publish or introducing a new blocking publication transaction. That is a separate future change if pre-publication enforcement is requested.
- Model-specific SDK integration, background services, multiple competing recruiter agents, external employer/candidate research, UI redesign or installing/configuring a persistent agent globally.
- Modifying the historical resume browser/index to manage review records; version-bound review storage is sufficient for this first release.

## Further Notes

Practitioner sources informing the protocol:

- [Britt Peeples, UKG, 2026-06-09](https://www.ukg.com/blog/life-ukg/what-recruiters-actually-scan-first-30-seconds-resume-review): locate relevant work, verify skills in experience, and identify personal outcomes. The author is identified by UKG as a Principal Talent Acquisition Partner.
- [Amy Miller, 2025-10-31, at 10:13](https://www.youtube.com/watch?v=piFVDwOsFTk&t=613s): start with the hiring problem and look for accomplishments and concrete tool use. Research used the video's automatic English transcript, not a visual review; her employer history is self-described rather than independently verified.
- [Amy Miller, minimum versus preferred qualifications, 2020-01-03](https://www.recruitinginyogapants.com/ama-friday-yall/): maintain the required/preferred distinction without importing historical ATS generalizations.
- [Gergely Orosz, hiring-manager screening chapter](https://thetechresume.com/samples/advice-for-hiring-managers): Yes/Maybe/No and independent calibration. The chapter does not expose a precise update date; older product examples and effect-size claims are not dependencies of this design.
- [Marton Trencseni, 2024-07-01](https://bytepawn.com/how-i-screen-cvs.html): evaluate relevance and outcomes, while rejecting his personal tenure, seniority and technology-ecosystem thresholds as universal rules.

The study exercise used fictional text, not a candidate PDF. Its initial model overstatement of distributed-system experience was corrected by the host, motivating the strict-entailment/partial boundary above. This establishes an implementation requirement, not evidence of predictive validity.

The specification is self-contained for an implementation agent; uncommitted local research notes are supporting context, not required remote dependencies. Existing unrelated work on Resume Generation Records must be preserved. This issue specifies implementation work; it does not assert that Recruiter Review is already active.
