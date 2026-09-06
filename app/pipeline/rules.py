# 규칙 필터 — exclude 키워드·도메인 판정. 포함 판단은 LLM 선별이 맡는다

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from urllib.parse import urlsplit

from app.config import Rules

MATCH_BODY_CHARS = 1500


@dataclass(slots=True)
class RuleResult:
    passed: bool
    reason: str
    matched_keywords: list[str] = field(default_factory=list)


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """단어 경계 매칭. 단, next.js·c++ 처럼 기호로 끝나는 키워드는 경계를 붙이지 않는다."""
    escaped = re.escape(keyword)
    left = r"\b" if keyword[:1].isalnum() else ""
    right = r"\b" if keyword[-1:].isalnum() else ""
    return re.compile(f"{left}{escaped}{right}", re.IGNORECASE)


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _keyword_pattern(kw).search(text)]


def _excluded_domain(url: str, patterns: list[str]) -> bool:
    """슬래시 없는 패턴은 호스트 매칭, 슬래시가 있으면 `host/path` 접두 매칭."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    full = f"{host}{parts.path}"
    return any(
        full.startswith(pattern) if "/" in pattern else fnmatch(host, pattern)
        for pattern in patterns
    )


def apply_rules(rules: Rules, *, title: str, body: str | None, url: str) -> RuleResult:
    """제목 + 본문 앞부분으로 제외만 판정한다. 포함 판단은 LLM 선별이 한다."""
    text = f"{title}\n{(body or '')[:MATCH_BODY_CHARS]}"
    excluded = find_keywords(text, rules.exclude.keywords)
    if excluded:
        return RuleResult(False, "exclude_keyword", excluded)
    if _excluded_domain(url, rules.exclude.domains):
        return RuleResult(False, "exclude_domain")
    return RuleResult(True, "ok")
