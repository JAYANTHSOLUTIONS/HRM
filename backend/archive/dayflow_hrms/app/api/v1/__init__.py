from fastapi import APIRouter

from app.api.v1.attendance import router as attendance_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import documents_router, employee_documents_router
from app.api.v1.employees import router as employees_router
from app.api.v1.leave import leave_router, leave_types_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.salary import router as salary_router

employee_module_router = APIRouter()
for r in (
    employees_router,
    attendance_router,
    leave_types_router,
    leave_router,
    salary_router,
    dashboard_router,
    notifications_router,
    employee_documents_router,
    documents_router,
):
    employee_module_router.include_router(r)
