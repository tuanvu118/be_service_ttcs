from datetime import datetime
from typing import List

from beanie import PydanticObjectId

from exceptions import ErrorCode, app_exception
from models.semester import Semester
from repositories.semester_repo import SemesterRepo
from schemas.semester import SemesterCreate, SemesterListResponse, SemesterRead, SemesterUpdate


class SemesterService:
    def __init__(self, repo: SemesterRepo) -> None:
        self.repo = repo

    @staticmethod
    def _validate_time(start_date, end_date) -> None:
        if start_date >= end_date:
            app_exception(ErrorCode.INVALID_SEMESTER_TIME)

    @staticmethod
    def _matches_text_filter(value: str | None, query: str | None) -> bool:
        if not query:
            return True
        return query.lower() in (value or "").lower()

    @staticmethod
    def _paginate(items: List, skip: int, limit: int) -> List:
        return items[skip : skip + limit]

    async def create_semester(self, payload: SemesterCreate) -> SemesterRead:
        self._validate_time(payload.start_date, payload.end_date)

        if payload.is_active:
            await self.repo.deactivate_active_except()

        semester = Semester(**payload.model_dump())
        saved = await self.repo.create(semester)
        return SemesterRead.model_validate(saved)

    async def list_semesters(
        self,
        skip: int = 0,
        limit: int = 20,
        name: str | None = None,
        academic_year: str | None = None,
        is_active: bool | None = None,
        start_date_from: datetime | None = None,
        start_date_to: datetime | None = None,
        end_date_from: datetime | None = None,
        end_date_to: datetime | None = None,
    ) -> SemesterListResponse:
        semesters = await self.repo.list_all()
        filtered_semesters = [
            semester
            for semester in semesters
            if self._matches_text_filter(semester.name, name)
            and self._matches_text_filter(semester.academic_year, academic_year)
            and (is_active is None or semester.is_active == is_active)
            and (start_date_from is None or semester.start_date >= start_date_from)
            and (start_date_to is None or semester.start_date <= start_date_to)
            and (end_date_from is None or semester.end_date >= end_date_from)
            and (end_date_to is None or semester.end_date <= end_date_to)
        ]
        total = len(filtered_semesters)
        paginated_semesters = self._paginate(filtered_semesters, skip, limit)
        return SemesterListResponse(
            items=[
                SemesterRead.model_validate(semester)
                for semester in paginated_semesters
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_current_semester(self) -> SemesterRead:
        semester = await self.repo.get_active()
        if not semester:
            app_exception(ErrorCode.ACTIVE_SEMESTER_NOT_FOUND)
        return SemesterRead.model_validate(semester)

    async def get_semester_by_id(self, semester_id: PydanticObjectId) -> SemesterRead:
        semester = await self.repo.get_by_id(semester_id)
        if not semester:
            app_exception(ErrorCode.SEMESTER_NOT_FOUND)
        return SemesterRead.model_validate(semester)

    async def update_semester(
        self,
        semester_id: PydanticObjectId,
        payload: SemesterUpdate,
    ) -> SemesterRead:
        semester = await self.repo.get_by_id(semester_id)
        if not semester:
            app_exception(ErrorCode.SEMESTER_NOT_FOUND)

        update_data = payload.model_dump(exclude_unset=True)

        new_start_date = update_data.get("start_date", semester.start_date)
        new_end_date = update_data.get("end_date", semester.end_date)
        self._validate_time(new_start_date, new_end_date)

        if update_data.get("is_active") is True:
            await self.repo.deactivate_active_except(semester.id)

        for field, value in update_data.items():
            setattr(semester, field, value)

        saved = await self.repo.save(semester)
        return SemesterRead.model_validate(saved)
