# FCM 기기 등록 — POST /devices, DELETE /devices/{token} (B5)

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.v1.deps import Session, UserId
from app.api.v1.queries.devices import delete_device, register_device
from app.api.v1.schemas.devices import DeviceIn, DeviceOut, Platform

router = APIRouter()


@router.post("/devices", status_code=201, responses={200: {"model": DeviceOut}})
async def post_device(
    body: DeviceIn, session: Session, user_id: UserId, response: Response
) -> DeviceOut:
    """앱 기동·토큰 갱신 때마다 부른다. 새 토큰 201, 이미 있으면 200 (비활성이었으면 다시 활성)."""
    device = await register_device(session, user_id, body.token, body.platform, body.app_version)
    if not device.created:
        response.status_code = 200
    return DeviceOut(
        id=str(device.id), platform=Platform(device.platform), registered_at=device.created_at
    )


@router.delete("/devices/{token}", status_code=204)
async def remove_device(token: str, session: Session, user_id: UserId) -> Response:
    """앱에서 푸시를 끌 때. 없는 토큰이어도 204. 다른 사용자의 토큰은 건드리지 않는다."""
    await delete_device(session, user_id, token)
    return Response(status_code=204)
