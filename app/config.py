# 설정 로더 — .env 시크릿(pydantic-settings)과 config/*.yaml 규칙·소스·앱 정적값

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import Kind

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class Settings(BaseSettings):
    """시크릿·런타임 스위치. 값은 전부 .env 또는 환경변수에서 온다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_daily_cap: int = 300

    # 임베딩. provider 는 voyage | openai. 모델을 바꾸면 backfill_embeddings.py 로 전량 재계산.
    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-3.5-lite"
    voyage_api_key: str = ""
    openai_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = ""

    discord_bot_token: str = ""
    discord_channel_id: str = ""
    discord_public_key: str = ""  # 인터랙션 서명 검증용. 비어 있으면 엔드포인트가 전부 401

    github_token: str = ""
    github_webhook_secret: str = ""

    # 앱 API 베어러 토큰. 비어 있으면 /api/v1 전부 401. 토큰 하나 = DEFAULT_USER_ID.
    app_api_token: str = ""
    discord_channel_name: str = ""  # 앱 알림 설정 화면 표시용 (#trend-alerts)
    fcm_project_id: str = ""
    fcm_service_account_file: str = ""  # 서비스 계정 JSON 경로. 커밋 금지

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


class _Strict(BaseModel):
    # v1 에서 삭제된 옛 키(키워드 목록·우회 소스 등)가 남아 있으면 기동이 실패해야 한다.
    model_config = ConfigDict(extra="forbid")


DEFAULT_TAXONOMY = (
    "llm-model",
    "agent",
    "mcp-tooling",
    "inference-opt",
    "rag-retrieval",
    "training-finetune",
    "python-backend",
    "web-frontend",
    "devops-infra",
    "ai-safety-eval",
    "dev-community",
    "video",
)


class PolicyConfig(_Strict):
    """선별·판정 프롬프트가 읽는 정책. 문장으로 쓴다. 관문이 아니라 힌트다."""

    interests: str = ""
    not_interested: str = ""
    focus_repos: list[str] = Field(default_factory=list)
    focus_stack: list[str] = Field(default_factory=list)
    # 선별 topics 의 분류표 (slug). 앱 표시 라벨은 config/app.yaml 이 따로 가진다.
    taxonomy: list[str] = Field(default_factory=lambda: list(DEFAULT_TAXONOMY))


class ExcludeConfig(_Strict):
    keywords: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class DedupeConfig(_Strict):
    # 2026-09-06 표본 보정값. 0.90~0.95 는 같은 채널의 다른 영상·다른 릴리즈였고,
    # 0.80~0.85 는 arXiv 두 피드의 주제 이웃이었다. rules.yaml 이 우선한다.
    dup_threshold: float = 0.96
    related_threshold: float = 0.88
    window_hours: int = 72


class TriageConfig(_Strict):
    batch_size: int = 25
    daily_cap_calls: int = 60
    min_batch: int = 10
    max_wait_minutes: int = 60


class ScoringConfig(_Strict):
    # 2026-09-10 조정. 소스 신뢰도가 arXiv 의 신호 밀도를 대신 벌하고 있어 비중을 관련도로 옮겼다.
    w_src: float = 0.20
    w_rel: float = 0.30
    w_hot: float = 0.2
    w_multi: float = 0.2
    w_fresh: float = 0.1
    threshold: float = 0.45
    # 모든 소스 공통. 이보다 오래된 항목은 선별 호출 없이 stale 로 버린다.
    max_age_hours: int = 72
    # kind 별 가점·감점. 곱이 아니라 그대로 더한다. 없는 kind 는 0. 키가 Kind 밖이면 기동 실패.
    # 감점만 둔다 — 가점(technique +0.10)은 실측으로 arXiv 154건/2.5일을 판정에 보냈다.
    kind_weights: dict[Kind, float] = Field(
        default_factory=lambda: {Kind.SURVEY: -0.15, Kind.TUTORIAL: -0.05, Kind.PROMO: -0.30}
    )


class NotifyConfig(_Strict):
    daily_push_cap: int = 15
    quiet_start_hour: int = 23
    quiet_end_hour: int = 8
    timezone: str = "Asia/Seoul"
    explore_judge_cap: int = 3


class Rules(_Strict):
    """config/rules.yaml — 정책·제외 규칙·임계값·발송 정책."""

    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)
    dedupe: DedupeConfig = Field(default_factory=DedupeConfig)
    triage: TriageConfig = Field(default_factory=TriageConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


class OnboardingConfig(_Strict):
    done: int = 8
    total: int = 8


class AppConfig(_Strict):
    """config/app.yaml — 앱 전용 정적값. 파이프라인은 읽지 않는다."""

    onboarding: OnboardingConfig = Field(default_factory=OnboardingConfig)
    personal_model_threshold: int = 50
    resurface_unread_after_days: int = 7
    screening_relevance_floor: float = 0.5
    planned_sources: list[str] = Field(default_factory=list)
    # policy.taxonomy slug → 표시 라벨. 없는 slug 는 slug 를 그대로 라벨로 쓴다.
    taxonomy_labels: dict[str, str] = Field(default_factory=dict)


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
def get_app_config() -> AppConfig:
    return AppConfig.model_validate(_read_yaml(CONFIG_DIR / "app.yaml"))


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
    get_app_config.cache_clear()
