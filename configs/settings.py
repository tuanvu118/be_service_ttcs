import os
from pathlib import Path

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parent

# Root .env is the main deploy source.
load_dotenv(PROJECT_ROOT / ".env")

# Legacy backend .env is only used when no runtime config was injected.
if not any(
    os.getenv(key)
    for key in (
        "MONGO_URI",
        "MONGO_HOST",
        "MONGO_INITDB_ROOT_USERNAME",
        "JWT_SECRET",
    )
):
    load_dotenv(APP_DIR / ".env")

API_PREFIX = "/api"
BACKEND_CONTAINER_PORT = int(os.getenv("BACKEND_CONTAINER_PORT", "8000"))
DB_NAME = os.getenv("MONGO_DATABASE") or os.getenv("DB_NAME", "ttcs")


def build_mongo_uri() -> str:
    explicit_uri = os.getenv("MONGO_URI")
    if explicit_uri:
        return explicit_uri

    username = os.getenv("MONGO_INITDB_ROOT_USERNAME", "ttcs_root")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "change_me_mongo_root_password")
    host = os.getenv("MONGO_HOST", "mongodb")
    port = os.getenv("MONGO_PORT", "27017")

    return f"mongodb://{username}:{password}@{host}:{port}/{DB_NAME}?authSource=admin"


MONGO_URI = build_mongo_uri()
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "CHANGE_ME_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def get_bool_env(key: str, default: bool) -> bool:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST.lstrip('/')}",
)

RABBITMQ_REGISTRATION_SYNC_EXCHANGE = os.getenv(
    "RABBITMQ_REGISTRATION_SYNC_EXCHANGE",
    "registration.sync.events",
)
RABBITMQ_REGISTRATION_SYNC_QUEUE = os.getenv(
    "RABBITMQ_REGISTRATION_SYNC_QUEUE",
    "registration.sync.queue",
)
RABBITMQ_REGISTRATION_SYNC_ROUTING_KEY = os.getenv(
    "RABBITMQ_REGISTRATION_SYNC_ROUTING_KEY",
    "registration.sync.requested",
)

RABBITMQ_PREFETCH_COUNT = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "20"))
HTSK_REGISTER_LOCK_TTL_SECONDS = int(os.getenv("HTSK_REGISTER_LOCK_TTL_SECONDS", "10"))
QR_MAX_WINDOWS_PER_SESSION = int(os.getenv("QR_MAX_WINDOWS_PER_SESSION", "720"))
ATTENDANCE_MANUAL_CODE_LENGTH = int(os.getenv("ATTENDANCE_MANUAL_CODE_LENGTH", "8"))
ENABLE_APP_SCHEDULER = get_bool_env("ENABLE_APP_SCHEDULER", True)

CLOUDINARY_NAME = os.getenv("CLOUDINARY_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "").strip()


def get_cors_origins() -> list[str]:
    raw_value = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if raw_value:
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
        "https://localhost",
        "https://127.0.0.1",
    ]
