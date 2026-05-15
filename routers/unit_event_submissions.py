from fastapi import APIRouter
from schemas.unit_event_submissions import (
    UnitEventSubmissionResponse,
    UnitEventSubmissionUpdate,
    UnitEventSubmissionStatusUpdate,
    UnitEventSubmissionMemberCreate,
    UnitEventSubmissionMemberUpdate,
    UnitEventSubmissionMemberResponse,
    UnitEventSubmissionWithUnitResponse,
    UnitEventSubmissionHTSKListItemResponse,
    HTSKStudentOverviewResponse,
    HTSKStudentRegisterRequest,
    HTSKStudentRegisterResponse,
)
from typing import List
from beanie import PydanticObjectId
from schemas.auth import TokenData
from security import require_manager, require_staff, require_user
from fastapi import Depends, Header, status
from schemas.unit_event_submissions import UnitEventSubmissionCreate
from services.unit_event_submissions_service import UnitEventSubmissionsService
from repositories.unit_event_submissions_repo import UnitEventSubmissionsRepo
from repositories.unit_event_submission_members_repo import UnitEventSubmissionMembersRepo
from schemas.response import BaseResponse

router = APIRouter(prefix="/unit-event-submissions", tags=["Unit Event Submissions"])

def get_unit_event_submission_service() -> UnitEventSubmissionsService:
    return UnitEventSubmissionsService(
        UnitEventSubmissionsRepo(),
        UnitEventSubmissionMembersRepo(),
    )

@router.post("/HTTT", response_model=UnitEventSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_unit_event_support_communication(
    data: UnitEventSubmissionCreate,
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionResponse:
    """
    Phản hồi sự kiện Hỗ trợ Truyền Thông cho đơn vị mình
    """
    return await service.create_unit_event_submission(data, current_user.sub)

@router.get("/HTTT", response_model=UnitEventSubmissionResponse)
async def get_unit_event_support_communication_by_unit_event_id(
    unit_event_id: PydanticObjectId,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionResponse:
    """
    Lấy phản hồi sự kiện Hỗ trợ Truyền Thông theo sự kiện id của đơn vị mình
    """
    return await service.get_unit_event_submissions_by_unit_event_id(
        unit_event_id, x_unit_id
    )


@router.get("/HTTT/all", response_model=List[UnitEventSubmissionWithUnitResponse])
async def get_all_unit_event_support_communication_by_unit_event_id(
    unit_event_id: PydanticObjectId,
    current_user: TokenData = Depends(require_manager),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> List[UnitEventSubmissionWithUnitResponse]:
    """
    Lấy tất cả phản hồi HTTT theo unit_event_id.
    Quyền: ADMIN hoặc MANAGER.
    """
    return await service.get_all_httt_submissions_by_unit_event_id(unit_event_id)


@router.put("/HTTT", response_model=UnitEventSubmissionResponse)
async def update_unit_event_support_communication(
    unit_event_id: PydanticObjectId,
    data: UnitEventSubmissionUpdate,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionResponse:
    """
    Sửa phản hồi sự kiện Hỗ trợ Truyền Thông theo unit_event_id và X-Unit-Id.

    Các trường có thể cập nhật:
    - content: str
    - evidenceUrl: str

    Quyền: Staff đơn vị
    Chỉ có thể sửa khi ở trạng thái PENDING hoặc REJECTED, sau khi sửa sẽ tự động chuyển sang trạng thái PENDING
    """
    return await service.update_unit_event_submission(unit_event_id, x_unit_id, data)


@router.post("/status", response_model=UnitEventSubmissionResponse)
async def update_unit_event_submission_status(
    data: UnitEventSubmissionStatusUpdate,
    current_user: TokenData = Depends(require_manager),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionResponse:
    """
    Cập nhật trạng thái phản hồi sự kiện (PENDING/APPROVED/REJECTED).
    Quyền: ADMIN hoặc MANAGER.
    """
    return await service.update_submission_status(data)

########################################################################################
#Phản hồi sự kiện có danh sách thành viên
########################################################################################
@router.post("/HTSK", response_model=UnitEventSubmissionMemberResponse)
async def create_unit_event_submission_member(
    data: UnitEventSubmissionMemberCreate,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionMemberResponse:
    """
    Tạo phản hồi HTSK có danh sách thành viên

    Danh sách thành viên: List[str] Mã sinh viên

    Quyền: Staff đơn vị

    Chỉ tạo được khi sự kiện đã được bắt đầu đăng kí và chưa kết thúc đăng kí

    Trạng thái sau khi tạo là APPROVED
    """
    return await service.create_unit_event_submission_member(data, x_unit_id)

@router.get("/HTSK", response_model=UnitEventSubmissionMemberResponse)
async def get_unit_event_submission_member_by_unit_event_id(
    unit_event_id: PydanticObjectId,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionMemberResponse:
    """
    Lấy phản hồi HTSK theo sự kiện id của đơn vị mình
    """
    return await service.get_unit_event_submissions_HTSK_by_unit_event_id(unit_event_id, x_unit_id)


@router.put("/HTSK", response_model=UnitEventSubmissionMemberResponse)
async def update_unit_event_submission_member(
    unit_event_id: PydanticObjectId,
    data: UnitEventSubmissionMemberUpdate,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> UnitEventSubmissionMemberResponse:
    """
    Sửa phản hồi HTSK theo unit_event_id và X-Unit-Id của đơn vị mình.

    Chỉ sửa được khi sự kiện đã được bắt đầu đăng kí và chưa kết thúc đăng kí, không quan tâm đến trạng thái phản hồi
    """
    return await service.update_unit_event_submission_member(unit_event_id, x_unit_id, data)


@router.get("/HTSK/list", response_model=List[UnitEventSubmissionHTSKListItemResponse])
async def get_all_unit_event_submission_members_by_unit_event_id(
    unit_event_id: PydanticObjectId,
    current_user: TokenData = Depends(require_manager),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> List[UnitEventSubmissionHTSKListItemResponse]:
    """
    Lấy danh sách sinh viên các đơn vị đã nộp lên theo unit_event_id (chỉ dành cho sự kiện HTSK).
    Quyền: ADMIN hoặc MANAGER.
    """
    return await service.get_all_htsk_members_by_unit_event_id(unit_event_id)


@router.get("/HTSK/student/overview", response_model=HTSKStudentOverviewResponse)
async def get_htsk_student_registration_overview(
    unit_event_id: PydanticObjectId,
    unit_id: PydanticObjectId,
    current_user: TokenData = Depends(require_user),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> HTSKStudentOverviewResponse:
    """
    Lấy thông tin sự kiện HTSK cho sinh viên đăng kí
    """
    return await service.get_htsk_student_registration_overview(
        unit_event_id=unit_event_id,
        unit_id=unit_id,
        current_user_id=current_user.sub,
    )


@router.post("/HTSK/student/register", response_model=HTSKStudentRegisterResponse)
async def register_htsk_student(
    data: HTSKStudentRegisterRequest,
    current_user: TokenData = Depends(require_user),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> HTSKStudentRegisterResponse:
    """
    Đăng kí sự kiện HTSK cho sinh viên
    """
    return await service.register_htsk_student(data, current_user.sub)


@router.delete("/HTSK/student/register", response_model=BaseResponse)
async def cancel_htsk_student_registration(
    data: HTSKStudentRegisterRequest,
    current_user: TokenData = Depends(require_user),
    service: UnitEventSubmissionsService = Depends(get_unit_event_submission_service),
) -> BaseResponse:
    """
    Hủy đăng kí sự kiện HTSK cho sinh viên
    """
    return await service.cancel_htsk_student_registration(data, current_user.sub)