---
paths:
  - "app/pipeline/**"
  - "config/rules.yaml"
---

# 파이프라인 규칙

설계 원칙 네 가지. **플러그인 · 멱등 · 정책은 문장으로 · 결정은 로그로.** 단계 흐름·임계값·상태 전이는 `docs/pipeline.md` 를 본다.

- **결정은 로그로** — 통과/탈락 판단마다 `decisions` 행을 남긴다 (`stage`, `passed`, `score`, `details` 에 매칭 근거·점수 내역·LLM 응답).
- **LLM 호출은 예약 뒤에** — `reserve_call` 로 `llm_calls` 행을 먼저 커밋하고 호출한다. 예산이 바닥나면 항목은 `NEW` 로 남기고 다음 실행에서 `decisions`·`summaries` 캐시를 재사용한다.
- **재처리 대상은 `NEW` 뿐** — `FILTERED_OUT`(중복·exclude)과 `DROPPED`(stale·점수·판정 탈락)는 다른 종단 분기다. 섞지 않는다.
- **정책은 문장으로** — `rules.yaml` 의 `policy` 문장을 선별·판정 프롬프트가 읽는다. 키워드 목록은 관문이 아니다. `exclude` 만 규칙 필터다.
- **임계값은 YAML** — dedupe·triage·scoring·notify 임계값은 `config/rules.yaml`. 코드에 숫자를 박지 않는다.
- **임베딩** — Voyage `voyage-3.5-lite` 1024차원 고정. `items.embedding` 은 파이썬에서 읽지 않고 비교는 SQL 로 한다. 모델을 바꾸면 `scripts/backfill_embeddings.py` 로 전량 재계산한다. 무료 등급은 분당 요청 3회라 배치 64건·간격 20초를 지킨다.
- **본문 보강 가드** — `llm.py` 의 `enrich_body` 는 사설·루프백·링크로컬 주소와 그리로 가는 리다이렉트(최대 5홉)를 열지 않는다. 이 가드를 약화시키지 않는다.
- **프롬프트 변경** — `tests/test_prompts.py` 로 구조화 출력 스키마가 유지되는지 확인한다.
- 수치·흐름을 바꾸면 `docs/pipeline.md` 를 같이 고친다.
