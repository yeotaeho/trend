# 디스코드 인터랙션 엔드포인트 — Ed25519 서명 검증 후 PING 응답과 👍/👎 피드백 기록

from __future__ import annotations

import json

from fastapi import APIRouter, Header, HTTPException, Request
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from app.config import get_settings
from app.db.feedback import upsert_feedback
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.notify.base import parse_feedback_callback

router = APIRouter(prefix="/webhook")
log = get_logger(__name__)

# Interaction / InteractionResponse 타입 (Discord API v10)
INTERACTION_PING = 1
INTERACTION_MESSAGE_COMPONENT = 3
RESPONSE_PONG = 1
RESPONSE_CHANNEL_MESSAGE = 4
FLAG_EPHEMERAL = 1 << 6  # 누른 사람에게만 보이는 답장

REPLY = {"useful": "👍 반영했습니다.", "useless": "👎 반영했습니다."}


def verify_signature(public_key_hex: str, signature_hex: str, timestamp: str, body: bytes) -> bool:
    """Discord 가 보낸 요청인지. 메시지 = timestamp + 원문 바디."""
    try:
        VerifyKey(bytes.fromhex(public_key_hex)).verify(
            timestamp.encode() + body, bytes.fromhex(signature_hex)
        )
    except (BadSignatureError, ValueError):
        return False
    return True


def _ephemeral(text: str) -> dict[str, object]:
    return {"type": RESPONSE_CHANNEL_MESSAGE, "data": {"content": text, "flags": FLAG_EPHEMERAL}}


@router.post("/discord")
async def discord_interaction(
    request: Request,
    x_signature_ed25519: str | None = Header(default=None),
    x_signature_timestamp: str | None = Header(default=None),
) -> dict[str, object]:
    body = await request.body()
    public_key = get_settings().discord_public_key
    if (
        not public_key
        or not x_signature_ed25519
        or not x_signature_timestamp
        or not verify_signature(public_key, x_signature_ed25519, x_signature_timestamp, body)
    ):
        raise HTTPException(status_code=401, detail="invalid request signature")

    interaction = json.loads(body)
    kind = interaction.get("type")
    if kind == INTERACTION_PING:
        # Interactions Endpoint URL 을 저장할 때 Discord 가 보내는 확인 요청.
        return {"type": RESPONSE_PONG}
    if kind != INTERACTION_MESSAGE_COMPONENT:
        return _ephemeral("지원하지 않는 상호작용입니다.")

    parsed = parse_feedback_callback(interaction.get("data", {}).get("custom_id") or "")
    if parsed is None:
        return _ephemeral("알 수 없는 버튼입니다.")
    verdict, item_id = parsed

    async with session_scope() as session:
        await upsert_feedback(session, DEFAULT_USER_ID, item_id, verdict, source="discord")

    log.info("webhook.discord_feedback", item_id=item_id, verdict=verdict)
    # 3초 안에 응답해야 한다. 별도 API 호출 없이 응답 본문으로 바로 답한다.
    return _ephemeral(REPLY[verdict])
