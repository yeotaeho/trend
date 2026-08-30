# 연결 문자열 처리 테스트 — libpq 전용 파라미터 제거와 TLS 컨텍스트 주입

import ssl

from app.db.session import connect_args, requires_tls, to_asyncpg_url

NEON = (
    "postgresql://u:p@ep-x-pooler.region.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_driver_prefix_is_rewritten():
    assert to_asyncpg_url("postgres://u:p@h/db").startswith("postgresql+asyncpg://")
    assert to_asyncpg_url("postgresql://u:p@h/db").startswith("postgresql+asyncpg://")


def test_already_asyncpg_url_is_kept():
    url = "postgresql+asyncpg://u:p@h/db"
    assert to_asyncpg_url(url) == url


def test_libpq_only_params_are_dropped():
    """sslmode·channel_binding 을 그대로 넘기면 asyncpg 가 TypeError 를 낸다."""
    result = to_asyncpg_url(NEON)
    assert "sslmode" not in result
    assert "channel_binding" not in result
    assert result.endswith("/neondb")


def test_non_libpq_params_survive():
    assert "application_key=v" in to_asyncpg_url("postgresql://u:p@h/db?application_key=v")


def test_requires_tls():
    assert requires_tls(NEON)
    assert requires_tls("postgresql://u:p@h/db?sslmode=verify-full")
    assert not requires_tls("postgresql://u:p@h/db?sslmode=disable")
    assert not requires_tls("postgresql://u:p@h/db")


def test_connect_args_for_neon():
    args = connect_args(NEON)
    # pgbouncer 는 prepared statement 를 지원하지 않는다.
    assert args["statement_cache_size"] == 0
    assert args["prepared_statement_cache_size"] == 0
    # sslmode 문자열 대신 컨텍스트를 직접 준다 (홈 경로의 비ASCII 문자 문제 회피).
    assert isinstance(args["ssl"], ssl.SSLContext)
    assert args["ssl"].verify_mode is ssl.CERT_REQUIRED
    assert args["ssl"].check_hostname


def test_connect_args_without_tls_has_no_ssl():
    assert "ssl" not in connect_args("postgresql://u:p@h/db")


def test_connect_args_for_non_postgres_is_empty():
    assert connect_args("sqlite+aiosqlite:///:memory:") == {}
