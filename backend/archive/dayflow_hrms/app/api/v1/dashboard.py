from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.auth import User, get_current_user
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.schemas.dashboard import DashboardMeOut
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/me", response_model=DashboardMeOut)
def get_my_dashboard(
    request: Request,
    employee: Employee = Depends(get_current_employee),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_dashboard(db, employee, user, str(request.base_url))
