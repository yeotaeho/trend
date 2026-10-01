# 교훈 대기열 (BANK)

> 한 번만 관찰됐거나 채택 여부가 정해지지 않은 교훈이다. 기록·정리 절차는 스킬 `lesson-capture` 다(세 조건, 가장 좁은 집, 다섯 기준 겹침, **독립 사건으로 세기**, 트랙, 폐기 조건). 결정·기각 사유·진행 상태의 원본은 옵시디언 `기술파악 - 결정 기록` 이다.
> 2026-10-01 재정리(#26). 09-30 채굴 때 경로 규칙에 바로 올렸던 교훈 가운데 독립 사건이 하나뿐인 것을 여기로 내렸다. 날짜 칸은 관찰한 사건의 날짜다. 레포가 public 이라 IP·엔드포인트 id 는 적지 않는다.

| 날짜 | 트랙 | 증상 | 교훈 | 안 된 방법 | 확인 방법 | 목적지 | 폐기 조건 |
|---|---|---|---|---|---|---|---|
| 10-01 | 버그 | 커밋이 main 에 들어가지 않은 채 남음 | 열려 있던 PR 의 브랜치(`feat/work-board`)에 이어서 커밋했는데, 그 사이 사용자가 PR 을 머지해 새 커밋 3개가 머지된 브랜치에만 남았다. 기존 PR 브랜치에 커밋을 더하기 전에 `gh pr view <번호> --json state` 로 아직 열려 있는지 본다. 머지됐으면 origin/main 에서 새 브랜치를 딴다 | 세션 앞부분에 본 PR 상태를 믿음 | `gh pr view <번호> --json state,mergedAt` | git-workflow (재관찰 시) | — |
| 09-30 | 버그 | 파일 여러 개가 첫 줄만 남음 | Serena `replace_content` 의 regex 모드는 MULTILINE·DOTALL 이라 `^# 헤더 .*$` 의 `.*` 가 줄 끝이 아니라 파일 끝까지 먹는다. 한 줄만 바꿀 때는 `[^\n]*` 을 쓰거나 literal 모드로 한다. 결과는 이제 `edit_check` 훅이 잡는다 | 헤더 한 줄 치환에 `.*$` | 치환 뒤 `wc -l`·`file` 로 줄 수 확인 | lessons.md (재관찰 시) | Serena 가 regex 플래그 기본값을 바꾸면. 두 줄짜리 임시 파일에 같은 치환으로 확인 |
| 09-30 | 지식 | 같은 owner 의 복제 레포 push 가 운영 이미지를 덮을 수 있음 | CI 의 `IMAGE` 가 `ghcr.io/${{ github.repository_owner }}/tech-radar` 라 같은 owner 복제 레포의 main push 가 `:latest` 를 덮고, VM 의 다음 pull 이 그 이미지를 받는다. 복제 레포 deploy 잡에 `github.repository == 'yeotaeho/trend'` 가드를 둔다(trend-2 `c29eeb2`). 원본 `ci.yml` 에는 아직 없다 | "시크릿이 없으니 SSH 에서 실패하고 끝난다" | 복제 레포 run 이 check success · deploy skipped 인지 | deploy.md (재관찰 시) | — |
| 09-30 | 지식 | 무관한 항목이 `cluster_dup` 으로 억제될 수 있음 | 09-10 에는 "관련 0.88 클러스터가 조코딩 영상 4편·arXiv 주제 이웃까지 묶어 클러스터당 하루 1건은 부적합" 으로 보류했다. 앱 v0.1 이 `cluster_daily_cap: 1` 로 구현했지만 그 우려가 풀렸다는 근거가 기록에 없다 | — | `notifications` 의 `level='cluster_dup'` 행과 같은 `cluster_id` 의 발송 항목 제목을 나란히 대조 | notify.md (재관찰 시) | — |
| 09-28 | 버그 | 겹친 낙관적 쓰기에서 실패한 요청이 성공한 다른 저장까지 화면에서 지움 | 실패하면 전체 스냅샷이 아니라 실패한 필드·항목만 되돌린다. 겹친 저장은 직렬화하고 가장 나중 저장이 화면을 정한다. 05·06·11 화면은 `test/features/optimistic_writes_test.dart` 가 지킨다 | 전체 스냅샷 롤백 | 겹친 요청 위젯 테스트 | mobile.md (새 화면에서 재관찰 시) | — |
| 09-28 | 지식 | Polecat 브랜치 병합이 매번 같은 곳에서 충돌 | 화면마다 `mobile/lib/app/router.dart`·`mobile/test/app/router_test.dart` 를 건드려 세 번의 병합 모두 거기서 충돌했다. 병합 뒤 쓰이지 않는 자리표시 화면을 지운다 | — | 병합 전 `git diff --stat` 으로 두 파일 확인 | git-workflow (재관찰 시) | — |
| 09-24 | 지식 | Gas Town 자동 체크포인트가 오버레이를 커밋 | `WIP: checkpoint (auto)` 가 Polecat 오버레이 `CLAUDE.local.md` 344줄을 커밋했다. 병합 전에 잔재를 확인한다 | — | `git log --stat` 에 `CLAUDE.local.md` | git-workflow (재관찰 시) | Gas Town 이 오버레이를 커밋에서 빼면. 체크포인트 커밋의 `--stat` 으로 확인 |
| 09-24 | 지식 | 같은 결함을 Polecat 셋이 따로 고침 | 공용 파일(fixture 저장소·테스트 도우미) 결함을 2분 사이에 서로 다르게 고쳤다. 공용 파일 결함은 bead 로 올려 한 곳에서 고친다 | 각자 우회 | 병합 전 `git log --all -- <공용 파일>` 로 같은 시각대 수정 확인 | git-workflow (재관찰 시) | Gas Town 이 공용 파일 잠금·중복 감지를 제공하면 |
| 09-24 | 지식 | 마이그레이션을 고치려고 새 리비전을 쌓음 | 아직 main 에 나가지 않은 리비전은 새 리비전 대신 그 리비전을 고친다. 병렬 작업 중에는 리비전을 한 작업에만 둔다 | — | `git log origin/main -- app/db/alembic/versions` | database.md (재관찰 시) | — |
| 09-18 | 지식 | `notify: 0` 을 발송 고장으로 봄 | 0 이 나오면 고장보다 상한부터 본다. push 하루 상한, 무음 해제 직후 몰림, `llm_calls` 상한, 선별 모으기 대기, 재임베딩 정지 순이다 | 발송 코드 의심 | 스킬 `pipeline-diagnose` 진단 순서 1 의 로그 이벤트 | pipeline-diagnose (재관찰 시) | — |
| 09-18 | 지식 | Git Bash `ssh` 가 `known_hosts` 를 못 씀 | 사용자 폴더 이름에 한글이 있으면 Git Bash `ssh` 가 경로를 CP949 로 깨뜨려 `known_hosts` 를 쓰지 못한다. 접속 자체는 된다 | — | `ssh -v` 출력의 known_hosts 경로 | deploy-verify (재관찰 시) | 한글 사용자 폴더가 아닌 PC 에서는 해당 없음 |
| 09-15 | 버그 | dev 실데이터로 `test_explore_db.py` 실패 | 전역 최고점을 고르는 테스트라 dev 에 실행 데이터가 쌓이면 깨진다(시드 id 스코핑은 후속). 실패하면 데이터부터 의심한다 | dev 행 삭제로 통과 | 실패 항목의 id 가 시드인지 | testing.md (재관찰 시) | 테스트가 시드 id 로 스코핑되면 |
| 09-14 | 지식 | 새 소스의 신호가 적재 병합에서 샘 | 새 소스를 붙이기 전에 그 신호(metrics·mentions)가 `pipeline/ingest.py` 병합에서 새지 않는지 읽는다. 소스 확장 1차 전에는 같은 URL 이 `ON CONFLICT DO NOTHING` 으로 버려져 hot·multi 항이 사실상 0 이었다 | — | 코드 읽기 | sources.md (재관찰 시) | — |
| 09-13 | 지식 | 사용자 증상 문구를 다른 고장으로 읽음 | "적시에 실행되지 않는다" 는 스케줄러가 아니라 디스코드 버튼의 "앱이 적시에 응답하지 않았습니다" 였다. 증상 문구는 화면·문구 그대로 되묻는다 | 스케줄러 첫 실행 수정 | 사용자에게 문구·화면 확인 | lessons.md · pipeline-diagnose (재관찰 시) | — |
| 09-13 | 버그 | VM SSH 가 간헐적으로 타임아웃(5회 중 4회) | 원인 미확정. 로컬 회선인지 Vultr 인지 모른다. CI 러너에서도 나면 `appleboy/ssh-action` 에 재시도를 둔다 | — | Actions `Deploy to VM` 단계의 실패 메시지 | deploy.md (확정 시) | — |
| 09-13 | 지식 | PowerShell 세션이 스스로 종료됨 | `Get-CimInstance Win32_Process` 를 명령줄 문자열로 필터링하면 필터 문자열이 실행 중인 PowerShell 자신의 명령줄에도 걸려 자기 세션을 죽인다. PID 나 포트로 대상을 고른다 | 명령줄 부분 문자열 필터 | 필터 결과에 자기 PID(`$PID`)가 있는지 | lessons.md (재관찰 시) | — |
| 09-11 | 지식 | 가중치를 옮겼는데 기대한 통과선이 열리지 않음 | 선별 관련도는 0.1 단위로 와서 실질 통과선이 계단식이다. 관련도 0.83 부터 열린다고 봤지만 0.8 은 0.44 로 0.01 모자랐다. 계산할 때 0.1 단위 값으로 대입한다 | 연속값으로 계산 | `decisions.details` 의 relevance 분포 | pipeline.md · pipeline-diagnose (재관찰 시) | 선별 프롬프트·모델이 연속값을 내면. 같은 분포로 확인 |
| 09-11 | 버그 | 스케줄러 테스트가 배선이 끊겨도 통과 | pending 속성만 검사했다. 진짜 `start()` 로 잡이 즉시 불리는지 보고, 고정 sleep 대신 `asyncio.Event` 를 기다린다 | 속성 검사 | 배선을 일부러 끊어 테스트가 실패하는지 | testing.md (재관찰 시) | — |
| 09-10 | 지식 | `.gitignore` 의 두 항목이 무시되지 않음 | 마지막 줄 개행이 없어 `.serena/` 와 `.ua/` 가 한 줄로 붙었다. 고칠 때 끝 바이트를 확인한다 | — | `tail -c 20 .gitignore \| od -c` | git-workflow (재관찰 시) | — |
| 09-10 | 버그 | 도구 산출물 수만 줄이 커밋됨 | `.ua/` 가 "." 커밋 둘로 들어가 `ruff check .` 가 깨졌다 | — | 커밋 전 `git status` | git-workflow (재관찰 시) | — |
| 09-07 | 지식 | `/understand-dashboard` 가 원격 뷰어 실행에서 막힘 | auto mode 분류기가 `npx` 로 원격 tarball 을 받아 실행하는 경로를 막는다. 플러그인 캐시의 `packages/dashboard` 에서 Vite dev 서버를 띄운다. 재기동마다 `?token=` 이 바뀐다 | fast path 재시도 | 브라우저 "Access Token Required" 여부 | lessons.md (재관찰 시) | 플러그인이 로컬 번들 뷰어를 기본으로 쓰게 되면 |
| 09-03 | 버그 | 예외 타입을 바꿨는데 옛 테스트가 계속 통과 | `RateLimited` 가 `RuntimeError` 하위라 옛 기대값 테스트가 남아 같은 경로를 덜 정확하게 검증했다. 예외 타입을 바꾸면 옛 기대값 테스트를 찾아 지운다 | — | `tests/` 에서 옛 예외 이름 grep | testing.md (재관찰 시) | — |
| 09-02 | 지식 | Anthropic 새 글이 수집되지 않음 | Anthropic 은 공식 RSS 가 없다(`/news/rss.xml` 과 후보 4개 404). 커뮤니티 미러(Olshansk/rss-feeds)를 `allowed_hosts: [anthropic.com]` 으로 묶어 쓴다. 2차 후보는 사이트맵 폴링이다 | 공식 경로 추측 | curl 로 후보 URL 상태 코드 | sources.md (사이트맵 전환 시) | Anthropic 이 공식 RSS 를 내면. 같은 curl 로 확인 |
