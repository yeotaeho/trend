# YouTube 채널 수집기 — 채널 RSS 피드를 RSS 수집기로 그대로 처리

from __future__ import annotations

from app.config import SourceConfig
from app.sources.base import Source, register
from app.sources.rss import RssSource

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


@register("youtube")
def _build(cfg: SourceConfig) -> Source:
    channel_id = cfg.config["channel_id"]
    patched = cfg.model_copy(
        update={"config": {"url": FEED_URL.format(channel_id=channel_id), "category_hint": "video"}}
    )
    return RssSource(patched)
