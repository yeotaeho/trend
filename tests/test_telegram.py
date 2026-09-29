# 텔레그램 렌더링·콜백 테스트 — HTML 이스케이프와 피드백 콜백 파싱

from datetime import UTC, datetime, timedelta

from app.db.models import Item, Summary
from app.notify.base import feedback_callback_data, parse_feedback_callback, relative_time
from app.notify.telegram import render

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def make_pair(title_ko="[릴리즈] Next.js 16 <출시>"):
    item = Item(
        id=7,
        url="https://example.com/a",
        title="Next.js 16",
        published_at=NOW - timedelta(minutes=12),
    )
    summary = Summary(
        item_id=7,
        title_ko=title_ko,
        summary_ko="주요 변경 3가지.",
        tags=["nextjs", "release"],
        importance=4,
        worth_notifying=True,
        model="claude-haiku-4-5",
    )
    return item, summary


def test_render_escapes_and_includes_source():
    item, summary = make_pair()
    text = render(item, summary, "rss:vercel", title=summary.title_ko, now=NOW)

    assert "&lt;출시&gt;" in text
    assert "출처: rss:vercel · 12분 전" in text
    assert "#nextjs #release" in text


def test_relative_time_units():
    assert relative_time(NOW - timedelta(minutes=5), now=NOW) == "5분 전"
    assert relative_time(NOW - timedelta(hours=3), now=NOW) == "3시간 전"
    assert relative_time(NOW - timedelta(days=2), now=NOW) == "2일 전"


def test_callback_roundtrip():
    assert parse_feedback_callback(feedback_callback_data("useful", 42)) == ("useful", 42)


def test_callback_rejects_garbage():
    assert parse_feedback_callback("fb:maybe:42") is None
    assert parse_feedback_callback("fb:useful:abc") is None
    assert parse_feedback_callback("something-else") is None


def test_render_uses_send_title_not_summary_title():
    item, summary = make_pair()
    text = render(item, summary, "rss:vercel", title="발송 제목 (v2 · v1)", now=NOW)

    assert "<b>발송 제목 (v2 · v1)</b>" in text
    assert "&lt;출시&gt;" not in text
