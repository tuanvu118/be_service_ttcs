import uuid
from datetime import datetime, timezone

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from configs.redis_config import get_redis
from configs.rabbitmq import publish_registration_sync_message
from schemas.registration_sync import RegistrationSyncMessage
from exceptions import ErrorCode, app_exception
from repositories.event_registration_repo import EventRegistrationRepository
from repositories.public_event_repo import PublicEventRepository
from repositories.unit_event_repo import UnitEventRepo
from repositories.user_repo import UserRepo
from schemas.event_registration import (
    EventRegistrationResponse,
    EventRegistrationUserResponse,
    MyEventRegistrationResponse,
    MyEventDetailResponse,
)
from utils.redis_lua import run_lua, rollback, _users_key

def to_utc(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

_db_retry = retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.2, max=1),
    reraise=True,
)

ERROR_MAP = {
    0: ErrorCode.ALREADY_REGISTERED,
    -1: ErrorCode.ALREADY_REGISTERED,
    -2: ErrorCode.EVENT_FULL,
    -3: ErrorCode.EVENT_FULL,
}

class EventRegistrationService:

    @staticmethod
    def _validate_answers(event, answers):

        if not event.form_fields:
            return

        answer_map = {a.field_id: a.value for a in answers}

        for field in event.form_fields:

            if field.required and (field.id not in answer_map or not str(answer_map[field.id]).strip()):
                app_exception(ErrorCode.MISSING_REQUIRED_FIELD, f"Trường '{field.label}' là bắt buộc")

            if field.id not in answer_map:
                continue

            value = str(answer_map[field.id])
            if not value.strip() and not field.required:
                continue

            if field.field_type in ["select", "radio"]:
                if value not in field.options:
                    app_exception(ErrorCode.INVALID_OPTION, f"Lựa chọn '{value}' không hợp lệ cho trường '{field.label}'")
            
            elif field.field_type == "checkbox":
                selected_options = [opt.strip() for opt in value.split(',')]
                for opt in selected_options:
                    if opt not in field.options:
                        app_exception(ErrorCode.INVALID_OPTION, f"Lựa chọn '{opt}' không hợp lệ cho trường '{field.label}'")
            
            elif field.field_type == "number":
                try:
                    float(value)
                except ValueError:
                    app_exception(ErrorCode.INVALID_FORM_FIELD, f"Trường '{field.label}' phải là một con số")
            
            elif field.field_type in ["text", "textarea"]:
                if len(value) > 1000:
                    app_exception(ErrorCode.INVALID_FORM_FIELD, f"Câu trả lời cho '{field.label}' không được vượt quá 1000 ký tự")

    @staticmethod
    async def register_public_event(
        event_id: PydanticObjectId,
        user_id: PydanticObjectId,
        answers,
        idempotency_key: str | None = None,
    ) -> EventRegistrationResponse:

        event = await PublicEventRepository.get_by_id(event_id)
        if not event:
            app_exception(ErrorCode.EVENT_NOT_FOUND)

        now = datetime.now(timezone.utc)
        if not (to_utc(event.registration_start) <= now <= to_utc(event.registration_end)):
            app_exception(ErrorCode.REGISTRATION_CLOSED)

        EventRegistrationService._validate_answers(event, answers)

        # REDIS CHECK
        max_p = event.max_participants if event.max_participants and event.max_participants > 0 else 1
        result = await run_lua(str(event_id), str(user_id), max_p, idempotency_key)
        
        if result in ERROR_MAP:
            app_exception(ERROR_MAP[result])

        # DB INSERT
        async def _insert():
            return await EventRegistrationRepository.create({
                "event_id": event_id,
                "event_type": "public",
                "user_id": user_id,
                "answers": [a.model_dump() for a in answers],
                "registered_at": now,
            })

        try:
            reg = await _db_retry(_insert)()
        except DuplicateKeyError:
            await rollback(str(event_id), str(user_id), idempotency_key)
            app_exception(ErrorCode.ALREADY_REGISTERED)
        except Exception:
            await rollback(str(event_id), str(user_id), idempotency_key)
            raise

        reg.registered_at = to_utc(reg.registered_at)
        
        # Publish to RabbitMQ
        try:
            user = await UserRepo().get_by_id(user_id)
            if user:
                msg = RegistrationSyncMessage(
                    user_id=str(user_id),
                    event_id=str(event_id),
                    event_type="public",
                    student_id=user.student_id,
                    full_name=user.full_name,
                    registered_at=reg.registered_at,
                    action="REGISTER"
                )
                await publish_registration_sync_message(msg.model_dump(mode="json"), str(reg.id))
        except Exception as e:
            print(f"Failed to publish registration sync message: {e}")

        return EventRegistrationResponse.model_validate(reg)

    # CANCEL
    @staticmethod
    async def cancel(
        event_id: PydanticObjectId,
        user_id: PydanticObjectId,
    ):
        deleted = await EventRegistrationRepository.delete_by_event_and_user(
            event_id,
            user_id,
        )

        if not deleted:
            app_exception(ErrorCode.REGISTRATION_NOT_FOUND)

        # Publish CANCEL to RabbitMQ
        try:
            msg = RegistrationSyncMessage(
                user_id=str(user_id),
                event_id=str(event_id),
                event_type="public",
                action="CANCEL"
            )
            # Dùng message_id là sự kết hợp để trace
            await publish_registration_sync_message(msg.model_dump(mode="json"), f"cancel_{event_id}_{user_id}")
        except Exception as e:
            print(f"Failed to publish cancel sync message: {e}")

        # Cập nhật lại Redis: xóa user khỏi Set
        try:
            redis = get_redis()
            event_id_str = str(event_id)
            user_id_str = str(user_id)
            u_key = _users_key(event_id_str)

            await redis.srem(u_key, user_id_str)  # type: ignore[misc]
        except Exception:
            pass

    @staticmethod
    async def get_my_registrations(
        user_id: PydanticObjectId,
    ) -> list[MyEventRegistrationResponse]:
        registrations = await EventRegistrationRepository.get_by_user(user_id)

        if not registrations:
            return []

        event_ids = [r.event_id for r in registrations]

        public_events = await PublicEventRepository.get_by_ids(event_ids)
        unit_events = await UnitEventRepo().get_by_ids(event_ids)

        event_map = {e.id: e for e in public_events + unit_events}

        result = []

        for r in registrations:

            event = event_map.get(r.event_id)

            if not event:
                continue

            reg_at = r.registered_at
            if reg_at.tzinfo is None:
                reg_at = reg_at.replace(tzinfo=timezone.utc)

            result.append(
                MyEventRegistrationResponse(
                    event_id=event.id,
                    title=event.title,
                    event_start=event.event_start,
                    registered_at=reg_at,
                )
            )

        return result

    @staticmethod
    async def get_event_registrations(
        event_id: PydanticObjectId,
    ) -> list[EventRegistrationUserResponse]:

        registrations = await EventRegistrationRepository.get_by_event(event_id)
        if not registrations:
            return []

        user_ids = [r.user_id for r in registrations]

        users = await UserRepo().get_by_ids(user_ids)

        user_map = {u.id: u for u in users}

        result = []

        for r in registrations:

            user = user_map.get(r.user_id)

            if not user:
                continue

            reg_at = r.registered_at
            if reg_at.tzinfo is None:
                reg_at = reg_at.replace(tzinfo=timezone.utc)

            result.append(
                EventRegistrationUserResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    student_id=user.student_id,
                    answers=r.answers,
                    registered_at=reg_at,
                    checked_in=getattr(r, "checked_in", False),
                )

            )

        return result

    @staticmethod
    async def get_my_event_detail(
        event_id: PydanticObjectId,
        user_id: PydanticObjectId,
    ) -> MyEventDetailResponse:

        registration = await EventRegistrationRepository.get_by_event_and_user(
            event_id,
            user_id,
        )

        if not registration:
            app_exception(ErrorCode.REGISTRATION_NOT_FOUND)

        reg_at = registration.registered_at
        if reg_at.tzinfo is None:
            reg_at = reg_at.replace(tzinfo=timezone.utc)

        return MyEventDetailResponse(
            event_id=registration.event_id,
            answers=registration.answers,
            registered_at=reg_at,
            checked_in=getattr(registration, 'checked_in', False),
        )
