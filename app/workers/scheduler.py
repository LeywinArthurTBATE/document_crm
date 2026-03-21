from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import AsyncSessionLocal
from app.workers.overdue_worker import process_overdue_documents


scheduler = AsyncIOScheduler()


async def overdue_job():
    async with AsyncSessionLocal() as db:
        await process_overdue_documents(db)


def start_scheduler():
    scheduler.add_job(
        overdue_job,
        "interval",
        minutes=1,  # ⚠️ потом можно увеличить до 5-10
        id="overdue_job",
        replace_existing=True,
    )

    scheduler.start()