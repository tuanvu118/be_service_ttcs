from datetime import datetime, timezone
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RefreshTokenSession(Document):
    user_id: PydanticObjectId
    jti: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "refresh_token_sessions"
