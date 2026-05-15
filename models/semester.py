from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field


class Semester(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    name: str
    academic_year: str
    start_date: datetime
    end_date: datetime
    is_active: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "semesters"
