from datetime import datetime, timezone
from typing import Optional, List
from beanie import Document, PydanticObjectId
from pydantic import Field, BaseModel


class OrganizationInfo(BaseModel):
    id: str  # String ID of the Unit
    name: str

class EventTime(BaseModel):
    start: datetime
    end: datetime

class EventPromotion(Document):
    title: str
    description: str
    organization: Optional[OrganizationInfo] = None
    
    # Relationships for filtering
    unit_id: Optional[PydanticObjectId] = None
    semester_id: Optional[PydanticObjectId] = None
    created_by_id: Optional[PydanticObjectId] = None

    status: str = "CHO_DUYET"  # CHO_DUYET | DA_DUYET | TU_CHOI
    image_url: Optional[str] = None
    external_links: Optional[List[str]] = []
    rejected_reason: Optional[str] = None
    
    time: Optional[EventTime] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "event_promotions"
        indexes = [
            "status",
            "unit_id",
            "time.start",
            "time.end"
        ]
