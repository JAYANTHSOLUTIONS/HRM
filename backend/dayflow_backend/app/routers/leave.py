import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_or_hr, require_any_role
from app.models.auth import User
from app.schemas.leave import LeaveTypeOut, LeaveRequestOut, LeaveReviewRequest
from app.schemas.common import Page
from app.services.leave_service import (
    list_leave_types, list_leave_requests, approve_leave_request, reject_leave_request,
)

router = APIRouter(tags=["Leave (Admin/HR)"])


def _to_out(lr) -> LeaveRequestOut:
    return LeaveRequestOut(
        leave_request_id=lr.leave_request_id,
        employee_id=lr.employee_id,
        employee_name=lr.employee.full_name if lr.employee else None,
        leave_type=lr.leave_type,
        start_date=lr.start_date,
        end_date=lr.end_date,
        number_of_days=lr.number_of_days,
        remarks=lr.remarks,
        attachment_path=lr.attachment_path,
        status=lr.status,
        submitted_at=lr.submitted_at,
        reviewed_by=lr.reviewed_by,
        reviewed_at=lr.reviewed_at,
        review_comment=lr.review_comment,
    )


@router.get("/leave-types", response_model=list[LeaveTypeOut])
def get_leave_types(db: Session = Depends(get_db), _=Depends(require_any_role)):
    return list_leave_types(db)


@router.get("/leave/requests", response_model=Page[LeaveRequestOut])
def get_leave_requests(
    status: str | None = Query(default=None, pattern="^(PENDING|APPROVED|REJECTED|CANCELLED)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_hr),
):
    items, total_items = list_leave_requests(db, page=page, page_size=page_size, status=status)
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    return {"page": page, "page_size": page_size, "total_items": total_items,
            "total_pages": total_pages, "items": [_to_out(i) for i in items]}


@router.post("/leave/requests/{leave_request_id}/approve", response_model=LeaveRequestOut)
def approve(
    leave_request_id: int, payload: LeaveReviewRequest,
    db: Session = Depends(get_db), user: User = Depends(require_admin_or_hr),
):
    lr = approve_leave_request(
        db, leave_request_id=leave_request_id, reviewer_user_id=user.user_id, comment=payload.comment
    )
    return _to_out(lr)


@router.post("/leave/requests/{leave_request_id}/reject", response_model=LeaveRequestOut)
def reject(
    leave_request_id: int, payload: LeaveReviewRequest,
    db: Session = Depends(get_db), user: User = Depends(require_admin_or_hr),
):
    lr = reject_leave_request(
        db, leave_request_id=leave_request_id, reviewer_user_id=user.user_id, comment=payload.comment
    )
    return _to_out(lr)
