from datetime import datetime, timezone
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import UploadFile

from exceptions import ErrorCode, app_exception
from models.event_promotion import EventPromotion, OrganizationInfo, EventTime
from repositories.event_promotion_repo import EventPromotionRepository
from schemas.event_promotion import EventPromotionCreate, EventPromotionUpdate, EventPromotionStatusUpdate
from schemas.auth import TokenData
from repositories.unit_repo import UnitRepo
from services.cloudinary_service import upload_image

class EventPromotionService:
    @staticmethod
    async def create_promotion(
        data: EventPromotionCreate, 
        unit_id: PydanticObjectId, 
        user_id: PydanticObjectId,
        image: Optional[UploadFile] = None
    ) -> EventPromotion:
        # Get Unit info for embedding
        unit = await UnitRepo().get_by_id(unit_id)
        if not unit:
            app_exception(ErrorCode.UNIT_NOT_FOUND)

        promo_data = data.model_dump()
        # Handle time
        time_data = promo_data.pop("time")
        
        if image:
            image_url, _ = upload_image(image)
            promo_data["image_url"] = image_url
        
        promo = {
            **promo_data,
            "time": EventTime(**time_data) if time_data else None,
            "unit_id": unit_id,
            "created_by_id": user_id,
            "organization": OrganizationInfo(id=str(unit_id), name=unit.name),
            "status": "CHO_DUYET"
        }
        
        return await EventPromotionRepository.create(promo)

    @staticmethod
    async def get_all_for_admin(
        status: Optional[str] = None, 
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        items, total = await EventPromotionRepository.get_all_for_admin(status, semester_id, skip, limit)
        return {"items": items, "total": total}

    @staticmethod
    async def get_for_unit(
        unit_id: PydanticObjectId, 
        status: Optional[str] = None,
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        items, total = await EventPromotionRepository.get_by_unit(unit_id, status, semester_id, skip, limit)
        return {"items": items, "total": total}

    @staticmethod
    async def get_for_students(skip: int = 0, limit: int = 10, unit_id: Optional[PydanticObjectId] = None):
        now = datetime.now(timezone.utc)
        items, total = await EventPromotionRepository.get_active_for_students(now, skip, limit, unit_id)
        return {"items": items, "total": total}

    @staticmethod
    async def get_detail(id: PydanticObjectId) -> EventPromotion:
        promo = await EventPromotionRepository.get_by_id(id)
        if not promo:
            app_exception(ErrorCode.EVENT_NOT_FOUND)
        return promo

    @staticmethod
    async def update_promotion(
        id: PydanticObjectId, 
        data: EventPromotionUpdate, 
        unit_id: PydanticObjectId,
        image: Optional[UploadFile] = None
    ) -> EventPromotion:
        promo = await EventPromotionService.get_detail(id)
        
        # Permission check: Same unit
        if str(promo.unit_id) != str(unit_id):
            app_exception(ErrorCode.INSUFFICIENT_PERMISSION)
            
        # Business Rule: Only editable if status is CHO_DUYET
        if promo.status != "CHO_DUYET":
            app_exception(ErrorCode.EVENT_LOCKED, extra_detail="Chỉ có thể chỉnh sửa khi đang chờ duyệt. Sự kiện bị từ chối hoặc đã duyệt không được sửa.")

        update_dict = data.model_dump(exclude_unset=True)
        
        if image:
            image_url, _ = upload_image(image)
            update_dict["image_url"] = image_url
            
        # Handle time separately if present
        if "time" in update_dict and update_dict["time"]:
            time_data = update_dict.pop("time")
            promo.time = EventTime(**time_data)
            
        for key, value in update_dict.items():
            setattr(promo, key, value)
            
        promo.updated_at = datetime.now(timezone.utc)
        return await EventPromotionRepository.update(promo)

    @staticmethod
    async def update_status(id: PydanticObjectId, data: EventPromotionStatusUpdate) -> EventPromotion:
        promo = await EventPromotionService.get_detail(id)
        
        # Admin can change status. 
        # Design says: Admin can reject approved event.
        # So we just update.
        promo.status = data.status
        if data.rejected_reason:
            promo.rejected_reason = data.rejected_reason
        else:
            promo.rejected_reason = None
            
        promo.updated_at = datetime.now(timezone.utc)
        return await EventPromotionRepository.update(promo)

    @staticmethod
    async def delete_promotion(id: PydanticObjectId, unit_id: PydanticObjectId):
        promo = await EventPromotionService.get_detail(id)
        
        # Permission check: Same unit
        if str(promo.unit_id) != str(unit_id):
            app_exception(ErrorCode.INSUFFICIENT_PERMISSION)
            
        # Business Rule: Cant delete if approved? Original design said cant delete if DA_DUYET.
        # User clarification: "từ chối thì huỷ luon. staff có quyền xoá".
        if promo.status == "DA_DUYET":
             app_exception(ErrorCode.EVENT_LOCKED, extra_detail="Không thể xóa sự kiện đã được phê duyệt công khai.")
             
        await EventPromotionRepository.delete(promo)
