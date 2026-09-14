# Hugging Face Daily Papers 수집기 — HF 목록을 arXiv URL로 매핑해 기존 항목에 upvotes 병합

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import SourceConfig
from app.schemas import Category, NormalizedItem
from app.sources.base import Source, fetch_url, register

API = "https://huggingface.co/api/daily_papers?limit={n}"
ARXIV_ABS = "https://arxiv.org/abs/{id}"
DEFAULT_LIMIT = 50
MAX_AUTHORS = 3
BODY_LIMIT = 3000


def paper_to_item(source_name: str, entry: dict[str, Any]) -> NormalizedItem | None:
    """목록 항목 하나를 정규화 항목으로. arXiv id·제목·게재 시각이 없으면 버린다."""
    paper = entry.get("paper") or {}
    paper_id = paper.get("id")
    title = paper.get("title") or entry.get("title")
    listed_at = entry.get("publishedAt")
    if not paper_id or not title or not listed_at:
        return None
    names = [a["name"] for a in paper.get("authors") or [] if isinstance(a, dict) and a.get("name")]
    return NormalizedItem(
        source=source_name,
        external_id=str(paper_id),
        # arXiv 링크 형식. 기존 논문이면 upvotes·멘션이 병합된다.
        url=ARXIV_ABS.format(id=paper_id),
        title=str(title).strip(),
        body=(paper.get("summary") or "")[:BODY_LIMIT] or None,
        author=", ".join(names[:MAX_AUTHORS]) or None,
        # 사건은 arXiv 게시일이 아니라 HF 목록에 오른 날이다.
        published_at=datetime.fromisoformat(str(listed_at)),
        category_hint=Category.TECHNIQUE,
        metrics={
            "upvotes": float(paper.get("upvotes") or 0),
            "comments": float(entry.get("numComments") or 0),
        },
        raw={"arxiv_id": str(paper_id)},
    )


class HfPapersSource:
    """하루 목록은 집합이라 since 로 자르지 않는다. upvotes 증가가 병합·되살림의 신호다."""

    def __init__(self, cfg: SourceConfig) -> None:
        self.name = cfg.name
        self.limit = int(cfg.config.get("limit", DEFAULT_LIMIT))

    async def fetch(self, since: datetime | None) -> list[NormalizedItem]:
        response = await fetch_url(API.format(n=self.limit))
        items = [paper_to_item(self.name, entry) for entry in response.json()]
        return [item for item in items if item]


@register("hf_papers")
def _build(cfg: SourceConfig) -> Source:
    return HfPapersSource(cfg)
