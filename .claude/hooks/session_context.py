# SessionStart 훅 — 브랜치·뒤처짐·미커밋 파일을 알리고 압축·재개 뒤엔 인수인계를 되돌려 넣는다
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

HANDOFF_MAX_LINES = 60
RECENT_HOURS = 48

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
cwd = data.get("cwd") or "."
source = data.get("source", "")
sid = re.sub(r"[^A-Za-z0-9_-]", "", data.get("session_id", ""))
root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
handoff_dir = root / ".claude" / "handoff"

# 작업 라우터가 이 뒤 첫 요청에 전체 목록을 다시 넣도록 카운터를 지운다
if sid:
    (Path(tempfile.gettempdir()) / "claude-trend-router" / f"{sid}.txt").unlink(missing_ok=True)


def git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=5
        )
        return out.stdout.strip()
    except Exception:
        return ""


branch = git("branch", "--show-current") or "(detached)"
dirty = [line for line in git("status", "--short").splitlines() if line.strip()]
trees = [line for line in git("worktree", "list").splitlines() if line.strip()]
ahead_behind = git("rev-list", "--left-right", "--count", "HEAD...@{u}").split()

lines = [f"[세션 시작] 현재 브랜치 `{branch}`."]
if source != "compact":  # 압축 직후는 같은 세션이 이어지는 중이라 이미 봤다
    lines.append(
        "- 이 세션의 첫 업무(수정·조사·배포 같은 작업) 요청을 받으면 손대기 전에 "
        "`python3 .claude/scripts/github_tasks.py board` 로 보드 현황을 보고, "
        "요청과 겹치는 이슈가 있으면 번호로 짚는다. 단순 질문에는 하지 않는다."
    )
if branch == "main":
    lines.append("- main 에서 바로 고치지 않는다. main 머지는 곧 운영 배포다. 기능 브랜치를 딴다.")
if len(ahead_behind) == 2 and ahead_behind[1] != "0":
    lines.append(
        f"- 이 브랜치가 upstream 보다 {ahead_behind[1]}커밋 뒤다(마지막 fetch 기준). "
        "배포·머지 상태는 `git fetch` 뒤 origin 기준으로 판단한다."
    )
if dirty:
    shown = ", ".join(line[3:] for line in dirty[:8])
    more = f" 외 {len(dirty) - 8}개" if len(dirty) > 8 else ""
    lines.append(
        f"- 미커밋 파일 {len(dirty)}개: {shown}{more}. 내가 만든 변경이 아니면 스테이징하지 않는다."
    )
if len(trees) > 1:
    lines.append("- worktree: " + " | ".join(" ".join(t.split()[::2]) for t in trees))

own = handoff_dir / f"{sid}.md" if sid else None
if source in ("compact", "resume") and own and own.exists():
    body = own.read_text(encoding="utf-8").splitlines()[:HANDOFF_MAX_LINES]
    lines.append(
        "- 압축·재개 직후다. 경로별 규칙은 사라졌으니 작업 중인 파일을 다시 Read 한다. "
        "아래는 압축 직전에 저장한 인수인계다."
    )
    lines += ["", *body]
elif source == "compact":
    lines.append(
        "- 압축 직후다. 경로별 규칙(.claude/rules 의 paths)은 사라졌으니 "
        "작업 중인 파일을 다시 Read 해 규칙을 되살린다."
    )
elif handoff_dir.is_dir():
    cutoff = time.time() - RECENT_HOURS * 3600
    recent = sorted(
        (p for p in handoff_dir.glob("*.md") if p.stem != sid and p.stat().st_mtime > cutoff),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if recent:
        p = recent[0]
        text = p.read_text(encoding="utf-8").splitlines()
        head = next((line for line in text if "브랜치" in line), "")
        when = datetime.fromtimestamp(p.stat().st_mtime)
        lines.append(
            f"- 최근 인수인계 {when:%m-%d %H:%M}: `{p}` {head.strip('- ')}. "
            "이어서 하는 작업이면 먼저 읽는다."
        )
print("\n".join(lines))
