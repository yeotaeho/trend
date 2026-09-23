---
paths:
  - "app/notify/**"
  - "app/api/telegram.py"
  - "app/api/discord.py"
  - "app/jobs/notify.py"
  - "app/jobs/feedback.py"
---

# 발송·피드백 규칙

- **Notifier 프로토콜** — `notify/base.py` 의 `send(...) -> message_id`. 채널 어댑터(`telegram.py`, `discord.py`)는 전송만 한다.
- **알림 피로 규칙은 `policy.py` 한 곳** — 강도(`delivery_by_importance`)·하루 push 상한(서로 다른 항목 수)·무음 시간(23:00~08:00 KST, 피드에만)·클러스터 하루 상한(`cluster_daily_cap`, 기본 1). 어댑터나 잡에 이 판단을 복제하지 않는다.
- **발송 기록** — 성공·실패 모두 `notifications` 에 채널마다 한 행 (`channel`, `level`, `message_id`, `error`, `title`). 보내지 않은 기록(피드 전용·`cluster_dup`)은 `channel='app'`. 모든 채널이 실패한 항목만 `FAILED` 다.
- **피드백** — 항목당 1건. 재클릭은 `db/feedback.py` 의 upsert 로 덮어쓴다. 텔레그램 콜백·디스코드 리액션은 `api/` 라우터 또는 `jobs/feedback.py` 폴링이 받아 같은 upsert 를 부른다.
- **웹훅 검증** — 외부에서 들어오는 요청은 시크릿 검증을 생략하지 않는다.
- 발송 정책 수치를 바꾸면 `config/rules.yaml` 과 `docs/pipeline.md` 를 같이 고친다.
