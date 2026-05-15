from typing import Optional
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Header, Query, status, Form, File, UploadFile
from exceptions import ErrorCode, app_exception
from security import require_manager, require_staff
from schemas.auth import TokenData
from schemas.event_promotion import (
    EventPromotionCreate, 
    EventPromotionUpdate, 
    EventPromotionRead, 
    EventPromotionStatusUpdate,
    EventTimeSchema,
    EventPromotionPaginationResponse
)
from services.event_promotion import EventPromotionService

router = APIRouter(prefix="/event-promotions", tags=["Event Promotions"])

def parse_utc_dt(dt_str: str) -> datetime:
    if not dt_str: return None
    from datetime import timezone
    # Handle 'Z' and ensure aware UTC for event promotions
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

@router.post(
    "",
    response_model=EventPromotionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)]
)
async def create_promotion(
    title: str = Form(...),
    description: str = Form(...),
    semester_id: Optional[str] = Form(None),
    event_start: Optional[str] = Form(None),
    event_end: Optional[str] = Form(None),
    external_links: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: TokenData = Depends(require_staff),
    x_unit_id: str = Header(..., alias="X-Unit-Id")
):
    try:
        import json
        u_id = PydanticObjectId(x_unit_id)
        user_id = PydanticObjectId(current_user.sub)
        s_id = PydanticObjectId(semester_id) if semester_id else None
        
        links_list = json.loads(external_links) if external_links else []
        
        time = None
        if event_start and event_end:
            time = EventTimeSchema(
                start=parse_utc_dt(event_start),
                end=parse_utc_dt(event_end)
            )
            
        data = EventPromotionCreate(
            title=title,
            description=description,
            semester_id=s_id,
            time=time,
            external_links=links_list
        )
    except Exception as e:
        app_exception(ErrorCode.INVALID_ID_FORMAT, extra_detail=str(e))
        
    return await EventPromotionService.create_promotion(data, u_id, user_id, image)

@router.get(
    "/admin",
    response_model=EventPromotionPaginationResponse,
    dependencies=[Depends(require_manager)]
)
async def list_promotions_for_admin(
    status: Optional[str] = Query(None),
    semester_id: Optional[PydanticObjectId] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    _ = Depends(require_manager)
):
    return await EventPromotionService.get_all_for_admin(status, semester_id, skip, limit)

@router.get(
    "/my-unit",
    response_model=EventPromotionPaginationResponse,
    dependencies=[Depends(require_staff)]
)
async def list_promotions_for_unit(
    status: Optional[str] = Query(None),
    semester_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    _ = Depends(require_staff)
):
    try:
        u_id = PydanticObjectId(x_unit_id)
        s_id = PydanticObjectId(semester_id) if semester_id else None
    except:
        app_exception(ErrorCode.INVALID_ID_FORMAT)
        
    return await EventPromotionService.get_for_unit(u_id, status, s_id, skip, limit)

@router.get(
    "/public",
    response_model=EventPromotionPaginationResponse
)
async def list_promotions_for_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    unit_id: Optional[PydanticObjectId] = Query(None)
):
    return await EventPromotionService.get_for_students(skip, limit, unit_id)

@router.get(
    "/{id}",
    response_model=EventPromotionRead
)
async def get_promotion_detail(id: PydanticObjectId):
    return await EventPromotionService.get_detail(id)

@router.put(
    "/{id}",
    response_model=EventPromotionRead,
    dependencies=[Depends(require_staff)]
)
async def update_promotion(
    id: PydanticObjectId,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    event_start: Optional[str] = Form(None),
    event_end: Optional[str] = Form(None),
    external_links: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    _ = Depends(require_staff)
):
    try:
        import json
        u_id = PydanticObjectId(x_unit_id)
        
        update_dict = {}
        if title is not None: update_dict["title"] = title
        if description is not None: update_dict["description"] = description
        if external_links is not None: 
            update_dict["external_links"] = json.loads(external_links)
        
        if event_start and event_end:
            update_dict["time"] = EventTimeSchema(
                start=parse_utc_dt(event_start),
                end=parse_utc_dt(event_end)
            )
            
        data = EventPromotionUpdate(**update_dict)
    except Exception as e:
        app_exception(ErrorCode.INVALID_ID_FORMAT, extra_detail=str(e))
        
    return await EventPromotionService.update_promotion(id, data, u_id, image)

@router.put(
    "/{id}/status",
    response_model=EventPromotionRead,
    dependencies=[Depends(require_manager)]
)
async def update_promotion_status(
    id: PydanticObjectId,
    data: EventPromotionStatusUpdate,
    _ = Depends(require_manager)
):
    return await EventPromotionService.update_status(id, data)

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_staff)]
)
async def delete_promotion(
    id: PydanticObjectId,
    x_unit_id: str = Header(..., alias="X-Unit-Id"),
    _ = Depends(require_staff)
):
    await EventPromotionService.delete_promotion(id, PydanticObjectId(x_unit_id))
