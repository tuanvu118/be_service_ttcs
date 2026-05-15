from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.report import ReportService
from services.unit_event_service import UnitEventService
from repositories.unit_event_repo import UnitEventRepo

scheduler = AsyncIOScheduler()

scheduler.add_job(
    ReportService.auto_create_monthly_reports,
    "cron",
    hour="*",
    minute=0,
)

scheduler.add_job(
    UnitEventService(UnitEventRepo()).auto_approve_waiting_submissions_after_registration_deadline,
    "interval",
    minutes=1,
)