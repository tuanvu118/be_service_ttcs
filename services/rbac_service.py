from typing import Dict, List, Set

from beanie import PydanticObjectId
from beanie.operators import In
from fastapi import HTTPException, status

from exceptions import ErrorCode, app_exception
from models.roles import Role, RoleCode
from models.user_unit import UserUnit
from models.users_roles import UserRole
from repositories.role_repo import RoleRepo
from repositories.semester_repo import SemesterRepo
from repositories.user_repo import UserRepo
from repositories.user_unit_repo import UserUnitRepo
from repositories.user_role_repo import UserRoleRepo
from schemas.rbac import RoleRead, UserRoleAssignmentListResponse, UserRoleAssignmentRead

ROLE_ADMIN = RoleCode.ADMIN
ROLE_MANAGER = RoleCode.MANAGER
ROLE_STAFF = RoleCode.STAFF
ROLE_USER = RoleCode.USER


class RBACService:
    def __init__(
        self,
        user_repo: UserRepo,
        role_repo: RoleRepo,
        user_role_repo: UserRoleRepo,
        semester_repo: SemesterRepo | None = None,
        user_unit_repo: UserUnitRepo | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.user_role_repo = user_role_repo
        self.semester_repo = semester_repo or SemesterRepo()
        self.user_unit_repo = user_unit_repo or UserUnitRepo()

    async def _ensure_user_unit_membership(
        self,
        user_id: PydanticObjectId,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
        added_by: PydanticObjectId,
    ) -> None:
        existing_membership = await self.user_unit_repo.get_active(
            user_id=user_id,
            unit_id=unit_id,
            semester_id=semester_id,
        )
        if existing_membership:
            return

        await self.user_unit_repo.create(
            UserUnit(
                user_id=user_id,
                unit_id=unit_id,
                semester_id=semester_id,
                added_by=added_by,
            )
        )

    async def build_unit_role_claims_for_user(
        self, user_id: PydanticObjectId
    ) -> List[Dict]:
        active_semester = await self.semester_repo.get_active()
        if not active_semester:
            return []

        user_roles = await self.user_role_repo.list_active_by_user(
            user_id,
            active_semester.id,
        )
        if not user_roles:
            return []

        role_ids: Set[PydanticObjectId] = {user_role.role_id for user_role in user_roles}
        roles = await Role.find(In(Role.id, list(role_ids))).to_list()
        role_map: Dict[str, str] = {str(role.id): role.code for role in roles}

        by_unit: Dict[str, Set[str]] = {}
        for user_role in user_roles:
            unit_id = str(user_role.unit_id)
            role_code = role_map.get(str(user_role.role_id))
            if not role_code:
                continue
            by_unit.setdefault(unit_id, set()).add(role_code)

        return [
            {"unit_id": unit_id, "roles": list(role_codes)}
            for unit_id, role_codes in by_unit.items()
        ]

    async def list_roles(self) -> List[RoleRead]:
        roles = await self.role_repo.list_all()
        roles = sorted(roles, key=lambda role: role.code)
        unique_roles_by_code: Dict[str, Role] = {}
        for role in roles:
            unique_roles_by_code.setdefault(str(role.code), role)
        return [RoleRead.model_validate(role) for role in unique_roles_by_code.values()]

    async def list_user_role_assignments(
        self,
        user_id: PydanticObjectId,
        semester_id: PydanticObjectId | None = None,
    ) -> UserRoleAssignmentListResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            app_exception(ErrorCode.USER_NOT_FOUND)

        if semester_id is None:
            active_semester = await self.semester_repo.get_active()
            if not active_semester:
                app_exception(ErrorCode.ACTIVE_SEMESTER_NOT_FOUND)
            semester_id = active_semester.id

        assignments = await self.user_role_repo.list_active_by_user(user_id, semester_id)
        role_ids: Set[PydanticObjectId] = {assignment.role_id for assignment in assignments}
        roles = await Role.find(In(Role.id, list(role_ids))).to_list() if role_ids else []
        role_map: Dict[str, str] = {str(role.id): role.code for role in roles}

        items = [
            UserRoleAssignmentRead(
                id=assignment.id,
                user_id=assignment.user_id,
                role_id=assignment.role_id,
                role_code=role_map.get(str(assignment.role_id), ""),
                unit_id=assignment.unit_id,
                semester_id=assignment.semester_id,
                is_active=assignment.is_active,
                created_at=assignment.created_at,
            )
            for assignment in assignments
        ]
        items.sort(key=lambda item: (item.role_code, str(item.unit_id), str(item.semester_id)))
        return UserRoleAssignmentListResponse(items=items, total=len(items))

    async def assign_role(
        self,
        actor_id: PydanticObjectId,
        target_user_id: PydanticObjectId,
        role_id: PydanticObjectId,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId | None = None,
    ) -> UserRole:
        actor = await self.user_repo.get_by_id(actor_id)
        target_user = await self.user_repo.get_by_id(target_user_id)
        if not actor or not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        if semester_id is None:
            active_semester = await self.semester_repo.get_active()
            if not active_semester:
                app_exception(ErrorCode.ACTIVE_SEMESTER_NOT_FOUND)
            semester_id = active_semester.id

        existed = await self.user_role_repo.get_active_by_user_role_unit_semester(
            user_id=target_user.id,
            role_id=role.id,
            unit_id=unit_id,
            semester_id=semester_id,
        )
        await self._ensure_user_unit_membership(
            user_id=target_user.id,
            unit_id=unit_id,
            semester_id=semester_id,
            added_by=actor_id,
        )
        if existed:
            return existed

        user_role = UserRole(
            user_id=target_user.id,
            role_id=role.id,
            unit_id=unit_id,
            semester_id=semester_id,
            is_active=True,
        )
        return await self.user_role_repo.create(user_role)

    async def remove_role_assignment(
        self,
        assignment_id: PydanticObjectId,
    ) -> None:
        assignment = await self.user_role_repo.get_by_id(assignment_id)
        if not assignment or not assignment.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        await self.user_role_repo.deactivate(assignment)
