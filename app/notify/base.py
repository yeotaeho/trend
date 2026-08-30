# 발송 어댑터 공통 계층 — Notifier 프로토콜

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.db.models import Item, Summary
from app.schemas import Level


@runtime_checkable
class Notifier(Protocol):
    """채널 하나 = 이 프로토콜을 만족하는 객체 하나. 성공 시 message_id 를 돌려준다."""

    channel: str

    async def send(self, item: Item, summary: Summary, level: Level, source_name: str) -> str: ...
