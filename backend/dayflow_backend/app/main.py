import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError

from app.core.config import get_settings
from app.exceptions import AppError, app_error_handler
from app.routers import (
    employees, reference, documents, attendance, leave, salary, dashboard, admin, audit,
)
from app.routers import auth
from app.routers.me import router as me_router, employee_dashboard_router

settings = get_settings()
logger = logging.getLogger("dayflow.part2")

# Automatically create all tables (including newly defined ones like employee_resumes)
from app.core.database import Base, engine
import app.models  # noqa: F401
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dayflow HRMS — Admin/HR API (Part 2)",
    description=(
        "Admin + HR module for the Dayflow HRMS backend. Authenticates against "
        "tokens issued by Part 1 (auth module) and shares Part 1's MySQL database."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins= ["http://localhost:8443",
        "http://localhost:5175",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("IntegrityError on %s %s: %s", request.method, request.url.path, exc)
    # MySQL trigger-based overlap protection (leave_requests) surfaces here as SIGNAL 45000.
    message = str(exc.orig) if exc.orig else "A database constraint was violated."
    if "Overlapping active leave request" in message:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "OVERLAPPING_LEAVE", "message": "This date range overlaps an existing pending or approved leave request.", "details": []}},
        )
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "DATA_INTEGRITY_ERROR", "message": "This operation violates a data integrity constraint.", "details": []}},
    )


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def db_error_handler(request: Request, exc):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "DATABASE_UNAVAILABLE", "message": "A database error occurred. Please try again.", "details": []}},
    )


API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(employees.router, prefix=API_PREFIX)
app.include_router(reference.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(leave.router, prefix=API_PREFIX)
app.include_router(salary.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(me_router, prefix=API_PREFIX)
app.include_router(employee_dashboard_router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
