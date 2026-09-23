# 설정 로더 — .env 시크릿(pydantic-settings)과 config/*.yaml 규칙·소스·앱 정적값

from __future__ import annotations

import copy
import functools
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import structlog
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import Kind

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
# app.log 이 이 모듈을 임포트하므로 structlog 를 직접 쓴다.
log = structlog.get_logger(__name__)


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
    # 앱 관심사 화면에서 고른 카테고리. 거름망이 아니라 프롬프트 힌트다. 생략하면 taxonomy 전체.
    categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _categories_within_taxonomy(self) -> PolicyConfig:
        if "categories" not in self.model_fields_set:
            self.categories = list(self.taxonomy)
        unknown = [c for c in self.categories if c not in self.taxonomy]
        if unknown:
            raise ValueError(f"policy.categories 에 taxonomy 밖 slug 가 있다: {unknown}")
        return self


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


Delivery = Literal["instant", "quiet", "feed_only"]


class DeliveryByImportanceConfig(_Strict):
    """importance 구간 → 알림 강도. 기본값은 notify/policy.py 의 level_for 와 같다."""

    high: Delivery = "instant"
    mid: Delivery = "quiet"
    low: Delivery = "feed_only"


class ChannelsConfig(_Strict):
    fcm: bool = True
    discord: bool = True
    telegram: bool = False


class NotifyConfig(_Strict):
    daily_push_cap: int = 15
    quiet_start_hour: int = 23
    quiet_end_hour: int = 8
    timezone: str = "Asia/Seoul"
    explore_judge_cap: int = 3
    # 같은 cluster_id 를 하루에 보내는 서로 다른 항목 수 상한. 0 = 끔.
    cluster_daily_cap: int = Field(default=1, ge=0)
    delivery_by_importance: DeliveryByImportanceConfig = Field(
        default_factory=DeliveryByImportanceConfig
    )
    explore_enabled: bool = True
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)


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


# user_prefs.data 중 Rules 밖 키. sources 는 sync_sources 가 따로 읽는다.
PREFS_NON_RULES_KEYS = frozenset({"sources"})
# 앱이 저장한 설정 덮어쓰기 (DEFAULT_USER_ID 의 user_prefs.data)와 그 저장 시각.
# set_prefs_overlay 로만 바꾼다.
_prefs_overlay: dict[str, Any] = {}
_prefs_version: datetime | None = None


def merge_overlay(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """깊은 병합. dict 는 키별로 내려가고 목록·값은 통째로 바꾼다. 입력은 건드리지 않는다."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_overlay(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _check_overlay_section(name: str, value: Any) -> None:
    if name not in Rules.model_fields:
        raise ValueError(f"알 수 없는 설정 섹션 {name!r}")
    if not isinstance(value, dict):
        raise ValueError(f"설정 섹션 {name!r} 은 객체여야 한다")
    if name == "policy" and "taxonomy" in value:
        # 선별 어휘라 YAML 만 바꾼다.
        raise ValueError("policy.taxonomy 는 덮어쓸 수 없다")


def _nest(path: list[str], value: Any) -> dict[str, Any]:
    for key in reversed(path):
        value = {key: value}
    assert isinstance(value, dict)
    return value


def _overlay_error(base: dict[str, Any], fragment: dict[str, Any]) -> str | None:
    """fragment(섹션 하나짜리 덮어쓰기)를 base 에 얹었을 때의 검증 오류. 맞으면 None."""
    try:
        for name, value in fragment.items():
            _check_overlay_section(name, value)
        Rules.model_validate(merge_overlay(base, fragment))
    except ValueError as exc:  # pydantic ValidationError 도 ValueError 다
        return str(exc)
    return None


def _valid_part(base: dict[str, Any], path: list[str], value: dict[str, Any]) -> dict[str, Any]:
    """path 아래 dict 에서 얹어도 맞는 키만 남긴다. 틀린 값이 dict 면 안으로 내려가 다시 고른다.

    통째로 버리면 옛 키 하나 때문에 같은 dict 의 멀쩡한 설정(채널 끔, kind 가중치 등)이 사라진다.
    """
    kept: dict[str, Any] = {}
    for key, item in value.items():
        error = _overlay_error(base, _nest(path, {**kept, key: item}))
        if error is None:
            kept[key] = item
            continue
        if isinstance(item, dict):
            inner_base = merge_overlay(base, _nest(path, kept))
            if inner := _valid_part(inner_base, [*path, key], item):
                kept[key] = inner
            continue
        log.warning("config.prefs_key_ignored", path=".".join([*path, key]), error=error)
    return kept


def _apply_overlay(
    base: dict[str, Any], overlay: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """덮어쓰기를 섹션 단위로 얹고 (병합 결과, 실제로 쓴 덮어쓰기) 를 돌려준다.

    섹션이 검증에 실패하면 맞지 않는 키만 경고 후 버린다. 다 버려진 섹션은 남기지 않는다.
    """
    merged = base
    kept: dict[str, Any] = {}
    for name, value in overlay.items():
        if name in PREFS_NON_RULES_KEYS:
            kept[name] = value
            continue
        if not isinstance(value, dict) or name not in Rules.model_fields:
            log.warning("config.prefs_key_ignored", path=name, error="알 수 없는 섹션")
            continue
        if _overlay_error(merged, {name: value}) is not None:
            value = _valid_part(merged, [name], value)
        if value:
            merged = merge_overlay(merged, {name: value})
            kept[name] = value
    return merged, kept


def rules_with_overlay(base: dict[str, Any], overlay: dict[str, Any]) -> Rules:
    """YAML 위에 덮어쓰기를 얹는다. 틀린 키는 버린다.

    YAML 키가 바뀌어 옛 덮어쓰기가 안 맞아도 기동을 멈추지 않는다. YAML 자체가 틀리면 실패한다.
    """
    merged, _ = _apply_overlay(base, overlay)
    return Rules.model_validate(merged)


def sanitize_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    """저장 경로용. 어차피 무시되는 틀린 키를 떼어 낸다.

    남겨 두면 그 위에 병합한 새 저장이 전부 검증에 걸려 앱에서 고칠 길이 없다.
    """
    _, kept = _apply_overlay(_read_yaml(CONFIG_DIR / "rules.yaml"), overlay)
    return kept


def validate_overlay(overlay: dict[str, Any]) -> Rules:
    """저장 전 검증. 섹션 하나라도 틀리면 ValueError. 저장된 값은 rules_with_overlay 가 읽는다."""
    for name, value in overlay.items():
        if name not in PREFS_NON_RULES_KEYS:
            _check_overlay_section(name, value)
    sections = {k: v for k, v in overlay.items() if k not in PREFS_NON_RULES_KEYS}
    return Rules.model_validate(merge_overlay(_read_yaml(CONFIG_DIR / "rules.yaml"), sections))


def set_prefs_overlay(overlay: dict[str, Any], version: datetime | None = None) -> None:
    """기동 시·설정 저장 직후 부른다. 다음 get_rules() 부터 새 유효 설정이다.

    version 은 user_prefs.updated_at. 커밋은 행 잠금 순서대로지만 커밋 뒤 이 호출은 순서가
    섞일 수 있어, 이미 가진 것보다 오래된 저장은 버린다.
    """
    global _prefs_overlay, _prefs_version
    if version is not None and _prefs_version is not None and version < _prefs_version:
        return
    _prefs_overlay = copy.deepcopy(overlay)
    _prefs_version = version
    get_rules.cache_clear()


def effective_rules(overlay: dict[str, Any]) -> Rules:
    """저장 전 덮어쓰기(잠근 뒤 읽은 값)로 본 유효 설정. 프로세스 캐시와 따로 계산한다."""
    return rules_with_overlay(_read_yaml(CONFIG_DIR / "rules.yaml"), overlay)


def yaml_rules() -> Rules:
    """덮어쓰기 없는 YAML 값. 앱이 '기본값으로 되돌리기' 를 계산할 때 쓴다."""
    return Rules.model_validate(_read_yaml(CONFIG_DIR / "rules.yaml"))


@functools.lru_cache(maxsize=1)
def get_rules() -> Rules:
    """유효 설정 = config/rules.yaml + 앱 덮어쓰기 (단일 프로세스 전역)."""
    return rules_with_overlay(_read_yaml(CONFIG_DIR / "rules.yaml"), _prefs_overlay)


@functools.lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    return AppConfig.model_validate(_read_yaml(CONFIG_DIR / "app.yaml"))


@functools.lru_cache(maxsize=1)
def get_source_configs() -> list[SourceConfig]:
    raw = _read_yaml(CONFIG_DIR / "sources.yaml")
    sources = raw.get("sources", [])
    assert isinstance(sources, list)
    configs = [SourceConfig.model_validate(s) for s in sources]
    names = [c.name for c in configs]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        # 이름이 소스 행·잡 ID·앱 소스 ID 다. 겹치면 어느 쪽이 이기는지 조용히 정하지 않는다.
        raise ValueError(f"sources.yaml 에 이름이 겹치는 소스가 있다: {duplicated}")
    return configs


def reload_configs() -> None:
    """YAML 을 다시 읽는다 (rules.yaml 핫리로드용). 덮어쓰기는 그대로 유지된다."""
    get_rules.cache_clear()
    get_source_configs.cache_clear()
    get_app_config.cache_clear()
