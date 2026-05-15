from beanie import Document, PydanticObjectId
from datetime import datetime
from enum import Enum
from pydantic import Field
from typing import Optional

class UnitEventSubmissionStatus(str, Enum):
    WAITING = "WAITING"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class UnitEventSubmission(Document):
    unitEventId: PydanticObjectId
    unitId: PydanticObjectId

    content: Optional[str] = None
    evidenceUrl: Optional[str] = None
    status: UnitEventSubmissionStatus = Field(default=UnitEventSubmissionStatus.PENDING)
    submittedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "unit_event_submissions"
        