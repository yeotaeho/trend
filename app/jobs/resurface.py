# 재알림 잡 — 오래 읽지 않은 찜을 한 번 FCM 조용히로 다시 알리고 resurfaced_at 을 남긴다

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.queries.alerts import alert_title, first_delivery
from app.config import get_app_config, get_rules, get_settings
from app.db.models import Bookmark, Item, Summary
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.notify.base import channel_connected
from app.notify.fcm import FcmNotifier
from app.notify.policy import in_quiet_hours

log = get_logger(__name__)


async def _claim(
    session: AsyncSession, user_id: int, saved_before: datetime
) -> tuple[Bookmark, Item] | None:
    """재알림할 찜 한 건을 잠근다. 락은 커밋 때 풀리므로 찜 하나가 곧 트랜잭션 하나다."""
    stmt = (
        select(Bookmark, Item)
        .join(Item, Item.id == Bookmark.item_id)
        .where(
            Bookmark.user_id == user_id,
            Bookmark.is_read.is_(False),
            Bookmark.resurfaced_at.is_(None),
            Bookmark.saved_at <= saved_before,
        )
        .order_by(Bookmark.saved_at, Bookmark.item_id)
        .limit(1)
        .with_for_update(of=Bookmark, skip_locked=True)
    )
    row = (await session.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def _title(session: AsyncSession, user_id: int, item: Item) -> str:
    """피드 카드와 같은 제목 — 발송한 제목 → 요약 제목 → 원문 제목."""
    delivery = first_delivery(user_id)
    row = (
        await session.execute(
            select(delivery.c.title, Summary.title_ko)
            .select_from(Item)
            .outerjoin(delivery, delivery.c.item_id == Item.id)
            .outerjoin(Summary, Summary.item_id == Item.id)
            .where(Item.id == item.id)
        )
    ).one()
    return alert_title(row.title, row.title_ko, item.title)


async def run_resurface(notifier: FcmNotifier | None = None) -> int:
    """보낸 건수를 돌려준다. FCM 이 꺼졌거나 연결 정보가 없거나 무음 시간이면 아무것도 안 한다.

    notifications 에 남기지 않으므로 피드·통계·push 상한에 들어가지 않는다. 발송 실패는
    기기·네트워크 문제라 다음 찜도 실패하므로 회차를 멈춘다. 그 찜은 resurfaced_at 을
    남기지 않아 다음 회차에 다시 시도한다.
    """
    cfg = get_rules().notify
    if not (cfg.channels.fcm and channel_connected(get_settings())["fcm"]):
        return 0
    now = datetime.now(UTC)
    if in_quiet_hours(cfg, now):
        return 0
    saved_before = now - timedelta(days=get_app_config().resurface_unread_after_days)
    notifier = notifier or FcmNotifier()
    sent = 0
    while True:
        async with session_scope() as session:
            claimed = await _claim(session, DEFAULT_USER_ID, saved_before)
            if claimed is None:
                break
            bookmark, item = claimed
            try:
                await notifier.send_resurface(item, await _title(session, DEFAULT_USER_ID, item))
            except Exception as exc:
                log.warning("resurface.failed", item_id=item.id, error=str(exc))
                break
            bookmark.resurfaced_at = datetime.now(UTC)
            sent += 1
    if sent:
        log.info("resurface.sent", count=sent)
    return sent
