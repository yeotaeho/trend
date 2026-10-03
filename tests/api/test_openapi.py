# OpenAPI 문서 테스트 — operation ID 가 겹치지 않고, v1 동작은 500 봉투까지 문서에 적는다

from __future__ import annotations

from app.main import app


def test_operation_ids_are_unique():
    # 같은 operation ID 가 두 번 나오면 문서가 규격을 어기고 클라이언트 생성기가 깨진다.
    ops = [op["operationId"] for path in app.openapi()["paths"].values() for op in path.values()]
    assert len(ops) == len(set(ops))


def test_v1_operations_document_500_envelope():
    for path, ops in app.openapi()["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, op in ops.items():
            assert "500" in op["responses"], f"{method.upper()} {path}"
