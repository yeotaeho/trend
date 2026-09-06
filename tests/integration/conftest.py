# 통합 테스트 공통 — TEST_DATABASE_URL 이 없으면 전부 건너뛴다. Neon dev 브랜치를 가리켜야 한다

import os

import pytest

_TEST_URL = os.environ.get("TEST_DATABASE_URL")
if not _TEST_URL:
    pytest.skip("TEST_DATABASE_URL 없음", allow_module_level=True)

from app.config import get_settings  # noqa: E402  (환경 확인 뒤에 앱을 불러야 한다)

# 테이블을 비우는 픽스처가 있다. 엔진이 다른 URL(운영 DB)을 보고 있으면 절대 돌리지 않는다.
if get_settings().database_url != _TEST_URL:
    pytest.skip(
        "DATABASE_URL 이 TEST_DATABASE_URL 과 다르다. 운영 DB 보호를 위해 건너뛴다",
        allow_module_level=True,
    )
