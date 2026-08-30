# 수집 잡 — 소스 하나를 폴링해 신규 항목을 items 에 적재하고 실패를 기록

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.config import SourceConfig
from app.db.models import Source
from app.db.session import session_scope
from app.log import get_logger
from app.notify.telegram import send_ops_alert
from app.pipeline.ingest import store_items
from app.sources import build_source

FAIL_ALERT_THRESHOLD = 5
log = get_logger(__name__)


async def run_source(source_id: int) -> int:
    """소스 하나를 폴링한다. 돌려주는 값은 새로 적재된 항목 수."""
    async with session_scope() as session:
        source = await session.get(Source, source_id)
        if source is None or not source.enabled:
            return 0

        cfg = SourceConfig(
            name=source.name,
            type=source.type,
            config=source.config,
            poll_interval_sec=source.poll_interval_sec,
            trust_score=source.trust_score,
        )
        try:
            items = await build_source(cfg).fetch(source.last_polled_at)
        except Exception as exc:
            source.fail_count += 1
            source.last_error = f"{type(exc).__name__}: {exc}"
            log.warning(
                "collect.failed", source=source.name, fail_count=source.fail_count, error=str(exc)
            )
            if source.fail_count == FAIL_ALERT_THRESHOLD:
                # 알림 채널이 죽었다고 실패 기록까지 롤백되면 안 된다.
                await session.commit()
                try:
                    await send_ops_alert(f"{source.name} 수집이 연속 {FAIL_ALERT_THRESHOLD}회 실패")
                except Exception as alert_exc:
                    log.warning("collect.alert_failed", error=str(alert_exc))
            return 0

        inserted = await store_items(session, source.id, items)
        source.last_polled_at = datetime.now(UTC)
        source.last_error = None
        source.fail_count = 0
        log.info("collect.done", source=source.name, fetched=len(items), inserted=len(inserted))
        return len(inserted)


async def run_all_sources() -> int:
    """수동 실행·백필용. 활성 소스를 순서대로 한 번씩 돌린다."""
    async with session_scope() as session:
        ids = list(
            (await session.execute(select(Source.id).where(Source.enabled.is_(True)))).scalars()
        )
    total = 0
    for source_id in ids:
        total += await run_source(source_id)
    return total
