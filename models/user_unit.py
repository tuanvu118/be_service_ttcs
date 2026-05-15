from datetime import datetime, timezone
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


def utcnow():
    return datetime.now(timezone.utc)


class UserUnit(Document):
    user_id: PydanticObjectId
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId
    is_active: bool = True
    joined_at: datetime = Field(default_factory=utcnow)
    left_at: Optional[datetime] = None
    added_by: Optional[PydanticObjectId] = None

    class Settings:
        name = "user_units"
