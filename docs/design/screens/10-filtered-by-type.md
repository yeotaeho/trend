# 10 걸러진 항목 · 종류별

- Figma node: `9:181` · 프레임 390 × 1100 · 스크린샷: [10-filtered-by-type.png](10-filtered-by-type.png)
- 하단 탭: **피드** 활성 · [09 소스별](09-filtered-by-source.md)과 같은 화면의 `종류별` 세그먼트 상태

## 목적

걸러진 항목을 변화 종류(kind)별로 묶어, 어떤 kind가 감점/경계로 많이 빠지는지 보여준다. 구조·컴포넌트는 09와 동일하며 그룹 기준만 다르다.

## 레이아웃 (위 → 아래) — 09와 차이점만 상세

### 1. TopBar + Segmented — `종류별` 선택 (나머지 09와 동일)

### 2. Summary 카드 (`9:200`, 358×144)
- 헤더·GateBar·범례는 09와 동일 (`오늘 걸러짐 571` / `/ 수집 612` / `최근 24시간`, exclude 9 · 중복 58 · 선별 318 · 점수 164 · 판정 22)
- 하단 안내 문구(2줄): `kind는 선별 단계 출력이라 exclude·중복 탈락 67건은 "미분류"로 묶입니다.`

### 3. SectionLabel `변화 종류별 (kind)` + 우측 `많은 순`

### 4. DropGroup 리스트
그룹 헤더에 **아이콘 타일 없음**(소스별과 차이). 제목 형식 `{kind} · {kind 한글명}` (SemiBold 14) + 요약 (Regular 11 `#8A877F`, 최대 2줄) + 건수 (Bold 16) + chev/chevd.

| 그룹 제목 | 요약 | 건수 | 상태 |
|---|---|---|---|
| `survey · 서베이·전망` | `감점 −0.15 · 불필요 4/4 → 감점 유지 중` | 187 | 펼침 |
| `technique · 기법·논문` | `점수 경계(0.35–0.45) 154건 · 탐색 슬롯이 하루 1건 판정` | 176 | 펼침 |
| `other · 기타` | `선별 relevance 0.3 이하가 대부분` | 96 | 접힘 |
| `release_patch · 패치 릴리즈` | `중복 8 (버전 형제) · 클러스터 하루 1건` | 31 | 접힘 |
| `tutorial · 튜토리얼` | `감점 −0.05` | 9 | 접힘 |
| `promo · 홍보·구인` | `감점 −0.30 · exclude 키워드 2` | 5 | 접힘 |
| `미분류 (exclude·중복)` | `선별 전 탈락 — kind 없음` | 67 | 접힘 (항상 마지막) |

펼친 그룹 항목 (DroppedItem, 09와 동일 컴포넌트; 사유 줄에 소스명이 들어감):

| 그룹 | 제목 | 배지 | 사유 |
|---|---|---|---|
| survey | Survey of Agentic Software Engineering, 2026H1 | 점수 탈락 | `0.41 · arXiv cs.SE` |
| survey | LLM Evaluation: A Position Paper | 선별 탈락 | `relevance 0.4 · "수치 없는 포지션 논문"` |
| technique | Beacon-style KV compaction for 1M-token context | 점수 탈락 | `0.43 · 경계 → 내일 탐색 슬롯 후보` |

### 5. TabBar — 공통, **피드** 활성 (스크린샷 하단에서 잘려 보임)

## 데이터 필드 (09에 추가/차이)

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| group.`kind` | enum? | `survey` / `technique` / `other` / `release_patch` / `tutorial` / `promo` / null(미분류) | null → `미분류 (exclude·중복)` |
| group.`kind_label` | string | `서베이·전망` | |
| group.`kind_weight` | float | −0.15 | 요약의 `감점 −0.15` (화면 04 kind 가중치와 동일 값) |
| group.`auto_penalty` | {not_useful, total, active} | 4/4, true | `불필요 4/4 → 감점 유지 중` |
| group.`borderline_count` | int | 154 | technique 그룹 |
| group.`exclude_keyword_hits` | int | 2 | promo 그룹 |
| group.`count` | int | 187 | |
| `unclassified_count` | int | 67 | = exclude 9 + 중복 58 |
| item.`source_name` | string | `arXiv cs.SE` | 종류별 보기에서 사유 줄에 표시 |

## 참고
- 그룹 합계(187+176+96+31+9+5+67 = 571) = 오늘 걸러짐 합계와 일치.
- kind 목록이 화면 04의 kind 가중치 목록(release_major, release_patch, technique, survey, tutorial, promo)에 `other`가 추가된 형태.
