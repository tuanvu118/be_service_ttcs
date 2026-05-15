import asyncio
import signal

from configs.database import init_db
from configs.seed_roles import seed_roles
from scheduler.monthly_report import scheduler


async def _wait_for_shutdown() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Signal handlers are not available on some platforms.
            pass

    await stop_event.wait()


async def _main() -> None:
    await init_db()
    await seed_roles()

    if not scheduler.running:
        scheduler.start()

    try:
        await _wait_for_shutdown()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(_main())
