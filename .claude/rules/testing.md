---
description: 백엔드 테스트를 새로 쓰거나 돌리거나 결과를 해석할 때. 특히 테스트는 통과하는데 운영에서 깨지는 상황이 의심될 때.
paths:
  - "tests/**"
---

# 테스트 규칙

- **스택** — pytest + pytest-asyncio + respx. HTTP 는 전부 `respx` 로 모킹하고 실제 응답 샘플을 `tests/fixtures/` 에 둔다. 네트워크·실 LLM 호출 금지.
- **순서** — 변경 모듈 근처 파일 먼저(`uv run pytest tests/sources/test_rss.py`), 마무리에 전체 `uv run pytest` + `ruff check` + `ruff format` + `mypy app`.
- **통합 테스트** — `tests/integration/` 는 `TEST_DATABASE_URL` 이 있어야 돈다. 단위 테스트로 대신할 수 없는 것(pgvector 쿼리, 예약 원자성)만 여기 둔다.
- **가짜 완료 금지** — `pytest.skip`, `xfail`, 빈 assert, 구현 없는 스텁 테스트는 완료 근거가 아니다. 발견하면 구현하거나 블로커로 보고한다.
- **결정 로그 검증** — 파이프라인 테스트는 상태 전이뿐 아니라 `decisions` 행이 남는지도 확인한다.

## 세션에서 배운 것

> 독립 사건 둘 이상으로 관찰된 것만 둔다(괄호는 사건 날짜). 한 번 관찰은 `lessons/BANK.md` 에, 한 곳의 이유는 코드 주석에 있다(통합 테스트 `engine.dispose()` 등).

- **429·게이트 테스트는 실제 sleep 을 쓴다**(09-03, 09-06, `retry_after` 0.1 이상). sleep 을 모킹하면 게이트가 끝나기 전에 재시도해 실패 원인이 가려진다. Windows 타이머는 최대 15ms 일찍 깬다.
- **새 테스트는 수정 전 코드에서 먼저 실패시킨다**(09-10, 09-11, 09-28 의 작업마다 밟은 절차).
- **예외 기대값은 실패 이유까지 좁힌다**(09-03, 10-05). 상위 예외나 `ValidationError` 만 보면 다른 이유로도 통과한다. `RateLimited`(`RuntimeError` 하위)로 바꾼 뒤 옛 기대값 테스트가 계속 통과했고, 설정 모델(`extra=forbid`) 범위 테스트는 키를 만들기 전에도 `extra_forbidden` 으로 통과했다. 오류 종류까지 본다.
- 단위 테스트가 다 통과해도 새 관문·소스·재처리 경로는 실배치로 확인한다(스킬 `pipeline-diagnose`).
- `.claude/` 훅·등록 스크립트의 판정은 `tests/test_claude_harness.py` 가 지킨다. 가드·라우터를 고치면 이 테스트도 고친다.
