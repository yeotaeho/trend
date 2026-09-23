# 피드백 폴링 잡 — 디스코드 최근 메시지의 👍/👎 리액션을 읽어 feedback 에 반영한다

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.feedback import upsert_feedback
from app.db.models import Feedback, Notification
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.notify.discord import DiscordNotifier, fetch_recent_messages, reaction_verdicts

log = get_logger(__name__)


async def sync_feedback(session: AsyncSession, verdicts: dict[str, str]) -> int:
    """메시지 id → 판정을 feedback 에 쓴다. 돌려주는 값은 바뀐 건수.

    같은 판정을 매번 다시 upsert 하면 created_at 이 폴링마다 밀려 '최근 30일' 창이 어긋난다.
    리액션을 지운 경우는 건드리지 않는다 — 마지막 판정이 남는다.
    """
    if not verdicts:
        return 0
    stmt = (
        select(Notification.message_id, Notification.item_id, Feedback.verdict)
        .outerjoin(
            Feedback,
            (Feedback.item_id == Notification.item_id) & (Feedback.user_id == DEFAULT_USER_ID),
        )
        .where(
            Notification.channel == DiscordNotifier.channel,
            Notification.message_id.in_(list(verdicts)),
        )
    )
    changed = 0
    for message_id, item_id, current in (await session.execute(stmt)).all():
        wanted = verdicts[message_id]
        if wanted != current:
            await upsert_feedback(session, DEFAULT_USER_ID, item_id, wanted, source="discord")
            changed += 1
    return changed


async def run_feedback() -> int:
    """최근 100개 메시지 한 번 읽기. 발송이 하루 5~15건이라 일주일치가 넘게 들어온다."""
    channel_id = get_settings().discord_channel_id
    if not channel_id:
        return 0
    verdicts = reaction_verdicts(await fetch_recent_messages(channel_id))
    async with session_scope() as session:
        changed = await sync_feedback(session, verdicts)
    log.info("feedback.done", reacted=len(verdicts), changed=changed)
    return changed
