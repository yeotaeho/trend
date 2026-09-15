# 기술 파악 (tech-radar)

개인용 개발 트렌드 알림 앱. GitHub·RSS·YouTube·HN·HF Papers 에서 새 항목을 모아 규칙 필터 → LLM 선별 → 점수 → LLM 판정·요약을 거쳐 읽을 가치가 있는 것만 디스코드(→텔레그램)로 푸시한다. 사용자는 한 명, 프로세스 하나 + Neon 하나. 이 파일은 지도다. 상세는 아래 [문서 지도](#문서-지도)의 파일을 열어 본다.

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

- **브랜치** — `feat-*` / `fix-*` / `refactor-*` (또는 `feat/*` 형식).
- **커밋 접두사** — `feat:` `fix:` `hotfix:` `refactor:` `docs:` `test:` `chore:` `perf:`
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
```

## 문서 지도

**무엇인지 (지식)** — `docs/`

| 파일 | 내용 |
|---|---|
| `docs/architecture.md` | 구성 요소·스택·폴더 지도·실행 흐름·코드 추적 순서·배포 |
| `docs/pipeline.md` | 검증 파이프라인 v2 — 단계별 관문·임계값·LLM 예산·상태 전이·발송 정책 |
| `docs/database.md` | 테이블·큐 겸용 방식·임베딩·Neon 연결·마이그레이션 |
| 루트 `기획서.md` `구현도.md` `검증파이프라인-v2-*.md` `소스확장-1차-*.md` `v2-다중사용자-1차-구현서.md` | 기획·설계 원문 |

**어떻게 할지 (규칙)** — `.claude/rules/`. `paths` 가 있는 규칙은 편집하는 파일 경로에 따라 자동 로드되고, 없는 규칙은 항상 로드된다.

| 파일 | 적용 경로 |
|---|---|
| `core-files.md` | 엔트리·공용 파일 — 수정 전 확인 |
| `sources.md` | `app/sources/`, `config/sources.yaml`, `tests/sources/` |
| `pipeline.md` | `app/pipeline/`, `config/rules.yaml` |
| `notify.md` | `app/notify/`, `app/api/telegram.py`, `app/api/discord.py` |
| `database.md` | `app/db/`, `scripts/backfill_embeddings.py` |
| `testing.md` | `tests/` |
| `codex-review.md` | 항상 — 커밋 후 최종 리뷰 게이트 |
| `obsidian-worklog.md` | 항상 — 작업 단위 종료 시 옵시디언 기록 |

작업 마무리 순서는 **커밋 → Codex 리뷰(지적 반영·재커밋 포함) → 옵시디언 기록 1회** 다.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
