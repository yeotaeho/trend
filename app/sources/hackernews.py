# Hacker News 수집기 — Algolia 프론트 페이지 폴링 (커뮤니티가 이미 고른 30건, since 무시)

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.config import SourceConfig
from app.pipeline.normalize import strip_html
from app.schemas import NormalizedItem
from app.sources.base import Source, fetch_url, register

API = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={n}"
HN_ITEM = "https://news.ycombinator.com/item?id={id}"
DEFAULT_HITS = 30
BODY_LIMIT = 3000


def hit_to_item(source_name: str, hit: dict[str, Any]) -> NormalizedItem | None:
    """Algolia hit 하나를 정규화 항목으로. 제목·id·시각이 없으면 버린다."""
    title = hit.get("title")
    object_id = hit.get("objectID")
    created = hit.get("created_at_i")
    if not title or not object_id or not created:
        return None
    hn_url = HN_ITEM.format(id=object_id)
    return NormalizedItem(
        source=source_name,
        external_id=str(object_id),
        # 링크 글은 원문이 항목이다. 같은 URL 을 다른 소스가 이미 넣었으면 적재가 병합한다.
        url=hit.get("url") or hn_url,
        title=str(title).strip(),
        # 자체 글(Ask/Show HN)만 본문이 있다. 링크 글은 비워 두고 판정 직전 보강에 맡긴다.
        body=strip_html(hit.get("story_text"))[:BODY_LIMIT] or None,
        author=hit.get("author"),
        published_at=datetime.fromtimestamp(int(created), UTC),
        metrics={
            "points": float(hit.get("points") or 0),
            "comments": float(hit.get("num_comments") or 0),
        },
        raw={"hn_id": str(object_id), "hn_url": hn_url},
    )


class HackerNewsSource:
    """프론트 페이지는 집합이라 since 로 자르지 않는다. 매 폴링 같은 URL 이 와도 병합만 일어난다.

    ponytail: 프론트 페이지 30건만 본다. 놓치는 사례가 리포트에 보이면
    search_by_date?tags=story&numericFilters=points>N,created_at_i>since 로 넓힌다.
    """

    def __init__(self, cfg: SourceConfig) -> None:
        self.name = cfg.name
        self.hits_per_page = int(cfg.config.get("hits_per_page", DEFAULT_HITS))

    async def fetch(self, since: datetime | None) -> list[NormalizedItem]:
        response = await fetch_url(API.format(n=self.hits_per_page))
        items = [hit_to_item(self.name, hit) for hit in response.json().get("hits", [])]
        return [item for item in items if item]


@register("hackernews")
def _build(cfg: SourceConfig) -> Source:
    return HackerNewsSource(cfg)
