# PreCompact 훅 — 압축 직전 요청·고친 파일·실패·커밋을 인수인계로 남긴다(Continuous-Claude 차용)
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

KEEP_DAYS = 14
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        )
    return ""


def parse(transcript: Path):
    requests, edits, failures, last_answer = [], Counter(), [], ""
    pending = {}  # tool_use_id -> 한 줄 설명
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except OSError:
        return requests, edits, failures, last_answer
    for raw in lines:
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if rec.get("type") == "user":
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                        body = c.get("content")
                        body = text_of(body) if not isinstance(body, str) else body
                        failures.append(
                            f"{pending.get(c.get('tool_use_id'), '도구')} → {body.strip()[:200]}"
                        )
            txt = text_of(content).strip()
            if txt and not txt.startswith("<") and not rec.get("isMeta"):
                requests.append(txt)
        elif rec.get("type") == "assistant" and isinstance(content, list):
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text", "").strip():
                    last_answer = c["text"]
                elif c.get("type") == "tool_use":
                    name, inp = c.get("name", ""), c.get("input") or {}
                    if name in EDIT_TOOLS and inp.get("file_path"):
                        edits[inp["file_path"]] += 1
                    brief = (
                        inp.get("description") or inp.get("command") or inp.get("file_path") or ""
                    )
                    pending[c.get("id")] = f"{name} {str(brief)[:100]}".strip()
    return requests, edits, failures, last_answer


def git(cwd: str, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=5
        ).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    sid = data.get("session_id") or "unknown"
    cwd = data.get("cwd") or os.getcwd()
    tpath = data.get("transcript_path")
    if not tpath:
        return
    requests, edits, failures, last_answer = parse(Path(tpath))

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    out_dir = root / ".claude" / "handoff"
    out_dir.mkdir(parents=True, exist_ok=True)

    branch = git(cwd, "branch", "--show-current") or "(detached)"
    status = git(cwd, "status", "--short").splitlines()
    commits = git(cwd, "log", "--oneline", "-5").splitlines()

    lines = [
        "# 인수인계 — 압축 직전 자동 저장",
        "",
        f"- 세션 `{sid}` · {datetime.now():%Y-%m-%d %H:%M} · 압축 방식 {data.get('trigger', '?')}",
        f"- 작업 폴더 `{cwd}` · 브랜치 `{branch}`",
        "",
        "## 사용자 요청 (최근 5개, 오래된 순)",
        *[f"{i}. {r[:300].replace(chr(10), ' ')}" for i, r in enumerate(requests[-5:], 1)],
        "",
        "## 이 세션에서 고친 파일",
        *([f"- `{p}` ({n}회)" for p, n in edits.most_common(15)] or ["- 없음"]),
        "",
        "## 미커밋 파일",
        *([f"- `{s}`" for s in status[:15]] or ["- 없음"]),
        "",
        "## 최근 커밋 (이 브랜치)",
        *([f"- {c}" for c in commits] or ["- 없음"]),
    ]
    if failures:
        lines += ["", "## 최근 실패 (마지막 5개)", *[f"- {f}" for f in failures[-5:]]]
    if last_answer:
        lines += ["", "## 마지막 답변 요지", last_answer.strip()[:600]]
    (out_dir / f"{sid}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    cutoff = time.time() - KEEP_DAYS * 86400
    for old in out_dir.glob("*.md"):
        if old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
