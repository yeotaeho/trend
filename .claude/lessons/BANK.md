# 교훈 대기열 (BANK)

> 한 번만 관찰됐거나 채택 여부가 정해지지 않은 교훈이다. 기록·정리 절차는 스킬 `lesson-capture` 다(세 조건, 가장 좁은 집, 다섯 기준 겹침, 트랙, 폐기 조건). 결정·기각 사유·진행 상태의 원본은 옵시디언 `기술파악 - 결정 기록` 이다.
> 2026-09-30 첫 정리. 두 번 이상 관찰된 것은 이미 rule·skill 로 올렸고, 여기에는 한 번 관찰된 것만 남겼다. 레포가 public 이라 IP·엔드포인트 id 는 적지 않는다.

| 날짜 | 트랙 | 증상 | 교훈 | 안 된 방법 | 확인 방법 | 목적지 | 폐기 조건 |
|---|---|---|---|---|---|---|---|
| 2026-09-30 | 버그 | 파일 여러 개가 첫 줄만 남음 | Serena `replace_content` 의 regex 모드는 MULTILINE·DOTALL 이라 `^# 헤더 .*$` 의 `.*` 가 줄 끝이 아니라 파일 끝까지 먹는다. 한 줄만 바꿀 때는 `[^\n]*` 을 쓰거나 literal 모드로 한다 | 헤더 한 줄 치환에 `.*$` | 치환 뒤 `wc -l`·`file` 로 줄 수 확인 | lessons.md (재관찰 시) | Serena 가 regex 플래그 기본값을 바꾸면. 두 줄짜리 임시 파일에 같은 치환으로 확인 |
| 2026-09-30 | 지식 | 무관한 항목이 `cluster_dup` 으로 억제될 수 있음 | 09-10 에는 "관련 0.88 클러스터가 조코딩 영상 4편·arXiv 주제 이웃까지 묶어 클러스터당 하루 1건은 부적합" 으로 보류했다. 앱 v0.1 이 `cluster_daily_cap: 1` 로 구현했지만 그 우려가 풀렸다는 근거가 기록에 없다 | — | `notifications` 의 `level='cluster_dup'` 행과 같은 `cluster_id` 의 발송 항목 제목을 나란히 대조 | notify.md (재관찰 시) | — |
| 2026-09-23 | 지식 | Gas Town Refinery 가 `timeout waiting for runtime prompt` 로 멈춤 | Claude Code 폴더 신뢰 창에서 멈췄다. Gas Town 의 `AcceptWorkspaceTrustDialog` 는 "1번이 Yes" 라고 보고 Enter 만 보내지만 Claude Code 2.1.280 은 1번이 `No, exit` 다. 에이전트 작업 경로를 `~/.claude.json` 에 미리 신뢰 등록한다 | 로그만 보기 | tmux 화면 캡처 | git-workflow.md (재관찰 시) | Gas Town 이 신뢰 창 처리를 고치거나 Claude Code 선택지 순서가 바뀌면. `gt up` 뒤 tmux 캡처로 확인 |
| 2026-09-18 | 지식 | Git Bash `ssh` 가 `known_hosts` 를 못 씀 | 사용자 폴더 이름에 한글이 있으면 Git Bash `ssh` 가 경로를 CP949 로 깨뜨려 `known_hosts` 를 쓰지 못한다. 접속 자체는 된다 | — | `ssh -v` 출력의 known_hosts 경로 | deploy-verify (재관찰 시) | 한글 사용자 폴더가 아닌 PC 에서는 해당 없음 |
| 2026-09-13 | 버그 | VM SSH 가 간헐적으로 타임아웃(5회 중 4회) | 원인 미확정. 로컬 회선인지 Vultr 인지 모른다. CI 러너에서도 나면 `appleboy/ssh-action` 에 재시도를 둔다 | — | Actions `Deploy to VM` 단계의 실패 메시지 | deploy.md (확정 시) | — |
| 2026-09-13 | 지식 | PowerShell 세션이 스스로 종료됨 | `Get-CimInstance Win32_Process` 를 명령줄 문자열로 필터링하면 필터 문자열이 실행 중인 PowerShell 자신의 명령줄에도 걸려 자기 세션을 죽인다. PID 나 포트로 대상을 고른다 | 명령줄 부분 문자열 필터 | 필터 결과에 자기 PID(`$PID`)가 있는지 | lessons.md (재관찰 시) | — |
| 2026-09-10 | 지식 | 옵시디언 기록이 실패함 | 옵시디언 앱이 꺼져 있으면 MCP 기록이 실패한다. 켠 뒤 다시 쓴다 | — | `vault_list` 가 응답하는지 | obsidian-worklog.md (재관찰 시) | 옵시디언 MCP 가 앱 없이 동작하게 되면 |
| 2026-09-07 | 지식 | `/understand-dashboard` 가 원격 뷰어 실행에서 막힘 | auto mode 분류기가 `npx` 로 원격 tarball 을 받아 실행하는 경로를 막는다. 플러그인 캐시의 `packages/dashboard` 에서 Vite dev 서버를 띄운다. 재기동마다 `?token=` 이 바뀐다 | fast path 재시도 | 브라우저 "Access Token Required" 여부 | lessons.md (재관찰 시) | 플러그인이 로컬 번들 뷰어를 기본으로 쓰게 되면 |
| 2026-09-02 | 지식 | Anthropic 새 글이 수집되지 않음 | Anthropic 은 공식 RSS 가 없다(`/news/rss.xml` 과 후보 4개 404). 커뮤니티 미러(Olshansk/rss-feeds)를 `allowed_hosts: [anthropic.com]` 으로 묶어 쓴다. 2차 후보는 사이트맵 폴링이다 | 공식 경로 추측 | curl 로 후보 URL 상태 코드 | sources.md (사이트맵 전환 시) | Anthropic 이 공식 RSS 를 내면. 같은 curl 로 확인 |
