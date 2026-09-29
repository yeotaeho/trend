# 화면 11 찜 — 폴더·찜 목록·추가·수정·해제 (B7)

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query, Response

from app.api.v1.alerts import existing_item_id
from app.api.v1.deps import Session, UserId
from app.api.v1.errors import ApiError
from app.api.v1.pagination import Paging
from app.api.v1.queries.saved import (
    UNFILED,
    FolderFilter,
    create_folder,
    delete_bookmark,
    delete_folder,
    folder_exists,
    folder_list,
    get_folder,
    get_saved,
    move_folder,
    parse_id,
    rename_folder,
    saved_page,
    update_bookmark,
    upsert_bookmark,
)
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.saved import (
    Folder,
    FolderIn,
    FolderList,
    FolderPatch,
    SavedItem,
    SavedPatch,
    SavedPut,
    SavedSort,
)

router = APIRouter()


async def existing_folder_id(session: Session, user_id: int, folder_id: str) -> int:
    """현재 사용자의 폴더 ID. 숫자가 아니거나 없거나 남의 폴더면 404."""
    fid = parse_id(folder_id)
    if fid is None or not await folder_exists(session, user_id, fid):
        raise ApiError(404, "not_found", "폴더를 찾을 수 없습니다.", {"folder_id": folder_id})
    return fid


async def _saved_or_404(session: Session, user_id: int, item_id: int) -> SavedItem:
    saved = await get_saved(session, user_id, item_id)
    if saved is None:
        raise ApiError(404, "not_found", "찜을 찾을 수 없습니다.", {"alert_id": str(item_id)})
    return saved


# ---------- 폴더 ----------


@router.get("/folders")
async def get_folders(session: Session, user_id: UserId) -> FolderList:
    return await folder_list(session, user_id)


@router.post("/folders", status_code=201)
async def post_folder(body: FolderIn, session: Session, user_id: UserId) -> Folder:
    """맨 뒤에 만든다. 같은 사용자 안에서 이름이 겹치면 409 conflict."""
    return await create_folder(session, user_id, body.name)


@router.patch("/folders/{folder_id}")
async def patch_folder(
    folder_id: str, body: FolderPatch, session: Session, user_id: UserId
) -> Folder:
    fid = await existing_folder_id(session, user_id, folder_id)
    if body.name is not None:
        await rename_folder(session, user_id, fid, body.name)
    if body.position is not None:
        await move_folder(session, user_id, fid, body.position)
    folder = await get_folder(session, user_id, fid)
    assert folder is not None  # 위에서 존재를 확인했고 같은 트랜잭션이다
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def remove_folder(folder_id: str, session: Session, user_id: UserId) -> Response:
    """안의 찜은 미분류로 남는다. 없는 폴더여도 204."""
    fid = parse_id(folder_id)
    if fid is not None:
        await delete_folder(session, user_id, fid)
    return Response(status_code=204)


# ---------- 찜 ----------


@router.get("/saved")
async def get_saved_list(
    session: Session,
    user_id: UserId,
    paging: Paging,
    folder_id: Annotated[str | None, Query()] = None,
    unread_only: Annotated[bool, Query()] = False,
    sort: Annotated[SavedSort, Query()] = SavedSort.SAVED_DESC,
) -> Page[SavedItem]:
    """folder_id 는 폴더 ID 또는 unfiled, 생략하면 전체."""
    folder: FolderFilter = None
    if folder_id == UNFILED:
        folder = UNFILED
    elif folder_id is not None:
        folder = await existing_folder_id(session, user_id, folder_id)
    items, next_cursor = await saved_page(
        session, user_id, folder, unread_only=unread_only, sort=sort, page=paging
    )
    return Page[SavedItem](items=items, next_cursor=next_cursor)


@router.put("/saved/{alert_id}", status_code=201, responses={200: {"model": SavedItem}})
async def put_saved(
    alert_id: str,
    session: Session,
    user_id: UserId,
    response: Response,
    body: Annotated[SavedPut | None, Body()] = None,
) -> SavedItem:
    """새로 만들면 201, 이미 있으면 200. 본문이 없거나 {} 면 새 찜은 미분류다."""
    item_id = await existing_item_id(session, alert_id)
    body = body or SavedPut()
    set_folder = "folder_id" in body.model_fields_set
    folder = (
        await existing_folder_id(session, user_id, body.folder_id)
        if body.folder_id is not None
        else None
    )
    created = await upsert_bookmark(session, user_id, item_id, folder, set_folder=set_folder)
    if not created:
        response.status_code = 200
    return await _saved_or_404(session, user_id, item_id)


@router.patch("/saved/{alert_id}")
async def patch_saved(
    alert_id: str, body: SavedPatch, session: Session, user_id: UserId
) -> SavedItem:
    """보낸 키만 바꾼다. 찜이 없으면 404."""
    item_id = await existing_item_id(session, alert_id)
    sent = body.model_fields_set
    values: dict[str, Any] = {}
    if "folder_id" in sent:
        values["folder_id"] = (
            await existing_folder_id(session, user_id, body.folder_id)
            if body.folder_id is not None
            else None
        )
    if "memo" in sent:
        values["memo"] = body.memo or None
    if body.is_read is not None:
        values["is_read"] = body.is_read
    if not await update_bookmark(session, user_id, item_id, values):
        raise ApiError(404, "not_found", "찜을 찾을 수 없습니다.", {"alert_id": alert_id})
    return await _saved_or_404(session, user_id, item_id)


@router.delete("/saved/{alert_id}", status_code=204)
async def remove_saved(alert_id: str, session: Session, user_id: UserId) -> Response:
    """찜이 없어도 204. 알림(항목) 자체가 없으면 404."""
    item_id = await existing_item_id(session, alert_id)
    await delete_bookmark(session, user_id, item_id)
    return Response(status_code=204)
