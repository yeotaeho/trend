# 찜 응답·요청 모델 — 폴더 칩·폴더 쓰기, SavedItem 카드, 찜 추가·수정, 정렬 열거형

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.api.v1.schemas.common import FOLDER_NAME_MAX, MEMO_MAX, StrictIn, UtcDateTime

# 앞뒤 공백을 뗀 뒤 1~30자 (계약 4.7).
FolderName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=FOLDER_NAME_MAX)
]


class SavedSort(StrEnum):
    SAVED_DESC = "saved_desc"
    SAVED_ASC = "saved_asc"
    DELIVERED_DESC = "delivered_desc"


class Folder(BaseModel):
    id: str
    name: str
    count: int
    unread_count: int
    position: int


class FolderList(BaseModel):
    """칩 줄. 미분류 찜은 total_count·unread_count 에만 들어간다."""

    total_count: int
    unread_count: int
    unfiled_count: int
    folders: list[Folder]


class FolderIn(StrictIn):
    name: FolderName


class FolderPatch(StrictIn):
    """둘 다 선택. position 은 옮겨 갈 자리(0부터)이고 나머지 폴더는 순서를 지킨 채 밀린다."""

    name: FolderName | None = None
    position: int | None = Field(default=None, ge=0)


class FolderRef(BaseModel):
    id: str
    name: str


class SavedItem(BaseModel):
    """찜 카드. 발송된 적 없는 항목(걸러진 항목을 찜함)은 delivered_at 이 null."""

    alert_id: str
    source_name: str
    title: str
    url: str
    delivered_at: UtcDateTime | None
    saved_at: UtcDateTime
    folder: FolderRef | None
    memo: str | None
    is_read: bool
    read_at: UtcDateTime | None


class SavedPut(StrictIn):
    """생략하면 미분류로 만든다. 이미 있는 찜은 folder_id 를 보냈을 때만 폴더를 바꾼다."""

    folder_id: str | None = None


class SavedPatch(StrictIn):
    """보낸 키만 바꾼다. memo 빈 문자열은 null, is_read=true 는 read_at 을 채운다."""

    folder_id: str | None = None
    memo: str | None = Field(default=None, max_length=MEMO_MAX)
    is_read: bool | None = None
