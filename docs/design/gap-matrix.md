# 디자인 ↔ 백엔드 갭 매트릭스

모바일 디자인(`docs/design/README.md` 의 통합 표·사용자 액션)을 현재 백엔드와 한 줄씩 대조하고, 계약(`docs/api/app-api-v1.md`)을 구현하기 위한 백엔드(B)·프론트(F) 작업을 나눈다.
기준 커밋은 `93439be`, 최신 Alembic 리비전은 `0003`. 파일 참조의 줄 번호는 이 커밋 기준이다.

상태 표기는 **있음**(API 로 꺼내기만 하면 됨) / **부분**(데이터·로직 일부만 있음) / **없음**(새로 만들어야 함).
공통 전제 — 지금 백엔드에는 앱용 REST API 가 전혀 없다 (`app/main.py:31-35` 는 health·웹훅 라우터뿐). 따라서 "있음" 도 B-task 의 API 작업은 필요하다.

## 1. 매트릭스

### 1.1 공통 · 인프라

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| 앱 API · 인증 | 전체 | 없음 | 웹훅 라우터만 (`app/main.py:31-35`), 시크릿 검증 패턴 (`app/api/telegram.py:22-27`) | `/api/v1` 패키지, `APP_API_TOKEN` 베어러 인증, 오류 형식, 커서 페이지네이션 | B1 |
| 설정 영속 (`user_prefs`) | 04, 05, 06 | 없음 | 문서에만 있음 (`docs/database.md:16`). 설정은 전부 YAML (`app/config.py:140-142`) | `user_prefs` 테이블 + YAML 위 덮어쓰기 병합, 저장 즉시 반영 | B1, B2 |
| 사용자 · 표시 이름 | 08 | 없음 | 사용자 테이블 없음 (단일 사용자 전제) | `user_prefs.data.display_name`, 기본값 `config/app.yaml` | B2, B9 |
| taxonomy 12개 (`taxonomy[]`) | 04, 03, 08 | 없음 | `Category` 7값 (`app/schemas.py:11-18`), `summaries.tags` 자유 텍스트 (`app/db/models.py:99`) | `config/app.yaml` taxonomy + `GET /meta`, 판정이 `topics` 출력 → `summaries.topics` | B1, B3 |
| 소스 표시명 (`source_name`) | 03, 07, 11 | 부분 | `sources.name` 만 (`rss:arxiv-cs-cl`) (`app/db/models.py:38`) | `sources.yaml` `config.display_name` 추가, 응답에서 대체 | B2 |

### 1.2 화면 03 피드

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| alert 목록 (`id`, `title`, `summary`, `url`) | 03 | 부분 | `notifications` 발송 기록 (`app/db/models.py:108-117`) + `summaries.title_ko/summary_ko` (`models.py:97-98`) | `GET /feed` 커서 목록, 항목당 한 카드(채널 여러 개 합침) | B6 |
| `delivered_at` | 03, 07 | 있음 | `notifications.sent_at` (`models.py:115`) | 오류 없는 행의 최소값 | B6 |
| `delivery_mode` / `is_exploration` | 03, 07 | 있음 | `Level` push/silent/feed/explore (`app/schemas.py:38-42`), `notifications.level` | 값 매핑 (`push→instant` …) | B6 |
| `categories` (`#mcp-tooling`) | 03 | 없음 | `summaries.tags` 는 자유 영문 (`app/pipeline/llm.py:41`) | `summaries.topics` + 판정 프롬프트 | B3 |
| `is_saved` | 03 | 없음 | 찜 없음 | `bookmarks` 존재 여부 | B1, B7 |
| `feedback` | 03, 07 | 부분 | `feedback` 항목당 1건 (`models.py:120-128`), 값 `useful`/`useless` (`app/notify/base.py:39`) | API 에서 `not_useful` 매핑, `cleared` 는 null | B6 |
| 피드 필터 (`all/instant/quiet/experiment/useful`) | 03 | 없음 | – | `filter` 쿼리 | B6 |
| `push_sent_today` | 03 | 부분 | `push_count_today` (`app/notify/policy.py:41-53`) 는 행 수를 센다 — 채널 팬아웃 뒤엔 중복 계산 | 서로 다른 항목 수로 변경, `GET /stats/today` | B4, B6 |
| `daily_push_cap` | 03, 05 | 있음 | `NotifyConfig.daily_push_cap` (`app/config.py:112`), `config/rules.yaml:71` | 덮어쓰기 가능하게 | B2 |
| `filtered_today_count` | 03 | 없음 | 결정 로그만 (`models.py:79-88`) | 걸러짐 집계 (09 와 같은 정의) | B8, B6 |
| 원문 열기 | 03, 07, 11 | 있음 | `items.url` (`models.py:60`) | – | B6 |

### 1.3 화면 07 피드백 · 판정 근거

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `score.total` / `threshold` | 07, 09 | 있음 | `items.score` (`models.py:71`), `ScoringConfig.threshold` (`app/config.py:101`) | 상세 API | B6 |
| `score.components.src/rel/fresh/kind` | 07, 09 | 있음 | `decisions(stage=score).details.breakdown` (`app/jobs/pipeline.py:285-292`, `app/pipeline/scoring.py:103-111`) — `hot`·`multi` 도 있음 | 6개 전부 + 바 정규화용 `component_max` | B6 |
| `routing_label` (`경계 → 탐색 슬롯`) | 07 | 부분 | 탐색 발송 `Level.EXPLORE` (`app/jobs/notify.py:242-251`) | `routing` 열거형 도출 | B6 |
| `screening.relevance/kind/reason` | 07, 09, 10 | 있음 | `decisions(stage=triage).details` (`app/jobs/pipeline.py:238-249`) | 상세·걸러짐 API | B6, B8 |
| `judgment.importance` | 07 | 있음 | `summaries.importance` (`models.py:100`) | – | B6 |
| `judgment.similar_feedback` | 07 | 없음 | 사례는 프롬프트 문자열로만 쓰고 버림 (`app/jobs/pipeline.py:303`, `app/jobs/notify.py:206`) | `decisions.details.examples` 에 `{item_id, verdict, title}` 저장 | B3 |
| 유용/불필요 설정·해제 | 03, 07 | 부분 | upsert 만 (`app/db/feedback.py:12-21`). 해제 없음. 리액션 폴링이 덮어씀 (`app/jobs/feedback.py:18-40`) | `PUT/DELETE /alerts/{id}/feedback`, `feedback.source`, 앱 판정 우선 | B1, B6 |
| `recent_feedback[]` / `today_count` | 07 | 부분 | `feedback.created_at` (`models.py:128`) | `GET /feedback/recent` | B6 |
| 안내 카드 소스명 | 07 | 있음 | 소스 조인 | `trust_note_source` | B6 |

### 1.4 화면 04 관심사

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `profile.self_description` | 04 | 부분 | `policy.interests` YAML (`config/rules.yaml:5-9`, `app/config.py:68`) | 덮어쓰기 + `PUT /settings/interests` | B2 |
| `profile.not_interested` | 04 | 부분 | `policy.not_interested` (`config/rules.yaml:10-12`) | 같음 | B2 |
| `selected_categories` | 04 | 없음 | – | `policy.categories` 새 필드, 프롬프트 반영 (`app/pipeline/llm.py:132-139`) | B2, B3 |
| `watch_keywords` (+ 추가) | 04 | 부분 | `focus_stack`·`focus_repos` (`config/rules.yaml:14-22`, `app/config.py:70-71`) | 두 목록을 하나로 보이고 `/` 로 나눠 저장 | B2 |
| `kind_weights.*` | 04, 10 | 있음 | `ScoringConfig.kind_weights` (`app/config.py:106-108`, `config/rules.yaml:60-68`) — 8개 kind | 덮어쓰기 + 범위 검증 | B2 |
| 명시 저장 | 04 | 없음 | 설정 변경은 YAML 수정·재기동뿐 (`app/config.py:153-156`) | 저장 즉시 유효 설정 교체 | B2 |

### 1.5 화면 05 알림 설정

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `channels.fcm.enabled` | 05 | 없음 | FCM 없음 | `FcmNotifier`, `devices`, 채널 토글 | B4, B5 |
| `channels.discord.enabled` | 05 | 부분 | 디스코드가 유일한 채널로 하드코딩 (`app/jobs/notify.py:56`) | 채널 토글 + 팬아웃 | B4 |
| `channels.discord.channel_name` | 05 | 없음 | 채널 ID 만 (`app/config.py:39`) | `.env` `DISCORD_CHANNEL_NAME` | B1, B2 |
| `channels.discord.reaction_sync` | 05, 07 | 있음 | 리액션 폴링 (`app/jobs/feedback.py:43-52`, `app/jobs/scheduler.py:22`) | 연결 여부로 표시 | B2 |
| `channels.telegram.enabled` / `connected` | 05 | 부분 | `TelegramNotifier` 는 있으나 어디서도 안 씀 (`app/notify/telegram.py:50-79`), 토큰 설정 (`app/config.py:34-36`) | 팬아웃에 연결, `connected` = 토큰·chat_id 존재 | B4 |
| `quiet_hours.start/end/timezone` | 05 | 부분 | 시 단위 (`app/config.py:113-115`, `app/notify/policy.py:31-38`). 무음 중 push 는 QUEUED 로 미룸 (`policy.py:63-65`) | `HH:00` 노출·편집. 무음 → 피드만 (열린 질문 1) | B2, B4 |
| `dedupe_same_issue_daily` | 05 | 없음 | 문서에만 (`docs/pipeline.md:54`, `.claude/rules/notify.md`). `items.cluster_id` 는 있음 (`models.py:70`) | 정책에 클러스터 하루 1건 구현 + 토글 | B4 |
| `delivery_by_importance.high/mid/low` | 05 | 부분 | 하드코딩 `level_for` (`app/notify/policy.py:23-28`) | 설정값으로 교체 | B2, B4 |
| `exploration_slot.enabled` | 05 | 부분 | 탐색 슬롯 항상 실행 (`app/jobs/notify.py:123-127`, `187-254`) | `explore_enabled` 토글 | B2, B4 |

### 1.6 화면 06 수집 소스

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `sources_enabled_count` / `total` | 06 | 있음 | `sources.enabled` (`models.py:45`) | 집계 | B2 |
| `items_collected_today` | 06, 09 | 있음 | `items.fetched_at` (`models.py:67`) | 최근 24시간 집계 | B2, B8 |
| `llm_calls_used_today` / `budget` | 06 | 부분 | `llm_calls` 예약 행 (`models.py:131-139`), 상한 (`app/db/budget.py:35-41`) — 사용량 조회 함수 없음 | `usage_today()` | B2 |
| source `id`/`type`/`poll_interval_min` | 06 | 있음 | `sources.name/type/poll_interval_sec` (`models.py:38-41`) | – | B2 |
| source `group` | 06 | 없음 | – | type·family 로 도출 | B2 |
| source `enabled` 토글 | 06 | 부분 | 컬럼은 있으나 기동 시 YAML 이 덮어씀 (`app/jobs/scheduler.py:41`), 활성 소스만 잡 등록 (`scheduler.py:73-79`) | `PATCH /sources/{id}` + 덮어쓰기 보존 + 전 소스 잡 등록 | B2 |
| `trust` / `trust_base → calibrated` | 06, 08 | 있음 | `trust_score`, `trust_adjusted` (`models.py:42-44`), 보정은 수동 `--apply` (`scripts/weekly_report.py:180-185`) | – | B2 |
| `consecutive_failures` / `error_hint` | 06 | 부분 | `fail_count`, `last_error` (`models.py:47-48`) — 조치 문구 없음 | `config.error_hint` (YAML) | B2 |
| `repo_count` | 06 | 있음 | `config.repos` (`config/sources.yaml:95-109`) | 길이 | B2 |
| `planned_sources` | 06 | 없음 | – (디자인의 Hacker News 는 이미 구현됨, `config/sources.yaml:114-119`) | **정적** `config/app.yaml` | B1, B2 |
| 소스 추가 (`+`) | 06 | 없음 | – | v1 제외 (열린 질문 2) | – |

### 1.7 화면 08 내 프로필

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `period_days` | 08 | 없음 | – | 7·14·30 쿼리 | B9 |
| `user.display_name` | 08 | 없음 | – | prefs + `PATCH /profile` | B9 |
| `user.discord_connected` | 08 | 있음 | `.env` 토큰 (`app/config.py:38-40`) | – | B9 |
| `onboarding_done/total` | 08 | 없음 | 온보딩 범위 밖 | **정적** `config/app.yaml` | B1, B9 |
| `alerts_received`/`push_count`/`experiment_count` | 08 | 있음 | `notifications.level` | 서로 다른 항목 집계 | B9 |
| `useful_ratio`/`useful_count`/`not_useful_count` | 08 | 있음 | `feedback` (`models.py:120-128`), `precision` (`app/pipeline/trust.py:15-18`) | 기간 집계 | B9 |
| `missed_issues` | 08 | 없음 | – | 복원 결정(`stage=user`) 수로 정의 | B8, B9 |
| `category_reactions[]` | 08 | 없음 | taxonomy 없음 | `summaries.topics` × 판정 | B3, B9 |
| `learned.kind_penalties[]` | 08, 10 | 부분 | kind 는 선별 결정에만 (`app/jobs/pipeline.py:246`), 감점은 설정값 (`config/rules.yaml:60-68`). 자동 감점 학습 없음 | kind × 판정 집계, `active` = 가중치 < 0 | B8, B9 |
| `learned.source_trust_changes[]` | 08 | 있음 | `trust_adjusted` (`models.py:44`) | – | B9 |
| `profile_vector_labels` / `personal_model_threshold` | 08 | 부분 / 없음 | 판정 수는 셀 수 있음. 개인 모델 없음 | 판정 수 + **정적** 50 | B9 |
| `weekly_report.latest` + 상세 | 08 | 부분 | 표준출력 리포트만 (`scripts/weekly_report.py:135-192`), 저장·스케줄 없음 | `weekly_reports` 테이블, 주간 cron 잡, `GET /reports` | B1, B9 |

### 1.8 화면 09 · 10 걸러진 항목

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `filtered_total` / `collected_total` / `window` | 09, 10 | 부분 | `items.status` DROPPED·FILTERED_OUT (`app/schemas.py:21-28`), 결정 시각 | 최근 24시간 집계 + `ix_decisions_created_at` | B1, B8 |
| `gate_counts.exclude/dedup` | 09, 10 | 있음 | `rule` 결정 reason `dup`·`exclude_*` (`app/jobs/pipeline.py:96-114`, `app/pipeline/rules.py:45-53`) | 분류 쿼리 | B8 |
| `gate_counts.screening` | 09, 10 | 부분 | 선별은 탈락시키지 않음 (triage 는 passed=true, 오류만 false: `app/jobs/pipeline.py:238-256`) | 표시용 분류 (relevance < 0.5 인 점수 탈락 + 선별 오류) | B8 |
| `gate_counts.score/judgment` | 09, 10 | 있음 | `score`·`llm` 결정 (`app/jobs/pipeline.py:285-318`) | 분류 쿼리 (+ `stale` 구간 추가) | B8 |
| `borderline_count` / `range` | 09, 10 | 있음 | `EXPLORE_BAND` (`app/jobs/notify.py:26`), 후보 조건 (`notify.py:150-184`) | 같은 조건으로 집계 | B8 |
| 그룹 (소스별 / 종류별 / 관문별) | 09, 10 | 없음 | – | `GET /filtered/groups` | B8 |
| dropped item 필드 | 09, 10 | 있음 | 결정 행들 | `DroppedItem` 조립 | B8 |
| `exploration_candidate` | 09, 10 | 있음 | 후보 조건 (`app/jobs/notify.py:171-179`) | 항목별 판정 | B8 |
| 👍 복원 (`restored`) | 09, 10 | 없음 | – | 피드백 + `stage=user` 결정 + `app/feed` 알림 행 | B8 |
| `unclassified_count` | 10 | 있음 | 선별 전 탈락 | 집계 | B8 |

### 1.9 화면 11 찜

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| `folders[]` / 새 폴더 | 11 | 없음 | – | `bookmark_folders` + CRUD | B1, B7 |
| saved 목록·정렬·`saved_total`/`unread_count` | 11 | 없음 | – | `bookmarks` + `GET /saved`, `GET /folders` | B1, B7 |
| 찜 추가/해제 | 03, 11 | 없음 | – | `PUT/DELETE /saved/{id}` | B7 |
| 폴더 이동 · 메모 · 읽음 | 11 | 없음 | – | `PATCH /saved/{id}` | B7 |
| `resurface_unread_after_days` (7일 재알림) | 11 | 없음 | – | 재알림 잡 (FCM 조용히) + `resurfaced_at` | B5, B7 |

### 1.10 FCM

| 디자인 요소 | 화면 | 상태 | 지금 있는 것 | 필요한 백엔드 작업 | B |
|---|---|---|---|---|---|
| FCM 토큰 등록 | 앱 | 없음 | – | `devices` + `POST/DELETE /devices` | B1, B5 |
| 앱 푸시 발송 (즉시·조용히·실험) | 앱 | 없음 | `Notifier` 프로토콜 (`app/notify/base.py:22-28`) | `FcmNotifier` (HTTP v1), 무효 토큰 비활성화 | B5 |

## 2. 백엔드 작업 분해

규칙 — 각 작업은 한 폴리캣 0.5~1일. 모든 작업은 `uv run pytest` + `ruff check` + `ruff format` + `mypy app` 통과, 새 소스 파일 한 줄 한국어 헤더, DB 테스트가 필요한 쿼리는 `tests/integration/` (`TEST_DATABASE_URL`). ★ 는 `.claude/rules/core-files.md` 대상 파일을 건드리는 작업으로, 착수 전 사용자 확인이 필요하다.

병렬 충돌을 줄이는 약속.
- Alembic 리비전은 **B1 의 `0004` 하나뿐**이다. 다른 작업은 마이그레이션을 만들지 않는다. 스키마가 더 필요하면 B1 에 되돌려 넣거나 사용자에게 묻는다.
- B1 이 `app/api/v1/__init__.py` 에 모든 하위 라우터(`meta feed alerts settings sources filtered saved profile reports devices`)를 빈 `APIRouter` 로 미리 등록한다. 뒤 작업은 자기 라우터 파일과 `app/api/v1/schemas/<영역>.py`, `app/api/v1/queries/<영역>.py` 만 채운다. `app/main.py` 는 B1 만 고친다.

### B1 — DB 스키마 0004 + API 골격 ★

- 범위
  - 계약 6.1 의 테이블·컬럼·인덱스 전부를 모델과 `0004_app_api` 한 리비전에 추가한다.
  - `Settings` 에 `APP_API_TOKEN`·`DISCORD_CHANNEL_NAME`·`FCM_PROJECT_ID`·`FCM_SERVICE_ACCOUNT_FILE`, `.env.example` 갱신.
  - `config/app.yaml` + `AppConfig` + `get_app_config()` (taxonomy 12개와 설명, 정적값).
  - `app/api/v1/` 골격 — `deps.py`(베어러 인증, 세션), `errors.py`(오류 봉투, 422 변환, 404/409 헬퍼), `pagination.py`(커서 인코딩·디코딩), `schemas/common.py`, 빈 하위 라우터 등록, `GET /meta` 구현.
  - `app/main.py` 에 `/api/v1` 등록과 예외 핸들러.
  - `docs/database.md` 표 갱신 (`user_prefs` 는 실제 테이블로, `bookmarks` 등 추가).
- 파일 — `app/db/models.py`, `app/db/alembic/versions/2026xxxx_0004_app_api.py`, `app/config.py`, `config/app.yaml`, `.env.example`, `app/main.py`, `app/api/v1/**`, `docs/database.md`, `tests/api/test_auth.py`, `tests/api/test_meta.py`, `tests/api/test_pagination.py`.
- 의존 — 없음.
- 수용 기준
  - `uv run alembic upgrade head` 가 dev 브랜치에서 성공하고 `downgrade -1` 로 되돌아간다. 기존 데이터에 `feedback.source='discord'`, `summaries.topics='{}'` 가 채워진다.
  - 토큰 없음·틀림·서버 토큰 빈 값에서 401 과 오류 봉투. 맞으면 `/api/v1/meta` 200, taxonomy 12개.
  - 잘못된 쿼리가 422 `validation_error` 봉투로 나온다. 커서 왕복 테스트.
  - `/health`·웹훅은 인증 없이 그대로 동작한다 (기존 테스트 통과).

### B2 — 설정 덮어쓰기 + 설정·소스 API ★

- 범위
  - `user_prefs` 읽기/쓰기, 깊은 병합 + `_Strict` 재검증, `set_prefs_overlay()` 로 `get_rules()` 캐시 교체. lifespan 에서 스케줄러 전에 적재.
  - `Rules` 새 필드 (`policy.categories`, `notify.cluster_daily_dedupe`, `notify.delivery_by_importance`, `notify.explore_enabled`, `notify.channels`) 와 `config/rules.yaml` 기본값. 정책 동작은 바꾸지 않는다 (B4 몫).
  - `GET/PUT /settings/interests`, `GET/PATCH /settings/notifications` (채널 `connected` 계산, 409 `channel_not_connected`).
  - `sync_sources` 가 `user_prefs.data.sources` 를 YAML 위에 적용, YAML 의 모든 소스에 잡 등록.
  - `GET /sources` (그룹 도출, `display_name`·`error_hint`, `budget.usage_today()`), `PATCH /sources/{id}`. `config/sources.yaml` 에 `display_name`·`error_hint` 추가.
  - `docs/pipeline.md` 에 "설정은 YAML + 앱 덮어쓰기" 한 단락.
- 파일 — `app/config.py`, `config/rules.yaml`, `config/sources.yaml`, `app/db/prefs.py`(새), `app/db/budget.py`, `app/jobs/scheduler.py`, `app/main.py`(lifespan 적재 한 줄), `app/api/v1/settings.py`, `app/api/v1/sources.py`, 스키마·쿼리 모듈, `tests/api/test_settings.py`, `tests/api/test_sources.py`, `tests/test_prefs_overlay.py`, `tests/test_scheduler.py`.
- 의존 — B1.
- 수용 기준
  - 덮어쓰기 병합 단위 테스트 — 목록 교체, 알 수 없는 키 거부, 옛 섹션 검증 실패 시 경고 후 무시.
  - `PUT /settings/interests` 뒤 `get_rules().policy.interests`·`scoring.kind_weights` 가 바로 바뀐다. `watch_keywords` 의 `anthropics/*` 는 `focus_repos` 로 간다. 카테고리 0개·범위 밖 가중치는 422.
  - `PATCH /settings/notifications` 가 부분 병합되고 `quiet_hours.start="23:30"` 은 422, 텔레그램 미연결 켜기는 409.
  - 소스를 끄고 `sync_sources()` 를 다시 불러도 꺼진 채로 남는다 (재기동 시나리오 테스트). 비활성 소스도 잡이 등록되고 `run_source` 가 0 을 돌려준다.
  - `GET /sources` 가 06 fixture 모양과 일치한다 (`llm_budget.triage.used` 는 오늘 `llm_calls` 수).

### B3 — 판정 출력 확장 (topics · 유사 사례 저장) ★

- 범위
  - `LLMVerdict.topics: list[str]` 추가. 판정 프롬프트에 taxonomy slug·설명을 넣고 1~3개 고르게 한다. 모르는 slug 는 버리고 최대 3개. `summaries.topics` 에 저장 (일반 판정·탐색 판정 둘 다).
  - `render_policy` 에 `관심 카테고리` 줄 (선택된 taxonomy 라벨).
  - 판정 호출 때 쓴 최근접 사례를 `decisions(stage=llm).details.examples = [{item_id, verdict, title}]` 로 저장 (일반·탐색 둘 다).
  - `nearest_feedback` 이 `verdict IN ('useful','useless')` 만 보고, 요약이 없는 항목(복원)은 `items.title` 로 LEFT JOIN 한다. `FeedbackExample` 에 `item_id` 추가.
  - `docs/pipeline.md` 판정 단계 설명 갱신.
- 파일 — `app/schemas.py`, `app/pipeline/llm.py`, `app/pipeline/feedback.py`, `app/jobs/pipeline.py`, `app/jobs/notify.py`(탐색 판정 저장 부분만), `tests/test_prompts.py`, `tests/test_feedback_examples.py`, `tests/integration/test_feedback_db.py`, `tests/integration/test_pipeline_db.py`.
- 의존 — B1, B2 (`policy.categories`).
- 수용 기준
  - 프롬프트 스냅샷 테스트에 taxonomy 12개와 관심 카테고리 줄이 들어간다.
  - 가짜 LLM 응답의 `topics=["mcp-tooling","nope","agent","video","llm-model"]` 이 `["mcp-tooling","agent","video"]` 로 저장된다.
  - 판정 결정 행에 `examples` 가 남는다 (통합 테스트, 사례 0건이면 `[]`).
  - `cleared` 판정 행은 사례에 나오지 않는다. 요약 없는 복원 항목도 사례로 나온다.

### B4 — 발송 정책 확장 + 채널 팬아웃 (텔레그램 연결) ★

- 범위
  - `policy.decide` 가 `delivery_by_importance` 를 읽는다 (`level_for` 대체).
  - 무음 시간 중 `instant`·`quiet` 은 `feed_only` 로 기록 (열린 질문 1 의 기본안. 사용자가 현행 유지를 고르면 이 항목만 뺀다).
  - `cluster_daily_dedupe` — 오늘(달력일) 같은 `cluster_id` 가 `push`·`silent`·`explore` 로 나갔으면 `feed_only`.
  - `push_count_today` 는 `count(DISTINCT item_id)`.
  - `enabled_notifiers(rules)` — 켜져 있고 연결된 채널 목록 (디스코드·텔레그램, FCM 은 B5 가 등록). `run_notify` 와 `_explore` 가 전 채널로 보내고 채널마다 `notifications` 행. 한 채널이라도 성공하면 `SENT`. 첫 채널부터 `RateLimited` 면 현행처럼 배치 중단, 다른 채널 성공 뒤의 `RateLimited` 는 그 채널 행에 `error='rate_limited'`.
  - 피드 전용 기록은 `channel='app'`. 켜진 채널이 없으면 전부 피드 전용.
  - `explore_enabled=false` 면 `_explore` 를 건너뜀.
  - 텔레그램 웹훅·디스코드 인터랙션 upsert 에 `source` 전달.
  - `docs/pipeline.md` 발송 정책 절과 `.claude/rules/notify.md` 수치 확인.
- 파일 — `app/notify/policy.py`, `app/notify/base.py`, `app/jobs/notify.py`, `app/api/telegram.py`, `app/api/discord.py`, `app/db/feedback.py`(source 인자), `tests/test_policy.py`, `tests/integration/test_explore_db.py`, `tests/test_notify_fanout.py`(새), `docs/pipeline.md`.
- 의존 — B2.
- 수용 기준
  - 정책 단위 테스트 — 매핑 변경(`mid=feed_only`)이 반영되고, 무음 시간 push 는 `feed_only`, 같은 클러스터 두 번째는 `feed_only`, 토글 끄면 둘 다 보냄.
  - 팬아웃 테스트(가짜 Notifier 2개) — 둘 다 행이 남고, 하나 실패해도 `SENT`, 둘 다 실패면 `FAILED`, 첫 채널 `RateLimited` 는 기록 없이 중단.
  - push 상한은 채널 2개로 보내도 항목 하나당 1로 센다.
  - 탐색 토글 off 에서 LLM 예약이 일어나지 않는다.
  - 텔레그램이 켜지고 연결되면 `TelegramNotifier.send` 가 respx 모킹으로 호출된다.

### B5 — FCM 채널 + 기기 등록 API

- 범위
  - `app/notify/fcm.py` `FcmNotifier` — 서비스 계정으로 OAuth 토큰(google-auth, 만료 전 재사용), FCM HTTP v1 `messages:send` 를 활성 기기마다 호출. 계약 4.9 페이로드 (Android 채널 `instant`/`quiet`, APNs 우선순위). `UNREGISTERED`·`INVALID_ARGUMENT` 는 `disabled_at`·`last_error` 기록. 기기가 0대이거나 전부 실패면 예외 → 그 채널 행에 오류.
  - `enabled_notifiers` 에 FCM 등록 (`connected` = 프로젝트 ID·서비스 계정 파일 존재).
  - 재알림용 `send_resurface(item, title)` (조용히, `data.type=resurface`).
  - `POST /devices`, `DELETE /devices/{token}`. `GET /settings/notifications` 의 `device_count`.
  - `pyproject.toml` 에 `google-auth`, `docker-compose.yml` 서비스 계정 볼륨 안내는 `.env.example` 주석으로.
- 파일 — `app/notify/fcm.py`(새), `app/notify/base.py`, `app/api/v1/devices.py`, 스키마·쿼리 모듈, `pyproject.toml`, `uv.lock`, `.env.example`, `tests/test_fcm.py`, `tests/api/test_devices.py`.
- 의존 — B1, B4.
- 수용 기준
  - respx 로 OAuth·FCM 을 모킹해 `instant`/`quiet`/`experiment` 페이로드가 계약과 같다.
  - 404 `UNREGISTERED` 응답 뒤 그 기기가 비활성화되고 다음 발송에서 빠진다.
  - `POST /devices` 두 번은 201 → 200, 비활성 기기 재등록은 다시 활성.
  - 네트워크·실 FCM 호출 없음.

### B6 — 피드 · 상세 · 피드백 API

- 범위
  - `GET /stats/today`, `GET /feed` (필터·커서, 항목당 한 카드), `GET /alerts/{id}` (근거 조립, `routing` 도출, `component_max`), `PUT/DELETE /alerts/{id}/feedback`, `GET /feedback/recent`.
  - `Alert` 직렬화기(`app/api/v1/queries/alerts.py`)를 공용으로 만든다 (B7·B8 이 재사용).
  - `db/feedback.py` 에 `clear_feedback` (`cleared`, `source='app'`).
  - `sync_feedback` 이 `feedback.source='app'` 인 항목을 건너뛴다.
  - `filtered_count` 는 B8 의 집계 함수를 쓰되, B8 전에는 같은 정의의 최소 쿼리를 `queries/filtered.py` 에 먼저 만든다 (B8 이 확장).
- 파일 — `app/api/v1/feed.py`, `app/api/v1/alerts.py`, `app/api/v1/queries/{alerts,feed,filtered}.py`, 스키마 모듈, `app/db/feedback.py`, `app/jobs/feedback.py`, `tests/api/test_feed.py`, `tests/api/test_alerts.py`, `tests/integration/test_feed_db.py`, `tests/test_feedback_reactions.py`.
- 의존 — B1. (B3 이 먼저 들어오면 `categories`·`similar_feedback` 이 채워지고, 아니면 `[]` 이다.)
- 수용 기준
  - 같은 항목이 디스코드·FCM 두 행이어도 피드에 한 번, `delivered_at` 은 이른 쪽.
  - 필터 5종, 커서 두 페이지 연속 조회에서 중복·누락 없음 (통합 테스트).
  - 피드백 PUT → `useful`, 반대 PUT → `not_useful`, DELETE → `feedback: null`. 이후 리액션 폴링이 다른 판정을 줘도 바뀌지 않는다. 디스코드에서만 준 판정은 폴링이 계속 갱신한다.
  - 07 fixture 와 같은 모양의 상세 응답 (점수 전 항목은 `score: null`, 선별 전은 `screening: null`).
  - `feedback/recent` 의 `today_count` 가 Asia/Seoul 달력일 기준.

### B7 — 찜 API + 읽지 않은 찜 재알림

- 범위
  - `GET/POST/PATCH/DELETE /folders`, `GET /saved`, `PUT/PATCH/DELETE /saved/{alert_id}` (계약 4.7).
  - 재알림 잡 — 1시간 주기, 무음 시간 밖에서만, `is_read=false AND resurfaced_at IS NULL AND saved_at <= now - 7일` 을 FCM 조용히로 보내고 `resurfaced_at` 기록. FCM 꺼짐·미연결이면 아무것도 하지 않는다. 피드·통계에 넣지 않는다.
- 파일 — `app/api/v1/saved.py`, 스키마·쿼리 모듈, `app/jobs/resurface.py`(새), `app/jobs/scheduler.py`(잡 등록), `tests/api/test_saved.py`, `tests/test_resurface.py`, `tests/integration/test_saved_db.py`.
- 의존 — B1, B5 (재알림). API 부분은 B1 뒤 바로 시작할 수 있다.
- 수용 기준
  - 폴더 이름 중복 409, 폴더 삭제 뒤 찜이 미분류로 남음, `unfiled` 필터 동작.
  - `PUT` 201 → 200 멱등, 메모 빈 문자열은 `null`, `is_read=true` 가 `read_at` 을 채움.
  - 정렬 3종·`unread_only`·커서 테스트. `GET /folders` 카운트가 목록과 맞는다.
  - 재알림은 한 번만 가고, 읽은 찜·7일 미만·무음 시간·FCM 꺼짐에서는 가지 않는다 (가짜 FCM).

### B8 — 걸러진 항목 API + 복원 ★

- 범위
  - 관문 분류 함수 (마지막 비사용자 결정 → `gate`, 계약 2 의 표). `screening_relevance_floor` 는 `config/app.yaml`.
  - `GET /filtered/summary`, `GET /filtered/groups` (`source`·`kind`·`gate`, 정렬, 미리보기 3건, 그룹 통계 필드), `GET /filtered/items`.
  - `POST/DELETE /filtered/items/{id}/restore` — 피드백·`Stage.USER` 결정·`app/feed` 알림 행을 한 트랜잭션으로. `Stage.USER` 추가.
  - 탐색 후보 조건을 `jobs/notify.py` 와 공유하도록 조건을 한 함수로 뺀다 (복제 금지).
- 파일 — `app/schemas.py`(`Stage.USER`), `app/api/v1/filtered.py`, `app/api/v1/queries/filtered.py`, 스키마 모듈, `app/jobs/notify.py`(후보 조건 추출만), `tests/api/test_filtered.py`, `tests/integration/test_filtered_db.py`.
- 의존 — B6 (`Alert` 직렬화기·`clear_feedback`).
- 수용 기준
  - 여섯 관문별 픽스처 항목이 맞는 `gate` 로 분류되고 `gate_counts` 합 = `filtered_total` = 종류별 그룹 합.
  - 경계 항목만 `exploration_candidate=true`, `borderline.range` 가 통과선 − 0.10 ~ 통과선.
  - 복원 뒤 `GET /feed` 첫 줄에 `feed_only` 카드로 나오고 `feedback=useful`, `decisions` 에 `stage=user` 행. 복원 항목은 이후 탐색 후보가 아니다. 취소하면 셋 다 원복.
  - 복원이 어떤 채널 발송도 일으키지 않는다.

### B9 — 프로필 통계 + 주간 리포트 저장·조회

- 범위
  - `GET /profile` (계약 4.8 집계 전부), `PATCH /profile` (`display_name`).
  - `app/jobs/report.py` — `scripts/weekly_report.py` 의 SQL 과 표 조립을 옮겨 `sections` 로 돌려주고 `weekly_reports` 에 upsert. 제목 `M월 N주차 리포트`(기간 시작일 기준), 부제는 섹션 이름 요약.
  - 스크립트는 이 함수를 불러 출력만 하고 `--apply` 신뢰도 기록은 그대로 둔다 (자동 적용하지 않는다).
  - 스케줄러에 월요일 09:00 Asia/Seoul cron 잡 (지난 7일).
  - `GET /reports`, `GET /reports/{id}`.
- 파일 — `app/api/v1/profile.py`, `app/api/v1/reports.py`, 스키마·쿼리 모듈, `app/jobs/report.py`(새), `app/jobs/scheduler.py`, `scripts/weekly_report.py`, `tests/api/test_profile.py`, `tests/test_weekly_report.py`, `tests/integration/test_profile_db.py`.
- 의존 — B3 (`topics`), B8 (`Stage.USER`).
- 수용 기준
  - 픽스처 데이터로 `useful_ratio` 반올림, 판정 0건이면 `null`, `period_days` 7·14·30 외는 422.
  - `category_reactions` 가 `total` 내림차순 상위 6, `missed_issues` = 기간 안 복원 수.
  - 리포트 잡을 두 번 돌려도 같은 주 행이 하나이고 `sections` 키 8개. 스크립트 출력이 이전과 같은 표를 낸다.
  - `weekly_report_latest` 가 없으면 `null`.

### 의존 그래프

```
B1 ─┬─ B2 ─┬─ B3 ──────────────┐
    │      └─ B4 ── B5 ── B7*   │
    ├─ B6 ── B8 ────────────── B9
    └─ B7 (API 부분)
```

`*` B7 의 재알림 잡만 B5 에 의존한다. 코어 파일 작업은 B1·B2·B3·B4·B8 (B6 은 `app/db/feedback.py` ★, B5 는 `pyproject.toml` ★ 을 건드린다). 사실상 B7·B9 만 코어 밖이다.

## 3. 프론트 작업 분해

규칙 — 각 작업은 한 폴리캣 0.5~1일, Flutter stable, `mobile/` 에서 `flutter analyze` 경고 0, `flutter test` 통과. 골든 테스트는 쓰지 않는다. 위젯 테스트는 **fixture 저장소**로 돌리고 텍스트·아이콘·상태 전이를 `find` 로 확인한다. 화면 작업은 백엔드 없이 fixture 로 끝내고, API 모드 확인은 해당 B 작업이 머지된 뒤 수동 스모크로 한다.

### F0 — Flutter 스캐폴딩 · 테마 · 공통 위젯 · 내비게이션

- 범위
  - `mobile/` 에 Flutter 앱 생성 (패키지 `tech_radar`, Android·iOS). `analysis_options.yaml` 은 `flutter_lints` + `prefer_const`·`always_declare_return_types`.
  - 의존성 — `flutter_riverpod`, `go_router`, `dio`, `google_fonts`(IBM Plex Sans KR), `lucide_icons_flutter`, `intl`, `url_launcher`, `json_annotation`/`json_serializable`/`build_runner`.
  - `lib/core/theme/` — `tokens.md` 색·타이포·간격·반경을 `AppColors`·`AppText`·`AppSpacing` 상수와 `ThemeData` 로. 다크 모드 없음.
  - `lib/core/widgets/` — Card, SectionLabel, Chip(선택·미선택·개수), Badge(4종), Toggle(44×26), ToggleRow/ValueRow, SegmentedControl, OpenButton·IconButton·FeedbackButton·RestoreButton·TextButton, StatCard, ScoreBar·StackedBar·GateBar, SubTopBar(뒤로가기)·RootTopBar, 빈·로딩·오류 상태 위젯.
  - `lib/core/labels.dart` (계약 2 의 한국어 라벨 전부), `lib/core/format.dart` (상대시간 `N분 전`·`N시간 전`·`어제`·`M월 d일`, 점수 2자리, 유니코드 `−` 부호).
  - `go_router` `StatefulShellRoute` 로 4탭(피드·찜·설정·내 프로필) + 탭별 중첩 스택, 07 은 루트 네비게이터(탭바 없음). 모든 화면은 자리표시 페이지.
  - `lib/core/api/` — dio 클라이언트 (`--dart-define=API_BASE_URL`, `APP_API_TOKEN` 베어러 인터셉터, 타임아웃 15초), 오류 봉투 → `ApiException(code, message, status)` 변환.
  - `ProviderScope` 와 `apiClientProvider`, `useFixturesProvider` (`--dart-define=USE_FIXTURES=true` 기본 true).
- 의존 — 없음 (계약 문서만).
- 수용 기준
  - `flutter analyze` 0, `flutter test` 통과.
  - 위젯 테스트 — 탭 4개 전환 시 활성 색 `#2D5BE3`, 찜 탭 활성 아이콘 채움. 하위 경로에서 탭바 유지, 07 경로에서 탭바 없음.
  - 공통 위젯 테스트 — Chip·FeedbackButton 선택 상태 색, Toggle on/off, SegmentedControl 선택 콜백, GateBar 구간 폭 비례.
  - `format.dart` 단위 테스트 (경계값 59분·23시간·어제·음수 부호).
  - dio 인터셉터가 `Authorization` 을 붙이고 401 봉투를 `ApiException('unauthorized')` 로 바꾼다 (mock adapter).

### F1 — 도메인 모델 · 저장소 계층 · fixture

- 범위
  - 계약 3·4 의 모든 객체를 `lib/data/models/` 에 `json_serializable` 로 (Alert, AlertDetail/Rationale, DroppedItem, FilteredSummary/Group, SavedItem, Folder/FolderList, Source/SourcesResponse, InterestsSettings, NotificationSettings, Profile, Report/ReportSummary, Meta, TodayStats, RecentFeedback, Page<T>). 모르는 열거형 값은 `unknown` 으로 받는다.
  - 저장소 인터페이스 (`FeedRepository`, `AlertRepository`, `SettingsRepository`, `SourceRepository`, `FilteredRepository`, `SavedRepository`, `ProfileRepository`, `MetaRepository`, `DeviceRepository`) 와 `Api*` 구현(dio), `Fixture*` 구현(메모리 상태로 쓰기 반영, 지연 300ms).
  - `mobile/assets/fixtures/*.json` — 계약 예시와 디자인 샘플 데이터(03 카드 3장, 07 BeaconKV, 04 12개 카테고리, 06 소스 7개, 08 통계, 09 그룹 6개·펼침 3건, 10 그룹 7개, 11 폴더 3개·찜 4건).
  - 저장소 프로바이더가 `useFixturesProvider` 로 구현을 고른다.
- 의존 — F0.
- 수용 기준
  - 모든 fixture 파일이 모델로 역직렬화되는 테스트 (필드 누락 없음, `null`·`[]` 처리).
  - Fixture 저장소 쓰기 테스트 — 피드백 PUT/DELETE, 찜 추가·이동·메모, 복원, 설정 PATCH 가 다음 조회에 반영.
  - `Api*` 구현을 dio mock adapter 로 경로·쿼리·본문 검증 (엔드포인트마다 1개 이상).

### F2 — 03 피드 + 07 피드백 · 판정 근거

- 범위
  - 03 — RootTopBar(`오늘`, 검색·벨 아이콘은 `준비 중` 토스트), 필터 칩 5개, 요약 줄(`오늘 push 4 / 15`, `걸러짐 571건 보기 ›` → 09), FeedCard(실험 헤더·배지·제목·요약·`#slug` 태그·원문·찜·유용/불필요), 무한 스크롤(커서), 당겨서 새로고침, 빈 상태.
  - 피드백 상호배타 토글·재클릭 해제, 찜 토글 모두 낙관적 갱신 + 실패 시 롤백·스낵바.
  - 07 — 요약 카드, 근거 카드(점수/통과선, `routing` 라벨, 점수 바 4행 + 0 아닌 hot·multi, 선별·판정 근거 두 줄), 판정 버튼(03 과 같은 상태 공유), 안내 카드(소스명 동적), 최근 판정 목록(행 탭 → 해당 07).
  - 피드·상세·최근 판정의 피드백 상태를 하나의 프로바이더로 공유한다.
- 의존 — F1. (API 모드는 B6 뒤.)
- 수용 기준
  - fixture 로 카드 3장이 디자인 샘플 문구대로 보이고 2번 카드만 실험 헤더.
  - 필터 `실험` 선택 시 1장, `유용` 선택 시 1장.
  - 03 에서 유용 → 07 로 이동하면 유용이 선택된 상태, 07 에서 해제 → 뒤로 가면 03 도 해제.
  - 저장소가 오류를 던지면 버튼 상태가 롤백되고 스낵바에 `message` 표시.
  - `score.kind` 가 음수면 값이 경고색이고 바 채움 없음.

### F3 — 11 찜

- 범위
  - RootTopBar(`찜`, 검색은 `준비 중`, 더보기 → 폴더 관리 시트: 이름 변경·삭제·순서), 폴더 칩(전체·폴더·`+`) 가로 스크롤, 정렬 선택 시트(3종), `안 읽음 N` 토글, SavedCard(메타·폴더 배지·제목·메모 박스·원문·폴더·찜 해제), 안내 카드.
  - 폴더 이동 바텀시트(폴더 목록 + 미분류 + 새 폴더), 새 폴더 다이얼로그(1~30자), 메모 편집 시트(500자), 찜 해제 되돌리기 스낵바.
  - 원문 열기·카드 탭(07) 시 `is_read=true` PATCH.
- 의존 — F1. (07 경로는 F0 에서 존재, 화면은 F2.) API 모드는 B7 뒤.
- 수용 기준
  - fixture 로 `전체 23`, 폴더 3개 개수, 찜 4장과 메모 2개가 보인다.
  - 폴더 이동 후 배지·칩 개수 갱신, 메모 비우면 메모 박스 사라짐, 해제 → 되돌리기로 폴더·메모 복원.
  - 새 폴더 이름 중복(409 fixture)에서 오류 문구.
  - `안 읽음` 토글 시 읽은 카드가 사라진다.

### F4 — 설정 루트 + 04 관심사

- 범위
  - 설정 루트(디자인 없음) — RootTopBar `설정`, 카드 행 `관심사`·`알림 설정`·`수집 소스` (보조 줄에 요약: 카테고리 N/12, push 상한, 활성 소스 N/M), `표시 이름` 편집 행(`PATCH /profile`), 앱 버전.
  - 04 — 헤더 `저장`(변경 없으면 비활성, 카테고리 0개면 비활성), 프로필 카드 편집 시트(두 필드), taxonomy 2열 그리드와 `N / 12 선택`, 키워드 칩 wrap(`+ 추가` 다이얼로그, 길게 눌러 삭제 확인), kind 가중치 8행(편집 시트 스테퍼 −0.50~+0.50 단계 0.05, `+0.00` 형식·유니코드 `−`), 저장 안 한 채 뒤로가기 확인 다이얼로그.
- 의존 — F1. API 모드는 B2 뒤.
- 수용 기준
  - fixture 로 8/12 선택, 키워드 7개 이상, 가중치 `−0.15`·`−0.05`·`−0.30` 경고색.
  - 셀 탭으로 카운트 증감, 전부 해제하면 저장 비활성.
  - 저장 시 `PUT` 본문이 로컬 상태와 같다 (fake 저장소 캡처). 422 응답이면 `message` 표시.
  - 더티 상태에서 뒤로가기 → 확인 다이얼로그, 취소 시 머무름.

### F5 — 05 알림 설정 + 06 수집 소스

- 범위
  - 05 — 채널 카드 3행(Discord 보조 줄 `{channel_name} · 유용/불필요 리액션 동기화`, Telegram `연결 안 됨`, FCM 기기 0대면 `등록된 기기 없음`), 알림 피로 카드(push 상한 피커 1~50, 무음 시간 시작·종료 시 단위 피커 + 시간대 보조 줄, 같은 이슈 하루 1건 토글), 중요도별 세그먼트 3개, 탐색 슬롯 토글. 모두 즉시 `PATCH` + 낙관적 갱신, 409 `channel_not_connected` 면 토글 되돌림과 안내.
  - 06 — Stat 3열(`9 / 10`, `612 건`, `41 / 60`), 그룹별 SourceRow(아이콘 타일, 상태 줄 조합 규칙 `{주기}` · `보정 a → b` · `저장소 n개` / 오류 `실패 n회 · {hint}` 오류색, `trust x.x`, 토글), `미착수` 칩, 헤더 `+` 는 `준비 중` 토스트.
- 의존 — F1. API 모드는 B2(05·06), B4·B5(채널 연결 상태) 뒤.
- 수용 기준
  - fixture 로 05 샘플 값(`15건`, `23:00 – 08:00`, 세그먼트 즉시/조용히/피드만) 표시.
  - 텔레그램 켜기 → 409 fixture → 토글 OFF 복귀와 스낵바.
  - 세그먼트 변경 시 `PATCH` 본문이 `{"delivery_by_importance": {"mid": "feed_only"}}`.
  - 06 에서 `rss:anthropic` 상태 줄이 오류색 `실패 5회 · 미러 확인 필요`, `rss:arxiv-cs-ai` 가 `60분 · 보정 0.5 → 0.58`, `github_release:watchlist` 가 `30분 · 저장소 10개`. 토글 시 활성 소스 Stat 이 갱신.

### F6 — 09 · 10 걸러진 항목 (+ 관문별)

- 범위
  - SubTopBar(`걸러진 항목`, 검색은 `준비 중`) + 세그먼트(소스별·종류별·관문별) — 한 화면에서 `view` 만 바꾼다.
  - Summary 카드(`오늘 걸러짐 571 / 수집 612`, `최근 24시간`, GateBar 6구간 + 범례, 보기별 하단 안내 문구), SectionLabel + 정렬(`많은 순`/`이름순`).
  - DropGroup(소스별은 아이콘 타일, 종류별은 `{kind} · {라벨}`, 관문별은 gate 라벨) 펼침/접힘, 요약 줄 조합(계약 4.6), DroppedItem(배지·사유 줄 조합 규칙), `더 보기`(커서), RestoreButton(복원·취소 토글, 복원 시 스낵바 `피드에 추가했습니다`), 걸러짐 0건 빈 상태.
- 의존 — F1. API 모드는 B8 뒤.
- 수용 기준
  - fixture 로 09 그룹 6개 순서·건수, 첫 그룹 펼침 3건과 사유 줄이 디자인 문구와 같다.
  - 종류별로 바꾸면 `미분류 (exclude·중복)` 가 마지막, 합계 571.
  - 복원 탭 → 버튼 선택 상태 → 피드 저장소 첫 항목이 그 항목 (fixture 공유 상태).
  - 그룹 펼침 상태가 보기 전환 뒤 초기화된다.

### F7 — 08 내 프로필 + 주간 리포트 상세

- 범위
  - RootTopBar(`내 프로필`, 우측 기간 선택 `최근 7·14·30일`), 사용자 행(이니셜 아바타, `Discord 연결됨 · 온보딩 8/8 완료`), Stat 3열(`61` / `push 38 · 실험 9`, `64%` / `유용 27 / 불필요 15`, `1` / 캡션), 반응 카테고리 스택 바(최대 합계로 정규화), 학습된 취향 행(kind 감점 경고색, 소스 신뢰도 변화, `42건 (개인 모델 전환 50건)`), 주간 리포트 카드 → 상세.
  - 리포트 상세(디자인 없음) — 섹션별 제목 + 가로 스크롤 표, 숫자 우정렬.
- 의존 — F1. API 모드는 B9 뒤.
- 수용 기준
  - fixture 로 08 샘플 문구 전부 표시, 카테고리 6행이 합계 내림차순.
  - 기간 변경 시 `period_days` 쿼리로 재조회.
  - `useful_ratio: null` 이면 `–`, `weekly_report_latest: null` 이면 카드 숨김.
  - 리포트 상세가 섹션 8개를 렌더링하고 `null` 셀은 `–`.

### F8 — FCM 연동 · 알림 탭 딥링크

- 범위
  - `firebase_core`, `firebase_messaging`, `flutter_local_notifications`. Android 알림 채널 `instant`(HIGH, 소리) · `quiet`(LOW, 무음) 생성, iOS 권한 요청.
  - 기동 시·`onTokenRefresh` 시 `POST /devices` (fixture 모드에서는 no-op 로그).
  - 알림 탭(종료·백그라운드·포그라운드) → `data.alert_id` 로 07 이동, `type=resurface` 도 07.
  - 포그라운드 수신 시 인앱 스낵바 + 피드 새로고침.
  - Firebase 설정 파일(`google-services.json`, `GoogleService-Info.plist`)은 커밋하지 않고 `mobile/README` 대신 `.gitignore` 와 빌드 안내를 계약 문서 링크로 남긴다.
- 의존 — F2. 실기기 확인은 B5 뒤.
- 수용 기준
  - 메시지 데이터 → 경로 변환 함수 단위 테스트 (`alert_id` 없으면 피드).
  - 토큰 등록 호출이 fake `DeviceRepository` 로 기동·갱신 때 각각 1회.
  - `flutter analyze` 0. 실기기 스모크(B5 머지 후) — `instant` 소리, `quiet` 무음, 탭 시 07.

### 프론트 의존 그래프

```
F0 ── F1 ─┬─ F2 ── F8
          ├─ F3
          ├─ F4
          ├─ F5
          ├─ F6
          └─ F7
```

F1 뒤 F2~F7 은 서로 독립이라 병렬로 돌릴 수 있다. 공통 위젯이 더 필요하면 자기 화면 폴더에 두고, 두 화면 이상이 쓰게 되면 `lib/core/widgets/` 로 옮기는 별도 PR 을 낸다.
