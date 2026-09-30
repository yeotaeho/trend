---
description: 알림 발송·재시도·429·무음 시간·하루 상한·클러스터 중복이 이상할 때, 👍/👎 피드백이 기록되지 않을 때, 디스코드·텔레그램·FCM 채널이나 웹훅 코드를 고칠 때.
paths:
  - "app/notify/**"
  - "app/api/telegram.py"
  - "app/api/discord.py"
  - "app/jobs/notify.py"
  - "app/jobs/feedback.py"
---

# 발송·피드백 규칙

- **Notifier 프로토콜** — `notify/base.py` 의 `send(...) -> message_id`. 채널 어댑터(`fcm.py`, `telegram.py`, `discord.py`)는 전송만 한다. FCM 은 무효 토큰 기기 비활성화까지만 한다.
- **알림 피로 규칙은 `policy.py` 한 곳** — 강도(`delivery_by_importance`)·하루 push 상한(서로 다른 항목 수)·무음 시간(23:00~08:00 KST, 피드에만)·클러스터 하루 상한(`cluster_daily_cap`, 기본 1). 어댑터나 잡에 이 판단을 복제하지 않는다.
- **발송 기록** — 성공·실패 모두 `notifications` 에 채널마다 한 행 (`channel`, `level`, `message_id`, `error`, `title`). 보내지 않은 기록(피드 전용·`cluster_dup`)은 `channel='app'`. 모든 채널이 실패한 항목만 `FAILED` 다.
- **피드백** — 항목당 1건. 재클릭은 `db/feedback.py` 의 upsert 로 덮어쓴다. 텔레그램 콜백·디스코드 리액션은 `api/` 라우터 또는 `jobs/feedback.py` 폴링이 받아 같은 upsert 를 부른다.
- **웹훅 검증** — 외부에서 들어오는 요청은 시크릿 검증을 생략하지 않는다.
- 발송 정책 수치를 바꾸면 `config/rules.yaml` 과 `docs/pipeline.md` 를 같이 고친다.

## 세션에서 배운 것

- **429 의 `retry_after` 는 "다음 요청까지" 의 대기다.** 프로세스 전역 게이트(`_blocked_until`)를 `max` 로만 늘리고, 재시도를 다 쓰면 FAILED 가 아니라 `RateLimited` 로 배치를 멈춘다. 이 모양이 잡히는 데 여섯 커밋이 걸렸다. 워커를 늘리면 게이트를 공유 저장소로 옮겨야 한다.
- **부수 작업 실패는 경고만 한다.** 리액션 시드·텔레그램 토스트 응답·운영 알림 실패로 발송을 FAILED 로 만들거나 500 을 돌려주면 재발송·중복 기록이 난다. 본 작업을 먼저 커밋하고 부수 작업은 별도 try 에 둔다.
- **외부 호출 예외 문자열을 그대로 저장·로그하지 않는다.** 텔레그램은 URL 에 봇 토큰이 들어가 `HTTPStatusError` 문자열을 타고 `notifications.error` 와 로그로 샜다.
- **외부 문자열은 적재에서 거른다.** http(s) 가 아닌 링크는 `pipeline/ingest.store_items`(`is_web_url`)가 거부하고, 디스코드 본문은 `escape_md` 로 링크 마스킹·헤딩까지 막는다. `allowed_mentions` 는 멘션만 막는다.
- **"오늘" 은 항목마다 다시 계산한다.** 23:59 에 시작한 발송 잡이 자정을 넘기면 상한 검사 날짜가 어긋난다.
- **같은 판정을 다시 쓰면 `created_at` 을 유지한다.** 밀리면 신뢰도 보정 30일 창과 "최근 판정" 순서가 어긋난다.
- **디스코드 버튼은 공개 HTTPS 엔드포인트가 있어야 도착한다.** 로컬에서는 리액션 폴링(`jobs/feedback.py`)만 동작한다. User-Agent 가 `DiscordBot (<url>, <version>)` 형식이 아니면 Cloudflare 가 1010 으로 막는다.
