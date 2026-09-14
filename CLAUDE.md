# CLAUDE.md

## Coding Behavior

1. **Think first** — 가정을 명시하고, 해석이 여러 개면 제시. 불명확하면 묻기.
2. **Simplicity** — 요청한 것만. 투기적 기능·단일 사용 추상화·불가능한 시나리오 처리 금지.
3. **Surgical edits + Dead code 제거** — 태스크가 요구하는 줄만 수정하고 기존 스타일 유지. 단, 수정으로 **대체·폐기된 이전 코드는 가차없이 제거**한다. 주석 처리로 남기기, 미사용 함수·임포트·분기 방치 금지. 죽은 코드를 발견하면 즉시 지운다.
4. **Verify** — 코딩 전 성공 기준 정의. 코드 수정 후 반드시 테스트 실행.
5. **Korean sentences** — 한국어 문장 종결은 `.` `?` `!` 만. `:` 로 끝내지 않기.
6. **File headers** — 새 소스 파일 첫 줄: 한 줄 한국어 주석으로 역할 명시 (config 파일 제외).
  예) `# GitHub Releases 수집기 — 관심 저장소 릴리즈 폴링·웹훅 수신`
7. **Semantic commits** — 논리적 단위 완성 시 즉시 커밋. 무관한 변경 묶지 않기.
8. **Read errors** — 실제 에러/스택 트레이스 읽고 수정. 패턴 매칭 추측 금지.
9. **Work log (Obsidian)** — 작업 단위의 커밋과 Codex 리뷰(지적 반영·재커밋 포함)까지 모두 끝난 뒤, 최종 상태를 옵시디언 MCP 로 **1회 기록**한다(프로젝트 노트 + 일일 노트). 위치·양식은 아래 [작업 기록 규칙](#작업-기록-규칙-obsidian) 참고.
10. **Codex 최종 리뷰** — 계획·구현·수정 작업을 논리적 단위로 마치고 커밋한 뒤, **마지막에 Codex 리뷰를 거친다**. 형식·절차는 아래 [Codex 리뷰 규칙](#codex-리뷰-규칙) 참고
11. **수정 범위 확인** — 지정받은 모듈·단계 내부만 자유롭게 수정한다. 그 밖의 수정 — 프로젝트 루트·엔트리 파일(`app/main.py`, `app/config.py`, `app/schemas.py`, `pyproject.toml`, `docker-compose.yml` 등)과 공용 모듈(`app/db/`, `app/pipeline/`, `app/notify/policy.py`, `config/*.yaml` 등), 지정 범위 밖 모듈 — 은 **수정 전에 사용자에게 물어본다**.

---



## Project Overview

**기술 파악(tech-radar)** — 개인용 개발 트렌드 알림 앱. 새로 나온 LLM·라이브러리·프레임워크·기법·플러그인·MCP 와 개발 커뮤니티 이슈를 여러 소스(GitHub, RSS, YouTube, HN, Reddit, X)에서 실시간에 가깝게 감지하고, 규칙 필터 → 점수화 → LLM 요약·판단을 거쳐 읽을 가치가 있는 것만 텔레그램(이후 앱/FCM)으로 푸시한다. 금융 앱의 "신상품 알림" UX 를 개발 정보에 적용한 것. 사용자는 나 혼자(단일 사용자)이며 상용화·회원가입·커뮤니티 기능은 비목표.

기획·설계 원문은 레포 루트의 `기획서.md`(v0.1), `구현도.md`(v0.2), 검증 파이프라인 v2 는 `검증파이프라인-v2-설계서.md`·`검증파이프라인-v2-구현서.md` 참고.

**프로세스 하나 + Neon 하나**로 구성 (MVP). 컨테이너는 `app` 이미지 1개.

| 구성 요소 | 파일 | 역할 |
| --- | --- | --- |
| API 서버 (FastAPI) | `app/main.py` | 웹훅 수신(GitHub release, 텔레그램 봇 콜백), 헬스체크, 이후 앱용 REST API. 같은 프로세스에서 스케줄러 기동 |
| Scheduler/Worker (APScheduler) | `app/jobs/` | 소스별 폴링 잡(`run_source`), 파이프라인 잡(`run_pipeline`), 발송 잡(`run_notify`), 피드백 폴링 잡(`run_feedback`) |
| Neon (Postgres) | — | 모든 상태의 단일 진실 원천. `status` 컬럼 + `FOR UPDATE SKIP LOCKED` 로 큐 역할도 겸함 (Redis·MQ 없음) |

**Stack** — Python 3.12+ · uv · FastAPI/uvicorn · APScheduler 3.x(AsyncIOScheduler, Postgres jobstore) · httpx + tenacity · feedparser · trafilatura(본문 보강 단계에서만) · Neon(Postgres 16/17, pg_trgm) · SQLAlchemy 2.x async(asyncpg, `statement_cache_size=0`) + Alembic · Pydantic v2 / pydantic-settings · Anthropic SDK(Claude Haiku 급, 구조화 JSON 출력) · python-telegram-bot 21.x · structlog · pytest + pytest-asyncio + respx · ruff + mypy · Docker Compose + Caddy · GitHub Actions

**파이프라인 (설계 원칙: 플러그인 · 멱등 · 정책은 문장으로 · 결정은 로그로)** — v2 (`검증파이프라인-v2-설계서.md`)

```
[소스] → [수집기 sources/*] → [적재 + 임베딩] → NEW
                └ 아는 URL 이면 버리지 않고 raw.metrics(키별 max)·mentions 병합. 점수 탈락 항목은 마지막 점수 + hot·multi 이득(마지막 결정의 breakdown 기준)이 임계값 이상이면 NEW 로 되살림 (선별 캐시, LLM 재호출 없음)
1국면 (항목별)   stale(72h) → 중복·관련 (벡터 코사인, 생존자 기준) → exclude 규칙
2국면 (25건 배치) LLM 선별 — 정책 문장을 읽고 관련도 0~1 + 이유
3국면 (항목별)   점수(src·rel·hot·multi·fresh + kind 감점 ≥ 0.45) → 본문 보강* → LLM 판정·요약 → SCORED
발송 잡          강도·상한·무음 → 디스코드 (+ 🧪 탐색 슬롯 1건/일)
```

키워드 목록은 관문이 아니다. `rules.yaml` 의 `policy` 문장을 선별·판정 프롬프트가 읽는다. 모든 LLM 호출은 `llm_calls` 예약 행을 먼저 커밋한다(일일 상한). 단일 프로세스 전제.

---



## Commands

```bash
# 설치
uv sync

# 로컬 실행 (FastAPI + APScheduler 같은 프로세스)
uv run uvicorn app.main:app --reload

# 컨테이너 실행 (app + caddy, DB 컨테이너 없음 — Neon)
docker compose up -d

# 마이그레이션 (컨테이너 시작 시 자동 실행되지만 수동으로도 가능)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "<메시지>"

# 테스트 (소스별 실제 응답 샘플은 tests/fixtures/, HTTP 는 respx 로 모킹)
uv run pytest
uv run pytest tests/sources/test_rss.py   # 변경 모듈 근처만 돌릴 때

# 린트·타입
uv run ruff check . && uv run ruff format .
uv run mypy app

# 수동 실행·백필·튜닝 리포트
uv run python scripts/run_job.py collect pipeline notify feedback   # 잡을 순서대로 한 번씩
uv run python scripts/backfill_embeddings.py               # 임베딩 NULL·모델 불일치 행 재계산 (멱등)
uv run python scripts/calibrate_dedupe.py                  # 유사도 구간별 쌍 표본 → dedupe 임계값 보정
uv run python scripts/weekly_report.py [--apply]           # 주간 튜닝 표, --apply 면 소스 신뢰도 보정 기록

# 통합 테스트 (pgvector 쿼리·예약 원자성). Neon dev 브랜치를 가리켜야 한다
TEST_DATABASE_URL=<dev> uv run pytest tests/integration
```

---



## Architecture (간단 구조)

```
tech-radar/
├── app/
│   ├── main.py               # FastAPI 앱 + 스케줄러 기동 (엔트리)
│   ├── config.py             # pydantic-settings, YAML 로더 (.env 는 gitignore 대상)
│   ├── schemas.py            # NormalizedItem 등 Pydantic 스키마
│   ├── db/                   # SQLAlchemy 모델, 세션, alembic/ 마이그레이션
│   │   ├── types.py          # Vector 컬럼 타입 (쓰기만, 비교는 SQL)
│   │   ├── budget.py         # reserve_call — LLM 호출 전 예약, 일일 상한
│   │   └── feedback.py       # 피드백 upsert (항목당 1건)
│   │
│   │  # 플러그인 계층 — 소스 하나 = 파일 하나
│   ├── sources/              # 수집기 (Source 프로토콜: name, interval, fetch(since))
│   │   ├── base.py           # Source 프로토콜, 등록 레지스트리
│   │   ├── rss.py            # 기업 블로그·arXiv 공통
│   │   ├── github_release.py # 관심 저장소 Releases (웹훅 + 보조 폴링)
│   │   ├── hackernews.py     # Algolia 프론트 페이지 30건 (since 무시, 재관측은 적재 병합이 처리)
│   │   ├── hf_papers.py      # HF Daily Papers → arXiv URL 로 적재해 기존 arXiv 항목에 upvotes 병합
│   │   ├── youtube.py        # 채널 RSS (조코딩·코딩애플 등)
│   │   ├── github_trending.py# 미구현 (2차, Search API)
│   │   └── reddit.py         # 미구현 (2차, OAuth 승인 후 httpx)
│   │
│   │  # 파이프라인 — NEW 항목을 단계별 관문으로 통과
│   ├── pipeline/
│   │   ├── normalize.py      # URL 정규화(utm 제거 등) → SHA-256 url_hash
│   │   ├── ingest.py         # url_hash 적재. 아는 URL 은 metrics·mentions 병합(같은 family 는 제외), hot·multi 이득이 임계값을 넘길 수 있는 점수 탈락은 되살림
│   │   ├── embedding.py      # Voyage/OpenAI 임베딩 어댑터, 적재 직후·보충 계산
│   │   ├── dedupe.py         # 72h 창 벡터 코사인 → 중복(≥0.96, 생존자 기준)·관련(≥0.88) → cluster_id
│   │   ├── rules.py          # exclude 키워드·도메인만 (config/rules.yaml)
│   │   ├── triage.py         # LLM 선별 배치 — 정책 문장 → 관련도 0~1 + 이유
│   │   ├── scoring.py        # trust·relevance·hotness·multi·freshness 가중합, stale 가드
│   │   ├── feedback.py       # 최근접 피드백 사례 (3단계)
│   │   ├── trust.py          # 소스 신뢰도 베이즈 보정 (4단계)
│   │   └── llm.py            # 본문 보강(trafilatura) → 판정 프롬프트, 구조화 출력, summaries 캐시
│   │
│   │  # 발송 — Notifier 프로토콜 어댑터
│   ├── notify/
│   │   ├── base.py           # Notifier 프로토콜 (send → message_id)
│   │   ├── telegram.py       # MVP. 인라인 버튼 👍/👎 → feedback
│   │   ├── discord.py        # 선택 (Webhook)
│   │   └── policy.py         # 강도(push/silent/feed)·하루 상한·무음 시간 — 알림 피로 규칙은 여기 한 곳에
│   │
│   ├── jobs/                 # APScheduler 잡 정의 (run_source, run_pipeline, run_notify)
│   └── api/                  # 웹훅 라우터(github, telegram), health, (3단계) items API
│
├── config/
│   ├── sources.yaml          # 소스 등록·폴링 주기·신뢰도
│   └── rules.yaml            # policy(관심 문장·주목 저장소)·exclude·dedupe/triage/scoring/notify 임계값
├── tests/
│   └── fixtures/             # 소스별 실제 응답 샘플
├── scripts/                  # 수동 실행·백필·주간 튜닝 리포트
├── docker-compose.yml        # app + caddy
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml  # ruff → mypy → pytest → 이미지 빌드(GHCR) → VM SSH 배포
```



### 데이터 모델

- `sources` — 수집 소스 정의 (`type`, `config` jsonb, `poll_interval_sec`, `trust_score`, `last_polled_at`, `last_error`)
- `items` — 정규화된 항목 (핵심). `url_hash` unique, `category`, `cluster_id`, `status`, `embedding vector(1024)`(적재 시점 텍스트, 파이썬에서 읽지 않음)·`embedding_model`
- `decisions` — 항목별 판단 기록 (`stage` rule|triage|score|llm, `passed`, `score`, `details` jsonb). 튜닝 근거
- `llm_calls` — LLM 호출 직전 예약 행 (`kind` triage|judge|explore, `batch_id`, `called_at`). 일일 상한은 이 표로 센다
- `summaries` — LLM 결과 (`title_ko`, `summary_ko`, `tags`, `importance` 1~5, `worth_notifying`, 토큰 수). 재실행 시 캐시
- `notifications` — 발송 기록 (`channel`, `level` push|silent|feed, `message_id`, `error`)
- `feedback` — 사용자 반응 (`verdict` useful|useless). 항목당 1건, 재클릭은 upsert
- `user_prefs` — 단일 사용자 설정 (MVP 는 YAML 로 대체 가능)

**상태 전이**

```
NEW ──stale(72h)──▶ DROPPED
NEW ──중복/exclude──▶ FILTERED_OUT
NEW ──관문 통과──▶ (선별 배치: 관련도) ──▶ (점수) ──미달──▶ DROPPED
                                              └─통과──▶ (판정) ──false──▶ DROPPED
                                                              └─true──▶ SCORED ──상한/무음──▶ QUEUED
                                                                               └─발송──▶ SENT / FAILED
```

`FILTERED_OUT` 과 `DROPPED` 는 서로 다른 종단 분기다. 재처리 대상은 `NEW` 뿐이며, 선별·판정 예산이 바닥나면 항목은 `NEW` 로 남고 선별 결과는 `decisions` 에서 재사용된다.

**발송 강도** — `importance ≥ 4 → push`, `3 → silent`, `≤ 2 → feed`(발송 안 함). 하루 push 상한·무음 시간(23:00~08:00 KST)은 `notify/policy.py` 에서 처리.

---



## Conventions

- **브랜치** — 새 브랜치의 이름은 `feat-`* / `fix-*` / `refactor-*` (또는 `feat/*` 형식)
- **커밋 접두사** — `feat:` `fix:` `hotfix:` `refactor:` `docs:` `test:` `chore:` `perf:`
- **배포** — GitHub Actions. push 시 `ruff → mypy → pytest`, `main` 머지 시 이미지 빌드 → GHCR 푸시 → VM 에 SSH 로 `docker compose pull && up -d`. Alembic 마이그레이션은 컨테이너 시작 시 자동 실행.
- **시크릿** — `.env` 로컬 관리 (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`(또는 `OPENAI_API_KEY`), `DISCORD_*`, `TELEGRAM_*`, `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `DATABASE_URL`). 커밋 금지. `.env.example` 이 안전한 참조본.
- **임베딩** — Voyage `voyage-3.5-lite` 1024차원 고정. 무료 등급은 분당 요청 3회·토큰 약 1만이라 배치 64건·간격 20초. 모델을 바꾸면 `backfill_embeddings.py` 로 전량 재계산하고, 불일치 행이 남아 있는 동안 파이프라인은 스스로 멈춘다.
- **설정 분리** — 소스·키워드·임계값은 `config/*.yaml`, 시크릿은 `.env`. 코드에 하드코딩하지 않는다.
- **소스 family** — `sources.yaml` 의 `config.family` 가 같은 소스(arXiv 두 피드)는 적재 병합에서 같은 소스로 본다. 교차 등재가 멘션·multi 신호를 만들지 않는다.
- **본문 보강 가드** — `pipeline/llm.py` 의 `enrich_body` 는 사설·루프백·링크로컬 주소와 그리로 가는 리다이렉트(최대 5홉)를 열지 않는다. DNS 리바인딩은 막지 않는다.
- **Neon 연결** — pooled 엔드포인트(pgbouncer, `sslmode=require`) 사용, 잡 단위로 커넥션을 열고 닫는다. 브랜치 `main`(운영) / `dev`(로컬·CI).
- **LLM 호출 위치** — 선별은 `pipeline/triage.py`(25건 배치, 관문 통과 항목 전부), 판정은 점수 관문을 통과한 항목에만 `pipeline/llm.py`. 모든 호출 직전에 `db/budget.py` 의 `reserve_call` 로 예약한다(선별 60·판정 300·탐색 3, Asia/Seoul 달력일). 결과는 `summaries`·`decisions` 캐시.
- **결정 로그** — 통과/탈락 판단은 반드시 `decisions` 에 남긴다 (매칭 키워드, 점수 내역, LLM 응답).

---



## 작업 기록 규칙 (Obsidian)

작업 단위의 **커밋 → Codex 리뷰(지적 반영·재커밋 포함)가 모두 끝난 뒤**, 최종 상태를 옵시디언 MCP 로 여태호 저장소의 **`여태호-project/` 폴더**에 **1회 기록**한다. 프로젝트 노트와 일일 노트 두 갈래로 남긴다.

- **자동 기록** — 사전 허락 없이 자동으로 기록하되, 기록 후 작성한 노트 경로를 보고한다.
- **경로 직접 쓰기** — 빈 폴더는 vault 목록에 나타나지 않으므로(REST API 가 파일 기준으로 인덱싱) 폴더를 탐색하지 말고 아래 정해진 경로에 `vault_write` 로 직접 작성한다. `여태호-project/` 하위 폴더가 루트 목록에 안 보여도 정상.
- **서비스명** — 이 레포는 단일 서비스이므로 서비스명은 **`기술파악`** 으로 고정한다. 모듈(`sources/`, `pipeline/`, `notify/`, `api/` 등)은 서비스가 아니라 기능 노트의 단위로 다룬다.



### 작성 스타일 — 학습노트 양식 준수

`학습노트/` 노트들과 같은 스타일로 쓴다. **불릿 하나에 긴 문장들을 대시로 이어붙이는 방식 금지.**

- **frontmatter** — `tags` 와 `created` (프로젝트 노트는 `updated` 추가).
- **맨 위** `> [!summary] 한 줄 요약` **콜아웃** — 노트 전체를 한두 문장으로.
- **H2 섹션으로 분리** — 항목당 짧은 문단 2~4줄. 서술이 길면 문단을 나누거나 소제목을 단다.
- **열거 사실은 표** (커밋·파일·타임라인), **흐름·구조는 코드블록**, **핵심 수치·결론은 굵게** (예: **5,004ms → 6ms**).
- `[[링크]]` **적극 사용** — 관련 프로젝트/일일 노트뿐 아니라 관련 학습노트(예: [[파이썬 웹 서버 실행 구조]])도 연결.



### ① 프로젝트 노트 — `여태호-project/프로젝트/<서비스명>-Hub/` (허브 + spoke)

```
여태호-project/프로젝트/기술파악-Hub/
├── 기술파악.md                            ← 허브
└── spoke/
    ├── <기능명>.md                        ← 기능 노트 (예: GitHub Releases 수집기, 텔레그램 발송)
    ├── 기술파악 - 폴더·파일 역할 지도.md     ← 상세 문서 4종
    ├── 기술파악 - 런타임 플로우.md
    ├── 기술파악 - 파일·함수 레퍼런스.md
    └── 기술파악 - 결정 기록.md
```

- **허브 노트** `<서비스명>.md` — 서비스 개요 + 기능별 현황 표 + spoke 노트 링크만. 상세 내용을 담지 않고 항상 짧게 유지한다.
- **기능 노트** `spoke/<기능명>.md` — 실제 작업 내용. **독립된 과제·기능 단위일 때만 생성**한다. 한두 커밋짜리 잔수정은 노트를 새로 만들지 않고 기존 기능 노트와 허브 표만 갱신한다.
- **상세 문서 4종** `spoke/<서비스명> - *.md` — 진행 상황이 아니라 **참조 정보**를 다루는 문서. 서비스 코드를 본격적으로 다루게 되면 작성하고, 관련 내용이 바뀌는 작업을 기록할 때 함께 갱신한다.
  - **폴더·파일 역할 지도** — 모듈 전체 폴더·파일이 무슨 역할인지 + 역인덱스("이걸 고치려면 어디를 보나")
  - **런타임 플로우** — 실행 생애 주기를 단계별로 + 예외 경로·동시성
  - **파일·함수 레퍼런스** — 파일 지도(전용/공용/재사용 자산) · 호출 체인 · 파일별 심볼 · 손댈 때 규칙·함정
  - **결정 기록** — 확정된 설계·운영 결정과 **기각한 대안·이유**. 특히 "하지 않기로 한 것"을 반드시 남긴다(같은 조사를 반복하지 않기 위해). 결정이 뒤집히면 해당 행을 갱신하고 경위는 일일 노트로. 구현도 2.2절·10장의 결정(Postgres 를 큐로, APScheduler, Neon, pg_trgm 우선, WaterCrawl 보류 등)을 초기 내용으로 옮겨 둔다.
- **있으면** — 작성돼 있는 양식에 맞춰 업데이트. 의미 없어졌거나 충돌하는 이전 내용은 **덮어쓴다**(이력 보존은 일일 노트 담당). 덮어쓰기는 해당 노트 안에서만 — 다른 노트를 침범하지 않는다. `updated` 를 업데이트한 날짜로 수정.

**허브 노트 양식**

```markdown
---
tags: [여태호, 프로젝트, <서비스명>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <서비스명>

> [!summary] 한 줄 요약
> 무슨 서비스이고 지금 주력 작업이 무엇인지 한두 문장.

## 서비스 개요

무슨 서비스인지, 코드 위치(백엔드·프론트)를 짧은 문단으로.

## 기능 현황

| 기능 (과제) | 상태 | 노트 |
|---|---|---|
| <기능명> | 진행 중 / 완료 / 미착수 | [[<기능명>]] |

## 상세 문서

- [[<서비스명> - 폴더·파일 역할 지도]]
- [[<서비스명> - 런타임 플로우]]
- [[<서비스명> - 파일·함수 레퍼런스]]
- [[<서비스명> - 결정 기록]]
```

**기능 노트 양식**

```markdown
---
tags: [여태호, 프로젝트, <서비스명>, <기능명>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <기능명>

> [!summary] 한 줄 요약
> 이 기능 작업이 무엇이고 지금 어떤 상태인지. 서비스: [[<서비스명>]]

## 무엇을 했나

무엇을 수정·추가했는지. 항목이 많으면 표나 목록으로 나눈다.

## 무엇이 달라졌나

이로 인한 변화·효과. 핵심 수치는 **굵게**.

## 왜

수정·추가한 배경·트리거를 짧은 문단으로.

## 어디

| 구분 | 내용 |
|---|---|
| 브랜치 | `feat/...` (`해시`..`해시`) |
| 핵심 파일 | `경로` |

## 추후 작업

- [ ] 남은 TODO (체크박스 목록)

## 일일 기록

- [[<서비스명> - <작업 제목>]]   ← 최신이 위
```



### ② 일일 노트 — `여태호-project/일일작업내역/YYYY-MM-DD(N일차)/<서비스명> - <작업 제목>.md`

- 항상 **새 파일로 추가**한다. 기존 일일 노트는 업데이트하지 않는다. 날짜는 기록 시점 기준.
- 해당 날짜 폴더가 없으면 `여태호-project/일일작업내역/` 안의 기존 폴더 중 최대 일차 +1 로 자동 생성 (예: `2026-09-01(2일차)`). 폴더가 하나도 없으면 `1일차` 부터 시작한다. `아사달/일일작업내역/` 의 일차와는 별개로 센다.
- 본문에 해당 `[[<기능명>]]` 링크를 넣어 기능 노트와 양방향으로 연결한다(해당 기능 노트가 없는 잔수정은 `[[<서비스명>]]` 허브로).

```markdown
---
tags: [여태호, 일일작업, <서비스명>]
created: YYYY-MM-DD
---

# <작업 제목>

> [!summary] 한 줄 요약
> 무엇을 했고 결과가 무엇인지 한 문장. 기능: [[<기능명>]]

## 무슨 작업

무엇을 했는지 짧은 문단으로. 결과 수치는 **굵게**.

## 왜

배경·트리거. 원인 분석이 길면 문단을 나누거나 코드블록을 활용한다.

## 어디

| 커밋 | 내용 | 파일 |
|---|---|---|
| `해시` | 한 줄 설명 | `경로` |

## 검증

실행한 테스트·결과 (`pytest`). 근거가 여럿이면 목록으로.
```



## Codex 리뷰 규칙

계획·구현·수정 작업을 논리적 단위로 마치고 **커밋한 뒤**, 턴을 끝내기 전에 Codex 리뷰를 최종 게이트로 실행한다.

- **언제** — 각 작업 단위(기능·수정·리팩터) 커밋 직후, 완료를 선언하기 전. 여러 커밋이 쌓였으면 마지막에 한 번 범위 리뷰.
- **어떻게** — `/codex:review` 슬래시 커맨드로 실행한다(내부적으로 codex-companion `review`).
  - 미커밋 변경 = working-tree 기본. **이미 커밋한 분** = `--base <직전 ref> --scope branch` 로 커밋 범위 리뷰.
  - 규모: 1~2파일 소규모 → foreground(`--wait`). 그 이상·불확실 → background.
  - 커스텀·적대적 관점이 필요하면 `/codex:adversarial-review`.
- **원칙** — 리뷰는 **read-only**. 지적사항을 무비판 수용하지 말고 실제 결함인지 별도 판단 후 반영한다([receiving-code-review 태도]). **Critical/Important** 는 조치 후 **재리뷰**, **Minor** 는 트리아지(즉시 vs 후속).
- **자동화(선택)** — `/codex:setup --enable-review-gate` 로 stop-time 리뷰 게이트를 켜면 턴 종료 전 자동으로 직전 변경을 리뷰한다.
