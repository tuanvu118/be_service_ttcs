from datetime import datetime
from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from repositories.user_repo import UserRepo
from schemas.auth import TokenData
from schemas.users import (
    UserCreate,
    UserListResponse,
    UserProfileResponse,
    UserRead,
    UserResponse,
    UserUpdate,
    UserEventStatsResponse,
    UserPointsSummaryResponse,
)
from security import require_admin_or_manager_global, require_user
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service() -> UserService:
    return UserService(UserRepo())


@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    full_name: str | None = Query(None),
    email: str | None = Query(None),
    student_id: str | None = Query(None),
    class_name: str | None = Query(None),
    current_user: TokenData = Depends(require_user),
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    return await service.list_visible_users(
        current_user=current_user,
        skip=skip,
        limit=limit,
        full_name=full_name,
        email=email,
        student_id=student_id,
        class_name=class_name,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    student_id: str = Form(...),
    class_name: str = Form(...),
    avatar: UploadFile | None = File(None),
    date_of_birth: datetime = Form(None),
    current_user: TokenData = Depends(require_admin_or_manager_global),
    service: UserService = Depends(get_user_service),
):
    try:
        payload = UserCreate(
            full_name=full_name,
            email=email,
            password=password,
            student_id=student_id,
            class_name=class_name,
            avatar_url=None,
            date_of_birth=date_of_birth,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    return await service.create_user(payload, avatar)


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_current_user(
    full_name: str | None = Form(None),
    email: str | None = Form(None),
    password: str | None = Form(None),
    student_id: str | None = Form(None),
    class_name: str | None = Form(None),
    avatar: UploadFile | None = File(None),
    date_of_birth: datetime | None = Form(None),
    current_user: TokenData = Depends(require_user),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        payload = UserUpdate(
            full_name=full_name,
            email=email,
            password=password,
            student_id=student_id,
            class_name=class_name,
            date_of_birth=date_of_birth,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    return await service.update_current_user(payload, avatar, current_user)


@router.get("/me", response_model=UserProfileResponse)
async def read_current_user(
    current_user: TokenData = Depends(require_user),
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    return await service.get_current_user_profile(current_user)


@router.get("/me/stats", response_model=UserEventStatsResponse)
async def get_my_event_stats(
    semester_id: PydanticObjectId | None = Query(None),
    current_user: TokenData = Depends(require_user),
    service: UserService = Depends(get_user_service),
) -> UserEventStatsResponse:
    return await service.get_user_event_stats(
        PydanticObjectId(current_user.sub),
        semester_id
    )


@router.get("/{user_id}", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def get_user_detail(
    user_id: PydanticObjectId,
    current_user: TokenData = Depends(require_user),
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    return await service.get_user_detail(user_id, current_user)


@router.get("/{user_id}/points-summary", response_model=UserPointsSummaryResponse)
async def get_user_points_summary(
    user_id: PydanticObjectId,
    current_user: TokenData = Depends(require_admin_or_manager_global),
    service: UserService = Depends(get_user_service),
) -> UserPointsSummaryResponse:
    return await service.get_user_points_summary(user_id)


@router.put("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: PydanticObjectId,
    full_name: str | None = Form(None),
    email: str | None = Form(None),
    password: str | None = Form(None),
    student_id: str | None = Form(None),
    class_name: str | None = Form(None),
    avatar: UploadFile | None = File(None),
    date_of_birth: datetime | None = Form(None),
    current_user: TokenData = Depends(require_admin_or_manager_global),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        payload = UserUpdate(
            full_name=full_name,
            email=email,
            password=password,
            student_id=student_id,
            class_name=class_name,
            date_of_birth=date_of_birth,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    return await service.update_user(user_id, payload, avatar, current_user)
