# 적재 가드 테스트 — 피드가 준 링크의 스킴 검증

from app.pipeline.ingest import is_web_url


def test_only_http_schemes_pass():
    assert is_web_url("https://example.com/a")
    assert is_web_url("http://example.com/a")
    assert not is_web_url("javascript:alert(1)")
    assert not is_web_url("data:text/html,hi")
    assert not is_web_url("ftp://example.com/a")
    assert not is_web_url("//example.com/a")
