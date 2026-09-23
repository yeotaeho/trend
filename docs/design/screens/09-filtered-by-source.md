# 09 걸러진 항목 · 소스별

- Figma node: `9:2` · 프레임 390 × 1080 · 스크린샷: [09-filtered-by-source.png](09-filtered-by-source.png)
- 하단 탭: **피드** 활성 (피드에서 push 된 하위 화면, 뒤로가기 있음)
- 같은 화면의 다른 탭: [10 종류별](10-filtered-by-type.md), `관문별`(디자인 없음)

## 목적

오늘 파이프라인이 사용자에게 보내지 않은(걸러진) 항목을 투명하게 보여준다. 어느 관문(exclude/중복/선별/점수/판정)에서 몇 건이 탈락했는지 요약하고, 소스별로 묶어 탈락 사유를 보여주며, 잘못 걸러진 항목을 👍(복원/유용)로 되살릴 수 있다.

진입: [03 피드](03-feed.md)의 `걸러짐 571건 보기 ›`.

## 레이아웃 (위 → 아래)

### 1. TopBar (`9:3`, 높이 77 + 세그먼트)
- `icon/back` 20 + 제목 `걸러진 항목` (Bold 18) / 우측 `icon/search` 22 → 걸러진 항목 검색(디자인 없음)
- **Segmented** (358×38, 좌우 16, TopBar 아래): `소스별` / `종류별` / `관문별` — 단일 선택, 이 화면은 `소스별` 선택. 스타일은 [tokens.md Segmented](../tokens.md#segmented-control).
  - `종류별` → 화면 10 / `관문별` → 관문(gate)별 그룹 화면(디자인 없음; 같은 DropGroup 구조로 gate 기준 그룹핑 권장)

### 2. Summary 카드 (`9:21`, 358×126)
- 헤더 행: `오늘 걸러짐 571` (Bold 15 `#1C1B19`) + ` / 수집 612` (Regular 13 `#8A877F`) / 우측 `최근 24시간` (Regular 12 `#8A877F`)
- **GateBar** 326×10, radius 5, 5구간 가로 스택 — 폭 = 건수 / 걸러짐 합계 × 326 (정확히 비례)

| 관문 | 라벨 | 건수 | 색 |
|---|---|---|---|
| exclude (키워드 제외) | `exclude 9` | 9 | `#B8B4AB` |
| 중복 제거 | `중복 58` | 58 | `#D6D2C9` |
| 선별(LLM relevance) | `선별 318` | 318 | `#9FB4EA` |
| 점수 미달 | `점수 164` | 164 | `#2D5BE3` |
| 판정(LLM importance) | `판정 22` | 22 | `#B5651D` |

- 범례 행: 8×8 원형 점 + 라벨 (Regular 11 `#55524B`), 항목 간 gap 10
- 하단 안내: `점수 탈락 중 경계(0.35–0.45) 154건 · 탐색 슬롯 후보` (Regular 12.5 `#55524B`)

### 3. SectionLabel `소스별` + 우측 `많은 순` (Regular 12 `#8A877F`, 정렬 표시. 탭 → 정렬 변경 권장: 많은 순/이름순)

### 4. DropGroup 리스트 (카드 간 gap 12)
**DropGroup 헤더** (접힘 시 카드 높이 64):
- 아이콘 타일 36×36 (`#F0EEE9`, radius 10, icon 18) — rss/github/youtube
- 소스 ID (SemiBold 14) + 탈락 사유 요약 (Regular 11 `#8A877F`)
- 우측 건수 (Bold 16 `#1C1B19`) + `icon/chev`(접힘, 오른쪽) / `icon/chevd`(펼침, 아래)
- 헤더 탭 → 펼침/접힘 토글 (펼치면 DroppedItem 목록, 샘플은 최대 3건 미리보기)

**DroppedItem** (펼친 그룹 안, 구분선 `#EFECE6`):
- 제목 (SemiBold 14 `#1C1B19`, 최대 2줄) + 우측 **RestoreButton** 32×32 (흰 배경, `#D9D5CC` 테두리, radius 8, `icon/thumbup` 15) → 탭 시 "이 항목은 유용했어야 함" 피드백 + 피드로 복원
- 아래 줄: 탈락 관문 Badge (`선별 탈락` / `점수 탈락` / (권장) `판정 탈락` `중복` `exclude`; 배경 `#E8EEFC`, 글자 `#2D5BE3`, SemiBold 11) + 사유 텍스트 (Regular 11 `#8A877F`, 최대 2줄)

| 소스 | 요약 | 건수 | 상태 |
|---|---|---|---|
| `rss:arxiv-cs-ai` (rss) | `선별 relevance 0.5 미만 71%` | 312 | 펼침 |
| `rss:arxiv-cs-cl` (rss) | `선별 relevance 0.5 미만 64%` | 198 | 접힘 |
| `rss:huggingface` (rss) | `중복 9 · 선별 11 · 점수 3` | 23 | 접힘 |
| `youtube:jocoding` (youtube) | `중복 4 (같은 채널 영상 클러스터) · 판정 10` | 14 | 접힘 |
| `github_release:watchlist` (github) | `중복 8 (버전 형제) · 판정 4` | 12 | 접힘 |
| `rss:vercel` (rss) | `exclude 2 (sponsored) · 선별 5` | 7 | 접힘 |

`rss:arxiv-cs-ai` 펼침 항목:

| 제목 | 배지 | 사유 |
|---|---|---|
| LLM 기반 자율주행 의사결정 프레임워크 제안 | 선별 탈락 | `relevance 0.3 · survey · "관심 스택과 무관한 도메인 서베이"` |
| Survey of Agentic Software Engineering, 2026H1 | 점수 탈락 | `0.41 (src 0.10 · rel 0.24 · kind −0.15)` |
| Beacon-style KV compaction for 1M-token context | 점수 탈락 | `0.43 · 경계 → 내일 탐색 슬롯 후보` |

### 5. TabBar — 공통, **피드** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `window` | string | `최근 24시간` | 집계 기간 |
| `filtered_total` | int | 571 | |
| `collected_total` | int | 612 | |
| `gate_counts.exclude` | int | 9 | |
| `gate_counts.dedup` | int | 58 | |
| `gate_counts.screening` | int | 318 | 선별 |
| `gate_counts.score` | int | 164 | 점수 |
| `gate_counts.judgment` | int | 22 | 판정 |
| `borderline_count` | int | 154 | 점수 탈락 중 경계 구간 |
| `borderline_range` | [float, float] | [0.35, 0.45] | 경계 구간 = [하한, 통과선] |
| group.`source_id` / `source_type` | string / enum | `rss:arxiv-cs-ai` / `rss` | |
| group.`count` | int | 312 | 정렬 기준 |
| group.`summary` | string | `선별 relevance 0.5 미만 71%` | 서버 생성 문자열 또는 gate별 count로 클라이언트 조합(`중복 9 · 선별 11 · 점수 3`) |
| item.`id` | string | – | 복원 API용 |
| item.`title` | string | `Survey of Agentic …` | 원문 제목(영문 그대로일 수 있음) |
| item.`dropped_gate` | enum | `screening` / `score` / `judgment` / `dedup` / `exclude` | 배지 |
| item.`relevance` | float | 0.3 | 선별 탈락 시 |
| item.`kind` | enum | `survey` | |
| item.`reason` | string | `관심 스택과 무관한 도메인 서베이` | LLM 사유 |
| item.`score_total` / `components` | float / {src, rel, kind, …} | 0.41 / src 0.10 · rel 0.24 · kind −0.15 | 점수 탈락 시 |
| item.`exploration_candidate` | bool | true | `경계 → 내일 탐색 슬롯 후보` |
| item.`restored` | bool | false | RestoreButton 상태 |

## 엣지
- 걸러짐 0건: GateBar 숨기고 "오늘 걸러진 항목이 없습니다" 권장.
- 그룹 펼침 시 전체 항목 수가 많으면 "더 보기" 페이징 필요(디자인 없음).
