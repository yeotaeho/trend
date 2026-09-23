# 09 걸러진 항목 · 소스별

- 원본 HTML: [`../source/DroppedBySource.dc.html`](../source/DroppedBySource.dc.html) (`gen.py.txt` `dropped_screen()` `drop_group()` `drop_item()`) · Figma node `9:2` · 프레임 390 × 1080 · 스크린샷 [09-filtered-by-source.png](09-filtered-by-source.png) (Figma)
- 하단 탭: **피드** 활성 (피드 하위, 뒤로가기)
- 같은 화면의 다른 보기: [10 종류별](10-filtered-by-type.md), `관문별` (디자인 없음)

## 목적

보내지 않은(걸러진) 항목을 투명하게 보여 준다. 관문(exclude·중복·선별·점수·판정)별 탈락 수, 소스별 묶음과 사유, 잘못 걸러진 항목의 👍 복원.

진입은 [03 피드](03-feed.md) 의 `걸러짐 571건 보기 ›`.

## 레이아웃 (위 → 아래)

### 1. 하위 TopBar
`back` 20 + `걸러진 항목` (18/600). 우측 `search` 22 (디자인 없음).

### 2. Segmented — `padding 4px 16px 10px`
`소스별` / `종류별` / `관문별`, 이 화면은 `소스별`.

### 3. Summary 카드 — Card (padding 16, **gap 10**)
- 헤더 행 (space-between) — 좌 `오늘 걸러짐 571` 15/600 + ` / 수집 612` (13 / 400 tertiary), 우 `최근 24시간` 12 tertiary.
- GateBar + 범례 ([tokens Bars](../tokens.md#bars)).

| 관문 | 범례 | 건수 | 색 |
|---|---|---|---|
| exclude | `exclude 9` | 9 | `#B8B4AB` |
| 중복 | `중복 58` | 58 | `#D6D2C9` |
| 선별 | `선별 318` | 318 | `#9FB4EA` |
| 점수 | `점수 164` | 164 | `#2D5BE3` |
| 판정 | `판정 22` | 22 | `#B5651D` |

- 안내 — 12 / lh 1.5 / `#55524B` — `점수 탈락 중 경계(0.35–0.45) 154건 · 탐색 슬롯 후보`.

### 4. SectionLabel `소스별 · 많은 순`
한 문자열이다. 정렬 전환(`많은 순`/`이름순`)은 라벨 탭으로 붙인다 (디자인 없음).

### 5. DropGroup 목록 — 세로 flex **gap 10**
DropGroup — Card `padding 6px 16px`, gap 0.
- 헤더 — flex gap 12, `padding 8px 0` (펼침이면 아래 1px `#EFECE6`).
  - 아이콘 타일 36×36 radius 10 `#F0EEE9`, 아이콘 18 `#55524B`.
  - 가운데(flex-grow) — 이름 14/600 primary, 요약 11 tertiary.
  - 건수 16/700, `chev`(접힘) / `chevd`(펼침) 16 `#B8B4AB`.
- 헤더 탭 → 펼침/접힘.

DroppedItem (펼친 그룹 안) — 세로 flex gap 6, `padding 10px 0`, 마지막 외 아래 1px `#EFECE6`.
- 윗줄 (space-between, gap 8) — 제목 13.5 / 500 / lh 1.4 primary, RestoreButton 32×32 (`thumbup` 15).
- 아랫줄 (flex gap 8) — 탈락 태그 `{관문} 탈락` ([tokens 탈락 태그](../tokens.md#탈락-태그-stage_tag-0910)) + 사유 11 tertiary.

| 소스 | 요약 | 건수 | 상태 |
|---|---|---|---|
| `rss:arxiv-cs-ai` (rss) | `선별 relevance 0.5 미만 71%` | 312 | 펼침 |
| `rss:arxiv-cs-cl` (rss) | `선별 relevance 0.5 미만 64%` | 198 | 접힘 |
| `rss:huggingface` (rss) | `중복 9 · 선별 11 · 점수 3` | 23 | 접힘 |
| `youtube:jocoding` (youtube) | `중복 4 (같은 채널 영상 클러스터) · 판정 10` | 14 | 접힘 |
| `github_release:watchlist` (github) | `중복 8 (버전 형제) · 판정 4` | 12 | 접힘 |
| `rss:vercel` (rss) | `exclude 2 (sponsored) · 선별 5` | 7 | 접힘 |

`rss:arxiv-cs-ai` 펼침 항목.

| 제목 | 태그 | 사유 |
|---|---|---|
| LLM 기반 자율주행 의사결정 프레임워크 제안 | 선별 탈락 | `relevance 0.3 · survey · "관심 스택과 무관한 도메인 서베이"` |
| Survey of Agentic Software Engineering, 2026H1 | 점수 탈락 | `0.41 (src 0.10 · rel 0.24 · kind −0.15)` |
| Beacon-style KV compaction for 1M-token context | 점수 탈락 | `0.43 · 경계 → 내일 탐색 슬롯 후보` |

### 6. TabBar — **피드** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `window_hours` | int | 24 | `최근 24시간` |
| `filtered_total` / `collected_total` | int | 571 / 612 | |
| `gate_counts.*` | int | 9 / 58 / 318 / 164 / 22 | 계약은 `stale` 과 `cluster_dup` (`클러스터 하루 1건`, 클러스터 하루 상한으로 억제된 항목) 구간을 더한다. 둘 다 디자인 색이 없어 계약 2 의 권장색을 쓴다 |
| `borderline.count` / `range` | int / [float, float] | 154 / [0.35, 0.45] | |
| group.`key` / `source` / `count` | – | `rss:arxiv-cs-ai` / 312 | |
| group 요약 재료 | – | `low_relevance_ratio`, `gate_counts` | 요약 문장은 클라이언트가 만든다 |
| item.`id` / `title` / `dropped_gate` | – | `score` | |
| item.`relevance` / `kind` / `reason` / `topics` | – | 0.3 / `survey` | 선별 결정 |
| item.`score` | {total, components} | 0.41 | 점수 결정 |
| item.`exploration_candidate` / `restored` | bool | true / false | |

## 엣지
- 걸러짐 0건이면 GateBar 를 숨기고 `오늘 걸러진 항목이 없습니다`.
- 그룹 항목이 많으면 `더 보기` 페이징 (디자인 없음).

## Figma 와 다른 점 (HTML 우선)
- 섹션 라벨은 `소스별 · 많은 순` 한 문자열이다 (Figma 는 좌 `소스별` + 우 `많은 순`).
- 그룹 카드 간격은 10 이다 (추출본 12).
- 탈락 태그 색이 관문마다 다르다 (추출본은 전부 `#E8EEFC` / `#2D5BE3`). `선별` 은 `#EAF0FC` / `#4A6FD0`.
- 항목 제목은 13.5 / 500 이다 (추출본 SemiBold 14). 범례 글자는 tertiary, 범례 점은 radius 3 사각형이다.
- 안내 문구는 12 / lh 1.5 다 (추출본 12.5).
