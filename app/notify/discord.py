# 디스코드 발송 — Bot API 채널 메시지 + 👍/👎 버튼, 운영 알림

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.db.models import Item, Summary
from app.notify.base import feedback_callback_data, relative_time
from app.schemas import Level

API = "https://discord.com/api/v10"
TIMEOUT = httpx.Timeout(15.0)
MAX_CONTENT = 2000  # 디스코드 메시지 본문 상한

# 메시지 플래그·컴포넌트 상수 (Discord API v10)
FLAG_SUPPRESS_NOTIFICATIONS = 1 << 12  # @silent — 알림 없이 도착
COMPONENT_ACTION_ROW = 1
COMPONENT_BUTTON = 2
BUTTON_SECONDARY = 2
BUTTON_LINK = 5

_MD_SPECIAL = re.compile(r"([*_~`|\\])")


def escape_md(text: str) -> str:
    """LLM 이 만든 문자열이 디스코드 마크다운으로 해석되지 않게 한다."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def render(item: Item, summary: Summary, source_name: str, *, now: datetime | None = None) -> str:
    lines = [
        f"🆕 **{escape_md(summary.title_ko)}**",
        escape_md(summary.summary_ko),
        f"*출처: {escape_md(source_name)} · {relative_time(item.published_at, now=now)}*",
    ]
    if summary.tags:
        lines.append(escape_md(" ".join(f"#{tag}" for tag in summary.tags)))
    return "\n\n".join(lines)[:MAX_CONTENT]


def components(item_id: int, url: str) -> list[dict[str, Any]]:
    return [
        {
            "type": COMPONENT_ACTION_ROW,
            "components": [
                {"type": COMPONENT_BUTTON, "style": BUTTON_LINK, "label": "원문 보기", "url": url},
                {
                    "type": COMPONENT_BUTTON,
                    "style": BUTTON_SECONDARY,
                    "label": "👍 유용",
                    "custom_id": feedback_callback_data("useful", item_id),
                },
                {
                    "type": COMPONENT_BUTTON,
                    "style": BUTTON_SECONDARY,
                    "label": "👎 불필요",
                    "custom_id": feedback_callback_data("useless", item_id),
                },
            ],
        }
    ]


def build_payload(item: Item, summary: Summary, level: Level, source_name: str) -> dict[str, Any]:
    """네트워크 없이 검증할 수 있게 발송 본문을 따로 만든다."""
    payload: dict[str, Any] = {
        "content": render(item, summary, source_name),
        "components": components(item.id, item.url),
        # LLM 문자열에 @everyone 이 섞여도 멘션으로 해석되지 않게 한다.
        "allowed_mentions": {"parse": []},
    }
    if level is not Level.PUSH:
        payload["flags"] = FLAG_SUPPRESS_NOTIFICATIONS
    return payload


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10), reraise=True)
async def _call(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """토큰은 헤더에만 들어가므로 예외 메시지에 새지 않는다. 디스코드 오류 본문은 남긴다."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.request(
            method,
            f"{API}{path}",
            json=payload,
            headers={"Authorization": f"Bot {settings.discord_bot_token}"},
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"discord {method} {path} HTTP {response.status_code}: {response.text[:200]}"
        )
    body: dict[str, Any] = response.json()
    return body


class DiscordNotifier:
    channel = "discord"

    async def send(self, item: Item, summary: Summary, level: Level, source_name: str) -> str:
        channel_id = get_settings().discord_channel_id
        body = await _call(
            "POST",
            f"/channels/{channel_id}/messages",
            build_payload(item, summary, level, source_name),
        )
        return str(body["id"])


async def send_ops_alert(text: str) -> None:
    """파이프라인·수집 실패를 같은 채널로 알린다."""
    channel_id = get_settings().discord_channel_id
    await _call(
        "POST",
        f"/channels/{channel_id}/messages",
        {"content": f"⚠️ {escape_md(text)}", "allowed_mentions": {"parse": []}},
    )
