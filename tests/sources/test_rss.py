# RSS 수집기 테스트 — 피드 파싱, since 필터, 본문 평문화 (HTTP 는 respx 로 모킹)

from datetime import UTC, datetime

import httpx
import respx

from app.config import SourceConfig
from app.schemas import Category
from app.sources.rss import RssSource
from app.sources.youtube import FEED_URL
from tests.conftest import fixture

FEED = "https://example.com/feed.xml"


def make_source(**config) -> RssSource:
    return RssSource(SourceConfig(name="rss:blog", type="rss", config={"url": FEED, **config}))


@respx.mock
async def test_parses_entries():
    respx.get(FEED).mock(return_value=httpx.Response(200, content=fixture("rss_blog.xml")))
    items = await make_source().fetch(None)

    assert len(items) == 2
    first = items[0]
    assert first.title == "Introducing Claude X"
    assert first.url.startswith("https://example.com/blog/claude-x")
    assert first.body == "Claude X doubles the context window at the same price."
    assert first.published_at == datetime(2026, 8, 30, 9, 0, tzinfo=UTC)
    assert first.category_hint is None


@respx.mock
async def test_since_filters_older_entries():
    respx.get(FEED).mock(return_value=httpx.Response(200, content=fixture("rss_blog.xml")))
    items = await make_source().fetch(datetime(2026, 8, 30, 0, 0, tzinfo=UTC))

    assert [item.title for item in items] == ["Introducing Claude X"]


@respx.mock
async def test_category_hint_from_config():
    respx.get(FEED).mock(return_value=httpx.Response(200, content=fixture("rss_blog.xml")))
    items = await make_source(category_hint="technique").fetch(None)

    assert all(item.category_hint is Category.TECHNIQUE for item in items)


def test_youtube_feed_url_shape():
    assert FEED_URL.format(channel_id="ABC").endswith("videos.xml?channel_id=ABC")
