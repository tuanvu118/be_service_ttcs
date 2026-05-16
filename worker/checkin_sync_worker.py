import asyncio
import json
import logging
from typing import Any

from beanie import PydanticObjectId
from bson.errors import InvalidId
from pydantic import ValidationError

from configs.database import init_db
from configs.rabbitmq import close_rabbitmq, get_checkin_sync_queue
from repositories.event_registration_repo import EventRegistrationRepository
from repositories.unit_event_submission_members_repo import UnitEventSubmissionMembersRepo
from repositories.unit_event_submissions_repo import UnitEventSubmissionsRepo

logger = logging.getLogger("be_service.checkin_sync_worker")
logger.setLevel(logging.INFO)


def _to_object_id(value: Any, field_name: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(value)
    except (InvalidId, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} khong dung dinh dang ObjectId") from exc


async def process_sync_message(payload: dict[str, Any]) -> None:
    event_type = payload.get("event_type")
    event_id = _to_object_id(payload.get("event_id"), "event_id")
    user_id = _to_object_id(payload.get("user_id"), "user_id")
    request_id = payload.get("request_id")

    if event_type == "public":
        registration = await EventRegistrationRepository.mark_checked_in(event_id, user_id)
        if registration:
            logger.info(
                "[be_ttcs: Thành công] Đã cập nhật check-in PublicEvent | request_id=%s | user=%s | event=%s",
                request_id,
                user_id,
                event_id,
            )
        else:
            logger.warning(
                "[be_ttcs: Cảnh báo] Không tìm thấy đăng ký PublicEvent để đồng bộ check-in, hoặc đã check-in trước đó | request_id=%s | user=%s | event=%s",
                request_id,
                user_id,
                event_id,
            )
        return

    if event_type == "unit":
        submissions = await UnitEventSubmissionsRepo().get_all_by_unit_event_id(event_id)
        submission_ids = [submission.id for submission in submissions if submission.id]
        updated_count = await UnitEventSubmissionMembersRepo().mark_checked_in_by_submission_ids_and_user(
            unit_event_submission_ids=submission_ids,
            user_id=user_id,
        )
        if updated_count > 0:
            logger.info(
                "[be_ttcs: Thành công] Đã cập nhật check-in UnitEvent | request_id=%s | user=%s | event=%s | members=%s",
                request_id,
                user_id,
                event_id,
                updated_count,
            )
        else:
            logger.warning(
                "[be_ttcs: Cảnh báo] Không tìm thấy thành viên UnitEvent để đồng bộ check-in, hoặc đã check-in trước đó | request_id=%s | user=%s | event=%s",
                request_id,
                user_id,
                event_id,
            )
        return

    raise ValueError(f"event_type khong hop le: {event_type}")


async def run_checkin_sync_worker() -> None:
    await init_db()
    queue = await get_checkin_sync_queue()
    logger.info("[be_ttcs: Thông báo] Đã khởi động Worker đồng bộ Check-in. Đang chờ tin nhắn...")

    async with queue.iterator() as queue_iterator:
        async for message in queue_iterator:
            async with message.process(requeue=True):
                try:
                    payload = json.loads(message.body.decode("utf-8"))
                    await process_sync_message(payload)
                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    ValidationError,
                    ValueError,
                    TypeError,
                    KeyError,
                ) as exc:
                    logger.error(
                        "[be_ttcs: Lỗi] Message đồng bộ check-in không hợp lệ, bỏ qua | message_id=%s | error=%s",
                        message.message_id,
                        exc,
                    )
                except Exception:
                    logger.exception(
                        "[be_ttcs: Lỗi] Lỗi khi xử lý message đồng bộ check-in | message_id=%s",
                        message.message_id,
                    )
                    raise


async def _main() -> None:
    try:
        await run_checkin_sync_worker()
    finally:
        await close_rabbitmq()


if __name__ == "__main__":
    asyncio.run(_main())
