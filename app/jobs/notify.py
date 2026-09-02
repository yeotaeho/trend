# 발송 잡 — SCORED/QUEUED 항목에 정책을 적용해 디스코드로 보내고 결과를 기록

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_rules
from app.db.models import Item, Notification, Source, Summary
from app.db.session import session_scope
from app.log import get_logger
from app.notify.base import Notifier
from app.notify.discord import DiscordNotifier
from app.notify.policy import decide
from app.schemas import ItemStatus, Level

BATCH_SIZE = 20
PENDING = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value)
log = get_logger(__name__)


async def _claim_one(
    session: AsyncSession, skip_ids: set[int]
) -> tuple[Item, Summary, Source] | None:
    """한 건씩 잠근다. 락은 커밋 때 풀리므로 항목 하나가 곧 트랜잭션 하나여야 한다.

    한 번에 20건을 잠그고 루프 안에서 커밋하면 첫 커밋에서 나머지 19건의 락까지
    풀려, 워커를 늘렸을 때 같은 항목이 두 번 발송될 수 있다.
    """
    stmt = (
        select(Item, Summary, Source)
        .join(Summary, Summary.item_id == Item.id)
        .join(Source, Source.id == Item.source_id)
        .where(Item.status.in_(PENDING), Summary.worth_notifying.is_(True))
        .order_by(Summary.importance.desc(), Item.published_at)
        .limit(1)
        .with_for_update(of=Item, skip_locked=True)
    )
    if skip_ids:
        # QUEUED 로 미룬 항목은 여전히 PENDING 이라 그냥 두면 같은 건만 계속 잡는다.
        stmt = stmt.where(Item.id.notin_(skip_ids))
    row = (await session.execute(stmt)).first()
    return (row[0], row[1], row[2]) if row else None


async def run_notify(notifier: Notifier | None = None) -> int:
    """실제로 발송한 건수를 돌려준다."""
    notifier = notifier or DiscordNotifier()
    cfg = get_rules().notify
    now = datetime.now(UTC)
    sent = 0

    async with session_scope() as session:
        visited: set[int] = set()
        for _ in range(BATCH_SIZE):
            claimed = await _claim_one(session, visited)
            if claimed is None:
                break
            item, summary, source = claimed
            visited.add(item.id)

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
                await session.commit()
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
                await session.commit()
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
            # 발송 직후 커밋한다. 배치를 한 트랜잭션으로 묶으면 뒤쪽 한 건이 실패했을 때
            # 이미 발송이 끝난 앞쪽 항목까지 롤백돼 다음 잡에서 다시 발송된다.
            await session.commit()
            sent += 1

    log.info("notify.done", sent=sent)
    return sent
