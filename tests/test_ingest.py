# 적재 테스트 — 링크 스킴 가드, 같은 URL 재관측의 raw 병합 (순수 함수)

from datetime import UTC, datetime

from app.pipeline.ingest import is_web_url, merge_raw
from app.schemas import NormalizedItem


def test_only_http_schemes_pass():
    assert is_web_url("https://example.com/a")
    assert is_web_url("http://example.com/a")
    assert not is_web_url("javascript:alert(1)")
    assert not is_web_url("data:text/html,hi")
    assert not is_web_url("ftp://example.com/a")
    assert not is_web_url("//example.com/a")


def obs(source: str = "hackernews:front", **metrics: float) -> NormalizedItem:
    return NormalizedItem(
        source=source,
        external_id="1",
        url="https://x/y",
        title="t",
        published_at=datetime(2026, 9, 14, tzinfo=UTC),
        metrics=metrics,
    )


def test_metrics_take_per_key_max_and_add_new_keys():
    raw, changed = merge_raw(
        {"metrics": {"points": 10.0, "comments": 5.0}},
        obs(points=3.0, upvotes=7.0),
        same_source=False,
    )
    assert changed
    assert raw["metrics"] == {"points": 10.0, "comments": 5.0, "upvotes": 7.0}


def test_other_source_is_recorded_as_mention():
    raw, changed = merge_raw({"source": "rss:blog"}, obs(), same_source=False)
    assert changed and raw["mentions"] == ["hackernews:front"]


def test_same_source_with_equal_metrics_is_unchanged():
    """GitHub 폴링처럼 같은 소스가 같은 값을 다시 줘도 되살림이 일어나면 안 된다."""
    existing = {"metrics": {"points": 10.0}}
    raw, changed = merge_raw(existing, obs(points=10.0), same_source=True)
    assert not changed and raw is existing


def test_old_row_without_mentions_key_is_unchanged_when_nothing_new():
    raw, changed = merge_raw({"repo": "a/b"}, obs(), same_source=True)
    assert not changed and "mentions" not in raw


def test_mentions_are_sorted_and_unique():
    raw, changed = merge_raw(
        {"mentions": ["rss:b", "hackernews:front"]}, obs(source="rss:a"), same_source=False
    )
    assert changed and raw["mentions"] == ["hackernews:front", "rss:a", "rss:b"]
    again, changed_again = merge_raw(raw, obs(source="rss:a"), same_source=False)
    assert not changed_again and again is raw


def test_lower_metric_does_not_change():
    raw, changed = merge_raw(
        {"metrics": {"points": 10.0}, "mentions": ["hackernews:front"]},
        obs(points=4.0),
        same_source=False,
    )
    assert not changed


def test_existing_keys_are_kept():
    raw, _ = merge_raw({"repo": "a/b", "metrics": {}}, obs(points=1.0), same_source=False)
    assert raw["repo"] == "a/b"
