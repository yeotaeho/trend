# 디스코드 발송 — Bot API 채널 메시지 + 👍/👎 버튼, 운영 알림

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from app.db.models import Item, Summary
from app.notify.base import RateLimited, feedback_callback_data, relative_time
from app.schemas import Level

API = "https://discord.com/api/v10"
TIMEOUT = httpx.Timeout(15.0)
MAX_CONTENT = 2000  # 디스코드 메시지 본문 상한
EXPLORE_PREFIX = "🧪 실험 · 경계 항목"  # 점수 관문 바로 아래 항목을 하루 1건 보내 라벨을 모은다
MAX_BUTTON_URL = 512  # 링크 버튼 url 상한
RETRY_ATTEMPTS = 3
MAX_RETRY_AFTER = 30.0  # 429 대기가 이보다 길면 재시도하지 않고 실패로 기록한다
GATE_SLACK = 1.0  # 게이트가 이만큼 미만 남았으면 배치를 멈추지 않고 마저 잔다
# 디스코드는 `DiscordBot (url, version)` 형식의 UA 를 요구한다. 없으면 Cloudflare 가 막을 수 있다.
USER_AGENT = "DiscordBot (https://github.com/yeotaeho/trend, 0.1.0)"

# 프로세스 전역 게이트 — 이 시각(monotonic) 전에는 디스코드에 어떤 요청도 보내지 않는다.
# 429 의 retry_after 는 "그 요청" 이 아니라 "다음 요청" 까지의 대기다. 발송·운영 알림이
# 전부 같은 채널 라우트를 쓰므로 global/라우트별 구분 없이 하나로 충분하다.
_blocked_until = 0.0

# 메시지 플래그·컴포넌트 상수 (Discord API v10)
FLAG_SUPPRESS_NOTIFICATIONS = 1 << 12  # @silent — 알림 없이 도착
COMPONENT_ACTION_ROW = 1
COMPONENT_BUTTON = 2
BUTTON_SECONDARY = 2
BUTTON_LINK = 5

# 서식(*_~`|), 링크 마스킹([]()), 줄 머리 헤딩·인용·리스트(# > -)까지. `\-` 는 `-` 로 보인다.
_MD_SPECIAL = re.compile(r"([*_~`|\\\[\]()#>-])")


def escape_md(text: str) -> str:
    """LLM 이 만든 문자열이 디스코드 마크다운으로 해석되지 않게 한다."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def _link_button(url: str) -> dict[str, Any] | None:
    """피드가 준 URL 이 http(s) 가 아니거나 너무 길면 링크 버튼을 뺀다 (디스코드가 400 을 낸다)."""
    if not url.startswith(("http://", "https://")) or len(url) > MAX_BUTTON_URL:
        return None
    return {"type": COMPONENT_BUTTON, "style": BUTTON_LINK, "label": "원문 보기", "url": url}


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
    buttons: list[dict[str, Any] | None] = [
        _link_button(url),
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
    ]
    return [{"type": COMPONENT_ACTION_ROW, "components": [b for b in buttons if b]}]


def build_payload(item: Item, summary: Summary, level: Level, source_name: str) -> dict[str, Any]:
    """네트워크 없이 검증할 수 있게 발송 본문을 따로 만든다."""
    content = render(item, summary, source_name)
    if level is Level.EXPLORE:
        content = f"{EXPLORE_PREFIX}\n\n{content}"[:MAX_CONTENT]
    payload: dict[str, Any] = {
        "content": content,
        "components": components(item.id, item.url),
        # LLM 문자열에 @everyone 이 섞여도 멘션으로 해석되지 않게 한다.
        "allowed_mentions": {"parse": []},
    }
    if level is not Level.PUSH:
        payload["flags"] = FLAG_SUPPRESS_NOTIFICATIONS
    return payload


def _retry_after_seconds(response: httpx.Response) -> float:
    """429 본문의 retry_after(초). 없거나 이상하면 1초. 자르지 않는다 — 디스코드가 준
    시간보다 빨리 같은 요청을 다시 보내면 429 가 반복되고 오류 임계에 걸린다."""
    try:
        return float(response.json().get("retry_after", 1.0))
    except (ValueError, AttributeError, TypeError):
        return 1.0


def _extend_gate(wait: float) -> None:
    """게이트를 뒤로만 민다. 동시에 진행 중이던 요청의 짧은 429 가 앞선 긴 대기를
    덮어써 줄이면 제한 만료 전에 요청이 나간다."""
    global _blocked_until
    _blocked_until = max(_blocked_until, time.monotonic() + wait)


async def _call(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """네트워크 오류·5xx·429 만 재시도한다. 429 는 디스코드가 알려준 시간만큼 기다린다.

    401·403·404 같은 영구 4xx 를 반복하면 디스코드가 봇을 제한할 수 있어 즉시 실패시킨다.
    토큰은 헤더에만 들어가므로 예외 메시지에 새지 않는다. 디스코드 오류 본문은 남긴다.
    """
    headers = {
        "Authorization": f"Bot {get_settings().discord_bot_token}",
        "User-Agent": USER_AGENT,
    }
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        # 매 시도 직전에 본다. 대기하는 사이 다른 요청이 게이트를 더 멀리 세웠을 수 있다.
        remaining = _blocked_until - time.monotonic()
        if remaining > GATE_SLACK:
            raise RateLimited(f"discord 대기 중 ({remaining:.0f}초 남음), 요청 보내지 않음")
        if remaining > 0:
            # 우리 자신의 429 대기가 막 끝난 참이다. asyncio 타이머는 시계 해상도(Windows 약 15ms)
            # 만큼 일찍 깨어나므로 남은 몇 ms 를 마저 자고 간다. 배치를 멈출 일이 아니다.
            await asyncio.sleep(remaining)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(
                    method, f"{API}{path}", json=payload, headers=headers
                )
        except httpx.TransportError:
            if attempt == RETRY_ATTEMPTS:
                raise
            await asyncio.sleep(attempt)
            continue

        status = response.status_code
        if status < 400:
            body: dict[str, Any] = response.json()
            return body
        detail = f"discord {method} {path} HTTP {status}: {response.text[:200]}"
        if status == 429:
            wait = _retry_after_seconds(response)
            _extend_gate(wait)
            if wait > MAX_RETRY_AFTER:
                # 잡을 그만큼 세울 수는 없다. 항목 실패가 아니라 배치 중단 신호를 보낸다 —
                # 게이트가 풀린 뒤 다음 발송 잡이 이 항목부터 다시 시도한다.
                raise RateLimited(f"{detail} (retry_after {wait:.0f}초)")
        elif status >= 500:
            wait = float(attempt)
        else:
            raise RuntimeError(detail)
        if attempt == RETRY_ATTEMPTS:
            if status == 429:
                # 짧은 429 가 반복돼 횟수를 소진한 것도 항목 탓이 아니다. 배치를 멈춘다.
                raise RateLimited(f"{detail} ({attempt}회 429)")
            raise RuntimeError(f"{detail} ({attempt}회 시도)")
        await asyncio.sleep(wait)
    raise AssertionError("unreachable")


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
