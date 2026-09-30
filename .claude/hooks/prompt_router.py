# UserPromptSubmit 훅 — 규칙·스킬의 "언제 쓰는가" 를 모아 주입하고 고르는 판단은 Claude 에 맡긴다
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

FULL_EVERY = 10  # 이 횟수마다(첫 요청 포함) 전체 목록, 그 사이엔 한 줄 알림
STATE_DIR = Path(tempfile.gettempdir()) / "claude-trend-router"


def frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"(\w+):\s*(.*)", line)  # paths: 처럼 값이 다음 줄에 오는 키도 잡는다
        if kv:
            fields[kv.group(1)] = kv.group(2).strip()
    return fields


def catalog(root: Path) -> list:
    """(종류, 이름, 언제, 읽는 법) 목록.

    paths 가 있는 규칙과 스킬만 담는다. 항상 로드되는 규칙은 이미 컨텍스트에 있다.
    """
    items = []
    for p in sorted((root / "rules").glob("*.md")):
        fm = frontmatter(p)
        if "description" in fm and "paths" in fm:
            items.append(("규칙", p.stem, fm["description"], f"Read .claude/rules/{p.name}"))
    for p in sorted((root / "skills").glob("*/SKILL.md")):
        fm = frontmatter(p)
        if "description" in fm:
            name = fm.get("name", p.parent.name)
            items.append(("스킬", name, fm["description"], f"Skill {name}"))
    return items


def bump(session_id: str) -> int:
    """이 세션에서 몇 번째 요청인지(0부터). 세션 id 가 없으면 늘 0."""
    if not session_id:
        return 0
    STATE_DIR.mkdir(exist_ok=True)
    f = STATE_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '', session_id)}.txt"
    try:
        n = int(f.read_text())
    except (OSError, ValueError):
        n = -1
    n += 1
    f.write_text(str(n))
    return n


try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".") / ".claude"
items = catalog(root)
if not items:
    sys.exit(0)

n = bump(data.get("session_id", ""))
if n % FULL_EVERY == 0:
    lines = [
        "[작업 라우터] 이 프로젝트의 작업별 규칙·스킬 목록이다. "
        "키워드가 아니라 요청이 실제로 하려는 일과 '언제' 설명을 대조해 해당하는 것을 고른다.",
        "고른 것은 손대기 전에 '읽는 법' 대로 먼저 읽고, "
        "답변 첫 줄에 `[적용: 이름, ...]` 로 밝힌다. 해당이 없으면 밝히지 않는다. "
        "이번 세션에 이미 읽은 것은 다시 읽지 않는다.",
    ]
    lines += [
        f"- {kind} `{name}` — 언제: {when} → 읽는 법: {how}" for kind, name, when, how in items
    ]
    lines.append(
        "- 고른 항목의 대기 교훈은 .claude/lessons/BANK.md 의 "
        "'목적지' 열에서 그 이름으로 grep 한다."
    )
else:
    names = " · ".join(name for _, name, _, _ in items)
    lines = [f"[작업 라우터] 요청 의도가 앞과 달라졌으면 작업 목록과 다시 대조한다: {names}"]
print("\n".join(lines))
