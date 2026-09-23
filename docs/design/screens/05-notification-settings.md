# 05 알림 설정

- Figma node: `5:193` · 프레임 390 × 1120 (세로 스크롤) · 스크린샷: [05-notification-settings.png](05-notification-settings.png)
- 하단 탭: **설정** 활성 (설정 하위 화면)

## 목적

알림 전달 채널, 알림 피로 방지 규칙(하루 상한·무음 시간·중복 억제), 중요도(importance)별 전달 강도, 실험(탐색 슬롯) 여부를 설정한다.

## 레이아웃 (위 → 아래)

### 1. TopBar (`5:194`)
- `icon/back` 20 + 제목 `알림 설정` (Bold 18). 우측 버튼 없음 → **변경 즉시 저장**(토글/세그먼트 변경 시 바로 API 반영).
- 주의: Figma에서 이 TopBar 높이가 152로 위쪽 여백이 과도함(디자인 실수로 보임). 다른 하위 화면과 동일하게 높이 77(`pt 44`)로 구현.

### 2. SectionLabel `채널` + 카드 (`5:203`)
Row(토글형): 좌측 제목(Medium 15) + 선택적 보조 줄(Regular 12 `#8A877F`), 우측 Toggle 44×26. 행 사이 구분선 1px `#EFECE6`.

| 행 제목 | 보조 텍스트 | 토글 샘플 | 설명 |
|---|---|---|---|
| `앱 푸시 (FCM)` | – | ON | 모바일 푸시 채널 |
| `Discord 채널` | `#trend-alerts · 유용/불필요 리액션 동기화` | ON | 연결된 Discord 채널명 + 리액션 동기화 안내 |
| `Telegram 봇` | `연결 안 됨` | OFF | 미연결 상태. ON 시 연결 플로우 필요(디자인 없음) |

### 3. SectionLabel `알림 피로 방지` + 카드 (`5:224`)
| 행 | 보조 텍스트 | 우측 | 인터랙션 |
|---|---|---|---|
| `하루 push 상한` | – | `15건` + `icon/chev` | 탭 → 숫자 선택(디자인 없음). 권장 옵션: 5/10/15/20/30/무제한 또는 1–50 스테퍼 |
| `무음 시간` | `Asia/Seoul · 무음 중엔 피드에만 쌓입니다` | `23:00 – 08:00` + chev | 탭 → 시작/종료 시간 선택(TimePicker 2개). 시간대 표시 |
| `같은 이슈 하루 1건` | `버전 형제 릴리즈는 제목에 병기` | Toggle ON | 동일 이슈 클러스터 하루 1회만 알림 |

값 텍스트: Regular 14 `#1C1B19`, chev 16 `#8A877F`.

### 4. SectionLabel `중요도별 강도` + 카드 (`5:249`, 358×258)
세 그룹, 각각 라벨(SemiBold 14 `#1C1B19`, 예: `importance 5 · 4`) + Segmented(326×38).
Segmented: 트랙 `#EBE8E1` radius 10, padding 3; 선택 세그먼트 흰 배경 radius 8 + 약한 그림자, 글자 SemiBold 13 `#1C1B19`; 미선택 글자 Medium 13 `#8A877F`.
옵션 3개: `즉시` / `조용히` / `피드만` (단일 선택)

| 그룹 라벨 | importance 값 | 샘플 선택 |
|---|---|---|
| `importance 5 · 4` | 5, 4 | 즉시 |
| `importance 3` | 3 | 조용히 |
| `importance 2 · 1` | 2, 1 | 피드만 |

의미: 즉시 = 소리/진동 있는 푸시, 조용히 = 무음 알림(알림센터에만), 피드만 = 푸시 없이 피드에만 적재.

### 5. SectionLabel `실험` + 카드 (`5:280`)
| 행 | 보조 텍스트 | 우측 |
|---|---|---|
| `탐색 슬롯` | `점수 경계 항목을 하루 1건 실험으로 보내 라벨을 모읍니다` | Toggle ON |

### 6. TabBar — 공통, **설정** 활성

## 설정값 (API 매핑 대상)

| 설정 | 타입 | 예시 | 옵션/범위 |
|---|---|---|---|
| `channels.fcm.enabled` | bool | true | – |
| `channels.discord.enabled` | bool | true | – |
| `channels.discord.channel_name` | string (read-only) | `#trend-alerts` | 연결 정보 표시 |
| `channels.discord.reaction_sync` | bool (표시용) | true | 보조 텍스트로만 노출 |
| `channels.telegram.enabled` | bool | false | 미연결 시 OFF |
| `channels.telegram.connected` | bool | false | false면 `연결 안 됨` |
| `daily_push_cap` | int | 15 | 표시 `15건`. 권장 범위 1–50 |
| `quiet_hours.start` | time(HH:mm) | `23:00` | 00:00–23:59 |
| `quiet_hours.end` | time(HH:mm) | `08:00` | 자정 넘김 허용 |
| `quiet_hours.timezone` | string (IANA) | `Asia/Seoul` | |
| `dedupe_same_issue_daily` | bool | true | 같은 이슈 하루 1건 |
| `delivery_by_importance.high` (5·4) | enum | `instant` | `instant`(즉시) / `quiet`(조용히) / `feed_only`(피드만) |
| `delivery_by_importance.mid` (3) | enum | `quiet` | 동일 |
| `delivery_by_importance.low` (2·1) | enum | `feed_only` | 동일 |
| `exploration_slot.enabled` | bool | true | 하루 1건 고정 (횟수는 설정 UI 없음) |

## 엣지
- Telegram 토글 ON 시 미연결이면 연결 안내(딥링크/봇 토큰)로 이동 — 디자인 없음.
- 무음 시간 중 도착 알림은 `피드에만 쌓임` (즉시 설정이어도 푸시 안 함).
