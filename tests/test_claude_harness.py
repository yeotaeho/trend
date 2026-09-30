# .claude 훅·업무 등록 스크립트 판정 테스트 — 가드 차단·라우터 목록·교훈 게이트·계획 검증
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"


def run_hook(name: str, payload: dict, cwd: Path = ROOT, tmp: Path | None = None) -> str:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    if tmp is not None:
        env.update(TMP=str(tmp), TEMP=str(tmp), TMPDIR=str(tmp))
    r = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps({"cwd": str(cwd), **payload}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def decision(out: str) -> str | None:
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    return tmp_path


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_guard_denies_commit_with_staged_env(repo: Path) -> None:
    (repo / ".env").write_text("X=1")
    subprocess.run(["git", "-C", str(repo), "add", ".env"], check=True)
    assert decision(run_hook("guard.py", bash('git commit -m "x"'), cwd=repo)) == "deny"


def test_guard_allows_env_example(repo: Path) -> None:
    (repo / ".env.example").write_text("X=")
    subprocess.run(["git", "-C", str(repo), "add", ".env.example"], check=True)
    assert decision(run_hook("guard.py", bash('git commit -m "x"'), cwd=repo)) is None


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git push", "deny"),  # main 브랜치에서 기본 원격으로
        ("git push origin HEAD:main", "deny"),
        ("git status && git push -u origin main", "deny"),
        ("git push origin feat/x", None),
        ("git push trend2 HEAD:main", None),  # 복제 레포는 배포 잡이 가드돼 있다
        ('echo "git push origin main"', None),  # 실행이 아니라 문자열
    ],
)
def test_guard_push_to_origin_main(repo: Path, command: str, expected: str | None) -> None:
    assert decision(run_hook("guard.py", bash(command), cwd=repo)) == expected


@pytest.mark.parametrize("form", ['git -C "{main}" push', 'cd "{main}" && git push'])
def test_guard_push_uses_the_folder_git_runs_in(repo: Path, tmp_path: Path, form: str) -> None:
    # 기능 브랜치 폴더에서 main 워크트리를 가리켜 push 해도 막는다 (Codex 리뷰 P1)
    feature = tmp_path / "feature"
    subprocess.run(["git", "init", "-q", "-b", "feat/x", str(feature)], check=True)
    command = form.format(main=repo.as_posix())
    assert decision(run_hook("guard.py", bash(command), cwd=feature)) == "deny"


@pytest.mark.parametrize(
    ("rel", "expected"),
    [("Dockerfile", "ask"), (".github/workflows/ci.yml", "ask"), ("app/main.py", None)],
)
def test_guard_asks_before_deploy_file_edit(rel: str, expected: str | None) -> None:
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / rel)}}
    assert decision(run_hook("guard.py", payload)) == expected


def test_router_full_list_then_one_line(tmp_path: Path) -> None:
    first = run_hook("prompt_router.py", {"session_id": "t1"}, tmp=tmp_path)
    assert "[작업 라우터]" in first
    assert "lesson-capture" in first and "work-intake" in first
    assert "`sources`" in first  # paths 와 description 이 있는 규칙
    assert "`lessons`" not in first  # 항상 로드되는 규칙은 목록에 넣지 않는다
    second = run_hook("prompt_router.py", {"session_id": "t1"}, tmp=tmp_path)
    assert len(second.splitlines()) == 1


def test_router_frontmatter_is_valid_yaml() -> None:
    # 설명이 따옴표로 시작하는 등 YAML 이 깨지면 Claude Code 가 스킬 설명을 못 읽는다
    files = [
        *(ROOT / ".claude" / "rules").glob("*.md"),
        *(ROOT / ".claude" / "skills").glob("*/SKILL.md"),
    ]
    for p in files:
        m = re.match(r"---\r?\n(.*?)\r?\n---", p.read_text(encoding="utf-8"), re.S)
        if m is None:
            continue  # 항상 로드되는 규칙은 머리말이 없다
        meta = yaml.safe_load(m.group(1))
        assert isinstance(meta.get("description"), str) and meta["description"], p


@pytest.mark.parametrize(
    ("payload", "blocks"),
    [
        ({"last_assistant_message": "커밋 abc1234 을 남겼다."}, True),
        ({"last_assistant_message": "커밋 abc1234. 기록할 교훈 없음."}, False),
        ({"last_assistant_message": "설명만 했다."}, False),
        ({"last_assistant_message": "커밋 abc1234", "stop_hook_active": True}, False),
    ],
)
def test_lesson_gate(payload: dict, blocks: bool) -> None:
    out = run_hook("lesson_gate.py", payload)
    assert (json.loads(out)["decision"] == "block") if blocks else out == ""


def load_tasks_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(
        "github_tasks", ROOT / ".claude" / "scripts" / "github_tasks.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plan_validation() -> None:
    tasks = load_tasks_module()
    good = {
        "project": "소스 확장 2차",
        "tasks": [
            {"key": "t1", "title": "조사", "kind": "조사", "area": "수집", "done_when": ["표"]},
            {"key": "t2", "title": "구현", "done_when": ["pytest 통과"], "depends_on": ["t1"]},
        ],
    }
    assert tasks.validate(good) == []
    bad = json.loads(json.dumps(good))
    bad["tasks"][1].update(area="프론트", depends_on=["t9"], done_when=[])
    bad["summary"] = "ANTHROPIC key sk-ant-abcdefghijklmnopqrstuvwx"
    errs = " ".join(tasks.validate(bad))
    assert "area" in errs and "t9" in errs and "done_when" in errs and "비밀값" in errs
