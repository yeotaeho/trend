# -*- coding: utf-8 -*-
import json, math, os

imports = json.load(open('.ua/tmp/ua-file-analyzer-input-1.json', encoding='utf-8'))['batchImportData']

nodes = []
edges = []


def F(path, name, summary, tags, complexity, notes=None):
    n = {"id": "file:" + path, "type": "file", "name": name, "filePath": path,
         "summary": summary, "tags": tags, "complexity": complexity}
    if notes:
        n["languageNotes"] = notes
    nodes.append(n)


def FN(path, name, lo, hi, summary, tags, complexity, kind="function"):
    nid = "%s:%s:%s" % (kind, path, name)
    nodes.append({"id": nid, "type": kind, "name": name, "filePath": path,
                  "lineRange": [lo, hi], "summary": summary, "tags": tags,
                  "complexity": complexity})
    edges.append({"source": "file:" + path, "target": nid,
                  "type": "contains", "direction": "forward", "weight": 1.0})


def E(s, t, ty, w):
    edges.append({"source": s, "target": t, "type": ty, "direction": "forward", "weight": w})


# ---------- file nodes ----------
F("app/api/__init__.py", "__init__.py",
  "app/api 패키지 마커. 내용이 없고 웹훅·헬스체크 라우터 모듈들을 하나의 패키지로 묶는 역할만 한다.",
  ["entry-point", "barrel", "package-marker", "api"], "simple")

F("app/api/discord.py", "discord.py",
  "디스코드 Interactions 엔드포인트. Ed25519 서명을 검증한 뒤 PING 확인 요청에 응답하고, 👍/👎 버튼 콜백을 feedback 테이블에 기록한다.",
  ["api-handler", "webhook", "security", "feedback", "validation"], "moderate",
  "3초 응답 제한 때문에 별도 API 호출 없이 응답 본문(ephemeral flag)으로 즉시 답한다.")

F("app/api/github.py", "github.py",
  "GitHub release 웹훅 수신 라우터. HMAC-SHA256 서명을 검증하고 published/released 액션만 골라 즉시 items 에 적재한다.",
  ["api-handler", "webhook", "security", "ingestion", "github"], "moderate")

F("app/api/health.py", "health.py",
  "헬스체크 엔드포인트. DB 왕복(SELECT 1)까지 확인해야 ok 를 돌려준다.",
  ["api-handler", "health-check", "monitoring", "database"], "simple")

F("app/api/telegram.py", "telegram.py",
  "텔레그램 봇 웹훅. secret token 을 상수 시간 비교로 검증하고 인라인 버튼 콜백을 feedback 으로 upsert 한다.",
  ["api-handler", "webhook", "feedback", "security", "telegram"], "moderate",
  "토스트 응답 실패로 500 을 돌려주면 텔레그램이 재전달해 피드백이 중복되므로 예외를 삼킨다.")

F("app/db/alembic/env.py", "env.py",
  "Alembic 마이그레이션 실행 환경. 자체 엔진을 만들지 않고 app.db.session 의 async 엔진과 모델 메타데이터를 그대로 쓴다.",
  ["migration", "database", "configuration", "alembic"], "simple",
  "asyncpg async 엔진이라 run_sync 로 동기 마이그레이션 컨텍스트를 감싼다.")

F("app/db/feedback.py", "feedback.py",
  "사용자 피드백 저장 헬퍼. ON CONFLICT DO UPDATE 로 항목당 1건을 보장하고, 다시 누르면 판정과 시각을 덮어쓴다.",
  ["data-model", "database", "upsert", "feedback"], "simple",
  "PostgreSQL 전용 insert().on_conflict_do_update 를 unique constraint 이름으로 지정한다.")

F("app/db/session.py", "session.py",
  "Neon pooled 엔드포인트용 async 엔진과 잡 단위 세션 컨텍스트. libpq 전용 파라미터를 걷어내고 asyncpg 연결 인자를 직접 조립한다.",
  ["database", "session", "configuration", "async", "utility"], "moderate",
  "pgbouncer 는 prepared statement 를 지원하지 않아 statement_cache_size 를 0 으로 두고, SSL 컨텍스트를 직접 만들어 asyncpg 의 root.crt 경로 탐색을 우회한다.")

F("app/jobs/collect.py", "collect.py",
  "소스 하나를 폴링해 신규 항목을 적재하는 수집 잡. 적재 실패는 savepoint 로 감싸 실패 카운트를 남기고, 연속 5회 실패 시 운영 알림을 보낸다.",
  ["job", "scheduler", "ingestion", "error-handling", "orchestration"], "complex",
  "savepoint(begin_nested) 로 감싸야 예외 뒤에도 세션이 살아 실패 기록을 커밋할 수 있다.")

F("app/jobs/scheduler.py", "scheduler.py",
  "APScheduler 부트스트랩. config/sources.yaml 을 DB 에 동기화한 뒤 소스별 폴링 잡과 파이프라인·발송 잡을 등록한다.",
  ["scheduler", "job", "configuration", "orchestration"], "moderate",
  "YAML 이 단일 진실 원천이라 YAML 에서 빠진 소스는 삭제 대신 비활성화한다.")

F("app/log.py", "log.py",
  "structlog JSON 로깅 설정. docker logs 로 그대로 흘리기 위해 표준 로깅에 JSONRenderer 를 얹는다.",
  ["logging", "configuration", "utility", "observability"], "simple")

F("app/main.py", "main.py",
  "FastAPI 엔트리 포인트. 헬스체크·웹훅 라우터를 등록하고 lifespan 에서 같은 프로세스에 APScheduler 를 띄웠다가 종료 시 정리한다.",
  ["entry-point", "api", "lifecycle", "scheduler"], "simple",
  "asynccontextmanager 기반 lifespan 으로 스케줄러 기동·종료와 엔진 dispose 를 한곳에서 처리한다.")

F("app/pipeline/embedding.py", "embedding.py",
  "임베딩 어댑터. Voyage/OpenAI 요청을 제공자별로 조립하고 429·5xx 재시도, 차원·index 검증, 미계산 항목 배치 채우기를 담당한다.",
  ["pipeline", "embedding", "http-client", "retry", "validation"], "complex",
  "무료 등급 RPM 제한 때문에 배치 64건 상한과 Retry-After 우선 백오프를 쓰고, 차원 오류는 설정 오류로 보아 None 대신 예외로 드러낸다.")

F("app/pipeline/ingest.py", "ingest.py",
  "정규화 항목 적재. url_hash 기준 ON CONFLICT DO NOTHING 으로 중복을 조용히 건너뛰고 새 항목 id 만 돌려준다.",
  ["pipeline", "ingestion", "database", "deduplication", "validation"], "moderate",
  "배치 안 중복까지 미리 걸러야 한 문장에서 ON CONFLICT 가 두 번 터지지 않는다.")

F("scripts/backfill_embeddings.py", "backfill_embeddings.py",
  "임베딩 백필 스크립트. NULL 이거나 모델이 바뀐 행을 배치 단위로 재계산하며, 멱등이라 중단 후 재실행할 수 있다.",
  ["script", "backfill", "embedding", "maintenance", "cli"], "moderate",
  "무료 등급 3 RPM 을 피하려 배치 사이 20초를 쉬고, 연속 5회 실패면 중단한다.")

F("scripts/calibrate_dedupe.py", "calibrate_dedupe.py",
  "중복 임계값 보정 스크립트. 최근 7일 항목 쌍을 코사인 유사도 구간별로 10개씩 뽑아 보여주고, 그 표본을 보고 rules.yaml 값을 정한다.",
  ["script", "cli", "tuning", "deduplication", "analysis"], "simple",
  "pgvector 의 <=> 연산자를 raw SQL 로 직접 써 유사도 구간 표본을 추출한다.")

F("scripts/run_job.py", "run_job.py",
  "잡 수동 실행 CLI. 스케줄러 없이 sync·collect·pipeline·notify 를 인자 순서대로 한 번씩 돌린다.",
  ["script", "cli", "job", "entry-point", "debugging"], "simple")

F("tests/test_embedding.py", "test_embedding.py",
  "임베딩 어댑터 단위 테스트. respx 로 HTTP 를 모킹해 텍스트 조립, 순서 보존, 차원·index 검증, 429/5xx 재시도와 대기 시간을 검증한다.",
  ["test", "unit-test", "embedding", "http-mocking", "retry"], "complex")

F("tests/test_feedback_upsert.py", "test_feedback_upsert.py",
  "피드백 upsert 문 단위 테스트. 재클릭 시 verdict 와 created_at 을 덮어쓰는 SET 절이 만들어지는지 확인한다.",
  ["test", "unit-test", "database", "feedback"], "simple")

F("tests/test_ingest.py", "test_ingest.py",
  "적재 URL 스킴 가드 테스트. http/https 만 통과하고 javascript:·data: 는 막히는지 확인한다.",
  ["test", "unit-test", "security", "validation"], "simple")

F("tests/test_session_url.py", "test_session_url.py",
  "DB 연결 문자열 변환 테스트. asyncpg 접두사 재작성, libpq 전용 파라미터 제거, TLS 판정과 연결 인자 조립을 검증한다.",
  ["test", "unit-test", "database", "configuration"], "moderate")

# ---------- function / class nodes ----------
p = "app/api/discord.py"
FN(p, "verify_signature", 30, 38, "Discord 가 보낸 요청인지 Ed25519 로 검증한다. 메시지는 timestamp 와 원문 바디를 이어붙인 값이다.", ["security", "validation", "signature", "webhook"], "simple")
FN(p, "discord_interaction", 46, 79, "디스코드 인터랙션 POST 핸들러. 서명 검증 실패는 401, PING 은 PONG, 컴포넌트 콜백은 피드백 upsert 후 ephemeral 답장을 돌려준다.", ["api-handler", "event-handler", "feedback", "webhook"], "moderate")

p = "app/api/github.py"
FN(p, "verify_signature", 22, 27, "GitHub 웹훅 서명(X-Hub-Signature-256)을 HMAC-SHA256 으로 계산해 상수 시간 비교한다.", ["security", "validation", "signature", "hmac"], "simple")
FN(p, "github_webhook", 31, 68, "release 웹훅 핸들러. 서명·이벤트·액션을 차례로 거르고 활성 github_release 소스를 찾아 릴리즈를 items 로 적재한다.", ["api-handler", "webhook", "ingestion", "github"], "moderate")

p = "app/api/health.py"
FN(p, "health", 14, 17, "헬스체크 핸들러. 세션을 열어 SELECT 1 을 돌려 DB 왕복까지 확인한 뒤 ok 를 반환한다.", ["health-check", "api-handler", "monitoring"], "simple")

p = "app/api/telegram.py"
FN(p, "telegram_webhook", 23, 51, "텔레그램 업데이트 핸들러. secret token 검증 후 callback_query 를 파싱해 피드백을 저장하고 토스트 응답을 보낸다.", ["api-handler", "webhook", "feedback", "telegram"], "moderate")

p = "app/db/alembic/env.py"
FN(p, "run_migrations_offline", 17, 25, "오프라인 모드 마이그레이션. 엔진 URL 문자열만 써서 SQL 을 literal bind 로 생성한다.", ["migration", "alembic", "database"], "simple")
FN(p, "run_migrations_online", 34, 37, "온라인 모드 마이그레이션. async 엔진으로 연결을 열고 run_sync 로 동기 마이그레이션을 실행한 뒤 엔진을 정리한다.", ["migration", "alembic", "async", "database"], "simple")

p = "app/db/feedback.py"
FN(p, "feedback_upsert_stmt", 12, 17, "피드백 INSERT ... ON CONFLICT DO UPDATE 문을 만든다. uq_feedback_item_id 충돌 시 verdict 와 created_at 을 갱신한다.", ["database", "upsert", "query-builder"], "simple")
FN(p, "upsert_feedback", 20, 21, "만들어진 upsert 문을 세션으로 실행하는 얇은 래퍼. 웹훅 핸들러들이 공통으로 호출한다.", ["database", "feedback", "utility"], "simple")

p = "app/db/session.py"
FN(p, "to_asyncpg_url", 21, 32, "psql 연결 문자열을 postgresql+asyncpg 형식으로 바꾸고 asyncpg 가 모르는 libpq 전용 쿼리 파라미터를 제거한다.", ["database", "url-parsing", "configuration", "utility"], "moderate")
FN(p, "requires_tls", 35, 36, "URL 의 sslmode 가 require/verify-ca/verify-full 인지 판정한다.", ["database", "tls", "utility"], "simple")
FN(p, "connect_args", 39, 50, "asyncpg 연결 인자를 조립한다. pgbouncer 대응으로 statement 캐시를 끄고, TLS 가 필요하면 기본 SSL 컨텍스트를 직접 만든다.", ["database", "tls", "configuration", "connection"], "moderate")
FN(p, "session_scope", 61, 69, "잡 하나 = 세션 하나 컨텍스트 매니저. 정상 종료 시 커밋하고 예외면 롤백 후 다시 던진다.", ["database", "session", "context-manager", "transaction"], "simple")

p = "app/jobs/collect.py"
FN(p, "run_source", 22, 80, "소스 하나를 폴링해 적재하고 새 항목 임베딩까지 시도한다. 수집·적재 실패는 fail_count·last_error 로 기록하고 임계치에서 운영 알림을 보낸다.", ["job", "ingestion", "error-handling", "orchestration"], "complex")
FN(p, "run_all_sources", 83, 92, "수동 실행·백필용. 활성 소스 id 를 모아 순서대로 run_source 를 한 번씩 돌리고 총 적재 수를 돌려준다.", ["job", "batch", "orchestration"], "simple")

p = "app/jobs/scheduler.py"
FN(p, "sync_sources", 21, 43, "config/sources.yaml 을 sources 테이블에 반영한다. 이름이 같으면 갱신, YAML 에서 빠진 소스는 비활성화하고 활성 목록을 돌려준다.", ["configuration", "database", "synchronization", "scheduler"], "moderate")
FN(p, "start_scheduler", 46, 66, "AsyncIOScheduler 를 만들어 소스별 폴링 잡과 파이프라인·발송 인터벌 잡을 등록하고 기동한다.", ["scheduler", "job", "bootstrap", "orchestration"], "moderate")

p = "app/log.py"
FN(p, "configure_logging", 12, 25, "설정의 로그 레벨을 읽어 표준 로깅과 structlog 프로세서 체인(타임스탬프·예외·JSON 렌더러)을 구성한다.", ["logging", "configuration", "bootstrap"], "simple")
FN(p, "get_logger", 28, 29, "모듈 이름으로 바인딩된 structlog 로거를 돌려주는 한 줄 헬퍼.", ["logging", "utility"], "simple")

p = "app/main.py"
FN(p, "lifespan", 20, 28, "FastAPI lifespan 컨텍스트. 기동 시 로깅을 구성하고 설정에 따라 스케줄러를 띄우며, 종료 시 스케줄러를 내리고 DB 엔진을 dispose 한다.", ["lifecycle", "bootstrap", "scheduler", "cleanup"], "simple")

p = "app/pipeline/embedding.py"
FN(p, "EmbeddingDimError", 33, 34, "응답 차원·개수·index 가 요청과 어긋났을 때의 예외. 장애가 아니라 설정 오류라 None 으로 숨기지 않고 위로 던진다.", ["exception", "validation", "embedding"], "simple", kind="class")
FN(p, "embedding_text", 37, 40, "제목과 본문 앞 300자를 이어 임베딩 입력 텍스트를 만든다. 적재 시점에 한 번만 만들어 벡터 비교의 재료를 고정한다.", ["embedding", "text-processing", "utility"], "simple")
FN(p, "needs_embedding", 43, 46, "임베딩이 NULL 이거나 모델이 현재 설정과 다른 행을 고르는 SQL 조건을 만든다. NULL 을 놓치지 않도록 is_distinct_from 을 쓴다.", ["embedding", "query-builder", "database"], "simple")
FN(p, "_request", 49, 67, "제공자(voyage/openai)에 따라 임베딩 API 의 url·헤더·요청 바디를 조립한다.", ["embedding", "http-client", "adapter"], "simple")
FN(p, "_retry_wait", 70, 77, "재시도 대기 시간을 계산한다. Retry-After 헤더가 우선이고, 없으면 429 는 분 단위 창, 5xx 는 시도 번호에 비례한 대기를 쓴다.", ["retry", "rate-limit", "http-client"], "simple")
FN(p, "_parse_vectors", 80, 90, "응답 데이터의 index 가 0..n-1 인지, 각 벡터 차원이 1024 인지 검증하고 요청 순서대로 정렬해 돌려준다.", ["validation", "embedding", "parsing"], "moderate")
FN(p, "embed", 93, 119, "텍스트 배치를 임베딩 API 로 보내 순서대로 벡터를 받는다. 전송 오류·5xx·429 만 재시도하고 최종 실패는 None 이다.", ["embedding", "http-client", "retry", "async"], "complex")
FN(p, "alert_dim_error", 122, 132, "차원 오류를 로그에 남기고 운영 채널에 알린다. 설정 오류라 매 잡마다 나므로 프로세스당 한 번만 보낸다.", ["alerting", "error-handling", "embedding"], "simple")
FN(p, "embed_pending", 135, 164, "미계산·모델 불일치 항목을 최대 배치 크기만큼 골라 임베딩을 계산·저장한다. 실패하면 NULL 로 남겨 다음 잡이 재시도하게 한다.", ["embedding", "batch", "database", "pipeline"], "complex")

p = "app/pipeline/ingest.py"
FN(p, "is_web_url", 17, 23, "http/https 스킴만 통과시키는 URL 가드. 모든 수집 경로가 store_items 를 지나므로 이 한 곳에서 javascript:·data: 를 막는다.", ["security", "validation", "url"], "simple")
FN(p, "to_row", 26, 41, "NormalizedItem 을 items 테이블 행 딕셔너리로 바꾼다. URL 정규화·해시, 본문 3000자 절단, 기본 카테고리·상태를 채운다.", ["serialization", "data-model", "normalization"], "moderate")
FN(p, "store_items", 44, 65, "정규화 항목들을 url_hash 기준으로 중복 없이 INSERT 한다. 배치 내 중복도 미리 걸러내고 새로 들어간 id 목록만 돌려준다.", ["ingestion", "database", "deduplication", "async"], "moderate")

FN("scripts/backfill_embeddings.py", "main", 20, 64, "임베딩 백필 루프. 남은 대상 수를 세고 배치마다 embed_pending 을 돌리며, 배치 실패 시 한 창을 쉬고 재시도하다 연속 5회면 중단한다.", ["script", "backfill", "batch", "cli", "retry"], "complex")
FN("scripts/calibrate_dedupe.py", "main", 31, 41, "유사도 구간마다 항목 쌍 표본 10개를 뽑아 소스·제목과 함께 출력한다.", ["script", "cli", "analysis", "tuning"], "simple")
FN("scripts/run_job.py", "main", 23, 30, "인자로 받은 잡 이름을 순서대로 실행하고 결과 수를 출력한 뒤 DB 엔진을 정리한다.", ["script", "cli", "job", "orchestration"], "simple")

# ---------- imports ----------
for f, targets in imports.items():
    for t in targets:
        E("file:" + f, "file:" + t, "imports", 0.7)

# ---------- exports ----------
for path, name in [
    ("app/db/feedback.py", "upsert_feedback"),
    ("app/db/session.py", "session_scope"),
    ("app/db/session.py", "to_asyncpg_url"),
    ("app/db/session.py", "requires_tls"),
    ("app/db/session.py", "connect_args"),
    ("app/log.py", "get_logger"),
    ("app/log.py", "configure_logging"),
    ("app/pipeline/ingest.py", "store_items"),
    ("app/pipeline/ingest.py", "is_web_url"),
    ("app/pipeline/embedding.py", "embed_pending"),
    ("app/pipeline/embedding.py", "alert_dim_error"),
    ("app/pipeline/embedding.py", "embedding_text"),
    ("app/pipeline/embedding.py", "needs_embedding"),
    ("app/pipeline/embedding.py", "embed"),
    ("app/jobs/collect.py", "run_source"),
    ("app/jobs/collect.py", "run_all_sources"),
    ("app/jobs/scheduler.py", "sync_sources"),
    ("app/jobs/scheduler.py", "start_scheduler"),
]:
    E("file:" + path, "function:%s:%s" % (path, name), "exports", 0.8)
E("file:app/pipeline/embedding.py", "class:app/pipeline/embedding.py:EmbeddingDimError", "exports", 0.8)

# ---------- calls ----------
for src, tgt in [
    ("app/api/discord.py", "function:app/db/feedback.py:upsert_feedback"),
    ("app/api/discord.py", "function:app/notify/base.py:parse_feedback_callback"),
    ("app/api/discord.py", "function:app/db/session.py:session_scope"),
    ("app/api/telegram.py", "function:app/db/feedback.py:upsert_feedback"),
    ("app/api/telegram.py", "function:app/notify/base.py:parse_feedback_callback"),
    ("app/api/telegram.py", "function:app/notify/telegram.py:answer_callback"),
    ("app/api/github.py", "function:app/pipeline/ingest.py:store_items"),
    ("app/api/github.py", "function:app/sources/github_release.py:release_to_item"),
    ("app/api/health.py", "function:app/db/session.py:session_scope"),
    ("app/jobs/collect.py", "function:app/pipeline/ingest.py:store_items"),
    ("app/jobs/collect.py", "function:app/pipeline/embedding.py:embed_pending"),
    ("app/jobs/collect.py", "function:app/pipeline/embedding.py:alert_dim_error"),
    ("app/jobs/collect.py", "function:app/notify/discord.py:send_ops_alert"),
    ("app/jobs/scheduler.py", "function:app/jobs/collect.py:run_source"),
    ("app/jobs/scheduler.py", "function:app/jobs/pipeline.py:run_pipeline"),
    ("app/jobs/scheduler.py", "function:app/jobs/notify.py:run_notify"),
    ("app/main.py", "function:app/jobs/scheduler.py:start_scheduler"),
    ("app/main.py", "function:app/log.py:configure_logging"),
    ("app/pipeline/embedding.py", "function:app/notify/discord.py:send_ops_alert"),
    ("app/pipeline/ingest.py", "function:app/pipeline/normalize.py:normalize_url"),
    ("app/pipeline/ingest.py", "function:app/pipeline/normalize.py:url_hash"),
    ("scripts/backfill_embeddings.py", "function:app/pipeline/embedding.py:embed_pending"),
    ("scripts/backfill_embeddings.py", "function:app/pipeline/embedding.py:needs_embedding"),
    ("scripts/run_job.py", "function:app/jobs/collect.py:run_all_sources"),
    ("scripts/run_job.py", "function:app/jobs/scheduler.py:sync_sources"),
    ("scripts/run_job.py", "function:app/jobs/pipeline.py:run_pipeline"),
    ("scripts/run_job.py", "function:app/jobs/notify.py:run_notify"),
    ("tests/test_embedding.py", "function:app/pipeline/embedding.py:embed"),
    ("tests/test_feedback_upsert.py", "function:app/db/feedback.py:feedback_upsert_stmt"),
    ("tests/test_ingest.py", "function:app/pipeline/ingest.py:is_web_url"),
    ("tests/test_session_url.py", "function:app/db/session.py:to_asyncpg_url"),
]:
    E("file:" + src, tgt, "calls", 0.8)

# ---------- tested_by ----------
for prod, test in [
    ("app/pipeline/embedding.py", "tests/test_embedding.py"),
    ("app/db/feedback.py", "tests/test_feedback_upsert.py"),
    ("app/pipeline/ingest.py", "tests/test_ingest.py"),
    ("app/db/session.py", "tests/test_session_url.py"),
]:
    E("file:" + prod, "file:" + test, "tested_by", 0.5)

# ---------- split & write ----------
files = sorted(imports.keys())
parts = max(1, int(math.ceil(max(len(nodes) / 60.0, len(edges) / 120.0))))
size = int(math.ceil(len(files) / float(parts)))
outdir = ".ua/intermediate"
written = []
for k in range(parts):
    group = set(files[k * size:(k + 1) * size])
    pn = [n for n in nodes if n["filePath"] in group]
    ids = set(n["id"] for n in pn)
    pe = [e for e in edges if e["source"] in ids]
    fname = "batch-1.json" if parts == 1 else "batch-1-part-%d.json" % (k + 1)
    fp = os.path.join(outdir, fname)
    with open(fp, "w", encoding="utf-8") as fh:
        json.dump({"nodes": pn, "edges": pe}, fh, ensure_ascii=False, indent=1)
    written.append((fp, len(pn), len(pe)))

print("nodes", len(nodes), "edges", len(edges), "parts", parts)
print("imports expected", sum(len(v) for v in imports.values()),
      "actual", sum(1 for e in edges if e["type"] == "imports"))
print("edges assigned", sum(w[2] for w in written), "of", len(edges))
print("dup node ids:", len(nodes) - len(set(n["id"] for n in nodes)))
print("self edges:", sum(1 for e in edges if e["source"] == e["target"]))
for w in written:
    print(w)
