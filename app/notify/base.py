# 발송 어댑터 공통 계층 — Notifier 프로토콜·채널 연결 여부와 채널이 공유하는 피드백 콜백·상대 시각

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from app.config import Settings
from app.db.models import Item, Summary
from app.schemas import Level

CALLBACK_PREFIX = "fb"
# 어느 채널로도 보내지 않은 기록(피드 전용·클러스터 억제)의 notifications.channel 값.
APP_CHANNEL = "app"


class RateLimited(RuntimeError):
    """채널이 대기를 요구했다. 항목의 실패가 아니라 "이 배치는 여기서 멈춰라" 는 신호다.

    발송 잡은 이 예외를 받으면 항목을 FAILED 로 기록하지 않고 배치를 끝낸다.
    대기가 끝나면 다음 잡이 같은 항목부터 다시 시도한다.
    """


@runtime_checkable
class Notifier(Protocol):
    """채널 하나 = 이 프로토콜을 만족하는 객체 하나. 성공 시 message_id 를 돌려준다.

    title 은 발송 제목이다 (형제 버전 병기 포함). 모든 채널이 같은 제목을 받는다.
    """

    channel: str

    async def send(
        self, item: Item, summary: Summary, level: Level, source_name: str, *, title: str
    ) -> str: ...


def channel_connected(settings: Settings) -> dict[str, bool]:
    """연결 정보(.env)가 있는 채널. 없는 채널은 켤 수 없고 발송하지 않는다."""
    return {
        "fcm": bool(settings.fcm_project_id and settings.fcm_service_account_file),
        "discord": bool(settings.discord_bot_token and settings.discord_channel_id),
        "telegram": bool(settings.telegram_bot_token and settings.telegram_chat_id),
    }


def feedback_callback_data(verdict: str, item_id: int) -> str:
    """버튼에 실어 보내는 값. 텔레그램 callback_data·디스코드 custom_id 공통."""
    return f"{CALLBACK_PREFIX}:{verdict}:{item_id}"


def parse_feedback_callback(data: str) -> tuple[str, int] | None:
    """`fb:useful:123` → ("useful", 123). 형식이 다르면 None."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX or parts[1] not in ("useful", "useless"):
        return None
    if not parts[2].isdigit():
        return None
    return parts[1], int(parts[2])


def relative_time(published_at: datetime, *, now: datetime | None = None) -> str:
    minutes = int(((now or datetime.now(UTC)) - published_at).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}분 전"
    if minutes < 60 * 24:
        return f"{minutes // 60}시간 전"
    return f"{minutes // (60 * 24)}일 전"
