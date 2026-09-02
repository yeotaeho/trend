# 설정 로더 — .env 시크릿(pydantic-settings)과 config/*.yaml 규칙·소스 정의

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class Settings(BaseSettings):
    """시크릿·런타임 스위치. 값은 전부 .env 또는 환경변수에서 온다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_daily_cap: int = 300

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = ""

    discord_bot_token: str = ""
    discord_channel_id: str = ""
    discord_public_key: str = ""  # 인터랙션 서명 검증용. 비어 있으면 엔드포인트가 전부 401

    github_token: str = ""
    github_webhook_secret: str = ""

    scheduler_enabled: bool = True
    log_level: str = "INFO"


class SourceConfig(BaseModel):
    """config/sources.yaml 한 항목. `config` 는 소스 타입별 자유 필드."""

    name: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    poll_interval_sec: int = 900
    trust_score: float = 0.5
    enabled: bool = True


class ScoringConfig(BaseModel):
    w_src: float = 0.25
    w_kw: float = 0.25
    w_hot: float = 0.2
    w_multi: float = 0.2
    w_fresh: float = 0.1
    threshold: float = 0.45
    # always_pass 소스가 점수 관문을 건너뛰는 유효 기간. 이보다 오래된 항목은 LLM 에 안 보낸다.
    whitelist_max_age_hours: int = 48


class NotifyConfig(BaseModel):
    daily_push_cap: int = 15
    quiet_start_hour: int = 23
    quiet_end_hour: int = 8
    timezone: str = "Asia/Seoul"


class Rules(BaseModel):
    """config/rules.yaml — 규칙 필터·점수 가중치·발송 정책."""

    include_keywords: list[str] = Field(default_factory=list)
    include_repos: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    always_pass_sources: list[str] = Field(default_factory=list)
    interests: str = ""
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@functools.lru_cache(maxsize=1)
def get_rules() -> Rules:
    return Rules.model_validate(_read_yaml(CONFIG_DIR / "rules.yaml"))


@functools.lru_cache(maxsize=1)
def get_source_configs() -> list[SourceConfig]:
    raw = _read_yaml(CONFIG_DIR / "sources.yaml")
    sources = raw.get("sources", [])
    assert isinstance(sources, list)
    return [SourceConfig.model_validate(s) for s in sources]


def reload_configs() -> None:
    """YAML 을 다시 읽는다 (rules.yaml 핫리로드용)."""
    get_rules.cache_clear()
    get_source_configs.cache_clear()
