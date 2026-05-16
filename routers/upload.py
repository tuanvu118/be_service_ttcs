from fastapi import APIRouter, Depends, UploadFile, status
from internal_auth import get_current_user_from_gateway
from services.cloudinary_service import upload_image

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user_from_gateway)],
)
async def upload_file(file: UploadFile):
    url, public_id = upload_image(file)
    return {"url": url, "public_id": public_id}
