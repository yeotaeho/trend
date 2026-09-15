---
paths:
  - "app/sources/**"
  - "config/sources.yaml"
  - "tests/sources/**"
---

# 수집기 규칙

**소스 하나 = 파일 하나.** `app/sources/base.py` 의 `Source` 프로토콜(`name`, `interval`, `fetch(since)`)을 구현하고 레지스트리에 등록한다. 수집기는 `NormalizedItem` 을 내보내는 데서 끝난다. 중복 제거·점수·판정은 파이프라인이 한다.

- **새 소스 추가** — `config/sources.yaml` 에 `type` · `poll_interval_sec` · `trust_score` · `config` 를 등록한다. 같은 매체의 피드 여러 개는 `config.family` 를 같게 둔다 (적재 병합에서 같은 소스로 본다).
- **since 를 못 쓰는 소스** (HN 프론트 페이지처럼 목록을 통째로 주는 API) — 수집기에서 걸러내지 않는다. 아는 URL 은 적재 단계가 `metrics`·`mentions` 로 병합한다.
- **HTTP** — `httpx` + `tenacity` 재시도. 테스트는 `respx` 로 모킹하고 실제 응답 샘플을 `tests/fixtures/` 에 둔다. 네트워크를 타는 테스트 금지.
- **URL** — 원본 URL 그대로 넘긴다. 정규화(utm 제거 등)와 `url_hash` 는 `pipeline/normalize.py` 담당.
- **webhook 이 있는 소스** (GitHub Releases) — 폴링은 보조다. 두 경로가 같은 `NormalizedItem` 을 만들어야 한다.
- 소스 표(`docs/architecture.md`)를 갱신한다.
