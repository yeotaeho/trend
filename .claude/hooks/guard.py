# PreToolUse 훅 — 비밀 파일 커밋·origin main 직접 push 를 막고 배포 설정 수정은 확인한다
import json
import os
import re
import shlex
import subprocess
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

# 커밋하면 안 되는 파일. .env.example 만 예외다
SECRET_FILE = re.compile(
    r"(^|/)(\.env(\.[^/]*)?|[^/]*\.(pem|key)|secrets/.*|caddy_data/.*|\.claude/handoff/.*)$"
)
# main 머지가 곧 운영 배포라서, 배포 동작을 바꾸는 파일은 수정 전에 확인한다
DEPLOY_FILE = re.compile(r"\.github/workflows/.*|Dockerfile|docker-compose\.yml|Caddyfile")
# 명령 위치(줄 시작 또는 ; && || | ( 뒤)에서 실제로 실행되는 git <sub> — (-C 경로, 인자)
ARG = r"(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)"
GIT_CMD = r"(?:^|[;&|\n(])\s*git\s+(?:-C\s+" + ARG + r"\s+)?{sub}\b([^;&|\n)]*)"
# 같은 명령 줄에서 git 앞에 폴더를 옮기는 명령
CD = re.compile(r"(?:^|[;&|\n(])\s*(?:cd|pushd|Set-Location)\s+" + ARG)

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
inp = data.get("tool_input") or {}
cwd = data.get("cwd") or "."


def decide(kind: str, reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


def git(*args: str, at: str = cwd) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=at, capture_output=True, text=True, encoding="utf-8", timeout=5
        ).stdout.strip()
    except Exception:
        return ""


def unquote(path: str) -> str:
    path = path[1:-1] if path[:1] in "\"'" else path
    if os.name == "nt":  # Git Bash 의 /c/... 를 Windows 경로로
        path = re.sub(r"^/([A-Za-z])/", r"\1:/", path)
    return path


def git_calls(sub: str, cmd: str) -> list[tuple[str, list[str]]]:
    """명령 문자열에서 실제로 실행되는 git <sub> 마다 (실행 폴더, 뒤따르는 인자).

    실행 폴더는 cwd 에서 앞선 cd 를 순서대로(`cd -` 포함) 적용하고 -C 를 더한 곳이다.
    브랜치·스테이징은 그 폴더에서 본다.
    """
    found = []
    for m in re.finditer(GIT_CMD.format(sub=sub), cmd):
        at = prev = cwd
        for c in CD.finditer(cmd, 0, m.start()):
            target = os.path.expanduser(unquote(c.group(1)))
            prev, at = at, (prev if target == "-" else os.path.join(at, target))
        if m.group(1):
            at = os.path.join(at, os.path.expanduser(unquote(m.group(1))))
        try:
            args = shlex.split(m.group(2))
        except ValueError:
            args = m.group(2).split()
        found.append((at, args))
    return found


def pushes_origin_main(args: list[str], branch: str) -> bool:
    """git push 인자가 origin(또는 기본 원격)의 main 을 갱신하는가. 다른 원격은 통과.

    브랜치를 판정하지 못하면("" — 폴더를 잘못 풀었거나 detached) main 으로 보고 막는다.
    """
    if {"--all", "--mirror"} & set(args):
        return True
    pos = [a for a in args if not a.startswith("-")]
    remote, refspecs = (pos[0], pos[1:]) if pos else (None, [])
    if remote not in (None, "origin"):
        return False
    maybe_main = branch in ("main", "")
    if not refspecs:
        return maybe_main
    for spec in refspecs:
        dst = spec.lstrip("+").split(":")[-1].removeprefix("refs/heads/")
        if dst == "main" or (dst == "HEAD" and maybe_main):
            return True
    return False


if tool in ("Bash", "PowerShell"):
    cmd = inp.get("command", "")
    for at, _ in git_calls("commit", cmd):
        staged = git("diff", "--cached", "--name-only", at=at).splitlines()
        bad = [f for f in staged if SECRET_FILE.search(f) and not f.endswith(".env.example")]
        if bad:
            decide(
                "deny",
                f"커밋 금지 파일이 스테이징돼 있다: {', '.join(bad)}. "
                "git restore --staged <파일> 로 뺀 뒤 다시 커밋한다.",
            )
    for at, args in git_calls("push", cmd):
        if pushes_origin_main(args, git("branch", "--show-current", at=at)):
            decide(
                "deny",
                "origin main 에 직접 push 하지 않는다. main 머지는 곧 운영 배포다. "
                "기능 브랜치를 push 하고 PR 로 머지한다.",
            )

if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    path = (inp.get("file_path") or inp.get("notebook_path") or "").replace("\\", "/")
    root = (os.environ.get("CLAUDE_PROJECT_DIR") or cwd).replace("\\", "/").rstrip("/")
    rel = path[len(root) + 1 :] if path.lower().startswith(root.lower() + "/") else path
    if DEPLOY_FILE.fullmatch(rel):
        decide(
            "ask",
            f"{rel} 은 배포 동작을 바꾸는 파일이다(main 머지 = 운영 배포). "
            "이번 작업 범위에 들어 있는지 사용자에게 확인한다(CLAUDE.md 원칙 9).",
        )
