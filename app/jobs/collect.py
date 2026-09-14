# 수집 잡 — 소스 하나를 폴링해 신규 항목을 items 에 적재하고 실패를 기록

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import SourceConfig, get_rules
from app.db.models import Source
from app.db.session import session_scope
from app.log import get_logger
from app.notify.discord import send_ops_alert
from app.pipeline.embedding import EmbeddingDimError, alert_dim_error, embed_pending
from app.pipeline.ingest import store_items
from app.sources import build_source

FAIL_ALERT_THRESHOLD = 5
log = get_logger(__name__)


def poll_since(
    last_polled_at: datetime | None, max_age_hours: int, *, now: datetime | None = None
) -> datetime:
    """첫 폴링은 신선도 가드와 같은 창만 본다.

    since 가 None 이면 RSS 수집기가 피드 전체를 돌려주고, 그 백로그는 임베딩까지 한 뒤
    파이프라인의 72h 가드에서 버려진다. 어차피 버릴 항목에 임베딩 예산을 쓰지 않는다.
    """
    return last_polled_at or (now or datetime.now(UTC)) - timedelta(hours=max_age_hours)


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
            since = poll_since(source.last_polled_at, get_rules().scoring.max_age_hours)
            items = await build_source(cfg).fetch(since)
            # 적재 실패도 수집 실패로 다룬다. savepoint 로 감싸야 예외 뒤에도 세션이
            # 살아 있어 아래 실패 기록을 커밋할 수 있다. 예외를 밖으로 흘리면
            # 이 소스의 실패가 기록되지 않고 run_all_sources 의 나머지 소스까지 죽는다.
            savepoint = await session.begin_nested()
            try:
                inserted = await store_items(session, source.id, items)
            except Exception:
                await savepoint.rollback()
                raise
            await savepoint.commit()
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

        embed_error: str | None = None
        if inserted:
            # 임베딩 실패는 수집 실패가 아니다. NULL 로 남기면 파이프라인 잡이 다시 시도한다.
            try:
                await embed_pending(session, inserted)
            except EmbeddingDimError as exc:
                # 설정 오류. 적재는 이미 끝났으니 수집 실패로 롤백하지 않고, 알림과
                # last_error 로 드러낸다. 파이프라인 잡은 같은 오류로 멈춘다.
                await alert_dim_error(exc)
                embed_error = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                log.warning("collect.embed_failed", source=source.name, error=str(exc))

        source.last_polled_at = datetime.now(UTC)
        source.last_error = embed_error
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
