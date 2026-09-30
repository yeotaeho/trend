---
name: pipeline-diagnose
description: "이 알림이 왜 왔지/왜 안 왔지", 알림이 0건이거나 갑자기 줄거나 늘 때, 중복·형제 버전 알림, LLM 예산 조기 소진, 소스가 조용할 때 원인을 찾거나, dedupe·선별·점수·판정 임계값과 소스 trust 를 실데이터로 보정할 때 쓴다. 실배치 실행과 decisions·notifications·llm_calls 조회 절차.
---

# 파이프라인 진단·보정

## 원칙

- **가설은 실데이터 한 배치와 `decisions` 로 확인한다.** 순수 함수 테스트 56개가 다 통과한 상태에서 화이트리스트 전멸·dedupe 기준 오류·arXiv 비율 오판이 전부 첫 실배치에서 드러났다.
- **0 이 나오면 고장보다 상한부터 의심한다.** push 하루 상한, 무음 시간(23:00~08:00 KST, 해제 직후 몰아서 나감), `llm_calls` 일일 상한, 선별 모으기 대기(10건 또는 60분), 재임베딩 정지 순이다. `notify: 0` 을 발송 고장으로 보았다가 실제로는 08:02 무음 해제분이 상한을 다 쓴 경우가 있었다.
- **사용자의 증상 문구를 정확히 되묻는다.** "적시에 실행되지 않는다" 는 스케줄러가 아니라 디스코드 버튼의 "앱이 적시에 응답하지 않았습니다" 였다.
- **운영 DB(Neon `main`)는 읽기만 한다.** 가설 검증은 트랜잭션을 롤백하는 스크립트로 하고, 실험 실행은 Neon `dev` 에서 한다.
- **LLM 출력은 양자화돼 있다.** 선별 관련도는 0.1 단위라 가중치·임계값을 옮겨도 실질 통과선은 계단식으로만 움직인다. 계산할 때 0.1 단위 값으로 대입한다.

## 진단 순서

1. **로그의 멈춤 신호**를 본다. 운영은 VM 에서 `docker compose logs --since 3h app`, 로컬은 `uv run python scripts/run_job.py collect pipeline notify feedback` 출력이다.

   | 이벤트 | 뜻 |
   |---|---|
   | `pipeline.triage_deferred` | 선별 대기 중(10건·60분 미달). 고장 아님 |
   | `pipeline.triage_cap_reached` · `pipeline.judge_cap_reached` | 오늘 LLM 예산 소진 |
   | `pipeline.paused_for_reembedding` | `embedding_model` 불일치 행이 남아 파이프라인 정지 |
   | `pipeline.done scored=` · `notify.done sent=` · `collect.done fetched= inserted=` | 각 잡 결과 |

2. **항목 하나의 이력**을 본다. 판정 근거는 `details` 에 있다.
   ```sql
   select d.stage, d.passed, d.score, d.details, d.created_at
   from decisions d join items i on i.id = d.item_id
   where i.url like '%<URL 일부>%' order by d.created_at;
   ```
3. **오늘 예산**을 본다. 오늘은 Asia/Seoul 달력일이다.
   ```sql
   select kind, count(*) from llm_calls
   where called_at >= date_trunc('day', now() at time zone 'Asia/Seoul') at time zone 'Asia/Seoul'
   group by kind;
   ```
4. **발송 기록**을 본다. 보내지 않은 기록(피드 전용·`cluster_dup`)은 `channel='app'` 이다.
   ```sql
   select channel, level, count(*), count(error) as errors
   from notifications where sent_at > now() - interval '24 hours' group by 1, 2;
   ```
5. **조용한 소스**를 본다. `last_error` 가 계속 같으면 소스 장애다(외부 404·405 전례).
   ```sql
   select name, last_polled_at, last_error from sources order by last_polled_at nulls first;
   ```
6. **모집단을 다시 계산해** 가설을 수치로 확인한다. 예) "이 임계값이면 하루 몇 건이 판정까지 가나".
7. **재처리 경로를 건드렸으면** 다음 실행에서 `decisions` 가 몇 행 늘어나는지 센다. `NEW` 로 남거나 되살아나는 항목이 실행마다 같은 판정을 쌓은 전례가 세 번 있다(항목당 최대 307행).

## 임계값·가중치 보정

1. 실DB 에서 대상 구간 분포를 뽑는다. 쌍 유사도, 점수 구간별 건수, 도착 시각 같은 것이다. dedupe 는 `uv run python scripts/calibrate_dedupe.py` 가 표본을 준다.
2. 후보 값마다 통과 건수와 LLM 호출 수를 계산하거나 시뮬레이션한다(선별 게이트는 72시간 도착 시각 1,811건으로 2분 틱을 시뮬레이션해 골랐다).
3. 표로 사용자에게 제시하고 **결정은 사용자가 한다.** 정책·임계값은 사용자 결정 사항이다.
4. `config/rules.yaml`, `app/config.py` 기본값, `docs/pipeline.md` 수치를 같이 고친다. 코드 기본값과 YAML 이 어긋나 테스트가 옛 기준으로 돈 전례가 있다.
5. 다음 실배치로 확인한다.
6. 소스 신뢰도는 `uv run python scripts/weekly_report.py --days 7` 로 보고, 사용자가 동의하면 `--apply` 로 쓴다.
