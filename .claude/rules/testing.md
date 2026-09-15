---
paths:
  - "tests/**"
---

# 테스트 규칙

- **스택** — pytest + pytest-asyncio + respx. HTTP 는 전부 `respx` 로 모킹하고 실제 응답 샘플을 `tests/fixtures/` 에 둔다. 네트워크·실 LLM 호출 금지.
- **순서** — 변경 모듈 근처 파일 먼저(`uv run pytest tests/sources/test_rss.py`), 마무리에 전체 `uv run pytest` + `ruff check` + `ruff format` + `mypy app`.
- **통합 테스트** — `tests/integration/` 는 `TEST_DATABASE_URL` 이 있어야 돈다. 단위 테스트로 대신할 수 없는 것(pgvector 쿼리, 예약 원자성)만 여기 둔다.
- **가짜 완료 금지** — `pytest.skip`, `xfail`, 빈 assert, 구현 없는 스텁 테스트는 완료 근거가 아니다. 발견하면 구현하거나 블로커로 보고한다.
- **결정 로그 검증** — 파이프라인 테스트는 상태 전이뿐 아니라 `decisions` 행이 남는지도 확인한다.
