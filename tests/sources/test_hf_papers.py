# HF Daily Papers 수집기 테스트 — arXiv URL 매핑, upvotes, HF 게재 시각, 저자 3명 제한, since 무시

from datetime import UTC, datetime

import httpx
import respx

from app.config import SourceConfig
from app.schemas import Category
from app.sources.hf_papers import API, HfPapersSource, paper_to_item
from tests.conftest import fixture


def make_source() -> HfPapersSource:
    return HfPapersSource(
        SourceConfig(name="hf_papers:daily", type="hf_papers", config={"limit": 2})
    )


@respx.mock
async def test_maps_to_arxiv_abs_url_with_upvotes():
    respx.get(API.format(n=2)).mock(
        return_value=httpx.Response(200, content=fixture("hf_daily_papers.json"))
    )
    # since 는 무시한다. 하루 목록은 집합이고 upvotes 증가가 병합 신호다.
    items = await make_source().fetch(datetime(2030, 1, 1, tzinfo=UTC))

    assert [i.url for i in items] == [
        "https://arxiv.org/abs/2609.06107",
        "https://arxiv.org/abs/2609.03502",
    ]
    first = items[0]
    assert first.external_id == "2609.06107"
    assert first.title == "DataFlex-RL: An Evaluation Platform for RLVR Data Policies"
    assert first.metrics == {"upvotes": 26.0, "comments": 1.0}
    assert first.published_at == datetime(2026, 9, 4, 20, 0, tzinfo=UTC)  # HF 게재 시각
    assert first.author == "Hao Liang, Mingrui Chen, Hengyi Feng"
    assert first.category_hint is Category.TECHNIQUE
    assert first.body is not None and first.body.startswith("Data policies")
    assert first.raw == {"arxiv_id": "2609.06107"}


def test_entry_without_paper_id_or_listing_time_is_dropped():
    no_id = {"paper": {}, "publishedAt": "2026-09-04T20:00:00.000Z"}
    no_listing = {"paper": {"id": "1", "title": "t"}}
    assert paper_to_item("hf_papers:daily", no_id) is None
    assert paper_to_item("hf_papers:daily", no_listing) is None
