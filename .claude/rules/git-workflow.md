# Git 워크플로 규칙 (항상 적용)

## 브랜치

- 새 브랜치는 `origin/main` 에서 딴다. 이름은 `feat/*` `fix/*` `refactor/*` (또는 `feat-*`) 이고, 에픽 이슈가 있으면 번호를 넣는다(`feat/123-...`).
- **main 머지 = 운영 배포다.** main 에 직접 push 하지 않는다(가드 훅이 origin main push 를 막는다). 작업 단위마다 브랜치 → PR 로 들어가고, **머지는 사용자가 결정한다.**
- **로컬 main 을 믿지 않는다.** PR 머지와 Gas Town 병합은 origin 에서 일어나 로컬 main 이 155커밋 뒤처진 적이 있다. 작업 전에 `git fetch` 하고 `origin/main` 을 기준으로 삼는다.
- 이 폴더에 다른 작업 브랜치가 체크아웃돼 있으면 `git worktree add ../trend-<작업> -b <브랜치> origin/main` 으로 분리한다. `.claude/` 는 커밋돼 있어 worktree 에도 규칙·스킬·훅이 따라온다. 이미 열린 세션은 재시작해야 새 훅을 읽는다.

## 커밋

- 접두사는 `feat:` `fix:` `hotfix:` `refactor:` `docs:` `test:` `chore:` `perf:` 다. 본문은 한국어로 `<접두사> <무엇> — <왜>` 형태로 쓴다. 리뷰를 반영한 커밋은 끝에 `(Codex 리뷰 반영)` 을 붙이고, 기각한 지적은 본문에 이유를 적는다.
- `git add <파일>` 로 명시한다. 도구 산출물(`.ua/`, `.serena/`, `graphify-out/`)이 딸려 가지 않았는지 `git status` 로 본다. `.ua/` 수만 줄이 커밋돼 `ruff check .` 가 깨진 전례가 있다.
- `.gitignore` 를 고치면 마지막 줄 개행을 확인한다. 개행이 없어 두 항목이 한 줄로 붙고 둘 다 무시되지 않은 전례가 있다.
- amend·force push 하지 않는다. 고칠 것은 새 커밋으로 남긴다.
- CLAUDE.md 와 `.claude/`(규칙·스킬·훅·BANK·업무 계획)는 커밋한다. 커밋하지 않는 것은 `.env`·`secrets/`·`caddy_data/`·`.claude/handoff/`·`.claude/settings.local.json` 이다. 앞의 넷은 가드 훅이 막는다. 로컬 절대 경로가 든 훅(graphify 등)은 `settings.local.json` 에 둔다.

## PR

- `gh` 가 로그인돼 있지 않으면 compare 링크 `https://github.com/yeotaeho/trend/compare/main...<브랜치>` 로 안내한다.
- PR 본문에 `closes #<작업 번호>` 를 적는다. push 는 사용자가 지시했을 때만 한다.

## Gas Town (다른 PC 의 WSL)

- Polecat 브랜치(`polecat/<이름>/tr-<id>@...`)는 통합 브랜치에 차례로 병합한다. 충돌은 거의 늘 `mobile/lib/app/router.dart`·`mobile/test/app/router_test.dart` 다.
- **병합 전에 Gas Town 잔재를 확인한다.** 자동 체크포인트(`WIP: checkpoint (auto)`)가 Polecat 오버레이 `CLAUDE.local.md` 344줄을 커밋한 적이 있다.
- 여러 Polecat 이 쓰는 공용 파일(fixture 저장소, 테스트 도우미)의 결함은 bead 로 먼저 올려 한 곳에서 고친다. 같은 결함을 셋이 따로 고친 전례가 있다.
- WSL 에는 GitHub 인증을 넣지 않는다. Refinery 기본 병합이 `git push origin main` 이라, 인증이 없는 상태 자체가 운영 배포 차단 장치다.
