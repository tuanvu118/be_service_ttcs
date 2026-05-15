from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel
from typing import Optional

class UnitEventSubmissionMember(Document):
    unitEventId: Optional[PydanticObjectId] = None
    unitEventSubmissionId: PydanticObjectId
    studentId: Optional[str] = None  # Mã sinh viên (MSV) - dùng khi create
    userId: Optional[PydanticObjectId] = None  # User ID - dùng khi update
    checkIn: bool = False

    class Settings:
        name = "unit_event_submission_members"
        indexes = [
            IndexModel(
                [("unitEventSubmissionId", ASCENDING), ("userId", ASCENDING)],
                unique=True,
                partialFilterExpression={"userId": {"$type": "objectId"}},
            ),
            IndexModel(
                [("unitEventId", ASCENDING), ("userId", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "unitEventId": {"$type": "objectId"},
                    "userId": {"$type": "objectId"},
                },
            ),
        ]