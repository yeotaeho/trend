# 05 알림 설정

- 원본 HTML: [`../source/NotifySettings.dc.html`](../source/NotifySettings.dc.html) · Figma node `5:193` · 프레임 390 × 1120 (세로 스크롤) · 스크린샷 [05-notification-settings.png](05-notification-settings.png) (Figma)
- 하단 탭: **설정** 활성 (설정 하위)

## 목적

전달 채널, 알림 피로 방지(하루 상한·무음 시간·같은 이슈 하루 1건), importance 별 전달 강도, 탐색 슬롯을 설정한다.

## 레이아웃 (위 → 아래)

### 1. 하위 TopBar
`back` 20 + `알림 설정` (18/600). 우측 버튼 없음 → **변경 즉시 저장**.

### 2. SectionLabel `채널` + 카드 (`padding 4px 16px`, gap 0, Row 3개)

| 행 | 보조 줄 | 토글 샘플 |
|---|---|---|
| `앱 푸시 (FCM)` | – | ON |
| `Discord 채널` | `#trend-alerts · 👍/👎 리액션 동기화` | ON |
| `Telegram 봇` | `연결 안 됨` | OFF |

### 3. SectionLabel `알림 피로 방지` + 카드 (`padding 4px 16px`, gap 0)

| 행 | 보조 줄 | 우측 | 인터랙션 |
|---|---|---|---|
| `하루 push 상한` | – | `15건` + chev | 숫자 피커 (디자인 없음, 1–50) |
| `무음 시간` | `Asia/Seoul · 무음 중엔 피드에만 쌓입니다` | `23:00 – 08:00` + chev | 시작·종료 시 피커 (디자인 없음) |
| `같은 이슈 하루 1건` | `버전 형제 릴리즈는 제목에 병기` | Toggle ON | 같은 클러스터는 하루 1건만 보내고 형제 버전을 첫 알림 제목에 병기 |

값 텍스트는 14 `#55524B`, chev 16 `#B8B4AB`.

### 4. SectionLabel `중요도별 강도` + 기본 Card (padding 16, gap 12)
카드 안은 세로 flex gap 14 의 세 그룹이다. 그룹은 라벨(14 / 500, `margin-bottom 8`) + Segmented ([tokens Segmented](../tokens.md#segmented-seg)) 이다. 옵션은 `즉시` / `조용히` / `피드만`.

| 그룹 라벨 | importance | 샘플 선택 |
|---|---|---|
| `importance 5 · 4` | 5, 4 | 즉시 |
| `importance 3` | 3 | 조용히 |
| `importance 2 · 1` | 2, 1 | 피드만 |

즉시 = 소리 있는 푸시, 조용히 = 무음 알림, 피드만 = 푸시 없이 피드에만.

### 5. SectionLabel `실험` + 카드 (`padding 4px 16px`)

| 행 | 보조 줄 | 우측 |
|---|---|---|
| `탐색 슬롯` | `점수 경계 항목을 하루 1건 🧪로 보내 라벨을 모읍니다` | Toggle ON |

### 6. TabBar — **설정** 활성

## 설정값 (API 매핑)

| 설정 | 타입 | 예시 | 옵션 / 범위 |
|---|---|---|---|
| `channels.fcm.enabled` | bool | true | – |
| `channels.discord.enabled` | bool | true | – |
| `channels.discord.channel_name` | string (읽기 전용) | `#trend-alerts` | – |
| `channels.discord.reaction_sync` | bool (읽기 전용) | true | 보조 줄 |
| `channels.telegram.enabled` / `connected` | bool / bool | false / false | 미연결이면 `연결 안 됨` |
| `daily_push_cap` | int | 15 | 1–50, 표시 `15건` |
| `quiet_hours.start` / `end` | `HH:mm` | `23:00` / `08:00` | 시 단위, 자정 넘김 허용 |
| `quiet_hours.timezone` | IANA (읽기 전용) | `Asia/Seoul` | – |
| `dedupe_same_issue_daily` | bool | true | `rules.notify.cluster_daily_cap > 0` 과 같다 (계약 4.4) |
| `delivery_by_importance.high/mid/low` | enum | `instant` / `quiet` / `feed_only` | – |
| `exploration_slot.enabled` | bool | true | 하루 1건 고정 |

## 엣지
- 텔레그램 ON 인데 미연결이면 연결 안내 (디자인 없음).
- 무음 시간 중 도착한 알림은 피드에만 쌓인다 (사용자 결정, 계약 4.4).

## Figma 와 다른 점 (HTML 우선)
- Discord 보조 줄은 `👍/👎 리액션 동기화`, 탐색 슬롯 보조 줄은 `🧪로 보내` 다 (Figma 는 `유용/불필요`, `실험으로`).
- Figma 의 TopBar 높이 152 는 실수다. HTML 은 다른 하위 화면과 같은 44 + 56 이다.
- 중요도 그룹 라벨은 14/500 이다 (추출본 SemiBold).
