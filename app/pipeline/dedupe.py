# 중복·관련 판정 — 72시간 창 안 임베딩 코사인 유사도. 중복은 생존 항목 기준, 관련은 상태 무관

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DedupeConfig
from app.schemas import ItemStatus

_SURVIVED = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value, ItemStatus.SENT.value)
# 버전 토큰 통째로: 16.4.0-canary.14, v1.2.3, 0.12.9. 앞뒤 경계는 공백·괄호·문장 끝.
_VERSION = re.compile(r"(?<![\w.])(v?\d+(?:\.\d+)+(?:[-.][0-9A-Za-z.]+)?)(?![\w.])")

# 쿼리 A — 생존자 중 최댓값 1건. 상위 k 를 먼저 자르고 상태를 거르면 생존 중복을 놓친다.
_DUP_SQL = text(
    """
    WITH q AS (SELECT embedding FROM items WHERE id = :item_id)
    SELECT i.id, i.source_id, i.cluster_id, i.title,
           1 - (i.embedding <=> q.embedding) AS sim
    FROM items i, q
    WHERE i.id <> :item_id
      AND i.embedding IS NOT NULL
      AND i.published_at >= :since
      AND i.status IN :statuses
    ORDER BY sim DESC
    LIMIT 1
    """
).bindparams(bindparam("statuses", expanding=True))

# 쿼리 B — 관련 임계값 이상 전부, 상태·소스 무관. mention_count 와 클러스터 상속에 쓴다.
_RELATED_SQL = text(
    """
    WITH q AS (SELECT embedding FROM items WHERE id = :item_id)
    SELECT i.id, i.source_id, i.cluster_id, i.title,
           1 - (i.embedding <=> q.embedding) AS sim
    FROM items i, q
    WHERE i.id <> :item_id
      AND i.embedding IS NOT NULL
      AND i.published_at >= :since
      AND 1 - (i.embedding <=> q.embedding) >= :related
    ORDER BY sim DESC
    """
)


@dataclass(slots=True, frozen=True)
class Candidate:
    id: int
    source_id: int
    cluster_id: int | None
    title: str
    sim: float


@dataclass(slots=True, frozen=True)
class Verdict:
    kind: Literal["dup", "related", "independent"]
    cluster_id: int
    mention_count: int


def version_tokens(title: str) -> frozenset[str]:
    return frozenset(_VERSION.findall(title))


def _inherit(c: Candidate) -> int:
    # 아직 처리되지 않은 NEW 후보는 cluster_id 가 NULL 이다. 그 항목 자신이 뿌리가 된다.
    return c.cluster_id if c.cluster_id is not None else c.id


def classify(
    *,
    item_id: int,
    own_source_id: int,
    own_title: str,
    dup: Candidate | None,
    related: list[Candidate],
    cfg: DedupeConfig,
) -> Verdict:
    """쿼리 결과만 받아 판정한다. DB 없이 테스트하기 위해 순수 함수다.

    같은 소스의 후속 글도 관련이 맞으니 클러스터 상속에는 쓰고, "여러 소스가 다뤘다" 는
    신호인 mention_count 에서만 자기 소스를 뺀다.
    """
    others = {c.source_id for c in related} - {own_source_id}
    mentions = len(others) + 1

    if dup is not None and dup.sim >= cfg.dup_threshold:
        mine, theirs = version_tokens(own_title), version_tokens(dup.title)
        if not (mine and theirs and mine != theirs):
            return Verdict("dup", _inherit(dup), mentions)
        # 버전이 다르면 같은 릴리즈가 아니다. 관련로 내린다.

    if related:
        best = max(related, key=lambda c: c.sim)
        return Verdict("related", _inherit(best), mentions)
    return Verdict("independent", item_id, mentions)


def _candidate(row: Any) -> Candidate:
    return Candidate(row.id, row.source_id, row.cluster_id, row.title, float(row.sim))


async def find_candidates(
    session: AsyncSession, item_id: int, cfg: DedupeConfig
) -> tuple[Candidate | None, list[Candidate]]:
    """쿼리 A 와 B. 항목의 embedding 이 NULL 이면 두 쿼리 모두 비어 (None, []) 다."""
    since = datetime.now(UTC) - timedelta(hours=cfg.window_hours)
    dup_row = (
        await session.execute(
            _DUP_SQL, {"item_id": item_id, "since": since, "statuses": list(_SURVIVED)}
        )
    ).first()
    related_rows = (
        await session.execute(
            _RELATED_SQL, {"item_id": item_id, "since": since, "related": cfg.related_threshold}
        )
    ).all()
    return (_candidate(dup_row) if dup_row else None, [_candidate(r) for r in related_rows])
