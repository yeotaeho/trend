# 11 찜

- 원본 HTML: [`../source/Saved.dc.html`](../source/Saved.dc.html) (`gen.py.txt` `fchip()` `saved_card()`) · Figma node `23:39` · 프레임 390 × 1360 (세로 스크롤) · 스크린샷 [11-saved.png](11-saved.png) (HTML 렌더, 대체 폰트라 높이가 실제보다 길다)
- 하단 탭: **찜** 활성 (아이콘은 윤곽선 `bookmark` 그대로, 색만 accent)

## 목적

찜한 알림을 폴더별로 보관·관리한다. 메모, 폴더 이동, 찜 해제, 원문 열기. 찜은 알림 상한·피드백 학습과 분리된 개인 보관함이다.

## 레이아웃 (위 → 아래)

### 1. 루트 TopBar — `margin-top 44`, 높이 56, `px 20`
좌 `찜` 22/700. 우 `search` 22 + `dots` 22 (gap 14). 더보기는 폴더 관리·정렬 (디자인 없음).

### 2. 폴더 칩 행 — `padding 4px 16px 12px`, gap 8, `overflow: hidden` (앱은 가로 스크롤)
FolderChip ([tokens FolderChip](../tokens.md#folderchip-fchip-11-전용)). 단일 선택.

| 칩 | 개수 | 샘플 |
|---|---|---|
| `전체` | 23 | 선택 |
| `나중에 읽기` | 9 | |
| `적용해보기` | 6 | |
| `ClickMe 참고` | 5 | |
| `+` | – | 새 폴더 |

### 3. 정렬 줄 — `padding 0 20px 8px`, space-between, 12 tertiary
좌 `최근 찜한 순` (정렬 시트), 우 `안 읽음 7` (안 읽은 찜만 보기 토글). 둘 다 400 tertiary 다.

### 4. SavedCard 목록 — 세로 flex gap 12
SavedCard — Card (padding 16, **gap 10**, 1px `#E5E2DB`).
1. 메타 행 (space-between)
   - 좌 (flex gap 8, 12 tertiary) — `{소스명} · {M월 d일}` + 안 읽음이면 점 6×6 radius 3 `#2D5BE3`.
   - 우 — 폴더 배지 11/600, `padding 3px 8px`, radius 6, `#EAF0FC` / `#4A6FD0`.
2. 제목 16 / 600 / lh 1.4.
3. (메모가 있을 때) 메모 박스 — flex gap 8, `padding 8px 10px`, `#F0EEE9`, radius 8. 라벨 `메모` 11/600 tertiary (줄어들지 않음), 본문 12 / lh 1.5 `#55524B`.
4. 액션 행 (flex gap 8) — OpenButton `external` + `원문`, OpenButton `folder` + `폴더`, 빈 공간(flex-grow), BookmarkButton 찜됨(`bookmarkfill` `#2D5BE3`).
- 카드 탭 → 07. `폴더` → 폴더 이동 시트, 찜 버튼 → 해제 + 되돌리기 스낵바, 메모 탭 → 편집 (모두 디자인 없음).

| # | 메타 | 안 읽음 | 폴더 | 제목 | 메모 |
|---|---|---|---|---|---|
| 1 | GitHub Releases · 9월 14일 | – | 적용해보기 | [릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 | trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인 |
| 2 | arXiv cs.CL · 9월 12일 | ● | 나중에 읽기 | BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배 | – |
| 3 | Anthropic · 9월 9일 | ● | ClickMe 참고 | [모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일 | 페르소나 시뮬레이터 배치 비용 재계산 |
| 4 | youtube:jocoding · 9월 8일 | – | 나중에 읽기 | Claude Code 서브에이전트로 1인 개발 팀 만들기 | – |

### 5. SectionLabel `찜 안내` + 안내 카드 (`padding 12px 16px`)
12 / lh 1.6 / tertiary — `찜한 항목은 알림 상한·무음 시간과 무관하게 보관되고, 유용/불필요 판정에는 반영되지 않습니다. 읽지 않은 찜이 7일 지나면 조용한 알림으로 한 번 다시 알려드립니다.`

### 6. TabBar — **찜** 활성

## 데이터 필드 · 설정값

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `folders[]` | {id, name, count} | `나중에 읽기` 9 | |
| `total_count` / `unread_count` | int | 23 / 7 | |
| `sort` | enum | `saved_desc` | `최근 찜한 순` |
| saved.`alert_id` / `source_name` / `title` / `url` | – | – | |
| saved.`saved_at` | datetime | 2026-09-14 | 메타 날짜 (계약 3.3) |
| saved.`folder` | {id, name}? | `적용해보기` | null 이면 배지 숨김 |
| saved.`memo` | string? | – | null 이면 박스 숨김 |
| saved.`is_read` | bool | false | 안 읽음 점 |
| `resurface_unread_after_days` | int | 7 | 정적 |

## 규칙 (안내문에서)
- 찜은 하루 push 상한·무음 시간과 무관하다.
- 찜은 유용/불필요 학습 신호로 쓰지 않는다.
- 읽지 않은 찜은 7일 뒤 조용한 알림으로 한 번 다시 알린다.

## Figma 와 다른 점 (HTML 우선)
이전 명세는 Figma 레이어 메타데이터만으로 썼다. HTML 로 확정한 값은 아래와 같다.
- 선택 칩은 검정 배경·흰 글자·`#1C1B19` 테두리, 개수는 12 (`#B8B4AB` / `#8A877F`).
- `안 읽음 7` 은 12 / 400 tertiary 다 (이전 명세 SemiBold accent). `최근 찜한 순` 도 tertiary 다 (이전 명세 secondary).
- 카드 테두리는 1px `#E5E2DB`, 카드 gap 10 이다. 안 읽음은 메타 행의 파란 점으로 표시한다.
- 폴더 배지는 `#EAF0FC` / `#4A6FD0` 다 (이전 명세 중립 회색).
- 메모 박스는 `#F0EEE9` 이고 라벨 11/600, 본문 12 `#55524B` 다 (이전 명세 `#F5F4F0`, 12 · 13 primary).
- 폴더 버튼은 OpenButton 과 같은 스타일이고 폭은 내용에 맞춘다 (Figma 76 고정).
- 탭 아이콘은 활성이어도 윤곽선 `bookmark` 다 (Figma `bookmarkFill`).
