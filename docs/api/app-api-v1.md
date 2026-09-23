# 앱 API v1 계약 (Flutter ↔ FastAPI)

모바일 앱(`mobile/`, Flutter)과 백엔드(FastAPI, 같은 프로세스)가 공유하는 계약서다. 화면 명세는 `docs/design/README.md` 와 `docs/design/screens/*.md` (픽셀 진실은 `docs/design/source/*.dc.html`), 현재 백엔드와의 차이·작업 분해는 `docs/design/gap-matrix.md` 를 본다.
스키마·선별 출력·발송 억제는 사용자 계획서 `v2-다중사용자-1차-구현서.md` (이하 **v2 계획서**) 를 따른다. 둘이 어긋나면 v2 계획서가 이긴다. 대응표는 10절에 있다.
이 문서가 바뀌면 프론트 fixture(`mobile/assets/fixtures/*.json`)와 백엔드 응답 모델(`app/api/v1/schemas/<영역>.py`)을 같은 PR 에서 맞춘다.

- 범위 — 화면 03·04·05·06·07·08·09·10·11. 로그인·온보딩(01·02)은 범위 밖이다.
- 사용자 — 한 명이지만 스키마는 다중 사용자를 받는다 (v2 계획서 Task 1). `users` 테이블에 `id=1` 한 행이 있고, 코드는 `DEFAULT_USER_ID = 1` (`app/db/users.py`) 로 돈다. 사용자별 데이터(`feedback`·`notifications`·앱 새 테이블)는 전부 `user_id` 를 가진다. 사용자 조회·가입·온보딩은 만들지 않는다.
- 원칙 — 단순함. 디자인에만 있고 백엔드 근거가 없는 값(개인 모델 전환선, 미착수 소스, 온보딩 진행도)은 API 로 노출하되 설정·정적값으로 채우고, 해당 필드 설명에 **정적** 이라고 적는다.

## 1. 공통 규약

### 1.1 기본 URL · 인증

- 기본 경로는 `https://{DOMAIN}/api/v1`. Caddy 는 이미 전체 경로를 `app:8000` 으로 넘기므로 프록시 변경은 없다.
- 모든 `/api/v1/*` 요청은 헤더 `Authorization: Bearer <APP_API_TOKEN>` 이 필요하다.
  - 서버는 `.env` 의 `APP_API_TOKEN` 과 `hmac.compare_digest` 로 비교한다.
  - `APP_API_TOKEN` 이 비어 있으면 모든 요청이 401 이다 (디스코드 공개키가 비었을 때와 같은 방식).
  - 앱은 토큰을 `--dart-define=APP_API_TOKEN=...` 로 빌드 시 주입한다. 앱 안에 입력 화면은 없다.
- 토큰은 하나이고 `DEFAULT_USER_ID` 로 매핑된다. `deps.current_user_id()` 가 이 값을 돌려주고, 모든 조회·쓰기는 이 `user_id` 로 거른다. 사용자별 토큰은 다중 사용자 설계 때 붙인다.
- 기존 웹훅(`/webhook/*`)과 `/health` 는 이 인증을 쓰지 않는다. 바뀌지 않는다.
- 모바일 전용이라 CORS 는 열지 않는다.

### 1.2 형식

- 요청·응답 본문은 `application/json; charset=utf-8`, 키는 `snake_case`.
- 시각은 전부 **ISO-8601 UTC**, 초 단위, `Z` 접미 (`2026-09-24T02:18:00Z`). 상대시간(`42분 전`, `어제`, `9월 14일`)은 클라이언트가 만든다.
- 날짜만 필요한 값은 `YYYY-MM-DD` (주간 리포트 기간). 시각(時刻) 값은 `HH:mm` (무음 시간).
- "오늘" 의 뜻은 두 가지로 고정한다.
  - **달력일** — Asia/Seoul 자정 기준. `push_sent_today`, LLM 예산 사용량, 클러스터 하루 1건. 백엔드의 기존 `today_start` 와 같다.
  - **최근 24시간** — 롤링 창. 수집 건수, 걸러짐 건수 (화면 06·09·10 의 `오늘 수집`, `오늘 걸러짐`). 응답에 `window_hours` 로 되돌려 준다.
- ID 는 전부 **문자열**이다. 알림 ID(`alert_id`)는 `items.id` 를 문자열로 바꾼 값이다. 소스 ID 는 `sources.name` (`rss:anthropic`) 이며 경로에 넣을 때 URL 인코딩한다 (`rss%3Aanthropic`, 콜론은 그대로 둬도 된다).
- 실수 점수는 서버가 반올림하지 않은 원값(float)을 준다. 표시 자릿수는 클라이언트가 정한다 (점수·trust 2자리, trust 목록 표시는 1자리).
- `null` 은 "값 없음" 이다. 빈 목록은 `[]` 로 주고 `null` 로 주지 않는다.

### 1.3 페이지네이션

목록 API(피드·찜·걸러진 항목)는 **커서** 방식이다.

| 쿼리 | 기본 | 설명 |
|---|---|---|
| `limit` | 20 | 1~100 |
| `cursor` | 없음 | 직전 응답의 `next_cursor` 를 그대로 넣는다. 불투명 문자열(base64url JSON)이며 클라이언트가 해석하지 않는다 |

응답 봉투는 `{"items": [...], "next_cursor": "..." | null}`. `next_cursor` 가 `null` 이면 끝이다. 정렬 키가 같은 행은 `id` 내림차순으로 안정 정렬한다.

### 1.4 오류 형식

```json
{
  "error": {
    "code": "validation_error",
    "message": "selected_categories 는 1개 이상이어야 합니다.",
    "details": {"field": "selected_categories"}
  }
}
```

| HTTP | `code` | 언제 |
|---|---|---|
| 400 | `bad_request` | 커서 해석 실패, 잘못된 쿼리 조합 |
| 401 | `unauthorized` | 토큰 없음·불일치·서버 토큰 미설정 |
| 404 | `not_found` | 알림·소스·폴더·찜·리포트가 없음 |
| 409 | `conflict` | 폴더 이름 중복 |
| 409 | `channel_not_connected` | 연결 정보(.env)가 없는 채널을 켜려 함 (텔레그램 토큰 없음, FCM 서비스 계정 없음) |
| 422 | `validation_error` | 본문·쿼리 검증 실패. FastAPI 기본 422 를 이 형식으로 바꿔 준다. `details.errors` 에 pydantic 오류 목록 |
| 503 | `unavailable` | DB 연결 실패 |

`message` 는 사람이 읽는 한국어 문장이다. 클라이언트는 `code` 로 분기하고 `message` 는 스낵바에 그대로 보여 줘도 된다.

### 1.5 쓰기 규칙

- 토글·세그먼트처럼 **즉시 저장** 하는 화면(05·06)은 `PATCH` 부분 갱신을 쓴다. 응답은 갱신 후 전체 객체다.
- **명시 저장** 화면(04 관심사)은 `PUT` 전체 교체를 쓴다.
- 멱등 동작(찜 추가, 피드백 설정)은 `PUT`, 해제는 `DELETE`. 이미 없는 것을 `DELETE` 해도 204 다.
- 낙관적 갱신을 권장한다. 실패하면 클라이언트가 이전 상태로 되돌리고 `message` 를 보여 준다.

## 2. 열거형 (값은 영어 snake_case, 한국어 라벨은 클라이언트 상수)

한국어 라벨은 `mobile/lib/core/labels.dart` 가 소유한다. 서버는 값만 준다. 예외는 **관심 카테고리(taxonomy)** 로, 설정 파일에서 바뀔 수 있어 라벨을 서버(`GET /meta`)가 준다. slug 는 `config/rules.yaml` `policy.taxonomy`, 라벨은 `config/app.yaml` `taxonomy_labels` 에서 온다 (6.3).

### `delivery_mode` — 알림 전달 강도 (배지)

| 값 | 라벨 | 배지 색 | 백엔드 `notifications.level` |
|---|---|---|---|
| `instant` | 즉시 | primary-soft / primary | `push` |
| `quiet` | 조용히 | subtle / muted (`#F0EEE9` / `#6B6862`) | `silent` |
| `feed_only` | 피드만 | feed-soft / feed (`#EEF5EE` / `#3D7A4A`) | `feed` |
| `experiment` | 실험 | warn-soft / warn | `explore` |

`notifications.level = cluster_dup` (v2 계획서 Task 3, 클러스터 하루 상한으로 보내지 않은 기록)은 전달이 아니므로 `delivery_mode` 가 없다. 피드·통계·push 상한 어디에도 들어가지 않고, 걸러진 항목(4.6)에 일곱째 관문 `cluster_dup` 으로 나온다.

### `feedback` — 사용자 판정

| 값 | 라벨 | 백엔드 `feedback.verdict` |
|---|---|---|
| `useful` | 유용 | `useful` |
| `not_useful` | 불필요 | `useless` |

DB 값은 바꾸지 않는다. API 계층에서만 `useless ↔ not_useful` 로 옮긴다.

### `feed_filter` — 피드 칩

| 값 | 라벨 | 조건 |
|---|---|---|
| `all` | 전체 | 모든 전달 항목 |
| `instant` | 즉시 | `delivery_mode = instant` |
| `quiet` | 조용히 | `delivery_mode = quiet` |
| `experiment` | 실험 | `delivery_mode = experiment` |
| `useful` | 👍 유용 | `feedback = useful` |

### `kind` — 변화 종류 (백엔드 `app/schemas.py` `Kind` 그대로)

| 값 | 라벨 |
|---|---|
| `release_major` | 메이저 릴리즈 |
| `release_patch` | 패치 릴리즈 |
| `technique` | 기법·논문 |
| `survey` | 서베이·전망 |
| `news` | 뉴스·사건 |
| `tutorial` | 튜토리얼 |
| `promo` | 홍보·구인 |
| `other` | 기타 |

`Kind` 와 선별의 `kind` 출력, `scoring.kind_weights` 는 main 에 이미 있다 (`app/pipeline/triage.py`, `app/config.py` — 키 타입이 `Kind` 라 범위 밖 키는 기동 실패). 화면 04 는 디자인대로 6행(`news`·`other` 제외)을 위 순서로 보여 주고, 10 그룹은 건수가 있는 kind 전부를 건수순으로 보여 준다.

### `gate` — 걸러진 관문

| 값 | 라벨 (범례 / 배지) | GateBar 색 | 판정 근거 |
|---|---|---|---|
| `exclude` | exclude / exclude | `gate/exclude` | 마지막 결정이 `rule` 탈락이고 reason 이 `exclude_keyword`·`exclude_domain` |
| `dedup` | 중복 / 중복 | `gate/dedup` | `rule` 탈락, reason `dup` |
| `stale` | 오래됨 / 오래됨 | `gate/exclude` 와 같은 색에 빗금 없음 (권장 `#CFCBC2`) | `score` 탈락, reason `stale` (72시간 신선도 가드) |
| `screening` | 선별 / 선별 탈락 | `gate/screening` | `triage` 오류 폐기, 또는 `score` 탈락이면서 선별 relevance < `screening_relevance_floor`(기본 0.5) |
| `score` | 점수 / 점수 탈락 | `gate/score` | 그 밖의 `score` 탈락 |
| `judgment` | 판정 / 판정 탈락 | `gate/judgment` | `llm` 판정 false |
| `cluster_dup` | 클러스터 하루 1건 / 클러스터 하루 1건 | 디자인 없음 (권장 `#E0A373` `accent/warn-muted`, 태그는 `#F0EEE9` / `#6B6862`) | 판정 통과했지만 발송 잡이 클러스터 하루 상한으로 억제 (`notifications.level='cluster_dup'` 만 있고 항목 상태 `SENT`) |

주의 — 백엔드 선별(triage)은 탈락시키지 않고 relevance 만 매긴다. `screening` 은 "relevance 가 낮아서 점수에서 떨어진 것" 을 보여 주기 위한 **표시용 분류** 다. 디자인에 없던 `stale` 을 여섯째, `cluster_dup` 을 일곱째 구간으로 추가한다. `cluster_dup` 은 결정 로그가 아니라 알림 행으로 판별하는 유일한 관문이다.

### `routing` — 07 "이 알림이 온 이유" 우측 라벨

| 값 | 라벨 | 조건 |
|---|---|---|
| `passed` | 통과 | 점수 ≥ 통과선, 판정 true |
| `explore_slot` | 경계 → 탐색 슬롯 | 탐색 슬롯으로 발송 |
| `restored` | 직접 복원 | 사용자가 걸러진 항목을 복원 |
| `dropped` | 탈락 | 발송되지 않음 (걸러진 항목을 상세로 열었을 때) |
| `cluster_dup` | 같은 이슈 → 앞 알림에 병기 | 클러스터 하루 상한으로 보내지 않음 (`level=cluster_dup`) |

### 기타

| 이름 | 값 → 라벨 |
|---|---|
| `source_type` | `rss` RSS · `github_release` GitHub 릴리즈 · `youtube` YouTube · `hackernews` Hacker News · `hf_papers` HF Papers |
| `source_group` | `blog_rss` 기술 블로그 · RSS · `paper_release_video` 논문 · 릴리즈 · 영상 · `community` 커뮤니티 |
| `importance_band` | `high` importance 5 · 4 · `mid` importance 3 · `low` importance 2 · 1 |
| `delivery_choice` (05 세그먼트) | `instant` 즉시 · `quiet` 조용히 · `feed_only` 피드만 |
| `channel` | `fcm` 앱 푸시 (FCM) · `discord` Discord 채널 · `telegram` Telegram 봇 |
| `filtered_view` | `source` 소스별 · `kind` 종류별 · `gate` 관문별 |
| `group_sort` | `count_desc` 많은 순 · `name_asc` 이름순 |
| `saved_sort` | `saved_desc` 최근 찜한 순 · `saved_asc` 오래된 순 · `delivered_desc` 알림 시간 순 |
| `platform` | `android` · `ios` |

`source_group` 은 서버가 정한다. 규칙은 `rss` 이면서 `config.family != arxiv` → `blog_rss`, `hackernews` → `community`, 나머지(arXiv RSS·`hf_papers`·`github_release`·`youtube`) → `paper_release_video`.

## 3. 공통 객체

### 3.1 `Alert` — 피드 카드 한 장

```json
{
  "id": "18342",
  "source_id": "github_release:watchlist",
  "source_name": "GitHub Releases",
  "source_type": "github_release",
  "delivered_at": "2026-09-24T02:18:00Z",
  "delivery_mode": "instant",
  "is_exploration": false,
  "title": "[릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 (v2.2.0 · v1.30.0)",
  "summary": "스트리밍 HTTP 클라이언트의 리다이렉트 처리와 OAuth 토큰 검증이 바뀐 보안 릴리즈. v1.30.0에 백포트됨.",
  "categories": ["mcp-tooling", "python-backend"],
  "tags": ["mcp", "oauth", "python"],
  "url": "https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0",
  "importance": 4,
  "is_saved": true,
  "feedback": "useful"
}
```

| 필드 | 출처 | 비고 |
|---|---|---|
| `id` | `items.id` | 피드백·찜·상세의 키 |
| `source_name` | `sources.config.display_name`, 없으면 `sources.name` | `sources.yaml` 각 항목 `config` 에 `display_name` 을 추가한다 |
| `delivered_at` | 그 항목 `notifications` 중 오류 없고 `level != cluster_dup` 인 행의 최소 `sent_at` | 채널이 여럿이어도 한 카드 |
| `delivery_mode` | 그 행의 `level` | 위 매핑표 |
| `is_exploration` | `delivery_mode == experiment` | 실험 헤더 표시용. 디자인 필드 유지 |
| `title` | 그 행의 `notifications.title` (발송한 제목, 형제 버전 병기 포함) → 없으면 `summaries.title_ko` → 없으면 `items.title` | 병기는 4.4 |
| `summary` | `summaries.summary_ko`. 요약이 없는 복원 항목은 `items.summary_raw` 앞 200자 | |
| `categories` | 그 항목의 마지막 선별 결정 `decisions(stage=triage, passed=true).details.topics` (taxonomy slug, 최대 3개) | 선별이 `topics` 를 내기 전(B3 전) 행·선별 전 항목은 `[]`. 카드는 `#slug` 로 표시 |
| `tags` | `summaries.tags` (자유 영문 키워드) | 카드에는 쓰지 않는다. 검색·디버그용 |
| `importance` | `summaries.importance` | 요약 없는 항목은 `null` |
| `is_saved` | `bookmarks` 존재 | |
| `feedback` | `feedback.verdict` (`cleared` 는 `null`) | |

### 3.2 `DroppedItem` — 걸러진 항목 한 줄

```json
{
  "id": "18107",
  "title": "Survey of Agentic Software Engineering, 2026H1",
  "url": "https://arxiv.org/abs/2609.01234",
  "source_id": "rss:arxiv-cs-se",
  "source_name": "arXiv cs.SE",
  "source_type": "rss",
  "dropped_gate": "score",
  "dropped_at": "2026-09-24T00:41:12Z",
  "relevance": 0.62,
  "kind": "survey",
  "topics": ["agent"],
  "reason": "서베이 성격의 동향 정리, 구체 수치 없음",
  "score": {
    "total": 0.41,
    "threshold": 0.45,
    "components": {"src": 0.10, "rel": 0.24, "hot": 0.0, "multi": 0.0, "fresh": 0.10, "kind": -0.15}
  },
  "matched_keywords": [],
  "exploration_candidate": false,
  "restored": false
}
```

- `relevance`·`kind`·`topics`·`reason` 은 선별 결정 행 `details` 에서 온다. 선별 전에 떨어진 항목(`exclude`·`dedup`·`stale`)은 `null` (`topics` 는 `[]`). 화면은 `topics` 를 쓰지 않지만 같은 행에서 공짜로 나온다.
- `score` 는 점수 결정 행의 `breakdown`. 점수 전 탈락이면 `null`.
- `matched_keywords` 는 `exclude` 일 때 걸린 키워드 (`["sponsored"]`).
- `exploration_candidate` 는 백엔드 탐색 후보 조건과 같다 — 점수 탈락, 점수 ∈ [통과선 − 0.10, 통과선), 발행 24시간 이내, 요약 없음.
- 사유 줄 조합은 클라이언트 몫이다. 규칙은 아래와 같다.
  - `screening` → `relevance 0.3 · survey · "관심 스택과 무관한 도메인 서베이"`
  - `score` → `0.41 (src 0.10 · rel 0.24 · kind −0.15)` (0 이 아닌 구성요소만), 탐색 후보면 `0.43 · 경계 → 내일 탐색 슬롯 후보`
  - 종류별 보기에서는 괄호 대신 소스명 → `0.41 · arXiv cs.SE`
  - `exclude` → `키워드 sponsored`, `dedup` → `같은 이슈 중복`, `stale` → `72시간 지난 항목`, `judgment` → `판정 false`, `cluster_dup` → `같은 이슈 하루 1건 → 앞 알림에 병기`
- `cluster_dup` 항목의 `dropped_at` 은 그 `cluster_dup` 알림 행의 `sent_at` 이다. 선별·점수 결정이 있으므로 `relevance`·`kind`·`score` 가 채워진다.

### 3.3 `SavedItem` — 찜 카드

```json
{
  "alert_id": "18342",
  "source_name": "GitHub Releases",
  "title": "[릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경",
  "url": "https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0",
  "delivered_at": "2026-09-14T03:02:00Z",
  "saved_at": "2026-09-14T05:40:00Z",
  "folder": {"id": "2", "name": "적용해보기"},
  "memo": "trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인",
  "is_read": false,
  "read_at": null
}
```

메타 행 날짜(`9월 14일`)는 `saved_at` 을 쓴다. `folder` 가 `null` 이면 미분류이고 배지를 숨긴다.

### 3.4 `Source` — 수집 소스 한 줄

```json
{
  "id": "rss:arxiv-cs-ai",
  "display_name": "arXiv cs.AI",
  "type": "rss",
  "group": "paper_release_video",
  "enabled": true,
  "poll_interval_min": 60,
  "trust": 0.58,
  "trust_base": 0.5,
  "trust_calibrated": 0.58,
  "consecutive_failures": 0,
  "error_hint": null,
  "last_error": null,
  "last_polled_at": "2026-09-24T02:00:03Z",
  "repo_count": null
}
```

- `trust` = `trust_calibrated ?? trust_base`. `trust_calibrated` 는 `sources.trust_adjusted` 이며 미보정이면 `null` (상태 줄의 `보정 0.5 → 0.58` 은 이 값이 있을 때만).
- `consecutive_failures` = `sources.fail_count`. 0 보다 크면 오류색 상태 줄.
- `error_hint` 는 `sources.yaml` 의 `config.error_hint` (예 `미러 확인 필요`). 없으면 `null` 이고, 클라이언트는 `last_error` 앞 30자를 대신 보여 준다.
- `repo_count` 는 `github_release` 의 `config.repos` 길이, 그 밖은 `null`.

## 4. 엔드포인트 (화면별)

### 4.0 공통

#### `GET /meta` — 마스터 데이터

앱 기동 시 한 번 읽고 캐시한다.

```json
{
  "server_time": "2026-09-24T03:00:00Z",
  "timezone": "Asia/Seoul",
  "taxonomy": [
    {"slug": "llm-model", "label": "새 모델·벤치마크"},
    {"slug": "agent", "label": "에이전트 패턴"},
    {"slug": "mcp-tooling", "label": "MCP·IDE·CLI"},
    {"slug": "inference-opt", "label": "추론 최적화"},
    {"slug": "rag-retrieval", "label": "RAG·검색"},
    {"slug": "training-finetune", "label": "학습·파인튜닝"},
    {"slug": "python-backend", "label": "Python 백엔드"},
    {"slug": "web-frontend", "label": "Next.js·React"},
    {"slug": "devops-infra", "label": "DevOps·인프라"},
    {"slug": "ai-safety-eval", "label": "안전·평가"},
    {"slug": "dev-community", "label": "논쟁·가격·정책"},
    {"slug": "video", "label": "영상 채널"}
  ],
  "kinds": ["release_major", "release_patch", "technique", "survey", "news", "tutorial", "promo", "other"],
  "limits": {
    "kind_weight": {"min": -0.5, "max": 0.5, "step": 0.05},
    "daily_push_cap": {"min": 1, "max": 50},
    "watch_keywords_max": 50,
    "folder_name_max": 30,
    "memo_max": 500
  },
  "resurface_unread_after_days": 7
}
```

`taxonomy` 는 `rules.policy.taxonomy` 순서대로, 라벨은 `config/app.yaml` `taxonomy_labels[slug]` (없으면 slug 그대로)다. 선별 프롬프트는 slug 만 쓰고 라벨을 보지 않는다.

### 4.1 화면 03 피드

#### `GET /stats/today` — 요약 줄

```json
{
  "date": "2026-09-24",
  "timezone": "Asia/Seoul",
  "push_sent_today": 4,
  "daily_push_cap": 15,
  "window_hours": 24,
  "collected_count": 612,
  "filtered_count": 571
}
```

- `push_sent_today` 는 오늘(달력일) `level=push` 로 발송된 **서로 다른 항목 수**. 채널이 여럿이어도 한 번만 센다.
- `filtered_count` 는 `GET /filtered/summary` 의 `filtered_total` 과 같은 정의다.

#### `GET /feed` — 알림 이력

| 쿼리 | 값 | 기본 |
|---|---|---|
| `filter` | `feed_filter` | `all` |
| `limit`, `cursor` | 1.3 참조 | |

정렬은 `delivered_at` 내림차순. 기간 제한 없이 과거까지 커서로 내려간다 (화면 제목 `오늘` 은 문구일 뿐이다). `level=cluster_dup` 만 있는 항목은 나오지 않는다. 모든 조건에 `notifications.user_id = 현재 사용자` 가 붙는다.

```json
{
  "items": [
    {"id": "18342", "source_name": "GitHub Releases", "delivery_mode": "instant", "...": "Alert 3.1"},
    {
      "id": "18301",
      "source_id": "rss:arxiv-cs-cl",
      "source_name": "arXiv cs.CL",
      "source_type": "rss",
      "delivered_at": "2026-09-23T23:55:00Z",
      "delivery_mode": "experiment",
      "is_exploration": true,
      "title": "BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배",
      "summary": "고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개.",
      "categories": ["inference-opt"],
      "tags": ["kv-cache", "long-context"],
      "url": "https://arxiv.org/abs/2609.04567",
      "importance": 4,
      "is_saved": false,
      "feedback": null
    }
  ],
  "next_cursor": "eyJ0IjoiMjAyNi0wOS0yM1QyMzo1NTowMFoiLCJpZCI6MTgzMDF9"
}
```

#### `PUT /alerts/{alert_id}/feedback` — 유용·불필요 설정/변경

요청 `{"verdict": "useful"}` (`useful` | `not_useful`). 응답 200.

```json
{"alert_id": "18342", "feedback": "useful", "updated_at": "2026-09-24T03:01:10Z"}
```

- `db/feedback.py` `upsert_feedback(session, user_id, item_id, verdict, source='app')` 를 부른다. 유니크는 `(user_id, item_id)` 다 (v2 계획서 Task 1).
- 앱에서 정한 판정은 디스코드 리액션 폴링(`jobs/feedback.py`)이 덮어쓰지 않는다. 디스코드·텔레그램에서 먼저 누른 판정은 앱이 바꿀 수 있다.
- 걸러진 항목에도 쓸 수 있다 (복원은 4.6 이 따로 한다).

#### `DELETE /alerts/{alert_id}/feedback` — 판정 해제

204. 행을 지우지 않고 `verdict='cleared', source='app'` 으로 바꾼다 (리액션 폴링이 되살리지 못하게 하는 표시). 모든 집계·사례 검색은 `useful`·`useless` 만 센다.

#### 찜 토글

피드 카드의 찜 버튼은 4.7 의 `PUT /saved/{alert_id}` (본문 없음 → 미분류) 와 `DELETE /saved/{alert_id}` 를 쓴다.

### 4.2 화면 07 피드백 · 판정 근거

#### `GET /alerts/{alert_id}` — 상세 + 근거

`Alert` 전체에 `rationale` 을 붙인다. 발송된 적 없는 항목도 조회된다 (`delivered_at`·`delivery_mode` 가 `null`, `routing = dropped`).

```json
{
  "id": "18301",
  "source_name": "arXiv cs.CL",
  "delivered_at": "2026-09-23T23:55:00Z",
  "delivery_mode": "experiment",
  "title": "BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배",
  "summary": "고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개.",
  "url": "https://arxiv.org/abs/2609.04567",
  "is_saved": false,
  "feedback": "useful",
  "...": "나머지 Alert 필드",
  "rationale": {
    "score": {
      "total": 0.43,
      "threshold": 0.45,
      "components": {"src": 0.10, "rel": 0.25, "hot": 0.0, "multi": 0.0, "fresh": 0.10, "kind": 0.0}
    },
    "routing": "explore_slot",
    "screening": {
      "relevance": 0.83,
      "kind": "technique",
      "topics": ["inference-opt"],
      "reason": "KV 캐시 압축의 구체 기법과 수치, 코드 공개"
    },
    "judgment": {
      "importance": 4,
      "worth_notifying": true,
      "similar_feedback": [
        {"alert_id": "17220", "feedback": "useful", "title": "PagedAttention v2 — 페이지 단위 KV 캐시 재사용"}
      ]
    },
    "trust_note_source": "arXiv cs.CL"
  }
}
```

- `score` 는 마지막 `score` 결정 행의 `breakdown`. 바 채움 폭은 디자인 원본(`bar()`)대로 모든 구성요소에 공통 눈금 0.5 를 쓴다 (채움 = min(값 ÷ 0.5, 1) × 트랙 폭). 클라이언트 상수이며 서버는 눈금을 주지 않는다. 음수(`kind`)는 채움 없이 값만 경고색으로 표시한다.
- 디자인은 `src·rel·fresh·kind` 4행이다. 앱은 이 4행을 항상 보여 주고 `hot`·`multi` 는 0 이 아닐 때만 행을 추가한다.
- `screening` 은 마지막 선별 결정 `details` 의 `relevance`·`kind`·`topics`·`reason` 이다. 선별 전 항목은 `null`, `topics` 가 없는 옛 행은 `[]`. `judgment` 가 없으면(판정 전) `null`.
- `cluster_dup` 로만 기록된 항목은 `delivered_at`·`delivery_mode` 가 `null` 이고 `routing = cluster_dup` 이다.
- `judgment.similar_feedback` 는 판정 호출 때 프롬프트에 넣은 최근접 피드백 사례다. 새로 `decisions.details.examples` 에 남기며, 이전 행은 `[]` 다. 화면은 첫 건만 쓴다.
- `trust_note_source` 는 안내 카드 문장(`… arXiv cs.CL의 신뢰도를 보정합니다`)에 넣을 소스 표시명이다.

#### `GET /feedback/recent` — 최근 판정

| 쿼리 | 기본 |
|---|---|
| `limit` | 5 (최대 20) |

```json
{
  "today_count": 3,
  "items": [
    {"alert_id": "18342", "feedback": "useful", "title": "MCP Python SDK v2.2.0 — HTTP 리다이렉트…", "created_at": "2026-09-24T02:20:00Z"},
    {"alert_id": "18011", "feedback": "not_useful", "title": "SDLC 에이전트 서베이 — 2026 상반기 동향", "created_at": "2026-09-23T09:10:00Z"}
  ]
}
```

`today_count` 는 오늘(달력일) 판정 수, `items` 는 기간과 무관한 최근 N건 (디자인의 "오늘 3건" 과 `어제` 행이 같이 있는 모순을 이렇게 정리한다). 채널(앱·디스코드·텔레그램)을 가리지 않고 현재 사용자 판정만 센다.

판정 버튼은 4.1 의 `PUT/DELETE /alerts/{id}/feedback` 을 그대로 쓴다.

### 4.3 화면 04 관심사

#### `GET /settings/interests`

```json
{
  "profile": {
    "self_description": "AI 시스템 개발자. LLM 애플리케이션·에이전트·MCP를 직접 만든다. 주력 스택: Python(FastAPI, SQLAlchemy, Pydantic), Postgres, Docker, TypeScript/Next.js.",
    "not_interested": "채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠"
  },
  "selected_categories": ["llm-model", "agent", "mcp-tooling", "inference-opt", "python-backend", "web-frontend", "dev-community", "video"],
  "watch_keywords": ["claude", "mcp", "langgraph", "fastapi", "pydantic", "next.js", "uv", "anthropics/*"],
  "kind_weights": {
    "release_major": 0.0, "release_patch": 0.0, "technique": 0.0, "survey": -0.15,
    "news": 0.0, "tutorial": -0.05, "promo": -0.30, "other": 0.0
  },
  "updated_at": "2026-09-20T11:00:00Z"
}
```

| API 필드 | 유효 설정 (YAML 기본값 위에 `user_prefs` 덮어쓰기) |
|---|---|
| `profile.self_description` | `rules.policy.interests` |
| `profile.not_interested` | `rules.policy.not_interested` |
| `selected_categories` | `rules.policy.categories` (새 필드, 기본값은 `rules.policy.taxonomy` 전체) |
| `watch_keywords` | `rules.policy.focus_stack` + `rules.policy.focus_repos` 를 이 순서로 이은 목록 |
| `kind_weights` | `rules.scoring.kind_weights` (8개 전부, 설정에 없는 kind 는 0. main 기본값은 survey −0.15 · tutorial −0.05 · promo −0.30, 나머지 0) |

`updated_at` 은 `user_prefs.updated_at`, 한 번도 저장하지 않았으면 `null`.

#### `PUT /settings/interests` — 명시 저장 (헤더 `저장`)

요청은 GET 응답에서 `updated_at` 을 뺀 전체 객체. 응답은 저장 후 GET 과 같은 객체.

검증 (위반 시 422).
- `profile.self_description` 1~1000자, `not_interested` 0~500자.
- `selected_categories` 1개 이상, 전부 `policy.taxonomy` 안의 slug, 중복 없음.
- `watch_keywords` 0~50개, 각 1~50자, 앞뒤 공백 제거 후 대소문자 무시 중복 제거. `/` 를 포함한 값은 `focus_repos`, 나머지는 `focus_stack` 으로 저장한다.
- `kind_weights` 키는 `kind` 8개 중에서, 값은 −0.50 ~ +0.50. 서버가 소수 2자리로 반올림한다. 빠진 키는 현재 유효값을 유지한다 (앱은 편집하지 않는 `news`·`other` 도 GET 값을 그대로 보낸다).
- 모르는 키(`updated_at` 포함)를 보내면 422. 본문이 맞아도 저장된 다른 설정과 합쳐 검증에 실패하면 저장하지 않고 422 이며 `details.reason` 에 이유가 있다 (05·06 저장도 같다).

저장 즉시 다음 선별·판정 호출부터 반영된다 (프로세스 안의 유효 설정 캐시를 갈아끼운다). 이미 매긴 점수는 다시 계산하지 않는다.
`selected_categories` 는 거름망이 아니라 힌트다. `render_policy` 가 선별·판정 프롬프트의 정책 블록에 `관심 카테고리: llm-model, agent, …` 한 줄을 넣는다. 선별은 여전히 `policy.taxonomy` 12개 전체에서 `topics` 를 고른다. 사용자별 카테고리 필터는 v2 계획서 범위 밖이다.

키워드 추가·삭제, 카테고리 선택, 가중치 편집은 모두 클라이언트 로컬 상태에서 바꾸고 이 PUT 한 번으로 저장한다.

### 4.4 화면 05 알림 설정

#### `GET /settings/notifications`

```json
{
  "channels": {
    "fcm": {"enabled": true, "connected": true, "device_count": 1},
    "discord": {"enabled": true, "connected": true, "channel_name": "#trend-alerts", "reaction_sync": true},
    "telegram": {"enabled": false, "connected": false}
  },
  "daily_push_cap": 15,
  "quiet_hours": {"start": "23:00", "end": "08:00", "timezone": "Asia/Seoul"},
  "dedupe_same_issue_daily": true,
  "delivery_by_importance": {"high": "instant", "mid": "quiet", "low": "feed_only"},
  "exploration_slot": {"enabled": true, "daily_limit": 1},
  "updated_at": "2026-09-20T11:00:00Z"
}
```

| API 필드 | 유효 설정 / 근거 |
|---|---|
| `channels.*.enabled` | `rules.notify.channels.{fcm,discord,telegram}` (새 필드, 기본 fcm·discord true, telegram false) |
| `channels.fcm.connected` | `.env` `FCM_PROJECT_ID`·`FCM_SERVICE_ACCOUNT_FILE` 존재 |
| `channels.fcm.device_count` | 활성 `devices` 수. 0 이면 행 보조 줄에 `등록된 기기 없음` 권장 |
| `channels.discord.connected` | `DISCORD_BOT_TOKEN`·`DISCORD_CHANNEL_ID` 존재 |
| `channels.discord.channel_name` | `.env` `DISCORD_CHANNEL_NAME` (새, 표시 전용). 없으면 `#` + 채널 ID, 둘 다 없으면 `null` |
| `channels.discord.reaction_sync` | `connected` 와 같음 (리액션 폴링 잡이 돈다) |
| `channels.telegram.connected` | `TELEGRAM_BOT_TOKEN`·`TELEGRAM_CHAT_ID` 존재 |
| `daily_push_cap` | `rules.notify.daily_push_cap` |
| `quiet_hours.start` / `end` | `rules.notify.quiet_start_hour` / `quiet_end_hour` 를 `HH:00` 으로 |
| `quiet_hours.timezone` | `rules.notify.timezone` (읽기 전용) |
| `dedupe_same_issue_daily` | `rules.notify.cluster_daily_cap > 0` (v2 계획서 Task 3, 기본 1) |
| `delivery_by_importance` | `rules.notify.delivery_by_importance` (새, 기본 high=instant, mid=quiet, low=feed_only — 현재 하드코딩 `level_for` 와 같은 값) |
| `exploration_slot.enabled` | `rules.notify.explore_enabled` (새, 기본 true). `daily_limit` 은 1 고정 (정적) |

#### `PATCH /settings/notifications` — 즉시 저장

바꿀 키만 보낸다 (중첩 병합). 응답은 GET 과 같은 전체 객체.

```json
{"channels": {"telegram": {"enabled": true}}}
{"daily_push_cap": 20}
{"quiet_hours": {"start": "00:00", "end": "07:00"}}
{"dedupe_same_issue_daily": false}
{"delivery_by_importance": {"mid": "feed_only"}}
{"exploration_slot": {"enabled": false}}
```

검증.
- `daily_push_cap` 1~50.
- `quiet_hours.start`·`end` 는 `HH:00` 만 허용한다 (백엔드 정책이 시 단위). 분이 0 이 아니면 422. 같은 값이면 무음 없음.
- `timezone`, `connected`, `channel_name`, `reaction_sync`, `device_count`, `daily_limit` 은 읽기 전용이며 보내면 422.
- `dedupe_same_issue_daily` 는 `cluster_daily_cap` 에 이렇게 옮긴다. `false` → 덮어쓰기 `notify.cluster_daily_cap = 0`. `true` → YAML 값이 1 이상이면 덮어쓰기 키를 지우고(YAML 값 복귀), 0 이면 1 을 쓴다. 상한 숫자 자체는 앱에서 바꾸지 않는다.
- `connected=false` 인 채널을 `enabled=true` 로 바꾸면 409 `channel_not_connected`. 앱은 토글을 되돌리고 `message` 를 보여 준다 (연결 플로우 디자인은 없다).

발송 동작 (백엔드 `notify/policy.py` 가 이 설정을 읽는다).
- importance → `delivery_by_importance` 로 강도를 정한다. `feed_only` 는 어느 채널로도 보내지 않고 피드에만 남긴다.
- 무음 시간 중 도착한 `instant`·`quiet` 항목은 **피드에만** 남긴다 (화면 문구 `무음 중엔 피드에만 쌓입니다` 를 따른다. 지금은 아침까지 미뤘다가 push 하는데, 사용자 결정으로 화면 쪽으로 바꾼다).
- 하루 push 상한을 넘은 `instant` 는 `quiet` 로 낮춘다 (현행 유지).
- **클러스터 하루 상한** (v2 계획서 Task 3, `cluster_daily_cap`, 0 = 끔). 강도가 `instant`·`quiet` (`push`·`silent`) 로 정해진 항목만 검사한다. `feed_only` 는 원래 보내지 않으므로 검사하지 않는다.
  - `cluster_sent_today(session, cluster_id, user_id, now)` 가 오늘(달력일) 같은 `cluster_id` 로 `push`·`silent`·`explore` 가 나간 **서로 다른 항목 수**를 센다 (v2 계획서 SQL 은 `count(*)` 인데, 채널 팬아웃 뒤에는 한 항목이 여러 행이라 `count(DISTINCT n.item_id)` 로 바꾼다).
  - 그 수가 상한 이상이면 보내지 않고 `notifications(level='cluster_dup', channel='app', message_id=NULL, user_id)` 한 행만 남기며 항목은 `SENT` 로 둔다. `decisions` 에는 남기지 않는다 (발송 정책이지 판정이 아니다). 앱에서는 걸러진 항목의 `cluster_dup` 관문으로 보이고 👍 복원할 수 있다 (4.6).
  - 보내는 항목은 같은 클러스터의 다른 항목(상태 `SCORED`·`QUEUED`·`SENT`, 72시간 창) 제목에서 `dedupe.version_tokens` 로 버전을 모아 `decorate_title(title_ko, sibling_versions(item.title, titles))` 로 제목 끝에 `(v2.2.0 · v1.30.0)` 을 붙인다. 버전이 2개 미만이면 그대로다. 모든 채널이 같은 제목을 받고, 그 제목을 `notifications.title` 에 남긴다 (피드 카드 제목, 3.1).
  - 탐색 슬롯 후보 쿼리는 `cluster_sent_today == 0` 인 클러스터만 고른다.
  - 순서는 강도 결정 → 무음 시간 → push 상한 강등 → 클러스터 상한 검사다. 무음 시간으로 `feed_only` 가 된 항목은 검사하지 않는다.
- 켜진 채널 전부로 보낸다. 채널마다 `notifications` 행이 하나씩 남는다. 켜진 채널이 없으면 피드에만 남는다.
- `exploration_slot.enabled=false` 면 탐색 슬롯 판정·발송을 하지 않는다.

### 4.5 화면 06 수집 소스

#### `GET /sources`

```json
{
  "stats": {
    "enabled_count": 9,
    "total": 10,
    "window_hours": 24,
    "items_collected": 612,
    "llm_budget": {
      "triage": {"used": 41, "cap": 60},
      "judge": {"used": 18, "cap": 300},
      "explore": {"used": 1, "cap": 3}
    }
  },
  "sources": [
    {"id": "rss:anthropic", "display_name": "Anthropic", "type": "rss", "group": "blog_rss", "enabled": true, "poll_interval_min": 15, "trust": 1.0, "trust_base": 1.0, "trust_calibrated": null, "consecutive_failures": 5, "error_hint": "미러 확인 필요", "last_error": "HTTPStatusError: 404", "last_polled_at": "2026-09-23T20:00:00Z", "repo_count": null},
    {"id": "github_release:watchlist", "display_name": "GitHub Releases", "type": "github_release", "group": "paper_release_video", "enabled": true, "poll_interval_min": 30, "trust": 1.0, "trust_base": 1.0, "trust_calibrated": null, "consecutive_failures": 0, "error_hint": null, "last_error": null, "last_polled_at": "2026-09-24T02:30:00Z", "repo_count": 10},
    {"id": "youtube:codingapple", "display_name": "코딩애플", "type": "youtube", "group": "paper_release_video", "enabled": false, "poll_interval_min": 15, "trust": 0.52, "trust_base": 0.6, "trust_calibrated": 0.52, "consecutive_failures": 0, "error_hint": null, "last_error": null, "last_polled_at": "2026-09-22T10:00:00Z", "repo_count": null}
  ],
  "planned_sources": ["Reddit", "GitHub Trending", "X"]
}
```

- 목록은 `sources.yaml` 에 있는 소스만 (YAML 에서 빠져 비활성화된 과거 행은 제외). 순서는 YAML 순서, 앱은 `group` 으로 섹션을 나눈다 (`community` 섹션은 디자인에 없으므로 라벨 `커뮤니티` 로 추가).
- 디자인 Stat `LLM 예산 41 / 60` 은 `llm_budget.triage` 다 (선별 호출 상한). 판정·탐색 예산은 보조 정보. `used` 는 오늘(달력일) `llm_calls` 예약 수이며 상한과 같은 기준으로 센다 — `judge.used` 는 판정 예산 전체(판정 + 탐색 판정), `explore.used` 는 탐색 판정만.
- `planned_sources` 는 **정적** (`config/app.yaml`). 디자인의 `Hacker News` 는 이미 구현된 소스(`hackernews:front`)라 목록에서 뺐다.
- 소스 추가(헤더 `+`)는 v1 범위 밖이다. 앱은 `준비 중` 토스트를 띄운다 (사용자 결정).

#### `PATCH /sources/{source_id}` — on/off

요청 `{"enabled": false}`. 응답은 갱신된 `Source`. `sources.yaml` 에 없는 ID 는 404 `not_found`.

- `sources.enabled` 와 `user_prefs.data.sources.{name}.enabled` 를 같이 쓴다. 기동 시 `sync_sources` 가 YAML 값 위에 이 덮어쓰기를 적용하므로 재시작해도 유지된다.
- 스케줄러는 YAML 의 모든 소스에 잡을 등록하고 `run_source` 가 비활성 소스를 건너뛴다. 그래서 켜고 끌 때 잡을 다시 등록할 필요가 없다.

### 4.6 화면 09 · 10 걸러진 항목

공통 쿼리 `hours` (기본 24, 1~168). 걸러진 항목은 둘을 합친 것이다.
- 상태가 `DROPPED`·`FILTERED_OUT` 이고 마지막 탈락 결정(사용자 복원 결정 제외)의 `created_at` 이 창 안에 있는 항목 (관문 6개).
- 현재 사용자의 `notifications` 가 `level='cluster_dup'` 행뿐이고 그 `sent_at` 이 창 안에 있는 항목 (관문 `cluster_dup`, 상태는 `SENT`). 복원한 뒤에도 목록에 남고 `restored=true` 다.

#### `GET /filtered/summary` — 요약 카드

```json
{
  "window_hours": 24,
  "filtered_total": 571,
  "collected_total": 612,
  "gate_counts": {"exclude": 9, "dedup": 58, "stale": 0, "screening": 318, "score": 164, "judgment": 22, "cluster_dup": 0},
  "borderline": {"count": 154, "range": [0.35, 0.45]},
  "unclassified_count": 67
}
```

- `collected_total` 은 창 안에 적재(`items.fetched_at`)된 항목 수.
- `borderline.range` = [통과선 − 0.10, 통과선]. 탐색 슬롯 후보 폭(`jobs/notify.py` `EXPLORE_BAND`)과 같다.
- `unclassified_count` 는 kind 가 없는 항목(선별 전 탈락, `exclude`+`dedup`+`stale`).

#### `GET /filtered/groups` — 그룹 목록

| 쿼리 | 값 | 기본 |
|---|---|---|
| `view` | `filtered_view` | `source` |
| `sort` | `group_sort` | `count_desc` |
| `hours` | | 24 |

```json
{
  "view": "kind",
  "groups": [
    {
      "key": "survey",
      "count": 187,
      "gate_counts": {"exclude": 0, "dedup": 0, "stale": 0, "screening": 60, "score": 120, "judgment": 7, "cluster_dup": 0},
      "source": null,
      "kind": "survey",
      "gate": null,
      "low_relevance_ratio": 0.32,
      "kind_weight": -0.15,
      "kind_feedback": {"not_useful": 4, "total": 4},
      "penalty_active": true,
      "borderline_count": 12,
      "exclude_keyword_hits": 0,
      "preview": [
        {"id": "18107", "title": "Survey of Agentic Software Engineering, 2026H1", "source_name": "arXiv cs.SE", "dropped_gate": "score", "...": "DroppedItem 3.2"}
      ]
    },
    {
      "key": "unclassified",
      "count": 67,
      "gate_counts": {"exclude": 9, "dedup": 58, "stale": 0, "screening": 0, "score": 0, "judgment": 0, "cluster_dup": 0},
      "source": null, "kind": null, "gate": null,
      "low_relevance_ratio": null, "kind_weight": null, "kind_feedback": null,
      "penalty_active": false, "borderline_count": 0, "exclude_keyword_hits": 9,
      "preview": []
    }
  ]
}
```

`view=source` 일 때 그룹 예시.

```json
{
  "key": "rss:arxiv-cs-ai",
  "count": 312,
  "gate_counts": {"exclude": 0, "dedup": 3, "stale": 0, "screening": 221, "score": 80, "judgment": 8, "cluster_dup": 0},
  "source": {"id": "rss:arxiv-cs-ai", "display_name": "arXiv cs.AI", "type": "rss"},
  "kind": null, "gate": null,
  "low_relevance_ratio": 0.71,
  "kind_weight": null, "kind_feedback": null, "penalty_active": false,
  "borderline_count": 40, "exclude_keyword_hits": 0,
  "preview": ["DroppedItem ×3"]
}
```

- `key` — `source` 보기는 소스 ID, `kind` 보기는 kind 값 또는 `unclassified` (항상 마지막), `gate` 보기는 `gate` 값.
- `low_relevance_ratio` — 선별 결과가 있는 항목 중 relevance < `screening_relevance_floor` 비율. 선별 결과가 없으면 `null`.
- `kind_feedback` — 최근 30일, 그 kind 로 선별된 항목에 붙은 판정 수. `penalty_active` = 현재 `kind_weights[kind] < 0`. 백엔드에 "자동 감점" 학습은 없고 설정값 감점이다.
- `preview` 는 최신 3건. 펼침 카드의 나머지는 아래 목록 API 로 더 불러온다.
- 요약 줄 조합은 클라이언트 몫이다.
  - 소스별 — `low_relevance_ratio ≥ 0.5` 이면 `선별 relevance 0.5 미만 71%`, 아니면 0 이 아닌 `gate_counts` 를 `중복 9 · 선별 11 · 점수 3` 형태로.
  - 종류별 — `kind_weight < 0` 이면 `감점 −0.15`, `kind_feedback` 이 있으면 `· 불필요 4/4 → 감점 유지 중`, `borderline_count > 0` 이면 `점수 경계(0.35–0.45) 154건`, `exclude_keyword_hits > 0` 이면 `exclude 키워드 2`, `gate_counts.cluster_dup > 0` 이면 `클러스터 하루 1건 N` (화면 10 `release_patch` 요약의 그 문구). `unclassified` 는 `선별 전 탈락 — kind 없음`.
  - 관문별 (디자인 없음) — 그룹 제목은 gate 라벨, 요약은 상위 소스 2개 (`arXiv cs.AI 221 · arXiv cs.CL 64`)를 `preview` 에서 만든다.

#### `GET /filtered/items` — 그룹 펼침 더 보기

쿼리 `view`, `key` (필수), `hours`, `limit`, `cursor`. 정렬은 `dropped_at` 내림차순. 응답 `{"items": [DroppedItem], "next_cursor": ...}`.

#### `POST /filtered/items/{item_id}/restore` — 👍 복원

본문 없음. 응답 200.

```json
{"item_id": "18107", "restored": true, "alert": {"id": "18107", "delivery_mode": "feed_only", "feedback": "useful", "...": "Alert 3.1"}}
```

서버 동작 (한 트랜잭션).
1. `feedback` 을 `useful`, `source='app'`, `user_id=DEFAULT_USER_ID` 로 upsert 한다.
2. `decisions` 에 `stage='user', passed=true, details={"reason": "restored", "user_id": 1}` 를 남긴다 (결정 로그 규칙). `decisions` 는 v2 계획서가 `user_id` 컬럼을 넣지 않은 테이블이라 `details` 에 둔다.
3. `notifications` 에 `channel='app', level='feed', user_id` 행을 추가해 피드에 올린다. 어느 채널로도 보내지 않는다.
4. LLM 을 다시 부르지 않는다. 요약이 없으면 피드 카드는 원문 제목·본문 앞부분을 쓴다.

`cluster_dup` 항목도 같은 방식으로 복원한다 (다른 관문과 일관되게). 항목 상태는 `SENT` 그대로이고 3의 `feed` 행 덕에 피드에 나온다.

이미 복원된 항목이면 같은 응답을 준다. 걸러진 항목이 아니면 404.

#### `DELETE /filtered/items/{item_id}/restore` — 복원 취소

204. 위 3의 알림 행과 2의 결정 행을 지우고, 판정은 `cleared` 로 바꾼다.

### 4.7 화면 11 찜

#### `GET /folders` — 폴더 칩

```json
{
  "total_count": 23,
  "unread_count": 7,
  "unfiled_count": 3,
  "folders": [
    {"id": "1", "name": "나중에 읽기", "count": 9, "unread_count": 4, "position": 0},
    {"id": "2", "name": "적용해보기", "count": 6, "unread_count": 2, "position": 1},
    {"id": "3", "name": "ClickMe 참고", "count": 5, "unread_count": 1, "position": 2}
  ]
}
```

`전체` 칩 = `total_count`, `안 읽음 7` = `unread_count`. 미분류 찜은 `전체` 에만 보인다.

#### `POST /folders` — 새 폴더 (`+` 칩)

요청 `{"name": "리팩터링 아이디어"}`. 201, 응답은 폴더 객체. 이름은 앞뒤 공백 제거 후 1~30자, 중복이면 409 `conflict`. `position` 은 맨 뒤.

#### `PATCH /folders/{folder_id}` / `DELETE /folders/{folder_id}`

PATCH `{"name": "...", "position": 0}` (둘 다 선택). DELETE 는 204 이고 안의 찜은 미분류가 된다 (찜 자체는 지우지 않는다). 폴더 관리 UI 디자인은 없으므로 앱은 더보기(`…`) 메뉴의 간단한 목록으로 구현한다.

#### `GET /saved` — 찜 목록

| 쿼리 | 값 | 기본 |
|---|---|---|
| `folder_id` | 폴더 ID, `unfiled`, 생략하면 전체 | 전체 |
| `unread_only` | bool | false |
| `sort` | `saved_sort` | `saved_desc` |
| `limit`, `cursor` | | |

응답 `{"items": [SavedItem], "next_cursor": ...}`.

#### `PUT /saved/{alert_id}` — 찜 추가

요청 본문은 선택. `{"folder_id": "1"}` 또는 `{}` (미분류). 새로 만들면 201, 이미 있으면 200 이고 `folder_id` 를 보냈을 때만 폴더를 바꾼다. 응답은 `SavedItem`. 알림(항목)이 없으면 404, 폴더가 없으면 404.

#### `PATCH /saved/{alert_id}` — 폴더 이동 · 메모 · 읽음

```json
{"folder_id": "2"}
{"folder_id": null}
{"memo": "trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인"}
{"memo": null}
{"is_read": true}
```

- `memo` 0~500자, 빈 문자열은 `null` 로 저장.
- `is_read=true` 이면 `read_at` 을 지금으로. 앱은 찜 카드에서 원문을 열거나 07 로 이동할 때 이 호출을 보낸다 (서버는 GET 에 부작용을 두지 않는다).

응답은 `SavedItem`.

#### `DELETE /saved/{alert_id}` — 찜 해제

204. 되돌리기 스낵바는 같은 폴더·메모로 `PUT` + `PATCH` 를 다시 보내 구현한다.

#### 읽지 않은 찜 재알림 (정책, 설정 UI 없음)

`resurface_unread_after_days`(7, `config/app.yaml`, 정적) 가 지나도록 `is_read=false` 인 찜은 한 번 FCM **조용한 알림**(`quiet`)으로 다시 알린다 (사용자 설계 문서의 "발송 잡의 silent 레벨로" 와 같은 강도다. 다만 별도 잡이며 `notifications` 에 남기지 않는다). `bookmarks.resurfaced_at` 에 기록하고 피드·통계·push 상한에는 넣지 않는다. FCM 이 꺼져 있으면 보내지 않고 기록도 하지 않는다. 무음 시간에는 보내지 않는다.

### 4.8 화면 08 내 프로필

#### `GET /profile`

| 쿼리 | 값 | 기본 |
|---|---|---|
| `period_days` | 7 · 14 · 30 | 14 |

```json
{
  "period_days": 14,
  "user": {
    "display_name": "여태호",
    "discord_connected": true,
    "onboarding_done": 8,
    "onboarding_total": 8
  },
  "stats": {
    "alerts_received": 61,
    "push_count": 38,
    "experiment_count": 9,
    "useful_count": 27,
    "not_useful_count": 15,
    "useful_ratio": 64,
    "missed_issues": 1
  },
  "category_reactions": [
    {"category": "mcp-tooling", "useful": 12, "not_useful": 2, "total": 14},
    {"category": "llm-model", "useful": 9, "not_useful": 2, "total": 11},
    {"category": "inference-opt", "useful": 6, "not_useful": 3, "total": 9},
    {"category": "agent", "useful": 4, "not_useful": 4, "total": 8},
    {"category": "video", "useful": 1, "not_useful": 5, "total": 6},
    {"category": "dev-community", "useful": 1, "not_useful": 3, "total": 4}
  ],
  "learned": {
    "kind_penalties": [
      {"kind": "survey", "weight": -0.15, "not_useful": 4, "total": 4, "active": true}
    ],
    "source_trust_changes": [
      {"source_id": "rss:arxiv-cs-cl", "source_name": "arXiv cs.CL", "from": 0.50, "to": 0.58},
      {"source_id": "youtube:codingapple", "source_name": "youtube:codingapple", "from": 0.60, "to": 0.52}
    ],
    "profile_vector_labels": 42,
    "personal_model_threshold": 50
  },
  "weekly_report_latest": {
    "id": "12",
    "title": "9월 2주차 리포트",
    "subtitle": "깔때기 · 소스별 정밀도 · 점수 구간 · 선별 보정",
    "period_start": "2026-09-08",
    "period_end": "2026-09-14"
  }
}
```

| 필드 | 정의 |
|---|---|
| `user.display_name` | `users.name` (현재 사용자). 마이그레이션이 `owner` 로 만들고 `PATCH /profile` 로 바꾼다. 아바타 이니셜은 첫 글자 (클라이언트) |
| `user.discord_connected` | 디스코드 채널 `connected` |
| `user.onboarding_done` / `total` | **정적** (`config/app.yaml`, 8 / 8). 온보딩은 범위 밖 |
| `stats.alerts_received` | 기간 안에 전달(모든 `delivery_mode`, 복원 포함)된 서로 다른 항목 수 |
| `stats.push_count` / `experiment_count` | 그중 `instant` / `experiment` |
| `stats.useful_count` / `not_useful_count` | 기간 안에 만들어진 판정 수 (채널 무관) |
| `stats.useful_ratio` | useful / (useful + not_useful) × 100 반올림 정수. 판정이 없으면 `null` |
| `stats.missed_issues` | 기간 안에 사용자가 **복원**한 걸러진 항목 수 (`decisions.stage='user'`, `details.user_id`). 캡션은 디자인 그대로 `직접 찾아본 건` (걸러진 항목을 직접 뒤져 되살린 건) |
| `category_reactions` | 기간 안 판정을 그 항목의 마지막 선별 `details.topics` 로 펼쳐 집계, `total` 내림차순 상위 6. `topics` 가 없는 항목은 세지 않는다 |
| `learned.kind_penalties` | `kind_weights < 0` 인 kind 마다 최근 30일 판정 수. `active` 는 항상 가중치 기준. 행 문구 `서베이·전망 논문 · 불필요 4 / 4 → 자동 감점 중` 은 클라이언트 조합 |
| `learned.source_trust_changes` | `trust_adjusted` 가 있고 기본값과 소수 2자리에서 다른 소스 |
| `learned.profile_vector_labels` | 현재 사용자의 전체 판정 수 (`useful`+`useless`) |
| `learned.personal_model_threshold` | **정적** 50 (`config/app.yaml`). 개인 모델은 없다 |
| `weekly_report_latest` | 현재 사용자의 가장 최근 `weekly_reports` 행, 없으면 `null` (카드 숨김) |

#### `PATCH /profile` — 표시 이름 (디자인 없음, 설정 루트에서 사용)

요청 `{"display_name": "여태호"}` (1~20자, `users.name` 에 저장). 응답은 `GET /profile` 과 같은 객체.

#### `GET /reports` · `GET /reports/{report_id}` — 주간 리포트

목록 `{"items": [{"id": "12", "title": "9월 2주차 리포트", "subtitle": "…", "period_start": "2026-09-08", "period_end": "2026-09-14", "created_at": "2026-09-15T00:00:05Z"}], "next_cursor": null}`.

상세는 표 묶음이다 (상세 디자인이 없어 범용 표로 렌더링한다).

```json
{
  "id": "12",
  "title": "9월 2주차 리포트",
  "subtitle": "깔때기 · 소스별 정밀도 · 점수 구간 · 선별 보정",
  "period_start": "2026-09-08",
  "period_end": "2026-09-14",
  "created_at": "2026-09-15T00:00:05Z",
  "sections": [
    {
      "key": "by_source",
      "title": "소스별 발송·👍·👎·정밀도",
      "columns": ["source", "trust", "adjusted", "sent", "useful", "useless", "precision"],
      "rows": [["rss:arxiv-cs-cl", 0.5, 0.58, 12, 7, 2, 0.78]]
    }
  ]
}
```

`sections[].key` 는 `funnel`, `drop_reasons`, `by_source`, `by_importance`, `by_score_band`, `triage_vs_judge`, `low_relevance_samples`, `trust_adjust` 이다 (`scripts/weekly_report.py` 의 표 순서). 셀 값은 문자열·숫자·`null`.

### 4.9 FCM 기기 등록

#### `POST /devices`

요청 `{"token": "fcm-registration-token", "platform": "android", "app_version": "0.1.0"}`. 새 토큰이면 201, 있으면 200 (`last_seen_at` 갱신, 비활성이었으면 다시 활성). 응답 `{"id": "3", "platform": "android", "registered_at": "2026-09-24T03:00:00Z"}`.

앱은 기동할 때와 `onTokenRefresh` 때마다 부른다. 기기는 현재 사용자(`devices.user_id`)에 묶인다. 같은 토큰이 다른 사용자로 다시 오면 `user_id` 를 옮긴다.

#### `DELETE /devices/{token}`

204. 로그아웃이 없으므로 앱 설정에서 푸시를 끌 때만 쓴다. FCM 이 `UNREGISTERED`·`INVALID_ARGUMENT` 를 돌려준 토큰은 서버가 스스로 비활성화한다.

#### 푸시 페이로드 (서버 → 기기)

```json
{
  "message": {
    "token": "…",
    "notification": {"title": "[릴리즈] MCP Python SDK v2.2.0 — …", "body": "스트리밍 HTTP 클라이언트의 …"},
    "data": {"alert_id": "18342", "delivery_mode": "instant", "type": "alert"},
    "android": {"priority": "HIGH", "notification": {"channel_id": "instant"}},
    "apns": {"headers": {"apns-priority": "10"}, "payload": {"aps": {"sound": "default"}}}
  }
}
```

- `quiet`·`experiment` 는 Android `channel_id: "quiet"` (중요도 LOW, 소리 없음), APNs `apns-priority: 5`, `sound` 없음. `experiment` 는 제목 앞에 `🧪 `.
- 재알림은 `data.type = "resurface"`, 제목 앞에 `📌 `.
- 앱은 알림 탭 시 `data.alert_id` 로 07 을 연다.

## 5. 화면 → 엔드포인트

| 화면 | 읽기 | 쓰기 |
|---|---|---|
| 공통 | `GET /meta` | `POST /devices` |
| 03 피드 | `GET /stats/today`, `GET /feed` | `PUT·DELETE /alerts/{id}/feedback`, `PUT·DELETE /saved/{id}` |
| 07 피드백 · 판정 근거 | `GET /alerts/{id}`, `GET /feedback/recent` | `PUT·DELETE /alerts/{id}/feedback` |
| 04 관심사 | `GET /meta`(taxonomy), `GET /settings/interests` | `PUT /settings/interests` |
| 05 알림 설정 | `GET /settings/notifications` | `PATCH /settings/notifications` |
| 06 수집 소스 | `GET /sources` | `PATCH /sources/{id}` |
| 08 내 프로필 | `GET /profile`, `GET /reports/{id}` | `PATCH /profile` |
| 09 · 10 걸러진 항목 (+관문별) | `GET /filtered/summary`, `GET /filtered/groups`, `GET /filtered/items` | `POST·DELETE /filtered/items/{id}/restore` |
| 11 찜 | `GET /folders`, `GET /saved` | `POST·PATCH·DELETE /folders…`, `PUT·PATCH·DELETE /saved/{id}` |
| 설정 루트 (디자인 없음) | `GET /profile`(이름), `GET /settings/notifications`(요약) | `PATCH /profile` |

### 5.1 사용자 액션 → 호출

| 액션 | 화면 | 호출 |
|---|---|---|
| 피드 필터 칩 | 03 | `GET /feed?filter=…` |
| 유용/불필요 누르기·바꾸기 | 03, 07 | `PUT /alerts/{id}/feedback` |
| 같은 버튼 다시 눌러 해제 | 03, 07 | `DELETE /alerts/{id}/feedback` |
| 찜 추가 / 해제 | 03, 11 | `PUT /saved/{id}` / `DELETE /saved/{id}` |
| 폴더 이동 | 11 | `PATCH /saved/{id}` `{"folder_id"}` |
| 메모 편집 | 11 | `PATCH /saved/{id}` `{"memo"}` |
| 읽음 처리 | 11 | `PATCH /saved/{id}` `{"is_read": true}` |
| 새 폴더 | 11 | `POST /folders` |
| 걸러진 항목 👍 복원 / 취소 | 09, 10 | `POST` / `DELETE /filtered/items/{id}/restore` |
| 보기 전환 (소스별·종류별·관문별) | 09, 10 | `GET /filtered/groups?view=…` |
| 그룹 펼침 더 보기 | 09, 10 | `GET /filtered/items?view=…&key=…` |
| 프로필 문장·관심 없음 편집 | 04 | 로컬 → `PUT /settings/interests` |
| 카테고리 선택 | 04 | 로컬 → `PUT /settings/interests` |
| 키워드 추가·삭제 | 04 | 로컬 → `PUT /settings/interests` |
| kind 가중치 편집 | 04 | 로컬 → `PUT /settings/interests` |
| 채널 토글 (FCM·Discord·Telegram) | 05 | `PATCH /settings/notifications` `{"channels": …}` |
| 하루 push 상한 | 05 | `PATCH` `{"daily_push_cap"}` |
| 무음 시간 | 05 | `PATCH` `{"quiet_hours": {"start","end"}}` |
| 같은 이슈 하루 1건 | 05 | `PATCH` `{"dedupe_same_issue_daily"}` |
| 중요도별 강도 세그먼트 | 05 | `PATCH` `{"delivery_by_importance": {"high"|"mid"|"low"}}` |
| 탐색 슬롯 | 05 | `PATCH` `{"exploration_slot": {"enabled"}}` |
| 소스 on/off | 06 | `PATCH /sources/{id}` |
| 기간 (최근 7·14·30일) | 08 | `GET /profile?period_days=…` |
| 주간 리포트 열기 | 08 | `GET /reports/{id}` |
| FCM 토큰 등록·갱신 | 앱 기동 | `POST /devices` |

## 6. 백엔드 변경

### 6.1 DB 스키마 — Alembic `0004` 한 개로 묶는다

v2 계획서 Task 1 의 사용자 식별자와 앱 테이블을 **B1 의 `0004` 한 리비전**(`app/db/alembic/versions/2026MMDD_0004_users_app_api.py`, `revision = "0004"`, `down_revision = "0003"`)에 넣는다. 병렬 작업에서 체인이 갈라지지 않게 다른 작업은 마이그레이션을 만들지 않는다. v2 계획서 Task 0 대로 `alembic current` 가 `0003` 인지 먼저 확인한다.

**v2 계획서 Task 1 그대로 (사용자 식별자)**

| 대상 | 변경 |
|---|---|
| `users` (새) | `id serial PK`, `name varchar(50) NOT NULL`, `created_at timestamptz NOT NULL DEFAULT now()`. `INSERT (1, 'owner')` 뒤 `setval('users_id_seq', 1)` |
| `feedback.user_id` | `int NOT NULL`, FK `fk_feedback_user_id` → `users(id)` `ON DELETE CASCADE`, 인덱스 `ix_feedback_user_id`. `server_default='1'` 로 기존 행을 채운 뒤 **기본값을 뗀다** (코드가 빠뜨리면 NOT NULL 위반으로 드러나게) |
| `notifications.user_id` | 위와 같음 (`fk_notifications_user_id`, `ix_notifications_user_id`, 기본값 뗌) |
| `feedback` 유니크 | `uq_feedback_item_id (item_id)` 를 지우고 `uq_feedback_user_item (user_id, item_id)` 를 만든다 |
| 코드 상수 | `app/db/users.py` `DEFAULT_USER_ID = 1`, 모델 `User`, `Feedback.user_id`, `Notification.user_id` |

**앱 새 테이블** — 전부 `user_id int NOT NULL` FK `users(id) ON DELETE CASCADE` 를 가지며 **기본값이 없다** (v2 계획서와 같은 이유로, 빠뜨리면 NOT NULL 위반으로 드러난다). API 계층이 `current_user_id()` = `DEFAULT_USER_ID` 를 명시로 넘긴다.

| 테이블 | 컬럼 | 제약 · 인덱스 |
|---|---|---|
| `user_prefs` | `user_id PK`, `data jsonb NOT NULL DEFAULT '{}'`, `updated_at timestamptz NOT NULL DEFAULT now()` | 사용자당 한 행 (`docs/database.md` 에 있던 표를 실제로 만든다) |
| `bookmark_folders` | `id serial PK`, `user_id`, `name text NOT NULL`, `position int NOT NULL DEFAULT 0`, `created_at timestamptz NOT NULL DEFAULT now()` | `uq_bookmark_folders_user_name (user_id, name)` |
| `bookmarks` | `user_id`, `item_id int FK items(id) ON DELETE CASCADE`, `folder_id int NULL FK bookmark_folders(id) ON DELETE SET NULL`, `memo text NULL`, `is_read bool NOT NULL DEFAULT false`, `read_at timestamptz NULL`, `saved_at timestamptz NOT NULL DEFAULT now()`, `resurfaced_at timestamptz NULL` | PK `(user_id, item_id)`, `ix_bookmarks_folder_id`, `ix_bookmarks_user_saved_at (user_id, saved_at)` |
| `devices` | `id serial PK`, `user_id`, `token text NOT NULL UNIQUE`, `platform varchar(10) NOT NULL`, `app_version varchar(30) NULL`, `created_at`, `last_seen_at timestamptz NOT NULL DEFAULT now()`, `disabled_at timestamptz NULL`, `last_error text NULL` | 활성 = `disabled_at IS NULL`, `ix_devices_user_id` |
| `weekly_reports` | `id serial PK`, `user_id`, `period_start date NOT NULL`, `period_end date NOT NULL`, `title text NOT NULL`, `subtitle text NOT NULL`, `sections jsonb NOT NULL`, `created_at` | `uq_weekly_reports_user_period (user_id, period_start)`. 같은 주를 다시 만들면 덮어쓴다 |

**기존 테이블 변경 (앱)**

| 테이블 | 변경 | 이유 |
|---|---|---|
| `feedback` | `source varchar(10) NOT NULL DEFAULT 'discord'` 추가 | 앱 판정 우선 규칙. 텔레그램 웹훅은 `telegram`, 앱은 `app` |
| `feedback` | `verdict` 값에 `cleared` 허용 (컬럼 변경 없음) | 앱 해제 표시. 모든 집계·사례는 `useful`·`useless` 만 |
| `notifications` | `title text NULL` 추가 | 발송한 제목 (형제 버전 병기 포함, 4.4). `NULL` 이면 `summaries.title_ko` |
| `notifications` | 인덱스 `ix_notifications_sent_at` | 피드 커서·통계 |
| `notifications` | `level` 을 `varchar(10)` → `varchar(20)` 으로 넓히고 `cluster_dup`(11자) 허용, `channel` 값에 `fcm`·`app` 허용 (`channel` 은 변경 없음) | v2 계획서 Task 3, `app` = 피드에만 남긴 행 |
| `decisions` | 인덱스 `ix_decisions_created_at` | 걸러짐 창 집계 |
| `decisions` | `stage` 값에 `user` 허용 (`Stage.USER`, 컬럼 변경 없음) | 복원 결정 로그 |

`summaries` 는 바꾸지 않는다. 이전 초안의 `summaries.topics` 는 없앴다 (topics 는 선별 결정 `details` 에 남는다, 6.5).

### 6.2 `user_prefs.data` 모양과 유효 설정

`data` 의 키는 `Rules` 의 섹션 이름을 그대로 따른다. YAML 을 읽은 dict 위에 깊은 병합(목록은 통째 교체)한 뒤 같은 `_Strict` 모델로 검증한다. 단일 사용자라 `get_rules()` 는 `DEFAULT_USER_ID` 의 행만 덮어쓴다.

```json
{
  "policy": {"interests": "…", "not_interested": "…", "focus_stack": ["claude"], "focus_repos": ["anthropics/*"], "categories": ["llm-model"]},
  "scoring": {"kind_weights": {"survey": -0.15}},
  "notify": {
    "daily_push_cap": 15, "quiet_start_hour": 23, "quiet_end_hour": 8,
    "cluster_daily_cap": 1, "explore_enabled": true,
    "delivery_by_importance": {"high": "instant", "mid": "quiet", "low": "feed_only"},
    "channels": {"fcm": true, "discord": true, "telegram": false}
  },
  "sources": {"youtube:codingapple": {"enabled": false}}
}
```

- `get_rules()` 는 시그니처를 유지하고 "YAML + 덮어쓰기" 를 돌려준다. 덮어쓰기는 프로세스 전역 값이며 기동 시(lifespan, 스케줄러 전) DB 에서 한 번 읽고, 설정 API 가 저장한 직후 갈아끼운다. 단일 프로세스 전제라 이것으로 충분하다.
- 덮어쓰기가 검증에 실패하면(YAML 키가 바뀌어 옛 값이 안 맞는 등) 기동을 멈추지 않고 경고 로그 후 해당 섹션을 무시한다.
- `policy.taxonomy` 는 덮어쓸 수 없다 (선별 어휘라 YAML 만). `sources` 는 `Rules` 밖이라 `sync_sources` 가 읽는다. 표시 이름은 `users.name` 이라 여기 없다.
- `config/rules.yaml` 에 새 키와 기본값을 적는다. 전부 기본값이 있어 옛 YAML 로도 기동된다 (v2 계획서 Global Constraints).

| 키 | 기본 | 작업 |
|---|---|---|
| `policy.taxonomy` | v2 계획서의 12 slug (`llm-model` `agent` `mcp-tooling` `inference-opt` `rag-retrieval` `training-finetune` `python-backend` `web-frontend` `devops-infra` `ai-safety-eval` `dev-community` `video`) | B1 |
| `policy.categories` | `policy.taxonomy` 전체 (검증기가 taxonomy 밖 값 거부) | B2 |
| `notify.cluster_daily_cap` | 1 (`ge=0`, 0 = 끔) | B2 필드, B4 동작 |
| `notify.delivery_by_importance` | high=instant, mid=quiet, low=feed_only (현재 하드코딩 `level_for` 와 같음) | B2 필드, B4 동작 |
| `notify.explore_enabled` | true | B2 필드, B4 동작 |
| `notify.channels` | fcm·discord true, telegram false | B2 필드, B4·B5 동작 |

### 6.3 새 설정 파일 · 환경변수

`config/app.yaml` (새, `AppConfig` 모델, 앱 전용 정적값). 파이프라인은 이 파일을 읽지 않는다.

```yaml
onboarding: {done: 8, total: 8}
personal_model_threshold: 50
resurface_unread_after_days: 7
screening_relevance_floor: 0.5
planned_sources: [Reddit, GitHub Trending, X]
# policy.taxonomy slug → 앱 표시 라벨. 선별 어휘는 rules.yaml 이 소유하고 여기는 라벨만 둔다.
taxonomy_labels:
  llm-model: 새 모델·벤치마크
  agent: 에이전트 패턴
  mcp-tooling: MCP·IDE·CLI
  inference-opt: 추론 최적화
  rag-retrieval: RAG·검색
  training-finetune: 학습·파인튜닝
  python-backend: Python 백엔드
  web-frontend: Next.js·React
  devops-infra: DevOps·인프라
  ai-safety-eval: 안전·평가
  dev-community: 논쟁·가격·정책
  video: 영상 채널
```

라벨을 `rules.yaml` 에 넣지 않은 이유 — v2 계획서가 `policy.taxonomy: list[str]` 로 못박았고, 라벨은 앱 표시 전용이라 선별 프롬프트 캐시와 무관해야 한다. 기동 시 `taxonomy_labels` 에 없는 slug 가 있으면 경고 로그만 남기고 slug 를 라벨로 쓴다.

`.env` / `.env.example` 추가.

| 키 | 용도 |
|---|---|
| `APP_API_TOKEN` | 앱 API 베어러 토큰 (긴 랜덤 문자열). `DEFAULT_USER_ID` 로 매핑 |
| `DISCORD_CHANNEL_NAME` | 05 화면 표시용 채널명 (`#trend-alerts`) |
| `FCM_PROJECT_ID` | Firebase 프로젝트 ID |
| `FCM_SERVICE_ACCOUNT_FILE` | 서비스 계정 JSON 경로 (컨테이너에 볼륨으로 마운트, 커밋 금지) |

`config/sources.yaml` 각 항목 `config` 에 선택 키 `display_name`, `error_hint` 를 추가한다 (`SourceConfig.config` 는 자유 dict 라 모델 변경 없음).

### 6.4 바뀌는 모듈

★ = `.claude/rules/core-files.md` 의 엔트리·공용 파일.

| 모듈 | 변경 |
|---|---|
| `app/main.py` ★ | `/api/v1` 라우터 등록, 오류 핸들러, lifespan 에서 `user_prefs` 덮어쓰기 적재 |
| `app/config.py` ★ | `Settings` 에 4개 키, `AppConfig` + `get_app_config()`, `PolicyConfig.taxonomy`·`categories`, `NotifyConfig` 새 필드(`cluster_daily_cap` 포함), 덮어쓰기 병합 (`set_prefs_overlay`). `ScoringConfig.kind_weights` 는 main 그대로 |
| `app/schemas.py` ★ | `Stage.USER`, `Level.CLUSTER_DUP` |
| `app/db/users.py` (새) | `DEFAULT_USER_ID = 1` |
| `app/db/models.py` + `alembic/versions/…_0004_users_app_api.py` ★ | 6.1 전부 |
| `app/db/feedback.py` ★ | `feedback_upsert_stmt(user_id, item_id, verdict, source)`, `upsert_feedback(session, user_id, item_id, verdict, source)` (충돌 대상 `uq_feedback_user_item`), `clear_feedback` |
| `app/db/budget.py` ★ | `usage_today()` — kind 별 오늘 사용량 (06 Stat) |
| `app/pipeline/triage.py` | `TriageItem.topics`, `TRIAGE_PROMPT_VERSION`, `MAX_TOPICS = 3`, 프롬프트 3) topics 절, `parse_triage(…, taxonomy=)` (6.5) |
| `app/pipeline/llm.py` ★ | `render_policy` 에 `관심 카테고리` 줄. 판정 출력(`LLMVerdict`)은 바꾸지 않는다. 피드백 사례 지시 완화(v2 계획서 Task 4)는 main 에 이미 있다 |
| `app/pipeline/feedback.py` ★ | `nearest_feedback(…, user_id=DEFAULT_USER_ID)` (`AND f.user_id = :user_id`), `useful`·`useless` 만, 요약 없는 복원 항목은 원문 제목으로 (LEFT JOIN), 사례에 `item_id` 포함 |
| `app/jobs/pipeline.py` | 선별 결정 `details` 에 `topics`·`prompt_version`, `_existing_relevance` 가 `topics` 복원, `llm` 결정 `details.examples` 저장 |
| `app/notify/policy.py` ★ | `delivery_by_importance`, 무음 → 피드만, `cluster_sent_today`·`sibling_versions`·`decorate_title`, push 수는 서로 다른 항목 |
| `app/notify/fcm.py` (새) | `FcmNotifier` — FCM HTTP v1, 서비스 계정 OAuth, 무효 토큰 비활성화 |
| `app/notify/base.py` | `Notifier.send` 는 그대로. 켜진 채널 목록을 만드는 `enabled_notifiers(rules)` |
| `app/jobs/notify.py` | 모든 `Notification(...)` 에 `user_id=DEFAULT_USER_ID`, 클러스터 상한·제목 병기·`notifications.title`, 채널 팬아웃, 탐색 토글과 후보의 클러스터 조건, 피드 전용 행은 `channel='app'` |
| `app/jobs/feedback.py` | 리액션 동기화 upsert 에 `user_id`·`source`, `source='app'` 행 건너뜀 |
| `app/api/telegram.py` · `app/api/discord.py` | `upsert_feedback(session, DEFAULT_USER_ID, item_id, verdict, source=…)` |
| `app/jobs/scheduler.py` | `sync_sources` 가 덮어쓰기 적용, 모든 YAML 소스에 잡 등록, 주간 리포트 cron 잡, 찜 재알림 잡 |
| `app/jobs/report.py` (새) | 주간 리포트 표 생성·저장. `scripts/weekly_report.py` 는 이것을 불러 출력만 한다 (`--apply` 동작 유지) |
| `app/api/v1/` (새 패키지) | `deps.py`(인증·세션·`current_user_id`), `errors.py`, `pagination.py`, `schemas/<영역>.py`(응답 모델, 공통은 `schemas/common.py`), 라우터 `meta.py` `feed.py` `alerts.py` `settings.py` `sources.py` `filtered.py` `saved.py` `profile.py` `reports.py` `devices.py`, 조회 SQL 은 `app/api/v1/queries/` |
| `config/rules.yaml` ★ | 6.2 표의 새 키 |
| `config/sources.yaml` ★ | `display_name`, `error_hint` |
| `config/app.yaml` (새) ★ | 6.3 |
| `pyproject.toml` ★ | `google-auth` (FCM 서비스 계정 토큰) |
| `docs/database.md` · `docs/pipeline.md` · `docs/architecture.md` | 테이블·선별 출력·발송 정책·API 계층 반영 |

### 6.5 선별 출력 `topics` (v2 계획서 Task 2 중 남은 부분)

main 에는 `Kind`, `TriageItem.kind`, 프롬프트 2) kind 절, `ScoringConfig.kind_weights`(키 검증 포함), `score_item(kind=)`, 선별 결정 `details.kind` 가 이미 있다. 남은 것은 아래뿐이며 v2 계획서의 이름을 그대로 쓴다.

- `PolicyConfig.taxonomy: list[str]` (6.2 기본값).
- `TriageItem.topics: list[str]`, `MAX_TOPICS = 3`, `TRIAGE_PROMPT_VERSION = "2026-09-08.1"` (출력 스키마·눈금이 바뀔 때 올린다).
- 프롬프트에 `3) topics — 아래 분류표에서 1~3개. 표에 없는 값은 쓰지 않는다.` 와 slug 목록을 넣는다. 시스템 블록은 정책·분류표만 담아 캐시가 유지된다.
- `parse_triage(batch, expected, *, taxonomy)` — 분류표 밖 slug 는 **버리고** 앞 3개로 자른다. 항목 실패로 세지 않는다.
- `decisions(stage=triage).details` = `{"relevance", "reason", "kind", "topics", "batch_id", "prompt_version"}`. `_existing_relevance` 는 `topics` 가 없는 옛 행을 `[]` 로 채우고 다시 호출하지 않는다.
- 판정(`llm.py`)은 topics 를 내지 않는다. 앱이 읽는 곳은 `Alert.categories`, `DroppedItem.topics`, `rationale.screening.topics`, `category_reactions` 넷이다.
- v2 계획서의 `kind_weights` 기본값(technique +0.10 등)은 main 에서 2026-09-09·10 실측으로 이미 조정됐다 (감점만). 화면 04 샘플도 main 값과 같다. B3 는 이 값을 건드리지 않는다.

## 7. 버전 · 변경 관리

- 호환이 깨지는 변경은 `/api/v2` 로 간다. v1 안에서는 필드 추가만 한다. 클라이언트는 모르는 필드를 무시하고, 모르는 열거형 값은 라벨 대신 값을 그대로 보여 준다.
- 이 문서의 JSON 예시는 프론트 fixture 의 원본이다. 예시를 바꾸면 fixture 도 같이 바꾼다.

## 8. 열린 질문

남은 열린 질문은 없다. 사용자가 정한 것은 아래와 같다.

1. **무음 시간** — 화면대로 무음 중 `instant`·`quiet` 은 `feed_only` 로 남긴다 (4.4, B4).
2. **소스 추가(06 헤더 `+`)** — v1 범위 밖. 앱은 `준비 중` 토스트 (4.5).
3. **클러스터 억제 항목** — 걸러진 항목에 일곱째 관문 `cluster_dup` (`클러스터 하루 1건`)으로 보이고 요약 `gate_counts`·소스별·종류별·관문별 그룹·항목 목록에 들어간다. 👍 복원도 다른 관문과 같다 (2, 4.6, B8).
4. **새 앱 테이블의 `user_id`** — v2 계획서처럼 기본값 없음. API 계층이 `DEFAULT_USER_ID` 를 넘긴다 (6.1, B1).
5. **taxonomy 라벨** — `config/app.yaml` `taxonomy_labels` 를 `GET /meta` 로 준다 (6.3).
6. **kind 가중치** — main 값 유지 (6.5).

이전 초안의 `버전 형제 릴리즈는 제목에 병기` 질문은 v2 계획서 Task 3 의 `decorate_title` 로 해소했다.

## 9. 사용자 설계 문서 대응 (`docs/design/source/앱-화면-설계-v0.1.md`)

### 9.1 "필요한 API" → 이 계약

엔드포인트 설계는 이 계약을 유지하고, 사용자 초안과는 아래처럼 대응한다.

| 사용자 초안 | 이 계약 | 차이 |
|---|---|---|
| `GET /items?level=&since=` | `GET /feed?filter=&cursor=` | `level` 대신 칩과 같은 `filter`, `since` 대신 커서 |
| `GET /items/{id}/decision` | `GET /alerts/{id}` 의 `rationale` | 상세와 근거를 한 번에 |
| `POST /feedback` (user_id, item_id, verdict) | `PUT·DELETE /alerts/{id}/feedback` | `user_id` 는 토큰에서, 해제는 `DELETE` |
| `GET/PUT /me/prefs` | `GET/PUT /settings/interests`, `GET/PATCH /settings/notifications` | 04 명시 저장 · 05 즉시 저장으로 나눔. 저장소는 같은 `user_prefs` |
| `GET/PUT /sources` | `GET /sources`, `PATCH /sources/{id}` | 소스별 부분 갱신 |
| `GET /items/dropped?group=source\|kind\|stage&since=24h` | `GET /filtered/summary`, `/filtered/groups?view=source\|kind\|gate&hours=24`, `/filtered/items` | `stage` → `gate` (표시용 관문 6개), 요약·그룹·목록 분리 |
| 버린 항목에 `POST /feedback` useful | `PUT /alerts/{id}/feedback` 또는 `POST /filtered/items/{id}/restore` | 복원은 피드에도 올림 |
| `GET/POST/DELETE /bookmarks`, `PATCH /bookmarks/{id}` | `GET /saved`, `PUT·PATCH·DELETE /saved/{alert_id}` | 키가 알림 ID. 컬럼 `note`·`created_at` 은 `memo`·`saved_at` |
| `GET/POST /bookmark-folders` | `GET·POST /folders`, `PATCH·DELETE /folders/{id}` | 이름 변경·삭제 추가 |
| 7일 미열람 찜 재알림은 발송 잡의 silent 레벨 | 4.7 재알림 잡 (FCM `quiet`) | 별도 잡, 피드·상한 제외 |
| `GET /me/stats` | `GET /profile`, `GET /reports` | 주간 리포트는 저장본 조회 |

### 9.2 "열린 결정" → 화면이 보여 주는 대로

| 사용자 열린 결정 | 결정 | 근거 |
|---|---|---|
| 온보딩 8건 추출 규칙 | 범위 밖 (02 온보딩 제외). 08 의 `온보딩 8/8` 은 정적값 | README 범위 |
| kind 가중치를 노출할지, 숫자 대신 3단계로 할지 | **숫자로 노출** (−0.50 ~ +0.50, 0.05 단계), 6행 | 04 HTML 이 `+0` `−0.15` 숫자 행 |
| "놓친 이슈" 는 수동 입력인지 | 수동 입력 없음. 걸러진 항목 복원 수로 센다. 캡션은 `직접 찾아본 건` 그대로 | 08 HTML, 09·10 의 👍 복원 |
| 찜을 프로필 벡터 약한 신호로 넣을지 | 넣지 않는다 | 11 HTML 안내문 `유용/불필요 판정에는 반영되지 않습니다` |

남은 결정은 없다 (8절).

## 10. v2 계획서 대응

| v2 Task | 이 계약 | 작업 |
|---|---|---|
| Task 0 전제 확인 | `alembic current` = 0003, 인터페이스 위치 확인 | B1 착수 전 |
| Task 1 사용자 식별자 (0004) | 6.1 앞 표, `DEFAULT_USER_ID`, 1.1 인증 매핑 | B1 |
| Task 2 `kind`·`topics`·`kind_weights` | `kind`·`kind_weights` 는 main 에 있음. `taxonomy` 설정은 B1, `topics`·`prompt_version` 은 B3 (6.5) | B1, B3 |
| Task 3 클러스터당 하루 1건 | 4.4 클러스터 하루 상한, `dedupe_same_issue_daily` ↔ `cluster_daily_cap` | B2 (필드), B4 (동작) |
| Task 4 피드백 사례 지시 완화 | main 에 이미 반영됨 (`app/pipeline/llm.py`·`triage.py` 에 "강하게" 없음). 회귀 확인만 | B3 |
| Task 5 relevance × kind 리포트 실행 | 범위 밖. 운영 작업이며 결과는 `rules.yaml` 가중치로만 간다. 앱 주간 리포트(B9)의 `by_score_band` 등과 별개 | – |
