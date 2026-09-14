# 수집기 패키지 — import 만으로 레지스트리에 소스 타입이 등록되게 한다

from app.sources import github_release, hackernews, hf_papers, rss, youtube  # noqa: F401
from app.sources.base import Source, build_source, register, registered_types

__all__ = ["Source", "build_source", "register", "registered_types"]
