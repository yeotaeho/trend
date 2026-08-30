# RSS/Atom 수집기 — 기업 기술 블로그·arXiv 공통

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import feedparser

from app.config import SourceConfig
from app.pipeline.normalize import strip_html
from app.schemas import Category, NormalizedItem
from app.sources.base import Source, fetch_url, register

BODY_LIMIT = 3000


def entry_published(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, key, None)
        if parsed:
            y, mo, d, h, mi, sec = parsed[:6]
            return datetime(y, mo, d, h, mi, sec, tzinfo=UTC)
    return None


def entry_body(entry: Any) -> str:
    contents = getattr(entry, "content", None)
    if contents:
        return strip_html(contents[0].get("value"))[:BODY_LIMIT]
    # YouTube 채널 피드는 summary 대신 media:description 에 설명을 담는다.
    raw = getattr(entry, "summary", None) or getattr(entry, "media_description", None)
    return strip_html(raw)[:BODY_LIMIT]


class RssSource:
    """피드가 주는 제목·요약·본문만 사용한다. 원문 페이지는 요청하지 않는다."""

    def __init__(self, cfg: SourceConfig) -> None:
        self.name = cfg.name
        self.url = str(cfg.config["url"])
        hint = cfg.config.get("category_hint")
        self.category_hint = Category(hint) if hint else None

    async def fetch(self, since: datetime | None) -> list[NormalizedItem]:
        response = await fetch_url(self.url)
        feed = feedparser.parse(response.content)
        items: list[NormalizedItem] = []
        for entry in feed.entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not link or not title:
                continue
            published = entry_published(entry)
            if published is None:
                continue
            if since and published <= since:
                continue
            items.append(
                NormalizedItem(
                    source=self.name,
                    external_id=str(getattr(entry, "id", link)),
                    url=link,
                    title=title.strip(),
                    body=entry_body(entry) or None,
                    author=getattr(entry, "author", None),
                    published_at=published,
                    category_hint=self.category_hint,
                )
            )
        return items


@register("rss")
def _build(cfg: SourceConfig) -> Source:
    return RssSource(cfg)
