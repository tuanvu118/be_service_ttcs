from datetime import datetime, timezone, timedelta
from typing import Optional, List

from beanie import PydanticObjectId
from fastapi import UploadFile

from exceptions import ErrorCode, app_exception
from schemas.public_event import PublicEventCreate, PublicEventRead, PublicEventUpdate
from repositories.public_event_repo import PublicEventRepository
from repositories.semester_repo import SemesterRepo
from repositories.event_registration_repo import EventRegistrationRepository

class PublicEventService:
    @staticmethod
    def _ensure_utc(dt):
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _validate_time(
        registration_start,
        registration_end,
        event_start,
        event_end,
    ):
        registration_start = PublicEventService._ensure_utc(registration_start)
        registration_end = PublicEventService._ensure_utc(registration_end)
        event_start = PublicEventService._ensure_utc(event_start)
        event_end = PublicEventService._ensure_utc(event_end)

        if registration_start >= registration_end:
            app_exception(ErrorCode.INVALID_REGISTRATION_TIME)

        if event_start < registration_end:
            app_exception(ErrorCode.EVENT_MUST_START_AFTER_REGISTRATION)

        if event_start >= event_end:
            app_exception(ErrorCode.INVALID_EVENT_TIME)
        
        return registration_start, registration_end, event_start, event_end

    #validate form fields
    @staticmethod
    def _validate_form_fields(form_fields):
        if not form_fields:
            return

        ids = set()

        for field in form_fields:
            if field.id in ids:
                app_exception(ErrorCode.INVALID_FORM_FIELD)

            ids.add(field.id)

            if field.field_type in ["select", "radio", "checkbox"]:
                if not field.options:
                    app_exception(ErrorCode.INVALID_FORM_FIELD)
    @staticmethod
    async def create_event(data: PublicEventCreate, image: Optional[UploadFile] = None):

        data.registration_start, data.registration_end, data.event_start, data.event_end = PublicEventService._validate_time(
            data.registration_start,
            data.registration_end,
            data.event_start,
            data.event_end,
        )

        # validate form
        PublicEventService._validate_form_fields(data.form_fields)
        payload = data.model_dump()
        
        # Ensure payload has the aware datetimes if model_dump didn't preserve them as aware (it should, but just in case)
        payload["registration_start"] = data.registration_start
        payload["registration_end"] = data.registration_end
        payload["event_start"] = data.event_start
        payload["event_end"] = data.event_end
        
        if image:
            from services.cloudinary_service import upload_image
            image_url, _ = upload_image(image)
            payload["image_url"] = image_url
            
        if payload.get("semester_id"):
            payload["semester_id"] = payload["semester_id"]
        else:
            semester = await SemesterRepo().get_active()
            if not semester:
                app_exception(ErrorCode.ACTIVE_SEMESTER_REQUIRED_FOR_EVENT)
            payload["semester_id"] = semester.id

        created_event = await PublicEventRepository.create(payload)
        return await PublicEventService._to_public_event_read(created_event)

    @staticmethod
    async def _add_participant_count(event) -> dict:
        count = await EventRegistrationRepository.count_by_event(event.id)
        dump = event.model_dump()
        dump["current_participants"] = count
        return dump

    @staticmethod
    async def _to_public_event_read(event) -> PublicEventRead:
        enriched_event = await PublicEventService._add_participant_count(event)
        return PublicEventRead.model_validate(enriched_event)

    @staticmethod
    async def get_events(
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        events, total = await PublicEventRepository.get_all(semester_id=semester_id, skip=skip, limit=limit)
        items = [await PublicEventService._to_public_event_read(e) for e in events]
        return {"items": items, "total": total}

    @staticmethod
    async def get_valid_events(
        semester_id: Optional[PydanticObjectId] = None,
        search: Optional[str] = None,
        time_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ):
        now = datetime.now(timezone.utc)
        
        started_after = None
        started_before = None
        
        if time_filter == "this_week":
            started_after = now
            started_before = now + timedelta(days=7)
        elif time_filter == "this_month":
            started_after = now
            started_before = now + timedelta(days=30)
        elif time_filter == "upcoming":
            started_after = now
            
        events, total = await PublicEventRepository.get_valid_events(
            now=now,
            semester_id=semester_id,
            search=search,
            started_after=started_after,
            started_before=started_before,
            skip=skip,
            limit=limit
        )
        items = [await PublicEventService._to_public_event_read(e) for e in events]
        return {"items": items, "total": total}

    @staticmethod
    async def get_event_by_id(event_id: PydanticObjectId):
        event = await PublicEventRepository.get_by_id(event_id)
        if not event:
             app_exception(ErrorCode.EVENT_NOT_FOUND)
             
        return await PublicEventService._to_public_event_read(event)

    @staticmethod
    async def update_event(event_id: PydanticObjectId, data: PublicEventUpdate, image: Optional[UploadFile] = None):

        event = await PublicEventRepository.get_by_id(event_id)
        if not event:
            app_exception(ErrorCode.EVENT_NOT_FOUND)

        update_data = data.model_dump(exclude_unset=True)
        # created_at should not be updated, but semester_id can be
        if "created_at" in update_data:
            del update_data["created_at"]

        if image:
            from services.cloudinary_service import upload_image
            image_url, _ = upload_image(image)
            update_data["image_url"] = image_url

        merged_data = {
            "registration_start": update_data.get(
                "registration_start", event.registration_start
            ),
            "registration_end": update_data.get(
                "registration_end", event.registration_end
            ),
            "event_start": update_data.get(
                "event_start", event.event_start
            ),
            "event_end": update_data.get(
                "event_end", event.event_end
            ),
        }

        merged_data["registration_start"], merged_data["registration_end"], merged_data["event_start"], merged_data["event_end"] = PublicEventService._validate_time(
            merged_data["registration_start"],
            merged_data["registration_end"],
            merged_data["event_start"],
            merged_data["event_end"],
        )

        # Update update_data with aware datetimes
        if "registration_start" in update_data: update_data["registration_start"] = merged_data["registration_start"]
        if "registration_end" in update_data: update_data["registration_end"] = merged_data["registration_end"]
        if "event_start" in update_data: update_data["event_start"] = merged_data["event_start"]
        if "event_end" in update_data: update_data["event_end"] = merged_data["event_end"]

        # validate form_fields nếu có update
        if data.form_fields is not None:
            PublicEventService._validate_form_fields(data.form_fields)

        updated_event = await PublicEventRepository.update(event_id, update_data)
        return await PublicEventService._to_public_event_read(updated_event)

    @staticmethod
    async def delete_event(event_id: PydanticObjectId):
        success = await PublicEventRepository.delete(event_id)
        if not success:
            app_exception(ErrorCode.EVENT_NOT_FOUND)
        return True
