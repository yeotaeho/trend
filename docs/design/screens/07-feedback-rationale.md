# 07 피드백 · 판정 근거

- 원본 HTML: [`../source/Feedback.dc.html`](../source/Feedback.dc.html) (`gen.py.txt` `bar()`) · Figma node `6:139` · 프레임 390 × 960 · 스크린샷 [07-feedback-rationale.png](07-feedback-rationale.png) (Figma)
- **하단 탭바 없음** (전체 화면 push)

## 목적

알림 하나에 대해 "왜 왔는지"(점수 구성, 선별·판정 근거)를 보여 주고 유용/불필요 판정을 받는다. 판정이 어디에 쓰이는지 안내하고 최근 판정 이력을 보여 준다.

진입은 [03 피드](03-feed.md) 카드 탭, 푸시 알림 탭, 최근 판정 행 탭이다.

## 레이아웃 (위 → 아래)

본문은 세로 flex **gap 12**, `padding-top 4` 다. 섹션 라벨도 이 gap 안에 들어가므로 라벨 위 간격은 12 + 20 이다.

### 1. 하위 TopBar
`back` 20 + `피드백` (18/600). 우측 `external` 22 → 원문 URL.

### 2. 알림 요약 카드 — 기본 Card (padding 16, gap 12)
- 메타 행 (space-between) — `arXiv cs.CL · 3시간 전` 12 tertiary + Badge `실험`.
- 제목 17 / 700 / lh 1.4 — `BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배`.
- 요약 13.5 / lh 1.55 / `#55524B` — `고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개.`

### 3. SectionLabel `이 알림이 온 이유` + 근거 카드 (기본 Card)
- 헤더 행 (space-between, baseline 정렬)
  - 좌 `점수 0.43` 13 / 600 primary + ` / 통과선 0.45` (같은 줄, 500 tertiary).
  - 우 `경계 → 탐색 슬롯` 12 / 600 `#B5651D`.
- ScoreBar 4행 ([tokens Bars](../tokens.md#bars)). 채움 폭 = 값 ÷ 0.5.

| 라벨 | 값 | 채움 | 색 |
|---|---|---|---|
| `src` | 0.10 | 20% | `#2D5BE3` |
| `rel` | 0.25 | 50% | `#2D5BE3` |
| `fresh` | 0.10 | 20% | `#2D5BE3` |
| `kind` | 0.00 | 0% | `#B8B4AB` |

샘플 합 0.45 는 점수 0.43 과 다르다. 앱은 서버가 준 `total` 을 그대로 쓴다.

- 근거 문장 — 12 / lh 1.55 / `#6B6862`, `padding-top 4`, 두 줄 (`<br>`). kind 값은 `mono`.
  - `선별: relevance 0.83 · kind technique — "KV 캐시 압축의 구체 기법과 수치, 코드 공개"`
  - `판정: importance 4 · 유사 피드백 👍 "PagedAttention v2 …"`

### 4. SectionLabel `당신의 판정` + FeedbackButton 두 개 (`px 16`)
`유용` 선택 샘플 (배경 `#1C1B19`, 흰 글자), `불필요` 미선택. 13/600, 높이 40, radius 10. 03 과 상태를 공유한다.

### 5. 안내 카드 — Card `padding 12px 16px`
12 / lh 1.6 / tertiary — `👍는 다음 선별·판정에 사례로 들어가고 arXiv cs.CL의 신뢰도를 보정합니다. Discord에서 누른 리액션과 자동으로 합쳐집니다.` 소스명(`arXiv cs.CL`)은 `mono` 이고 동적이다.

### 6. SectionLabel `최근 판정 · 오늘 3건` + 목록 카드 (`padding 4px 16px`, gap 0)
행 — flex gap 10, `padding 6px 0`, 첫 행 아래 1px `#EFECE6`. 아이콘 16 (👍 `thumbup` `#2D5BE3`, 👎 `thumbdown` `#B5651D`) + 제목 13 / 400 primary (flex-grow, 한 줄 말줄임) + 시간 11 tertiary.

| 판정 | 제목 | 시간 |
|---|---|---|
| 👍 | `MCP Python SDK v2.2.0 — HTTP 리다이렉트…` | `42분` |
| 👎 | `SDLC 에이전트 서베이 — 2026 상반기 동향` | `어제` |

`오늘 3건` 은 오늘 판정 수이고 목록은 기간과 무관한 최근 N건이다 (계약 4.2). 행 탭 → 그 알림의 07.

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| alert 필드 | – | 03 과 같음 | |
| score.`total` / `threshold` | float | 0.43 / 0.45 | |
| score.`components.*` | float | src 0.10 · rel 0.25 · fresh 0.10 · kind 0.00 | `hot`·`multi` 는 0 이 아닐 때만 행 추가 |
| `routing` | enum | `explore_slot` | 라벨 `경계 → 탐색 슬롯` |
| screening.`relevance` / `kind` / `reason` | float / enum / string | 0.83 / `technique` / `KV 캐시 …` | 선별 결정 |
| screening.`topics` | string[] | `["inference-opt"]` | 화면에는 쓰지 않음 |
| judgment.`importance` | int | 4 | |
| judgment.`similar_feedback[0]` | {feedback, title} | 👍 `PagedAttention v2 …` | |
| `recent_feedback` | {today_count, items[]} | 3, 2행 | |
| `trust_note_source` | string | `arXiv cs.CL` | 안내 카드 |

## 엣지
- 경계가 아니면 우측 라벨은 `routing` 라벨(`통과` 등)이다.
- `kind` 가 음수면 채움 없이 값만 `#B5651D` 로 보인다.

## Figma 와 다른 점 (HTML 우선)
- 제목은 17 / 700 / 1.4 다 (이전 추출본 18 · 1.35).
- 점수 바 라벨은 tertiary `mono` 이고 값은 `mono` 다. 채움 눈금은 공통 0.5 다 (이전 추출본 0.47).
- 근거 문장 색은 `#6B6862` 다 (추출본 `#55524B`).
- 판정 버튼 라벨은 13 이다 (추출본 14).
- 안내 카드 문장은 `👍는 …` 으로 시작한다 (Figma `유용 판정은 …`). 근거 둘째 줄도 `유사 피드백 👍` 다 (Figma `유용`).
- 최근 판정 제목은 400 이다 (추출본 Medium).
