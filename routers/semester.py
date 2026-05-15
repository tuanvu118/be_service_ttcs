from typing import List

from beanie import PydanticObjectId
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from repositories.semester_repo import SemesterRepo
from schemas.auth import TokenData
from schemas.semester import SemesterCreate, SemesterListResponse, SemesterRead, SemesterUpdate
from security import require_global_admin, require_user
from services.semester_service import SemesterService


router = APIRouter(prefix="/semesters", tags=["Semesters"])


def get_semester_service() -> SemesterService:
    return SemesterService(SemesterRepo())


@router.post(
    "",
    response_model=SemesterRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_semester(
    payload: SemesterCreate,
    current_user: TokenData = Depends(require_global_admin),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterRead:
    return await service.create_semester(payload)


@router.get(
    "",
    response_model=SemesterListResponse,
)
async def list_semesters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    name: str | None = Query(None),
    academic_year: str | None = Query(None),
    is_active: bool | None = Query(None),
    start_date_from: datetime | None = Query(None),
    start_date_to: datetime | None = Query(None),
    end_date_from: datetime | None = Query(None),
    end_date_to: datetime | None = Query(None),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterListResponse:
    return await service.list_semesters(
        skip=skip,
        limit=limit,
        name=name,
        academic_year=academic_year,
        is_active=is_active,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        end_date_from=end_date_from,
        end_date_to=end_date_to,
    )


@router.get(
    "/current",
    response_model=SemesterRead,
)
async def get_current_semester(
    service: SemesterService = Depends(get_semester_service),
) -> SemesterRead:
    return await service.get_current_semester()


@router.put(
    "/{semester_id}",
    response_model=SemesterRead,
)
async def update_semester(
    semester_id: PydanticObjectId,
    payload: SemesterUpdate,
    current_user: TokenData = Depends(require_global_admin),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterRead:
    return await service.update_semester(semester_id, payload)
