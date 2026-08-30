# GitHub Releases 수집기 — 관심 저장소 릴리즈 폴링 (웹훅 수신 시 변환도 담당)

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.config import SourceConfig, get_settings
from app.log import get_logger
from app.schemas import Category, NormalizedItem
from app.sources.base import Source, fetch_url, register

API = "https://api.github.com/repos/{repo}/releases?per_page={per_page}"
BODY_LIMIT = 3000
log = get_logger(__name__)


def auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def release_to_item(source_name: str, repo: str, release: dict[str, Any]) -> NormalizedItem | None:
    """릴리즈 JSON 하나를 정규화 항목으로. 초안·시각 누락은 버린다."""
    if release.get("draft"):
        return None
    published = release.get("published_at")
    html_url = release.get("html_url")
    if not published or not html_url:
        return None
    name = release.get("name") or release.get("tag_name") or ""
    return NormalizedItem(
        source=source_name,
        external_id=str(release["id"]),
        url=html_url,
        title=f"{repo} {name}".strip(),
        body=(release.get("body") or "")[:BODY_LIMIT] or None,
        author=(release.get("author") or {}).get("login"),
        published_at=datetime.fromisoformat(published),
        category_hint=Category.LIBRARY,
        metrics={"prerelease": float(bool(release.get("prerelease")))},
        raw={"repo": repo, "tag_name": release.get("tag_name")},
    )


class GithubReleaseSource:
    """웹훅이 주 경로이고 이 폴링은 누락 보정용이다."""

    def __init__(self, cfg: SourceConfig) -> None:
        self.name = cfg.name
        self.repos = [str(r) for r in cfg.config.get("repos", [])]
        self.per_page = int(cfg.config.get("per_page", 5))

    async def _fetch_repo(self, repo: str, since: datetime | None) -> list[NormalizedItem]:
        response = await fetch_url(
            API.format(repo=repo, per_page=self.per_page), headers=auth_headers()
        )
        items = []
        for release in response.json():
            item = release_to_item(self.name, repo, release)
            if item and not (since and item.published_at <= since):
                items.append(item)
        return items

    async def fetch(self, since: datetime | None) -> list[NormalizedItem]:
        results = await asyncio.gather(
            *(self._fetch_repo(repo, since) for repo in self.repos), return_exceptions=True
        )
        items: list[NormalizedItem] = []
        for repo, result in zip(self.repos, results, strict=True):
            if isinstance(result, BaseException):
                # 저장소 하나가 실패해도 나머지는 수집한다.
                log.warning("github_release.repo_failed", repo=repo, error=str(result))
                continue
            items.extend(result)
        return items


@register("github_release")
def _build(cfg: SourceConfig) -> Source:
    return GithubReleaseSource(cfg)
