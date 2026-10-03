# Git 워크플로 규칙 (항상 적용)

## 브랜치

- 새 브랜치는 `origin/main` 에서 딴다. 이름은 `feat/*` `fix/*` `refactor/*` (또는 `feat-*`) 이고, 에픽 이슈가 있으면 번호를 넣는다(`feat/123-...`).
- **main 머지 = 운영 배포다.** main 에 직접 push 하지 않는다(가드 훅이 origin main push 를 막는다). 작업 단위마다 브랜치 → PR 로 들어가고, **머지는 사용자가 결정한다.**
- **로컬 main 을 믿지 않는다.** PR 머지와 Gas Town 병합은 origin 에서 일어난다. 작업 전에 `git fetch` 하고 `origin/main` 을 기준으로 삼는다. 뒤처짐은 SessionStart 훅이 알려 준다.
- 이 폴더에 다른 작업 브랜치가 체크아웃돼 있으면 `git worktree add ../trend-<작업> -b <브랜치> origin/main` 으로 분리한다.
- **worktree 파일은 그 폴더에서 새 세션을 열어 고친다.** 원본 세션에서 고치면 경로별 규칙이 붙지 않는다(Claude Code 는 세션 폴더 기준으로만 맞춘다). 가드 훅이 다른 worktree 파일 편집 전에 확인을 묻는다.
- worktree 의 `.claude/` 는 그 브랜치 커밋 판이다. main 에서 하네스가 바뀌면 그 브랜치에 origin/main 을 합쳐야 따라오고, 이미 열린 세션은 재시작해야 새 훅을 읽는다. 인수인계(`.claude/handoff/`)와 graphify 는 git 밖이라 폴더마다 따로다.
- worktree 의 브랜치가 머지되면 그 폴더에서도 `git switch -c <새 브랜치> origin/main` 으로 새로 딴다. 에픽이 끝나 `git worktree remove` 로 지울 때는 git 밖 파일(`mobile/env/prod.json`, `.env`)을 먼저 옮긴다.

## 커밋

- 접두사는 `feat:` `fix:` `hotfix:` `refactor:` `docs:` `test:` `chore:` `perf:` 다. 본문은 한국어로 `<접두사> <무엇> — <왜>` 형태로 쓴다. 리뷰를 반영한 커밋은 끝에 `(Codex 리뷰 반영)` 을 붙이고, 기각한 지적은 본문에 이유를 적는다.
- `git add <파일>` 로 명시하고, 도구 산출물(`.ua/`, `.serena/`, `graphify-out/`)이 딸려 가지 않았는지 `git status` 로 본다.
- amend·force push 하지 않는다. 고칠 것은 새 커밋으로 남긴다.
- CLAUDE.md 와 `.claude/`(규칙·스킬·훅·BANK·업무 계획)는 커밋한다. 커밋하지 않는 것은 `.env`·`secrets/`·`caddy_data/`·`.claude/handoff/`·`.claude/settings.local.json` 이다. 앞의 넷은 가드 훅이 막는다. 로컬 절대 경로가 든 훅(graphify 등)은 `settings.local.json` 에 둔다.

## PR

- `gh` 가 로그인돼 있지 않으면 compare 링크 `https://github.com/yeotaeho/trend/compare/main...<브랜치>` 로 안내한다.
- PR 본문에 `closes #<작업 번호>` 를 적는다. push 는 사용자가 지시했을 때만 한다.
- push 는 `git push -u origin <브랜치>` 처럼 대상을 적는다. 가드는 cd 가 섞인 명령에서 대상을 생략한 push 를 실행 폴더를 확정할 수 없어 막는다.

## 업무 보드 (GitHub Projects `기술파악`)

- 등록된 작업 이슈를 시작하면(브랜치를 따고 첫 수정 전) In Progress 로, PR 머지나 완료 기준 충족이면 Done 으로 옮긴다. 명령과 판단 표는 스킬 `work-intake` 의 "보드 칸" 이다.
- 새 세션의 첫 업무 요청, 진행 상황 질문, 등록된 업무와 겹치는 요청에는 손대기 전에 `python3 .claude/scripts/github_tasks.py board` 로 현황을 본다.
- PR 로 들어가는 작업은 머지 전에 Done 으로 옮기지 않는다.

## Gas Town (다른 PC 의 WSL)

- Polecat 브랜치(`polecat/<이름>/tr-<id>@...`)는 통합 브랜치에 차례로 병합한다. 병합 때 본 함정(충돌 지점·체크포인트 잔재·공용 파일 중복 수정)은 한 번씩 관찰돼 `lessons/BANK.md` 에 있다. 병합 전에 목적지 `git-workflow` 로 grep 한다.
- WSL 에는 GitHub 인증을 넣지 않는다. Refinery 기본 병합이 `git push origin main` 이라, 인증이 없는 상태 자체가 운영 배포 차단 장치다.
