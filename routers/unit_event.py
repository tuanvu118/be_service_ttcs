from fastapi import APIRouter, Depends, Query
from fastapi import status
from schemas.unit_event import (
    UnitEventCreate,
    UnitEventResponse,
    UnitEventResponseByUnitId,
    UnitEventUpdate,
    UnitEventPaginationResponse,
)
from schemas.response import BaseResponse
from security import require_manager, require_staff
from services.unit_event_service import UnitEventService
from repositories.unit_event_repo import UnitEventRepo
from schemas.auth import TokenData
from typing import List, Optional
from beanie import PydanticObjectId
from exceptions import ErrorCode, app_exception
from models.unit_event import UnitEventEnum

router = APIRouter(prefix="/unit-events", tags=["Unit Events"])

def get_unit_event_service() -> UnitEventService:
    return UnitEventService(UnitEventRepo())

import json
from fastapi import Form


def parse_list_unit_ids(raw_value: Optional[str]) -> list[str]:
    if raw_value is None:
        return []

    value = raw_value.strip()
    if not value:
        return []

    current = value
    for _ in range(2):
        try:
            parsed = json.loads(current)
        except json.JSONDecodeError:
            break

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        if isinstance(parsed, str):
            current = parsed.strip()
            continue

        break

    if value and not value.startswith("["):
        return [value]

    app_exception(
        ErrorCode.INVALID_FORM_FIELD,
        extra_detail='listUnitId phai la JSON array hop le, vi du: ["<unit_id>"]',
    )

@router.post("/", 
response_model=UnitEventResponse,
status_code=status.HTTP_201_CREATED,
dependencies=[Depends(require_manager)]
)
async def Create_Unit_Event(
    title: str = Form(...),
    description: str = Form(None),
    location: Optional[str] = Form(None),
    point: float = Form(0),
    type: str = Form(...),
    is_student_registration: bool = Form(False),
    limit_student_registration_in_one_unit: int = Form(10000),
    event_start: str = Form(...),
    event_end: str = Form(...),
    registration_start: Optional[str] = Form(None),
    registration_end: Optional[str] = Form(None),
    listUnitId: str = Form("[]"),
    semester_id: Optional[str] = Form(None),
    current_user: TokenData = Depends(require_manager),
    service: UnitEventService = Depends(get_unit_event_service),
) -> UnitEventResponse:
    """
    Tạo sự kiện đẩy xuống đơn vị (HTTT hoặc HTSK) với sự hỗ trợ của Multipart/Form-data.
    
    Với HTSK, bắt buộc phải điền thêm is_student_registration
    Với HTTT, không cần điền is_student_registration
    """
    from schemas.unit_event import UnitEventCreate
    from datetime import datetime
    from decimal import Decimal
    
    # Parse listUnitId từ JSON string
    unit_ids = parse_list_unit_ids(listUnitId)
    
    data = UnitEventCreate(
        title=title,
        description=description,
        location=location,
        point=Decimal(str(point)),
        type=type,
        is_student_registration=is_student_registration,
        limit_student_registration_in_one_unit=limit_student_registration_in_one_unit,
        event_start=datetime.fromisoformat(event_start),
        event_end=datetime.fromisoformat(event_end),
        registration_start=datetime.fromisoformat(registration_start) if registration_start else None,
        registration_end=datetime.fromisoformat(registration_end) if registration_end else None,
        listUnitId=unit_ids,
        semesterId=PydanticObjectId(semester_id) if semester_id else None
    )
    
    if data.type == UnitEventEnum.HTSK and data.is_student_registration:
        return await service.create_unit_event_student_registration(data, current_user.sub)
    return await service.create_unit_event(data, current_user.sub)

@router.get("/all", response_model=UnitEventPaginationResponse, dependencies=[Depends(require_manager)])
async def Get_All_Unit_Events_By_Semester(
    semester_id: Optional[PydanticObjectId] = Query(None, alias="semesterId"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    _ = Depends(require_manager),
    service: UnitEventService = Depends(get_unit_event_service),
) -> UnitEventPaginationResponse:
    """
    Lấy danh sách tất cả sự kiện đẩy xuống đơn vị (bao gồm cả HTTT và HTSK) theo kì học
    
    Query: semesterId - id kỳ học cần lọc.

    Quyền xem: VPĐ hoặc ADMIN
    """
    return await service.get_all_unit_events_by_semester_id(semester_id, skip=skip, limit=limit)

@router.get("/my", response_model=List[UnitEventResponseByUnitId], dependencies=[Depends(require_staff)])
async def Get_My_Unit_Events_By_Semester(
    semester_id: PydanticObjectId = Query(..., alias="semesterId"),
    current_user: TokenData = Depends(require_staff),
    service: UnitEventService = Depends(get_unit_event_service),
) -> List[UnitEventResponseByUnitId]:
    """
    Lấy danh sách sự kiện đẩy xuống đơn vị của tôi theo kỳ học

    Query: semesterId - id kỳ học cần lọc.

    Quyền xem: Quản lý đơn vị
    """
    return await service.get_unit_events_by_unit_id(current_user.sub, semester_id)


@router.get("/{event_id}", response_model=UnitEventResponse, dependencies=[Depends(require_manager)])
async def Get_Unit_Event_By_Id(
    event_id: PydanticObjectId,
    service: UnitEventService = Depends(get_unit_event_service),
) -> UnitEventResponse:
    """
    Lấy sự kiện đẩy xuống đơn vị theo id
    
    Quyền xem: VPĐ hoặc ADMIN hoặc STAFF
    """
    return await service.get_unit_event_by_id(event_id)

@router.put("/{event_id}", response_model=BaseResponse, dependencies=[Depends(require_manager)])
async def Update_Unit_Event(
    event_id: PydanticObjectId,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    point: Optional[float] = Form(None),
    event_start: Optional[str] = Form(None),
    event_end: Optional[str] = Form(None),
    registration_start: Optional[str] = Form(None),
    registration_end: Optional[str] = Form(None),
    listUnitId: Optional[str] = Form(None),
    semester_id: Optional[str] = Form(None),
    _ = Depends(require_manager),
    service: UnitEventService = Depends(get_unit_event_service),
) -> BaseResponse:
    from datetime import datetime
    from decimal import Decimal
    
    update_data = {}
    if title is not None: update_data["title"] = title
    if description is not None: update_data["description"] = description
    if location is not None: update_data["location"] = location
    if point is not None: update_data["point"] = Decimal(str(point))
    if event_start is not None: update_data["event_start"] = datetime.fromisoformat(event_start)
    if event_end is not None: update_data["event_end"] = datetime.fromisoformat(event_end)
    if registration_start is not None:
        update_data["registration_start"] = (
            datetime.fromisoformat(registration_start) if registration_start else None
        )
    if registration_end is not None:
        update_data["registration_end"] = (
            datetime.fromisoformat(registration_end) if registration_end else None
        )
    
    if listUnitId:
        update_data["listUnitId"] = parse_list_unit_ids(listUnitId)
    
    if semester_id:
        update_data["semesterId"] = PydanticObjectId(semester_id)
        
    data = UnitEventUpdate(**update_data)
    
    return await service.update_unit_event(event_id, data)

@router.delete("/{event_id}", response_model=BaseResponse, dependencies=[Depends(require_manager)])
async def Delete_Unit_Event(
    event_id: PydanticObjectId,
    _ = Depends(require_manager),
    service: UnitEventService = Depends(get_unit_event_service),
) -> BaseResponse:
    """
    Xóa mềm sự kiện đẩy xuống đơn vị theo id
    
    Quyền xóa: VPĐ hoặc ADMIN
    """
    return await service.delete_unit_event(event_id)
