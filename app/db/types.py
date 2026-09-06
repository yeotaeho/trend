# 벡터 컬럼 타입 — pgvector 를 파이썬 의존성 없이 쓴다. 쓰기만 지원하고 비교·읽기는 SQL 에서 한다

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy import Text, cast
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[Sequence[float]]):
    """`vector(dim)` 컬럼.

    값은 `[0.1,0.2,…]` 문자열로 만들어 `CAST(CAST(:v AS text) AS vector(dim))` 로 넣는다.
    asyncpg 는 vector 타입 코덱이 없어서 파라미터가 vector 로 추론되면 실패한다.
    text 를 거치면 서버가 text→vector 캐스트를 해 준다. 파이썬에서 벡터를 읽는 경로는 없다.
    """

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: Any) -> str:
        return f"vector({self.dim})"

    def bind_processor(self, dialect: Dialect) -> Callable[[Any], str | None]:
        def process(value: Sequence[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{x:.7g}" for x in value) + "]"

        return process

    def bind_expression(self, bindvalue: ColumnElement[Any]) -> ColumnElement[Any]:
        return cast(cast(bindvalue, Text), self)
