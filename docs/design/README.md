# 모바일 앱 디자인 명세 (Flutter 구현용)

Figma 파일 `xbgeR2ik7vN0BXtBxFPfI5` · 섹션 "기술 파악 · 모바일 앱 v0.1"에서 추출. Figma 접근 권한 없이 구현할 수 있도록 화면별 레이아웃·문구·데이터 필드·설정값을 정리했다.
공통 색/타이포/컴포넌트는 [tokens.md](tokens.md) 참조.

- 제외: `1 로그인`(2:2), `2 온보딩 · 콜드스타트`(4:2) — 요청 범위 밖
- 기준 프레임 390 × 844, 폰트 IBM Plex Sans KR, Figma 변수 없음

## 화면 목록

| # | 화면 | Figma node | 명세 | 스크린샷 | 탭 |
|---|---|---|---|---|---|
| 03 | 피드 (알림 이력) | `4:66` | [03-feed.md](screens/03-feed.md) | [png](screens/03-feed.png) | 피드 (루트) |
| 04 | 관심사 | `5:2` | [04-interests.md](screens/04-interests.md) | [png](screens/04-interests.png) | 설정 › |
| 05 | 알림 설정 | `5:193` | [05-notification-settings.md](screens/05-notification-settings.md) | [png](screens/05-notification-settings.png) | 설정 › |
| 06 | 수집 소스 | `6:2` | [06-sources.md](screens/06-sources.md) | [png](screens/06-sources.png) | 설정 › |
| 07 | 피드백 · 판정 근거 | `6:139` | [07-feedback-rationale.md](screens/07-feedback-rationale.md) | [png](screens/07-feedback-rationale.png) | 전체화면 push |
| 08 | 내 프로필 (사용자 파악) | `6:217` | [08-profile.md](screens/08-profile.md) | [png](screens/08-profile.png) | 내 프로필 (루트) |
| 09 | 걸러진 항목 · 소스별 | `9:2` | [09-filtered-by-source.md](screens/09-filtered-by-source.md) | [png](screens/09-filtered-by-source.png) | 피드 › |
| 10 | 걸러진 항목 · 종류별 | `9:181` | [10-filtered-by-type.md](screens/10-filtered-by-type.md) | [png](screens/10-filtered-by-type.png) | 피드 › |
| 11 | 찜한 알림 | `23:39` | [11-saved.md](screens/11-saved.md) | **없음** (Figma MCP 한도 초과) | 찜 (루트) |

## 내비게이션 맵

```
[TabBar]
 ├─ 피드 ──── 03 피드
 │             ├─ 카드 탭 ─────────────────→ 07 피드백·판정 근거 (탭바 없음)
 │             │                               ├─ 헤더 ↗ → 원문(외부 브라우저)
 │             │                               └─ 최근 판정 행 → 07 (다른 알림)
 │             ├─ [원문] → 외부 브라우저
 │             ├─ [찜] → 11에 추가/해제 (화면 이동 없음)
 │             ├─ 🔍 / 🔔 → (디자인 없음)
 │             └─ "걸러짐 571건 보기 ›" ──→ 09 걸러진 항목·소스별
 │                                              ⇄ (세그먼트) 10 종류별
 │                                              ⇄ (세그먼트) 관문별 (디자인 없음)
 ├─ 찜 ────── 11 찜한 알림
 │             ├─ 카드 탭 → 07 (권장)
 │             ├─ [원문] → 외부 브라우저 / [폴더] → 폴더 이동 시트 (디자인 없음)
 │             └─ 폴더 칩 "+" → 새 폴더 (디자인 없음)
 ├─ 설정 ──── (설정 루트 목록: 디자인 없음 — 구현 필요)
 │             ├─→ 04 관심사        (헤더 "저장"으로 명시 저장)
 │             ├─→ 05 알림 설정     (즉시 저장)
 │             └─→ 06 수집 소스     (헤더 + → 소스 추가, 디자인 없음)
 └─ 내 프로필 ─ 08 내 프로필
               └─ 주간 리포트 카드 → 리포트 상세 (디자인 없음)
```

04/05/06/09/10은 탭바를 유지한 채 해당 탭 스택에 push(부모 탭 활성 표시). 07만 탭바 없이 전체 화면.

## 디자인 공백 (구현 시 결정 필요)
- 설정 탭 루트 화면, 검색 화면(피드/걸러짐/찜), 알림(🔔) 화면, 관문별 보기, 주간 리포트 상세, 소스 추가/상세, 폴더 이동/생성, 각종 값 편집(push 상한·무음 시간·kind 가중치) 피커, 빈 상태/로딩/오류 상태 — 모두 디자인 없음.
- 11 찜 화면은 스크린샷 미확보로 일부 색상 추정(★).

## 데이터 필드 · 설정값 목록

백엔드 API와 diff 하기 위한 통합 표. 필드명은 제안(snake_case)이며 화면 문구 기준으로 명명했다. **설정**(사용자가 바꾸는 값)은 구분 열에 `설정`으로 표시.

| 필드 / 설정 | 구분 | 화면 | 타입 | 예시 |
|---|---|---|---|---|
| `push_sent_today` | 통계 | 03 | int | 4 |
| `daily_push_cap` | 설정 | 03, 05 | int (건) | 15 |
| `filtered_today_count` / `filtered_total` | 통계 | 03, 09, 10 | int | 571 |
| `collected_total` / `items_collected_today` | 통계 | 06, 09, 10 | int | 612 |
| alert.`id` | 알림 | 03, 07, 11 | string | – |
| alert.`source_name` | 알림 | 03, 07, 11 | string | `GitHub Releases`, `arXiv cs.CL` |
| alert.`delivered_at` | 알림 | 03, 07 | datetime → 상대시간 | `42분 전` |
| alert.`delivery_mode` | 알림 | 03, 07 | enum `instant`/`quiet`/`feed_only`/`experiment` | `즉시` |
| alert.`is_exploration` | 알림 | 03 | bool | true (`실험 · 경계 항목`) |
| alert.`title` | 알림 | 03, 07, 11 | string | `[릴리즈] MCP Python SDK v2.2.0 — …` |
| alert.`summary` | 알림 | 03, 07 | string | `스트리밍 HTTP 클라이언트의 …` |
| alert.`categories` | 알림 | 03 | string[] | `["mcp-tooling","python-backend"]` |
| alert.`url` | 알림 | 03, 07, 11 | URL | – |
| alert.`is_saved` | 사용자 상태 | 03 | bool | true |
| alert.`feedback` | 사용자 입력 | 03, 07 | enum? `useful`/`not_useful`/null | `useful` |
| feed filter | 쿼리 | 03 | enum `all`/`instant`/`quiet`/`experiment`/`useful` | `전체` |
| score.`total` | 판정 근거 | 07, 09, 10 | float | 0.43 |
| score.`threshold` | 판정 근거 | 07 | float | 0.45 |
| score.`components.src/rel/fresh/kind` | 판정 근거 | 07, 09 | float ×4 | 0.10 / 0.25 / 0.10 / 0.00 |
| `routing_label` | 판정 근거 | 07 | string/enum | `경계 → 탐색 슬롯` |
| screening.`relevance` | 판정 근거 | 07, 09, 10 | float | 0.83 |
| screening.`kind` | 판정 근거 | 07, 09 | enum | `technique` |
| screening.`reason` | 판정 근거 | 07, 09, 10 | string | `KV 캐시 압축의 구체 기법과 수치, 코드 공개` |
| judgment.`importance` | 판정 근거 | 07 | int 1–5 | 4 |
| judgment.`similar_feedback` | 판정 근거 | 07 | {label, title} | 유용 `PagedAttention v2 …` |
| `recent_feedback[]` | 이력 | 07 | {alert_id, feedback, title, created_at} | 유용 · `MCP Python SDK …` · `42분` |
| `recent_feedback_today_count` | 이력 | 07 | int | 3 |
| `profile.self_description` | 설정 | 04 | string | `AI 시스템 개발자. LLM 애플리케이션…` |
| `profile.not_interested` | 설정 | 04 | string | `채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠` |
| `taxonomy[]` | 마스터 | 04 | {slug, label}[] (12) | `llm-model` 새 모델·벤치마크 |
| `selected_categories` | 설정 | 04 | string[] | 8 / 12 |
| `watch_keywords` | 설정 | 04 | string[] | `claude, mcp, langgraph, fastapi, pydantic, next.js, uv` |
| `kind_weights.release_major` | 설정 | 04 | float | +0 |
| `kind_weights.release_patch` | 설정 | 04 | float | 0 |
| `kind_weights.technique` | 설정 | 04 | float | 0 |
| `kind_weights.survey` | 설정 | 04, 10 | float | −0.15 |
| `kind_weights.tutorial` | 설정 | 04, 10 | float | −0.05 |
| `kind_weights.promo` | 설정 | 04, 10 | float | −0.30 |
| `channels.fcm.enabled` | 설정 | 05 | bool | true |
| `channels.discord.enabled` | 설정 | 05 | bool | true |
| `channels.discord.channel_name` | 연결 정보 | 05 | string | `#trend-alerts` |
| `channels.discord.reaction_sync` | 연결 정보 | 05, 07 | bool | true |
| `channels.telegram.enabled` / `connected` | 설정 / 연결 정보 | 05 | bool / bool | false / false (`연결 안 됨`) |
| `quiet_hours.start` / `end` | 설정 | 05 | time HH:mm | `23:00` / `08:00` |
| `quiet_hours.timezone` | 설정 | 05 | IANA tz | `Asia/Seoul` |
| `dedupe_same_issue_daily` | 설정 | 05 | bool | true |
| `delivery_by_importance.high` (5·4) | 설정 | 05 | enum `instant`/`quiet`/`feed_only` | `instant` (즉시) |
| `delivery_by_importance.mid` (3) | 설정 | 05 | enum | `quiet` (조용히) |
| `delivery_by_importance.low` (2·1) | 설정 | 05 | enum | `feed_only` (피드만) |
| `exploration_slot.enabled` | 설정 | 05 | bool | true (하루 1건) |
| `sources_enabled_count` / `sources_total` | 통계 | 06 | int / int | 9 / 10 |
| `llm_calls_used_today` / `llm_calls_budget` | 통계 / 설정(?) | 06 | int / int | 41 / 60 |
| source.`id` | 소스 | 06, 09, 08 | string `{type}:{name}` | `rss:anthropic` |
| source.`type` | 소스 | 06, 09 | enum `rss`/`github_release`/`youtube` | `rss` |
| source.`group` | 소스 | 06 | enum | `기술 블로그 · RSS` / `논문 · 릴리즈 · 영상` |
| source.`enabled` | 설정 | 06 | bool | true |
| source.`poll_interval_min` | 소스 | 06 | int (분) | 15 / 30 / 60 |
| source.`trust` | 소스 | 06 | float 0–1 | 0.9 |
| source.`trust_base` → `trust_calibrated` | 학습 | 06, 08 | float → float | 0.5 → 0.58 |
| source.`consecutive_failures` / `error_hint` | 소스 상태 | 06 | int / string | 5 / `미러 확인 필요` |
| source.`repo_count` | 소스 | 06 | int | 10 |
| `planned_sources` | 마스터 | 06 | string[] | `Hacker News, Reddit, GitHub Trending, X` |
| `period_days` | 쿼리 | 08 | int | 14 |
| user.`display_name` | 사용자 | 08 | string | `여태호` |
| user.`discord_connected` | 사용자 | 08 | bool | true |
| user.`onboarding_done` / `onboarding_total` | 사용자 | 08 | int / int | 8 / 8 |
| stats.`alerts_received` / `push_count` / `experiment_count` | 통계 | 08 | int ×3 | 61 / 38 / 9 |
| stats.`useful_ratio` / `useful_count` / `not_useful_count` | 통계 | 08 | % / int / int | 64% / 27 / 15 |
| stats.`missed_issues` | 통계 | 08 | int | 1 |
| `category_reactions[]` | 통계 | 08 | {category, useful, not_useful, total} | `mcp-tooling` 14 |
| `learned.kind_penalties[]` | 학습 | 08, 10 | {kind, not_useful, total, active} | 서베이·전망 4/4 자동 감점 중 |
| `learned.profile_vector_labels` / `personal_model_threshold` | 학습 | 08 | int / int | 42 / 50 |
| `weekly_report.latest` | 리포트 | 08 | {id, title, subtitle} | `9월 2주차 리포트` |
| `window` | 쿼리 | 09, 10 | string | `최근 24시간` |
| `gate_counts.exclude/dedup/screening/score/judgment` | 통계 | 09, 10 | int ×5 | 9 / 58 / 318 / 164 / 22 |
| `borderline_count` / `borderline_range` | 통계 | 09, 10 | int / [float,float] | 154 / [0.35, 0.45] |
| filtered view mode | 쿼리 | 09, 10 | enum `source`/`kind`/`gate` | `소스별` |
| group (소스별).`source_id`, `count`, `summary` | 통계 | 09 | string, int, string | `rss:arxiv-cs-ai`, 312, `선별 relevance 0.5 미만 71%` |
| group (종류별).`kind`, `kind_label`, `count`, `summary` | 통계 | 10 | enum?, string, int, string | `survey`, `서베이·전망`, 187 |
| `unclassified_count` | 통계 | 10 | int | 67 |
| dropped item.`id`, `title`, `dropped_gate`, `reason`, `source_name` | 걸러진 항목 | 09, 10 | – | `Survey of Agentic …`, `score`, `0.41 · arXiv cs.SE` |
| dropped item.`exploration_candidate` | 걸러진 항목 | 09, 10 | bool | true (`경계 → 내일 탐색 슬롯 후보`) |
| dropped item.`restored` | 사용자 입력 | 09, 10 | bool (👍 복원) | false |
| `folders[]` | 설정 | 11 | {id, name, count} | `나중에 읽기` 9 |
| `saved_total` / `unread_count` | 통계 | 11 | int / int | 23 / 7 |
| saved sort | 쿼리 | 11 | enum | `최근 찜한 순` |
| saved.`alert_id`, `source_name`, `saved_at`, `folder`, `title`, `url` | 찜 | 11 | – | `GitHub Releases · 9월 14일`, `적용해보기` |
| saved.`memo` | 사용자 입력 | 11 | string? | `trend 레포 python-sdk 올릴 때 OAuth 검증 부분 확인` |
| saved.`is_read` | 사용자 상태 | 11 | bool | – |
| `resurface_unread_after_days` | 정책(고정) | 11 | int | 7 |

### 사용자 액션 (쓰기 API 후보)
| 액션 | 화면 |
|---|---|
| 피드백 유용/불필요 설정·해제 | 03, 07 |
| 찜 추가/해제, 폴더 이동, 메모 편집, 폴더 생성 | 03, 11 |
| 걸러진 항목 복원(👍) | 09, 10 |
| 관심사 저장(프로필 문장, 카테고리, 키워드, kind 가중치) | 04 |
| 알림 설정 개별 변경(즉시 저장) | 05 |
| 소스 on/off, 소스 추가 | 06 |
