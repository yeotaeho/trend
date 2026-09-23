# 기기 등록 통합 테스트 — upsert 새로·기존 구분, 비활성 재등록, 비활성·삭제 기기 발송 제외

from sqlalchemy import delete, select

from app.api.v1.queries.devices import delete_device, register_device
from app.db.models import Device
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID
from app.notify import fcm

TOKEN = "itest-fcm-token"


async def _cleanup() -> None:
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(Device).where(Device.token.like("itest-%")))


async def test_register_upsert_reactivates_and_disable_excludes():
    await _cleanup()
    try:
        async with SessionLocal() as s, s.begin():
            first = await register_device(s, DEFAULT_USER_ID, TOKEN, "android", "0.1.0")
        assert first.created

        await fcm.disable_device(first.id, "fcm HTTP 404 UNREGISTERED")
        assert (first.id, TOKEN) not in await fcm.active_devices(DEFAULT_USER_ID)

        async with SessionLocal() as s, s.begin():
            again = await register_device(s, DEFAULT_USER_ID, TOKEN, "android", "0.1.1")
        assert not again.created
        assert again.id == first.id
        assert (first.id, TOKEN) in await fcm.active_devices(DEFAULT_USER_ID)

        async with SessionLocal() as s:
            row = (await s.execute(select(Device).where(Device.id == first.id))).scalar_one()
        assert row.disabled_at is None and row.last_error is None
        assert row.app_version == "0.1.1"

        async with SessionLocal() as s, s.begin():
            await delete_device(s, DEFAULT_USER_ID, TOKEN)
        assert (first.id, TOKEN) not in await fcm.active_devices(DEFAULT_USER_ID)
    finally:
        await _cleanup()
