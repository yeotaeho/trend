# 07 피드백 · 판정 근거

- Figma node: `6:139` · 프레임 390 × 960 · 스크린샷: [07-feedback-rationale.png](07-feedback-rationale.png)
- **하단 탭바 없음** (피드 카드에서 push 되는 상세 화면)

## 목적

특정 알림 하나에 대해 "왜 이 알림이 왔는지"(점수 구성, 선별/판정 LLM 근거)를 투명하게 보여주고, 유용/불필요 판정을 받는다. 판정이 이후 선별·신뢰도에 어떻게 반영되는지 안내하고, 최근 판정 이력을 보여준다.

진입: [03 피드](03-feed.md) 카드 탭, (권장) 푸시 알림 탭, 최근 판정 행 탭.

## 레이아웃 (위 → 아래)

### 1. TopBar (`6:140`, 높이 77)
- `icon/back` 20 + 제목 `피드백` (Bold 18) / 우측 `icon/external` 22 → 원문 URL 외부 브라우저 열기

### 2. 알림 요약 카드 (`6:151`, 358×166)
FeedCard의 축약판(액션 행·태그 없음):
- 메타 행: `arXiv cs.CL · 3시간 전` (Regular 12 `#8A877F`) + Badge `실험` (배경 `#FDF1E2`, 글자 `#B5651D`)
- 제목: `BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배` (Bold/SemiBold 18, lh 1.35 — 피드 카드보다 큼, 텍스트 높이 48 = 2줄)
- 요약: `고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개.` (Regular 13.5 `#55524B`)

### 3. SectionLabel `이 알림이 온 이유` + 근거 카드 (`6:161`, 358×225)
- 헤더 행 (space-between):
  - 좌: `점수 0.43` (SemiBold 13 `#1C1B19`) + ` / 통과선 0.45` (Regular 13 `#8A877F`)
  - 우: `경계 → 탐색 슬롯` (SemiBold 12 `#B5651D`) — 결과 라우팅 라벨
- 점수 분해 바 4행 (각 17 높이, 행 간 10):
  - 라벨(56 폭, Regular 12 `#55524B`) / 바 트랙 206×8 radius 4 `#EFECE6` + 채움 `#2D5BE3` / 값(44 폭, 우정렬 Regular 12 `#55524B`)
  - 채움 폭(Figma px): src 44, rel 110, fresh 44, kind 2 → 대략 `폭 = 값 / 0.47 × 206` (스케일 최대값은 추정; 각 구성요소의 최대 기여도로 정규화 권장)

| 구성요소 | 의미 | 값 |
|---|---|---|
| `src` | 소스 신뢰도 기여 | 0.10 |
| `rel` | relevance(관련도) 기여 | 0.25 |
| `fresh` | 신선도 기여 | 0.10 |
| `kind` | kind 가중치 기여 | 0.00 |

(주: 샘플 합계 0.45 ≠ 점수 0.43 — 반올림/기타 항목 차이. 서버가 준 total을 그대로 표시)

- 근거 텍스트 (Regular 12 / lh 1.55 `#55524B`, 2줄 블록):
  - `선별: relevance 0.83 · kind technique — "KV 캐시 압축의 구체 기법과 수치, 코드 공개"`
  - `판정: importance 4 · 유사 피드백 유용 "PagedAttention v2 …"`

### 4. SectionLabel `당신의 판정` + Feedback 버튼 2개 (각 175×40, gap 8, 좌우 16)
- `유용` (icon/thumbup) — 샘플 **선택됨**: 배경 `#1C1B19`, 흰 글자
- `불필요` (icon/thumbdown) — 미선택: 흰 배경, `#D9D5CC` 테두리
- radius 10, SemiBold 14. 상호배타 토글, 03 피드의 버튼과 동일 상태 공유

### 5. 안내 카드 (`6:201`, 358×62)
Regular 12 / lh 1.55 `#8A877F`: `유용 판정은 다음 선별·판정에 사례로 들어가고 arXiv cs.CL의 신뢰도를 보정합니다. Discord에서 누른 리액션과 자동으로 합쳐집니다.` (소스명은 동적)

### 6. SectionLabel `최근 판정 · 오늘 3건` + 리스트 카드 (`6:206`)
행: 판정 아이콘 16 (유용 = `icon/thumbup` `#2D5BE3`, 불필요 = `icon/thumbdown` `#B5651D`) + 제목 1줄 말줄임(Medium 13 `#1C1B19`) + 우측 시간(Regular 11 `#8A877F`). 행 구분선 `#EFECE6`.

| 판정 | 제목 | 시간 |
|---|---|---|
| 유용 | `MCP Python SDK v2.2.0 — HTTP 리다이렉트…` | `42분` |
| 불필요 | `SDLC 에이전트 서베이 — 2026 상반기 동향` | `어제` |

(라벨은 "오늘 3건"이지만 샘플 행은 2개, 그중 하나는 `어제` — 개수·기간 정의 확인 필요.) 행 탭 → 해당 알림의 07 화면.

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| alert.`source_name`, `delivered_at`, `delivery_mode`, `title`, `summary`, `url` | – | 03과 동일 | |
| score.`total` | float(2자리) | 0.43 | `점수 0.43` |
| score.`threshold` | float | 0.45 | `통과선 0.45` |
| score.`components.src` | float | 0.10 | |
| score.`components.rel` | float | 0.25 | |
| score.`components.fresh` | float | 0.10 | |
| score.`components.kind` | float | 0.00 | 음수 가능(감점 kind) |
| `routing_label` | enum/string | `경계 → 탐색 슬롯` | 통과/경계→탐색 슬롯/탈락 등 |
| screening.`relevance` | float | 0.83 | 선별 LLM 출력 |
| screening.`kind` | enum | `technique` | |
| screening.`reason` | string | `KV 캐시 압축의 구체 기법과 수치, 코드 공개` | 따옴표로 감싸 표시 |
| judgment.`importance` | int 1–5 | 4 | 판정 LLM 출력 |
| judgment.`similar_feedback` | {label, title} | 유용, `PagedAttention v2 …` | few-shot 사례 |
| alert.`feedback` | enum? | `useful` | 버튼 상태 |
| `recent_feedback[]` | {alert_id, feedback, title, created_at} | 위 표 | 시간 표시 `42분`, `어제` |
| `recent_feedback_today_count` | int | 3 | 섹션 라벨 |

## 엣지
- 경계 항목이 아니면 우측 라벨 없음 또는 `통과` 표시 권장.
- kind 값 0이면 바 채움 최소 2px (0 표시용).
