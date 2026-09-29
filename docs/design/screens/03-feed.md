# 03 피드 (알림 이력)

- 원본 HTML: [`../source/Main.dc.html`](../source/Main.dc.html) (`gen.py.txt` `feed_card()`) · Figma node `4:66` · 프레임 390 × 844 · 스크린샷 [03-feed.png](03-feed.png) (Figma)
- 하단 탭: **피드** 활성

## 목적

앱의 홈. 사용자에게 전달된 알림(즉시·조용히·실험·피드만)을 시간 역순 카드로 보여 주고, 원문 열기·찜·유용/불필요 피드백을 받는다. 걸러진 항목 화면으로 들어가는 입구도 둔다.

## 레이아웃 (위 → 아래)

### 1. 루트 TopBar — `margin-top 44`, 높이 56, `px 20`, space-between
| 요소 | 내용 | 스타일 | 인터랙션 |
|---|---|---|---|
| 제목 | `오늘` | 22 / 700 / primary | – |
| `search` | 22 | primary, 아이콘 간 gap 14 | 알림 검색 (디자인 없음) |
| `bell` | 22 | primary | 알림 센터 (디자인 없음) |

### 2. 필터 칩 행 — `padding 4px 16px 12px`, gap 8, `overflow: hidden` (앱은 가로 스크롤)
단일 선택 Chip 5개 ([tokens Chip](../tokens.md#chip-chip)).

| 칩 | 의미 | 기본 |
|---|---|---|
| `전체` | 모든 전달 항목 | 선택 |
| `즉시` | `delivery_mode = instant` | |
| `조용히` | `delivery_mode = quiet` | |
| `실험` | `delivery_mode = experiment` | |
| `👍 유용` | `feedback = useful` | |

### 3. 요약 줄 — `padding 0 20px 8px`, space-between, 12 / 400 / tertiary
| 요소 | 텍스트 | 스타일 | 인터랙션 |
|---|---|---|---|
| 좌 | `오늘 push 4 / 15` | 12 tertiary | 오늘 push 수 / 하루 push 상한 |
| 우 | `걸러짐 571건 보기 ›` | 12 / 600 / `#2D5BE3` | [09 걸러진 항목 · 소스별](09-filtered-by-source.md) |

### 4. 피드 리스트 — 세로 flex, 카드 간 gap 12
FeedCard 는 Card(padding 16, **gap 10**, 좌우 margin 16)이고 위에서 아래로 아래 요소를 쌓는다.
1. (실험 항목만) **실험 헤더** — `flask` 14 `#B5651D` + gap 6 + `실험 · 경계 항목` 12 / 600 / `#B5651D`.
2. **메타 행** (space-between) — 좌 `{소스명} · {상대시간}` 12 tertiary, 우 Badge (`즉시`·`조용히`·`실험`·`피드만`, [tokens Badge](../tokens.md#badge-badge)).
3. **제목** — 16 / 600 / lh 1.4 / primary. 줄 수 제한 없음.
4. **요약** — 13.5 / 400 / lh 1.55 / `#55524B`.
5. **태그** — flex wrap gap 8, 각 `#{slug}` 12 / `#2D5BE3`.
6. **액션 행** — flex gap 8, 세로 가운데 정렬.
   - OpenButton `external` 16 + `원문` (13/600 primary) → 원문 URL 외부 브라우저.
   - BookmarkButton 40×40 — `bookmark` 18 `#55524B` / 찜됨 `bookmarkfill` 18 `#2D5BE3`. 토글.
   - FeedbackButton 두 개(`유용` `thumbup` · `불필요` `thumbdown`)가 남은 폭을 나눈다 (gap 8). 상호배타, 다시 누르면 해제.
- 카드 본문(제목·요약) 탭 → [07 피드백 · 판정 근거](07-feedback-rationale.md).

### 5. TabBar — [tokens 탭바](../tokens.md#하단-탭바)

## 샘플 데이터 (HTML 그대로)

| # | 소스 · 시간 | 배지 | 실험 헤더 | 제목 | 요약 | 태그 | 찜 | 피드백 |
|---|---|---|---|---|---|---|---|---|
| 1 | GitHub Releases · 42분 전 | 즉시 | – | [릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 (v2.2.0 · v1.30.0) | 스트리밍 HTTP 클라이언트의 리다이렉트 처리와 OAuth 토큰 검증이 바뀐 보안 릴리즈. v1.30.0에 백포트됨. | #mcp-tooling #python-backend | 찜됨 | 유용 선택 |
| 2 | arXiv cs.CL · 3시간 전 | 실험 | 실험 · 경계 항목 | BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배 | 고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개. | #inference-opt | – | 없음 |
| 3 | Anthropic · 5시간 전 | 즉시 | – | [모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일 | 새 최상위 모델. 툴 사용과 장문 추론 벤치마크 갱신, API 가격은 이전 세대와 동일. | #llm-model | – | 없음 |

1번 제목 끝의 `(v2.2.0 · v1.30.0)` 은 같은 클러스터 형제 릴리즈의 버전 병기다 (알림 설정 `같은 이슈 하루 1건`, 계약 4.4).

## 데이터 필드

| 필드 | 타입 | 예시 | 형식/비고 |
|---|---|---|---|
| `push_sent_today` | int | 4 | 오늘 push 로 보낸 서로 다른 항목 수 |
| `daily_push_cap` | int | 15 | 화면 05 |
| `filtered_count` | int | 571 | 화면 09·10 요약과 같은 정의 |
| alert.`id` | string | – | 피드백·찜·상세 키 |
| alert.`source_name` | string | `GitHub Releases` | 소스 표시명 |
| alert.`delivered_at` | datetime | – | 상대시간 `42분 전`, `3시간 전` |
| alert.`delivery_mode` | enum | `instant` / `quiet` / `feed_only` / `experiment` | 배지 |
| alert.`is_exploration` | bool | true | 실험 헤더 |
| alert.`title` | string | `[릴리즈] MCP Python SDK v2.2.0 — …` | 발송한 제목 (형제 버전 병기 포함) |
| alert.`summary` | string | – | 2~3줄 요약 |
| alert.`categories` | string[] | `["mcp-tooling","python-backend"]` | 선별이 고른 taxonomy slug (`#` 접두) |
| alert.`url` | URL | – | 원문 |
| alert.`is_saved` | bool | true | 찜 아이콘 |
| alert.`feedback` | enum? | `useful` / `not_useful` / null | 버튼 상태 |

## 인터랙션 요약
- 필터 칩 → 피드 재조회 (`filter`).
- 유용/불필요 → 판정 설정·변경·해제.
- 찜 → 추가·해제.
- `걸러짐 571건 보기 ›` → 09.
- 카드 탭 → 07.

## 빈 상태 / 엣지
- 빈 상태 디자인은 없다. 필터 결과가 없으면 `오늘 받은 알림이 없습니다` 와 걸러짐 링크를 둔다.

## Figma 와 다른 점 (HTML 우선)
- 다섯째 칩 라벨은 `👍 유용` 이다 (Figma `유용`).
- 헤더는 상태바 44 + 56 이다 (Figma 77).
- 태그는 공백이 아니라 flex gap 8 로 띄운다.
- `조용히` 배지는 `#F0EEE9` / `#6B6862`, `피드만` 배지는 `#EEF5EE` / `#3D7A4A` 로 HTML 에 정의되어 있다 (Figma 에는 샘플이 없었다).
