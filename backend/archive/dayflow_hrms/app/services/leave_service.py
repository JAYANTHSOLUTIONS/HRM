from datetime import date, datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.assumed_existing.org_models import Employee
from app.core.exceptions import AppError
from app.models.document import Document
from app.models.leave import LeaveBalance, LeaveRequest, LeaveRequestStatus, LeaveType
from app.schemas.leave import LeaveRequestCreate

_ACTIVE_STATUSES = (LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED)


def list_leave_types(db: Session) -> list[LeaveType]:
    return db.query(LeaveType).order_by(LeaveType.leave_type_id.asc()).all()


def get_balances(db: Session, employee: Employee, year: int | None = None):
    year = year or datetime.now(timezone.utc).year
    balances = (
        db.query(LeaveBalance)
        .filter(LeaveBalance.employee_id == employee.employee_id, LeaveBalance.year == year)
        .all()
    )
    items = [
        {
            "leave_type": b.leave_type.name,
            "allocated_days": b.allocated_days,
            "used_days": b.used_days,
            "remaining_days": round(b.allocated_days - b.used_days, 2),
        }
        for b in balances
    ]
    return {"year": year, "items": items}


def _business_days_inclusive(start: date, end: date) -> float:
    """Counts Mon-Fri as leave days; weekends are not charged against
    balance. Swap for an org holiday-calendar service if one exists."""
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current = current.fromordinal(current.toordinal() + 1)
    return float(days)


def _has_overlap(db: Session, employee_id: int, start: date, end: date) -> bool:
    overlap = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(_ACTIVE_STATUSES),
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .first()
    )
    return overlap is not None


def apply_leave(db: Session, employee: Employee, payload: LeaveRequestCreate) -> LeaveRequest:
    leave_type = db.query(LeaveType).filter(LeaveType.leave_type_id == payload.leave_type_id).first()
    if leave_type is None:
        raise AppError("LEAVE_TYPE_NOT_FOUND", "Unknown leave type.", status_code=404)

    if leave_type.requires_attachment and not payload.attachment_document_id:
        raise AppError(
            "ATTACHMENT_REQUIRED",
            f"{leave_type.name} requires a supporting attachment.",
            status_code=422,
        )

    if payload.attachment_document_id:
        doc = (
            db.query(Document)
            .filter(
                Document.document_id == payload.attachment_document_id,
                Document.employee_id == employee.employee_id,
            )
            .first()
        )
        if doc is None:
            raise AppError(
                "ATTACHMENT_NOT_FOUND",
                "Attachment must be a document you previously uploaded.",
                status_code=404,
            )

    # Backend pre-check. A DB-level uniqueness/exclusion constraint or
    # trigger on (employee_id, status, daterange) is the final line of
    # defense against a race between two concurrent requests — this
    # application-level check narrows the window but a trigger should
    # still reject the rare concurrent double-insert with the same
    # OVERLAPPING_LEAVE_REQUEST error.
    if _has_overlap(db, employee.employee_id, payload.start_date, payload.end_date):
        raise AppError(
            "OVERLAPPING_LEAVE_REQUEST",
            "You already have a pending or approved leave request that overlaps these dates.",
            status_code=409,
        )

    number_of_days = _business_days_inclusive(payload.start_date, payload.end_date)

    if leave_type.is_balance_tracked:
        year = payload.start_date.year
        balance = (
            db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == employee.employee_id,
                LeaveBalance.leave_type_id == leave_type.leave_type_id,
                LeaveBalance.year == year,
            )
            .first()
        )
        remaining = (balance.allocated_days - balance.used_days) if balance else 0.0
        if number_of_days > remaining:
            raise AppError(
                "INSUFFICIENT_LEAVE_BALANCE",
                f"You only have {remaining} day(s) remaining for {leave_type.name}.",
                status_code=422,
            )

    request = LeaveRequest(
        employee_id=employee.employee_id,
        leave_type_id=leave_type.leave_type_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        number_of_days=number_of_days,
        remarks=payload.remarks,
        attachment_document_id=payload.attachment_document_id,
        status=LeaveRequestStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_my_requests(db: Session, employee: Employee, status_filter: str | None = None):
    query = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee.employee_id)
    if status_filter:
        try:
            status_enum = LeaveRequestStatus(status_filter)
        except ValueError:
            raise AppError("INVALID_STATUS", f"Unknown status '{status_filter}'.", status_code=400)
        query = query.filter(LeaveRequest.status == status_enum)
    return query.order_by(LeaveRequest.submitted_at.desc()).all()


def cancel_request(db: Session, employee: Employee, leave_request_id: int) -> LeaveRequest:
    request = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.leave_request_id == leave_request_id,
            LeaveRequest.employee_id == employee.employee_id,
        )
        .first()
    )
    if request is None:
        raise AppError("LEAVE_REQUEST_NOT_FOUND", "Leave request not found.", status_code=404)

    if request.status != LeaveRequestStatus.PENDING:
        raise AppError(
            "CANNOT_CANCEL",
            f"Only PENDING requests can be cancelled (current status: {request.status.value}).",
            status_code=409,
        )

    request.status = LeaveRequestStatus.CANCELLED
    request.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request
