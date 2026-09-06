# 통합 테스트 공통 — TEST_DATABASE_URL 이 없으면 전부 건너뛴다. Neon dev 브랜치를 가리켜야 한다

import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("TEST_DATABASE_URL 없음", allow_module_level=True)
