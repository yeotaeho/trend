# 선별 배치 테스트 — 사용자 블록 조립, 배치 실패와 항목 실패의 구분

import pytest

from app.pipeline.triage import (
    TriageBatch,
    TriageBatchError,
    TriageEntry,
    TriageItem,
    build_user_content,
    parse_triage,
)


def entries():
    return [
        TriageEntry(1, "rss:arxiv-cs-cl", "Over-Refusal and Subspaces", "abstract…"),
        TriageEntry(2, "youtube:jocoding", "클로드 가격 논란", "", '👎 "[영상] 가격 논란"'),
    ]


def items(*pairs: tuple[int, float]) -> TriageBatch:
    return TriageBatch(items=[TriageItem(idx=i, relevance=r, reason="r") for i, r in pairs])


def test_user_content_numbers_items_and_appends_examples():
    text = build_user_content(entries())
    assert "[1] rss:arxiv-cs-cl | Over-Refusal and Subspaces\nabstract…" in text
    assert "[2] youtube:jocoding | 클로드 가격 논란" in text
    assert '유사 피드백: 👎 "[영상] 가격 논란"' in text


def test_parse_valid_batch():
    ok, failed = parse_triage(items((1, 0.2), (2, 0.7)), [1, 2])
    assert set(ok) == {1, 2} and failed == []


def test_count_mismatch_is_batch_error():
    with pytest.raises(TriageBatchError):
        parse_triage(items((1, 0.2)), [1, 2])


def test_unknown_idx_is_batch_error():
    with pytest.raises(TriageBatchError):
        parse_triage(items((1, 0.2), (9, 0.2)), [1, 2])


def test_duplicate_idx_marks_missing_item_failed():
    ok, failed = parse_triage(items((1, 0.2), (1, 0.3)), [1, 2])
    assert set(ok) == {1} and failed == [2]


def test_out_of_range_relevance_is_item_failure():
    ok, failed = parse_triage(items((1, 1.4), (2, 0.3)), [1, 2])
    assert set(ok) == {2} and failed == [1]


def test_reason_is_truncated_to_200_chars():
    batch = TriageBatch(items=[TriageItem(idx=1, relevance=0.5, reason="x" * 500)])
    ok, _ = parse_triage(batch, [1])
    assert len(ok[1].reason) == 200
