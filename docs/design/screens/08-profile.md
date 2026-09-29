# 08 내 프로필 (사용자 파악)

- 원본 HTML: [`../source/Profile.dc.html`](../source/Profile.dc.html) (`gen.py.txt` `stat()` `hbar()`) · Figma node `6:217` · 프레임 390 × 1020 · 스크린샷 [08-profile.png](08-profile.png) (Figma)
- 하단 탭: **내 프로필** 활성 (탭 루트)

## 목적

최근 14일 동안 시스템이 사용자를 어떻게 파악했는지 보여 준다. 받은 알림·유용 비율·놓친 이슈, 카테고리별 반응, 학습된 취향, 주간 리포트 진입.

## 레이아웃 (위 → 아래)

### 1. 루트 TopBar — `margin-top 44`, 높이 56, `px 20`
좌 `내 프로필` 22/700, 우 `최근 14일` 13 tertiary (기간 선택 7·14·30일로 확장).

### 2. 사용자 행 — flex gap 12, `padding 4px 20px 12px`
- Avatar 44×44 `#1C1B19`, 이니셜 `여` 16/700 흰색.
- 이름 `여태호` 15/600, 아래 `Discord 연결됨 · 온보딩 8/8 완료` 12 tertiary.

### 3. Stat 3열 — flex gap 10, `px 16`
StatCard(08) — radius 14, padding 14, gap 2. 라벨 11 tertiary, 값 24/700, 캡션 11 tertiary.

| 라벨 | 값 | 캡션 |
|---|---|---|
| `받은 알림` | `61` | `push 38 · 실험 9` |
| `유용 비율` | `64%` | `👍 27 / 👎 15` |
| `놓친 이슈` | `1` | `직접 찾아본 건` |

### 4. SectionLabel `반응한 카테고리 · 👍 / 👎` + 카드 (padding 16, gap 10)
StackedBar 6행 ([tokens Bars](../tokens.md#bars)). 라벨은 slug 그대로(12 `#55524B`, 폭 92).

| slug | 👍 폭 | 👎 폭 | 합계 |
|---|---|---|---|
| `mcp-tooling` | 55% | 10% | 14 |
| `llm-model` | 48% | 8% | 11 |
| `inference-opt` | 36% | 12% | 9 |
| `agent` | 25% | 20% | 8 |
| `video` | 10% | 30% | 6 |
| `dev-community` | 8% | 24% | 4 |

샘플 폭은 목업이라 합계와 비례하지 않는다. 앱은 최대 합계를 트랙 100% 로 두고 👍·👎 를 개수 비율로 나눈다. 정렬은 합계 내림차순.

### 5. SectionLabel `학습된 취향` + 카드 (기본 Card, 안쪽 세로 gap 10)
행 — space-between, 13px. 좌 `#55524B`, 우 600.

| 좌 | 우 | 우측 스타일 |
|---|---|---|
| `서베이·전망 논문` | `👎 4 / 4 → 자동 감점 중` | `#B5651D` |
| `arXiv cs.CL 신뢰도` | `0.50 → 0.58` | `mono` |
| `youtube:codingapple` | `0.60 → 0.52` | `mono` |
| `프로필 벡터 라벨` | `42건 (개인 모델 전환 50건)` | 괄호 부분 500 tertiary |

### 6. SectionLabel `주간 리포트` + 카드 (`padding 14px 16px`, 탭 가능)
좌 `9월 2주차 리포트` 14/600, 아래 `relevance 구간 × kind · 통과/탈락/👍/👎` 12 tertiary. 우 `chev` 18 `#B8B4AB`. 탭 → 리포트 상세 (디자인 없음).

### 7. TabBar — **내 프로필** 활성

## 데이터 필드

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `period_days` | int | 14 | |
| user.`display_name` | string | `여태호` | 이니셜 = 첫 글자 |
| user.`discord_connected` | bool | true | |
| user.`onboarding_done` / `total` | int / int | 8 / 8 | 정적 |
| stats.`alerts_received` / `push_count` / `experiment_count` | int | 61 / 38 / 9 | |
| stats.`useful_ratio` / `useful_count` / `not_useful_count` | int / int / int | 64 / 27 / 15 | |
| stats.`missed_issues` | int | 1 | 기간 안 복원 수 (계약 4.8) |
| `category_reactions[]` | {category, useful, not_useful, total} | `mcp-tooling` 14 | 판정 × 선별 topics |
| `learned.kind_penalties[]` | {kind, weight, not_useful, total, active} | survey 4/4 | |
| `learned.source_trust_changes[]` | {source_name, from, to} | 0.50 → 0.58 | |
| `learned.profile_vector_labels` / `personal_model_threshold` | int / int | 42 / 50 | 50 은 정적 |
| `weekly_report_latest` | {id, title, subtitle} | `9월 2주차 리포트` | |

## Figma 와 다른 점 (HTML 우선)
- 아바타는 44 에 16/700 이다 (추출본 40, 14 SemiBold).
- Stat 값은 24, 간격은 10 이다 (추출본 22, 8).
- 이모지 문구가 HTML 원문이다. `👍 27 / 👎 15`, `반응한 카테고리 · 👍 / 👎`, `👎 4 / 4 → 자동 감점 중`, `통과/탈락/👍/👎` (Figma 는 `유용`·`불필요` 로 바꿔 적었다).
- 카테고리 바 라벨 색은 `#55524B`, 합계는 tertiary `mono` 다. 바 폭은 백분율이다 (추출본 px).
- 학습된 취향 좌측 색은 `#55524B` 다 (추출본 primary).
