# 텔레그램 웹훅 — 인라인 버튼 콜백을 feedback 테이블에 기록

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.db.models import Feedback
from app.db.session import session_scope
from app.log import get_logger
from app.notify.telegram import answer_callback, parse_feedback_callback

router = APIRouter(prefix="/webhook")
log = get_logger(__name__)

REPLY = {"useful": "👍 반영했습니다.", "useless": "👎 반영했습니다."}


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, object]:
    secret = get_settings().telegram_webhook_secret
    if not secret or not hmac.compare_digest(secret, x_telegram_bot_api_secret_token or ""):
        raise HTTPException(status_code=401, detail="secret token mismatch")

    update = await request.json()
    query = update.get("callback_query")
    if not query:
        return {"ignored": "not_callback"}

    parsed = parse_feedback_callback(query.get("data") or "")
    if parsed is None:
        return {"ignored": "unknown_callback"}
    verdict, item_id = parsed

    async with session_scope() as session:
        session.add(Feedback(item_id=item_id, verdict=verdict))

    await answer_callback(query["id"], REPLY[verdict])
    log.info("webhook.telegram_feedback", item_id=item_id, verdict=verdict)
    return {"item_id": item_id, "verdict": verdict}
