# 임베딩 어댑터 — Voyage/OpenAI 호출, 항목 텍스트 조립, 미계산 항목 채우기

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Item
from app.log import get_logger

DIM = 1024
MAX_BATCH = 128
SNIPPET_CHARS = 300
TIMEOUT = httpx.Timeout(30.0)
RETRY_ATTEMPTS = 3
RETRY_WAIT = 1.0  # 초. 시도 번호를 곱한다
log = get_logger(__name__)


class EmbeddingDimError(RuntimeError):
    """응답 차원이 DIM 과 다르다. 장애가 아니라 설정 오류라 None 으로 숨기지 않는다."""


def embedding_text(title: str, summary_raw: str | None) -> str:
    """적재 시점에 한 번만 만든다. 보강 뒤 재계산하지 않는다. 벡터는 같은 재료여야 비교가 맞다."""
    snippet = (summary_raw or "")[:SNIPPET_CHARS]
    return f"{title}\n{snippet}" if snippet else title


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
        return float(header) if header else RETRY_WAIT * attempt
    except ValueError:
        return RETRY_WAIT * attempt


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
            rows = sorted(response.json()["data"], key=lambda r: int(r["index"]))
            vectors = [[float(x) for x in r["embedding"]] for r in rows]
            bad = [len(v) for v in vectors if len(v) != DIM]
            if bad or len(vectors) != len(texts):
                raise EmbeddingDimError(
                    f"차원 {bad[:1] or '?'} 또는 개수 {len(vectors)}/{len(texts)} 가 맞지 않음"
                )
            return vectors

        retry = response.status_code == 429 or response.status_code >= 500
        log.warning("embedding.http_error", status=response.status_code, attempt=attempt)
        if not retry or attempt == RETRY_ATTEMPTS:
            return None
        await asyncio.sleep(_retry_wait(response, attempt))
    return None


async def embed_pending(session: AsyncSession, item_ids: list[int] | None = None) -> int:
    """NULL 이거나 모델이 바뀐 항목(주어지면 그 id 안에서)을 최대 MAX_BATCH 건 계산해 저장한다.

    실패하면 NULL 로 남기고 0 을 돌려준다. 다음 잡이 다시 시도한다.
    """
    model = get_settings().embedding_model
    stmt = (
        select(Item.id, Item.title, Item.summary_raw)
        # NULL 이거나 모델이 바뀐 행. 모델 교체 중엔 불일치 행이 남아 있는 동안 파이프라인이 멈춘다.
        .where(or_(Item.embedding.is_(None), Item.embedding_model != model))
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

    for (item_id, _, _), vector in zip(rows, vectors, strict=True):
        await session.execute(
            update(Item).where(Item.id == item_id).values(embedding=vector, embedding_model=model)
        )
    return len(rows)
