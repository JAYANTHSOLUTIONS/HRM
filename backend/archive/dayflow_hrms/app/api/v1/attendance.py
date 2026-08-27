from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.core.exceptions import AppError
from app.schemas.attendance import (
    AttendanceRangeOut,
    AttendanceTodayOut,
    CheckInOut,
    CheckOutOut,
)
from app.services import attendance_service

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


@router.get("/today", response_model=AttendanceTodayOut)
def get_today(employee: Employee = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = attendance_service.get_today(db, employee)
    if record is None:
        return AttendanceTodayOut(
            attendance_date=datetime.now(timezone.utc).date(),
            check_in_at=None,
            check_out_at=None,
            work_hours=0.0,
            status="ABSENT",
        )
    return record


@router.post("/check-in", response_model=CheckInOut)
def check_in(employee: Employee = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = attendance_service.check_in(db, employee)
    return record


@router.post("/check-out", response_model=CheckOutOut)
def check_out(employee: Employee = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = attendance_service.check_out(db, employee)
    return record


@router.get("/me", response_model=AttendanceRangeOut)
def get_my_attendance(
    range: str = Query(..., pattern="^(daily|weekly)$"),
    date_: date = Query(..., alias="date"),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    result = attendance_service.get_range(db, employee, range, date_)
    return result
