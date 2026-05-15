from typing import List

from beanie import PydanticObjectId
from fastapi import UploadFile

from exceptions import ErrorCode, app_exception
from models.unit import Unit
from models.user_unit import UserUnit
from repositories.semester_repo import SemesterRepo
from repositories.unit_repo import UnitRepo
from repositories.user_repo import UserRepo
from repositories.user_unit_repo import UserUnitRepo
from schemas.auth import TokenData
from schemas.unit_member import UnitMemberCreate, UnitMemberListResponse, UnitMemberRead
from schemas.unit import UnitCreate, UnitListResponse, UnitRead, UnitUpdate
from services.cloudinary_service import upload_image


class UnitService:
    def __init__(
        self,
        repo: UnitRepo,
        user_repo: UserRepo | None = None,
        semester_repo: SemesterRepo | None = None,
        user_unit_repo: UserUnitRepo | None = None,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo or UserRepo()
        self.semester_repo = semester_repo or SemesterRepo()
        self.user_unit_repo = user_unit_repo or UserUnitRepo()

    @staticmethod
    def _ensure_member_management_permission(
        current_user: TokenData,
        target_unit_id: PydanticObjectId,
    ) -> None:
        has_admin_or_manager = any(
            "ADMIN" in unit_role.roles or "MANAGER" in unit_role.roles
            for unit_role in current_user.roles
        )
        if has_admin_or_manager:
            return

        is_staff_of_unit = any(
            unit_role.unit_id == str(target_unit_id) and "STAFF" in unit_role.roles
            for unit_role in current_user.roles
        )
        if not is_staff_of_unit:
            app_exception(ErrorCode.INSUFFICIENT_PERMISSION)

    async def _resolve_semester(self, semester_id: PydanticObjectId | None):
        if semester_id is not None:
            semester = await self.semester_repo.get_by_id(semester_id)
            if not semester:
                app_exception(ErrorCode.SEMESTER_NOT_FOUND)
            return semester

        semester = await self.semester_repo.get_active()
        if not semester:
            app_exception(ErrorCode.ACTIVE_SEMESTER_NOT_FOUND)
        return semester

    @staticmethod
    def _build_member_response(user, membership: UserUnit) -> UnitMemberRead:
        return UnitMemberRead(
            user_id=user.id,
            full_name=user.full_name,
            student_id=user.student_id,
            class_name=user.class_name,
            email=user.email,
            avatar_url=user.avatar_url,
            unit_id=membership.unit_id,
            semester_id=membership.semester_id,
            joined_at=membership.joined_at,
        )

    @staticmethod
    def _matches_text_filter(value: str | None, query: str | None) -> bool:
        if not query:
            return True
        return query.lower() in (value or "").lower()

    @staticmethod
    def _paginate(items: List, skip: int, limit: int) -> List:
        return items[skip : skip + limit]

    async def _enrich_unit_member_count(self, unit_read: UnitRead) -> UnitRead:
        count = await self.user_unit_repo.count_distinct_members(PydanticObjectId(unit_read.id))
        unit_read.member_count = count
        return unit_read

    async def create_unit(
            self, 
            payload: UnitCreate,
            logo_file: UploadFile | None = None,
            cover_file: UploadFile | None = None) -> UnitRead:
        logo_url = None
        cover_url = None
        if logo_file:
            logo_url, _ = upload_image(logo_file)
        if cover_file:
            cover_url, _ = upload_image(cover_file)
            
        unit = Unit(
            name=payload.name,
            logo=logo_url,
            cover_url=cover_url,
            introduction=payload.introduction,
            type=payload.type,
            established_year=payload.established_year,
            email=payload.email,
            fb_url=payload.fb_url,
        )
        saved = await self.repo.create(unit)
        return UnitRead.model_validate(saved)

    async def get_unit(self, unit_id: PydanticObjectId) -> UnitRead:
        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)
        unit_read = UnitRead.model_validate(unit)
        return await self._enrich_unit_member_count(unit_read)

    async def list_units(
        self,
        skip: int = 0,
        limit: int = 20,
        name: str | None = None,
        type: str | None = None,
        introduction: str | None = None,
    ) -> UnitListResponse:
        items = await self.repo.list_all()
        filtered_units = [
            unit
            for unit in items
            if self._matches_text_filter(unit.name, name)
            and self._matches_text_filter(unit.type.value if unit.type else None, type)
            and self._matches_text_filter(unit.introduction, introduction)
        ]
        total = len(filtered_units)
        paginated_units = self._paginate(filtered_units, skip, limit)
        return UnitListResponse(
            items=[UnitRead.model_validate(unit) for unit in paginated_units],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def update_unit(
         self,
         unit_id: PydanticObjectId, 
         payload: UnitUpdate,
         current_user: TokenData,
         logo_file: UploadFile | None = None,
         cover_file: UploadFile | None = None
    ) -> UnitRead:
        self._ensure_member_management_permission(current_user, unit_id)
        
        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(unit, field, value)

        if logo_file:
            logo_url, _ = upload_image(logo_file)
            unit.logo = logo_url

        if cover_file:
            cover_url, _ = upload_image(cover_file)
            unit.cover_url = cover_url

        saved = await self.repo.update(unit)
        unit_read = UnitRead.model_validate(saved)
        return await self._enrich_unit_member_count(unit_read)

    async def delete_unit(self, unit_id: PydanticObjectId) -> None:
        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)
        await self.repo.delete(unit)

    async def add_member(
        self,
        unit_id: PydanticObjectId,
        payload: UnitMemberCreate,
        actor_id: PydanticObjectId,
        current_user: TokenData,
    ) -> UnitMemberRead:
        self._ensure_member_management_permission(current_user, unit_id)

        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        user = await self.user_repo.get_by_student_id(payload.student_id)
        if not user:
            app_exception(ErrorCode.USER_NOT_FOUND)

        semester = await self._resolve_semester(None)
        existed = await self.user_unit_repo.get_active(
            user.id,
            unit_id,
            semester.id,
        )
        if existed:
            app_exception(ErrorCode.USER_ALREADY_IN_UNIT)

        membership = await self.user_unit_repo.create(
            UserUnit(
                user_id=user.id,
                unit_id=unit_id,
                semester_id=semester.id,
                added_by=actor_id,
            )
        )
        return self._build_member_response(user, membership)

    async def list_members(
        self,
        unit_id: PydanticObjectId,
        current_user: TokenData,
        semester_id: PydanticObjectId | None = None,
        skip: int = 0,
        limit: int = 20,
        full_name: str | None = None,
        email: str | None = None,
        student_id: str | None = None,
        class_name: str | None = None,
    ) -> UnitMemberListResponse:
        self._ensure_member_management_permission(current_user, unit_id)

        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        semester = await self._resolve_semester(semester_id)
        memberships = await self.user_unit_repo.list_active_by_unit(unit_id, semester.id)
        user_ids = [membership.user_id for membership in memberships]
        users = await self.user_repo.get_by_ids(user_ids)
        user_map = {user.id: user for user in users}

        result: List[UnitMemberRead] = []
        for membership in memberships:
            user = user_map.get(membership.user_id)
            if user is None:
                continue
            result.append(self._build_member_response(user, membership))
        filtered_members = [
            member
            for member in result
            if self._matches_text_filter(member.full_name, full_name)
            and self._matches_text_filter(member.email, email)
            and self._matches_text_filter(member.student_id, student_id)
            and self._matches_text_filter(member.class_name, class_name)
        ]
        total = len(filtered_members)
        paginated_members = self._paginate(filtered_members, skip, limit)
        return UnitMemberListResponse(
            items=paginated_members,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def remove_member(
        self,
        unit_id: PydanticObjectId,
        user_id: PydanticObjectId,
        current_user: TokenData,
        semester_id: PydanticObjectId | None = None,
    ) -> None:
        self._ensure_member_management_permission(current_user, unit_id)

        unit = await self.repo.get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        semester = await self._resolve_semester(semester_id)
        membership = await self.user_unit_repo.get_active(user_id, unit_id, semester.id)
        if not membership:
            app_exception(ErrorCode.USER_NOT_IN_UNIT)

        await self.user_unit_repo.deactivate(membership)
