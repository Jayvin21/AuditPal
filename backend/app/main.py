from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import init_db

from app.api.routes import (
    health,
    workspaces,
    uploads,
    audit_runs,
    findings,
    records,
    column_mappings,
    reports, import_templates,
)


app = FastAPI(title=settings.app_name)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(health.router)
app.include_router(workspaces.router)
app.include_router(uploads.router)
app.include_router(audit_runs.router)
app.include_router(findings.router)
app.include_router(records.router)
app.include_router(column_mappings.router)
app.include_router(reports.router)
app.include_router(import_templates.router)