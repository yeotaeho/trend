# 06 수집 소스

- Figma node: `6:2` · 프레임 390 × 930 · 스크린샷: [06-sources.png](06-sources.png)
- 하단 탭: **설정** 활성 (설정 하위 화면)

## 목적

수집 파이프라인이 긁어오는 소스(RSS, arXiv, GitHub 릴리즈, YouTube) 목록과 상태(주기, 실패, 신뢰도 trust)를 보고 소스별 on/off를 제어한다. 상단에 오늘의 수집 통계와 LLM 호출 예산을 보여준다.

## 레이아웃 (위 → 아래)

### 1. TopBar (`6:3`, 높이 77)
- `icon/back` 20 + 제목 `수집 소스` (Bold 18) / 우측 `icon/plus` 22 → 소스 추가(디자인 없음. 유형 선택: RSS URL / GitHub 저장소 / YouTube 채널 권장)

### 2. Stat 3열 (카드 111×88, gap 8, 좌우 16)
Stat 카드: 흰 배경, 1px `#E5E2DB`, radius 14, padding 14. 라벨(Regular 11 `#55524B`) / 값(Bold 22 lh 1.2 `#1C1B19`) / 캡션(Regular 11 `#8A877F`).

| 라벨 | 값 | 캡션 |
|---|---|---|
| `활성 소스` | `9 / 10` | `sources.enabled` |
| `오늘 수집` | `612 건` | `items 오늘` |
| `LLM 예산` | `41 / 60` | `llm_calls` |

(캡션은 개발용 필드명이 그대로 노출된 형태 — 디자인 의도대로 유지하거나 문구 교체는 기획 확인)

### 3. SectionLabel `기술 블로그 · RSS` + 카드 (SourceRow 3개)
### 4. SectionLabel `논문 · 릴리즈 · 영상` + 카드 (SourceRow 4개)
SourceRow (326×60, 구분선 `#EFECE6`):
- 좌: 아이콘 타일 36×36 (배경 `#F0EEE9`, radius 10, 아이콘 18 `#55524B`: `icon/rss` / `icon/github` / `icon/youtube`)
- 중: 소스 ID (SemiBold 14 `#1C1B19`) + 상태 줄 (Regular 11): 정상 `#8A877F`, **오류는 SemiBold `#C2410C`계열 붉은 주황**(`실패 5회 · 미러 확인 필요`)
- 우: `trust 1.0` (Regular 12 `#8A877F`) + Toggle 44×26
- 행 탭 → 소스 상세(디자인 없음), 토글 → 소스 활성/비활성

| 그룹 | 소스 ID | 아이콘 | 상태 줄 | trust | 토글 |
|---|---|---|---|---|---|
| 기술 블로그 · RSS | `rss:anthropic` | rss | `실패 5회 · 미러 확인 필요` (오류색) | 1.0 | ON |
| | `rss:openai` | rss | `15분` | 0.9 | ON |
| | `rss:huggingface` | rss | `15분` | 0.8 | ON |
| 논문 · 릴리즈 · 영상 | `rss:arxiv-cs-ai` | rss | `60분 · 보정 0.5 → 0.58` | 0.5 | ON |
| | `github_release:watchlist` | github | `30분 · 저장소 10개` | 1.0 | ON |
| | `youtube:jocoding` | youtube | `15분` | 0.6 | ON |
| | `youtube:codingapple` | youtube | `15분` | 0.6 | OFF |

상태 줄 조합 규칙: `{폴링 주기}` + 선택적 `· 보정 {base} → {calibrated}` / `· 저장소 {n}개` / 오류 시 `실패 {n}회 · {조치}`로 대체.

### 5. SectionLabel `미착수` + 칩 (wrap)
비활성 스타일 칩(흰 배경, `#D9D5CC` 테두리, Medium 13 `#55524B`): `Hacker News`, `Reddit`, `GitHub Trending`, `X`. 아직 지원 예정인 소스 — 탭 동작 없음(또는 "준비 중" 토스트).

### 6. TabBar — 공통, **설정** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `sources_enabled_count` / `sources_total` | int / int | 9 / 10 | `9 / 10` |
| `items_collected_today` | int | 612 | `612 건` |
| `llm_calls_used_today` / `llm_calls_budget` | int / int | 41 / 60 | 일일 LLM 호출 예산 |
| source.`id` | string | `rss:anthropic` | `{type}:{name}` 형식 |
| source.`type` | enum | `rss` / `github_release` / `youtube` | 아이콘·그룹 결정 |
| source.`group` | enum | `blog_rss` / `paper_release_video` | 섹션 분류 (arXiv RSS는 논문 그룹) |
| source.`enabled` | bool | true | 토글 (설정값) |
| source.`poll_interval_min` | int | 15 / 30 / 60 | 표시 `15분` |
| source.`trust` | float(0–1, 소수1자리) | 1.0 | `trust 0.9` |
| source.`trust_base` → `trust_calibrated` | float | 0.5 → 0.58 | 피드백 기반 보정, 있을 때만 |
| source.`consecutive_failures` | int | 5 | >0 이면 오류 표시 |
| source.`error_hint` | string | `미러 확인 필요` | |
| source.`repo_count` | int | 10 | github watchlist 전용 |
| `planned_sources` | string[] | `Hacker News, Reddit, GitHub Trending, X` | 미착수 |

## 엣지
- 오류 소스는 상태 줄을 오류색으로 표시(토글은 ON 유지 가능).
- 비활성(OFF) 소스는 토글만 회색, 행 스타일 동일.
