from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Form, Query, UploadFile, status

from repositories.unit_repo import UnitRepo
from schemas.auth import TokenData
from schemas.unit_member import UnitMemberCreate, UnitMemberListResponse, UnitMemberRead
from schemas.unit import UnitCreate, UnitListResponse, UnitRead, UnitUpdate
from security import require_admin, require_user
from services.unit_service import UnitService


router = APIRouter(prefix="/units", tags=["Units"])


def get_unit_service() -> UnitService:
    return UnitService(UnitRepo())


@router.post(
    "",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_unit(
    name: str = Form(...),
    type: str = Form(...),
    introduction: str | None = Form(None),
    established_year: int | None = Form(None),
    member_count: int | None = Form(None),
    email: str | None = Form(None),
    fb_url: str | None = Form(None),
    logo: UploadFile | None = None,
    cover: UploadFile | None = None,
    service: UnitService = Depends(get_unit_service),
) -> UnitRead:
    payload = UnitCreate(
        name=name, 
        type=type, 
        introduction=introduction,
        established_year=established_year,
        member_count=member_count,
        email=email,
        fb_url=fb_url
    )
    return await service.create_unit(payload, logo, cover)


@router.get(
    "",
    response_model=UnitListResponse,
)
async def list_units(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    name: str | None = Query(None),
    type: str | None = Query(None),
    introduction: str | None = Query(None),
    service: UnitService = Depends(get_unit_service),
) -> UnitListResponse:
    return await service.list_units(
        skip=skip,
        limit=limit,
        name=name,
        type=type,
        introduction=introduction,
    )


@router.get(
    "/{unit_id}",
    response_model=UnitRead,
)
async def get_unit(
    unit_id: PydanticObjectId,
    service: UnitService = Depends(get_unit_service),
) -> UnitRead:
    return await service.get_unit(unit_id)


@router.put(
    "/{unit_id}",
    response_model=UnitRead,
)
async def update_unit(
    unit_id: PydanticObjectId,
    name: str = Form(None),
    type: str = Form(None),
    introduction: str | None = Form(None),
    established_year: int | None = Form(None),
    member_count: int | None = Form(None),
    email: str | None = Form(None),
    fb_url: str | None = Form(None),
    logo: UploadFile | None = None,
    cover: UploadFile | None = None,
    current_user: TokenData = Depends(require_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitRead:
    payload = UnitUpdate(
        name=name, 
        type=type, 
        introduction=introduction,
        established_year=established_year,
        member_count=member_count,
        email=email,
        fb_url=fb_url
    )
    return await service.update_unit(unit_id, payload, current_user, logo, cover)


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_unit(
    unit_id: PydanticObjectId,
    service: UnitService = Depends(get_unit_service),
) -> None:
    await service.delete_unit(unit_id)


@router.post(
    "/{unit_id}/members",
    response_model=UnitMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_unit_member(
    unit_id: PydanticObjectId,
    payload: UnitMemberCreate,
    current_user: TokenData = Depends(require_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitMemberRead:
    return await service.add_member(
        unit_id=unit_id,
        payload=payload,
        actor_id=PydanticObjectId(current_user.sub),
        current_user=current_user,
    )


@router.get(
    "/{unit_id}/members",
    response_model=UnitMemberListResponse,
)
async def list_unit_members(
    unit_id: PydanticObjectId,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    full_name: str | None = Query(None),
    email: str | None = Query(None),
    student_id: str | None = Query(None),
    class_name: str | None = Query(None),
    semester_id: PydanticObjectId | None = None,
    current_user: TokenData = Depends(require_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitMemberListResponse:
    return await service.list_members(
        unit_id=unit_id,
        current_user=current_user,
        semester_id=semester_id,
        skip=skip,
        limit=limit,
        full_name=full_name,
        email=email,
        student_id=student_id,
        class_name=class_name,
    )


@router.delete(
    "/{unit_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_unit_member(
    unit_id: PydanticObjectId,
    user_id: PydanticObjectId,
    semester_id: PydanticObjectId | None = None,
    current_user: TokenData = Depends(require_user),
    service: UnitService = Depends(get_unit_service),
) -> None:
    await service.remove_member(
        unit_id=unit_id,
        user_id=user_id,
        current_user=current_user,
        semester_id=semester_id,
    )
