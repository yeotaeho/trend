# GitHub 업무 등록 — 업무 계획(JSON)을 에픽·작업(sub-issue)·선행 관계·스프린트(마일스톤)로 올린다
"""사용법

  python3 .claude/scripts/github_tasks.py check                    gh 로그인·쓰기 권한 확인
  python3 .claude/scripts/github_tasks.py milestones               열린 스프린트(마일스톤) 목록
  python3 .claude/scripts/github_tasks.py new-milestone <제목> [YYYY-MM-DD 마감] [설명]
  python3 .claude/scripts/github_tasks.py apply <계획.json> [--dry-run]
  python3 .claude/scripts/github_tasks.py status <계획.json>

인증은 gh CLI 로그인(`gh auth login`)을 그대로 쓴다. 토큰을 따로 받지 않는다.
대상은 GITHUB_REPO(기본 yeotaeho/trend).
apply 는 만든 이슈 번호를 계획 파일의 "created" 에 즉시 적는다.
중간에 실패해도 다시 돌리면 이어서 만든다.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = os.environ.get("GITHUB_REPO", "yeotaeho/trend")

# (이름, 색) — GitHub 라벨에는 범위가 없어 "범위/이름" 을 이름 규칙으로만 쓴다
LABELS = [
    ("종류/에픽", "6f42c1"),
    ("종류/작업", "0366d6"),
    ("종류/버그", "d73a4a"),
    ("종류/조사", "fbca04"),
    ("영역/수집", "1d76db"),
    ("영역/파이프라인", "0e8a16"),
    ("영역/발송", "5319e7"),
    ("영역/DB", "006b75"),
    ("영역/API", "c5def5"),
    ("영역/앱", "f9d0c4"),
    ("영역/배포", "bfd4f2"),
    ("우선순위/높음", "b60205"),
    ("우선순위/보통", "e4e669"),
    ("우선순위/낮음", "cccccc"),
]
KINDS = {"작업", "버그", "조사"}
AREAS = {"수집", "파이프라인", "발송", "DB", "API", "앱", "배포"}
PRIORITIES = {"높음", "보통", "낮음"}

# 공개 저장소라 비밀값이 이슈에 올라가면 안 된다
SECRET = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"postgres(?:ql)?://[^\s:@/]+:[^\s@/]+@"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S{6,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def gh(*args: str, body: str | None = None) -> str:
    try:
        r = subprocess.run(
            ["gh", *args],
            input=body,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except FileNotFoundError:
        sys.exit("gh CLI 가 없다. https://cli.github.com 에서 설치한다.")
    if r.returncode != 0:
        err = (r.stderr or r.stdout).strip()
        if "auth login" in err or "not logged" in err:
            sys.exit("gh 가 로그인돼 있지 않다. 사용자가 직접 `gh auth login` 을 한 번 실행한다.")
        sys.exit(f"gh {' '.join(args[:3])} 실패: {err[:300]}")
    return r.stdout


def api(path: str, *fields: str, method: str = "GET") -> object:
    """gh api 호출. fields 는 -f/-F 인자 쌍 목록."""
    out = gh("api", "-X", method, f"repos/{REPO}{path}", *fields)
    return json.loads(out) if out.strip() else None


# ── 계획 검증 ────────────────────────────────────────────────────────────────


def validate(plan: dict) -> list[str]:
    errs = []
    if not plan.get("project"):
        errs.append("project(에픽 제목)가 없다")
    tasks = plan.get("tasks") or []
    if not tasks:
        errs.append("tasks 가 비었다")
    keys = [t.get("key") for t in tasks]
    if len(set(keys)) != len(keys) or None in keys or "epic" in keys:
        errs.append("task key 가 비었거나 겹치거나 예약어 epic 이다")
    for t in tasks:
        k = t.get("key")
        if not t.get("title"):
            errs.append(f"{k}: title 없음")
        if t.get("kind", "작업") not in KINDS:
            errs.append(f"{k}: kind 는 {sorted(KINDS)} 중 하나")
        if t.get("area", "파이프라인") not in AREAS:
            errs.append(f"{k}: area 는 {sorted(AREAS)} 중 하나")
        if t.get("priority", "보통") not in PRIORITIES:
            errs.append(f"{k}: priority 는 {sorted(PRIORITIES)} 중 하나")
        if not t.get("done_when"):
            errs.append(f"{k}: done_when(완료 기준)이 없다")
        for d in t.get("depends_on", []):
            if d not in keys:
                errs.append(f"{k}: depends_on 의 {d} 가 없는 key")
    text = json.dumps(plan, ensure_ascii=False)
    for pat in SECRET:
        if pat.search(text):
            errs.append(
                f"비밀값으로 보이는 문자열이 있다({pat.pattern[:30]}…). 공개 저장소라 올리지 않는다"
            )
    return errs


def warnings(plan: dict) -> list[str]:
    text = json.dumps(plan, ensure_ascii=False)
    return [
        f"IP 주소 {m} 가 들어 있다. 공개 저장소에 올려도 되는지 확인한다"
        for m in sorted(set(IP.findall(text)))
    ]


# ── 본문 ────────────────────────────────────────────────────────────────────


def section(title: str, items: str | list[str] | None) -> list[str]:
    if not items:
        return []
    if isinstance(items, str):
        return [f"## {title}", "", items, ""]
    return [f"## {title}", "", *[f"- {x}" for x in items], ""]


def task_body(t: dict, epic_no: int | None) -> str:
    lines = [f"상위 업무: #{epic_no}", ""] if epic_no else []
    lines += section("할 일", t.get("body"))
    lines += ["## 완료 기준", "", *[f"- [ ] {x}" for x in t["done_when"]], ""]
    lines += section("검증", t.get("verify"))
    lines += section("관련 파일", [f"`{f}`" for f in t.get("files", [])])
    lines += ["---", "Claude Code 가 업무 계획에서 등록했다."]
    return "\n".join(lines)


def epic_body(plan: dict, created: dict) -> str:
    lines = section("배경", plan.get("why")) + section("요약", plan.get("summary"))
    lines += ["## 작업", ""]
    for t in plan["tasks"]:
        no = created.get(t["key"])
        ref = f"#{no}" if no else "(미등록)"
        deps = ", ".join(f"#{created[d]}" for d in t.get("depends_on", []) if created.get(d))
        lines.append(f"- {ref} {t['title']}" + (f" — 선행 {deps}" if deps else ""))
    lines += ["", "---", "Claude Code 가 업무 계획에서 등록했다. 작업은 이 이슈의 sub-issue 다."]
    return "\n".join(lines)


# ── 명령 ────────────────────────────────────────────────────────────────────


def cmd_check() -> None:
    login = gh("api", "user", "--jq", ".login").strip()
    repo = api("")
    assert isinstance(repo, dict)
    perm = repo.get("permissions") or {}
    print(
        f"로그인 {login} · 저장소 {REPO} · 쓰기 권한 {'있음' if perm.get('push') else '없음'}"
        f" · 공개 여부 {'비공개' if repo.get('private') else '공개'}"
    )


def open_milestones() -> list[dict]:
    ms = api("/milestones?state=open&per_page=100")
    return ms if isinstance(ms, list) else []


def cmd_milestones() -> None:
    ms = open_milestones()
    if not ms:
        print("열린 스프린트(마일스톤)가 없다.")
    for m in ms:
        due = (m.get("due_on") or "")[:10] or "마감 없음"
        print(f"- {m['title']} · 마감 {due} · 열림 {m['open_issues']} / 닫힘 {m['closed_issues']}")


def cmd_new_milestone(title: str, due: str = "", desc: str = "") -> None:
    title = title.strip()
    if not title:
        sys.exit("스프린트 제목이 비었다.")
    if due and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
        sys.exit("마감일은 YYYY-MM-DD 형식이다.")
    fields = ["-f", f"title={title}", "-f", f"description={desc}"]
    if due:
        fields += ["-f", f"due_on={due}T23:59:59+09:00"]
    m = api("/milestones", *fields, method="POST")
    assert isinstance(m, dict)
    print(f"스프린트 생성: {m['title']} (번호 {m['number']})")


def ensure_labels() -> None:
    listed = gh("label", "list", "-R", REPO, "-L", "200").splitlines()
    have = {line.split("\t")[0] for line in listed}
    for name, color in LABELS:
        if name not in have:
            gh("label", "create", name, "-R", REPO, "--color", color)
            print(f"라벨 생성: {name}")


def issue_id(number: int) -> str:
    """sub-issue·선행 관계 API 는 이슈 번호가 아니라 내부 id 를 받는다."""
    return gh("api", f"repos/{REPO}/issues/{number}", "--jq", ".id").strip()


def cmd_apply(path: str, dry: bool) -> None:
    p = Path(path)
    plan = json.loads(p.read_text(encoding="utf-8"))
    errs = validate(plan)
    if errs:
        sys.exit("계획 검증 실패\n- " + "\n- ".join(errs))
    for w in warnings(plan):
        print(f"주의: {w}")
    created = plan.setdefault("created", {})

    if dry:
        print(f"[미리보기] {REPO} · 스프린트 {plan.get('milestone') or '없음'}")
        print(f"에픽: {plan['project']}")
        for t in plan["tasks"]:
            deps = ",".join(t.get("depends_on", [])) or "-"
            tags = "/".join(
                [t.get("kind", "작업"), t.get("area", "파이프라인"), t.get("priority", "보통")]
            )
            print(
                f"  - [{tags}] {t['key']} {t['title']} · 선행 {deps}"
                f" · 완료 기준 {len(t['done_when'])}개"
            )
        return

    milestone = plan.get("milestone")
    if milestone and milestone not in {m["title"] for m in open_milestones()}:
        sys.exit(
            f"스프린트 '{milestone}' 가 없다. "
            "사용자에게 확인하고 new-milestone 으로 만들거나 계획에서 비운다."
        )
    ensure_labels()

    def save() -> None:
        p.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def create(title: str, body: str, labels: list[str]) -> int:
        args = ["issue", "create", "-R", REPO, "--title", title, "--body-file", "-"]
        for name in labels:
            args += ["--label", name]
        if milestone:
            args += ["--milestone", milestone]
        url = gh(*args, body=body).strip().splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1])

    if not created.get("epic"):
        created["epic"] = create(plan["project"], epic_body(plan, created), ["종류/에픽"])
        save()
        print(f"에픽 #{created['epic']} {plan['project']}")
    epic = created["epic"]

    for t in plan["tasks"]:
        if created.get(t["key"]):
            continue
        labels = [
            f"종류/{t.get('kind', '작업')}",
            f"영역/{t.get('area', '파이프라인')}",
            f"우선순위/{t.get('priority', '보통')}",
        ]
        created[t["key"]] = create(t["title"], task_body(t, epic), labels)
        save()
        print(f"  작업 #{created[t['key']]} {t['title']}")

    # 에픽 ← 작업은 sub-issue(진행률 표시), 작업 간 선행은 blocked_by 로 잇는다
    linked = set(plan.setdefault("linked", []))
    pairs = [("sub", "epic", t["key"]) for t in plan["tasks"]]
    pairs += [("dep", t["key"], d) for t in plan["tasks"] for d in t.get("depends_on", [])]
    for kind, a, b in pairs:
        tag = f"{kind}:{a}>{b}"
        if tag in linked:
            continue
        if kind == "sub":
            url, field = f"/issues/{created[a]}/sub_issues", "sub_issue_id"
        else:
            url, field = f"/issues/{created[a]}/dependencies/blocked_by", "issue_id"
        api(url, "-F", f"{field}={issue_id(created[b])}", method="POST")
        linked.add(tag)
        plan["linked"] = sorted(linked)
        save()

    gh("issue", "edit", str(epic), "-R", REPO, "--body-file", "-", body=epic_body(plan, created))
    print(f"완료: https://github.com/{REPO}/issues/{epic}")


def cmd_status(path: str) -> None:
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    created = plan.get("created") or {}
    if not created:
        sys.exit("아직 등록하지 않은 계획이다.")
    for key in ["epic", *[t["key"] for t in plan["tasks"]]]:
        if key in created:
            fields = "number,state,title,milestone"
            view = gh("issue", "view", str(created[key]), "-R", REPO, "--json", fields)
            i = json.loads(view)
            ms = (i.get("milestone") or {}).get("title", "-")
            print(f"#{i['number']:<4} {i['state']:<6} 스프린트 {ms:<12} {i['title']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "check":
        cmd_check()
    elif a[0] == "milestones":
        cmd_milestones()
    elif a[0] == "new-milestone" and len(a) >= 2:
        cmd_new_milestone(*a[1:4])
    elif a[0] == "apply" and len(a) >= 2:
        cmd_apply(a[1], "--dry-run" in a)
    elif a[0] == "status" and len(a) >= 2:
        cmd_status(a[1])
    else:
        sys.exit(__doc__)
