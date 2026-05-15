from typing import List, Optional
from repositories.unit_event_repo import UnitEventRepo
from schemas.unit_event import UnitEventCreate, UnitEventResponse, UnitEventUpdate, UnitEventResponseByUnitId
from schemas.response import BaseResponse
from models.unit_event import UnitEvent, UnitEventEnum
from datetime import datetime, timezone
from beanie import PydanticObjectId
from exceptions import ErrorCode, app_exception
from repositories.semester_repo import SemesterRepo
from repositories.unit_repo import UnitRepo
from repositories.user_role_repo import UserRoleRepo
from services.semester_service import SemesterService
from schemas.unit import UnitRead
from repositories.unit_event_submissions_repo import UnitEventSubmissionsRepo
from models.unit_event_submissions import UnitEventSubmission, UnitEventSubmissionStatus

class UnitEventService:
    def __init__(
        self,
        repo: UnitEventRepo,
        unit_repo: UnitRepo | None = None,
        user_role_repo: UserRoleRepo | None = None,
        unit_event_submissions_repo: UnitEventSubmissionsRepo | None = None,
    ) -> None:
        self.repo = repo
        self.unit_repo = unit_repo or UnitRepo()
        self.user_role_repo = user_role_repo or UserRoleRepo()
        self.unit_event_submissions_repo = unit_event_submissions_repo or UnitEventSubmissionsRepo()
        self.semester_service = SemesterService(SemesterRepo())

    def _parse_object_id(self, value: PydanticObjectId | str, field_name: str) -> PydanticObjectId:
        try:
            return PydanticObjectId(str(value))
        except Exception:
            app_exception(
                ErrorCode.INVALID_ID_FORMAT,
                extra_detail=f"{field_name} không đúng định dạng",
            )

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_event_time(event_start: datetime, event_end: datetime) -> tuple[datetime, datetime]:
        normalized_start = UnitEventService._ensure_utc(event_start)
        normalized_end = UnitEventService._ensure_utc(event_end)
        if normalized_start >= normalized_end:
            app_exception(ErrorCode.INVALID_EVENT_TIME)
        return normalized_start, normalized_end

    @staticmethod
    def _validate_registration_time(
        registration_start: datetime, registration_end: datetime
    ) -> tuple[datetime, datetime]:
        normalized_start = UnitEventService._ensure_utc(registration_start)
        normalized_end = UnitEventService._ensure_utc(registration_end)
        if normalized_start >= normalized_end:
            app_exception(
                ErrorCode.INVALID_REGISTRATION_TIME,
                extra_detail="registration_start phải nhỏ hơn registration_end",
            )
        return normalized_start, normalized_end

    async def _ensure_units_exist(
        self, unit_ids: List[PydanticObjectId | str]
    ) -> List[PydanticObjectId]:
        normalized_ids = [self._parse_object_id(unit_id, "unit_id") for unit_id in unit_ids]
        unique_unit_ids = list(dict.fromkeys(normalized_ids))
        units = await self.unit_repo.list_by_ids(unique_unit_ids)
        if len(units) != len(unique_unit_ids):
            app_exception(
                ErrorCode.UNIT_NOT_FOUND,
                extra_detail="Một hoặc nhiều đơn vị được giao không tồn tại",
            )
        return unique_unit_ids

    async def _build_event_response(self, event: UnitEvent) -> UnitEventResponse:
        unit_ids = event.listUnitId or []
        units = await self.unit_repo.list_by_ids(unit_ids)
        unit_map = {str(unit.id): unit for unit in units}
        assigned_units = [
            UnitRead(
                id=unit_map[str(unit_id)].id,
                name=unit_map[str(unit_id)].name,
                logo=unit_map[str(unit_id)].logo,
                type=unit_map[str(unit_id)].type,
            )
            for unit_id in unit_ids
            if str(unit_id) in unit_map
        ]

        return UnitEventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            location=event.location,
            point=event.point,
            type=event.type,
            event_start=event.event_start,
            event_end=event.event_end,
            registration_start=event.registration_start,
            registration_end=event.registration_end,
            is_student_registration=event.is_student_registration,
            limit_student_registration_in_one_unit=event.limit_student_registration_in_one_unit,
            semesterId=event.semesterId,
            created_at=event.created_at,
            created_by=event.created_by,
            assigned_units=assigned_units,
        )

    async def _build_event_response_by_unit_id(self, event: UnitEvent) -> UnitEventResponseByUnitId:
        return UnitEventResponseByUnitId(
            id=event.id,
            title=event.title,
            description=event.description,
            location=event.location,
            point=event.point,
            type=event.type,
            event_start=event.event_start,
            event_end=event.event_end,
            registration_start=event.registration_start,
            registration_end=event.registration_end,
            semesterId=event.semesterId,
            is_student_registration=event.is_student_registration,
            limit_student_registration_in_one_unit=event.limit_student_registration_in_one_unit,
            created_at=event.created_at,
        )

    async def create_unit_event(
        self,
        payload: UnitEventCreate,
        current_user: str,
    ) -> UnitEventResponse:
        if payload.point < 0 or payload.point > 10:
            app_exception(ErrorCode.INVALID_POINT_VALUE)
        if payload.type not in UnitEventEnum:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)

        unique_unit_ids = await self._ensure_units_exist(payload.listUnitId)
        event_start, event_end = self._validate_event_time(
            payload.event_start,
            payload.event_end,
        )
        registration_start = payload.registration_start
        registration_end = payload.registration_end
        if payload.type == UnitEventEnum.HTSK:
            if registration_start is not None and registration_end is not None:
                registration_start, registration_end = self._validate_registration_time(
                    registration_start, registration_end
                )
            elif registration_start is not None or registration_end is not None:
                app_exception(
                    ErrorCode.INVALID_REGISTRATION_TIME,
                    extra_detail="Cần truyền đủ registration_start và registration_end cho HTSK hoặc để null cả hai",
                )
        else:
            registration_start = None
            registration_end = None
        location = payload.location if payload.type == UnitEventEnum.HTSK else None

        unit_event = UnitEvent(
            title=payload.title,
            description=payload.description,
            location=location,
            point=payload.point,
            type=payload.type,
            event_start=event_start,
            event_end=event_end,
            registration_start=registration_start,
            registration_end=registration_end,
            is_student_registration=payload.is_student_registration,
            limit_student_registration_in_one_unit=payload.limit_student_registration_in_one_unit,
            semesterId=payload.semesterId or (await self.semester_service.get_current_semester()).id,
            listUnitId=unique_unit_ids,
            created_at=datetime.now(timezone.utc),
            created_by=self._parse_object_id(current_user, "current_user_id"),
        )
        saved = await self.repo.create(unit_event)
        return await self._build_event_response(saved)


    async def _handle_after_create_student_registration_event(
        self, event: UnitEventResponse
    ) -> None:
        """Tạo ngay phản hồi HTSK cho tất cả đơn vị, không cần danh sách thành viên.

        Tạo cho tất cả UnitId thuộc event.listUnitId
        content: None
        evidenceUrl: None
        status: UnitEventSubmissionStatus = WAITING
"""
        event_id = self._parse_object_id(event.id, "unit_event_id")
        submitted_at = datetime.now(timezone.utc)
        for unit in event.assigned_units:
            unit_id = self._parse_object_id(unit.id, "unit_id")
            existing_submission = await self.unit_event_submissions_repo.get_by_unit_event_id_and_unit_id(
                event_id, unit_id
            )
            if existing_submission:
                continue

            await self.unit_event_submissions_repo.create(
                UnitEventSubmission(
                    unitEventId=event_id,
                    unitId=unit_id,
                    content=None,
                    evidenceUrl=None,
                    status=UnitEventSubmissionStatus.WAITING,
                    submittedAt=submitted_at,
                )
            )

    async def create_unit_event_student_registration(
        self,
        payload: UnitEventCreate,
        current_user: str,
    ) -> UnitEventResponse:
        created_event = await self.create_unit_event(payload, current_user)
        await self._handle_after_create_student_registration_event(created_event)
        return created_event

    async def auto_approve_waiting_submissions_after_registration_deadline(self) -> None:
        """Tự động duyệt các submission WAITING khi event HTSK đã qua registration_end."""
        now = datetime.now(timezone.utc)
        expired_events = await self.repo.list_expired_htsk_events_by_registration_end(now)
        if not expired_events:
            return

        for event in expired_events:
            submissions = await self.unit_event_submissions_repo.get_all_by_unit_event_id(event.id)
            for submission in submissions:
                if submission.status != UnitEventSubmissionStatus.WAITING:
                    continue
                submission.status = UnitEventSubmissionStatus.APPROVED
                await self.unit_event_submissions_repo.update(submission)






    async def get_all_unit_events_by_semester_id(
        self, 
        semester_id: Optional[PydanticObjectId | str] = None,
        skip: int = 0,
        limit: int = 10
    ):
        parsed_semester_id = None
        if semester_id and semester_id != 'all':
            parsed_semester_id = self._parse_object_id(semester_id, "semesterId")
            await self.semester_service.get_semester_by_id(parsed_semester_id)

        events, total = await self.repo.list_active_by_semester_id(parsed_semester_id, skip=skip, limit=limit)
        items = [await self._build_event_response(event) for event in events]
        return {"items": items, "total": total}

    async def get_unit_events_by_unit_id(
        self,
        user_id: PydanticObjectId | str,
        semester_id: PydanticObjectId | str,
    ) -> List[UnitEventResponseByUnitId]:
        parsed_user_id = self._parse_object_id(user_id, "user_id")
        parsed_semester_id = self._parse_object_id(semester_id, "semesterId")
        await self.semester_service.get_semester_by_id(parsed_semester_id)
        
        user_roles = await self.user_role_repo.list_active_by_user(parsed_user_id)
        if not user_roles:
            app_exception(
                ErrorCode.UNIT_NOT_FOUND,
                extra_detail="User chưa được gán vào đơn vị nào",
            )

        unit_ids = list(dict.fromkeys([ur.unit_id for ur in user_roles]))
        seen_event_ids: set[PydanticObjectId] = set()
        events: List[UnitEvent] = []
        for unit_id in unit_ids:
            unit_events = await self.repo.list_by_unit_id_and_semester_id(
                unit_id, parsed_semester_id
            )
            for event in unit_events:
                if event.id not in seen_event_ids:
                    seen_event_ids.add(event.id)
                    events.append(event)

        return [await self._build_event_response_by_unit_id(event) for event in events]

    async def get_unit_event_by_id(self, event_id: PydanticObjectId | str) -> UnitEventResponse:
        parsed_event_id = self._parse_object_id(event_id, "event_id")
        try:
            event = await self.repo.get_by_id(parsed_event_id)
        except Exception:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if event is None:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        return await self._build_event_response(event)

    async def update_unit_event(
        self, 
        event_id: PydanticObjectId | str, 
        data: UnitEventUpdate,
    ) -> BaseResponse:
        parsed_event_id = self._parse_object_id(event_id, "event_id")
        try:
            event = await self.repo.get_by_id(parsed_event_id)
        except Exception:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if event is None:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)

        update_data = data.model_dump(exclude_unset=True)
        list_unit_id = update_data.pop("listUnitId", None)

        merged_event_start = update_data.get("event_start", event.event_start)
        merged_event_end = update_data.get("event_end", event.event_end)
        if merged_event_start is None or merged_event_end is None:
            app_exception(
                ErrorCode.INVALID_EVENT_TIME,
                extra_detail="unit_event phai co event_start va event_end",
            )
        (
            update_data["event_start"],
            update_data["event_end"],
        ) = self._validate_event_time(merged_event_start, merged_event_end)

        if event.type == UnitEventEnum.HTSK:
            merged_registration_start = update_data.get(
                "registration_start", event.registration_start
            )
            merged_registration_end = update_data.get(
                "registration_end", event.registration_end
            )
            if merged_registration_start is not None and merged_registration_end is not None:
                (
                    update_data["registration_start"],
                    update_data["registration_end"],
                ) = self._validate_registration_time(
                    merged_registration_start, merged_registration_end
                )
            elif merged_registration_start is not None or merged_registration_end is not None:
                app_exception(
                    ErrorCode.INVALID_REGISTRATION_TIME,
                    extra_detail="Cần truyền đủ registration_start và registration_end cho HTSK hoặc để null cả hai",
                )
        else:
            update_data["registration_start"] = None
            update_data["registration_end"] = None

        if event.type == UnitEventEnum.HTTT:
            update_data["location"] = None

        for field, value in update_data.items():
            setattr(event, field, value)

        if list_unit_id is not None:
            validated_unit_ids = await self._ensure_units_exist(list_unit_id)
            event.listUnitId = validated_unit_ids

        await self.repo.update(event)

        return BaseResponse(message="Sự kiện đẩy xuống đơn vị đã được cập nhật thành công")

    async def delete_unit_event(
        self, event_id: PydanticObjectId | str
    ) -> BaseResponse:
        parsed_event_id = self._parse_object_id(event_id, "event_id")
        try:
            event = await self.repo.get_by_id(parsed_event_id)
        except Exception:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if event is None:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)

        event.deleted_at = datetime.now(timezone.utc)
        await self.repo.update(event)
        return BaseResponse(message="Sự kiện đẩy xuống đơn vị đã được xóa thành công")
