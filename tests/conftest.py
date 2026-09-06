# 테스트 공통 설정 — app 임포트 전에 필수 환경변수를 채운다

from __future__ import annotations

import os
from pathlib import Path

# 통합 테스트(tests/integration)는 TEST_DATABASE_URL 의 Neon dev 브랜치를 같은 엔진으로 쓴다.
# 셸에 DATABASE_URL(운영) 이 있어도 TEST_DATABASE_URL 이 이긴다. 테스트가 운영 DB 를 보면 안 된다.
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "1")
# 환경변수가 .env 보다 우선하므로 실제 키가 테스트에 섞이지 않는다.
os.environ.setdefault("DISCORD_BOT_TOKEN", "test-discord-token")
os.environ.setdefault("DISCORD_CHANNEL_ID", "42")
os.environ.setdefault("DISCORD_PUBLIC_KEY", "")
os.environ.setdefault("VOYAGE_API_KEY", "test-voyage-key")

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
