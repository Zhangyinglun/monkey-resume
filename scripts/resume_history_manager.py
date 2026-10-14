#!/usr/bin/env python3
"""Durable Resume Generation Records and an offline directory."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.resume_shared import add_workspace_argument, resolve_user_workspace  # noqa: E402


def history_path(workspace: Path) -> Path:
    workspace = resolve_user_workspace(workspace)
    root = workspace / "resume_history"
    if workspace == PROJECT_ROOT or PROJECT_ROOT in workspace.parents:
        raise ValueError("History must live outside the Skill package.")
    if root.resolve() != root:
        raise ValueError("History directory must not be a symlink.")
    return root


def validate_job_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or "\\" in value
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError("Job URL must be an absolute HTTP(S) URL without credentials or whitespace.")
    return value


def atomic_text(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def history_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError(f"History is busy: {lock}. If interrupted, remove this lock after stopping writers.") from exc
    try:
        yield
    finally:
        lock.rmdir()


def read_records(root: Path) -> list[dict[str, str]]:
    records = []
    for directory in sorted(root.glob("generation-*")):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"Invalid history directory: {directory}")
        record = json.loads((directory / "record.json").read_text(encoding="utf-8"))
        fields = {"record_id", "company", "job_title", "job_url", "generated_at"}
        if (not isinstance(record, dict) or set(record) != fields
                or not all(isinstance(value, str) for value in record.values())
                or record["record_id"] != directory.name
                or not re.fullmatch(r"generation-[0-9a-f]{32}", directory.name)):
            raise ValueError(f"Invalid Resume Generation Record: {directory}")
        validate_job_url(record["job_url"])
        pdf = directory / "resume.pdf"
        if not pdf.is_file() or pdf.is_symlink():
            raise ValueError(f"Missing or unsafe historical PDF: {pdf}")
        records.append(record)
    return sorted(records, key=lambda record: (record["generated_at"], record["record_id"]), reverse=True)


def render_directory(records: list[dict[str, str]]) -> str:
    rows = []
    for record in records:
        url = validate_job_url(record["job_url"])
        job_link = f'<a href="{escape(url, quote=True)}" rel="noreferrer">岗位链接</a>' if url else "未填写"
        record_id = escape(record["record_id"], quote=True)
        cells = [escape(record["company"] or "未填写"), escape(record["job_title"] or "未填写"),
                 job_link, f'<time>{escape(record["generated_at"])}</time>',
                 f'<a href="{record_id}/resume.pdf">历史简历 PDF</a><br><small>{record_id}</small>']
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    body = "".join(rows) or '<tr><td colspan="5">暂无简历生成记录。成功生成后会自动收录。</td></tr>'
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>简历生成记录</title><style>
body{margin:0;background:#f7f6f3;color:#2f3437;font:16px/1.6 'Helvetica Neue',sans-serif}
main{max-width:1200px;margin:auto;padding:64px 24px}h1{font-family:Georgia,serif;font-size:36px}
.table-wrap{overflow-x:auto;background:white;border:1px solid #eaeaea}
table{width:100%;border-collapse:collapse;text-align:left}th,td{padding:20px;vertical-align:top;border-bottom:1px solid #eaeaea}
th{white-space:nowrap}a{color:#1f6c9f;text-underline-offset:3px}a:focus-visible{outline:2px solid #1f6c9f;outline-offset:4px}
small,time{font-family:monospace;overflow-wrap:anywhere}small{font-size:11px}
</style></head><body><main><h1>简历生成记录</h1>
<p>每次成功生成的独立版本，按时间倒序排列。这不是投递记录。使用浏览器查找公司或岗位。</p>
<div class="table-wrap"><table><caption>已通过自动校验的历史简历</caption>
<thead><tr><th scope="col">公司</th><th scope="col">岗位名称</th><th scope="col">岗位链接</th><th scope="col">生成时间 (UTC)</th><th scope="col">简历</th></tr></thead>
<tbody>''' + body + '</tbody></table></div></main></body></html>\n'


@contextmanager
def register_generation(workspace: Path, pdf: Path, company: str, job_title: str,
                        job_url: str) -> Iterator[Path]:
    """Register only a QA-passed candidate; roll back if publication fails."""
    root = history_path(workspace)
    job_url = validate_job_url(job_url)
    with history_lock(root):
        records = read_records(root)
        record_id = "generation-" + uuid4().hex
        record = dict(record_id=record_id, company=company.strip(), job_title=job_title.strip(),
                      job_url=job_url, generated_at=datetime.now(timezone.utc).isoformat())
        directory = root / record_id
        index = root / "index.html"
        previous_index = index.read_text(encoding="utf-8") if index.exists() else None
        directory.mkdir()
        try:
            shutil.copyfile(pdf, directory / "resume.pdf")
            (directory / "resume.pdf").chmod(0o444)
            atomic_text(directory / "record.json", json.dumps(record, ensure_ascii=False, indent=2))
            atomic_text(index, render_directory([record, *records]))
            yield directory / "resume.pdf"
        except Exception:
            shutil.rmtree(directory)
            if previous_index is None:
                index.unlink(missing_ok=True)
            else:
                atomic_text(index, previous_index)
            raise


def update_job_url(workspace: Path, record_id: str, job_url: str) -> Path:
    root = history_path(workspace)
    job_url = validate_job_url(job_url)
    with history_lock(root):
        records = read_records(root)
        record = next((item for item in records if item["record_id"] == record_id), None)
        if record is None:
            raise ValueError(f"Resume Generation Record not found: {record_id}")
        path = root / record_id / "record.json"
        previous = path.read_text(encoding="utf-8")
        record["job_url"] = job_url
        try:
            atomic_text(path, json.dumps(record, ensure_ascii=False, indent=2))
            atomic_text(root / "index.html", render_directory(records))
        except Exception:
            atomic_text(path, previous)
            raise
    return root / "index.html"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["rebuild", "set-url"])
    add_workspace_argument(parser)
    parser.add_argument("--record-id")
    parser.add_argument("--job-url")
    args = parser.parse_args()
    try:
        root = history_path(args.workspace)
        if args.action == "set-url":
            if not args.record_id or args.job_url is None:
                raise ValueError("set-url requires --record-id and --job-url.")
            update_job_url(args.workspace, args.record_id, args.job_url)
        else:
            with history_lock(root):
                atomic_text(root / "index.html", render_directory(read_records(root)))
        print(root / "index.html")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
