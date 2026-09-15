# Hacker News 수집기 테스트 — 프론트 페이지 파싱, 자체 글의 링크·본문, HTML 평문화, since 무시

import json
from datetime import UTC, datetime

import httpx
import respx

from app.config import SourceConfig
from app.sources.hackernews import API, HN_ITEM, HackerNewsSource, hit_to_item
from tests.conftest import fixture


def make_source() -> HackerNewsSource:
    return HackerNewsSource(
        SourceConfig(name="hackernews:front", type="hackernews", config={"hits_per_page": 30})
    )


def mock_front_page() -> None:
    respx.get(API.format(n=30)).mock(
        return_value=httpx.Response(200, content=fixture("hn_front_page.json"))
    )


@respx.mock
async def test_link_story_uses_target_url_and_empty_body():
    mock_front_page()
    items = await make_source().fetch(None)

    assert len(items) == 3
    first = items[0]
    assert first.external_id == "49688695"
    assert first.url == "https://www.vals.ai/blogs/fable-solves-cyphral-distich"
    assert first.body is None  # 링크 글은 판정 직전 보강에 맡긴다
    assert first.author == "u1hcw9nx"
    assert first.metrics == {"points": 1075.0, "comments": 480.0}
    assert first.published_at == datetime(2026, 9, 13, 21, 6, 13, tzinfo=UTC)
    assert first.raw == {"hn_id": "49688695", "hn_url": HN_ITEM.format(id="49688695")}
    assert first.category_hint is None


@respx.mock
async def test_self_post_uses_hn_link_and_story_text():
    mock_front_page()
    ask = (await make_source().fetch(None))[1]

    assert ask.url == HN_ITEM.format(id="49686380")
    assert ask.body == "What are you working on? What have you been curious about lately?"


def test_story_text_html_is_flattened():
    hit = json.loads(fixture("hn_front_page.json"))["hits"][2]
    item = hit_to_item("hackernews:front", hit)

    assert item is not None and item.body is not None
    assert "<a" not in item.body
    assert "github.com/ca" in item.body  # &#x2F; 가 / 로 풀린다


def test_hit_without_title_or_time_is_dropped():
    assert hit_to_item("hackernews:front", {"objectID": "1", "created_at_i": 1}) is None
    assert hit_to_item("hackernews:front", {"objectID": "1", "title": "t"}) is None


@respx.mock
async def test_since_is_ignored():
    """프론트 페이지는 집합이다. 아는 URL 은 store_items 가 병합·되살린다."""
    mock_front_page()
    assert len(await make_source().fetch(datetime(2030, 1, 1, tzinfo=UTC))) == 3
