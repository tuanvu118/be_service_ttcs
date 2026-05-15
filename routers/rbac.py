from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Response, status

from repositories.role_repo import RoleRepo
from repositories.semester_repo import SemesterRepo
from repositories.user_repo import UserRepo
from repositories.user_role_repo import UserRoleRepo
from schemas.rbac import (
    AssignRoleRequest,
    RoleRead,
    UserRoleAssignmentListResponse,
    UserRoleAssignmentRead,
)
from schemas.auth import TokenData
from security import require_admin
from services.rbac_service import RBACService


router = APIRouter(prefix="/rbac", tags=["RBAC"])


def get_rbac_service() -> RBACService:
    return RBACService(UserRepo(), RoleRepo(), UserRoleRepo(), SemesterRepo())


@router.get("/roles", response_model=List[RoleRead], status_code=status.HTTP_200_OK)
async def list_roles(
    current_user: TokenData = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> List[RoleRead]:
    return await rbac_service.list_roles()


@router.get(
    "/users/{user_id}/assignments",
    response_model=UserRoleAssignmentListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_user_role_assignments(
    user_id: PydanticObjectId,
    semester_id: PydanticObjectId | None = None,
    current_user: TokenData = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> UserRoleAssignmentListResponse:
    return await rbac_service.list_user_role_assignments(user_id, semester_id)


@router.post("/assign-role", response_model=UserRoleAssignmentRead, status_code=status.HTTP_201_CREATED)
async def assign_role(
    payload: AssignRoleRequest,
    current_user: TokenData = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
):
    assignment = await rbac_service.assign_role(
        actor_id=PydanticObjectId(current_user.sub),
        target_user_id=payload.target_user_id,
        role_id=payload.role_id,
        unit_id=payload.unit_id,
        semester_id=payload.semester_id,
    )
    role = await RoleRepo().get_by_id(assignment.role_id)
    return UserRoleAssignmentRead(
        id=assignment.id,
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        role_code=role.code if role else "",
        unit_id=assignment.unit_id,
        semester_id=assignment.semester_id,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_assignment(
    assignment_id: PydanticObjectId,
    current_user: TokenData = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> Response:
    await rbac_service.remove_role_assignment(assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
