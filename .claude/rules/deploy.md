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

> 구성 사실과 결정만 둔다. Caddyfile 을 `mv` 대신 같은 inode 에 덮어쓰는 이유는 `ci.yml` 주석에, 한 번 관찰된 운영 함정은 `lessons/BANK.md` 와 스킬 `deploy-verify` 의 "막혔을 때" 표에 있다.

- **롤백 대상은 SHA 태그다.** `IMAGE_TAG=<SHA>` 로 pull·up 한다(`docker-compose.yml` 머리 주석). `:latest` 만 있으면 되돌릴 이미지가 없다.
- **시크릿은 `VM_HOST`·`VM_USER`·`VM_SSH_KEY` 셋이다.** `GITHUB_` 접두사는 저장소 시크릿 이름으로 쓸 수 없고, GHCR 푸시는 자동 `GITHUB_TOKEN` 이 한다. 앱 키는 VM 의 `~/tech-radar/.env` 에만, 파일로 된 비밀(FCM 서비스 계정 JSON)은 `~/tech-radar/secrets/` 에만 있다. 이 폴더는 컨테이너 `/run/secrets` 에 읽기 전용으로 붙는다. `.env.example` 에 키를 더하면 VM `.env` 에도 넣어야 한다고 사용자에게 알린다.
- **이미지에 비밀값을 굽지 않는다.** GHCR 패키지는 public 이다.
- alembic 실패 시 재시작 루프는 의도다(일시적 Neon 장애에서 스스로 복구). 영구 실패는 `IMAGE_TAG` 롤백으로 되돌린다.

## 운영

- **비용이 드는 외부 조작**(VM 생성·자동 백업·유료 옵션)과 비밀키·DNS·시크릿 입력은 사용자가 한다. Claude 는 구성까지만 하고 멈춘다.
