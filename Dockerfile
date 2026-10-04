FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY alembic.ini ./
COPY app ./app
COPY config ./config
RUN uv sync --no-dev

# 배포한 커밋. CI 가 build-args 로 넣고 GET /api/v1/settings 의 git_sha 가 읽는다.
# 맨 끝에 두어 SHA 가 바뀌어도 의존성 설치 층 캐시가 깨지지 않는다.
ARG GIT_SHA=""
ENV GIT_SHA=$GIT_SHA

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
