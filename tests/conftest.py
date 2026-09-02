# 테스트 공통 설정 — app 임포트 전에 필수 환경변수를 채운다

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "1")
# 환경변수가 .env 보다 우선하므로 실제 키가 테스트에 섞이지 않는다.
os.environ.setdefault("DISCORD_BOT_TOKEN", "test-discord-token")
os.environ.setdefault("DISCORD_CHANNEL_ID", "42")
os.environ.setdefault("DISCORD_PUBLIC_KEY", "")

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
