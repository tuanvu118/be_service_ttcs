from beanie import PydanticObjectId
from pydantic import BaseModel, Field

class ManualAttendanceRequest(BaseModel):
    event_id: PydanticObjectId
    user_id: PydanticObjectId
    event_type: str = Field(default="public", pattern="^(public|unit)$")

class ManualAttendanceResponse(BaseModel):
    message: str = "Điểm danh thủ công thành công"
    event_id: PydanticObjectId
    user_id: PydanticObjectId
    event_type: str
