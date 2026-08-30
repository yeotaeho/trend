# 발송 잡 — SCORED/QUEUED 항목에 정책을 적용해 텔레그램으로 보내고 결과를 기록

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_rules
from app.db.models import Item, Notification, Source, Summary
from app.db.session import session_scope
from app.log import get_logger
from app.notify.base import Notifier
from app.notify.policy import decide
from app.notify.telegram import TelegramNotifier
from app.schemas import ItemStatus, Level

BATCH_SIZE = 20
PENDING = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value)
log = get_logger(__name__)


async def _claim_batch(session: AsyncSession) -> list[tuple[Item, Summary, Source]]:
    """중요한 것부터 보낸다. 같은 중요도면 오래된 것 먼저."""
    stmt = (
        select(Item, Summary, Source)
        .join(Summary, Summary.item_id == Item.id)
        .join(Source, Source.id == Item.source_id)
        .where(Item.status.in_(PENDING), Summary.worth_notifying.is_(True))
        .order_by(Summary.importance.desc(), Item.published_at)
        .limit(BATCH_SIZE)
        .with_for_update(of=Item, skip_locked=True)
    )
    return [
        (item, summary, source) for item, summary, source in (await session.execute(stmt)).all()
    ]


async def run_notify(notifier: Notifier | None = None) -> int:
    """실제로 발송한 건수를 돌려준다."""
    notifier = notifier or TelegramNotifier()
    cfg = get_rules().notify
    now = datetime.now(UTC)
    sent = 0

    async with session_scope() as session:
        for item, summary, source in await _claim_batch(session):
            verdict = await decide(session, cfg, importance=summary.importance, now=now)

            if verdict.level is None:
                if verdict.reason == "feed_only":
                    # 발송하지 않고 이력만 남긴다.
                    session.add(
                        Notification(
                            item_id=item.id, channel=notifier.channel, level=Level.FEED.value
                        )
                    )
                    item.status = ItemStatus.SENT.value
                else:
                    item.status = ItemStatus.QUEUED.value
                    log.info("notify.deferred", item_id=item.id, reason=verdict.reason)
                continue

            try:
                message_id = await notifier.send(item, summary, verdict.level, source.name)
            except Exception as exc:
                session.add(
                    Notification(
                        item_id=item.id,
                        channel=notifier.channel,
                        level=verdict.level.value,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                item.status = ItemStatus.FAILED.value
                log.warning("notify.failed", item_id=item.id, error=str(exc))
                continue

            session.add(
                Notification(
                    item_id=item.id,
                    channel=notifier.channel,
                    level=verdict.level.value,
                    message_id=message_id,
                )
            )
            item.status = ItemStatus.SENT.value
            sent += 1

    log.info("notify.done", sent=sent)
    return sent
