# 아키텍처

**기술 파악(tech-radar)** — 개인용 개발 트렌드 알림 앱. 새로 나온 LLM·라이브러리·프레임워크·기법·플러그인·MCP 와 개발 커뮤니티 이슈를 여러 소스에서 실시간에 가깝게 감지하고, 규칙 필터 → 점수화 → LLM 요약·판단을 거쳐 읽을 가치가 있는 것만 푸시한다. 금융 앱의 "신상품 알림" UX 를 개발 정보에 적용한 것. 사용자는 한 명. 상용화·회원가입·커뮤니티 기능은 비목표.

기획·설계 원문은 레포 루트의 `기획서.md`(v0.1), `구현도.md`(v0.2), `검증파이프라인-v2-설계서.md`·`검증파이프라인-v2-구현서.md`, `소스확장-1차-설계서.md`·`소스확장-1차-구현서.md`, `v2-다중사용자-1차-구현서.md`.

## 구성 요소 — 프로세스 하나 + Neon 하나

컨테이너는 `app` 이미지 1개 (+ Caddy).

| 구성 요소 | 파일 | 역할 |
|---|---|---|
| API 서버 (FastAPI) | `app/main.py` | 웹훅 수신(GitHub release, 텔레그램 콜백), 헬스체크. 같은 프로세스에서 스케줄러 기동 |
| Scheduler/Worker (APScheduler) | `app/jobs/` | 소스별 폴링(`run_source`), 파이프라인(`run_pipeline`), 발송(`run_notify`), 피드백 폴링(`run_feedback`) |
| Neon (Postgres) | — | 모든 상태의 단일 진실 원천. `status` + `FOR UPDATE SKIP LOCKED` 로 큐 겸용 (Redis·MQ 없음) |

**Stack** — Python 3.12+ · uv · FastAPI/uvicorn · APScheduler 3.x(AsyncIOScheduler, Postgres jobstore) · httpx + tenacity · feedparser · trafilatura(본문 보강만) · Neon(Postgres 16/17, pgvector) · SQLAlchemy 2.x async(asyncpg) + Alembic · Pydantic v2 / pydantic-settings · Anthropic SDK(Claude Haiku 급, 구조화 JSON) · Voyage 임베딩 · python-telegram-bot 21.x · structlog · pytest + pytest-asyncio + respx · ruff + mypy · Docker Compose + Caddy · GitHub Actions

## 폴더 지도

```
tech-radar/
├── app/
│   ├── main.py               # FastAPI 앱 + 스케줄러 기동 (엔트리)
│   ├── config.py             # pydantic-settings, YAML 로더
│   ├── schemas.py            # NormalizedItem, Kind 등 Pydantic 스키마
│   ├── log.py                # structlog 설정
│   ├── db/                   # 모델·세션·alembic/ 마이그레이션
│   │   ├── types.py          # Vector 컬럼 타입 (쓰기만, 비교는 SQL)
│   │   ├── budget.py         # reserve_call — LLM 호출 전 예약, 일일 상한
│   │   └── feedback.py       # 피드백 upsert (항목당 1건)
│   ├── sources/              # 수집기 플러그인 — 소스 하나 = 파일 하나
│   │   ├── base.py           # Source 프로토콜, 레지스트리
│   │   ├── rss.py            # 기업 블로그·arXiv 공통
│   │   ├── github_release.py # 관심 저장소 Releases (웹훅 + 보조 폴링)
│   │   ├── hackernews.py     # Algolia 프론트 페이지 30건 (since 무시)
│   │   ├── hf_papers.py      # HF Daily Papers → arXiv URL 로 적재해 upvotes 병합
│   │   └── youtube.py        # 채널 RSS
│   ├── pipeline/             # NEW 항목을 단계별 관문으로 통과 → docs/pipeline.md
│   │   ├── normalize.py      # URL 정규화 → SHA-256 url_hash
│   │   ├── ingest.py         # 적재. 아는 URL 은 metrics·mentions 병합, 되살림
│   │   ├── embedding.py      # Voyage 임베딩 어댑터
│   │   ├── dedupe.py         # 72h 창 벡터 코사인 → 중복·관련 → cluster_id
│   │   ├── rules.py          # exclude 키워드·도메인
│   │   ├── triage.py         # LLM 선별 배치 (25건)
│   │   ├── scoring.py        # 가중합 점수, 되살림 이득
│   │   ├── feedback.py       # 최근접 피드백 사례
│   │   ├── trust.py          # 소스 신뢰도 베이즈 보정
│   │   └── llm.py            # 본문 보강(enrich_body) → 판정·요약
│   ├── notify/               # Notifier 어댑터 + policy.py(강도·상한·무음)
│   ├── jobs/                 # scheduler.py, collect.py, pipeline.py, notify.py, feedback.py
│   └── api/                  # github.py, telegram.py, discord.py, health.py
├── config/
│   ├── sources.yaml          # 소스 등록·폴링 주기·신뢰도·family
│   └── rules.yaml            # policy 문장·exclude·dedupe/triage/scoring/notify 임계값
├── scripts/                  # run_job, backfill_embeddings, calibrate_dedupe, weekly_report
├── tests/                    # 단위 + sources/ + integration/ + fixtures/
├── docs/                     # 이 문서들
├── docker-compose.yml, Dockerfile, Caddyfile, alembic.ini, pyproject.toml
└── .github/workflows/ci.yml  # ruff → mypy → pytest → 이미지 빌드(GHCR) → VM SSH 배포
```

## 실행 흐름과 코드 추적 순서

낯선 동작을 추적할 때는 이 순서로 내려간다.

```
app/main.py (lifespan)
  └─ app/jobs/scheduler.py        잡 등록. 소스별 run_source(interval) + pipeline/notify/feedback
       ├─ jobs/collect.py         Source.fetch(since) → pipeline/normalize → pipeline/ingest (NEW 적재·병합)
       ├─ jobs/pipeline.py        NEW 항목: stale → dedupe → rules → triage(배치) → scoring → llm → SCORED
       ├─ jobs/notify.py          SCORED: notify/policy → Notifier.send → notifications
       └─ jobs/feedback.py        리액션·콜백 폴링 → db/feedback upsert
app/api/*                          웹훅 진입점 (github → ingest, telegram → feedback)
```

역인덱스 — "이걸 고치려면 어디를 보나"

| 바꾸려는 것 | 위치 |
|---|---|
| 소스 추가·폴링 주기·신뢰도 | `config/sources.yaml`, `app/sources/<소스>.py` |
| 관심 주제 문장·exclude | `config/rules.yaml` `policy`·`exclude` |
| 중복·관련 임계값 | `config/rules.yaml` `dedupe`, `app/pipeline/dedupe.py` |
| 점수 가중치·kind 감점·되살림 | `config/rules.yaml` `scoring`, `app/pipeline/scoring.py` |
| 선별·판정 프롬프트 | `app/pipeline/triage.py`, `app/pipeline/llm.py` |
| LLM 일일 상한 | `app/db/budget.py` |
| 발송 강도·상한·무음 시간 | `app/notify/policy.py`, `config/rules.yaml` `notify` |
| 테이블 | `app/db/models.py` + Alembic 리비전 |

## 배포·시크릿

- **CI/CD** — push 시 `ruff → mypy → pytest`. `main` 머지 시 이미지 빌드 → GHCR 푸시 → VM 에 SSH 로 `docker compose pull && up -d`. Alembic 마이그레이션은 컨테이너 시작 시 자동.
- **시크릿** — `.env` 로컬 관리 (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `DISCORD_*`, `TELEGRAM_*`, `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `DATABASE_URL`). `.env.example` 이 참조본.
- **Neon** — pooled 엔드포인트, 브랜치 `main`(운영) / `dev`(로컬·CI). 상세는 `docs/database.md`.
