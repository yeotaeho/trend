# 08 내 프로필 (사용자 파악)

- Figma node: `6:217` · 프레임 390 × 1020 · 스크린샷: [08-profile.png](08-profile.png)
- 하단 탭: **내 프로필** 활성 (탭 루트 화면, 뒤로가기 없음)

## 목적

최근 14일 동안 시스템이 사용자를 어떻게 파악했는지 보여준다: 받은 알림·유용 비율·놓친 이슈 통계, 카테고리별 반응, 자동 학습된 취향(감점/신뢰도 보정/개인 모델 진행도), 주간 리포트 진입.

## 레이아웃 (위 → 아래)

### 1. TopBar (`6:218`, 높이 83)
- 좌: 제목 `내 프로필` (Bold 22) / 우: `최근 14일` (Regular 13 `#8A877F`) — 기간 표시. 탭 가능 여부 디자인상 불명(기간 선택 드롭다운으로 확장 가능: 7일/14일/30일 권장)

### 2. 사용자 행
- 아바타 40×40 원형, 배경 `#1C1B19`, 이니셜 `여` (SemiBold 14 흰색)
- 이름 `여태호` (SemiBold 15 `#1C1B19`) / 부가 `Discord 연결됨 · 온보딩 8/8 완료` (Regular 12 `#8A877F`)

### 3. Stat 3열 (각 112×88, gap 8) — 06 화면과 같은 Stat 컴포넌트
| 라벨 | 값 | 캡션 |
|---|---|---|
| `받은 알림` | `61` | `push 38 · 실험 9` |
| `유용 비율` | `64%` | `유용 27 / 불필요 15` |
| `놓친 이슈` | `1` | `직접 찾아본 건` |

### 4. SectionLabel `반응한 카테고리 · 유용 / 불필요` + 카드 (`6:243`)
행 6개 (각 17 높이, 행 간 10): 카테고리 slug (96 폭, Regular 12 `#55524B`) / 스택 바 182×10 radius 5 (트랙 `#EFECE6`, 유용 구간 `#2D5BE3`, 불필요 구간 `#E0A373`) / 우측 총 반응 수(Regular 12 `#55524B`, 우정렬).

| 카테고리 | 합계 | 유용 바(px) | 불필요 바(px) |
|---|---|---|---|
| `mcp-tooling` | 14 | 110 | 20 |
| `llm-model` | 11 | 96 | 16 |
| `inference-opt` | 9 | 72 | 24 |
| `agent` | 8 | 50 | 40 |
| `video` | 6 | 20 | 60 |
| `dev-community` | 4 | 16 | 48 |

(바 폭은 샘플 목업값으로 합계와 정확히 비례하지 않음. 구현: 바 전체 폭 = 최대 합계 기준 정규화, 내부를 유용/불필요 비율로 분할 권장. 정렬: 합계 내림차순.)

### 5. SectionLabel `학습된 취향` + 카드 (`6:283`)
키-값 행 4개 (좌 Regular 13 `#1C1B19` / 우 SemiBold 13, 강조 시 `#B5651D`):

| 좌 | 우 | 비고 |
|---|---|---|
| `서베이·전망 논문` | `불필요 4 / 4 → 자동 감점 중` (주황) | kind 자동 감점 규칙 발동 |
| `arXiv cs.CL 신뢰도` | `0.50 → 0.58` | 소스 trust 보정 |
| `youtube:codingapple` | `0.60 → 0.52` | 소스 trust 보정(하향) |
| `프로필 벡터 라벨` | `42건 (개인 모델 전환 50건)` | 개인 모델 전환까지 진행도 |

### 6. SectionLabel `주간 리포트` + 카드 (`6:299`, 탭 가능)
- 제목 `9월 2주차 리포트` (SemiBold 14) / 부제 `relevance 구간 × kind · 통과/탈락/유용/불필요` (Regular 12 `#8A877F`) / 우측 `icon/chev` 18
- 탭 → 주간 리포트 상세 (디자인 없음)

### 7. TabBar — 공통, **내 프로필** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `period_days` | int | 14 | `최근 14일` |
| user.`display_name` | string | `여태호` | 아바타 이니셜 = 첫 글자 `여` |
| user.`discord_connected` | bool | true | `Discord 연결됨` |
| user.`onboarding_done` / `onboarding_total` | int / int | 8 / 8 | `온보딩 8/8 완료` |
| stats.`alerts_received` | int | 61 | |
| stats.`push_count` | int | 38 | |
| stats.`experiment_count` | int | 9 | |
| stats.`useful_ratio` | percent(int) | 64 | `64%` = useful/(useful+not_useful) |
| stats.`useful_count` | int | 27 | |
| stats.`not_useful_count` | int | 15 | |
| stats.`missed_issues` | int | 1 | 사용자가 직접 찾아본(놓친) 건 수 |
| `category_reactions[]` | {category, useful, not_useful, total} | `mcp-tooling`, 14 | |
| `learned.kind_penalties[]` | {kind_label, not_useful, total, auto_penalty_active} | `서베이·전망 논문`, 4/4, true | |
| `learned.source_trust_changes[]` | {source_label, from, to} | `arXiv cs.CL`, 0.50→0.58 | 소수 2자리 |
| `learned.profile_vector_labels` | int | 42 | |
| `learned.personal_model_threshold` | int | 50 | |
| `weekly_report.latest` | {id, title, subtitle} | `9월 2주차 리포트` | |
