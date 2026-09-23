# 06 수집 소스

- 원본 HTML: [`../source/SourceSettings.dc.html`](../source/SourceSettings.dc.html) (`gen.py.txt` `src_row()`) · Figma node `6:2` · 프레임 390 × 930 · 스크린샷 [06-sources.png](06-sources.png) (Figma)
- 하단 탭: **설정** 활성 (설정 하위)

## 목적

수집 소스 목록과 상태(주기·실패·trust)를 보고 소스별 on/off 를 바꾼다. 위에 오늘 수집량과 LLM 예산을 보여 준다.

## 레이아웃 (위 → 아래)

### 1. 하위 TopBar
`back` 20 + `수집 소스` (18/600). 우측 `plus` 22 → 소스 추가 (v1 범위 밖, `준비 중` 토스트).

### 2. Stat 3열 — 컨테이너 `padding 8px 16px 4px`, gap 12
StatCard(06) — Card `padding 12px 14px`, gap 2, margin 0, flex-grow. 라벨 11 tertiary, 값 22/700 + 접미 13/500 tertiary. **캡션 없음**.

| 라벨 | 값 | 접미 |
|---|---|---|
| `활성 소스` | `9` | ` / 10` |
| `오늘 수집` | `612` | ` 건` |
| `LLM 예산` | `41` | ` / 60` |

### 3. SectionLabel `기술 블로그 · RSS` + 카드 (`padding 2px 16px`, gap 0, SourceRow 3개)
### 4. SectionLabel `논문 · 릴리즈 · 영상` + 카드 (SourceRow 4개)
SourceRow — flex, gap 12, `padding 12px 0`, 마지막 외 아래 1px `#EFECE6`.
- 아이콘 타일 36×36, radius 10, `#F0EEE9`, 아이콘 18 `#55524B` (`rss` / `github` / `youtube`).
- 가운데(flex-grow) — 소스 ID 14 / 600 `mono` primary, 아래 상태 줄 11 tertiary. 오류면 상태 줄이 11 / 600 `#C2410C`.
- `trust {x}` 12 tertiary `mono`.
- Toggle.

| 그룹 | 소스 ID | 아이콘 | 상태 줄 | trust | 토글 |
|---|---|---|---|---|---|
| 기술 블로그 · RSS | `rss:anthropic` | rss | `실패 5회 · 미러 확인 필요` (오류색) | 1.0 | ON |
| | `rss:openai` | rss | `15분` | 0.9 | ON |
| | `rss:huggingface` | rss | `15분` | 0.8 | ON |
| 논문 · 릴리즈 · 영상 | `rss:arxiv-cs-ai` | rss | `60분 · 보정 0.5 → 0.58` | 0.5 | ON |
| | `github_release:watchlist` | github | `30분 · 저장소 10개` | 1.0 | ON |
| | `youtube:jocoding` | youtube | `15분` | 0.6 | ON |
| | `youtube:codingapple` | youtube | `15분` | 0.6 | OFF |

상태 줄 규칙 — `{주기}` 뒤에 선택적으로 `· 보정 {base} → {calibrated}` 또는 `· 저장소 {n}개`. 실패가 있으면 `실패 {n}회 · {조치}` 로 **바꾼다** (`gen.py.txt` 는 오류일 때 원래 상태 줄을 버린다).

### 5. SectionLabel `미착수` + 칩 (flex wrap, gap 8, `px 16`)
미선택 Chip — `Hacker News` `Reddit` `GitHub Trending` `X`. 탭 동작 없음.

### 6. TabBar — **설정** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `enabled_count` / `total` | int / int | 9 / 10 | |
| `items_collected` | int | 612 | 최근 24시간 |
| `llm_budget.triage.used` / `cap` | int / int | 41 / 60 | 선별 호출 |
| source.`id` | string | `rss:anthropic` | `sources.name` |
| source.`type` | enum | `rss` / `github_release` / `youtube` / `hackernews` / `hf_papers` | 아이콘 |
| source.`group` | enum | `blog_rss` / `paper_release_video` / `community` | 섹션 |
| source.`enabled` | bool | true | 토글 |
| source.`poll_interval_min` | int | 15 | `15분` |
| source.`trust` / `trust_base` / `trust_calibrated` | float | 0.58 / 0.5 / 0.58 | |
| source.`consecutive_failures` / `error_hint` | int / string? | 5 / `미러 확인 필요` | |
| source.`repo_count` | int? | 10 | github 전용 |
| `planned_sources` | string[] | `Reddit, GitHub Trending, X` | 정적 (계약 4.5) |

## 엣지
- 오류 소스도 토글은 ON 일 수 있다.
- OFF 소스는 토글만 회색이고 행 스타일은 같다.

## Figma 와 다른 점 (HTML 우선)
- Stat 카드에 캡션(`sources.enabled` `items 오늘` `llm_calls`)이 없다. 값 뒤 접미(`/ 10` `건` `/ 60`)가 13/500 tertiary 로 붙는다. Stat 간격은 12 다.
- Stat 라벨 색은 tertiary 다 (추출본 secondary).
- 소스 ID·trust 는 `mono` 다.
