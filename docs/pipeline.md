# 검증 파이프라인 v2

설계 원칙 — **플러그인 · 멱등 · 정책은 문장으로 · 결정은 로그로.** 원문은 `검증파이프라인-v2-설계서.md`·`검증파이프라인-v2-구현서.md`. 임계값의 실제 값은 `config/rules.yaml` 이 진실이고 아래 수치는 참고다.

## 설정 — YAML + 앱 덮어쓰기

유효 설정은 `config/rules.yaml` 위에 앱이 저장한 덮어쓰기(`user_prefs.data`, 키는 `Rules` 섹션 이름)를 깊은 병합(목록은 통째 교체)한 값이다. `get_rules()` 가 이 값을 돌려주며, 기동 시(lifespan, 스케줄러 전) DB 에서 한 번 읽고 설정 API(`/api/v1/settings/*`, `/api/v1/sources/{id}`)가 저장·커밋한 직후 `set_prefs_overlay()` 로 갈아끼운다. 다음 선별·판정·발송부터 반영되고 이미 매긴 점수는 다시 계산하지 않는다. 덮어쓰기 섹션이 검증에 실패하면(YAML 키가 바뀐 옛 값 등) 기동은 계속하고 그 섹션의 키를 하나씩 얹어 맞지 않는 키만 경고 후 무시하며, 다음 앱 저장이 그 키를 지운다. `policy.taxonomy` 는 선별 어휘라 YAML 로만 바꾼다. 소스 on/off 는 `data.sources` 에 남고 `sync_sources` 가 YAML 위에 얹는다. YAML 을 고쳐도 앱이 덮어쓴 키는 앱 값이 이긴다.

## 흐름

```
[소스] → [수집기 sources/*] → [적재 + 임베딩] → NEW
                └ 아는 URL 이면 버리지 않고 raw.metrics(키별 max)·mentions 병합.
                  점수 탈락 항목은 마지막 점수 + hot·multi 이득(마지막 결정의 breakdown 기준,
                  신선도 감쇠 반영)이 임계값 이상이면 NEW 로 되살림 (LLM 재호출 없음)
1국면 (항목별)   stale(72h) → 중복·관련 (벡터 코사인, 생존자 기준) → exclude 규칙
2국면 (25건 배치) LLM 선별 — 10건이 모이거나 60분을 기다리면 호출. 관련도 0~1 + kind + topics + 이유
3국면 (항목별)   점수(src·rel·hot·multi·fresh + kind 감점 ≥ 0.45) → 본문 보강 → LLM 판정·요약 → SCORED
발송 잡          강도·무음·push 상한·클러스터 하루 상한 → 켜진 채널 전부 (+ 🧪 탐색 슬롯 1건/일)
```

## 단계별 요점

| 단계 | 파일 | 요점 |
|---|---|---|
| 정규화 | `pipeline/normalize.py` | utm 등 제거 → SHA-256 `url_hash`. 같은 글의 다른 URL 을 한 항목으로 |
| 적재·병합 | `pipeline/ingest.py` | `url_hash` unique. 아는 URL 은 `metrics`(키별 max)·`mentions` 병합. 같은 `family` 소스의 교차 등재는 멘션·multi 신호를 만들지 않는다 |
| 되살림 | `pipeline/ingest.py` + `scoring.revive_gain` | `DROPPED`(점수 탈락) 항목의 hot·multi 변화량이 마지막 점수를 임계값 위로 올릴 수 있을 때만 `NEW` 로. 선별 결과는 캐시 재사용 |
| 임베딩 | `pipeline/embedding.py` | Voyage `voyage-3.5-lite` 1024차원. 적재 직후 계산, 모델 불일치 행이 남아 있으면 파이프라인이 스스로 멈춘다 |
| 중복·관련 | `pipeline/dedupe.py` | 72h 창, 코사인 **≥ 0.96 중복**(FILTERED_OUT) · **≥ 0.88 관련**(같은 `cluster_id`). 생존자 기준 비교 |
| exclude | `pipeline/rules.py` | `rules.yaml` 의 exclude 키워드·도메인만. 통과 관문이 아니라 배제 관문 |
| 선별 | `pipeline/triage.py` | 25건 배치. 대기 항목이 10건 모이거나 가장 오래된 항목이 60분을 기다려야 호출하고, 그 전에는 `NEW` 로 둔다. `policy` 문장(관심 카테고리 힌트 포함)과 분류표 `policy.taxonomy` 를 읽고 관련도 0~1·`kind`·`topics`·이유를 낸다. `topics` 는 분류표 slug 1~3개이며 표 밖 값은 버리고 앞 3개만 남긴다 (항목 실패 아님). `decisions(stage=triage).details` = `relevance`·`reason`·`kind`·`topics`·`batch_id`·`prompt_version`. 캐시 재사용 때 `kind`·`topics` 가 없는 옛 행은 `other`·`[]` 로 채우고 다시 부르지 않는다 |
| 점수 | `pipeline/scoring.py` | trust·relevance·hotness·multi·freshness 가중합 + kind 감점. 임계값 **0.45** 미달 → DROPPED. `decisions(stage=score)` 에 breakdown |
| 본문 보강 | `pipeline/llm.py` `enrich_body` | trafilatura. 사설·루프백·링크로컬 주소와 그리로 가는 리다이렉트(최대 5홉)를 열지 않는다. DNS 리바인딩은 막지 않는다 |
| 판정·요약 | `pipeline/llm.py` | 구조화 출력 → `summaries`(`title_ko`, `summary_ko`, `tags`, `importance` 1~5, `worth_notifying`). 최근접 피드백 사례(👍/👎 만, 해제 `cleared` 제외, 요약 없는 복원 항목은 원문 제목)를 프롬프트에 주입하고 `decisions(stage=llm).details.examples` = `[{item_id, verdict, title}]` 로 남긴다 (탐색 판정 포함, 0건이면 `[]`) |
| 소스 신뢰도 | `pipeline/trust.py` | 피드백으로 베이즈 보정. `scripts/weekly_report.py --apply` 로 기록 |

## LLM 예산

모든 호출 직전에 `db/budget.py` 의 `reserve_call` 로 `llm_calls` 행을 먼저 커밋한다. 독립 트랜잭션 + 단일 키 자문 잠금. 일일 상한은 **선별 60 · 판정 300 · 탐색 3**, 오늘은 Asia/Seoul 달력일. 예산이 바닥나면 항목은 `NEW` 로 남고 다음 실행에서 `decisions`·`summaries` 캐시를 재사용한다. 단일 프로세스 전제.

## 상태 전이

```
NEW ──stale(72h)──▶ DROPPED
NEW ──중복/exclude──▶ FILTERED_OUT
NEW ──관문 통과──▶ (선별: 관련도) ──▶ (점수) ──미달──▶ DROPPED ──hot·multi 이득──▶ NEW (되살림)
                                          └─통과──▶ (판정) ──false──▶ DROPPED
                                                          └─true──▶ SCORED ──발송·피드 전용·클러스터 억제──▶ SENT
                                                                           └─모든 채널 실패──▶ FAILED
```

`FILTERED_OUT` 과 `DROPPED` 는 다른 종단 분기다. 재처리 대상은 `NEW` 뿐이다. `QUEUED` 는 무음 시간 항목을 아침까지 미루던 옛 상태라 더는 만들지 않고, 남은 행은 발송 잡이 `SCORED` 와 함께 처리한다.

## 발송 정책 (`notify/policy.py`)

판단 순서는 **강도 → 무음 시간 → push 상한 강등 → 클러스터 하루 상한** 이다. 보내지 않는 항목(피드 전용·클러스터 억제)도 `notifications` 에 `channel='app'` 행을 남기고 `SENT` 로 둔다.

| 규칙 | 설정 (`rules.notify`) | 동작 |
|---|---|---|
| 강도 | `delivery_by_importance` (high 5·4 / mid 3 / low 2·1) | 기본 **instant · quiet · feed_only** → `push` · `silent` · `feed`. `feed` 는 어느 채널로도 보내지 않는다 |
| 무음 시간 | `quiet_start_hour`·`quiet_end_hour` (**23:00~08:00 KST**) | 무음 중 `push`·`silent` 는 **피드에만** 남긴다 (`feed`). 아침 몰아 보내기는 없다 |
| push 상한 | `daily_push_cap` (**15**) | 오늘 `push` 로 나간 **서로 다른 항목 수**가 상한 이상이면 `silent` 로 낮춘다. 채널 수와 `cluster_dup` 은 세지 않는다 |
| 클러스터 하루 상한 | `cluster_daily_cap` (**1**, 0 = 끔) | `push`·`silent` 항목만 본다. 오늘 같은 `cluster_id` 로 `push`·`silent`·`explore` 가 나간 서로 다른 항목 수가 상한 이상이면 `level='cluster_dup'` 행만 남긴다. `decisions` 에는 남기지 않는다 |
| 제목 병기 | — | 보내는 항목은 같은 클러스터 형제(`SCORED`·`QUEUED`·`SENT`, 72h) 제목의 버전을 모아 `(v2.2.0 · v1.30.0)` 을 붙인다. 버전이 2개 미만이면 그대로. 모든 채널이 같은 제목을 받고 `notifications.title` 에 남는다 |
| 채널 | `channels.{fcm,discord,telegram}` + `.env` 연결 정보 (FCM 은 서비스 계정 파일도 있어야 한다) | 켜져 있고 연결된 채널 전부로 보내고 채널마다 행 하나. 켜진 채널이 없으면 전부 피드 전용 |

- **팬아웃 실패** — 한 채널이라도 성공하면 `SENT`, 전부 실패하면 `FAILED`. 아직 어느 채널도 성공하지 않았는데 `RateLimited` 면 기록 없이 배치를 멈추고 다음 잡이 그 항목부터 다시 시도한다. 다른 채널이 이미 나간 뒤의 `RateLimited` 는 그 채널 행에 `error='rate_limited'` 로 남긴다.
- **탐색 슬롯** — 경계 항목(점수 0.35~0.45) 하루 1건을 판정해 🧪 silent 로 켜진 채널 전부에 보낸다. 판정 예산은 탐색 3회/일. `explore_enabled=false` 거나 켜진 채널이 없으면 판정도 하지 않는다. 클러스터 하루 상한이 켜져 있으면 오늘 이미 나간 클러스터의 항목은 후보가 아니다.
- **피드백** — 디스코드 리액션·텔레그램 👍/👎 → `feedback` upsert(항목당 1건) → 최근접 사례 주입·소스 신뢰도 보정.
