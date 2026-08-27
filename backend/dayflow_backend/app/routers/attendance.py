import math
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_or_hr
from app.models.auth import User
from app.schemas.attendance import AttendanceOut, AttendanceCorrectRequest
from app.schemas.common import Page
from app.services.attendance_service import list_attendance, correct_attendance

router = APIRouter(prefix="/attendance", tags=["Attendance (Admin/HR)"])


def _to_out(record) -> AttendanceOut:
    return AttendanceOut(
        attendance_id=record.attendance_id,
        employee_id=record.employee_id,
        employee_name=record.employee.full_name if record.employee else None,
        attendance_date=record.attendance_date,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        work_hours=record.work_hours,
        overtime_hours=record.overtime_hours,
        status=record.status,
        is_corrected=record.is_corrected,
    )


@router.get("", response_model=Page[AttendanceOut])
def get_attendance(
    date_: date | None = Query(default=None, alias="date"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_hr),
):
    items, total_items = list_attendance(db, page=page, page_size=page_size, attendance_date=date_)
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    return {"page": page, "page_size": page_size, "total_items": total_items,
            "total_pages": total_pages, "items": [_to_out(i) for i in items]}


@router.patch("/{attendance_id}/correct", response_model=AttendanceOut)
def correct(
    attendance_id: int, payload: AttendanceCorrectRequest,
    db: Session = Depends(get_db), user: User = Depends(require_admin_or_hr),
):
    record = correct_attendance(
        db, attendance_id=attendance_id, check_in_at=payload.check_in_at,
        check_out_at=payload.check_out_at, reason=payload.reason, corrected_by_user_id=user.user_id,
    )
    return _to_out(record)
