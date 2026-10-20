# Installation

Use Python 3.11 or newer and a project-local virtual environment:

### Linux / macOS (Bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
mkdir -p ~/.agents/skills
ln -s /absolute/path/to/monkey-resume ~/.agents/skills/monkey-resume
```

### Windows (PowerShell, no WSL required)

From the repository directory:

```powershell
$env:PYTHONUTF8 = '1'
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.agents\skills\monkey-resume" -Target (Get-Location).Path
```

Create the junction only when that destination is unused. A directory junction
does not require symlink privileges. If your host uses another Skill directory,
use its documented location instead. Keep candidate workspaces outside this link
and outside the repository.

Use the environment's absolute Python path rather than relying on activation,
the Windows Store `python3` alias, or LibreOffice's bundled Python. Bash examples
use `$NAME` and backslash line continuations; translate them to PowerShell local
variables and one-line commands (or PowerShell backticks), for example:

```powershell
$MONKEY_RESUME_DIR = (Get-Location).Path
$env:PYTHONUTF8 = '1'
$USER_WORKSPACE = Join-Path $HOME 'Documents\MonkeyResume'
& "$MONKEY_RESUME_DIR\.venv\Scripts\python.exe" "$MONKEY_RESUME_DIR\scripts\evidence_ledger_manager.py" prepare --workspace "$USER_WORKSPACE" --input 'C:\Candidate Files\notes.docx'
```

Keep personal candidate data and generated output in an external workspace.
Install LibreOffice Writer, Poppler and licensed Arial separately; the current
workflow requires actual Arial and rejects rendered font substitution. See
[output and QA](../../references/docx-output.md) for rendering details.

On macOS, install LibreOffice and Poppler with `brew install --cask libreoffice`
and `brew install poppler`. A standard `/Applications/LibreOffice.app` install is
discovered even when `soffice` is not on PATH. Arial is discovered in system and
user font directories; missing or substituted Arial still blocks rendering.
POSIX workspace paths are canonicalized before cache checks, including macOS's
`/var` system alias. Cache symlinks and a symlink at the workspace itself remain
rejected.

On Windows, install LibreOffice Writer normally. The renderer detects standard
Program Files installations and uses the console launcher `soffice.com`; custom
installations must expose it on PATH. Add Poppler's `bin` directory (containing
`pdftoppm.exe` and `pdfinfo.exe`) to PATH. Windows' installed Arial is discovered
in system and per-user font directories. Avoid prepending LibreOffice's program
directory to PATH: it can select LibreOffice's Python instead of your environment.

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

Windows, without activating scripts or changing execution policy:

```powershell
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\skills-ref.exe validate (Get-Location).Path
& .\.venv\Scripts\python.exe -m ruff check scripts templates tests
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers cross-process workspace exclusion, failed-publication cleanup,
and real DOCX/PDF/reference rendering with paths containing spaces and Unicode.
Symlink-specific tests require symlink privileges on Windows (Developer Mode or
an elevated process); junction protection is tested without those privileges.

`requirements-dev.txt` pins the Skill validator. Rendering integration tests
report an explicit environment-dependent skip if Arial or renderer tools are
unavailable. A skipped render is unavailable coverage, not a passing Arial result.
Windows/macOS CI sets `MONKEY_RESUME_REQUIRE_RENDERING=1`: missing LibreOffice, Poppler
or Arial fails the suite instead of skipping real rendering. Set the same
environment variable locally when complete rendering coverage is required.
