# 11 찜한 알림

- Figma node: `23:39` · 프레임 390 × 1360 (세로 스크롤)
- **스크린샷 없음**: Figma MCP 호출 한도(Starter 플랜) 초과로 PNG 추출 실패. 아래 명세는 Figma 레이어 메타데이터(텍스트·위치·크기)와 다른 화면의 공통 컴포넌트 스타일을 기반으로 작성. 색상 중 일부는 추정(★ 표시).
- 하단 탭: **찜** 활성 (탭 아이콘이 `icon/bookmarkFill`로 바뀜)

## 목적

사용자가 찜(북마크)한 알림을 폴더별로 보관·관리한다. 메모, 폴더 이동, 찜 해제, 원문 열기를 제공한다. 찜은 알림 상한·피드백 학습과 분리된 개인 보관함이다.

## 레이아웃 (위 → 아래)

### 1. TopBar (`23:40`, 높이 83)
- 좌: 제목 `찜` (Bold 22) — 탭 루트, 뒤로가기 없음
- 우: `icon/search` 22 (찜 검색) + `icon/dots` 22 (더보기 메뉴: 폴더 관리/정렬 등 — 디자인 없음), gap 14

### 2. 폴더 칩 행 (`23:50`, 높이 52, 가로 스크롤 — 마지막 칩이 390 폭 밖까지 이어짐)
칩 높이 36, gap 8, 좌 padding 16. 칩 = 폴더명(Medium 13) + 개수(Regular 11, 폴더명 오른쪽). 단일 선택. 선택 칩은 검정 배경/흰 글자(03 필터 칩과 동일 규칙 ★), 미선택은 흰 배경+`#D9D5CC` 테두리.

| 칩 | 개수 | 샘플 상태 |
|---|---|---|
| `전체` | 23 | 선택 ★ |
| `나중에 읽기` | 9 | |
| `적용해보기` | 6 | |
| `ClickMe 참고` | 5 | |
| `+` | – | 탭 → 새 폴더 만들기 (이름 입력) |

### 3. 정렬/필터 줄 (`23:65`, 높이 25, px 20)
- 좌: `최근 찜한 순` (Regular 12 `#55524B`) — 탭 → 정렬 선택(권장: 최근 찜한 순 / 오래된 순 / 알림 시간 순)
- 우: `안 읽음 7` (SemiBold 12 `#2D5BE3` ★) — 탭 → 안 읽은 찜만 보기 토글 권장

### 4. SavedCard 리스트 (`23:68`, 카드 간 gap 12)
SavedCard (358 폭, radius 14, 흰 배경, 테두리 ★; 내부 padding 17 → 1px보다 굵은 테두리 가능성 있음, 안 읽음 강조일 수 있음 — 확인 필요):
1. 메타 행: `{소스명} · {찜/알림 날짜}` (Regular 12 `#8A877F`, 날짜 형식 `9월 14일`) + 우측 폴더 Badge (SemiBold 11, 중립 배지 ★ 배경 `#F0EEE9` 글자 `#55524B`)
2. 제목 (SemiBold 16 / lh 1.4, 최대 2줄)
3. (메모가 있을 때만) **Memo** 박스 324×34: 좌 `메모` 라벨 (SemiBold 12 `#8A877F`) + 메모 본문 (Regular 13 `#1C1B19`), 배경 `#F5F4F0` ★ radius 8, padding 8/10
4. 액션 행 (높이 40, gap 8): `원문` OpenButton 76×40 (`icon/external`) → 원문 열기 / `폴더` MoveButton 76×40 (`icon/folder`) → 폴더 이동 바텀시트 / (빈 공간) / IconButton 40×40 `icon/bookmarkFill`(파랑) → 찜 해제(확인 또는 되돌리기 스낵바 권장)
- 카드 탭 → [07 피드백 · 판정 근거](07-feedback-rationale.md) (해당 알림 상세) 권장; 메모 탭 → 메모 편집(디자인 없음)

| # | 메타 | 폴더 배지 | 제목 | 메모 |
|---|---|---|---|---|
| 1 | GitHub Releases · 9월 14일 | 적용해보기 | [릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 | trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인 |
| 2 | arXiv cs.CL · 9월 12일 | 나중에 읽기 | BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배 | – |
| 3 | Anthropic · 9월 9일 | ClickMe 참고 | [모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일 | 페르소나 시뮬레이터 배치 비용 재계산 |
| 4 | youtube:jocoding · 9월 8일 | 나중에 읽기 | Claude Code 서브에이전트로 1인 개발 팀 만들기 | – |

### 5. SectionLabel `찜 안내` + 안내 카드 (`23:168`)
Regular 12 / lh 1.55 `#8A877F`: `찜한 항목은 알림 상한·무음 시간과 무관하게 보관되고, 유용/불필요 판정에는 반영되지 않습니다. 읽지 않은 찜이 7일 지나면 조용한 알림으로 한 번 다시 알려드립니다.`

### 6. TabBar — 공통, **찜** 활성

## 데이터 필드 · 설정값

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `folders[]` | {id, name, count} | `나중에 읽기`, 9 | 사용자 정의 폴더 |
| `saved_total` | int | 23 | `전체` 칩 개수 |
| `unread_count` | int | 7 | `안 읽음 7` |
| `sort` | enum | `saved_desc` | `최근 찜한 순` |
| saved.`alert_id` | string | – | 원본 알림 참조 |
| saved.`source_name` | string | `GitHub Releases` | |
| saved.`saved_at` (또는 알림 날짜) | date | 2026-09-14 | 표시 `9월 14일` (메타 날짜가 찜 시각인지 알림 시각인지 확인 필요) |
| saved.`folder_id` / `folder_name` | string | `적용해보기` | 배지 |
| saved.`title` | string | `[릴리즈] MCP Python SDK …` | |
| saved.`memo` | string? | `trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인` | 없으면 Memo 박스 숨김 |
| saved.`url` | URL | – | 원문 |
| saved.`is_read` | bool | – | 안 읽음 카운트/강조 |
| `resurface_unread_after_days` | int | 7 | 읽지 않은 찜 재알림 (조용한 알림, 1회) — 현재 고정값, 설정 UI 없음 |

## 규칙 (안내문에서 도출)
- 찜은 하루 push 상한·무음 시간에 영향받지 않음.
- 찜은 유용/불필요 학습 신호로 쓰지 않음.
- 읽지 않은 찜 7일 경과 시 `조용히` 모드 재알림 1회.
