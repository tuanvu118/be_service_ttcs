# services/cloudinary_service.py
from fastapi import UploadFile
from cloudinary.uploader import upload, destroy

from configs.cloudinary import CLOUDINARY_FOLDER
import configs.cloudinary
from exceptions import ErrorCode, app_exception

ALLOWED = {"image/jpeg", "image/png", "image/jpg"}


def upload_image(file: UploadFile):
    if file.content_type not in ALLOWED:
        app_exception(ErrorCode.INVALID_IMAGE_TYPE)

    res = upload(
        file.file,
        folder=(CLOUDINARY_FOLDER or None),
        resource_type="image",
    )
    return res["secure_url"], res["public_id"]


def delete_image(public_id: str):
    if not public_id:
        return None
    return destroy(public_id, resource_type="image")
