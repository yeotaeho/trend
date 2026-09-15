# 데이터 모델

Neon(Postgres 16/17, pgvector)이 모든 상태의 단일 진실 원천이다. 큐도 `items.status` + `FOR UPDATE SKIP LOCKED` 로 Postgres 가 맡는다. 모델은 `app/db/models.py`, 마이그레이션은 `app/db/alembic/`.

## 테이블

| 테이블 | 역할 | 주요 컬럼 |
|---|---|---|
| `sources` | 수집 소스 정의 | `type`, `config` jsonb(family 등), `poll_interval_sec`, `trust_score`, `last_polled_at`, `last_error` |
| `items` | 정규화된 항목 (핵심) | `url_hash` unique, `category`, `kind`, `cluster_id`, `status`, `raw`(metrics·mentions), `embedding vector(1024)`, `embedding_model` |
| `decisions` | 항목별 판단 기록 — 튜닝 근거 | `stage` rule / triage / score / llm, `passed`, `score`, `details` jsonb |
| `llm_calls` | LLM 호출 직전 예약 행 — 일일 상한은 이 표로 센다 | `kind` triage / judge / explore, `batch_id`, `called_at` |
| `summaries` | LLM 결과 캐시 | `title_ko`, `summary_ko`, `tags`, `importance` 1~5, `worth_notifying`, 토큰 수 |
| `notifications` | 발송 기록 | `channel`, `level` push / silent / feed, `message_id`, `error` |
| `feedback` | 사용자 반응, 항목당 1건 | `verdict` useful / useless (재클릭은 upsert) |
| `user_prefs` | 단일 사용자 설정 | MVP 는 YAML 로 대체 가능 |

`items.status` 값과 전이는 `docs/pipeline.md` 의 상태 전이 참고.

## 임베딩

- `items.embedding` 은 적재 시점 텍스트로 계산한 Voyage `voyage-3.5-lite` **1024차원** 고정. 파이썬에서 읽지 않고 코사인 비교는 SQL 에서 한다.
- `db/types.py` 의 Vector 타입은 쓰기 전용.
- 모델을 바꾸면 `scripts/backfill_embeddings.py` 로 전량 재계산한다(멱등). `embedding_model` 불일치 행이 남아 있는 동안 파이프라인은 스스로 멈춘다.
- Voyage 무료 등급은 분당 요청 3회·토큰 약 1만이라 배치 64건·간격 20초.

## 연결

- SQLAlchemy 2.x async + asyncpg, `statement_cache_size=0` (pgbouncer 호환).
- pooled 엔드포인트(`sslmode=require`). 잡 단위로 커넥션을 열고 닫는다.
- 브랜치 `main`(운영) / `dev`(로컬·CI). 통합 테스트는 `TEST_DATABASE_URL` 로 dev 를 가리킨다.

## 마이그레이션

```bash
uv run alembic revision --autogenerate -m "<메시지>"   # 생성 파일을 읽어 확인
uv run alembic upgrade head                            # 컨테이너 시작 시 자동 실행
```

컨테이너가 뜰 때 자동 적용되므로 데이터가 사라지는 마이그레이션은 쓰지 않는다.
