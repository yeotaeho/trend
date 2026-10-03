# PostToolUse 훅 — 편집 도구가 성공을 알려도 파일이 커밋본의 절반 미만으로 줄었으면 멈춰 확인시킨다
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

MIN_LINES = 10  # 이보다 짧은 파일은 보지 않는다
SHRINK = 0.5  # 커밋본 줄 수의 이 비율 미만이면 멈춘다
STATE_DIR = Path(tempfile.gettempdir()) / "claude-trend-edit-check"

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

inp = data.get("tool_input") or {}
root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
# Edit·Write 는 file_path, Serena 편집 도구는 relative_path.
# ponytail: replace_in_files 처럼 여러 파일을 고치는 도구는 경로가 하나가 아니라 보지 않는다
raw = inp.get("file_path") or inp.get("relative_path") or ""
if not raw:
    sys.exit(0)
path = Path(raw) if Path(raw).is_absolute() else root / raw


def git(*args: str, at: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", *args], cwd=at, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )  # fmt: skip
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


# 세션 프로젝트가 아니라 파일이 든 worktree 의 커밋본과 비교한다
# (원본 세션에서 다른 worktree 파일을 고칠 때도 멈추게)
top = git("rev-parse", "--show-toplevel", at=path.parent) if path.parent.is_dir() else None
if not top:
    sys.exit(0)  # git 밖 파일이거나 폴더째 지웠다
tree = Path(top.strip())
try:
    rel = path.resolve().relative_to(tree.resolve()).as_posix()
except (ValueError, OSError):
    sys.exit(0)

before = git("show", f"HEAD:{rel}", at=tree)
if before is None:
    before = git("show", f":{rel}", at=tree)  # 아직 커밋 전이면 스테이징본과 비교한다
if before is None:
    sys.exit(0)  # 새 파일
try:
    now = path.read_text(encoding="utf-8", errors="replace")
except OSError:
    sys.exit(0)  # 지운 파일은 의도한 삭제로 본다
old_n, new_n = len(before.splitlines()), len(now.splitlines())
if old_n < MIN_LINES or new_n >= old_n * SHRINK:
    sys.exit(0)

# 같은 세션에서 한 번 확인한 파일은 다시 멈추지 않는다(의도한 큰 삭제 뒤 편집마다 막히지 않게)
sid = re.sub(r"[^A-Za-z0-9_-]", "", data.get("session_id", ""))
if sid:
    STATE_DIR.mkdir(exist_ok=True)
    seen_file = STATE_DIR / f"{sid}.txt"
    seen = set(seen_file.read_text(encoding="utf-8").splitlines()) if seen_file.exists() else set()
    key = path.resolve().as_posix()  # worktree 마다 같은 rel 이 있다
    if key in seen:
        sys.exit(0)
    seen_file.write_text("\n".join(sorted(seen | {key})), encoding="utf-8")

reason = (
    f"{rel} 이 커밋본 {old_n}줄에서 {new_n}줄로 줄었다. 도구가 성공을 알려도 결과를 확인한다. "
    f'의도한 삭제가 아니면 `git -C "{tree.as_posix()}" diff -- {rel}` 로 보고 원문으로 되돌린다. '
    "의도한 삭제면 그대로 진행한다."
)
print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
