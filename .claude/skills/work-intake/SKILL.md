---
name: work-intake
description: 사용자가 새 업무·과제·요구사항을 하달하거나("~ 해야 한다", "~ 붙여 줘", 설계서·기획서 전달), 여러 단계로 나눠 관리할 만한 일을 맡겼을 때 쓴다. 업무를 에픽과 작업으로 나누고 GitHub 이슈로 등록하며, 스프린트(마일스톤)는 사용자가 정하거나 물어서 붙인다. 등록된 작업을 시작하거나 끝냈을 때 보드 칸(Todo·In Progress·Done)을 옮길 때, 진행 상황·남은 일·이슈 번호를 묻거나 요청이 이미 등록된 업무와 겹쳐 보드 현황을 확인해야 할 때도 쓴다.
---

# 업무 접수 → GitHub 이슈 등록

> 저장소는 GitHub `yeotaeho/trend` 다. **공개 저장소**이므로 이슈에 비밀값·VM 주소·DB 연결 문자열·봇 토큰을 적지 않는다. "프로젝트" 는 **에픽 이슈**(작업은 그 sub-issue), "스프린트" 는 **마일스톤**으로 표현한다. 인증은 `gh` 로그인이다.

## 언제 등록하나

| 요청 | 처리 |
|---|---|
| 한 번에 끝나는 질문·잔수정 | 등록하지 않는다 |
| 커밋이 둘 이상 필요하거나, 여러 날에 걸치거나, 백엔드·앱·배포가 섞인 업무 | 에픽 + 작업 이슈로 등록한다 |
| 작업 중 발견한 별개 결함 | 버그 이슈 한 건을 제안한다 |

## 절차

1. **이해** — 요청을 한 문단으로 다시 쓴다. 모호한 점이 결과를 크게 바꾸면 묻고, 아니면 가정을 적고 진행한다.
2. **조사** — 나누기 전에 코드를 본다. `docs/architecture.md` 의 코드 추적 순서로 진입점·모듈을 찾고, 라우터 목록에서 해당 규칙·스킬을 읽는다. 설계서가 있으면(루트 `*-설계서.md`·`*-구현서.md`) 그 단계 구분을 따른다. 파일 이름만 보고 나누지 않는다.
3. **분해** — 에픽 하나와 작업 3~8개. 작업 하나는 커밋 하나에서 반나절 정도의 크기다. 각 작업에 다음을 채운다.
   - `kind` 작업·버그·조사 / `area` 수집·파이프라인·발송·DB·API·앱·배포 / `priority` 높음·보통·낮음
   - `done_when` 완료 기준 — 확인 가능한 문장으로(예: "uv run pytest tests/sources 통과", "decisions 에 stage=triage 행이 남는다").
   - `verify` 검증 방법, `files` 관련 파일, `depends_on` 선행 작업 key
   - 엔트리·공용 파일(`.claude/rules/core-files.md`)이나 배포 파일 수정이 들어가면 작업 제목에 "(허락 필요)" 를 붙인다.
   - 조사부터 해야 결론이 나는 일은 `조사` 작업을 앞에 두고 나머지를 거기에 의존시킨다.
4. **스프린트** — 사용자가 요청에서 스프린트를 말했으면 그대로 쓴다. 말하지 않았으면 `milestones` 로 열린 목록을 보여 주고 **묻는다**(AskUserQuestion). 선택지는 열린 스프린트들, "스프린트 없이 등록", "새 스프린트 만들기(이름·마감일을 받아서)". 스프린트를 임의로 고르거나 만들지 않는다.
5. **미리보기** — 계획을 `.claude/tasks/<YYYY-MM-DD>-<짧은이름>.json` 에 쓰고 `apply <파일> --dry-run` 결과를 표로 보여 준다. 비밀값 검사에 걸리면 고친다.
6. **등록** — 사용자가 미리보기를 확인하면 `apply <파일>` 로 올린다. 사용자가 "바로 등록" 이라고 했으면 미리보기 확인을 건너뛴다. 에픽과 작업은 보드 '기술파악' 의 Todo 에 함께 오른다. 끝나면 에픽 링크와 이슈 번호 표를 보고한다.
7. **작업과 연결** — 이후 이 업무를 할 때
   - 브랜치 이름에 에픽 번호를 넣는다(예: `feat/123-source-expansion-2`).
   - 커밋 메시지 끝에 `#<작업 번호>` 를 적는다.
   - PR 본문에 `closes #<작업 번호>` 를 적어 머지 때 닫히게 한다. 에픽은 sub-issue 가 모두 닫히면 `sync` 가 닫는다.
   - 옵시디언 기능 노트의 "어디" 표에 에픽 링크를 넣는다.
8. **보드 칸 옮기기** — 아래 "보드 칸" 표대로 상태가 바뀌는 순간에 옮긴다.
9. **진행 확인** — "그 업무 어디까지 됐지?" 에는 `board` 로 답하고, 한 업무만 보면 `status <파일>` 을 쓴다.

## 보드 칸

보드는 GitHub Projects `기술파악`(레포에 연결)이다. Status 칸은 Todo · In Progress · Done 셋이다.

| 순간 | 할 일 | 명령 |
|---|---|---|
| 등록 | Todo 에 올린다 | `apply` 가 한다 |
| 작업을 시작한다(브랜치를 따고 첫 수정 전, 조사면 조사 시작 전) | In Progress 로 옮긴다. 에픽도 따라 In Progress 가 된다 | `move <번호> in-progress` |
| PR 로 들어가는 작업의 PR 이 머지됐다 | `closes #번호` 로 이슈가 닫히면 Done 이다. 확인한 김에 맞춘다 | `sync` |
| PR 없이 끝나는 작업(조사·설정·운영 확인)의 완료 기준을 다 채웠다 | 결과를 보고하고 Done 으로 옮긴다(이슈도 닫힌다) | `move <번호> done` |
| 작업을 멈추거나 다음으로 미룬다 | Todo 로 되돌리고 이유를 이슈 댓글로 남긴다 | `move <번호> todo` |

- **PR 로 들어가는 작업은 머지 전에 Done 으로 옮기지 않는다.** main 머지가 곧 운영 배포라 머지가 완료 시점이다. 머지는 사용자가 한다.
- 에픽은 손으로 옮기지 않는다. `move`·`sync` 가 작업 칸을 보고 In Progress 로 옮기고, 작업이 모두 닫히면 에픽을 닫아 Done 으로 옮긴다.

## 현황 확인 — 언제 보드를 보나

- **새 세션의 첫 업무 요청** — 손대기 전에 `board` 를 돌린다. SessionStart 훅이 알려 준다. 요청과 겹치는 이슈가 있으면 번호로 짚고, 이미 In Progress 인 작업을 이어서 하는지 새 작업인지 밝힌다. 단순 질문에는 돌리지 않는다.
- **진행 상황·남은 일·이슈 번호를 물을 때**, **요청이 등록된 업무와 겹칠 때**(같은 기능·파일·에픽), **PR 머지를 확인했을 때** 도 본다.
- `board` 가 "어긋난 칸" 을 보이면(닫혔는데 Done 이 아님, 보드에 없음 등) `sync` 로 맞추고 무엇을 옮겼는지 보고한다.
- 보드가 없다고 나오면 사용자에게 알리고, 원할 때만 `board-init` 으로 만든다. project 권한이 없다고 나오면 사용자에게 `gh auth refresh -s project` 를 부탁한다.

## 계획 파일 형식

```json
{
  "project": "소스 확장 2차 — Anthropic 사이트맵 · MCP 레지스트리",
  "why": "소스 확장 1차 이후 공식 발표·MCP 서버 소식을 놓친다.",
  "summary": "수집기 두 개를 추가하고 sources.yaml 에 등록한다.",
  "milestone": "2026-10 1주차",
  "tasks": [
    {"key": "t1", "title": "Anthropic 사이트맵 수집기", "kind": "작업", "area": "수집",
     "priority": "높음", "body": "sitemap.xml 의 lastmod 로 since 를 거른다.",
     "done_when": ["uv run pytest tests/sources 통과"], "verify": ["run_job.py collect 로 1회 적재"],
     "files": ["app/sources/anthropic_sitemap.py", "config/sources.yaml"], "depends_on": []}
  ]
}
```

`created`·`linked` 는 스크립트가 채운다. 손으로 지우면 중복 등록된다. 계획 파일은 커밋해 진행 기록으로 남긴다.

## 명령

```bash
python3 .claude/scripts/github_tasks.py check
python3 .claude/scripts/github_tasks.py milestones
python3 .claude/scripts/github_tasks.py new-milestone "2026-10 1주차" 2026-10-09
python3 .claude/scripts/github_tasks.py apply .claude/tasks/<파일>.json --dry-run
python3 .claude/scripts/github_tasks.py apply .claude/tasks/<파일>.json
python3 .claude/scripts/github_tasks.py status .claude/tasks/<파일>.json
python3 .claude/scripts/github_tasks.py board
python3 .claude/scripts/github_tasks.py move 12 13 in-progress
python3 .claude/scripts/github_tasks.py move 14 done
python3 .claude/scripts/github_tasks.py sync
python3 .claude/scripts/github_tasks.py board-init          # 사용자가 보드를 만들라고 했을 때만
```

- `gh` 가 로그인돼 있지 않으면 사용자에게 `gh auth login` 을 직접 한 번 해 달라고 한다. 토큰을 채팅으로 받지 않는다.
- 라벨(종류·영역·우선순위)은 첫 등록 때 없으면 자동으로 만든다.
- `new-milestone` 은 사용자가 스프린트를 만들라고 했을 때만 쓴다.
- Gas Town(다른 PC 의 WSL) 에 넘길 일이면 등록 뒤 이슈 번호를 사용자에게 주고, Mayor 에게 전달하는 것은 사용자가 한다.
