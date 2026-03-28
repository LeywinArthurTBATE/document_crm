from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import AsyncSessionLocal
from app.workers.overdue_worker import process_overdue_documents
import asyncio

scheduler = AsyncIOScheduler()

async def run_overdue_worker():
    async with AsyncSessionLocal() as db:
        await process_overdue_documents(db)

def start_scheduler():
    # запускаем каждые 30 минут
    scheduler.add_job(
        run_overdue_worker,
        trigger=IntervalTrigger(minutes=1),
        id="overdue_worker",
        replace_existing=True,
        next_run_time=datetime.now()   # ← КЛЮЧЕВОЕ
    )
    scheduler.start()