# 03 피드 (알림 이력)

- Figma node: `4:66` · 프레임 390 × 844 · 스크린샷: [03-feed.png](03-feed.png)
- 하단 탭: **피드** 활성

## 목적

앱의 홈. 오늘 사용자에게 전달된 알림(푸시/조용히/실험)을 시간 역순 카드로 보여주고, 각 항목에 대해 원문 열기 · 찜 · 유용/불필요 피드백을 받는다. 오늘 걸러진(전달되지 않은) 항목 화면으로 진입하는 입구도 제공한다.

## 레이아웃 (위 → 아래)

### 1. TopBar (`4:67`) — 높이 약 77, padding `pt 44 / pb 8 / px 20`, 좌우 space-between
| 요소 | 내용 | 스타일 | 인터랙션 |
|---|---|---|---|
| 제목 | `오늘` | Bold 22 / lh 1.4 / `#1C1B19` | – |
| 아이콘 `icon/search` | 22×22 | 아이콘 간 gap 14 | 탭 → 알림 검색 (검색 화면은 디자인 없음) |
| 아이콘 `icon/bell` | 22×22 | | 탭 → 알림 센터/시스템 알림 목록 (디자인 없음) |

### 2. 필터 칩 행 (`4:76`) — padding `pt 4 / pb 12 / px 16`, gap 8, 가로 스크롤 가능
단일 선택 칩 5개. 선택된 칩 = 검정 배경(`#1C1B19`) + 흰 글자, 미선택 = 흰 배경 + `#D9D5CC` 1px 테두리 + `#55524B` 글자. 칩: `px 14 / py 9`, radius 20, Medium 13 / lh 1.2.

| 칩 | 의미(필터 조건) | 기본 선택 |
|---|---|---|
| `전체` | 모든 전달 항목 | ✅ |
| `즉시` | delivery_mode = 즉시(푸시) | |
| `조용히` | delivery_mode = 조용히(무음 알림) | |
| `실험` | 탐색 슬롯(경계 항목)으로 보낸 실험 항목 | |
| `유용` | 사용자가 유용 피드백을 준 항목 | |

### 3. 요약 줄 (`4:87`) — padding `px 20 / pb 8`, space-between, 12px / lh 1.4
| 요소 | 텍스트 | 스타일 | 인터랙션 |
|---|---|---|---|
| 좌측 | `오늘 push 4 / 15` | Regular 12 `#8A877F` | – (오늘 푸시 발송 수 / 하루 push 상한) |
| 우측 링크 | `걸러짐 571건 보기  ›` | SemiBold 12 `#2D5BE3` | 탭 → [09 걸러진 항목 · 소스별](09-filtered-by-source.md) |

### 4. 피드 리스트 (`4:90`) — 세로 스크롤, 카드 간 gap 12, 좌우 padding 16
각 항목은 **FeedCard** (흰 배경, 1px `#E5E2DB`, radius 14, padding 16, 내부 세로 gap 10).

FeedCard 구성 (위→아래):
1. (실험 항목일 때만) **실험 헤더**: `icon/flask` 14×14 + `실험 · 경계 항목` (SemiBold 12, `#B5651D`), gap 6
2. **메타 행** (space-between): 좌 `{소스명} · {상대시간}` (Regular 12 `#8A877F`) / 우 **Badge** (전달 모드)
   - `즉시` 배지: 배경 `#E8EEFC`, 글자 `#2D5BE3`
   - `실험` 배지: 배경 `#FDF1E2`, 글자 `#B5651D`
   - (`조용히` 배지는 샘플에 없음 — 중립 회색 계열 권장: 배경 `#F0EEE9`, 글자 `#55524B`)
3. **제목**: SemiBold 16 / lh 1.4 `#1C1B19`, 여러 줄 허용 (스크린샷상 줄바꿈 제한 없음)
4. **요약**: Regular 13.5 / lh 1.55 `#55524B`
5. **태그**: `#{category_slug}` 공백 2칸 구분, Regular 12 `#2D5BE3`
6. **액션 행** (gap 8, 높이 40):
   - `원문` OpenButton: 흰 배경, `#D9D5CC` 테두리, radius 10, px 14, `icon/external` 16 + `원문` SemiBold 13 → 탭 시 원문 URL 외부 브라우저로 열기
   - 찜 IconButton 40×40: `icon/bookmark`(미찜) / `icon/bookmarkFill`(찜됨, 파란 채움 `#2D5BE3`) → 토글, 찜 목록([11](11-saved.md))에 추가/삭제
   - Feedback 그룹 (남은 폭을 2등분, gap 8): `유용`(`icon/thumbup`) / `불필요`(`icon/thumbdown`)
     - 선택된 상태: 배경·테두리 `#1C1B19`, 아이콘·글자 흰색 (첫 카드의 `유용`)
     - 미선택: 흰 배경, `#D9D5CC` 테두리, 글자 `#55524B`
     - 둘 중 하나만 선택되는 상호배타 토글. 다시 누르면 해제(권장).
- 카드 본문(제목/요약 영역) 탭 → [07 피드백 · 판정 근거](07-feedback-rationale.md) (해당 알림의 상세)

### 5. TabBar (`4:167`) — 공통 컴포넌트, [tokens.md](../tokens.md#하단-탭바) 참조

## 샘플 데이터 (스크린샷 그대로)

| # | 소스 · 시간 | 배지 | 실험 헤더 | 제목 | 요약 | 태그 | 찜 | 피드백 |
|---|---|---|---|---|---|---|---|---|
| 1 | GitHub Releases · 42분 전 | 즉시 | – | [릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 (v2.2.0 · v1.30.0) | 스트리밍 HTTP 클라이언트의 리다이렉트 처리와 OAuth 토큰 검증이 바뀐 보안 릴리즈. v1.30.0에 백포트됨. | #mcp-tooling #python-backend | ✅ 찜됨 | 유용 선택 |
| 2 | arXiv cs.CL · 3시간 전 | 실험 | 실험 · 경계 항목 | BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배 | 고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개. | #inference-opt | – | 없음 |
| 3 | Anthropic · 5시간 전 | 즉시 | – | [모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일 | 새 최상위 모델. 툴 사용과 장문 추론 벤치마크 갱신, API 가격은 이전 세대와 동일. | #llm-model | – | 없음 |

## 데이터 필드

| 필드 | 타입 | 예시 | 형식/비고 |
|---|---|---|---|
| `push_sent_today` | int | 4 | 오늘 발송된 푸시 수 |
| `daily_push_cap` | int | 15 | 알림 설정의 하루 push 상한 (화면 05) |
| `filtered_today_count` | int | 571 | 오늘 걸러진 항목 수 (화면 09/10 요약과 동일) |
| alert.`id` | string | – | 카드 식별자 (피드백·찜·상세 이동에 사용) |
| alert.`source_name` | string | `GitHub Releases`, `arXiv cs.CL`, `Anthropic` | 사람이 읽는 소스 표시명 |
| alert.`delivered_at` | datetime | – | 표시: 상대시간 `42분 전`, `3시간 전` (1시간 미만 분, 24시간 미만 시간 단위) |
| alert.`delivery_mode` | enum | `instant`(즉시) / `quiet`(조용히) / `feed_only`(피드만) / `experiment`(실험) | 배지 텍스트·색 결정 |
| alert.`is_exploration` | bool | true | true면 실험 헤더 `실험 · 경계 항목` 표시 |
| alert.`title` | string | `[릴리즈] MCP Python SDK v2.2.0 — …` | 접두 `[릴리즈]`, `[모델]` 등 kind 라벨 포함 |
| alert.`summary` | string | `스트리밍 HTTP 클라이언트의 …` | 1~3문장 한국어 요약 |
| alert.`categories` | string[] | `["mcp-tooling","python-backend"]` | `#` 접두 태그로 표시 |
| alert.`url` | string(URL) | – | `원문` 버튼 대상 |
| alert.`is_saved` | bool | true | 찜 아이콘 채움 여부 |
| alert.`feedback` | enum? | `useful` / `not_useful` / null | 유용/불필요 버튼 상태 |

## 인터랙션 요약 (API 호출)
- 필터 칩 변경 → 피드 목록 재조회 (filter 파라미터)
- 유용/불필요 → 피드백 저장/변경/해제
- 찜 → 찜 추가/해제
- `걸러짐 571건 보기` → 화면 09
- 카드 탭 → 화면 07

## 빈 상태 / 엣지
- 디자인에 빈 상태 없음. 권장: 필터 결과가 없으면 "오늘 받은 알림이 없습니다" + 걸러짐 링크 유지.
- 실험 헤더는 실험 항목에서만 노출.
