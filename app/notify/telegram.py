# 텔레그램 발송 — Bot API sendMessage + 👍/👎 인라인 버튼, 콜백 응답

from __future__ import annotations

from datetime import datetime
from html import escape

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.db.models import Item, Summary
from app.notify.base import feedback_callback_data, relative_time
from app.schemas import Level

API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = httpx.Timeout(15.0)


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
    """봇 토큰이 URL 에 들어가므로 예외 메시지에 URL 이 새지 않게 갈아끼운다."""
    settings = get_settings()
    url = API.format(token=settings.telegram_bot_token, method=method)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body: dict[str, object] = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"telegram {method} HTTP {exc.response.status_code}") from None
    except httpx.HTTPError as exc:
        raise RuntimeError(f"telegram {method} 요청 실패: {type(exc).__name__}") from None
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
