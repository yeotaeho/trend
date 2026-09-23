# 디자인 토큰 · 공통 컴포넌트

출처: Figma `xbgeR2ik7vN0BXtBxFPfI5` (섹션 "기술 파악 · 모바일 앱 v0.1"). Figma 변수(Variables)는 **정의되어 있지 않음**(`get_variable_defs` 결과 비어 있음) — 아래 값은 화면 3의 디자인 코드에서 직접 추출한 값과 스크린샷 픽셀 샘플링 값이다. "추정"이 붙은 값은 레이어 크기에서 역산한 것.

기준 프레임: **390 × 844** (iPhone 14/15 논리 해상도). 스크롤 화면은 세로로 더 김.

## 색상

| 토큰 | Hex | 용도 |
|---|---|---|
| `bg/canvas` | `#F5F4F0` | 화면 배경 (따뜻한 오프화이트) |
| `bg/surface` | `#FFFFFF` | 카드, 탭바, 미선택 칩/버튼 |
| `bg/subtle` | `#F0EEE9` | 아이콘 타일(소스 아이콘 배경), 중립 배지 |
| `bg/segmented-track` | `#EBE8E1` | 세그먼트 컨트롤 트랙 |
| `bg/track` | `#EFECE6` | 진행/점수 바 트랙, 카드 내부 행 구분선 |
| `border/card` | `#E5E2DB` | 카드 테두리, 탭바 상단 선 |
| `border/control` | `#D9D5CC` | 칩·버튼 테두리, 토글 OFF 트랙, 빈 체크 원 |
| `text/primary` | `#1C1B19` | 제목·본문 강조, 선택 칩/버튼 배경(inverse), 아바타 배경 |
| `text/secondary` | `#55524B` | 요약 본문, 미선택 칩 글자 |
| `text/tertiary` | `#8A877F` | 메타(소스·시간), 섹션 라벨, 캡션, 비활성 탭 |
| `text/inverse` | `#FFFFFF` | 어두운 배경 위 글자 |
| `accent/primary` | `#2D5BE3` | 링크, 태그, 활성 탭, 토글 ON, 체크, 점수 바, `즉시`·관문 배지 글자 |
| `accent/primary-soft` | `#E8EEFC` | `즉시` 배지 / 관문 배지 배경 |
| `accent/primary-muted` | `#9FB4EA` | GateBar "선별" 구간 |
| `accent/warn` | `#B5651D` | 실험·경계, 음수 가중치, 감점, 불필요 아이콘, GateBar "판정" |
| `accent/warn-soft` | `#FDF1E2` | `실험` 배지 배경 |
| `accent/warn-muted` | `#E0A373` | 프로필 카테고리 바 "불필요" 구간 |
| `status/error` | `#C2410C` | 소스 오류 상태 (`실패 5회 · 미러 확인 필요`) |
| `gate/exclude` | `#B8B4AB` | GateBar exclude |
| `gate/dedup` | `#D6D2C9` | GateBar 중복 |
| `gate/screening` | `#9FB4EA` | GateBar 선별 |
| `gate/score` | `#2D5BE3` | GateBar 점수 |
| `gate/judgment` | `#B5651D` | GateBar 판정 |

다크 모드: 디자인 없음.

## 타이포그래피

폰트: **IBM Plex Sans KR** (Google Fonts, `google_fonts` 패키지 또는 번들 에셋). 웨이트: Regular 400 / Medium 500 / SemiBold 600 / Bold 700. 숫자 강조도 같은 폰트.

| 스타일 | 크기 | 웨이트 | line-height | 색 | 사용처 |
|---|---|---|---|---|---|
| `title/tab-root` | 22 | Bold | 1.4 | primary | 탭 루트 화면 제목 (`오늘`, `내 프로필`, `찜`) |
| `title/sub` | 18 | Bold | 1.4 (추정) | primary | 뒤로가기 헤더 제목 (`관심사`, `알림 설정` …) |
| `stat/value` | 22 | Bold | 1.2 (추정) | primary | Stat 카드 값 (`612 건`, `64%`) |
| `card/title` | 16 | SemiBold | 1.4 | primary | 피드/찜 카드 제목 |
| `detail/title` | 18 | SemiBold~Bold | 1.35 (추정) | primary | 07 상세 카드 제목 |
| `count/lg` | 16 | Bold | 1.4 (추정) | primary | DropGroup 건수 |
| `row/title` | 15 | Medium | 1.4 (추정) | primary | 설정 행 제목 |
| `body/md` | 14 | Regular/SemiBold | 1.4 | primary | 설정 값, 소스 ID(SemiBold), 택소노미 셀 제목(SemiBold) |
| `body/summary` | 13.5 | Regular | 1.55 | secondary | 카드 요약 |
| `label/button` | 13 | SemiBold | 1.4 | primary / secondary | 버튼 라벨 |
| `label/chip` | 13 | Medium | 1.2 | secondary / inverse | 칩 |
| `caption/md` | 12 | Regular | 1.4 | tertiary | 메타, 행 보조 텍스트, 태그(accent) |
| `section/label` | 12 | SemiBold | 1.4 | tertiary | SectionLabel |
| `caption/sm` | 11 | Regular | 1.4 | tertiary | Stat 라벨·캡션, 소스 상태, 범례 |
| `badge` | 11 | SemiBold | 1.3 | 배지별 | Badge |
| `tab/label` | 11 | SemiBold(활성) / Medium | 1.4 | accent / tertiary | 탭바 |
| `slug` | 10–11 | Regular | 14px | tertiary | 택소노미 slug |

## 간격 · 레이아웃

| 토큰 | 값 | 비고 |
|---|---|---|
| 화면 좌우 여백 (카드) | 16 | CardWrap `px 16` → 카드 폭 358 |
| 화면 좌우 여백 (텍스트) | 20 | TopBar, SectionLabel, 요약 줄 |
| TopBar | `pt 44 / pb 8`, 높이 77 (루트 83) | 44 = 상태바 영역. Flutter에선 SafeArea + 상단 8 |
| SectionLabel | 높이 45: `pt 20 / pb 8`, 텍스트 17 | |
| 카드 padding | 16 | |
| 카드 내부 세로 gap | 10 | FeedCard |
| 카드 간 gap | 12 | |
| 칩 간 gap | 8 | |
| 버튼 간 gap | 8 | |
| 설정 Row 높이 | 50 (단일 줄) / 64 (보조 줄) / 45 (값형) | 행 사이 1px 구분선 `#EFECE6` |
| Stat 카드 | 3열 동일 폭, gap 8, 높이 88 | |
| 스크롤 하단 여백 | 탭바 위 약 34 | |

## 모서리 반경

| 토큰 | 값 |
|---|---|
| 카드 | 14 |
| 버튼 (OpenButton/Feedback/IconButton) | 10 |
| 택소노미 셀, 아이콘 타일, 세그먼트 트랙 | 10 |
| 세그먼트 선택 조각, RestoreButton, Memo | 8 |
| 배지 | 6 |
| 칩 | 20 (pill) |
| 토글 | 13 (완전 pill) |
| 바(점수/카테고리/Gate) | 높이의 절반 (4 / 5) |

## 그림자

- 카드·버튼·칩: **그림자 없음** (1px 테두리로 구분하는 flat 스타일)
- 세그먼트 선택 조각: 아주 약한 그림자 (권장 `0 1 2 rgba(28,27,25,0.08)`)
- 토글 knob: 약한 그림자 (권장 `0 1 2 rgba(0,0,0,0.15)`)

## 아이콘

모두 라인(outline) 스타일, stroke ≈ 1.5–1.75px, `#1C1B19`/`#55524B`/`#8A877F` 단색. Lucide 계열과 모양이 거의 같음 → Flutter `lucide_icons` 패키지 권장. (Figma 레이어명 → Lucide 대응)

| Figma 레이어 | 크기 | Lucide 대응 | 사용처 |
|---|---|---|---|
| `icon/search` | 22 | `search` | 피드/걸러짐/찜 헤더 |
| `icon/bell` | 22 | `bell` | 피드 헤더 |
| `icon/back` | 20 | `chevron-left` | 하위 화면 헤더 |
| `icon/plus` | 22 | `plus` | 수집 소스 추가 |
| `icon/dots` | 22 | `more-horizontal` | 찜 헤더 |
| `icon/external` | 16 / 22 | `external-link` | 원문 버튼, 07 헤더 |
| `icon/bookmark` / `icon/bookmarkFill` | 18 / 22 | `bookmark` (채움 = fill `#2D5BE3`) | 찜 버튼, 찜 탭 |
| `icon/thumbup` / `icon/thumbdown` | 15–16 | `thumbs-up` / `thumbs-down` | 피드백, 복원 |
| `icon/flask` | 14 | `flask-conical` | 실험 헤더 |
| `icon/home` | 22 | `home` | 탭 피드 |
| `icon/sliders` | 22 | `sliders-horizontal` | 탭 설정 |
| `icon/user` | 22 | `user` | 탭 내 프로필 |
| `icon/check` | 12 | `check` | 택소노미 체크 |
| `icon/chev` / `icon/chevd` | 16–18 | `chevron-right` / `chevron-down` | 행 이동, 그룹 접힘/펼침 |
| `icon/rss` | 18 | `rss` | RSS 소스 |
| `icon/github` | 18 | `github` | GitHub 소스 |
| `icon/youtube` | 18 | `youtube` | YouTube 소스 |
| `icon/folder` | 16 | `folder` | 찜 폴더 이동 |

## 하단 탭바

높이 80 (콘텐츠 `pt 10`, 나머지는 홈 인디케이터 영역), 흰 배경, 상단 1px `#E5E2DB`. 탭 4개 균등 분할(각 97.5), 아이콘 22 + gap 4 + 라벨 11.
활성: 아이콘·라벨 `#2D5BE3`, 라벨 SemiBold. 비활성: `#8A877F`, Medium. 찜 탭 활성 시 아이콘이 `bookmarkFill`.

| 순서 | 라벨 | 아이콘 | 열리는 화면 |
|---|---|---|---|
| 1 | `피드` | home | [03 피드](screens/03-feed.md) (하위: 07, 09, 10) |
| 2 | `찜` | bookmark | [11 찜한 알림](screens/11-saved.md) |
| 3 | `설정` | sliders | 설정 루트 — **디자인 없음**. 하위 화면 [04 관심사](screens/04-interests.md), [05 알림 설정](screens/05-notification-settings.md), [06 수집 소스](screens/06-sources.md)로 가는 목록 화면 필요 |
| 4 | `내 프로필` | user | [08 내 프로필](screens/08-profile.md) |

하위 화면(04/05/06/09/10)에서도 탭바는 유지되고 부모 탭이 활성 표시된다(탭별 중첩 Navigator 구조). 07은 탭바 없는 전체 화면 push.

## 공통 컴포넌트

### Card
흰 배경, 1px `#E5E2DB`, radius 14, padding 16, 그림자 없음. `CardWrap`이 좌우 16 여백 제공.

### SectionLabel
좌측 텍스트(SemiBold 12 `#8A877F`), 선택적 우측 보조 텍스트(`많은 순`, Regular 12 `#8A877F`). 컨테이너 높이 45, `px 20 / pt 20 / pb 8`.

### Chip (필터/폴더/키워드)
높이 34–36, `px 14 / py 9`, radius 20, Medium 13.
- 선택: bg `#1C1B19`, border `#1C1B19`, text `#FFFFFF`
- 미선택: bg `#FFFFFF`, border 1px `#D9D5CC`, text `#55524B`
- 폴더 칩은 이름 뒤에 개수(11px) 추가

### Badge
`px 8 / py 3`, radius 6, SemiBold 11 / lh 1.3.
- 즉시·관문(선별/점수 탈락): bg `#E8EEFC` / text `#2D5BE3`
- 실험: bg `#FDF1E2` / text `#B5651D`
- 중립(조용히·폴더명, 권장): bg `#F0EEE9` / text `#55524B`

### Toggle (Switch)
44×26, knob 22 흰색(inset 2). ON 트랙 `#2D5BE3`, OFF 트랙 `#D9D5CC`. Flutter `CupertinoSwitch`에 색 지정하거나 커스텀.

### Toggle Row / Value Row (설정 행)
좌: 제목(Medium 15 primary) + 보조(Regular 12 tertiary). 우: Toggle 또는 값 텍스트(Regular 14 primary) + `chevron-right` 16 tertiary. 행 사이 1px `#EFECE6`, 카드 내부 좌우 16.

### Segmented Control
높이 38, 트랙 `#EBE8E1` radius 10, 내부 padding 3. 선택 조각 흰색 radius 8 + 약한 그림자, 라벨 SemiBold 13 primary; 미선택 라벨 Medium 13 tertiary. 옵션 균등 분할. 사용처: 05 중요도별 강도(즉시/조용히/피드만), 09·10 보기 전환(소스별/종류별/관문별).

### Buttons
- **OpenButton**: 높이 40, `px 14`, 흰 bg, 1px `#D9D5CC`, radius 10, 아이콘 16 + gap 6 + SemiBold 13 primary
- **IconButton**: 40×40, 같은 테두리, 아이콘 18
- **FeedbackButton**: 높이 40, flex, 아이콘 16 + 라벨. 선택 = bg/border `#1C1B19` + 흰 글자, 미선택 = 흰 bg + `#D9D5CC` + `#55524B`
- **RestoreButton**: 32×32, radius 8, 테두리 `#D9D5CC`, thumbs-up 15
- **Text button** (헤더 `저장`): SemiBold 14 `#2D5BE3`

### FeedCard
[03 피드](screens/03-feed.md) 참조: (실험 헤더) → 메타+배지 → 제목 → 요약 → 태그 → 액션 행.

### Stat Card
3열, 높이 88, Card 스타일(padding 14): 라벨 11 secondary / 값 Bold 22 / 캡션 11 tertiary.

### Horizontal Bar
- 점수 분해 바(07): 트랙 206×8 `#EFECE6`, 채움 `#2D5BE3`
- 스택 바(08): 182×10, 유용 `#2D5BE3` + 불필요 `#E0A373`
- GateBar(09/10): 326×10, 5구간 비례 스택 + 8px 원형 범례

### DropGroup / DroppedItem
[09](screens/09-filtered-by-source.md) 참조. 접힘 카드 높이 64, 헤더 탭으로 펼침.

### Avatar
40 원형, bg `#1C1B19`, 이니셜 흰색 SemiBold.
