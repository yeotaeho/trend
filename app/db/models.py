# SQLAlchemy 모델 — 파이프라인 테이블(sources·items·decisions·…·llm_calls)과 사용자·앱 테이블

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import Vector
from app.schemas import Category, ItemStatus

Json = JSONB().with_variant(JSON(), "sqlite")
StrArray = ARRAY(Text()).with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    config: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    poll_interval_sec: Mapped[int] = mapped_column(Integer, default=900)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    # sources.yaml 의 trust_score 는 그대로 두고, 피드백으로 보정한 값은 여기. NULL 이면 미보정.
    trust_adjusted: Mapped[float | None] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("url_hash", name="uq_items_url_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    # 피드에서 오는 문자열은 길이를 보장할 수 없다. varchar(n) 은 Postgres 에서
    # 성능 이득이 없고 적재 크래시만 만든다.
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    url_normalized: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    summary_raw: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped[str] = mapped_column(String(30), default=Category.UNKNOWN.value)
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.NEW.value, index=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    raw: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    # 적재 시점의 `제목 + 본문 300자` 임베딩. NULL 은 미계산 또는 실패. 파이썬에서 읽지 않는다
    # (deferred). 비교는 전부 SQL. 모델을 바꾸면 embedding_model 이 달라진 행을 백필이 재계산한다.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), deferred=True)
    embedding_model: Mapped[str | None] = mapped_column(Text)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(10))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    details: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Summary(Base):
    __tablename__ = "summaries"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    title_ko: Mapped[str] = mapped_column(Text)
    summary_ko: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(StrArray, default=list)
    importance: Mapped[int] = mapped_column(Integer)
    worth_notifying: Mapped[bool] = mapped_column(Boolean)
    model: Mapped[str] = mapped_column(String(100))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 기본값이 없다. 빠뜨리면 NOT NULL 위반으로 드러나야 한다.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(20))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    message_id: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(Text)
    # 발송한 제목 (형제 버전 병기 포함). NULL 이면 summaries.title_ko 를 쓴다.
    title: Mapped[str | None] = mapped_column(Text)


class Feedback(Base):
    __tablename__ = "feedback"
    # 판정은 (사용자, 항목) 당 하나. 다시 누르면 덮어쓴다 (웹훅 upsert).
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_feedback_user_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    # useful | useless | cleared (앱 해제). 집계·사례는 useful·useless 만 본다.
    verdict: Mapped[str] = mapped_column(String(10))
    # discord | telegram | app. 앱 판정이 리액션 폴링보다 우선한다.
    source: Mapped[str] = mapped_column(String(10), server_default="discord")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LlmCall(Base):
    """LLM 호출 직전에 독립 트랜잭션으로 커밋하는 예약 행. 일일 상한은 이 표로 센다."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)  # triage | judge | explore
    batch_id: Mapped[str] = mapped_column(String(36))
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class UserPrefs(Base):
    """앱 설정 덮어쓰기. `data` 키는 Rules 섹션 이름을 따르고 YAML 위에 깊은 병합한다."""

    __tablename__ = "user_prefs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(Json, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BookmarkFolder(Base):
    __tablename__ = "bookmark_folders"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_bookmark_folders_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bookmark(Base):
    """찜. 키는 (사용자, 항목) — 앱의 alert_id 가 items.id 다."""

    __tablename__ = "bookmarks"
    __table_args__ = (Index("ix_bookmarks_user_saved_at", "user_id", "saved_at"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookmark_folders.id", ondelete="SET NULL"), index=True
    )
    memo: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=false())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # 읽지 않은 찜 재알림을 보낸 시각. 한 번만 보낸다.
    resurfaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    """FCM 기기 토큰. 활성 = disabled_at IS NULL."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(String(10))  # android | ios
    app_version: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class WeeklyReport(Base):
    """주간 리포트 저장본. 같은 주를 다시 만들면 덮어쓴다."""

    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_weekly_reports_user_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(Text)
    subtitle: Mapped[str] = mapped_column(Text)
    sections: Mapped[dict[str, Any]] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
