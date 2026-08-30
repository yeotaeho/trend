# GitHub 웹훅 — release 이벤트를 서명 검증 후 즉시 items 에 적재

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Source
from app.db.session import session_scope
from app.log import get_logger
from app.pipeline.ingest import store_items
from app.sources.github_release import release_to_item

router = APIRouter(prefix="/webhook")
log = get_logger(__name__)


def verify_signature(body: bytes, signature: str | None) -> bool:
    secret = get_settings().github_webhook_secret
    if not secret or not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, object]:
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="signature mismatch")
    if x_github_event != "release":
        return {"ignored": x_github_event}

    payload = await request.json()
    if payload.get("action") not in ("published", "released"):
        return {"ignored": payload.get("action")}

    repo = payload.get("repository", {}).get("full_name")
    if not repo:
        raise HTTPException(status_code=400, detail="repository 누락")

    async with session_scope() as session:
        source = (
            await session.execute(
                select(Source)
                .where(Source.type == "github_release", Source.enabled.is_(True))
                .order_by(Source.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=503, detail="github_release 소스가 없다")

        item = release_to_item(source.name, repo, payload["release"])
        if item is None:
            return {"ignored": "draft"}
        inserted = await store_items(session, source.id, [item])

    log.info("webhook.github", repo=repo, inserted=len(inserted))
    return {"inserted": len(inserted)}
