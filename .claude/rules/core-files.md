---
paths:
  - "app/main.py"
  - "app/config.py"
  - "app/schemas.py"
  - "app/db/**"
  - "app/pipeline/**"
  - "app/notify/policy.py"
  - "config/*.yaml"
  - "pyproject.toml"
  - "docker-compose.yml"
  - "Dockerfile"
  - "Caddyfile"
  - "alembic.ini"
---

# 엔트리·공용 파일 — 수정 전 확인

이 파일들은 여러 모듈이 함께 쓰거나 프로세스 전체를 좌우한다. **지정받은 작업 범위에 포함되지 않았다면 수정 전에 사용자에게 묻는다.** 범위 안이라면 자유롭게 수정하되, 다른 모듈에 미치는 영향을 한 줄로 밝힌다.

- `app/main.py` — FastAPI 앱 + 스케줄러 기동 엔트리.
- `app/config.py` `app/schemas.py` — 설정·스키마. 필드 추가는 YAML·`.env.example` 도 같이.
- `app/db/` `app/pipeline/` — 모든 잡이 공유하는 저장·처리 계층.
- `app/notify/policy.py` — 알림 피로 규칙은 이 한 곳에만 있다.
- `config/*.yaml` — 소스·정책 문장·임계값. 값을 바꾸면 `docs/pipeline.md` 의 수치도 맞춘다.
