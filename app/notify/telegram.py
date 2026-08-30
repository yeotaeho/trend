# 텔레그램 발송 — Bot API sendMessage + 👍/👎 인라인 버튼, 콜백 응답

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.db.models import Item, Summary
from app.schemas import Level

API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = httpx.Timeout(15.0)

CALLBACK_PREFIX = "fb"


def feedback_callback_data(verdict: str, item_id: int) -> str:
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


def render(item: Item, summary: Summary, source_name: str, *, now: datetime | None = None) -> str:
    lines = [
        f"🆕 <b>{escape(summary.title_ko)}</b>",
        escape(summary.summary_ko),
        f"<i>출처: {escape(source_name)} · {relative_time(item.published_at, now=now)}</i>",
    ]
    if summary.tags:
        lines.append(escape(" ".join(f"#{tag}" for tag in summary.tags)))
    return "\n\n".join(lines)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10), reraise=True)
async def _call(method: str, payload: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            API.format(token=settings.telegram_bot_token, method=method), json=payload
        )
        response.raise_for_status()
        body: dict[str, object] = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"telegram {method} 실패: {body.get('description')}")
    return body


class TelegramNotifier:
    channel = "telegram"

    async def send(self, item: Item, summary: Summary, level: Level, source_name: str) -> str:
        payload = {
            "chat_id": get_settings().telegram_chat_id,
            "text": render(item, summary, source_name),
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
            "disable_notification": level is not Level.PUSH,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "원문 보기", "url": item.url},
                        {
                            "text": "👍 유용",
                            "callback_data": feedback_callback_data("useful", item.id),
                        },
                        {
                            "text": "👎 불필요",
                            "callback_data": feedback_callback_data("useless", item.id),
                        },
                    ]
                ]
            },
        }
        body = await _call("sendMessage", payload)
        result = body["result"]
        assert isinstance(result, dict)
        return str(result["message_id"])


async def answer_callback(callback_query_id: str, text: str) -> None:
    """버튼을 누른 사용자에게 토스트로 응답한다."""
    await _call("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})


async def send_ops_alert(text: str) -> None:
    """파이프라인·수집 실패를 봇으로 알린다."""
    await _call("sendMessage", {"chat_id": get_settings().telegram_chat_id, "text": f"⚠️ {text}"})
