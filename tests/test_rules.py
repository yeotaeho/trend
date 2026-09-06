# 규칙 필터 테스트 — exclude 키워드·도메인만 판정한다. 통과는 기본값이다

from app.config import ExcludeConfig, Rules
from app.pipeline.rules import apply_rules

RULES = Rules(
    exclude=ExcludeConfig(
        keywords=["hiring", "giveaway"], domains=["spam.example", "medium.com/@bot"]
    )
)


def call(**kwargs):
    base = {"title": "", "body": None, "url": "https://ok.example/a"}
    return apply_rules(RULES, **{**base, **kwargs})


def test_plain_item_passes():
    result = call(title="주말 잡담")
    assert result.passed and result.reason == "ok"


def test_exclude_keyword():
    result = call(title="Claude team is hiring")
    assert not result.passed and result.reason == "exclude_keyword"
    assert result.matched_keywords == ["hiring"]


def test_excluded_domain():
    assert call(title="Claude X", url="https://spam.example/a").reason == "exclude_domain"


def test_excluded_domain_path_prefix():
    assert call(title="x", url="https://medium.com/@bot/some-post").reason == "exclude_domain"


def test_word_boundary_avoids_substring_match():
    assert call(title="hiringham 마을 소식").passed


def test_body_is_searched():
    assert call(title="새 소식", body="본문에 giveaway 안내").reason == "exclude_keyword"
