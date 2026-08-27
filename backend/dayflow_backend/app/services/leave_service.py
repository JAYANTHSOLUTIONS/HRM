from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.leave import LeaveRequest, LeaveBalance, LeaveRequestReview, LeaveType
from app.exceptions import not_found, conflict, bad_request
from app.services.audit_service import write_audit_log
from app.services.notification_service import notify


def list_leave_types(db: Session):
    return db.query(LeaveType).filter(LeaveType.is_active.is_(True)).order_by(LeaveType.name).all()


def list_leave_requests(db: Session, *, page: int, page_size: int, status: str | None):
    query = db.query(LeaveRequest).options(
        joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type)
    )
    if status is not None:
        query = query.filter(LeaveRequest.status == status)

    total_items = query.order_by(None).with_entities(func.count(LeaveRequest.leave_request_id)).scalar()
    items = (
        query.order_by(LeaveRequest.submitted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_items


def _lock_request_and_balance(db: Session, leave_request_id: int):
    leave_request = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.leave_request_id == leave_request_id)
        .with_for_update()
        .first()
    )
    if leave_request is None:
        raise not_found("Leave request")

    balance = None
    if leave_request.leave_type.is_balance_tracked if leave_request.leave_type else True:
        leave_year = leave_request.start_date.year
        balance = (
            db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == leave_request.employee_id,
                LeaveBalance.leave_type_id == leave_request.leave_type_id,
                LeaveBalance.leave_year == leave_year,
            )
            .with_for_update()
            .first()
        )
    return leave_request, balance


def approve_leave_request(db: Session, *, leave_request_id: int, reviewer_user_id: int, comment: str | None):
    leave_request, balance = _lock_request_and_balance(db, leave_request_id)

    if leave_request.status != "PENDING":
        raise conflict(
            "This request was already reviewed and is no longer pending.",
            code="ALREADY_REVIEWED",
        )

    leave_type = leave_request.leave_type
    if leave_type and leave_type.is_balance_tracked:
        if balance is None or (balance.allocated_days - balance.used_days) < leave_request.number_of_days:
            raise bad_request(
                "Employee does not have sufficient leave balance for this request.",
                code="INSUFFICIENT_BALANCE",
            )
        balance.used_days = balance.used_days + leave_request.number_of_days

    previous_status = leave_request.status
    leave_request.status = "APPROVED"
    leave_request.reviewed_by = reviewer_user_id
    leave_request.reviewed_at = datetime.now(timezone.utc)
    leave_request.review_comment = comment
    db.flush()

    db.add(LeaveRequestReview(
        leave_request_id=leave_request.leave_request_id,
        reviewer_user_id=reviewer_user_id,
        previous_status=previous_status,
        new_status="APPROVED",
        comment=comment,
        reviewed_at=datetime.now(timezone.utc),
    ))

    write_audit_log(
        db, actor_user_id=reviewer_user_id, action="LEAVE_APPROVED",
        target_entity="leave_requests", target_id=leave_request.leave_request_id,
        old_values={"status": previous_status}, new_values={"status": "APPROVED", "comment": comment},
    )

    notify(
        db,
        recipient_user_id=leave_request.employee.user_id,
        type="LEAVE_APPROVED",
        title="Leave request approved",
        message=f"Your leave request ({leave_request.start_date} to {leave_request.end_date}) was approved.",
    )

    db.commit()
    db.refresh(leave_request)
    return leave_request


def reject_leave_request(db: Session, *, leave_request_id: int, reviewer_user_id: int, comment: str | None):
    leave_request, _ = _lock_request_and_balance(db, leave_request_id)

    if leave_request.status != "PENDING":
        raise conflict(
            "This request was already reviewed and is no longer pending.",
            code="ALREADY_REVIEWED",
        )

    previous_status = leave_request.status
    leave_request.status = "REJECTED"
    leave_request.reviewed_by = reviewer_user_id
    leave_request.reviewed_at = datetime.now(timezone.utc)
    leave_request.review_comment = comment
    db.flush()

    db.add(LeaveRequestReview(
        leave_request_id=leave_request.leave_request_id,
        reviewer_user_id=reviewer_user_id,
        previous_status=previous_status,
        new_status="REJECTED",
        comment=comment,
        reviewed_at=datetime.now(timezone.utc),
    ))

    write_audit_log(
        db, actor_user_id=reviewer_user_id, action="LEAVE_REJECTED",
        target_entity="leave_requests", target_id=leave_request.leave_request_id,
        old_values={"status": previous_status}, new_values={"status": "REJECTED", "comment": comment},
    )

    notify(
        db,
        recipient_user_id=leave_request.employee.user_id,
        type="LEAVE_REJECTED",
        title="Leave request rejected",
        message=f"Your leave request ({leave_request.start_date} to {leave_request.end_date}) was rejected.",
    )

    db.commit()
    db.refresh(leave_request)
    return leave_request
