# 10 걸러진 항목 · 종류별

- 원본 HTML: [`../source/DroppedByKind.dc.html`](../source/DroppedByKind.dc.html) · Figma node `9:181` · 프레임 390 × 1100 · 스크린샷 [10-filtered-by-type.png](10-filtered-by-type.png) (Figma)
- 하단 탭: **피드** 활성 · [09 소스별](09-filtered-by-source.md) 과 같은 화면의 `종류별` 보기

## 목적

걸러진 항목을 변화 종류(kind)별로 묶어 어떤 kind 가 감점·경계로 빠지는지 보여 준다. 구조·컴포넌트는 09 와 같고 묶는 기준만 다르다.

## 레이아웃 — 09 와 다른 점만

### 1. Segmented — `종류별` 선택

### 2. Summary 카드
헤더·GateBar·범례는 09 와 같다. 안내 문구는 `kind는 선별 단계 출력이라 exclude·중복 탈락 67건은 "미분류"로 묶입니다.`

### 3. SectionLabel `종류별 · 많은 순`

### 4. DropGroup 목록
그룹 헤더에 **아이콘 타일이 없다**. 이름은 `{kind} · {라벨}` 14/600.

| 그룹 이름 | 요약 | 건수 | 상태 |
|---|---|---|---|
| `survey · 서베이·전망` | `감점 −0.15 · 불필요 4/4 → 감점 유지 중` | 187 | 펼침 |
| `technique · 기법·논문` | `점수 경계(0.35–0.45) 154건 · 탐색 슬롯이 하루 1건 판정` | 176 | 펼침 |
| `other · 기타` | `선별 relevance 0.3 이하가 대부분` | 96 | 접힘 |
| `release_patch · 패치 릴리즈` | `중복 8 (버전 형제) · 클러스터 하루 1건` | 31 | 접힘 |
| `tutorial · 튜토리얼` | `감점 −0.05` | 9 | 접힘 |
| `promo · 홍보·구인` | `감점 −0.30 · exclude 키워드 2` | 5 | 접힘 |
| `미분류 (exclude·중복)` | `선별 전 탈락 — kind 없음` | 67 | 접힘 (항상 마지막) |

펼친 항목 (사유 줄에 소스명이 들어간다).

| 그룹 | 제목 | 태그 | 사유 |
|---|---|---|---|
| survey | Survey of Agentic Software Engineering, 2026H1 | 점수 탈락 | `0.41 · arXiv cs.SE` |
| survey | LLM Evaluation: A Position Paper | 선별 탈락 | `relevance 0.4 · "수치 없는 포지션 논문"` |
| technique | Beacon-style KV compaction for 1M-token context | 점수 탈락 | `0.43 · 경계 → 내일 탐색 슬롯 후보` |

### 5. TabBar — **피드** 활성

## 데이터 필드 (09 에 더해)

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| group.`kind` | enum? | `survey` … / null | null 은 `미분류 (exclude·중복)` |
| group.`kind_weight` | float | −0.15 | 화면 04 값 |
| group.`kind_feedback` / `penalty_active` | {not_useful, total} / bool | 4/4 / true | |
| group.`borderline_count` | int | 154 | |
| group.`exclude_keyword_hits` | int | 2 | |
| `unclassified_count` | int | 67 | exclude 9 + 중복 58 |
| item.`source_name` | string | `arXiv cs.SE` | 사유 줄 |

## 참고
- 그룹 합 187+176+96+31+9+5+67 = 571 로 걸러짐 합계와 같다.
- 그룹 목록은 04 의 kind 6개에 `other` 가 더해졌고 `news` 는 샘플에 없다. 앱은 건수가 있는 kind 를 모두 보여 준다.
- `release_patch` 요약의 `클러스터 하루 1건` 은 클러스터 하루 상한으로 억제된 항목 수다. 이 항목들은 일곱째 관문 `cluster_dup` 으로 걸러짐 합계·GateBar·kind 그룹에 들어가고 👍 복원할 수 있다 (계약 2·4.6).

## Figma 와 다른 점 (HTML 우선)
- 섹션 라벨은 `종류별 · 많은 순` 이다 (Figma `변화 종류별 (kind)` + 우 `많은 순`).
- 나머지 차이는 09 와 같다.
