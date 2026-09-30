---
description: 테이블·컬럼·마이그레이션을 바꿀 때, Neon 연결·잠금·SKIP LOCKED·savepoint 오류(MissingGreenlet 등)를 볼 때, pgvector·예약 원자성 통합 테스트를 돌릴 때.
paths:
  - "app/db/**"
  - "alembic.ini"
  - "scripts/backfill_embeddings.py"
  - "tests/integration/**"
---

# DB 규칙

- **Neon 이 단일 진실 원천** — 큐도 `items.status` + `FOR UPDATE SKIP LOCKED` 로 Postgres 가 맡는다. Redis·MQ 를 추가하지 않는다.
- **연결** — SQLAlchemy 2.x async + asyncpg, `statement_cache_size=0`. pooled 엔드포인트(pgbouncer, `sslmode=require`). 잡 단위로 커넥션을 열고 닫는다. 브랜치는 `main`(운영) / `dev`(로컬 실험·통합 테스트). CI 는 통합 테스트를 돌리지 않는다.
- **모델 변경 → Alembic** — `uv run alembic revision --autogenerate -m "..."` 로 리비전을 만들고 생성된 파일을 읽어 확인한다. 컨테이너 시작 시 `upgrade head` 가 자동 실행되므로 데이터가 사라지는 마이그레이션은 쓰지 않는다.
- **Vector 컬럼** — `db/types.py` 는 쓰기 전용. 벡터 비교(코사인)는 SQL 에서만 한다.
- **예약 행** — `budget.py` 의 `reserve_call` 은 독립 트랜잭션 + 단일 키 자문 잠금. 일일 상한의 오늘은 Asia/Seoul 달력일이다.
- **통합 테스트** — pgvector 쿼리·예약 원자성은 `tests/integration/` 에서 `TEST_DATABASE_URL`(Neon dev 브랜치)로 검증한다. 운영 브랜치를 가리키지 않는다.
- 테이블·컬럼을 바꾸면 `docs/database.md` 를 같이 고친다.

## 세션에서 배운 것

- **savepoint 롤백은 그 안에서 수정된 객체를 만료시킨다.** 롤백 뒤 `except`·로그에서 `item.id` 를 읽으면 async 세션이 동기 로드를 시도해 `MissingGreenlet` 으로 배치가 멈춘다. id 는 savepoint 에 들어가기 전에 변수로 빼 둔다. deferred 벡터 컬럼을 파이썬에서 읽어도 같은 오류가 난다.
- **여러 행을 잠근 뒤 루프에서 커밋하지 않는다.** 첫 커밋에 나머지 잠금이 풀린다. 발송은 `_claim_one` 으로 한 건씩 잠그고 커밋한다. 파이프라인이 잠근 행을 수집 잡이 기다리지 않도록 적재 병합은 `SKIP LOCKED` 로 다음 폴링에 미룬다.
- **처음엔 없는 행을 잠그지 않는다.** 첫 저장 전의 `user_prefs` 행을 잠그면 동시 첫 저장이 유실된다. 항상 있는 `users` 행을 `FOR NO KEY UPDATE` 로 잠근다(FK 삽입의 KEY SHARE 와 부딪치지 않는다, `db/prefs.py`).
- **문자열 컬럼 폭을 새 값으로 확인한다.** 외부 문자열은 `text` 다. 짧은 코드값 컬럼도 새 값 길이를 본다. `notifications.level` 에 `cluster_dup`(11자)이 안 들어간 전례가 있다.
- **아직 main 에 나가지 않은 리비전은** 새 리비전을 쌓지 말고 그 리비전을 고친다. 병렬 작업 중에는 리비전을 한 작업에만 둔다.
- **테스트가 운영 DB 를 보지 않게 하는 가드를 지우지 않는다.** `tests/conftest.py` 는 셸의 `DATABASE_URL` 보다 `TEST_DATABASE_URL` 을 우선한다. 통합 테스트 전에 `TEST_DATABASE_URL` 이 운영 엔드포인트와 다른지 대조한다.
- 상관 서브쿼리가 자동 상관으로 FROM 을 잃으면 `aliased(...)` 와 `correlate(Item)` 을 쓴다.
