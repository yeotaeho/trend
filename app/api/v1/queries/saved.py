# 찜 SQL — 폴더 칩 집계·폴더 쓰기(이름 유니크·순서 이동), 찜 목록(필터·정렬 3종·커서)·추가·수정·해제

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    Boolean,
    ColumnElement,
    Select,
    and_,
    delete,
    func,
    literal_column,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import ApiError
from app.api.v1.pagination import PageParams, paginate
from app.api.v1.queries.alerts import (
    INT4_MAX,
    alert_title,
    first_delivery,
    source_display_name,
)
from app.api.v1.schemas.saved import Folder, FolderList, FolderRef, SavedItem, SavedSort
from app.db.models import Bookmark, BookmarkFolder, Item, Source, Summary

UNFILED: Literal["unfiled"] = "unfiled"
FOLDER_NAME_UNIQUE = "uq_bookmark_folders_user_name"
# GET /saved 의 폴더 조건. None = 전체, UNFILED = 미분류, int = 그 폴더.
FolderFilter = int | Literal["unfiled"] | None


def parse_id(raw: str) -> int | None:
    """경로·본문의 ID 문자열. ASCII 숫자이고 int4 범위여야 한다 (전각 숫자·범위 밖은 None)."""
    value = int(raw) if raw.isascii() and raw.isdecimal() else 0
    return value if 0 < value <= INT4_MAX else None


def folder_conflict(name: str) -> ApiError:
    return ApiError(409, "conflict", "같은 이름의 폴더가 이미 있습니다.", {"field": "name"})


# ---------- 폴더 ----------


def _folder_select(user_id: int) -> Select[Any]:
    """폴더와 그 안의 찜 수·안 읽은 수. 빈 폴더도 0 으로 나온다."""
    unread = func.count(Bookmark.item_id).filter(Bookmark.is_read.is_(False))
    return (
        select(
            BookmarkFolder.id,
            BookmarkFolder.name,
            BookmarkFolder.position,
            func.count(Bookmark.item_id).label("count"),
            unread.label("unread_count"),
        )
        .outerjoin(
            Bookmark,
            and_(Bookmark.folder_id == BookmarkFolder.id, Bookmark.user_id == user_id),
        )
        .where(BookmarkFolder.user_id == user_id)
        .group_by(BookmarkFolder.id)
    )


def _to_folder(row: Any) -> Folder:
    return Folder(
        id=str(row.id),
        name=row.name,
        count=row.count,
        unread_count=row.unread_count,
        position=row.position,
    )


async def folder_list(session: AsyncSession, user_id: int) -> FolderList:
    folders = (
        await session.execute(
            _folder_select(user_id).order_by(BookmarkFolder.position, BookmarkFolder.id)
        )
    ).all()
    totals = (
        await session.execute(
            select(
                func.count().label("total"),
                func.count().filter(Bookmark.is_read.is_(False)).label("unread"),
                func.count().filter(Bookmark.folder_id.is_(None)).label("unfiled"),
            ).where(Bookmark.user_id == user_id)
        )
    ).one()
    return FolderList(
        total_count=totals.total,
        unread_count=totals.unread,
        unfiled_count=totals.unfiled,
        folders=[_to_folder(r) for r in folders],
    )


async def get_folder(session: AsyncSession, user_id: int, folder_id: int) -> Folder | None:
    row = (
        await session.execute(_folder_select(user_id).where(BookmarkFolder.id == folder_id))
    ).first()
    return _to_folder(row) if row else None


async def folder_exists(session: AsyncSession, user_id: int, folder_id: int) -> bool:
    found = await session.scalar(
        select(BookmarkFolder.id).where(
            BookmarkFolder.id == folder_id, BookmarkFolder.user_id == user_id
        )
    )
    return found is not None


async def create_folder(session: AsyncSession, user_id: int, name: str) -> Folder:
    """맨 뒤 자리에 만든다. 같은 사용자 안에서 이름이 겹치면 409."""
    last = (
        select(func.coalesce(func.max(BookmarkFolder.position) + 1, 0))
        .where(BookmarkFolder.user_id == user_id)
        .scalar_subquery()
    )
    stmt = (
        insert(BookmarkFolder)
        .values(user_id=user_id, name=name, position=last)
        .on_conflict_do_nothing(constraint=FOLDER_NAME_UNIQUE)
        .returning(BookmarkFolder.id, BookmarkFolder.position)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise folder_conflict(name)
    return Folder(id=str(row.id), name=name, count=0, unread_count=0, position=row.position)


async def rename_folder(session: AsyncSession, user_id: int, folder_id: int, name: str) -> None:
    """이름 충돌은 409. 세이브포인트 안에서 바꿔 요청 트랜잭션을 살려 둔다."""
    try:
        async with session.begin_nested():
            await session.execute(
                update(BookmarkFolder)
                .where(BookmarkFolder.id == folder_id, BookmarkFolder.user_id == user_id)
                .values(name=name)
            )
    except IntegrityError as exc:
        raise folder_conflict(name) from exc


async def move_folder(session: AsyncSession, user_id: int, folder_id: int, position: int) -> None:
    """폴더를 position 번째로 옮기고 사용자의 폴더 전부를 0..n-1 로 다시 매긴다.

    position 이 끝을 넘으면 맨 뒤다. 폴더는 사용자당 몇 개뿐이라 행마다 갱신한다.
    """
    ids = list(
        (
            await session.scalars(
                select(BookmarkFolder.id)
                .where(BookmarkFolder.user_id == user_id)
                .order_by(BookmarkFolder.position, BookmarkFolder.id)
                .with_for_update()
            )
        ).all()
    )
    ids.remove(folder_id)
    ids.insert(position, folder_id)
    for index, fid in enumerate(ids):
        await session.execute(
            update(BookmarkFolder)
            .where(BookmarkFolder.id == fid, BookmarkFolder.position != index)
            .values(position=index)
        )


async def delete_folder(session: AsyncSession, user_id: int, folder_id: int) -> None:
    """안의 찜은 FK ON DELETE SET NULL 로 미분류가 된다. 없는 폴더여도 조용히 지나간다."""
    await session.execute(
        delete(BookmarkFolder).where(
            BookmarkFolder.id == folder_id, BookmarkFolder.user_id == user_id
        )
    )


# ---------- 찜 ----------


def _saved_select(user_id: int) -> tuple[Select[Any], ColumnElement[Any]]:
    """SavedItem 한 장에 필요한 열과 전달 시각 열. 전달 시각·제목은 피드와 같은 첫 전달 행."""
    delivery = first_delivery(user_id)
    stmt = (
        select(
            Bookmark.item_id,
            Bookmark.saved_at,
            Bookmark.memo,
            Bookmark.is_read,
            Bookmark.read_at,
            Item.title.label("item_title"),
            Item.url,
            Source.name.label("source_id"),
            Source.config.label("source_config"),
            Summary.title_ko,
            delivery.c.sent_at,
            delivery.c.title.label("sent_title"),
            BookmarkFolder.id.label("folder_id"),
            BookmarkFolder.name.label("folder_name"),
        )
        .select_from(Bookmark)
        .join(Item, Item.id == Bookmark.item_id)
        .join(Source, Source.id == Item.source_id)
        .outerjoin(Summary, Summary.item_id == Item.id)
        .outerjoin(delivery, delivery.c.item_id == Item.id)
        .outerjoin(BookmarkFolder, BookmarkFolder.id == Bookmark.folder_id)
        .where(Bookmark.user_id == user_id)
    )
    return stmt, delivery.c.sent_at


def _to_saved(row: Any) -> SavedItem:
    return SavedItem(
        alert_id=str(row.item_id),
        source_name=source_display_name(row.source_id, row.source_config),
        title=alert_title(row.sent_title, row.title_ko, row.item_title),
        url=row.url,
        delivered_at=row.sent_at,
        saved_at=row.saved_at,
        folder=(
            FolderRef(id=str(row.folder_id), name=row.folder_name)
            if row.folder_id is not None
            else None
        ),
        memo=row.memo,
        is_read=row.is_read,
        read_at=row.read_at,
    )


def _cursor(key: dict[str, Any]) -> tuple[datetime | None, int]:
    """찜 커서 = 직전 페이지 마지막 카드의 (정렬 시각, alert_id). 전달 전 찜은 시각이 null."""
    try:
        raw, item_id = key["t"], int(key["id"])
        at = None if raw is None else datetime.fromisoformat(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.") from exc
    if not 0 < item_id <= INT4_MAX:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return at, item_id


def _after(column: Any, desc: bool, at: datetime | None, item_id: int) -> Any:
    """(column 방향, alert_id 내림차순, null 은 맨 뒤) 순서에서 커서 뒤에 오는 행."""
    tie = Bookmark.item_id < item_id
    if at is None:
        return and_(column.is_(None), tie)
    beyond = column < at if desc else column > at
    return or_(beyond, and_(column == at, tie), column.is_(None))


async def saved_page(
    session: AsyncSession,
    user_id: int,
    folder: FolderFilter,
    *,
    unread_only: bool,
    sort: SavedSort,
    page: PageParams,
) -> tuple[list[SavedItem], str | None]:
    """정렬 키가 같으면 alert_id 내림차순. 알림 시간 순에서 전달 전 찜은 맨 뒤다."""
    stmt, delivered_at = _saved_select(user_id)
    if folder == UNFILED:
        stmt = stmt.where(Bookmark.folder_id.is_(None))
    elif folder is not None:
        stmt = stmt.where(Bookmark.folder_id == folder)
    if unread_only:
        stmt = stmt.where(Bookmark.is_read.is_(False))

    column = delivered_at if sort is SavedSort.DELIVERED_DESC else Bookmark.saved_at
    desc = sort is not SavedSort.SAVED_ASC
    if page.after is not None:
        stmt = stmt.where(_after(column, desc, *_cursor(page.after)))
    order = column.desc() if desc else column.asc()
    stmt = stmt.order_by(order.nulls_last(), Bookmark.item_id.desc()).limit(page.limit + 1)

    field = "sent_at" if sort is SavedSort.DELIVERED_DESC else "saved_at"

    def key(row: Any) -> dict[str, Any]:
        at = getattr(row, field)
        return {"t": at.isoformat() if at else None, "id": row.item_id}

    rows, next_cursor = paginate((await session.execute(stmt)).all(), page.limit, key)
    return [_to_saved(r) for r in rows], next_cursor


async def get_saved(session: AsyncSession, user_id: int, item_id: int) -> SavedItem | None:
    stmt, _ = _saved_select(user_id)
    row = (await session.execute(stmt.where(Bookmark.item_id == item_id))).first()
    return _to_saved(row) if row else None


async def upsert_bookmark(
    session: AsyncSession, user_id: int, item_id: int, folder_id: int | None, *, set_folder: bool
) -> bool:
    """새로 만들었으면 True. 이미 있으면 set_folder 일 때만 폴더를 바꾸고 나머지는 그대로 둔다."""
    new = insert(Bookmark).values(user_id=user_id, item_id=item_id, folder_id=folder_id)
    folder = new.excluded.folder_id if set_folder else Bookmark.folder_id
    stmt = new.on_conflict_do_update(
        index_elements=[Bookmark.user_id, Bookmark.item_id], set_={"folder_id": folder}
    ).returning(literal_column("xmax = 0", Boolean).label("created"))
    return bool(await session.scalar(stmt))


async def update_bookmark(
    session: AsyncSession, user_id: int, item_id: int, values: dict[str, Any]
) -> bool:
    """찜이 있으면 True. values 가 비어도 존재만 확인한다.

    is_read=true 는 read_at 이 비어 있을 때만 지금으로 채운다 (처음 읽은 시각을 남긴다).
    is_read=false 는 read_at 을 비운다.
    """
    where = (Bookmark.user_id == user_id, Bookmark.item_id == item_id)
    if "is_read" in values:
        values = {
            **values,
            "read_at": func.coalesce(Bookmark.read_at, func.now()) if values["is_read"] else None,
        }
    if not values:
        found = await session.scalar(select(Bookmark.item_id).where(*where))
        return found is not None
    stmt = update(Bookmark).where(*where).values(**values).returning(Bookmark.item_id)
    return (await session.scalar(stmt)) is not None


async def delete_bookmark(session: AsyncSession, user_id: int, item_id: int) -> None:
    await session.execute(
        delete(Bookmark).where(Bookmark.user_id == user_id, Bookmark.item_id == item_id)
    )
