# SQLAlchemy 모델 — sources / items / decisions / summaries / notifications / feedback

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas import Category, ItemStatus

Json = JSONB().with_variant(JSON(), "sqlite")
StrArray = ARRAY(Text()).with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    config: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    poll_interval_sec: Mapped[int] = mapped_column(Integer, default=900)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("url_hash", name="uq_items_url_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    url_normalized: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    summary_raw: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped[str] = mapped_column(String(30), default=Category.UNKNOWN.value)
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.NEW.value, index=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    raw: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(10))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    details: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(10))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    message_id: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(Text)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    verdict: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
