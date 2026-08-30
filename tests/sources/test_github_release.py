# GitHub Releases 수집기 테스트 — 초안 제외, since 필터, 웹훅 변환 함수 공유

import json
from datetime import UTC, datetime

import httpx
import respx

from app.config import SourceConfig
from app.schemas import Category
from app.sources.github_release import GithubReleaseSource, release_to_item
from tests.conftest import fixture

API = "https://api.github.com/repos/fastapi/fastapi/releases"


def make_source() -> GithubReleaseSource:
    return GithubReleaseSource(
        SourceConfig(
            name="github_release:watchlist",
            type="github_release",
            config={"repos": ["fastapi/fastapi"], "per_page": 5},
        )
    )


@respx.mock
async def test_skips_drafts():
    respx.get(url__startswith=API).mock(
        return_value=httpx.Response(200, content=fixture("github_release.json"))
    )
    items = await make_source().fetch(None)

    assert [item.external_id for item in items] == ["1001"]
    assert items[0].title == "fastapi/fastapi 0.120.0"
    assert items[0].category_hint is Category.LIBRARY
    assert items[0].raw["repo"] == "fastapi/fastapi"


@respx.mock
async def test_since_filter():
    respx.get(url__startswith=API).mock(
        return_value=httpx.Response(200, content=fixture("github_release.json"))
    )
    items = await make_source().fetch(datetime(2026, 9, 1, tzinfo=UTC))

    assert items == []


@respx.mock
async def test_one_failing_repo_does_not_break_the_rest():
    respx.get(url__startswith=API).mock(return_value=httpx.Response(500))
    source = make_source()
    source.repos = ["fastapi/fastapi"]

    assert await source.fetch(None) == []


def test_release_to_item_drops_draft():
    release = json.loads(fixture("github_release.json"))[1]
    assert release_to_item("github_release:watchlist", "fastapi/fastapi", release) is None
