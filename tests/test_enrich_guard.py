# 본문 보강 가드 테스트 — 사설 주소 차단, 리다이렉트 홉별 검사, 홉 상한
# (HTTP 는 respx, DNS 는 monkeypatch)

import httpx
import pytest
import respx

from app.pipeline import llm
from app.pipeline.llm import all_global, enrich_body

# 호스트 → 해석된 주소. 실제 DNS 를 타지 않는다.
TABLE = {
    "pub.example": ["93.184.216.34"],
    "dual.example": ["93.184.216.34", "10.0.0.5"],
    "169.254.169.254": ["169.254.169.254"],
    "localhost": ["127.0.0.1"],
}


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch):
    async def fake_resolve(host: str) -> list[str]:
        return TABLE.get(host, [])

    monkeypatch.setattr(llm, "resolve", fake_resolve)
    # trafilatura 가 아니라 가드를 검증한다. 추출은 고정값으로.
    monkeypatch.setattr(llm.trafilatura, "extract", lambda html: "본문")


def test_all_global_rejects_private_loopback_linklocal_and_empty():
    assert all_global(["93.184.216.34"])
    assert all_global(["2606:2800:220:1:248:1893:25c8:1946"])
    assert not all_global(["10.0.0.1"])
    assert not all_global(["127.0.0.1"])
    assert not all_global(["169.254.169.254"])  # VM 메타데이터
    assert not all_global(["::1"])
    assert not all_global(["93.184.216.34", "10.0.0.5"])  # 하나라도 사설이면 막는다
    assert not all_global([])  # 해석 실패도 막는다


@respx.mock
async def test_blocked_host_is_never_requested():
    route = respx.get("http://169.254.169.254/latest/meta-data").mock(
        return_value=httpx.Response(200, text="secret")
    )
    assert await enrich_body("http://169.254.169.254/latest/meta-data") is None
    assert not route.called


@respx.mock
async def test_unknown_host_is_blocked():
    route = respx.get("https://nx.example/a").mock(return_value=httpx.Response(200, text="x"))
    assert await enrich_body("https://nx.example/a") is None
    assert not route.called


@respx.mock
async def test_redirect_into_private_address_is_blocked():
    respx.get("https://pub.example/go").mock(
        return_value=httpx.Response(302, headers={"location": "http://localhost:8080/admin"})
    )
    inner = respx.get("http://localhost:8080/admin").mock(
        return_value=httpx.Response(200, text="x")
    )
    assert await enrich_body("https://pub.example/go") is None
    assert not inner.called


@respx.mock
async def test_redirect_loop_stops_at_max_hops():
    route = respx.get("https://pub.example/loop").mock(
        return_value=httpx.Response(302, headers={"location": "/loop"})
    )
    assert await enrich_body("https://pub.example/loop") is None
    assert route.call_count == llm.MAX_REDIRECTS + 1


@respx.mock
async def test_public_redirect_then_page_is_extracted():
    respx.get("https://pub.example/old").mock(
        return_value=httpx.Response(301, headers={"location": "https://pub.example/new"})
    )
    respx.get("https://pub.example/new").mock(
        return_value=httpx.Response(200, text="<html><body><p>hello</p></body></html>")
    )
    assert await enrich_body("https://pub.example/old") == "본문"


@respx.mock
async def test_non_http_scheme_is_blocked():
    assert await enrich_body("ftp://pub.example/a") is None


@respx.mock
async def test_mixed_public_and_private_resolution_is_blocked():
    """dual.example 은 공인·사설 주소가 섞여 해석된다. 하나라도 사설이면 요청 자체를 막는다."""
    route = respx.get("https://dual.example/a").mock(return_value=httpx.Response(200, text="x"))
    assert await enrich_body("https://dual.example/a") is None
    assert not route.called
