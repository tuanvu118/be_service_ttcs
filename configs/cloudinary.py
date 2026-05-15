import cloudinary

from configs.settings import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_FOLDER,
    CLOUDINARY_NAME,
)


def init_cloudinary() -> None:
    cloudinary.config(
        cloud_name=CLOUDINARY_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
