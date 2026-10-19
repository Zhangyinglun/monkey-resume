# Installation

Use Python 3.11 or newer and a project-local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
mkdir -p ~/.agents/skills
ln -s /absolute/path/to/monkey-resume ~/.agents/skills/monkey-resume
```

Keep personal candidate data and generated output in an external workspace.
Install LibreOffice Writer, Poppler and licensed Arial separately; the current
workflow requires actual Arial and rejects rendered font substitution. See
[output and QA](../../references/docx-output.md) for rendering details.

The public OpenAI visual QA script and its license are vendored with provenance;
no dependency Skill installation is required. Restart OpenCode after installing
or updating the Skill or agent instructions.

## Development validation

Run checks with the project environment active:

```bash
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

`requirements-dev.txt` pins the Skill validator. Rendering integration tests
report an explicit environment-dependent skip if Arial or renderer tools are
unavailable. A skipped render is unavailable coverage, not a passing Arial result.
