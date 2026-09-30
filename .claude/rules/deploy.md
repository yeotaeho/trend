---
description: 배포가 실패하거나 운영에 반영되지 않을 때, GitHub Actions·GHCR 이미지·VM·Caddy·인증서·운영 .env 를 보거나 고칠 때, 롤백할 때. 배포 파일 수정은 가드 훅이 확인을 요청한다.
paths:
  - "Dockerfile"
  - ".dockerignore"
  - "docker-compose.yml"
  - "Caddyfile"
  - ".github/**"
  - ".env.example"
---

# 배포·CI 규칙

**main 머지가 곧 운영 배포다.** `.github/workflows/ci.yml` 은 PR·main push 에 `check`(ruff check·format·mypy·pytest)를 돌리고, main 이면 `deploy` 로 GHCR 이미지(`:latest` + `:<SHA>`)를 올린 뒤 VM 에서 같은 SHA 의 compose·Caddyfile 을 받아 `up -d --wait` 와 caddy reload 를 한다. 컨테이너가 뜰 때 `alembic upgrade head` 가 돈다. 배포 뒤 확인 절차는 스킬 `deploy-verify` 다.

## 바꿀 때 지킬 것

- **Caddyfile 은 같은 inode 에 덮어쓴다.** 파일 바인드 마운트라 `mv` 로 갈아 끼우면 실행 중인 caddy 는 옛 inode 를 보고 reload 가 헛돈다. compose 파일은 `mv` 로 원자적 교체가 맞다.
- **롤백 대상은 SHA 태그다.** `IMAGE_TAG=<SHA>` 로 pull·up 한다(`docker-compose.yml` 머리 주석). `:latest` 만 있으면 되돌릴 이미지가 없다.
- **이미지 이름이 owner 기준이다**(`ghcr.io/${{ github.repository_owner }}/tech-radar`). 같은 owner 의 복제 레포(예 `yeotaeho/trend-2`)가 main 에 push 하면 운영 `:latest` 를 덮는다. 복제 레포의 deploy 잡에는 `github.repository == 'yeotaeho/trend'` 가드가 있어야 한다.
- **시크릿은 `VM_HOST`·`VM_USER`·`VM_SSH_KEY` 셋이다.** `GITHUB_` 접두사는 저장소 시크릿 이름으로 쓸 수 없고, GHCR 푸시는 자동 `GITHUB_TOKEN` 이 한다. 앱 키는 VM 의 `~/tech-radar/.env` 에만 있다. `.env.example` 에 키를 더하면 VM `.env` 에도 넣어야 한다고 사용자에게 알린다.
- **이미지에 비밀값을 굽지 않는다.** GHCR 패키지는 public 이다.
- alembic 실패 시 재시작 루프는 의도다(일시적 Neon 장애에서 스스로 복구). 영구 실패는 `IMAGE_TAG` 롤백으로 되돌린다.

## 운영 함정

- **운영 컨테이너가 떠 있을 때 로컬 스케줄러를 같은 DB 로 돌리지 않는다.** 스케줄러가 둘이면 중복 발송된다. 로컬은 `SCHEDULER_ENABLED=false` 로 띄우거나 Neon `dev` 를 쓴다.
- **디스코드 버튼(인터랙션)은 공개 HTTPS 엔드포인트가 있어야 도착한다.** 로컬에서는 버튼 피드백을 시험할 수 없다. 디스코드는 Interactions Endpoint 를 저장할 때 정상 PING 과 위조 서명 요청을 둘 다 보낸다.
- **DNS 없이 ACME 가 반복 실패하면 Caddy 가 스테이징 인증서로 내려간다.** DNS 를 넣은 뒤 `docker compose restart caddy` 로 상태를 초기화한다.
- **GitHub 장애 때 run 이 queued 로 굳으면** cancel·rerun 이 거부된다. githubstatus 를 보고, 풀리면 `workflow_dispatch`(`gh workflow run ci --ref main`)로 새 실행을 만든다.
- **비용이 드는 외부 조작**(VM 생성·자동 백업·유료 옵션)과 비밀키·DNS·시크릿 입력은 사용자가 한다. Claude 는 구성까지만 하고 멈춘다.
