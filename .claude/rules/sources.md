---
description: 수집기를 새로 만들거나 고칠 때, 특정 소스에서 항목이 안 들어오거나 같은 글이 여러 번 들어올 때, config/sources.yaml 에 소스를 추가·조정할 때.
paths:
  - "app/sources/**"
  - "config/sources.yaml"
  - "tests/sources/**"
---

# 수집기 규칙

**소스 하나 = 파일 하나.** `app/sources/base.py` 의 `Source` 프로토콜(`name`, `fetch(since)`)을 구현하고 `@register` 로 레지스트리에 등록한다. 폴링 주기는 YAML 의 `poll_interval_sec` 이다. 수집기는 `NormalizedItem` 을 내보내는 데서 끝난다. 중복 제거·점수·판정은 파이프라인이 한다.

- **새 소스 추가** — `config/sources.yaml` 에 `type` · `poll_interval_sec` · `trust_score` · `config` 를 등록한다. 같은 매체의 피드 여러 개는 `config.family` 를 같게 둔다 (적재 병합에서 같은 소스로 본다).
- **since 를 못 쓰는 소스** (HN 프론트 페이지처럼 목록을 통째로 주는 API) — 수집기에서 걸러내지 않는다. 아는 URL 은 적재 단계가 `metrics`·`mentions` 로 병합한다.
- **HTTP** — `httpx` + `tenacity` 재시도. 테스트는 `respx` 로 모킹하고 실제 응답 샘플을 `tests/fixtures/` 에 둔다. 네트워크를 타는 테스트 금지.
- **URL** — 원본 URL 그대로 넘긴다. 정규화(utm 제거 등)와 `url_hash` 는 `pipeline/normalize.py` 담당.
- **webhook 이 있는 소스** (GitHub Releases) — 폴링은 보조다. 두 경로가 같은 `NormalizedItem` 을 만들어야 한다.
- 소스 표(`docs/architecture.md`)를 갱신한다.

## 세션에서 배운 것

- **부분 실패에 커서를 전진시키지 않는다.** GitHub Releases 는 `since` 를 일부러 무시하고 매번 최근 릴리즈를 다시 본다. 저장소 하나가 실패해도 `last_polled_at` 이 전진해 그 사이 릴리즈를 영구히 놓친 전례 때문이다. 중복은 `url_hash` 유니크가 막으니 이 동작을 "최적화" 하지 않는다.
- **재시도는 네트워크·429·5xx 만**(`base.retryable`). 401·403·404 를 반복하면 차단을 부르고, 옛 토큰 같은 진짜 원인도 가린다.
- **소스 하나의 실패는 그 소스 안에서 끝낸다.** `fetch` 뿐 아니라 적재(`store_items`)까지 실패 경로에 넣는다. 적재 예외가 새어 `fail_count` 가 오르지 않고 뒤 소스가 전부 멈춘 전례가 있다.
- **외부 문자열 길이를 가정하지 않는다.** arXiv 저자 목록이 `varchar(300)` 을 넘겨 적재가 죽었다. 새 필드는 `text` 로 둔다.
- **새 소스를 붙이기 전에** curl 로 피드가 실제로 있는지와 형식을 본다. Anthropic 은 공식 RSS 가 없어 미러를 `allowed_hosts` 로 묶어 쓴다. 새 소스의 신호(metrics·mentions)가 적재 병합에서 새지 않는지 `pipeline/ingest.py` 를 먼저 읽는다.
- **첫 폴링 백로그를 계산한다.** 새 RSS 첫 폴링은 72h 창만 받는다. 새 소스 여러 개가 동시에 첫 폴링하면 Voyage 429 가 한 번 몰린다.
- **Neon dev 에서 확인한다.** `uv run python scripts/run_job.py sync collect pipeline` 로 소스별 fetched/inserted, 병합 수, 같은 family 의 교차 멘션 0 을 본다.
