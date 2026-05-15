from repositories.unit_event_submissions_repo import UnitEventSubmissionsRepo
from repositories.unit_event_submission_members_repo import UnitEventSubmissionMembersRepo
from repositories.unit_repo import UnitRepo
from repositories.user_repo import UserRepo
from repositories.user_unit_repo import UserUnitRepo
from configs.redis_config import get_redis
from configs.settings import HTSK_REGISTER_LOCK_TTL_SECONDS
from configs.rabbitmq import publish_registration_sync_message
from schemas.registration_sync import RegistrationSyncMessage
from schemas.unit_event_submissions import (
    UnitEventSubmissionCreate,
    UnitEventSubmissionResponse,
    UnitEventSubmissionUpdate,
    UnitEventSubmissionStatusUpdate,
    UnitEventSubmissionMemberCreate,
    UnitEventSubmissionMemberUpdate,
    UnitEventSubmissionMemberResponse,
    UnitEventSubmissionWithUnitResponse,
    UnitEventSubmissionHTSKListItemResponse,
    HTSKStudentOverviewResponse,
    StudentRegistrationInfo,
    HTSKStudentRegisterRequest,
    HTSKStudentRegisterResponse,
)
from models.unit_event_submissions import UnitEventSubmission, UnitEventSubmissionStatus
from models.unit_event import UnitEvent
from models.unit_event_submission_members import UnitEventSubmissionMember
from exceptions import ErrorCode, app_exception
from models.unit_event import UnitEventEnum
from beanie import PydanticObjectId
from datetime import datetime, timezone
from schemas.unit import UnitBase
from typing import List
from schemas.users import UserRead
from schemas.response import BaseResponse
from uuid import uuid4
from pymongo.errors import DuplicateKeyError

class UnitEventSubmissionsService:
    def __init__(
        self,
        repo: UnitEventSubmissionsRepo,
        unit_event_submission_members_repo: UnitEventSubmissionMembersRepo | None = None,
        unit_repo: UnitRepo | None = None,
    ):
        self.repo = repo
        self.unit_event_submission_members_repo = (
            unit_event_submission_members_repo or UnitEventSubmissionMembersRepo()
        )
        self.unit_repo = unit_repo or UnitRepo()
        self.user_repo = UserRepo()
        self.user_unit_repo = UserUnitRepo()
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
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def _ensure_unit_assigned_to_event(
        self, unit_event: UnitEvent, unit_id: PydanticObjectId
    ) -> dict[str, PydanticObjectId]:
        """Kiểm tra đơn vị có trong listUnitId của sự kiện."""
        list_unit_id = unit_event.listUnitId or []
        if unit_id not in list_unit_id:
            app_exception(ErrorCode.UNIT_NOT_ASSIGNED_TO_EVENT)

    def _ensure_htsk_submission_open(self, unit_event: UnitEvent) -> None:
        if unit_event.type != UnitEventEnum.HTSK:
            return

        if unit_event.registration_start is None or unit_event.registration_end is None:
            app_exception(
                ErrorCode.UNIT_EVENT_SUBMISSION_CLOSED,
                extra_detail="Sự kiện HTSK chưa cấu hình thời gian đăng ký",
            )

        now = self._utc_now()
        registration_start = self._ensure_utc(unit_event.registration_start)
        registration_end = self._ensure_utc(unit_event.registration_end)
        if now < registration_start or now >= registration_end:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_CLOSED)

    def _is_htsk_submission_open(self, unit_event: UnitEvent) -> bool:
        if unit_event.registration_start is None or unit_event.registration_end is None:
            return False
        now = self._utc_now()
        registration_start = self._ensure_utc(unit_event.registration_start)
        registration_end = self._ensure_utc(unit_event.registration_end)
        return registration_start <= now < registration_end

    @staticmethod
    async def _acquire_lock(lock_key: str, token: str) -> bool:
        redis = get_redis()
        acquired = await redis.set(
            lock_key,
            token,
            ex=HTSK_REGISTER_LOCK_TTL_SECONDS,
            nx=True,
        )
        return bool(acquired)

    @staticmethod
    async def _release_lock(lock_key: str, token: str) -> None:
        redis = get_redis()
        current_token = await redis.get(lock_key)
        if current_token == token:
            await redis.delete(lock_key)

    async def _build_submission_member_response(
        self, submission: UnitEventSubmission
    ) -> UnitEventSubmissionMemberResponse:
        members = await self.unit_event_submission_members_repo.get_all_by_unit_event_submission_id(
            submission.id
        )
        list_user_id = []
        for member in members:
            if member.studentId is not None:
                list_user_id.append(member.studentId)
            elif member.userId is not None:
                list_user_id.append(member.userId)
        return UnitEventSubmissionMemberResponse(
            unitEventId=submission.unitEventId,
            unitId=submission.unitId,
            content=submission.content or "",
            evidenceUrl=submission.evidenceUrl or "",
            status=submission.status,
            submittedAt=submission.submittedAt,
            list_user_id=list_user_id,
        )

    async def _validate_students_belong_to_unit(
        self,
        student_ids: List[str],
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
    ) -> dict[str, PydanticObjectId]:
        normalized_student_ids = [str(student_id).strip() for student_id in student_ids if str(student_id).strip()]
        if not normalized_student_ids:
            app_exception(ErrorCode.LIST_USER_ID_IS_REQUIRED)

        users = await self.user_repo.get_by_student_ids(normalized_student_ids)
        user_by_student_id = {user.student_id: user for user in users}
        missing_student_ids = [
            student_id for student_id in normalized_student_ids if student_id not in user_by_student_id
        ]
        if missing_student_ids:
            app_exception(
                ErrorCode.USER_NOT_IN_UNIT,
                extra_detail="Sinh viên không thuộc đơn vị do bạn quản lý",
            )

        user_ids = [user.id for user in users]
        active_memberships = await self.user_unit_repo.list_active_by_unit_and_users(
            unit_id, semester_id, user_ids
        )
        active_user_ids = {membership.user_id for membership in active_memberships}
        invalid_student_ids = [
            student_id
            for student_id in normalized_student_ids
            if user_by_student_id[student_id].id not in active_user_ids
        ]
        if invalid_student_ids:
            app_exception(
                ErrorCode.USER_NOT_IN_UNIT,
                extra_detail="Sinh viên không thuộc đơn vị do bạn quản lý",
            )

        return {
            student_id: user_by_student_id[student_id].id
            for student_id in normalized_student_ids
        }

    async def create_unit_event_submission(self, data: UnitEventSubmissionCreate, current_user: str) -> UnitEventSubmissionResponse:
        unit_event_id = self._parse_object_id(data.unitEventId, "unitEventId")
        unit_event = await UnitEvent.get(unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTTT:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)
        unit_id = self._parse_object_id(data.unitId, "unitId")
        self._ensure_unit_assigned_to_event(unit_event, unit_id)
        existing_submission = await self.repo.get_by_unit_event_id_and_unit_id(unit_event_id, unit_id)
        if existing_submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_ALREADY_EXISTS)
        unit_event_submission = UnitEventSubmission(
            unitEventId=unit_event_id,
            unitId=unit_id,
            content=data.content,
            evidenceUrl=data.evidenceUrl,
            submittedAt=self._utc_now(),
        )
        saved = await self.repo.create(unit_event_submission)
        return UnitEventSubmissionResponse.model_validate(saved)
    
    async def get_unit_event_submissions_by_unit_event_id(
        self, unit_event_id: PydanticObjectId | str, unit_id: PydanticObjectId | str
    ) -> UnitEventSubmissionResponse:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(unit_id, "unit_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)
        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
        return UnitEventSubmissionResponse.model_validate(submission)

    async def get_all_httt_submissions_by_unit_event_id(
        self, unit_event_id: PydanticObjectId | str
    ) -> List[UnitEventSubmissionWithUnitResponse]:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTTT:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)

        submissions = await self.repo.get_all_by_unit_event_id(parsed_unit_event_id)
        unit_ids = list(dict.fromkeys([submission.unitId for submission in submissions]))
        units = await self.unit_repo.list_by_ids(unit_ids)
        unit_map = {str(unit.id): unit for unit in units}

        result: List[UnitEventSubmissionWithUnitResponse] = []
        for submission in submissions:
            unit = unit_map.get(str(submission.unitId))
            if not unit:
                continue
            result.append(
                UnitEventSubmissionWithUnitResponse(
                    id=submission.id,
                    unitEventId=submission.unitEventId,
                    unit=UnitBase(name=unit.name, logo=unit.logo, type=unit.type),
                    content=submission.content or "",
                    evidenceUrl=submission.evidenceUrl or "",
                    status=submission.status,
                    submittedAt=submission.submittedAt,
                )
            )
        return result

    async def update_unit_event_submission(
        self,
        unit_event_id: PydanticObjectId | str,
        unit_id: PydanticObjectId | str,
        data: UnitEventSubmissionUpdate,
    ) -> UnitEventSubmissionResponse:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(unit_id, "unit_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)

        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)

        if submission.status == UnitEventSubmissionStatus.APPROVED:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_ALREADY_APPROVED)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(submission, field, value)
        if submission.status == UnitEventSubmissionStatus.REJECTED:
            submission.status = UnitEventSubmissionStatus.PENDING
        submission.submittedAt = datetime.now()

        saved = await self.repo.update(submission)
        return UnitEventSubmissionResponse.model_validate(saved)

    async def update_submission_status(
        self, data: UnitEventSubmissionStatusUpdate
    ) -> UnitEventSubmissionResponse:
        submission_id = self._parse_object_id(
            data.unit_event_submission_id, "unit_event_submission_id"
        )
        submission = await self.repo.get_by_id(submission_id)
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)

        submission.status = data.status
        saved = await self.repo.update(submission)
        return UnitEventSubmissionResponse.model_validate(saved)


    async def create_unit_event_submission_member(
        self, data: UnitEventSubmissionMemberCreate, x_unit_id: str
    ) -> UnitEventSubmissionMemberResponse:
        unit_event_id = self._parse_object_id(data.unitEventId, "unitEventId")
        unit_event = await UnitEvent.get(unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTSK:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)
        self._ensure_htsk_submission_open(unit_event)
        unit_id = self._parse_object_id(x_unit_id, "x_unit_id")
        self._ensure_unit_assigned_to_event(unit_event, unit_id)
        existing_submission = await self.repo.get_by_unit_event_id_and_unit_id(unit_event_id, unit_id)
        if existing_submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_ALREADY_EXISTS)
        if data.list_MSV is None:
            app_exception(ErrorCode.LIST_USER_ID_IS_REQUIRED)
        user_ids_by_student_id = await self._validate_students_belong_to_unit(
            data.list_MSV, unit_id, unit_event.semesterId
        )
        unit_event_submission = UnitEventSubmission(
            unitEventId=unit_event_id,
            unitId=unit_id,
            content=data.content,
            evidenceUrl=getattr(data, "evidenceUrl", None) or "",
            status=UnitEventSubmissionStatus.APPROVED,
            submittedAt=self._utc_now(),
        )
        saved = await self.repo.create(unit_event_submission)

        for student_id in data.list_MSV:
            unit_event_submission_member = UnitEventSubmissionMember(
                unitEventId=unit_event_id,
                unitEventSubmissionId=saved.id,
                studentId=student_id,
                userId=user_ids_by_student_id[str(student_id).strip()],
                checkIn=False,
            )
            try:
                await self.unit_event_submission_members_repo.create(unit_event_submission_member)
            except DuplicateKeyError:
                    app_exception(
                        ErrorCode.ALREADY_REGISTERED,
                        extra_detail="Sinh viên đã đăng ký ở đơn vị khác trong cùng sự kiện",
                    )
            
            # Bulk Sync to RabbitMQ
            try:
                users = await self.user_repo.get_by_student_ids(data.list_MSV)
                for user in users:
                    msg = RegistrationSyncMessage(
                        user_id=str(user.id),
                        event_id=str(unit_event_id),
                        event_type="unit",
                        student_id=user.student_id,
                        full_name=user.full_name,
                        registered_at=saved.submittedAt,
                        action="REGISTER"
                    )
                    await publish_registration_sync_message(msg.model_dump(mode="json"), f"bulk_{saved.id}_{user.id}")
            except Exception as e:
                print(f"Failed to publish bulk HTSK sync: {e}")

        return await self._build_submission_member_response(saved)


    async def get_unit_event_submissions_HTSK_by_unit_event_id(
        self, unit_event_id: PydanticObjectId | str, x_unit_id: str
    ) -> UnitEventSubmissionMemberResponse:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(x_unit_id, "x_unit_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type == UnitEventEnum.HTSK:
            self._ensure_htsk_submission_open(unit_event)
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)
        submission = await self.repo.get_by_unit_event_id_and_unit_id(parsed_unit_event_id, parsed_unit_id)
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
        return await self._build_submission_member_response(submission)

    async def update_unit_event_submission_member(
        self,
        unit_event_id: PydanticObjectId | str,
        x_unit_id: str,
        data: UnitEventSubmissionMemberUpdate,
    ) -> UnitEventSubmissionMemberResponse:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(x_unit_id, "x_unit_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type == UnitEventEnum.HTSK:
            self._ensure_htsk_submission_open(unit_event)
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)

        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)

        update_data = data.model_dump(exclude_unset=True)
        list_MSV = update_data.pop("list_MSV", None)
        if list_MSV is not None:
            list_MSV = [str(x).strip() for x in list_MSV if str(x).strip()]
        for field, value in update_data.items():
            setattr(submission, field, value)
        submission.submittedAt = self._utc_now()
        saved = await self.repo.update(submission)

        if list_MSV is not None:
            if len(list_MSV) == 0:
                app_exception(ErrorCode.LIST_USER_ID_IS_REQUIRED)
            user_ids_by_student_id = await self._validate_students_belong_to_unit(
                list_MSV, parsed_unit_id, unit_event.semesterId
            )
            # Sync: Cancel old members before deleting
            try:
                old_members = await self.unit_event_submission_members_repo.get_all_by_unit_event_submission_id(saved.id)
                for old_member in old_members:
                    cancel_msg = RegistrationSyncMessage(
                        user_id=str(old_member.userId),
                        event_id=str(parsed_unit_event_id),
                        event_type="unit",
                        action="CANCEL"
                    )
                    await publish_registration_sync_message(cancel_msg.model_dump(mode="json"), f"bulk_cancel_{saved.id}_{old_member.userId}")
            except Exception as e:
                print(f"Failed to publish bulk cancel sync: {e}")

            await self.unit_event_submission_members_repo.delete_all_by_unit_event_submission_id(
                saved.id
            )
            for student_id in list_MSV:
                try:
                    await self.unit_event_submission_members_repo.create(
                        UnitEventSubmissionMember(
                            unitEventId=parsed_unit_event_id,
                            unitEventSubmissionId=saved.id,
                            studentId=student_id,
                            userId=user_ids_by_student_id[str(student_id).strip()],
                            checkIn=False,
                        )
                    )
                except DuplicateKeyError:
                    app_exception(
                        ErrorCode.ALREADY_REGISTERED,
                        extra_detail="Sinh viên đã đăng ký ở đơn vị khác trong cùng sự kiện",
                    )

            # Bulk Sync: Register new members
            try:
                new_users = await self.user_repo.get_by_student_ids(list_MSV)
                for user in new_users:
                    reg_msg = RegistrationSyncMessage(
                        user_id=str(user.id),
                        event_id=str(parsed_unit_event_id),
                        event_type="unit",
                        student_id=user.student_id,
                        full_name=user.full_name,
                        registered_at=saved.submittedAt,
                        action="REGISTER"
                    )
                    await publish_registration_sync_message(reg_msg.model_dump(mode="json"), f"bulk_update_{saved.id}_{user.id}")
            except Exception as e:
                print(f"Failed to publish bulk update sync: {e}")

        return await self._build_submission_member_response(saved)

    async def get_all_htsk_members_by_unit_event_id(
        self, unit_event_id: PydanticObjectId | str
    ) -> List[UnitEventSubmissionHTSKListItemResponse]:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTSK:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)

        submissions = await self.repo.get_all_by_unit_event_id(parsed_unit_event_id)
        if not submissions:
            return []

        submission_ids = [submission.id for submission in submissions]
        members = await self.unit_event_submission_members_repo.get_all_by_unit_event_submission_ids(
            submission_ids
        )
        if not members:
            return []

        unit_ids = list({submission.unitId for submission in submissions})
        units = await self.unit_repo.list_by_ids(unit_ids)
        unit_name_map = {str(unit.id): unit.name for unit in units}

        submission_unit_map = {str(submission.id): submission.unitId for submission in submissions}

        user_id_members = [member.userId for member in members if member.userId is not None]
        student_ids = [
            str(member.studentId).strip()
            for member in members
            if member.userId is None and member.studentId is not None and str(member.studentId).strip()
        ]

        users_by_id = {
            str(user.id): user for user in await UserRepo.get_by_ids(user_id_members)
        }
        users_by_student_id = {
            user.student_id: user for user in await self.user_repo.get_by_student_ids(student_ids)
        }

        result: List[UnitEventSubmissionHTSKListItemResponse] = []
        for member in members:
            user = None
            if member.userId is not None:
                user = users_by_id.get(str(member.userId))
            elif member.studentId is not None:
                user = users_by_student_id.get(str(member.studentId).strip())
            if user is None:
                continue

            unit_id = submission_unit_map.get(str(member.unitEventSubmissionId))
            if unit_id is None:
                continue
            unit_name = unit_name_map.get(str(unit_id), "")

            result.append(
                UnitEventSubmissionHTSKListItemResponse(
                    user=UserRead.model_validate(user),
                    unit_name=unit_name,
                    checkIn=member.checkIn,
                )
            )
        return result

    async def get_htsk_student_registration_overview(
        self,
        unit_event_id: PydanticObjectId | str,
        unit_id: PydanticObjectId | str,
        current_user_id: PydanticObjectId | str,
    ) -> HTSKStudentOverviewResponse:
        parsed_unit_event_id = self._parse_object_id(unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(unit_id, "unit_id")
        parsed_current_user_id = self._parse_object_id(current_user_id, "current_user_id")

        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTSK:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)
        if not unit_event.is_student_registration:
            app_exception(
                ErrorCode.INVALID_OPTION,
                extra_detail="Sự kiện này không mở đăng ký cho sinh viên",
            )
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)

        membership = await self.user_unit_repo.get_active(
            parsed_current_user_id, parsed_unit_id, unit_event.semesterId
        )
        if not membership:
            app_exception(ErrorCode.USER_NOT_IN_UNIT)

        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)

        unit = await self.unit_repo.get_by_id(parsed_unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        user = await self.user_repo.get_by_id(parsed_current_user_id)
        if not user:
            app_exception(ErrorCode.USER_NOT_FOUND)

        slot_limit = unit_event.limit_student_registration_in_one_unit
        slot_used = await self.unit_event_submission_members_repo.count_by_unit_event_submission_id(
            submission.id
        )
        slot_remaining = max(slot_limit - slot_used, 0)

        existing_by_user = await self.unit_event_submission_members_repo.get_by_unit_event_and_user(
            parsed_unit_event_id, parsed_current_user_id
        )
        existing_by_student = None
        if not existing_by_user and user.student_id:
            existing_by_student = await self.unit_event_submission_members_repo.get_by_unit_event_and_student(
                parsed_unit_event_id, str(user.student_id).strip()
            )
        existing_member = existing_by_user or existing_by_student
        is_registered = existing_member is not None
        registered_unit_id = None
        registered_unit_name = None
        if existing_member:
            registered_submission = await self.repo.get_by_id(existing_member.unitEventSubmissionId)
            if registered_submission:
                registered_unit_id = registered_submission.unitId
                registered_unit = await self.unit_repo.get_by_id(registered_submission.unitId)
                if registered_unit:
                    registered_unit_name = registered_unit.name

        is_registration_open = self._is_htsk_submission_open(unit_event)
        can_register = (
            is_registration_open
            and submission.status == UnitEventSubmissionStatus.WAITING
            and slot_remaining > 0
            and not is_registered
        )

        return HTSKStudentOverviewResponse(
            unit_event_id=unit_event.id,
            title=unit_event.title,
            description=unit_event.description,
            location=unit_event.location,
            event_start=unit_event.event_start,
            event_end=unit_event.event_end,
            registration_start=unit_event.registration_start,
            registration_end=unit_event.registration_end,
            unit_id=parsed_unit_id,
            unit_name=unit.name,
            is_student_registration=unit_event.is_student_registration,
            submission_id=submission.id,
            submission_status=submission.status,
            slot_limit=slot_limit,
            slot_used=slot_used,
            slot_remaining=slot_remaining,
            is_registration_open=is_registration_open,
            can_register=can_register,
            my_registration=StudentRegistrationInfo(
                is_registered=is_registered,
                unit_id=registered_unit_id,
                unit_name=registered_unit_name,
                check_in=existing_member.checkIn if existing_member else None,
            ),
        )

    async def register_htsk_student(
        self,
        data: HTSKStudentRegisterRequest,
        current_user_id: PydanticObjectId | str,
    ) -> HTSKStudentRegisterResponse:
        parsed_unit_event_id = self._parse_object_id(data.unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(data.unit_id, "unit_id")
        parsed_current_user_id = self._parse_object_id(current_user_id, "current_user_id")

        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTSK:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)
        if not unit_event.is_student_registration:
            app_exception(
                ErrorCode.INVALID_OPTION,
                extra_detail="Sự kiện này không mở đăng ký cho sinh viên",
            )
        self._ensure_htsk_submission_open(unit_event)
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)

        membership = await self.user_unit_repo.get_active(
            parsed_current_user_id, parsed_unit_id, unit_event.semesterId
        )
        if not membership:
            app_exception(ErrorCode.USER_NOT_IN_UNIT)

        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
        user = await self.user_repo.get_by_id(parsed_current_user_id)
        if not user:
            app_exception(ErrorCode.USER_NOT_FOUND)

        lock_key = f"htsk_student_register_lock:{submission.id}"
        lock_token = str(uuid4())
        if not await self._acquire_lock(lock_key, lock_token):
            app_exception(
                ErrorCode.INVALID_OPTION,
                extra_detail="Yêu cầu đăng ký đang được xử lý, vui lòng thử lại",
            )

        normalized_student_id = str(user.student_id).strip() if user.student_id else None
        try:
            latest_submission = await self.repo.get_by_id(submission.id)
            if not latest_submission:
                app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
            if latest_submission.status != UnitEventSubmissionStatus.WAITING:
                app_exception(
                    ErrorCode.INVALID_OPTION,
                    extra_detail="Đơn vị không ở trạng thái chờ đăng ký sinh viên",
                )

            existing_by_user = await self.unit_event_submission_members_repo.get_by_unit_event_and_user(
                parsed_unit_event_id, parsed_current_user_id
            )
            existing_by_student = None
            if not existing_by_user and normalized_student_id:
                existing_by_student = await self.unit_event_submission_members_repo.get_by_unit_event_and_student(
                    parsed_unit_event_id, normalized_student_id
                )
            if existing_by_user or existing_by_student:
                app_exception(
                    ErrorCode.ALREADY_REGISTERED,
                    extra_detail="Bạn đã đăng ký ở đơn vị khác trong cùng sự kiện",
                )

            slot_limit = unit_event.limit_student_registration_in_one_unit
            slot_used = await self.unit_event_submission_members_repo.count_by_unit_event_submission_id(
                latest_submission.id
            )
            if slot_used >= slot_limit:
                app_exception(ErrorCode.EVENT_FULL)

            try:
                created_member = await self.unit_event_submission_members_repo.create(
                    UnitEventSubmissionMember(
                        unitEventId=parsed_unit_event_id,
                        unitEventSubmissionId=latest_submission.id,
                        userId=parsed_current_user_id,
                        studentId=normalized_student_id,
                        checkIn=False,
                    )
                )
            except DuplicateKeyError:
                app_exception(
                    ErrorCode.ALREADY_REGISTERED,
                    extra_detail="Bạn đã đăng ký ở đơn vị khác trong cùng sự kiện",
                )
        finally:
            await self._release_lock(lock_key, lock_token)

        updated_slot_used = slot_used + 1
        registered_at = self._utc_now()

        # Publish to RabbitMQ for QR Service sync
        try:
            if user:
                msg = RegistrationSyncMessage(
                    user_id=str(parsed_current_user_id),
                    event_id=str(parsed_unit_event_id),
                    event_type="unit", # Đánh dấu là unit event để QR service biết
                    student_id=user.student_id,
                    full_name=user.full_name,
                    registered_at=self._utc_now(),
                    action="REGISTER"
                )
                await publish_registration_sync_message(msg.model_dump(mode="json"), str(created_member.id))
        except Exception as e:
            print(f"Failed to publish HTSK registration sync message: {e}")

        return HTSKStudentRegisterResponse(
            member_id=created_member.id,
            unit_event_id=parsed_unit_event_id,
            submission_id=latest_submission.id,
            slot_used=updated_slot_used,
            slot_remaining=max(slot_limit - updated_slot_used, 0),
            registered_at=self._utc_now(),
        )

    async def cancel_htsk_student_registration(
        self,
        data: HTSKStudentRegisterRequest,
        current_user_id: PydanticObjectId | str,
    ) -> BaseResponse:
        parsed_unit_event_id = self._parse_object_id(data.unit_event_id, "unit_event_id")
        parsed_unit_id = self._parse_object_id(data.unit_id, "unit_id")
        parsed_current_user_id = self._parse_object_id(current_user_id, "current_user_id")

        unit_event = await UnitEvent.get(parsed_unit_event_id)
        if not unit_event:
            app_exception(ErrorCode.UNIT_EVENT_NOT_FOUND)
        if unit_event.type != UnitEventEnum.HTSK:
            app_exception(ErrorCode.INVALID_UNIT_EVENT_TYPE_VALUE)
        if not unit_event.is_student_registration:
            app_exception(
                ErrorCode.INVALID_OPTION,
                extra_detail="Sự kiện này không mở đăng ký cho sinh viên",
            )
        self._ensure_unit_assigned_to_event(unit_event, parsed_unit_id)

        membership = await self.user_unit_repo.get_active(
            parsed_current_user_id, parsed_unit_id, unit_event.semesterId
        )
        if not membership:
            app_exception(ErrorCode.USER_NOT_IN_UNIT)

        submission = await self.repo.get_by_unit_event_id_and_unit_id(
            parsed_unit_event_id, parsed_unit_id
        )
        if not submission:
            app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
        user = await self.user_repo.get_by_id(parsed_current_user_id)
        if not user:
            app_exception(ErrorCode.USER_NOT_FOUND)

        lock_key = f"htsk_student_register_lock:{submission.id}"
        lock_token = str(uuid4())
        if not await self._acquire_lock(lock_key, lock_token):
            app_exception(
                ErrorCode.INVALID_OPTION,
                extra_detail="Yêu cầu hủy đăng ký đang được xử lý, vui lòng thử lại",
            )

        try:
            latest_submission = await self.repo.get_by_id(submission.id)
            if not latest_submission:
                app_exception(ErrorCode.UNIT_EVENT_SUBMISSION_NOT_FOUND)
            if latest_submission.status != UnitEventSubmissionStatus.WAITING:
                app_exception(
                    ErrorCode.INVALID_OPTION,
                    extra_detail="Chỉ được hủy khi đơn vị đang ở trạng thái WAITING",
                )

            existing_member = await self.unit_event_submission_members_repo.get_by_submission_and_user(
                latest_submission.id, parsed_current_user_id
            )
            if not existing_member and user.student_id:
                existing_member = await self.unit_event_submission_members_repo.get_by_submission_and_student(
                    latest_submission.id, str(user.student_id).strip()
                )
            if not existing_member:
                app_exception(ErrorCode.REGISTRATION_NOT_FOUND)

            await existing_member.delete()

            # Publish CANCEL to RabbitMQ
            try:
                msg = RegistrationSyncMessage(
                    user_id=str(parsed_current_user_id),
                    event_id=str(parsed_unit_event_id),
                    event_type="unit",
                    action="CANCEL"
                )
                await publish_registration_sync_message(msg.model_dump(mode="json"), f"cancel_unit_{parsed_unit_event_id}_{parsed_current_user_id}")
            except Exception as e:
                print(f"Failed to publish HTSK cancel sync message: {e}")

        finally:
            await self._release_lock(lock_key, lock_token)
        return BaseResponse(message="Hủy đăng ký tham gia HTSK thành công")
