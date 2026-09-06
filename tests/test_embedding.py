# 임베딩 어댑터 테스트 — 텍스트 조립, 배치 분할, 차원 검증, 재시도와 None 폴백

import httpx
import pytest
import respx

from app.pipeline.embedding import DIM, EmbeddingDimError, embed, embedding_text

VOYAGE = "https://api.voyageai.com/v1/embeddings"


def vec(seed: float) -> list[float]:
    return [seed] * DIM


def test_embedding_text_joins_title_and_300_chars():
    text = embedding_text("제목", "본" * 500)
    assert text.startswith("제목\n")
    assert len(text) == len("제목\n") + 300


def test_embedding_text_without_body():
    assert embedding_text("제목", None) == "제목"


@respx.mock
async def test_embed_returns_vectors_in_order():
    route = respx.post(VOYAGE).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": vec(0.1)}, {"index": 1, "embedding": vec(0.2)}]
            },
        )
    )
    result = await embed(["a", "b"])
    assert result == [vec(0.1), vec(0.2)]
    sent = route.calls[0].request
    assert sent.headers["authorization"] == "Bearer test-voyage-key"
    body = sent.read().decode()
    assert '"output_dimension": 1024' in body or '"output_dimension":1024' in body


@respx.mock
async def test_wrong_dimension_raises_not_none():
    respx.post(VOYAGE).mock(
        return_value=httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1] * 512}]})
    )
    with pytest.raises(EmbeddingDimError):
        await embed(["a"])


@respx.mock
async def test_duplicate_index_raises():
    respx.post(VOYAGE).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": vec(0.1)}, {"index": 0, "embedding": vec(0.2)}]
            },
        )
    )
    with pytest.raises(EmbeddingDimError):
        await embed(["a", "b"])


@respx.mock
async def test_negative_retry_after_is_clamped(monkeypatch):
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("app.pipeline.embedding.asyncio.sleep", fake_sleep)
    respx.post(VOYAGE).mock(
        side_effect=[
            httpx.Response(503, headers={"retry-after": "-3"}),
            httpx.Response(200, json={"data": [{"index": 0, "embedding": vec(0.1)}]}),
        ]
    )
    assert await embed(["a"]) == [vec(0.1)]
    assert waits == [0.0]


@respx.mock
async def test_server_error_retries_then_none(monkeypatch):
    monkeypatch.setattr("app.pipeline.embedding.RETRY_WAIT", 0)
    route = respx.post(VOYAGE).mock(return_value=httpx.Response(503))
    assert await embed(["a"]) is None
    assert route.call_count == 3


@respx.mock
async def test_client_error_fails_immediately(monkeypatch):
    monkeypatch.setattr("app.pipeline.embedding.RETRY_WAIT", 0)
    route = respx.post(VOYAGE).mock(return_value=httpx.Response(401))
    assert await embed(["a"]) is None
    assert route.call_count == 1


async def test_more_than_max_batch_is_rejected():
    with pytest.raises(ValueError):
        await embed(["x"] * 129)


@respx.mock
async def test_retry_after_header_is_honored(monkeypatch):
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("app.pipeline.embedding.asyncio.sleep", fake_sleep)
    respx.post(VOYAGE).mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "7"}),
            httpx.Response(200, json={"data": [{"index": 0, "embedding": vec(0.1)}]}),
        ]
    )
    assert await embed(["a"]) == [vec(0.1)]
    assert waits == [7.0]
