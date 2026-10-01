# Stop 훅 — 답변이 [적용: ...] 로 밝힌 규칙·스킬을 이 세션에서 실제로 읽었는지 기록과 대조한다
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if data.get("stop_hook_active"):
    sys.exit(0)

declared_line = re.match(
    r"\[적용:\s*([^\]\n]+)\]", (data.get("last_assistant_message") or "").lstrip()
)
if not declared_line:
    sys.exit(0)
declared = [n.strip().strip("`") for n in re.split(r"[,·]", declared_line.group(1)) if n.strip()]

root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
root_posix = str(root.resolve()).replace("\\", "/").rstrip("/")


def rel_of(path: str) -> str:
    p = path.replace("\\", "/")
    return p[len(root_posix) + 1 :] if p.lower().startswith(root_posix.lower() + "/") else p


def rule_paths(name: str) -> list[str] | None:
    """규칙의 paths 패턴. 그런 규칙이 없으면 None."""
    p = root / ".claude" / "rules" / f"{name}.md"
    if not p.exists():
        return None
    fm = re.match(r"---\r?\n(.*?)\r?\n---", p.read_text(encoding="utf-8"), re.S)
    return re.findall(r'^\s*-\s*"?([^"\n]+?)"?\s*$', fm.group(1), re.M) if fm else []


# 세션 전체 기록에서 기본 Read 와 Skill 호출을 모은다.
# 경로 규칙은 기본 Read 로 그 경로 파일을 열 때만 붙으므로 Serena 읽기는 세지 않는다
reads, skills = set(), set()
transcript = data.get("transcript_path")
try:
    records = Path(transcript).read_text(encoding="utf-8").splitlines() if transcript else []
except OSError:
    records = []
for raw in records:
    try:
        rec = json.loads(raw)
    except ValueError:
        continue
    if rec.get("type") != "assistant":
        continue
    for c in (rec.get("message") or {}).get("content") or []:
        if not isinstance(c, dict) or c.get("type") != "tool_use":
            continue
        inp = c.get("input") or {}
        if c.get("name") == "Read" and inp.get("file_path"):
            reads.add(rel_of(inp["file_path"]))
        elif c.get("name") == "Skill" and inp.get("skill"):
            skills.add(str(inp["skill"]).split(":")[-1])

missing, unknown = [], []
for name in declared:
    patterns = rule_paths(name)
    if patterns is not None:
        ok = f".claude/rules/{name}.md" in reads or any(
            fnmatch.fnmatch(r, pat) for r in reads for pat in patterns
        )
    elif (root / ".claude" / "skills" / name / "SKILL.md").exists():
        ok = name in skills or f".claude/skills/{name}/SKILL.md" in reads
    else:
        unknown.append(name)
        continue
    if not ok:
        missing.append(name)

if not missing and not unknown:
    sys.exit(0)
problems = []
if missing:
    problems.append(
        f"{', '.join(missing)} 를 이 세션에서 읽지 않았다(규칙은 Read, 스킬은 Skill 로 읽는다)"
    )
if unknown:
    problems.append(f"{', '.join(unknown)} 는 작업 라우터 목록에 없는 이름이다")
reason = (
    f"답변 첫 줄이 [적용: {declared_line.group(1).strip()}] 를 밝혔지만 {' · '.join(problems)}. "
    "선언한 것을 실제로 읽고 답을 다시 확인한다. 해당이 없으면 선언을 고친다."
)
print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
