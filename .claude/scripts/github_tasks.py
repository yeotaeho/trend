# GitHub 업무 등록 — 업무 계획(JSON)을 에픽·작업(sub-issue)·선행 관계·스프린트(마일스톤)로 올린다
"""사용법

  python3 .claude/scripts/github_tasks.py check                    gh 로그인·쓰기 권한 확인
  python3 .claude/scripts/github_tasks.py milestones               열린 스프린트(마일스톤) 목록
  python3 .claude/scripts/github_tasks.py new-milestone <제목> [YYYY-MM-DD 마감] [설명]
  python3 .claude/scripts/github_tasks.py apply <계획.json> [--dry-run]
  python3 .claude/scripts/github_tasks.py status <계획.json>
  python3 .claude/scripts/github_tasks.py board                    보드 현황과 어긋난 칸
  python3 .claude/scripts/github_tasks.py move <번호...> <todo|in-progress|done>
  python3 .claude/scripts/github_tasks.py sync                     닫힘·에픽 진행에 맞춰 칸 이동
  python3 .claude/scripts/github_tasks.py board-init               보드를 만들고 레포에 잇는다

인증은 gh CLI 로그인(`gh auth login`)을 그대로 쓴다. 토큰을 따로 받지 않는다.
보드(GitHub Projects)는 토큰에 project 권한이 있어야 한다(`gh auth refresh -s project`).
대상은 GITHUB_REPO(기본 yeotaeho/trend), 보드는 GITHUB_PROJECT_TITLE(기본 기술파악).
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
OWNER = REPO.split("/", 1)[0]
PROJECT_TITLE = os.environ.get("GITHUB_PROJECT_TITLE", "기술파악")
# 보드 Status 칸 — GitHub Projects 기본 선택지 이름
STATUSES = {"todo": "Todo", "in-progress": "In Progress", "done": "Done"}

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
    ("영역/하네스", "c2e0c6"),
    ("우선순위/높음", "b60205"),
    ("우선순위/보통", "e4e669"),
    ("우선순위/낮음", "cccccc"),
]
KINDS = {"작업", "버그", "조사"}
AREAS = {"수집", "파이프라인", "발송", "DB", "API", "앱", "배포", "하네스"}  # 하네스 = .claude/
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
        if "missing required scopes" in err:
            sys.exit(
                "gh 토큰에 보드(project) 권한이 없다. "
                "사용자가 직접 `gh auth refresh -s project` 를 한 번 실행한다."
            )
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
    board = find_board()
    if board:
        items = board_items(board)
        for number in [epic, *(created[t["key"]] for t in plan["tasks"])]:
            if number not in items:
                set_status(board, add_to_board(board, number), "Todo")
        print(f"보드 '{PROJECT_TITLE}' 의 Todo 에 올렸다.")
    else:
        print(f"보드 '{PROJECT_TITLE}' 가 없어 칸에는 올리지 않았다. 사용자가 원하면 board-init.")
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


# ── 보드 (GitHub Projects) ───────────────────────────────────────────────────


def ghj(*args: str) -> dict:
    return json.loads(gh(*args))


def find_board(create: bool = False) -> dict | None:
    """제목이 PROJECT_TITLE 인 열린 보드와 Status 칸 선택지. 없으면 None(create 면 만든다)."""
    listed = ghj("project", "list", "--owner", OWNER, "-L", "100", "--format", "json")
    p = next(
        (x for x in listed["projects"] if x["title"] == PROJECT_TITLE and not x.get("closed")),
        None,
    )
    if p is None:
        if not create:
            return None
        p = ghj("project", "create", "--owner", OWNER, "--title", PROJECT_TITLE, "--format", "json")
        gh("project", "link", str(p["number"]), "--owner", OWNER, "--repo", REPO)
        print(f"보드 생성: {p['url']}")
    fields = ghj("project", "field-list", str(p["number"]), "--owner", OWNER, "--format", "json")
    status = next(f for f in fields["fields"] if f["name"] == "Status")
    options = {o["name"]: o["id"] for o in status.get("options", [])}
    missing = sorted(set(STATUSES.values()) - set(options))
    if missing:
        sys.exit(f"보드 Status 칸에 {missing} 선택지가 없다. 보드 설정에서 이름을 맞춘다.")
    return {
        "number": str(p["number"]),
        "id": p["id"],
        "field": status["id"],
        "options": options,
        "url": p["url"],
    }


def require_board() -> dict:
    board = find_board()
    if board is None:
        sys.exit(f"보드 '{PROJECT_TITLE}' 가 없다. 사용자가 원하면 board-init 으로 만든다.")
    return board


def board_items(board: dict) -> dict[int, dict]:
    """이 레포 이슈의 보드 항목. 이슈 번호 → {id, status}."""
    data = ghj(
        "project", "item-list", board["number"], "--owner", OWNER, "-L", "1000", "--format", "json"
    )
    items = {}
    for it in data["items"]:
        c = it.get("content") or {}
        if c.get("type") == "Issue" and c.get("repository") == REPO:
            items[c["number"]] = {"id": it["id"], "status": it.get("status") or ""}
    return items


def add_to_board(board: dict, number: int) -> str:
    url = f"https://github.com/{REPO}/issues/{number}"
    added = ghj(
        "project", "item-add", board["number"], "--owner", OWNER, "--url", url, "--format", "json"
    )
    return str(added["id"])


def set_status(board: dict, item_id: str, status: str) -> None:
    option = board["options"][status]
    gh(
        "project", "item-edit", "--id", item_id, "--project-id", board["id"],
        "--field-id", board["field"], "--single-select-option-id", option,
    )  # fmt: skip


def repo_issues() -> dict[int, dict]:
    """work-intake 로 등록한 이슈(종류/ 라벨). 번호 → {closed, epic, title}."""
    rows = json.loads(
        gh(
            "issue",
            "list",
            "-R",
            REPO,
            "--state",
            "all",
            "-L",
            "1000",
            "--json",
            "number,state,title,labels",
        )  # fmt: skip
    )
    out = {}
    for r in rows:
        names = {label["name"] for label in r["labels"]}
        if any(n.startswith("종류/") for n in names):
            out[r["number"]] = {
                "closed": r["state"] == "CLOSED",
                "epic": "종류/에픽" in names,
                "title": r["title"],
            }
    return out


def sub_issues(number: int) -> list[tuple[int, bool]]:
    """에픽의 작업 (번호, 닫힘). 100개를 넘어도 모든 페이지를 읽는다."""
    out = gh(
        "api", "--paginate", f"repos/{REPO}/issues/{number}/sub_issues?per_page=100",
        "--jq", '.[] | "\\(.number) \\(.state)"',
    )  # fmt: skip
    rows = [line.split() for line in out.splitlines() if line.strip()]
    return [(int(n), state == "closed") for n, state in rows]


def desired_status(current: str, closed: bool, subs: list[tuple[bool, str]] | None) -> str | None:
    """이슈 상태에 맞는 보드 칸. 지금 칸이 맞으면 None.

    subs 는 에픽일 때 작업들의 (닫힘, 칸) 목록이고, 작업 이슈면 None 이다.
    닫힌 이슈는 Done, 작업이 하나라도 시작·완료된 열린 에픽은 In Progress,
    Done 칸에 있는데 열려 있으면(다시 열림) In Progress, 칸이 비었으면 Todo 다.
    """
    if closed:
        target = "Done"
    elif current == "Done" or (subs and any(c or s in ("In Progress", "Done") for c, s in subs)):
        target = "In Progress"
    elif not current:
        target = "Todo"
    else:
        return None
    return None if target == current else target


def plan_sync(
    issues: dict[int, dict], items: dict[int, dict], subs: dict[int, list[tuple[int, bool]]]
) -> tuple[list[tuple[int, str]], list[int], list[int]]:
    """(옮길 (번호, 칸) 목록, 닫을 에픽, 다시 열 에픽).

    subs 는 에픽 번호 → 작업 (번호, 닫힘) 목록이다. 작업이 모두 닫힌 열린 에픽은 닫고,
    닫힌 에픽인데 열린 작업이 In Progress 면 작업이 재개된 것이라 다시 연다.
    """
    moves, close, reopen = [], [], []
    for n, info in issues.items():
        current = items.get(n, {}).get("status", "")
        epic_subs = None
        if info["epic"]:
            epic_subs = [(c, items.get(s, {}).get("status", "")) for s, c in subs.get(n, [])]
            if not info["closed"] and epic_subs and all(c for c, _ in epic_subs):
                close.append(n)
                if current != "Done":
                    moves.append((n, "Done"))
                continue
            if info["closed"] and any(not c and s == "In Progress" for c, s in epic_subs):
                reopen.append(n)
                if current != "In Progress":
                    moves.append((n, "In Progress"))
                continue
        target = desired_status(current, info["closed"], epic_subs)
        if target:
            moves.append((n, target))
    return moves, close, reopen


def epic_subs(issues: dict[int, dict]) -> dict[int, list[tuple[int, bool]]]:
    """모든 에픽(닫힌 것 포함)의 작업. 닫힌 에픽도 봐야 재개된 작업을 알아챈다."""
    return {n: sub_issues(n) for n, i in issues.items() if i["epic"]}


def cmd_board() -> None:
    board = require_board()
    issues, items = repo_issues(), board_items(board)
    columns: dict[str, list[int]] = {}
    for n, it in items.items():
        columns.setdefault(it["status"] or "(칸 없음)", []).append(n)
    print(f"보드 {board['url']}")
    for col in ("In Progress", "Todo", "(칸 없음)"):
        rows = sorted(columns.get(col, []))
        if rows or col != "(칸 없음)":
            print(f"[{col}] {len(rows)}건")
        for n in rows:
            print(f"  #{n} {issues.get(n, {}).get('title', '')}")
    print(f"[Done] {len(columns.get('Done', []))}건")
    moves, close, reopen = plan_sync(issues, items, epic_subs(issues))
    missing = [n for n in issues if n not in items]
    if moves or close or reopen or missing:
        print("어긋난 칸 — sync 로 맞춘다")
        for n in missing:
            print(f"  #{n} 보드에 없음")
        for n, s in moves:
            print(f"  #{n} → {s}")
        for n in close:
            print(f"  에픽 #{n} 작업이 모두 닫힘")
        for n in reopen:
            print(f"  에픽 #{n} 닫혔는데 작업이 다시 진행 중")


def cmd_sync(board: dict | None = None) -> None:
    board = board or require_board()
    issues, items = repo_issues(), board_items(board)
    for n in issues:
        if n not in items:
            items[n] = {"id": add_to_board(board, n), "status": ""}
    moves, close, reopen = plan_sync(issues, items, epic_subs(issues))
    for n in close:
        gh(
            "issue", "close", str(n), "-R", REPO, "--reason", "completed",
            "--comment", "작업 이슈가 모두 닫혀 에픽을 닫는다(github_tasks.py sync).",
        )  # fmt: skip
        print(f"에픽 #{n} 닫음")
    for n in reopen:
        gh(
            "issue", "reopen", str(n), "-R", REPO,
            "--comment", "작업이 다시 진행 중이라 에픽을 다시 연다(github_tasks.py sync).",
        )  # fmt: skip
        print(f"에픽 #{n} 다시 엶")
    for n, s in moves:
        set_status(board, items[n]["id"], s)
        print(f"#{n} → {s}")
    if not moves and not close and not reopen:
        print("보드 칸이 이슈 상태와 맞다.")


def cmd_move(args: list[str]) -> None:
    *numbers, state = args
    if state not in STATUSES or not numbers or not all(n.isdigit() for n in numbers):
        sys.exit(__doc__)
    board = require_board()
    items = board_items(board)
    for raw in numbers:
        n = int(raw)
        closed = json.loads(gh("issue", "view", raw, "-R", REPO, "--json", "state"))["state"]
        if state != "done" and closed == "CLOSED":
            sys.exit(f"#{n} 은 닫힌 이슈다. 다시 할 일이면 사용자 확인 뒤 `gh issue reopen {n}`.")
        item = items[n]["id"] if n in items else add_to_board(board, n)
        if state == "done" and closed != "CLOSED":
            gh("issue", "close", raw, "-R", REPO, "--reason", "completed")
        set_status(board, item, STATUSES[state])
        print(f"#{n} → {STATUSES[state]}")
    cmd_sync(board)  # 작업을 옮겼으면 에픽 칸도 따라 맞춘다


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
    elif a[0] == "board":
        cmd_board()
    elif a[0] == "move" and len(a) >= 3:
        cmd_move(a[1:])
    elif a[0] == "sync":
        cmd_sync()
    elif a[0] == "board-init":
        board = find_board(create=True)
        print(f"보드: {board['url']}" if board else "보드를 찾지 못했다.")
    else:
        sys.exit(__doc__)
