# MonkeyResume

[简体中文](README.zh-CN.md)

> **Evidence-grounded resume tailoring.** Zero hallucinations, traceable claims, and verified single-page A4 DOCX delivery with optional matching PDF.

MonkeyResume turns your real experience into role-specific resumes without inventing skills, metrics, or titles. Every claim links to an evidence ledger, and publication is blocked if any bullet cannot be traced.

---

## Resume Generation Records

Successful generations, including DOCX-only delivery, automatically retain independent historical QA PDFs. Open
`$USER_WORKSPACE/resume_history/index.html` to find the company, role, optional
posting URL, generation time, and the exact historical resume. Pass known target
metadata with `--company`, `--job-title`, and `--job-url`; unknown values may be
omitted. Always pass the same external `--workspace` used for your evidence.

For generation examples, URL backfill, and directory recovery, see
[Resume Generation Records](references/resume-generation-records.md).

## Quick Start (~2 minutes)

### 1. Clone the repository

```bash
git clone https://github.com/Zhangyinglun/monkey-resume.git ~/Projects/monkey-resume
cd ~/Projects/monkey-resume
```

### 2. Install dependencies (Python 3.9+)

```bash
python3 -m pip install -r requirements.txt
```

### 3. Register as an Agent Skill

```bash
mkdir -p ~/.agents/skills
ln -s ~/Projects/monkey-resume ~/.agents/skills/monkey-resume
```

### 4. Run with your AI agent

Provide your resume and job description (JD), then prompt:

```text
Use $monkey-resume to tailor my resume for this role and generate a verified single-page DOCX.
```

---

## Key Features

- **No Hallucinations**: Only writes from verified facts. Unsupported JD points remain visible gaps.
- **Full Traceability**: Every resume bullet links directly to a verified Claim ID.
- **JD Alignment**: Maps job requirements into direct, transferable, or missing capabilities.
- **Physical Geometry Gate**: Guarantees a clean single-page A4 layout without overflow.
- **Safe Rollback**: QA-rejected candidates land in `rejected/`; handled history/publication failures preserve your last accepted DOCX/PDF.

---

## 5-Step Pipeline

```text
[1. Snapshot] ➔ [2. Ledger] ➔ [3. Analyze JD] ➔ [4. Plan & Draft] ➔ [5. Audit & Publish]
```

1. **Snapshot**: Ingest base resume (`.pdf`, `.docx`, `.md`, `.txt`) into an immutable snapshot.
2. **Ledger**: Extract experience into reusable, entity-bound Atomic Claims.
3. **Analyze JD**: Match requirements against candidate evidence; ask targeted clarification only.
4. **Plan & Draft**: Select evidence into a Projection Plan and draft recruiter-ready bullets.
5. **Audit & Publish**: Audit facts, render DOCX with a same-source QA PDF, and verify 1-page A4 geometry before publication.

---

## Workspace Architecture

Your personal resume data and generated DOCX/PDF files stay isolated in the candidate workspace.
The CLI defaults to `~/Documents/MonkeyResume`; pass `--workspace` to override it:

```text
USER_WORKSPACE/
├── cache/
│   ├── base-resume.json          # Immutable source snapshot
│   ├── candidate-evidence.json   # Multi-JD candidate evidence ledger
│   ├── jd-analysis.json          # JD requirement mapping
│   ├── resume-working.json       # Current tailored resume data
│   └── resume-changes.json       # Field-level tailoring changelog
└── resume_output/
    ├── Candidate_Resume_Role.docx # Verified editable DOCX
    └── rejected/                 # Failed runs (auto-isolated)
```

---

## Development Checks

Run the complete test suite:

```bash
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

---

## License

[MIT](LICENSE)


## DOCX-first output / 默认 DOCX

默认交付可编辑 DOCX，保留 `--format pdf` 和 `--format both`。PDF 由同一份 DOCX 经 LibreOffice 转换，不维护两套排版。旧命令显式指定 `.pdf` 仍输出 PDF。需安装 LibreOffice、Poppler 和 Carlito 字体。

Default output is editable DOCX. PDF is exported from the exact same document. See [output and QA guide](references/docx-output.md) for dependencies, compatibility, the pinned Apache-2.0 OpenAI public QA tool, and renderer/font limitations.
