# 정규화 테스트 — 추적 파라미터·www·트레일링 슬래시 제거와 HTML 평문화

from app.pipeline.normalize import normalize_url, strip_html, url_hash


def test_tracking_params_removed():
    assert (
        normalize_url("https://WWW.Example.com/post/?utm_source=x&ref=hn&id=7")
        == "https://example.com/post?id=7"
    )


def test_trailing_slash_and_fragment():
    assert normalize_url("https://example.com/a/b/#top") == "https://example.com/a/b"


def test_root_path_kept():
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_same_url_variants_share_hash():
    a = url_hash(normalize_url("https://www.example.com/x?utm_campaign=a"))
    b = url_hash(normalize_url("https://example.com/x/"))
    assert a == b


def test_strip_html():
    assert strip_html("<p>Hello   <b>world</b>&amp;more</p>") == "Hello world &more"
    assert strip_html(None) == ""
