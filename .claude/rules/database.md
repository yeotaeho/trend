---
paths:
  - "app/db/**"
  - "alembic.ini"
  - "scripts/backfill_embeddings.py"
  - "tests/integration/**"
---

# DB 규칙

- **Neon 이 단일 진실 원천** — 큐도 `items.status` + `FOR UPDATE SKIP LOCKED` 로 Postgres 가 맡는다. Redis·MQ 를 추가하지 않는다.
- **연결** — SQLAlchemy 2.x async + asyncpg, `statement_cache_size=0`. pooled 엔드포인트(pgbouncer, `sslmode=require`). 잡 단위로 커넥션을 열고 닫는다. 브랜치는 `main`(운영) / `dev`(로컬·CI).
- **모델 변경 → Alembic** — `uv run alembic revision --autogenerate -m "..."` 로 리비전을 만들고 생성된 파일을 읽어 확인한다. 컨테이너 시작 시 `upgrade head` 가 자동 실행되므로 데이터가 사라지는 마이그레이션은 쓰지 않는다.
- **Vector 컬럼** — `db/types.py` 는 쓰기 전용. 벡터 비교(코사인)는 SQL 에서만 한다.
- **예약 행** — `budget.py` 의 `reserve_call` 은 독립 트랜잭션 + 단일 키 자문 잠금. 일일 상한의 오늘은 Asia/Seoul 달력일이다.
- **통합 테스트** — pgvector 쿼리·예약 원자성은 `tests/integration/` 에서 `TEST_DATABASE_URL`(Neon dev 브랜치)로 검증한다. 운영 브랜치를 가리키지 않는다.
- 테이블·컬럼을 바꾸면 `docs/database.md` 를 같이 고친다.
