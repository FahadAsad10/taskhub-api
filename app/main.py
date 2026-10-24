from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.deps import DbSession
from app.routers import auth, projects, tasks

app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="A task and project management REST API with JWT auth, filtering, pagination and stats.",
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health", tags=["meta"])
def health(db: DbSession) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
