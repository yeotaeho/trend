# 디자인 토큰 · 공통 컴포넌트

출처는 `source/gen.py.txt` 의 공통 CSS·조각 함수(`icon` `topbar` `tabbar` `section` `card` `row` `tog` `chip` `badge` `fb_buttons` 등)와 그 출력인 `source/*.dc.html` 이다. 두 파일은 픽셀 기준의 진실이며, Figma(`xbgeR2ik7vN0BXtBxFPfI5`)는 이 HTML 을 옮겨 그린 것이다. 값이 Figma 와 다르면 **HTML 이 이긴다**. 다른 점은 각 절의 "Figma 와 다른 점" 에 적었다.
예외는 프레임 높이 하나다. `preview/*.png` 와 `.dc.html` 아트보드 높이는 대체 폰트로 렌더링되어 실제보다 길다. 스크롤 화면의 전체 높이는 Figma 프레임 높이(IBM Plex Sans KR 로 잰 값)를 따른다.

기준 폭 **390**. 화면 루트는 `display: flex; flex-direction: column; overflow: hidden`, 배경 `#F5F4F0`. Figma 변수(Variables)는 정의되어 있지 않다.

## 색상

| 토큰 | Hex | 용도 (gen.py.txt 기준) |
|---|---|---|
| `bg/canvas` | `#F5F4F0` | 화면 배경 |
| `bg/surface` | `#FFFFFF` | 카드, 탭바, 미선택 칩·버튼, 세그먼트 선택 조각, 토글 knob |
| `bg/subtle` | `#F0EEE9` | 소스 아이콘 타일, `조용히` 배지, `exclude`·`중복` 탈락 태그, 찜 메모 박스 |
| `bg/segmented-track` | `#EBE8E1` | 세그먼트 트랙 |
| `bg/track` | `#EFECE6` | 점수·카테고리 바 트랙, 카드 안 행 구분선 |
| `border/card` | `#E5E2DB` | 카드 테두리, 탭바 윗선 |
| `border/control` | `#D9D5CC` | 칩·버튼 테두리, 빈 체크 원(1.5px) |
| `control/off` | `#D6D2C9` | 토글 OFF 트랙, GateBar `중복` |
| `icon/chevron` | `#B8B4AB` | 행·그룹의 chevron, 선택된 택소노미 셀 slug, 선택 폴더 칩의 개수, 점수 바 `kind` 0 채움, GateBar `exclude` |
| `text/primary` | `#1C1B19` | 제목·본문, 선택 칩·버튼 배경(inverse), 아바타 배경 |
| `text/secondary` | `#55524B` | 요약, 행 값, 미선택 칩 글자, 소스 아이콘, 걸러짐 안내 문구 |
| `text/muted` | `#6B6862` | 07 근거 문장, `조용히` 배지 글자, `exclude`·`중복` 탈락 태그 글자 |
| `text/tertiary` | `#8A877F` | 메타, 섹션 라벨, 보조 줄, 캡션, 비활성 탭 |
| `text/inverse` | `#FFFFFF` | 어두운 배경 위 글자 |
| `accent/primary` | `#2D5BE3` | 링크, `#태그`, 활성 탭, 토글 ON, 체크 원, 점수·유용 바, 찜 채움, 안 읽음 점, `즉시` 배지 글자, `점수 탈락` 태그 글자, GateBar `점수` |
| `accent/primary-soft` | `#E8EEFC` | `즉시` 배지 배경, `점수 탈락` 태그 배경 |
| `accent/info` | `#4A6FD0` | `선별 탈락` 태그 글자, 찜 폴더 배지 글자 |
| `accent/info-soft` | `#EAF0FC` | `선별 탈락` 태그 배경, 찜 폴더 배지 배경 |
| `accent/primary-muted` | `#9FB4EA` | GateBar `선별` |
| `accent/warn` | `#B5651D` | 실험 헤더·배지 글자, 음수 가중치, 감점, 경계 라벨, 불필요 아이콘, `판정 탈락` 태그 글자, GateBar `판정` |
| `accent/warn-soft` | `#FDF1E2` | `실험` 배지 배경, `판정 탈락` 태그 배경 |
| `accent/warn-muted` | `#E0A373` | 프로필 카테고리 바 👎 구간 |
| `accent/feed` | `#3D7A4A` | `피드만` 배지 글자 |
| `accent/feed-soft` | `#EEF5EE` | `피드만` 배지 배경 |
| `status/error` | `#C2410C` | 소스 오류 상태 줄 |
| `link/hover` | `#1F45B8` | 웹 링크 hover (앱에서는 쓰지 않음) |
| `gate/exclude` | `#B8B4AB` | GateBar exclude |
| `gate/dedup` | `#D6D2C9` | GateBar 중복 |
| `gate/screening` | `#9FB4EA` | GateBar 선별 |
| `gate/score` | `#2D5BE3` | GateBar 점수 |
| `gate/judgment` | `#B5651D` | GateBar 판정 |

다크 모드 디자인은 없다.

Figma 와 다른 점 (HTML 우선).
- 토글 OFF 트랙은 `#D6D2C9` 다 (Figma 추출본은 `#D9D5CC`).
- `#6B6862` · `#4A6FD0` · `#EAF0FC` · `#EEF5EE` · `#3D7A4A` 는 이전 추출본에 없던 값이다.

## 타이포그래피

폰트는 **IBM Plex Sans KR** (Google Fonts, 웨이트 400·500·600·700). 대체 스택은 `Apple SD Gothic Neo, Malgun Gothic, system-ui`. 코드·slug·수치 일부는 `ui-monospace, Menlo, monospace` (아래 `mono` 표시). 전역 `-webkit-font-smoothing: antialiased`.

line-height 열의 `normal` 은 HTML 이 값을 지정하지 않았다는 뜻이다. Figma 에서 IBM Plex Sans KR 의 normal 은 약 1.4 (18px → 25, 12px → 17)로 재어졌으므로 Flutter 에서는 `height: 1.4` 로 고정한다.

| 스타일 | 크기 | 웨이트 | line-height | 색 | 사용처 |
|---|---|---|---|---|---|
| `title/root` | 22 | 700 | normal | primary | 탭 루트 제목 (`오늘` `내 프로필` `찜`) |
| `title/sub` | 18 | 600 | normal | primary | 뒤로가기 헤더 제목 (`관심사` `알림 설정` …) |
| `title/detail` | 17 | 700 | 1.4 | primary | 07 알림 요약 카드 제목 |
| `title/card` | 16 | 600 | 1.4 | primary | 피드·찜 카드 제목 |
| `stat/value-lg` | 24 | 700 | normal | primary | 08 Stat 값 |
| `stat/value` | 22 | 700 | normal | primary | 06 Stat 값 (접미 `/ 10` `건` 은 13/500 tertiary) |
| `count` | 16 | 700 | normal | primary | DropGroup 건수 |
| `avatar` | 16 | 700 | normal | inverse | 아바타 이니셜 |
| `row/title` | 15 | 500 | normal | primary | 설정 행 제목 |
| `summary/title` | 15 | 600 | normal | primary | 걸러짐 요약 헤더 (`오늘 걸러짐 571`), 프로필 이름 |
| `body/md` | 14 | 400 | normal | secondary | 설정 행 값 |
| `body/profile` | 14 | 400 | 1.6 | primary | 04 자기소개 문장 |
| `label/strong` | 14 | 600 | normal | primary | 택소노미 셀 제목, 소스 ID(`mono`), DropGroup 이름, 주간 리포트 제목, 헤더 `저장`(accent) |
| `label/group` | 14 | 500 | normal | primary | 05 중요도 그룹 라벨 |
| `body/summary` | 13.5 | 400 | 1.55 | secondary | 카드 요약 |
| `body/dropped` | 13.5 | 500 | 1.4 | primary | 걸러진 항목 제목 |
| `label/button` | 13 | 600 | normal | primary / secondary | 원문·폴더·유용·불필요 버튼 |
| `label/chip` | 13 | 500 | normal | secondary / inverse | 칩 |
| `label/segment` | 13 | 600 | normal | primary(선택) / tertiary | 세그먼트 (선택·미선택 모두 600) |
| `body/sm` | 13 | 400 | normal | primary / secondary | 07 최근 판정 제목, 08 학습된 취향 행 |
| `caption/md` | 12 | 400 | normal | tertiary | 메타, 행 보조 줄, 요약 줄, `#태그`(accent) |
| `caption/note` | 12 | 400 | 1.5 / 1.55 / 1.6 | secondary / muted / tertiary | 걸러짐 안내(1.5, secondary), 07 근거(1.55, muted), 안내 카드(1.6, tertiary) |
| `section/label` | 12 | 600 | normal | tertiary | SectionLabel, 자간 `0.04em` |
| `caption/strong` | 12 | 600 | normal | accent / warn | `걸러짐 571건 보기 ›`, 실험 헤더, 경계 라벨 |
| `caption/sm` | 11 | 400 | normal | tertiary | Stat 라벨·캡션, 소스 상태 줄, 범례, 그룹 요약, 탈락 사유, 최근 판정 시간 |
| `caption/sm-strong` | 11 | 600 | normal | error / tertiary | 소스 오류 상태 줄, 메모 라벨 |
| `slug` | 11 | 400 | normal | tertiary / chevron | 택소노미 slug (`mono`) |
| `badge` | 11 | 600 | normal | 배지별 | Badge, 탈락 태그, 폴더 배지 |
| `tab/label` | 11 | 600(활성) / 500 | normal | accent / tertiary | 탭바 |

Figma 와 다른 점 (HTML 우선).
- `title/sub` 는 600 이다 (Figma 추출본은 Bold).
- 07 제목은 17/700/1.4 다 (이전 추출본 18 · 1.35).
- 08 Stat 값은 24 다 (추출본 22). 06 Stat 값만 22 다.
- 세그먼트 미선택 라벨도 600 이다 (추출본 Medium).
- 05 중요도 그룹 라벨은 500 이다 (추출본 SemiBold).
- 07 최근 판정 제목은 400 이다 (추출본 Medium).
- 07 판정 버튼 라벨은 13 이다 (추출본 14).
- 폴더 칩 개수는 12 다 (추출본 11).
- 걸러짐 안내 문구는 12 다 (추출본 12.5).
- 섹션 라벨 자간 `0.04em` 은 추출본에 없던 값이다.

## 간격 · 레이아웃

| 토큰 | 값 | 비고 |
|---|---|---|
| 상태바 영역 | 44 | 모든 헤더의 `margin-top: 44px`. Flutter 는 SafeArea 로 대체 |
| 헤더(TopBar) | 높이 56 | 루트 `px 20`, 하위 `px 16`. 상태바 포함 100 |
| 카드 좌우 여백 | 16 | 카드 폭 358 |
| 텍스트 좌우 여백 | 20 | 루트 헤더, SectionLabel, 요약 줄 |
| SectionLabel | `pt 20 / px 20 / pb 8` | |
| 카드 padding | 16 (기본) | 행 목록 카드는 `4px 16px`, 소스 카드 `2px 16px`, 그룹 카드 `6px 16px`, 안내 카드 `12px 16px`, 주간 리포트 `14px 16px`, 06 Stat `12px 14px`, 08 Stat 14 |
| 카드 내부 gap | 12 (기본) | 피드·찜 카드와 걸러짐 요약 10, 행 목록 0, Stat 2 |
| 카드 간 gap | 12 | 걸러진 그룹 목록만 10 |
| 칩·버튼 간 gap | 8 | |
| 칩 행 | `pt 4 / px 16 / pb 12` | 03·11 |
| 요약 줄 | `px 20 / pb 8` | 03·11 |
| 설정 Row | `min-height 52`, `py 10` | 행 사이 1px `#EFECE6` (마지막 행 없음) |
| Stat 카드 | 06 은 gap 12, 08 은 gap 10, 모두 균등 폭 | |
| 탭바 | 높이 80, 셀 `pt 10` | 나머지는 홈 인디케이터 영역 |

Figma 와 다른 점 (HTML 우선).
- 헤더는 44 + 56 = 100 이다 (추출본은 하위 77, 루트 83). 하위 헤더 좌우 여백은 16 이다.
- 설정 Row 는 `min-height 52` 에 `py 10` 이라 보조 줄이 있으면 늘어난다 (추출본 50 / 64 / 45 고정값).
- 08 Stat 간격은 10, 06 은 12 다 (추출본 8).
- 걸러진 그룹 카드 간격은 10 이다 (추출본 12).

## 모서리 반경

| 대상 | 값 |
|---|---|
| 카드, Stat 카드 | 14 |
| 택소노미 셀 | 12 |
| 버튼(원문·폴더·찜·유용·불필요), 아이콘 타일, 세그먼트 트랙 | 10 |
| 세그먼트 선택 조각, 복원 버튼, 메모 박스 | 8 |
| 배지, 탈락 태그, 폴더 배지 | 6 |
| 칩 | 20 |
| 토글 트랙 / knob | 13 / 11 |
| 체크 원 | 9 (18×18) |
| 점수 바 / 카테고리·Gate 바 | 4 / 5 |
| 범례 점 | 3 (8×8, 둥근 사각형) |
| 안 읽음 점 | 3 (6×6) |
| 아바타 | 22 (44×44 원) |

Figma 와 다른 점 (HTML 우선). 택소노미 셀은 12 다 (이전 추출본 10). 범례 점은 원이 아니라 반경 3 의 둥근 사각형이다.

## 그림자

- 카드·버튼·칩·토글 knob 은 그림자가 없다. 1px 테두리로만 구분한다.
- 세그먼트 선택 조각만 `0 1px 2px rgba(0,0,0,0.08)`.

## 아이콘

모든 아이콘은 `gen.py.txt` `icon()` 이 만드는 인라인 SVG 다. Lucide 와 모양이 다르므로 **`flutter_svg` 로 아래 경로를 그대로 그린다** (`lib/core/icons.dart` 에 문자열 상수로 둔다).

공통 래퍼는 아래와 같다. `{size}` 는 표시 크기(viewBox 는 항상 24), `{color}` 는 선 색이다.

```svg
<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}"
     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>
```

선 굵기는 표시 크기와 무관하게 viewBox 기준 1.8 이다 (22px 이면 약 1.65px, 16px 이면 1.2px). 채움은 `bookmarkfill` 만 있다 (`fill="currentColor"` 이며 `currentColor` = `{color}`). `github`·`discord` 도 채움 없이 윤곽선만 그린다.

| 이름 | SVG 내용 (viewBox 0 0 24 24) | 크기 · 색 | 사용처 |
|---|---|---|---|
| `back` | `<path d="M15 5l-7 7 7 7"/>` | 20 · primary | 하위 헤더 |
| `bell` | `<path d="M6 8a6 6 0 0 1 12 0v5l2 3H4l2-3z"/><path d="M10 19a2 2 0 0 0 4 0"/>` | 22 · primary | 03 헤더 |
| `home` | `<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>` | 22 · 탭색 | 탭 `피드` |
| `user` | `<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>` | 22 · 탭색 | 탭 `내 프로필` |
| `sliders` | `<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>` | 22 · 탭색 | 탭 `설정` |
| `thumbup` | `<path d="M7 11v9H3v-9zM7 11l4-8a2 2 0 0 1 2 2v4h5a2 2 0 0 1 2 2l-1 7a2 2 0 0 1-2 2H7"/>` | 16 (버튼·최근 판정 `#2D5BE3`) · 15 (복원 `#55524B`) | 유용, 복원 |
| `thumbdown` | `<path d="M17 13V4h4v9zM17 13l-4 8a2 2 0 0 1-2-2v-4H6a2 2 0 0 1-2-2l1-7a2 2 0 0 1 2-2h10"/>` | 16 (최근 판정 `#B5651D`) | 불필요 |
| `external` | `<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v6H4V6h6"/>` | 16 (원문 버튼) · 22 (07 헤더) · primary | 원문 |
| `chev` | `<path d="M9 5l7 7-7 7"/>` | 16 (행·그룹) · 18 (주간 리포트) · `#B8B4AB` | 이동, 접힘 |
| `chevd` | `<path d="M5 9l7 7 7-7"/>` | 16 · `#B8B4AB` | 펼침 |
| `plus` | `<path d="M12 5v14M5 12h14"/>` | 22 · primary | 06 헤더 |
| `flask` | `<path d="M9 3h6M10 3v6L4 20h16l-6-11V3"/>` | 14 · `#B5651D` | 실험 헤더 |
| `check` | `<path d="M5 12l5 5 9-10"/>` | 12 · 흰색 | 택소노미 체크 원 |
| `search` | `<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>` | 22 · primary | 03·09·10·11 헤더 |
| `github` | `<path d="M12 2a10 10 0 0 0-3 19.5c.5 0 .7-.2.7-.5v-2c-2.8.6-3.4-1.2-3.4-1.2-.4-1.1-1-1.4-1-1.4-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5a4 4 0 0 1 1-2.7 3.7 3.7 0 0 1 .1-2.7s.8-.3 2.8 1a9.5 9.5 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7a4 4 0 0 1 1 2.7c0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8v2.7c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/>` | 18 · `#55524B` | GitHub 소스 |
| `discord` | `<path d="M8 17c-2.5 0-4-1.5-5-3 0-3 1-6 2.5-8.5C7 5 8.5 4.5 10 4.5l.5 1.5a12 12 0 0 1 3 0l.5-1.5c1.5 0 3 .5 4.5 1 1.5 2.5 2.5 5.5 2.5 8.5-1 1.5-2.5 3-5 3l-1-1.5c-1.5.5-3.5.5-5 0z"/><circle cx="9.5" cy="12" r="1"/><circle cx="14.5" cy="12" r="1"/>` | 20 | 로그인(범위 밖). 채널 표시용 예비 |
| `mail` | `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>` | 20 | 로그인(범위 밖) |
| `rss` | `<path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1.5"/>` | 18 · `#55524B` | RSS 소스 |
| `youtube` | `<rect x="3" y="6" width="18" height="12" rx="3"/><path d="M10 9l5 3-5 3z"/>` | 18 · `#55524B` | YouTube 소스 |
| `clock` | `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>` | – | 정의만 있고 화면에서 안 씀 |
| `trend` | `<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>` | – | 정의만 있고 화면에서 안 씀 |
| `logo` | `<path d="M4 18L10 6l4 8 2-4 4 8"/>` | 26 · 흰색 | 로그인(범위 밖), 앱 아이콘 후보 |
| `bookmark` | `<path d="M6 3h12v18l-6-4-6 4z"/>` | 18 (찜 버튼 `#55524B`) · 22 (탭) | 찜 안 됨, 탭 `찜` |
| `bookmarkfill` | `<path d="M6 3h12v18l-6-4-6 4z" fill="currentColor"/>` | 18 · `#2D5BE3` | 찜됨 |
| `folder` | `<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>` | 16 · primary | 찜 `폴더` 버튼 |
| `dots` | `<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>` | 22 · primary | 11 헤더 |

Figma 와 다른 점 (HTML 우선). 찜 탭이 활성이어도 아이콘은 `bookmark`(윤곽선)이고 색만 `#2D5BE3` 이다 (추출본은 활성 시 `bookmarkFill`). 선 굵기는 1.8 이다 (추출본 1.5–1.75).

## 하단 탭바

높이 80, 흰 배경, 윗선 1px `#E5E2DB`, `margin-top: auto` 로 화면 바닥에 붙는다. 셀 4개 균등 분할, 셀은 세로 `pt 10`, 아이콘 22 + gap 4 + 라벨 11.
활성은 아이콘·라벨 `#2D5BE3`, 라벨 600. 비활성은 `#8A877F`, 500.

| 순서 | 라벨 | 아이콘 | 열리는 화면 |
|---|---|---|---|
| 1 | `피드` | home | [03 피드](screens/03-feed.md) (하위 07·09·10) |
| 2 | `찜` | bookmark | [11 찜](screens/11-saved.md) |
| 3 | `설정` | sliders | 설정 루트 — **디자인 없음**. 하위 [04 관심사](screens/04-interests.md), [05 알림 설정](screens/05-notification-settings.md), [06 수집 소스](screens/06-sources.md) |
| 4 | `내 프로필` | user | [08 내 프로필](screens/08-profile.md) |

하위 화면(04·05·06·09·10)은 탭바를 유지하고 부모 탭을 활성 표시한다. 07 만 탭바가 없다.

## 공통 컴포넌트

### Card (`card()`)
흰 배경, 1px `#E5E2DB`, radius 14, padding 16, 세로 flex gap 12, 좌우 margin 16. 화면마다 padding·gap 을 바꿔 쓴다 (간격 표 참조).

### SectionLabel (`section()`)
12 / 600 / `#8A877F` / 자간 0.04em, `padding: 20px 20px 8px`. 텍스트 한 줄뿐이며 우측 요소가 없다 (`소스별 · 많은 순` 처럼 한 문자열로 쓴다).

### TopBar
- 루트 (`오늘` `내 프로필` `찜`) — `margin-top 44`, 높이 56, `px 20`, space-between. 좌 `title/root`, 우 아이콘 22 두 개 gap 14 (또는 `최근 14일` 13 tertiary).
- 하위 (`topbar()`) — `margin-top 44`, 높이 56, `px 16`, space-between. 좌 `back` 20 + gap 8 + `title/sub`. 우 슬롯 gap 8 (아이콘 22 또는 `저장` 14/600 accent).

### Chip (`chip()`)
`padding 9px 14px`, radius 20, 13/500.
- 선택 — 배경 `#1C1B19`, 글자 흰색, **테두리 없음**.
- 미선택 — 배경 흰색, 1px `#D9D5CC`, 글자 `#55524B`.
- 선택 칩은 테두리가 없어 미선택보다 2px 낮다. Flutter 에서는 선택 칩에 같은 색 1px 테두리를 둬서 높이를 맞춘다.

### FolderChip (`fchip()`, 11 전용)
Chip 과 같지만 선택도 1px 테두리(`#1C1B19`)가 있고, `white-space: nowrap`, 라벨 뒤 gap 6 으로 개수(12, 선택 `#B8B4AB` / 미선택 `#8A877F`). `+` 칩은 개수 없음.

### Badge (`badge()`)
11 / 600, `padding 3px 8px`, radius 6.

| 종류 | 배경 | 글자 | 라벨 |
|---|---|---|---|
| `push` (즉시) | `#E8EEFC` | `#2D5BE3` | `즉시` |
| `silent` (조용히) | `#F0EEE9` | `#6B6862` | `조용히` |
| `explore` (실험) | `#FDF1E2` | `#B5651D` | `실험` |
| `feed` (피드만) | `#EEF5EE` | `#3D7A4A` | `피드만` |

### 탈락 태그 (`stage_tag()`, 09·10)
Badge 와 같은 치수, `flex-shrink: 0`, 라벨 `{관문} 탈락`.

| 관문 | 배경 | 글자 |
|---|---|---|
| `exclude` · `중복` | `#F0EEE9` | `#6B6862` |
| `선별` | `#EAF0FC` | `#4A6FD0` |
| `점수` | `#E8EEFC` | `#2D5BE3` |
| `판정` | `#FDF1E2` | `#B5651D` |

### Toggle (`tog()`)
44×26, radius 13. knob 22×22 흰색 radius 11, `top 2`, ON `left 22` / OFF `left 2`. 트랙 ON `#2D5BE3`, OFF `#D6D2C9`. 그림자 없음.

### Row (`row()`)
space-between, `min-height 52`, `padding 10px 0`, 마지막 행 외 아래 1px `#EFECE6`.
- 좌 — 제목 15/500 primary, 보조 줄(있으면) 12 tertiary, `margin-top 2`.
- 우 — 토글, 또는 값(14 secondary) + gap 6 + `chev` 16 `#B8B4AB`.

### Segmented (`seg()`)
트랙 `#EBE8E1`, radius 10, padding 3, 조각 간 gap 2. 조각은 균등 폭, `padding 8px 0`, radius 8, 13/600. 선택은 흰 배경·`#1C1B19`·그림자 `0 1px 2px rgba(0,0,0,0.08)`, 미선택은 투명·`#8A877F`.

### Buttons
- **OpenButton** (`원문`, 11 의 `폴더`) — 높이 40, `px 14`, radius 10, 흰 배경, 1px `#D9D5CC`, 아이콘 16 + gap 6 + 13/600 primary.
- **BookmarkButton** (`bm_btn()`) — 40×40, radius 10, 같은 테두리, `bookmark` 18 `#55524B` / `bookmarkfill` 18 `#2D5BE3`.
- **FeedbackButton** (`fb_buttons()`) — 두 개가 남은 폭을 나눈다 (gap 8). 높이 40, radius 10, 1px 테두리, 아이콘 16 + gap 6 + 13/600. 선택은 배경·테두리 `#1C1B19`·글자 흰색, 미선택은 흰 배경·`#D9D5CC`·`#55524B`. 라벨 `유용` / `불필요`.
- **RestoreButton** (09·10) — 32×32, radius 8, 흰 배경, 1px `#D9D5CC`, `thumbup` 15 `#55524B`. 선택 상태 디자인은 없다 (FeedbackButton 선택 색을 쓴다).
- **TextButton** (04 `저장`) — 14/600 `#2D5BE3`.

### FeedCard
[03 피드](screens/03-feed.md) 참조. 카드 gap 10.

### StatCard
- 06 — Card(`12px 14px`, gap 2, 좌우 margin 0, flex-grow). 라벨 11 tertiary, 값 22/700 + 접미 13/500 tertiary. 캡션 없음.
- 08 (`stat()`) — 흰 배경, 1px `#E5E2DB`, radius 14, padding 14, gap 2, flex-grow. 라벨 11 tertiary, 값 24/700, 캡션 11 tertiary.

### Bars
- **ScoreBar** (07, `bar()`) — 행 gap 10, 12px. 라벨 폭 56 tertiary `mono`, 트랙(flex-grow) 높이 8 radius 4 `#EFECE6`, 채움 radius 4 (`#2D5BE3`, 0 인 `kind` 는 `#B8B4AB` 폭 0), 값 폭 44 우정렬 secondary `mono`. 채움 폭은 **값 ÷ 0.5** 비율이다 (0.10 → 20%, 0.25 → 50%).
- **StackedBar** (08, `hbar()`) — 행 gap 10, 12px. 라벨 폭 92 secondary, 트랙(flex-grow) 높이 10 radius 5 `#EFECE6` overflow hidden, 👍 구간 `#2D5BE3` + 👎 구간 `#E0A373` (각각 트랙 폭 대비 %), 합계 폭 28 우정렬 tertiary `mono`.
- **GateBar** (09·10, `gate_bar()`) — 높이 10 radius 5 overflow hidden, 5구간 폭 = 건수 ÷ 합계. 아래 범례는 gap 10 wrap, 항목은 8×8 radius 3 점 + gap 4 + `{라벨} {건수}` 11 tertiary.

### DropGroup / DroppedItem
[09](screens/09-filtered-by-source.md) 참조.

### Avatar
44×44, radius 22, `#1C1B19`, 이니셜 16/700 흰색.
