# 규칙 필터 테스트 — exclude 우선, 화이트리스트 소스, 저장소 패턴, 단어 경계

from app.config import Rules
from app.pipeline.rules import apply_rules

RULES = Rules(
    include_keywords=["claude", "mcp", "next.js"],
    include_repos=["anthropics/*", "vercel/next.js"],
    exclude_keywords=["hiring", "giveaway"],
    exclude_domains=["spam.example", "medium.com/@bot"],
    always_pass_sources=["youtube:*"],
)


def call(**kwargs):
    base = {"source": "rss:blog", "title": "", "body": None, "url": "https://ok.example/a"}
    return apply_rules(RULES, **{**base, **kwargs})


def test_include_keyword_passes():
    result = call(title="Claude X 출시")
    assert result.passed and result.matched_keywords == ["claude"]


def test_no_keyword_fails():
    assert call(title="주말 잡담").reason == "no_keyword"


def test_exclude_beats_include():
    result = call(title="Claude team is hiring")
    assert not result.passed and result.reason == "exclude_keyword"


def test_excluded_domain():
    assert call(title="Claude X", url="https://spam.example/a").reason == "exclude_domain"


def test_excluded_domain_path_prefix():
    result = call(title="Claude X", url="https://medium.com/@bot/some-post")
    assert result.reason == "exclude_domain"


def test_always_pass_source_skips_keywords():
    result = call(source="youtube:jocoding", title="주말 잡담")
    assert result.passed and result.reason == "always_pass_source"


def test_include_repo():
    result = call(title="release 1.2.3", repo="vercel/next.js")
    assert result.passed and result.reason == "include_repo"


def test_word_boundary_avoids_substring_match():
    assert call(title="mcparland 인터뷰").reason == "no_keyword"


def test_symbol_keyword_matches():
    assert call(title="Next.js 16 released").passed


def test_body_is_searched():
    assert call(title="새 소식", body="본문에 mcp 서버 이야기").passed
