from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_or_hr
from app.schemas.dashboard import AdminDashboardOut
from app.services.dashboard_service import get_admin_dashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=AdminDashboardOut)
def admin_dashboard(db: Session = Depends(get_db), _=Depends(require_admin_or_hr)):
    return get_admin_dashboard(db)
