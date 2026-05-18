from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, status

from schemas.attendance import ManualAttendanceRequest, ManualAttendanceResponse
from schemas.auth import TokenData
from internal_auth import get_current_user_from_gateway
from services.manual_attendance_service import ManualAttendanceService

router = APIRouter(prefix="/manual-attendance", tags=["Manual Attendance"])

@router.post(
    "/mark",
    response_model=ManualAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mark_manual_attendance(
    request_body: ManualAttendanceRequest,
    current_user: TokenData = Depends(get_current_user_from_gateway),
):
    """
    Điểm danh thủ công cho sinh viên (chỉ dành cho Admin/Manager).
    """
    return await ManualAttendanceService.mark_manual_attendance(
        actor_id=PydanticObjectId(current_user.sub),
        request=request_body,
    )
