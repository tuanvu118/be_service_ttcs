from datetime import datetime, timezone
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(Document):
    user_id: PydanticObjectId
    role_id: PydanticObjectId
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId

    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "user_roles"
