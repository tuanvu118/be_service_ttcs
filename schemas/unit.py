from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict


class UnitBase(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    cover_url: Optional[str] = None
    introduction: Optional[str] = None
    type: Optional[str] = None
    established_year: Optional[int] = None
    email: Optional[str] = None
    fb_url: Optional[str] = None
    member_count: Optional[int] = 0


class UnitCreate(UnitBase):
    name: str
    type: Optional[str] = None


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    introduction: Optional[str] = None
    type: Optional[str] = None
    established_year: Optional[int] = None
    member_count: Optional[int] = None
    cover_url: Optional[str] = None
    email: Optional[str] = None
    fb_url: Optional[str] = None


class UnitRead(UnitBase):
    id: PydanticObjectId

    model_config = ConfigDict(from_attributes=True)


class UnitListResponse(BaseModel):
    items: list[UnitRead]
    total: int
    skip: int
    limit: int
