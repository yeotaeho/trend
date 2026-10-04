# 설정 로더 — .env 시크릿(pydantic-settings)과 config/*.yaml 규칙·소스·앱 정적값

from __future__ import annotations

import copy
import functools
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import JsonDict
from pydantic.fields import FieldInfo
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


# 앱이 바꿀 수 있는 값의 한도. 설정 모델 검증과 앱 API(/meta·쓰기 스키마)가 이 값 하나를 쓴다.
# kind 가중치는 감점 전용이다(10-01 사용자 결정). 가점은 09-09 실측으로 기각했다.
KIND_WEIGHT_MIN = -0.5
KIND_WEIGHT_MAX = 0.0
DAILY_PUSH_CAP_MIN = 1
DAILY_PUSH_CAP_MAX = 50
INTERESTS_MAX_CHARS = 1000
NOT_INTERESTED_MAX_CHARS = 500
WATCH_KEYWORDS_MAX = 50

Scope = Literal["user", "global"]
KindWeight = Annotated[float, Field(ge=KIND_WEIGHT_MIN, le=KIND_WEIGHT_MAX)]


def app_field(**kwargs: Any) -> Any:
    """앱이 덮어쓸 수 있는 키(user_prefs). 저장하면 다음 잡부터 반영된다."""
    meta: JsonDict = {"owner": "app", "apply": "next_job", "scope": "user"}
    return Field(json_schema_extra=meta, **kwargs)


def yaml_field(*, scope: Scope = "global", **kwargs: Any) -> Any:
    """YAML 이 주인인 키. 앱은 읽기만 하고, 바꾸면 배포 때 반영된다."""
    meta: JsonDict = {"owner": "yaml", "apply": "deploy", "scope": scope}
    return Field(json_schema_extra=meta, **kwargs)


class SourceConfig(BaseModel):
    """config/sources.yaml 한 항목. `config` 는 소스 타입별 자유 필드."""

    name: str = yaml_field()
    type: str = yaml_field()
    config: dict[str, Any] = yaml_field(default_factory=dict)
    poll_interval_sec: int = yaml_field(default=900, ge=300)
    trust_score: float = yaml_field(default=0.5, ge=0, le=1)
    # 06 화면 토글. 앱이 끈 값은 user_prefs.sources 에 있고 sync_sources 가 반영한다.
    enabled: bool = app_field(default=True)


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

    interests: str = app_field(default="", max_length=INTERESTS_MAX_CHARS)
    not_interested: str = app_field(default="", max_length=NOT_INTERESTED_MAX_CHARS)
    focus_repos: list[str] = app_field(default_factory=list)
    focus_stack: list[str] = app_field(default_factory=list)
    # 선별 topics 의 분류표 (slug). 앱 표시 라벨은 config/app.yaml 이 따로 가진다.
    taxonomy: list[str] = yaml_field(default_factory=lambda: list(DEFAULT_TAXONOMY))
    # 앱 관심사 화면에서 고른 카테고리. 거름망이 아니라 프롬프트 힌트다. 생략하면 taxonomy 전체.
    categories: list[str] = app_field(default_factory=list)

    @model_validator(mode="after")
    def _categories_within_taxonomy(self) -> PolicyConfig:
        if "categories" not in self.model_fields_set:
            self.categories = list(self.taxonomy)
        unknown = [c for c in self.categories if c not in self.taxonomy]
        if unknown:
            raise ValueError(f"policy.categories 에 taxonomy 밖 slug 가 있다: {unknown}")
        return self

    @model_validator(mode="after")
    def _keywords_within_limit(self) -> PolicyConfig:
        # 앱 04 의 관심 키워드 한 목록이 두 키로 나뉘어 저장된다(저장소 경로는 focus_repos).
        count = len(self.focus_stack) + len(self.focus_repos)
        if count > WATCH_KEYWORDS_MAX:
            limit = WATCH_KEYWORDS_MAX
            raise ValueError(f"focus_stack·focus_repos 는 합쳐 {limit}개까지다: {count}")
        return self


class ExcludeConfig(_Strict):
    keywords: list[str] = yaml_field(default_factory=list)
    domains: list[str] = yaml_field(default_factory=list)


class DedupeConfig(_Strict):
    # 2026-09-06 표본 보정값. 0.90~0.95 는 같은 채널의 다른 영상·다른 릴리즈였고,
    # 0.80~0.85 는 arXiv 두 피드의 주제 이웃이었다. rules.yaml 이 우선한다.
    dup_threshold: float = yaml_field(default=0.96, gt=0, le=1)
    related_threshold: float = yaml_field(default=0.88, gt=0, le=1)
    window_hours: int = yaml_field(default=72, ge=1, le=168)

    @model_validator(mode="after")
    def _related_not_above_dup(self) -> DedupeConfig:
        if self.related_threshold > self.dup_threshold:
            raise ValueError("dedupe.related_threshold 는 dup_threshold 이하여야 한다")
        return self


class TriageConfig(_Strict):
    batch_size: int = yaml_field(default=25, ge=1, le=40)
    daily_cap_calls: int = yaml_field(default=60, ge=0, le=200)
    min_batch: int = yaml_field(default=10, ge=1)
    max_wait_minutes: int = yaml_field(default=60, ge=1, le=240)


class ScoringConfig(_Strict):
    # 2026-09-10 조정. 소스 신뢰도가 arXiv 의 신호 밀도를 대신 벌하고 있어 비중을 관련도로 옮겼다.
    w_src: float = yaml_field(default=0.20, ge=0, le=1)
    w_rel: float = yaml_field(default=0.30, ge=0, le=1)
    w_hot: float = yaml_field(default=0.2, ge=0, le=1)
    w_multi: float = yaml_field(default=0.2, ge=0, le=1)
    w_fresh: float = yaml_field(default=0.1, ge=0, le=1)
    threshold: float = yaml_field(default=0.45, ge=0, le=1)
    # 모든 소스 공통. 이보다 오래된 항목은 선별 호출 없이 stale 로 버린다.
    max_age_hours: int = yaml_field(default=72, ge=1, le=168)
    # kind 별 감점(−0.5~0). 곱이 아니라 그대로 더한다. 없는 kind 는 0. 키가 Kind 밖이면 기동 실패.
    # 가점(technique +0.10)은 실측으로 arXiv 154건/2.5일을 판정에 보내 범위에서 뺐다.
    kind_weights: dict[Kind, KindWeight] = app_field(
        default_factory=lambda: {Kind.SURVEY: -0.15, Kind.TUTORIAL: -0.05, Kind.PROMO: -0.30}
    )


Delivery = Literal["instant", "quiet", "feed_only"]


class DeliveryByImportanceConfig(_Strict):
    """importance 구간 → 알림 강도. notify/policy.py 의 delivery_for 가 읽는다."""

    high: Delivery = app_field(default="instant")
    mid: Delivery = app_field(default="quiet")
    low: Delivery = app_field(default="feed_only")


class ChannelsConfig(_Strict):
    fcm: bool = app_field(default=True)
    discord: bool = app_field(default=True)
    telegram: bool = app_field(default=False)


class NotifyConfig(_Strict):
    daily_push_cap: int = app_field(default=15, ge=DAILY_PUSH_CAP_MIN, le=DAILY_PUSH_CAP_MAX)
    quiet_start_hour: int = app_field(default=23, ge=0, le=23)
    quiet_end_hour: int = app_field(default=8, ge=0, le=23)
    timezone: str = yaml_field(default="Asia/Seoul", scope="user")
    explore_judge_cap: int = yaml_field(default=3, ge=0, le=10)
    # 같은 cluster_id 를 하루에 보내는 서로 다른 항목 수 상한. 0 = 끔.
    cluster_daily_cap: int = app_field(default=1, ge=0, le=5)
    delivery_by_importance: DeliveryByImportanceConfig = Field(
        default_factory=DeliveryByImportanceConfig
    )
    explore_enabled: bool = app_field(default=True)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"notify.timezone 이 IANA 시간대 이름이 아니다: {value!r}") from exc
        return value


class Rules(_Strict):
    """config/rules.yaml — 정책·제외 규칙·임계값·발송 정책."""

    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)
    dedupe: DedupeConfig = Field(default_factory=DedupeConfig)
    triage: TriageConfig = Field(default_factory=TriageConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


class OnboardingConfig(_Strict):
    done: int = yaml_field(default=8, ge=0)
    total: int = yaml_field(default=8, ge=0)


class AppConfig(_Strict):
    """config/app.yaml — 앱 화면과 찜 재알림 잡이 읽는 정적값. 선별·판정은 읽지 않는다."""

    onboarding: OnboardingConfig = Field(default_factory=OnboardingConfig)
    personal_model_threshold: int = yaml_field(default=50, ge=1)
    resurface_unread_after_days: int = yaml_field(default=7, ge=1, le=30, scope="user")
    screening_relevance_floor: float = yaml_field(default=0.5, ge=0, le=1)
    planned_sources: list[str] = yaml_field(default_factory=list)
    # policy.taxonomy slug → 표시 라벨. 없는 slug 는 slug 를 그대로 라벨로 쓴다.
    taxonomy_labels: dict[str, str] = yaml_field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


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


def _sub_model(info: FieldInfo | None) -> type[BaseModel] | None:
    sub = info.annotation if info else None
    return sub if isinstance(sub, type) and issubclass(sub, BaseModel) else None


def _app_owned(info: FieldInfo | None) -> bool:
    extra = info.json_schema_extra if info else None
    return isinstance(extra, dict) and extra.get("owner") == "app"


def _owned_part(
    value: dict[str, Any], model: type[BaseModel], path: list[str], dropped: list[str]
) -> dict[str, Any]:
    """value 에서 앱 소유 키만 남긴다. 하위 모델은 안으로 내려가고 그 밖은 필드 주인을 본다.

    kind_weights 처럼 값이 dict 인 필드도 키 하나다. 모르는 키·주인이 앱이 아닌 키는 경로를
    dropped 에 쌓는다.
    """
    kept: dict[str, Any] = {}
    for key, item in value.items():
        info = model.model_fields.get(key)
        sub = _sub_model(info)
        if sub and isinstance(item, dict):
            if part := _owned_part(item, sub, [*path, key], dropped):
                kept[key] = part
        elif _app_owned(info):
            kept[key] = item
        else:
            dropped.append(".".join([*path, key]))
    return kept


def _split_owned(overlay: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """(앱 소유 키만 남긴 덮어쓰기, 버린 키 경로). 키마다 주인이 하나다(에픽 #30).

    sources 는 Rules 밖이다. sources.yaml 에 있는 이름 아래가 SourceConfig 이고
    sync_sources 가 읽는다.
    """
    dropped: list[str] = []
    kept = _owned_part({k: v for k, v in overlay.items() if k != "sources"}, Rules, [], dropped)
    sources = overlay.get("sources", {})
    if not isinstance(sources, dict):
        dropped.append("sources")
        sources = {}
    names = {c.name for c in get_source_configs()}
    for name, item in sources.items():
        if name in names and isinstance(item, dict):
            if part := _owned_part(item, SourceConfig, ["sources", name], dropped):
                kept.setdefault("sources", {})[name] = part
        else:
            dropped.append(f"sources.{name}")
    return kept, dropped


def _nest(path: list[str], value: Any) -> dict[str, Any]:
    for key in reversed(path):
        value = {key: value}
    assert isinstance(value, dict)
    return value


def _overlay_error(base: dict[str, Any], fragment: dict[str, Any]) -> str | None:
    """fragment(섹션 하나짜리 덮어쓰기)를 base 에 얹었을 때의 검증 오류. 맞으면 None."""
    try:
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
    """앱 소유 키만 섹션 단위로 얹고 (병합 결과, 실제로 쓴 덮어쓰기) 를 돌려준다.

    주인이 앱이 아니거나 모르는 키, 검증에 실패하는 키는 경고 후 버린다. 다 버려진 섹션은
    남기지 않는다.
    """
    owned, dropped = _split_owned(overlay)
    for path in dropped:
        log.warning("config.prefs_key_ignored", path=path, error="앱이 덮어쓸 수 없는 키")
    merged = base
    kept: dict[str, Any] = {}
    for name, value in owned.items():
        if name == "sources":
            kept[name] = value
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
    """저장 전 검증. 앱 소유가 아닌 키가 있거나 합친 값이 틀리면 ValueError.

    저장된 값은 rules_with_overlay 가 읽는다.
    """
    _, dropped = _split_owned(overlay)
    if dropped:
        raise ValueError(f"앱에서 바꿀 수 없는 설정 키다: {', '.join(dropped)}")
    sections = {k: v for k, v in overlay.items() if k != "sources"}
    return Rules.model_validate(merge_overlay(_read_yaml(CONFIG_DIR / "rules.yaml"), sections))


def prune_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    """YAML 값과 같은 말단을 지운 사본. 차이만 남겨야 YAML 을 고쳤을 때 앱 값에 가려지지 않는다.

    dict 는 말단 단위(kind_weights 는 kind 마다), 목록은 통째로 비교한다. 생략된 categories 의
    YAML 값은 검증기가 채운 taxonomy 전체다.
    """
    return _differences(overlay, _yaml_values())


def _yaml_values() -> dict[str, Any]:
    """YAML 값 전체(JSON 모양). sources 는 이름 → SourceConfig 다."""
    values = yaml_rules().model_dump(mode="json")
    values["sources"] = {c.name: c.model_dump(mode="json") for c in get_source_configs()}
    return values


def _differences(value: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict) and isinstance(base.get(key), dict):
            if inner := _differences(item, base[key]):
                kept[key] = inner
        elif key not in base or item != base[key]:
            kept[key] = item
    return kept


def _collect(model: type[BaseModel], value: Any, path: list[str], leaves: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        return
    for key, info in model.model_fields.items():
        if key not in value:
            continue
        item, sub = value[key], _sub_model(info)
        if sub:
            _collect(sub, item, [*path, key], leaves)
        elif _app_owned(info) and isinstance(item, dict):
            leaves.update({".".join([*path, key, k]): v for k, v in item.items()})
        elif _app_owned(info):
            leaves[".".join([*path, key])] = item


def _app_leaves(values: dict[str, Any]) -> dict[str, Any]:
    """설정 모양 dict → {앱 소유 키 점 경로: 값}. kind_weights 는 kind 마다, sources 는 이름마다."""
    leaves: dict[str, Any] = {}
    _collect(Rules, values, [], leaves)
    sources = values.get("sources")
    if isinstance(sources, dict):
        for name, source in sources.items():
            _collect(SourceConfig, source, ["sources", name], leaves)
    return leaves


def overlay_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """두 덮어쓰기 사이에 유효값이 바뀐 앱 소유 키. [{key, old, new, default}]

    default 는 지금 YAML 값이다. 기동 때 config.default_changed 가 이 값과 비교한다.
    """
    yaml = _yaml_values()
    default = _app_leaves(yaml)
    old = _app_leaves(merge_overlay(yaml, before))
    return [
        {"key": key, "old": old.get(key), "new": new, "default": default.get(key)}
        for key, new in _app_leaves(merge_overlay(yaml, after)).items()
        if old.get(key) != new
    ]


def restorable(overlay: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """옛 저장값을 지금 모델·주인 기준으로 정리한다. (남길 덮어쓰기, 버린 키 경로)"""
    kept = sanitize_overlay(overlay)
    return kept, sorted(_leaf_paths(overlay) - _leaf_paths(kept))


def _leaf_paths(value: dict[str, Any], path: tuple[str, ...] = ()) -> set[str]:
    paths: set[str] = set()
    for key, item in value.items():
        if isinstance(item, dict) and item:
            paths |= _leaf_paths(item, (*path, key))
        else:
            paths.add(".".join((*path, key)))
    return paths


def warn_changed_defaults(overlay: dict[str, Any], then: dict[str, Any]) -> None:
    """앱 값이 있는 키 가운데 앱이 마지막으로 바꾼 뒤 YAML 값이 바뀐 키를 경고한다.

    그 키는 앱 값이 이겨 YAML 변경이 반영되지 않는다. then 은 키마다 마지막 이력의 default 이고,
    이력이 없는 키(#34 이전 저장)는 알 수 없어 넘어간다.
    """
    now = _app_leaves(_yaml_values())
    for key, value in _app_leaves(overlay).items():
        if key in then and then[key] != now.get(key):
            log.warning(
                "config.default_changed", key=key, value=value, then=then[key], now=now.get(key)
            )


def app_key_path(key: str) -> list[str] | None:
    """점 경로가 앱 소유 키면 경로 목록, 아니면 None. 섹션·하위 모델 자체는 키가 아니다.

    예) notify.daily_push_cap, scoring.kind_weights.survey, sources.rss:openai.enabled
    """
    path = key.split(".")
    _, dropped = _split_owned(_nest(path, None))
    return None if dropped else path


def without_key(overlay: dict[str, Any], path: list[str]) -> dict[str, Any]:
    """path 의 덮어쓰기를 뺀 사본. 비게 된 상위 dict 는 저장 때 prune_overlay 가 지운다."""
    result = copy.deepcopy(overlay)
    parent: Any = result
    for key in path[:-1]:
        parent = parent.get(key)
        if not isinstance(parent, dict):
            return result
    parent.pop(path[-1], None)
    return result


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
    """덮어쓰기 없는 YAML 값. 저장 때 이 값과 같은 덮어쓰기를 지운다(prune_overlay)."""
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
