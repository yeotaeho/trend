# 기술파악(trend) 보안 리뷰 지침

> security-guidance 플러그인이 모든 LLM 리뷰 프롬프트에 붙이는 프로젝트 규칙이다. 비밀값을 적지 않는다.

## 구조

- 단일 사용자용 서비스다. 백엔드는 FastAPI + APScheduler 한 프로세스이고, Caddy 가 앞에서 TLS 를 끝내고 `app:8000` 으로 넘긴다.
- **레포는 public 이다.** CI 배포 잡도 레포 raw 파일을 인증 없이 받는다. 커밋·이슈·PR 본문에 비밀값·VM 주소·DB 연결 문자열이 들어가면 곧 공개다.
- 외부에서 들어오는 경로는 네 가지다. 모두 **비밀이 비어 있으면 거부하는(fail-closed)** 방식이 기준이다.

| 경로 | 검증 |
|---|---|
| `/api/v1/*` (모바일 앱) | `deps.require_token` — `APP_API_TOKEN` 베어러를 `hmac.compare_digest` 로 비교. 비면 전부 401 |
| `/webhook/discord` | `discord.verify_signature` — `DISCORD_PUBLIC_KEY` Ed25519 서명 |
| `/webhook/telegram` | `X-Telegram-Bot-Api-Secret-Token` 을 `TELEGRAM_WEBHOOK_SECRET` 과 비교 |
| `/webhook/github` | `X-Hub-Signature-256` HMAC-SHA256 (`GITHUB_WEBHOOK_SECRET`) |

## 중점 확인

- 새 엔드포인트가 위 표의 검증을 거치지 않거나, 비밀이 빈 값일 때 통과시키는지. 비교는 `hmac.compare_digest` 여야 한다.
- 수집한 외부 URL 을 서버가 여는 경로(`pipeline/llm.py` 의 `enrich_body`)가 사설·루프백·링크로컬 주소와 그리로 가는 리다이렉트를 막는 가드를 우회하는지. 새로 외부 URL 을 여는 코드도 같은 가드를 써야 한다.
- 수집한 문자열(제목·본문·URL)이 디스코드·텔레그램 메시지에서 마크다운·멘션으로 해석되거나, 검증 안 된 스킴(`javascript:` 등)의 링크가 되는지.
- LLM 호출이 `app/db/budget.py` 의 `reserve_call` 예약 없이 나가는지. 예약 없는 호출은 일일 상한을 무력화한다.
- `.env` 값, `ANTHROPIC_API_KEY`·`VOYAGE_API_KEY`·봇 토큰·`APP_API_TOKEN`·FCM 서비스 계정이 로그(`structlog`)·응답·예외 메시지·`decisions.details` 에 찍히는지.
- SQL 이 문자열 조합으로 만들어지는지. 쿼리는 SQLAlchemy 바인딩으로만 쓴다.

## 알고 있고 수용한 것 (반복 지적하지 않는다)

- 사용자는 한 명이다. `/api/v1` 은 토큰 하나가 `DEFAULT_USER_ID` 에 매핑되는 구조이고, 사용자별 권한 분리가 없는 것은 의도다.
- GHCR 이미지는 public 이다. VM 이 로그인 없이 pull 하기 위한 선택이다. 이미지에 비밀값을 굽지 않는 것이 전제다.
- `/health` 는 인증이 없다. 상태 문자열 외에 아무것도 돌려주지 않는 것이 전제다.
- `.env`·`secrets/`·`caddy_data/`·`.claude/handoff/` 는 커밋하지 않는 파일이다. 스테이징되면 결함이다.
