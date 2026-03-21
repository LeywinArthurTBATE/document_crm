from fastapi import FastAPI
from app.api.router import router
from app.workers.scheduler import start_scheduler, scheduler
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
app = FastAPI()

app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    if not scheduler.running:
        start_scheduler()

