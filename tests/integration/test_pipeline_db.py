# 파이프라인 2국면 통합 테스트 — 항목 실패 2회 DROPPED, 기반 실패는 행 없이 NEW, 재사용, topics

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.config import get_rules
from app.db.models import Decision, Item, LlmCall, Source
from app.db.session import SessionLocal
from app.jobs import pipeline
from app.pipeline.triage import TRIAGE_PROMPT_VERSION, TriageBatch, TriageItem
from app.schemas import Kind


@pytest.fixture
async def items():
    """소스 하나와 NEW 항목 3건. 끝나면 지운다."""
    now = datetime.now(UTC)
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:pipeline", type="rss", config={})
        s.add(src)
        await s.flush()
        rows = [
            Item(
                source_id=src.id,
                external_id=f"p{i}",
                url=f"https://t/p{i}",
                url_normalized=f"https://t/p{i}",
                url_hash=f"pl-{i}",
                title=f"item {i}",
                published_at=now,
            )
            for i in range(3)
        ]
        s.add_all(rows)
        await s.flush()
        ids = [r.id for r in rows]
        src_id = src.id
    yield ids, src_id
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(Item).where(Item.id.in_(ids)))
        await s.execute(delete(Source).where(Source.id == src_id))
        await s.execute(delete(LlmCall))


async def _load(ids):
    """열린 세션과 (Item, Source) 쌍을 돌려준다. 호출자가 `async with s:` 로 닫는다.

    여기서 `async with SessionLocal()` 로 감싸면 반환 시점에 세션이 닫혀, 뒤이은 commit 이 무시된다.
    """
    s = SessionLocal()
    rows = (
        await s.execute(
            select(Item, Source).join(Source, Source.id == Item.source_id).where(Item.id.in_(ids))
        )
    ).all()
    return s, [(i, src) for i, src in rows]


def _eager():
    """3건으로 호출 경로를 보는 테스트용. 모으기 대기를 끈다."""
    rules = get_rules()
    return rules.model_copy(update={"triage": rules.triage.model_copy(update={"min_batch": 1})})


async def test_few_fresh_items_wait_without_a_call(items, monkeypatch):
    ids, _ = items
    calls: list[int] = []

    async def fake_triage(_rules, entries):
        calls.append(len(entries))
        return TriageBatch(
            items=[
                TriageItem(idx=e.idx, relevance=0.4, reason="r", kind=Kind.NEWS, topics=[])
                for e in entries
            ]
        )

    monkeypatch.setattr(pipeline, "call_triage", fake_triage)
    s, survivors = await _load(ids)
    async with s:
        # 기본값은 10건·60분. 방금 들어온 3건은 기다린다.
        result = await pipeline._triage(s, get_rules(), survivors)
        await s.commit()

    async with SessionLocal() as s:
        decisions = (
            (await s.execute(select(Decision).where(Decision.item_id.in_(ids)))).scalars().all()
        )
        statuses = [(await s.get(Item, i)).status for i in ids]
    assert result == {} and calls == [] and decisions == [] and statuses == ["NEW"] * 3


async def test_item_failure_twice_drops_only_that_item(items, monkeypatch):
    ids, _ = items
    rules = _eager()

    async def fake_triage(_rules, entries):
        # 첫 항목만 relevance 범위 밖(항목 실패), 나머지 정상. 개수·idx 는 맞아 배치 실패가 아니다.
        return TriageBatch(
            items=[
                TriageItem(
                    idx=e.idx,
                    relevance=5.0 if e.idx == ids[0] else 0.5,
                    reason="r",
                    kind=Kind.NEWS,
                    topics=[],
                )
                for e in entries
            ]
        )

    monkeypatch.setattr(pipeline, "call_triage", fake_triage)

    for _ in range(2):
        s, survivors = await _load(ids)
        async with s:
            await pipeline._triage(s, rules, survivors)
            await s.commit()

    async with SessionLocal() as s:
        first = await s.get(Item, ids[0])
        others = [await s.get(Item, i) for i in ids[1:]]
        errors = (
            (
                await s.execute(
                    select(Decision).where(
                        Decision.item_id == ids[0],
                        Decision.stage == "triage",
                        Decision.passed.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        calls = (await s.execute(select(LlmCall))).scalars().all()
    assert first.status == "DROPPED" and len(errors) == 2
    assert all(o.status == "NEW" for o in others)
    assert len(calls) == 2  # 호출마다 예약 행 하나


async def test_infra_failure_leaves_no_decision_rows(items, monkeypatch):
    ids, _ = items
    rules = _eager()

    async def boom(_rules, entries):
        raise RuntimeError("network")

    monkeypatch.setattr(pipeline, "call_triage", boom)
    s, survivors = await _load(ids)
    async with s:
        result = await pipeline._triage(s, rules, survivors)
        await s.commit()

    async with SessionLocal() as s:
        decisions = (
            (await s.execute(select(Decision).where(Decision.item_id.in_(ids)))).scalars().all()
        )
        statuses = [(await s.get(Item, i)).status for i in ids]
    assert result == {} and decisions == [] and statuses == ["NEW"] * 3


async def test_existing_relevance_is_reused_without_a_call(items, monkeypatch):
    ids, _ = items
    rules = _eager()
    async with SessionLocal() as s, s.begin():
        s.add(
            Decision(
                item_id=ids[0],
                stage="triage",
                passed=True,
                details={"relevance": 0.7, "reason": "이전 결과", "batch_id": "x"},
            )
        )

    calls: list[int] = []

    async def fake_triage(_rules, entries):
        calls.append(len(entries))
        return TriageBatch(
            items=[
                TriageItem(idx=e.idx, relevance=0.4, reason="r", kind=Kind.NEWS, topics=[])
                for e in entries
            ]
        )

    monkeypatch.setattr(pipeline, "call_triage", fake_triage)
    s, survivors = await _load(ids)
    async with s:
        result = await pipeline._triage(s, rules, survivors)
        await s.commit()

    assert result[ids[0]].relevance == 0.7  # 재사용
    # kind·topics 도입 전 행이다. 중립값으로 채우고 다시 부르지 않는다.
    assert result[ids[0]].kind is Kind.OTHER and result[ids[0]].topics == []
    assert calls == [2]  # 나머지 둘만 호출


async def test_triage_decision_keeps_topics_and_prompt_version(items, monkeypatch):
    ids, _ = items
    rules = _eager()

    async def fake_triage(_rules, entries):
        # 분류표 밖 slug 는 버려지고 항목 실패로 세지 않는다.
        return TriageBatch(
            items=[
                TriageItem(
                    idx=e.idx,
                    relevance=0.6,
                    reason="r",
                    kind=Kind.TECHNIQUE,
                    topics=["inference-opt", "nope", "agent"],
                )
                for e in entries
            ]
        )

    monkeypatch.setattr(pipeline, "call_triage", fake_triage)
    s, survivors = await _load(ids)
    async with s:
        result = await pipeline._triage(s, rules, survivors)
        await s.commit()

    async with SessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(Decision).where(Decision.item_id.in_(ids), Decision.stage == "triage")
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 3 and all(r.passed for r in rows)
    for r in rows:
        assert r.details["topics"] == ["inference-opt", "agent"]
        assert r.details["kind"] == "technique"
        assert r.details["prompt_version"] == TRIAGE_PROMPT_VERSION
    assert result[ids[0]].topics == ["inference-opt", "agent"]

    # 저장된 행에서 복원하면 topics 가 그대로 돌아오고 선별을 다시 부르지 않는다.
    async def must_not_call(_rules, entries):
        raise AssertionError("재호출")

    monkeypatch.setattr(pipeline, "call_triage", must_not_call)
    s, survivors = await _load(ids)
    async with s:
        again = await pipeline._triage(s, rules, survivors)
    assert all(again[i].topics == ["inference-opt", "agent"] for i in ids)
