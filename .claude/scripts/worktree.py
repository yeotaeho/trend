# 작업 폴더 준비 — git 이 무시해 worktree 에 따라오지 않는 파일(.env·로컬 훅 설정)을 원본에서 채운다
"""사용법

  python3 .claude/scripts/worktree.py link

Orca 가 작업 폴더를 만들면 orca.yaml 의 setup 이 부른다(ORCA_ROOT_PATH·ORCA_WORKTREE_PATH).
다른 방법으로 만든 worktree 는 그 폴더에서 손으로 돌린다. 이때 원본은 git 의 첫 worktree 다.

작업 폴더에 이미 있는 파일은 덮어쓰지 않는다. 복사라서 원본을 고친 내용은 따라오지 않는다.
.claude/ 와 CLAUDE.md 는 git 이 추적하니 브랜치 판을 그대로 쓴다. 원본에 junction 으로 묶으면
git 이 junction 을 보통 폴더로 따라가 원본 체크아웃의 내용을 이 브랜치의 수정으로 본다(10-16 실험).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

LOCAL_FILES = (".env", ".claude/settings.local.json", "mobile/env/prod.json")


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return r.stdout.strip()


def main() -> None:
    if sys.argv[1:] != ["link"]:
        sys.exit(__doc__)
    env_here, env_root = os.environ.get("ORCA_WORKTREE_PATH"), os.environ.get("ORCA_ROOT_PATH")
    here = Path(env_here or git(Path.cwd(), "rev-parse", "--show-toplevel"))
    first = git(here, "worktree", "list", "--porcelain").splitlines()[0]
    root = Path(env_root or first.removeprefix("worktree "))
    for rel in LOCAL_FILES:
        src, dst = root / rel, here / rel
        if src.is_file() and not dst.exists():  # 원본에서 돌리면 src 와 dst 가 같아 건너뛴다
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"복사 {rel}")


if __name__ == "__main__":
    main()
