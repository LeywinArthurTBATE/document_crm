# app/main.py
from fastapi import FastAPI
from app.api.router import router
from app.workers.scheduler import start_scheduler, scheduler
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    print("Starting up")
    if not scheduler.running:
        print("Starting scheduler")
        start_scheduler()