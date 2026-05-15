from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel


class UnitMemberCreate(BaseModel):
    student_id: str


class UnitMemberRead(BaseModel):
    user_id: PydanticObjectId
    full_name: str
    student_id: str
    class_name: str
    email: str
    avatar_url: Optional[str] = None
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId
    joined_at: datetime


class UnitMemberListResponse(BaseModel):
    items: list[UnitMemberRead]
    total: int
    skip: int
    limit: int
