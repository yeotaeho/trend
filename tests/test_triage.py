# 선별 배치 테스트 — 사용자 블록 조립, 배치 실패와 항목 실패의 구분, topics 정리, 호출 시점

from datetime import UTC, datetime, timedelta

import pytest

from app.config import TriageConfig
from app.db.models import Item, Source
from app.jobs.pipeline import _triage_due
from app.pipeline.triage import (
    MAX_TOPICS,
    SYSTEM_PROMPT,
    TriageBatch,
    TriageBatchError,
    TriageEntry,
    TriageItem,
    build_user_content,
    call_triage,
    parse_triage,
    system_prompt,
)
from app.schemas import Kind
from tests.test_rules import RULES

TAXONOMY = ["inference-opt", "agent"]


def entries():
    return [
        TriageEntry(1, "rss:arxiv-cs-cl", "Over-Refusal and Subspaces", "abstract…"),
        TriageEntry(2, "youtube:jocoding", "클로드 가격 논란", "", '👎 "[영상] 가격 논란"'),
    ]


def items(*pairs: tuple[int, float]) -> TriageBatch:
    return TriageBatch(
        items=[
            TriageItem(idx=i, relevance=r, reason="r", kind=Kind.NEWS, topics=[]) for i, r in pairs
        ]
    )


def test_user_content_numbers_items_and_appends_examples():
    text = build_user_content(entries())
    assert "[1] rss:arxiv-cs-cl | Over-Refusal and Subspaces\nabstract…" in text
    assert "[2] youtube:jocoding | 클로드 가격 논란" in text
    assert '유사 피드백: 👎 "[영상] 가격 논란"' in text


def test_parse_valid_batch():
    ok, failed = parse_triage(items((1, 0.2), (2, 0.7)), [1, 2], taxonomy=TAXONOMY)
    assert set(ok) == {1, 2} and failed == []


def test_count_mismatch_is_batch_error():
    with pytest.raises(TriageBatchError):
        parse_triage(items((1, 0.2)), [1, 2], taxonomy=TAXONOMY)


def test_unknown_idx_is_batch_error():
    with pytest.raises(TriageBatchError):
        parse_triage(items((1, 0.2), (9, 0.2)), [1, 2], taxonomy=TAXONOMY)


def test_duplicate_idx_marks_missing_item_failed():
    ok, failed = parse_triage(items((1, 0.2), (1, 0.3)), [1, 2], taxonomy=TAXONOMY)
    assert set(ok) == {1} and failed == [2]


def test_out_of_range_relevance_is_item_failure():
    ok, failed = parse_triage(items((1, 1.4), (2, 0.3)), [1, 2], taxonomy=TAXONOMY)
    assert set(ok) == {2} and failed == [1]


def test_reason_is_truncated_to_200_chars():
    batch = TriageBatch(
        items=[TriageItem(idx=1, relevance=0.5, reason="x" * 500, kind=Kind.NEWS, topics=[])]
    )
    ok, _ = parse_triage(batch, [1], taxonomy=TAXONOMY)
    assert len(ok[1].reason) == 200


def test_parse_keeps_kind():
    batch = TriageBatch(
        items=[TriageItem(idx=1, relevance=0.5, reason="r", kind=Kind.SURVEY, topics=[])]
    )
    ok, failed = parse_triage(batch, [1], taxonomy=TAXONOMY)
    assert failed == [] and ok[1].kind is Kind.SURVEY


def test_unknown_topic_is_dropped_not_failed():
    batch = TriageBatch(
        items=[
            TriageItem(
                idx=1, relevance=0.5, reason="r", kind=Kind.NEWS, topics=["inference-opt", "nope"]
            )
        ]
    )
    ok, failed = parse_triage(batch, [1], taxonomy=["inference-opt"])
    assert failed == [] and ok[1].topics == ["inference-opt"]


def test_more_than_three_topics_truncated():
    batch = TriageBatch(
        items=[
            TriageItem(
                idx=1, relevance=0.5, reason="r", kind=Kind.NEWS, topics=["a", "b", "c", "d"]
            )
        ]
    )
    ok, _ = parse_triage(batch, [1], taxonomy=["a", "b", "c", "d"])
    assert ok[1].topics == ["a", "b", "c"] and MAX_TOPICS == 3


def test_repeated_topic_counts_once():
    batch = TriageBatch(
        items=[TriageItem(idx=1, relevance=0.5, reason="r", kind=Kind.NEWS, topics=["a", "a", "b"])]
    )
    ok, _ = parse_triage(batch, [1], taxonomy=["a", "b"])
    assert ok[1].topics == ["a", "b"]


def test_user_content_unchanged_by_new_fields():
    # 입력 형식은 그대로다. 출력 스키마만 는다.
    assert build_user_content(entries()).startswith("[1] ")


def test_system_prompt_lists_taxonomy():
    text = system_prompt(RULES)
    assert "3) topics" in text
    assert all(f"- {t}" in text for t in RULES.policy.taxonomy)


def test_prompt_lists_every_kind():
    assert all(k.value in SYSTEM_PROMPT for k in Kind)


async def test_invalid_kind_from_model_is_a_batch_error(monkeypatch):
    """enum 밖 kind 는 SDK 의 pydantic 검증에서 터진다. 기반 실패가 아니라 배치 실패다."""
    import app.pipeline.triage as triage

    class _Messages:
        async def parse(self, **_kwargs):
            TriageBatch.model_validate(
                {
                    "items": [
                        {"idx": 1, "relevance": 0.5, "reason": "r", "kind": "nope", "topics": []}
                    ]
                }
            )
            raise AssertionError("unreachable")

    class _Client:
        messages = _Messages()

    monkeypatch.setattr(triage, "client", lambda: _Client())
    with pytest.raises(TriageBatchError, match="검증"):
        await call_triage(RULES, entries())


def test_triage_waits_until_batch_fills_or_oldest_waited_long_enough():
    cfg = TriageConfig(min_batch=3, max_wait_minutes=60)
    now = datetime(2026, 9, 18, tzinfo=UTC)

    def pending(*minutes_ago: int) -> list[tuple[Item, Source]]:
        return [(Item(fetched_at=now - timedelta(minutes=m)), Source()) for m in minutes_ago]

    assert not _triage_due(cfg, pending(5, 59), now)
    assert _triage_due(cfg, pending(5, 60), now)
    assert _triage_due(cfg, pending(1, 1, 1), now)
