import asyncio
import logging

from fastapi import APIRouter, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from utils.rate_limiter import limiter

from configs.cloudinary import init_cloudinary
from configs.database import init_db
from configs.seed_roles import seed_roles
from configs.rabbitmq import close_rabbitmq
from configs.redis_config import close_redis
from configs.settings import API_PREFIX, ENABLE_APP_SCHEDULER
from middleware.cors import register_cors
from routers.auth import router as auth_router
from routers.event_registration import router as event_registration_router
from routers.public_event import router as public_event_router
from routers.rbac import router as rbac_router
from routers.report import router as report_router
from routers.semester import router as semester_router
from routers.unit import router as unit_router
from routers.unit_event import router as unit_event_router
from routers.unit_event_submissions import router as unit_event_submissions_router
from routers.users import router as users_router
from routers.event_promotion import router as event_promotion_router
from routers.upload import router as upload_router
from routers.manual_attendance import router as manual_attendance_router
from scheduler.monthly_report import scheduler
from worker.checkin_sync_worker import run_checkin_sync_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logging.getLogger("be_service").setLevel(logging.INFO)

app = FastAPI(
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

register_cors(app)

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(rbac_router)
api_router.include_router(users_router)
api_router.include_router(unit_router)
api_router.include_router(semester_router)
api_router.include_router(public_event_router)
api_router.include_router(report_router)
api_router.include_router(event_registration_router)

api_router.include_router(unit_event_router)
api_router.include_router(unit_event_submissions_router)
api_router.include_router(event_promotion_router)
api_router.include_router(upload_router)
api_router.include_router(manual_attendance_router)
app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    await init_db()
    init_cloudinary()
    await seed_roles()
    asyncio.create_task(run_checkin_sync_worker())
    if ENABLE_APP_SCHEDULER and not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
async def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await close_rabbitmq()
    await close_redis()


@app.get(f"{API_PREFIX}/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
