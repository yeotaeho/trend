# 기술 파악 (tech-radar)

개인용 개발 트렌드 알림 앱. GitHub·RSS·YouTube·HN·HF Papers 에서 새 항목을 모아 규칙 필터 → LLM 선별 → 점수 → LLM 판정·요약을 거쳐 읽을 가치가 있는 것만 디스코드·앱(FCM)으로 푸시한다(텔레그램은 대안 어댑터). 플러터 앱(`mobile/`)은 앱 API v1(`/api/v1`)로 피드·찜·설정을 본다. 사용자는 한 명, 프로세스 하나 + Neon 하나. 운영은 Vultr VM 의 Docker Compose 이고 **main 머지가 곧 운영 배포**다. 이 파일은 지도다. 상세는 아래 [문서 지도](#문서-지도)의 파일을 열어 본다.

## 작업 원칙

1. **Think first** — 가정을 명시하고, 해석이 여러 개면 제시한다. 불명확하면 묻는다.
2. **Simplicity** — 요청한 것만. 투기적 기능·단일 사용 추상화·불가능한 시나리오 처리 금지.
3. **Surgical edits + Dead code 제거** — 태스크가 요구하는 줄만 수정하고 기존 스타일을 유지한다. 단, 수정으로 대체·폐기된 이전 코드는 가차없이 제거한다. 주석 처리로 남기기, 미사용 함수·임포트·분기 방치 금지.
4. **Verify** — 코딩 전 성공 기준을 정의하고, 수정 후 반드시 테스트를 실행한다.
5. **Read errors** — 실제 에러·스택 트레이스를 읽고 고친다. 패턴 매칭 추측 금지.
6. **Korean sentences** — 한국어 문장 종결은 `.` `?` `!` 만. `:` 로 끝내지 않는다.
7. **File headers** — 새 소스 파일 첫 줄은 한 줄 한국어 주석으로 역할을 쓴다 (config 파일 제외).
   예) `# GitHub Releases 수집기 — 관심 저장소 릴리즈 폴링·웹훅 수신`
8. **Semantic commits** — 논리적 단위가 끝나면 즉시 커밋한다. 무관한 변경을 묶지 않는다.
9. **수정 범위 확인** — 지정받은 모듈 내부만 자유롭게 수정한다. 엔트리·공용 파일과 지정 범위 밖 모듈은 수정 전에 사용자에게 묻는다. 대상 목록은 `.claude/rules/core-files.md`.

## 컨벤션

- **브랜치·커밋·PR** — `.claude/rules/git-workflow.md`. origin main 직접 push 는 가드 훅이 막는다.
- **설정 분리** — 소스·키워드·임계값은 `config/*.yaml`, 시크릿은 `.env`. 코드에 하드코딩하지 않는다.
- **시크릿** — `.env` 는 커밋 금지. `.env.example` 이 안전한 참조본.
- **결정 로그** — 통과/탈락 판단은 반드시 `decisions` 테이블에 남긴다.
- **LLM 호출** — 모든 호출 직전에 `app/db/budget.py` 의 `reserve_call` 로 예약한다.

## 명령

```bash
uv sync                                   # 설치
uv run uvicorn app.main:app --reload      # 로컬 실행 (FastAPI + APScheduler 같은 프로세스)
docker compose up -d                      # 컨테이너 (app + caddy, DB 는 Neon)

uv run alembic upgrade head               # 마이그레이션 (컨테이너 시작 시 자동)
uv run alembic revision --autogenerate -m "<메시지>"

uv run pytest                             # 전체 테스트
uv run pytest tests/sources/test_rss.py   # 변경 모듈 근처만
uv run ruff check . && uv run ruff format .
uv run mypy app

uv run python scripts/run_job.py collect pipeline notify feedback   # 잡을 순서대로 한 번씩
uv run python scripts/backfill_embeddings.py                        # 임베딩 재계산 (멱등)
uv run python scripts/calibrate_dedupe.py                           # dedupe 임계값 보정 표본
uv run python scripts/weekly_report.py [--apply]                    # 주간 튜닝 표

TEST_DATABASE_URL=<dev> uv run pytest tests/integration             # Neon dev 브랜치 필요

cd mobile && flutter analyze && flutter test                         # 앱 (TEMP 는 ASCII 경로)
python3 .claude/scripts/github_tasks.py apply .claude/tasks/<계획>.json --dry-run   # 업무 → 이슈 미리보기
```

## 문서 지도

**무엇인지 (지식)** — `docs/`

| 파일 | 내용 |
|---|---|
| `docs/architecture.md` | 구성 요소·스택·폴더 지도·실행 흐름·코드 추적 순서·배포 |
| `docs/pipeline.md` | 검증 파이프라인 v2 — 단계별 관문·임계값·LLM 예산·상태 전이·발송 정책 |
| `docs/database.md` | 테이블·큐 겸용 방식·임베딩·Neon 연결·마이그레이션 |
| `docs/api/app-api-v1.md` · `docs/design/` | 앱 ↔ 서버 계약, 화면 명세·픽셀 원본·백엔드 갭 |
| 루트 `기획서.md` `구현도.md` `검증파이프라인-v2-*.md` `소스확장-1차-*.md` `v2-다중사용자-1차-구현서.md` | 기획·설계 원문 |

**어떻게 할지 (규칙·스킬·훅)** — `.claude/`. 작업마다 필요한 것만 붙는다. 전체 배치와 교훈 기록 규칙은 `.claude/rules/lessons.md` 다.

| 작업 대상 | 규칙·스킬 | 로드 |
|---|---|---|
| 공통 교훈·기록 규칙 | `rules/lessons.md` | 항상 |
| 브랜치·커밋·PR·Gas Town | `rules/git-workflow.md` | 항상 |
| 커밋 후 최종 리뷰 | `rules/codex-review.md` | 항상 |
| 작업 단위 종료 기록 | `rules/obsidian-worklog.md` | 항상 |
| 엔트리·공용 파일 | `rules/core-files.md` | 해당 경로 Read 시 — 수정 전 확인 |
| `app/sources/` `config/sources.yaml` | `rules/sources.md` | 해당 경로 Read 시 · 요청 의도로 선택 |
| `app/pipeline/` `config/rules.yaml` | `rules/pipeline.md` | 〃 |
| `app/notify/` 웹훅 `jobs/notify·feedback` | `rules/notify.md` | 〃 |
| `app/db/` 통합 테스트 | `rules/database.md` | 〃 |
| `app/api/v1/` `docs/api/` fixture | `rules/app-api.md` | 〃 |
| `mobile/` | `rules/mobile.md` | 〃 |
| Dockerfile·compose·Caddyfile·`.github/` | `rules/deploy.md` | 〃 |
| `tests/` | `rules/testing.md` | 〃 |
| 알림 원인 진단·임계값 보정 | 스킬 `pipeline-diagnose` | 요청 의도로 선택 |
| 운영 배포 확인·롤백 | 스킬 `deploy-verify` | 〃 |
| 교훈 기록·BANK 정리 | 스킬 `lesson-capture` | 커밋 뒤 Stop 훅 · 요청 의도로 선택 |
| 업무 하달 → 에픽·작업 이슈 등록 | 스킬 `work-intake` | 요청 의도로 선택. 스프린트는 사용자가 정하거나 물어서 붙인다 |

| 훅 (`.claude/settings.json`) | 하는 일 |
|---|---|
| SessionStart `session_context.py` | 브랜치·upstream 대비 뒤처짐·미커밋 파일을 알린다. 압축·재개 뒤엔 인수인계를 되돌려 넣는다 |
| UserPromptSubmit `prompt_router.py` | 규칙·스킬 머리말의 "언제 쓰는가" 를 모아 넣고, Claude 가 요청 의도로 골라 `[적용: ...]` 로 밝힌다. 첫 요청·10번째마다 전체, 그 사이엔 이름만 |
| PreToolUse `guard.py` | 비밀 파일 커밋·origin main 직접 push 를 막고, 배포 파일 수정 전 확인을 요청한다 |
| Stop `lesson_gate.py` | 커밋이 있던 턴 끝에 마무리 순서와 교훈 기록 여부를 한 번 확인시킨다 |
| PreCompact `pre_compact.py` | 압축 직전 요청·고친 파일·실패·커밋을 `.claude/handoff/<세션>.md` 로 저장한다 |
| 플러그인 security-guidance | 편집 시 위험 패턴 경고, 커밋·push 때 보안 리뷰(턴 끝 리뷰는 끔). 기준은 `.claude/claude-security-guidance.md` |

작업 마무리 순서는 **커밋 → Codex 리뷰(지적 반영·재커밋 포함) → 교훈 판단(`lesson-capture`) → 옵시디언 기록 1회** 다.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
