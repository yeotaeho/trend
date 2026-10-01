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

> 독립 사건 둘 이상으로 관찰된 것만 둔다(괄호는 사건 날짜). 한 번 관찰은 `lessons/BANK.md` 에 있다.

- **부분 실패를 성공처럼 처리하지 않는다**(08-30, 09-02). 저장소 하나가 실패해도 `last_polled_at` 이 전진해 그 사이 릴리즈를 영구히 놓쳤고, 적재(`store_items`) 예외가 `fetch` 전용 try 밖으로 새어 `fail_count` 가 오르지 않고 뒤 소스가 멈췄다. 커서·카운터는 소스 전체가 성공했을 때만 움직이고, 적재까지 실패 경로에 넣는다.
- **재시도는 네트워크·429·5xx 만**(`base.retryable`, 09-03, 09-10). 401·403·404 를 반복하면 차단을 부르고, 옛 토큰 같은 진짜 원인도 가린다.
- **새 소스를 붙이기 전에 curl 로 피드가 실제로 있는지와 형식을 본다**(09-02, 09-15). Anthropic 은 공식 RSS 가 없어 미러를 `allowed_hosts` 로 묶어 쓴다.
- **첫 폴링 백로그를 계산한다**(09-02, 09-15). 새 RSS 첫 폴링은 72h 창만 받는다. 새 소스 여러 개가 동시에 첫 폴링하면 Voyage 429 가 한 번 몰린다.
- **Neon dev 에서 확인한다**(09-02, 09-15). `uv run python scripts/run_job.py sync collect pipeline` 로 소스별 fetched/inserted, 병합 수, 같은 family 의 교차 멘션 0 을 본다.
