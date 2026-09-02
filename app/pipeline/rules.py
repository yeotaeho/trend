# 규칙 필터 (1단계 관문) — include/exclude 키워드·저장소·도메인 매칭

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


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(fnmatch(value, pattern) for pattern in patterns)


def _excluded_domain(url: str, patterns: list[str]) -> bool:
    """슬래시 없는 패턴은 호스트 매칭, 슬래시가 있으면 `host/path` 접두 매칭."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    full = f"{host}{parts.path}"
    return any(
        full.startswith(pattern) if "/" in pattern else fnmatch(host, pattern)
        for pattern in patterns
    )


def apply_rules(
    rules: Rules,
    *,
    source: str,
    title: str,
    body: str | None,
    url: str,
    repo: str | None = None,
) -> RuleResult:
    """제목 + 본문 앞부분으로 판정한다. exclude 가 언제나 우선한다."""
    text = f"{title}\n{(body or '')[:MATCH_BODY_CHARS]}"

    excluded = find_keywords(text, rules.exclude_keywords)
    if excluded:
        return RuleResult(False, "exclude_keyword", excluded)

    if _excluded_domain(url, rules.exclude_domains):
        return RuleResult(False, "exclude_domain")

    # 화이트리스트 경로도 매칭 키워드를 돌려준다. 점수 관문의 kw 항이 이 목록 길이를
    # 쓰므로, 비워서 보내면 신뢰도 1.0 소스도 최대 0.35 라 임계값(0.45)을 절대 못 넘는다.
    matched = find_keywords(text, rules.include_keywords)

    if _matches_any(source, rules.always_pass_sources):
        return RuleResult(True, "always_pass_source", matched)

    if repo and _matches_any(repo, rules.include_repos):
        return RuleResult(True, "include_repo", matched)

    if matched:
        return RuleResult(True, "include_keyword", matched)

    return RuleResult(False, "no_keyword")
