from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance, UTCDateTime
from app.models.hr import Employee
from app.exceptions import not_found, bad_request
from app.services.audit_service import write_audit_log


def list_attendance(db: Session, *, page: int, page_size: int, attendance_date: date | None):
    query = db.query(Attendance).options(joinedload(Attendance.employee))
    if attendance_date is not None:
        query = query.filter(Attendance.attendance_date == attendance_date)

    total_items = query.order_by(None).with_entities(func.count(Attendance.attendance_id)).scalar()
    items = (
        query.order_by(Attendance.attendance_date.desc(), Attendance.attendance_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_items


def _compute_work_hours(check_in_at: datetime | None, check_out_at: datetime | None) -> Decimal:
    if check_in_at is None or check_out_at is None:
        return Decimal("0.00")
    if check_out_at <= check_in_at:
        raise bad_request("check_out_at must be after check_in_at.")
    delta_hours = Decimal((check_out_at - check_in_at).total_seconds()) / Decimal(3600)
    return delta_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def correct_attendance(
    db: Session,
    *,
    attendance_id: int,
    check_in_at: datetime | None,
    check_out_at: datetime | None,
    reason: str,
    corrected_by_user_id: int,
) -> Attendance:
    # Row lock so two concurrent corrections don't race.
    record = (
        db.query(Attendance)
        .filter(Attendance.attendance_id == attendance_id)
        .with_for_update()
        .first()
    )
    if record is None:
        raise not_found("Attendance record")

    old_values = {
        "check_in_at": record.check_in_at.isoformat() if record.check_in_at else None,
        "check_out_at": record.check_out_at.isoformat() if record.check_out_at else None,
        "work_hours": str(record.work_hours),
        "status": record.status,
    }

    new_check_in = UTCDateTime.normalize(check_in_at) if check_in_at is not None else record.check_in_at
    new_check_out = UTCDateTime.normalize(check_out_at) if check_out_at is not None else record.check_out_at

    # NEVER trust client work_hours — always recomputed server-side.
    record.check_in_at = new_check_in
    record.check_out_at = new_check_out
    record.work_hours = _compute_work_hours(new_check_in, new_check_out)
    record.status = "PRESENT" if record.work_hours > 0 else record.status
    record.is_corrected = True
    record.corrected_by = corrected_by_user_id
    record.correction_reason = reason

    db.flush()

    new_values = {
        "check_in_at": record.check_in_at.isoformat() if record.check_in_at else None,
        "check_out_at": record.check_out_at.isoformat() if record.check_out_at else None,
        "work_hours": str(record.work_hours),
        "status": record.status,
        "reason": reason,
    }
    write_audit_log(
        db,
        actor_user_id=corrected_by_user_id,
        action="ATTENDANCE_CORRECTED",
        target_entity="attendance",
        target_id=record.attendance_id,
        old_values=old_values,
        new_values=new_values,
    )
    db.commit()
    db.refresh(record)
    return record
