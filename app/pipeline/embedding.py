# 임베딩 어댑터 — Voyage/OpenAI 호출, 항목 텍스트 조립, 미계산 항목 채우기

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.config import get_settings
from app.db.models import Item
from app.log import get_logger
from app.notify.discord import send_ops_alert

DIM = 1024
MAX_BATCH = 128
SNIPPET_CHARS = 300
TIMEOUT = httpx.Timeout(30.0)
RETRY_ATTEMPTS = 3
RETRY_WAIT = 1.0  # 초. 시도 번호를 곱한다
log = get_logger(__name__)

# 차원 오류는 설정 오류라 고칠 때까지 매 잡마다 난다. 운영 알림은 프로세스당 한 번만 보낸다.
_dim_error_alerted = False


class EmbeddingDimError(RuntimeError):
    """응답 차원·개수·index 가 요청과 다르다. 장애가 아니라 설정 오류라 None 으로 숨기지 않는다."""


def embedding_text(title: str, summary_raw: str | None) -> str:
    """적재 시점에 한 번만 만든다. 보강 뒤 재계산하지 않는다. 벡터는 같은 재료여야 비교가 맞다."""
    snippet = (summary_raw or "")[:SNIPPET_CHARS]
    return f"{title}\n{snippet}" if snippet else title


def needs_embedding() -> ColumnElement[bool]:
    """NULL 이거나 모델이 현재 설정과 다른 행. `!=` 는 NULL 모델을 놓치므로 distinct 를 쓴다."""
    model = get_settings().embedding_model
    return or_(Item.embedding.is_(None), Item.embedding_model.is_distinct_from(model))


def _request(texts: list[str]) -> tuple[str, dict[str, str], dict[str, Any]]:
    """제공자별 (url, headers, json). Voyage 는 공식 문서로 대조했다 (2026-09)."""
    s = get_settings()
    if s.embedding_provider == "openai":
        return (
            "https://api.openai.com/v1/embeddings",
            {"Authorization": f"Bearer {s.openai_api_key}"},
            {"input": texts, "model": s.embedding_model, "dimensions": DIM},
        )
    return (
        "https://api.voyageai.com/v1/embeddings",
        {"Authorization": f"Bearer {s.voyage_api_key}"},
        {
            "input": texts,
            "model": s.embedding_model,
            "output_dimension": DIM,
            "input_type": "document",
        },
    )


def _retry_wait(response: httpx.Response, attempt: int) -> float:
    """429·5xx 의 Retry-After(초) 를 존중한다. 없거나 숫자가 아니면 시도 번호 × RETRY_WAIT."""
    header = response.headers.get("retry-after")
    try:
        return max(0.0, float(header)) if header else RETRY_WAIT * attempt
    except ValueError:
        return RETRY_WAIT * attempt


def _parse_vectors(data: list[dict[str, Any]], expected: int) -> list[list[float]]:
    """index 가 정확히 0..n-1 이어야 한다. 어긋난 대응은 이후 중복 판정을 계속 오염시킨다."""
    indices = sorted(int(r["index"]) for r in data)
    if indices != list(range(expected)):
        raise EmbeddingDimError(f"index 가 0..{expected - 1} 과 다름: {indices[:5]}…")
    rows = sorted(data, key=lambda r: int(r["index"]))
    vectors = [[float(x) for x in r["embedding"]] for r in rows]
    bad = [len(v) for v in vectors if len(v) != DIM]
    if bad:
        raise EmbeddingDimError(f"차원 {bad[0]} (기대 {DIM})")
    return vectors


async def embed(texts: list[str]) -> list[list[float]] | None:
    """텍스트 순서대로 벡터를 돌려준다. 네트워크·5xx·429 만 재시도하고 최종 실패는 None 이다."""
    if len(texts) > MAX_BATCH:
        raise ValueError(f"한 호출 최대 {MAX_BATCH}건")
    if not texts:
        return []
    url, headers, payload = _request(texts)
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TransportError as exc:
            log.warning("embedding.transport_error", attempt=attempt, error=str(exc))
            if attempt == RETRY_ATTEMPTS:
                return None
            await asyncio.sleep(RETRY_WAIT * attempt)
            continue

        if response.status_code < 400:
            return _parse_vectors(response.json()["data"], len(texts))

        retry = response.status_code == 429 or response.status_code >= 500
        log.warning("embedding.http_error", status=response.status_code, attempt=attempt)
        if not retry or attempt == RETRY_ATTEMPTS:
            return None
        await asyncio.sleep(_retry_wait(response, attempt))
    return None


async def alert_dim_error(exc: EmbeddingDimError) -> None:
    """설정 오류 알림. 프로세스당 한 번만 보낸다. 알림 실패는 삼킨다."""
    global _dim_error_alerted
    log.error("embedding.dim_error", error=str(exc))
    if _dim_error_alerted:
        return
    _dim_error_alerted = True
    try:
        await send_ops_alert(f"임베딩 차원 오류: {exc}")
    except Exception as alert_exc:
        log.warning("embedding.alert_failed", error=str(alert_exc))


async def embed_pending(session: AsyncSession, item_ids: list[int] | None = None) -> int:
    """NULL 이거나 모델이 바뀐 항목(주어지면 그 id 안에서)을 최대 MAX_BATCH 건 계산해 저장한다.

    실패하면 NULL 로 남기고 0 을 돌려준다. 다음 잡이 다시 시도한다.
    """
    stmt = (
        select(Item.id, Item.title, Item.summary_raw)
        .where(needs_embedding())
        .order_by(Item.id)
        .limit(MAX_BATCH)
    )
    if item_ids is not None:
        if not item_ids:
            return 0
        stmt = stmt.where(Item.id.in_(item_ids))
    rows = (await session.execute(stmt)).all()
    if not rows:
        return 0

    vectors = await embed([embedding_text(title, body) for _, title, body in rows])
    if vectors is None:
        log.warning("embedding.batch_failed", count=len(rows))
        return 0

    model = get_settings().embedding_model
    for (item_id, _, _), vector in zip(rows, vectors, strict=True):
        await session.execute(
            update(Item).where(Item.id == item_id).values(embedding=vector, embedding_model=model)
        )
    return len(rows)
