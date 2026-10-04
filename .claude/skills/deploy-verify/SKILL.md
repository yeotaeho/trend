---
name: deploy-verify
description: main 머지·PR 머지 뒤 운영 배포가 됐는지 확인하거나, 배포가 실패·지연될 때, 운영에서 안 된다는 보고를 받았을 때, 이미지를 롤백하거나 수동 배포할 때 쓴다. Actions run 판독, VM 컨테이너·로그, 헬스·웹훅 스모크, 인증서, 롤백 절차.
---

# 운영 배포 확인

> 도메인은 `trend.yeotaeho.kr`, VM 의 배포 폴더는 `~/tech-radar`(코드 없음, `.env`·`secrets/`(FCM 서비스 계정) 와 배포 SHA 의 compose·Caddyfile 만)다. VM 접속 정보는 GitHub 시크릿 `VM_HOST`·`VM_USER` 와 같다. 레포가 public 이라 IP 를 파일에 적지 않는다.

## 절차

1. **Actions run** — `gh run list --workflow ci --limit 5` 또는 Actions 화면에서 `check` → `docker/build-push-action` → `Deploy to VM` 이 모두 초록인지 본다. `Deploy to VM` 이 실패하면 run 로그의 `docker compose logs --tail 80 app` 출력부터 읽는다.
2. **바깥에서 스모크** — 이 PC 에서 바로 돌린다.
   ```bash
   curl -s -w " %{http_code}\n" https://trend.yeotaeho.kr/health                             # {"status":"ok"} 200
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://trend.yeotaeho.kr/webhook/discord  # 401
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://trend.yeotaeho.kr/webhook/github   # 401
   curl -s -o /dev/null -w "%{http_code}\n" https://trend.yeotaeho.kr/api/v1/meta              # 401 (토큰 없음)
   curl -s -o /dev/null -w "%{http_code}\n" http://trend.yeotaeho.kr/health                    # 308
   echo | openssl s_client -connect trend.yeotaeho.kr:443 -servername trend.yeotaeho.kr 2>/dev/null | openssl x509 -noout -issuer -enddate   # Let's Encrypt 운영 발급자(STAGING 아님)
   ```
   인증서는 openssl 로 본다. 이 PC 의 curl 은 Schannel 이라 `-v` 에 issuer 를 찍지 않아, `curl -svI | grep issuer` 는 스테이징 인증서여도 빈 출력으로 통과처럼 보인다(10-04 확인). 발급자 줄이 안 나오면 실패로 본다.
3. **VM 안** — SSH 가 되면 직접, 안 되면 아래를 사용자에게 준다. 첫 줄은 항상 `cd ~/tech-radar` 다.
   ```bash
   cd ~/tech-radar && docker compose ps                                   # app·caddy 모두 healthy
   docker compose logs --since 30m app | grep -E "collect.done|pipeline.done|notify.done|error" | tail -40
   docker compose images app                                              # 태그가 배포 SHA 인지
   ```
   기동 직후에는 소스별 `collect.done` 이 한 번씩 찍혀야 한다(`next_run_time=now`).
4. **스케줄러가 하나인지** — 로컬에서 운영 DB 로 uvicorn 이 떠 있지 않은지 본다. 둘이면 중복 발송된다.
5. **피드백 경로** — 필요할 때만, 사용자가 디스코드 카드에 👍 를 눌러 `feedback` 행과 로그 `webhook.discord_feedback` 를 확인한다.

## 롤백·수동 배포

```bash
cd ~/tech-radar
IMAGE_TAG=<되돌릴 커밋 SHA> docker compose pull
IMAGE_TAG=<되돌릴 커밋 SHA> docker compose up -d --wait --wait-timeout 150
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile
```

- compose·Caddyfile 을 손으로 받을 때는 같은 SHA 의 raw 파일을 쓰고, Caddyfile 은 `cat 새파일 > Caddyfile` 로 inode 를 유지한다.
- 롤백은 운영 조작이다. 사용자 승인을 받고 실행한다.
- **마지막 마이그레이션보다 앞 SHA 로는 되돌리지 않는다.** `app/db/alembic/versions/` 의 가장 큰 리비전(10-04 기준 `0005` settings_revisions)이 들어간 커밋 이후 SHA 만 된다. 그 이전 이미지에는 DB 에 적힌 리비전 파일이 없어 `alembic upgrade head` 가 `Can't locate revision identified by '0005'` 로 실패하고 컨테이너가 재시작을 반복한다(10-04 dev 에서 확인). 더 앞으로 가야 하면 지금 이미지에서 먼저 `docker compose exec -T app alembic downgrade 0004` 로 내린다. 설정 이력이 사라진다.

## 막혔을 때

| 증상 | 먼저 볼 것 |
|---|---|
| run 이 `queued` 에서 안 움직임 | githubstatus. 풀리면 `gh workflow run ci --ref main` 으로 새 실행 |
| `Deploy to VM` 이 인증 실패 | `VM_SSH_KEY` 시크릿 내용(끝 줄바꿈 포함) |
| 인증서가 스테이징 | DNS A 레코드를 여러 리졸버(8.8.8.8·9.9.9.9)로 확인한 뒤 `docker compose restart caddy` |
| 컨테이너가 재시작 반복 | `docker compose logs app` 의 alembic 오류. 일시 장애면 스스로 복구, 영구면 롤백 |
| 새 설정 키가 안 먹음 | VM `~/tech-radar/.env` 에 키가 있는지(`.env.example` 만 바뀐 경우) |
| 디스코드 버튼 "앱이 적시에 응답하지 않았습니다" | Interactions Endpoint URL 등록 여부와 앱 로그의 `POST /webhook/discord` |
