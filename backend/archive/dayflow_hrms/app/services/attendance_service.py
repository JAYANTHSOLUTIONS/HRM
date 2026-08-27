from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.assumed_existing.org_models import Employee
from app.core.exceptions import AppError
from app.models.attendance import Attendance, AttendanceStatus
from app.models.leave import LeaveRequest, LeaveRequestStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_today(db: Session, employee: Employee) -> Attendance | None:
    today = _utcnow().date()
    return (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.employee_id, Attendance.attendance_date == today)
        .first()
    )


def check_in(db: Session, employee: Employee) -> Attendance:
    today = _utcnow().date()
    existing = get_today(db, employee)
    if existing is not None and existing.check_in_at is not None:
        raise AppError(
            code="ALREADY_CHECKED_IN",
            message="You have already checked in today.",
            status_code=409,
        )

    now = _utcnow()
    if existing is None:
        record = Attendance(
            employee_id=employee.employee_id,
            attendance_date=today,
            check_in_at=now,
            status=AttendanceStatus.PRESENT,
        )
        db.add(record)
    else:
        existing.check_in_at = now
        existing.status = AttendanceStatus.PRESENT
        record = existing

    db.commit()
    db.refresh(record)
    return record


def check_out(db: Session, employee: Employee) -> Attendance:
    record = get_today(db, employee)
    if record is None or record.check_in_at is None:
        raise AppError(
            code="NOT_CHECKED_IN",
            message="You must check in before you can check out.",
            status_code=409,
        )
    if record.check_out_at is not None:
        raise AppError(
            code="ALREADY_CHECKED_OUT",
            message="You have already checked out today.",
            status_code=409,
        )

    now = _utcnow()
    record.check_out_at = now
    delta_seconds = (now - record.check_in_at).total_seconds()
    record.work_hours = round(max(delta_seconds, 0) / 3600, 2)

    db.commit()
    db.refresh(record)
    return record


def _week_bounds(for_date: date) -> tuple[date, date]:
    # Sunday-start week, matching the spec's example
    # (17 Aug 2026 is a Monday; 23 Aug 2026 is the following Sunday —
    # the spec's own example uses week_start=Mon, week_end=Sun).
    weekday = for_date.weekday()  # Monday=0
    week_start = for_date - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_range(db: Session, employee: Employee, range_: str, for_date: date):
    if range_ not in ("daily", "weekly"):
        raise AppError("INVALID_RANGE", "range must be 'daily' or 'weekly'.", status_code=400)

    if range_ == "daily":
        start, end = for_date, for_date
    else:
        start, end = _week_bounds(for_date)

    records = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.employee_id,
            Attendance.attendance_date >= start,
            Attendance.attendance_date <= end,
        )
        .order_by(Attendance.attendance_date.asc())
        .all()
    )

    present_days = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)

    leaves_used = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee.employee_id,
            LeaveRequest.status == LeaveRequestStatus.APPROVED,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .count()
    )

    total_working_days = (end - start).days + 1
    if range_ == "weekly":
        # Mon-Fri by default; overridable once an org calendar service exists.
        total_working_days = 5

    return {
        "range": range_,
        "week_start": start if range_ == "weekly" else None,
        "week_end": end if range_ == "weekly" else None,
        "summary": {
            "count_of_days_present": present_days,
            "leaves_used": leaves_used,
            "total_working_days": total_working_days,
        },
        "items": records,
    }
