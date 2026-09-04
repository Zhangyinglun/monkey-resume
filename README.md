# MonkeyResume

[简体中文](README.zh-CN.md)

> **Evidence-grounded resume tailoring.** Zero hallucinations, traceable claims, and verified single-page A4 PDF delivery.

MonkeyResume turns your real experience into role-specific resumes without inventing skills, metrics, or titles. Every claim links to an evidence ledger, and publication is blocked if any bullet cannot be traced.

---

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
Use $monkey-resume to tailor my resume for this role and generate a verified single-page PDF.
```

---

## Key Features

- **No Hallucinations**: Only writes from verified facts. Unsupported JD points remain visible gaps.
- **Full Traceability**: Every resume bullet links directly to a verified Claim ID.
- **JD Alignment**: Maps job requirements into direct, transferable, or missing capabilities.
- **Physical Geometry Gate**: Guarantees a clean single-page A4 layout without overflow.
- **Safe Rollback**: Failed candidate builds land in `rejected/`—your last accepted PDF is protected.

---

## 5-Step Pipeline

```text
[1. Snapshot] ➔ [2. Ledger] ➔ [3. Analyze JD] ➔ [4. Plan & Draft] ➔ [5. Audit & Publish]
```

1. **Snapshot**: Ingest base resume (`.pdf`, `.docx`, `.md`, `.txt`) into an immutable snapshot.
2. **Ledger**: Extract experience into reusable, entity-bound Atomic Claims.
3. **Analyze JD**: Match requirements against candidate evidence; ask targeted clarification only.
4. **Plan & Draft**: Select evidence into a Projection Plan and draft recruiter-ready bullets.
5. **Audit & Publish**: Run factual integrity audit, render PDF, and verify 1-page A4 geometry.

---

## Workspace Architecture

Your personal resume data and generated PDFs stay isolated in the candidate workspace.
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
    ├── Candidate_Resume_Role.pdf # Verified published PDF
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
