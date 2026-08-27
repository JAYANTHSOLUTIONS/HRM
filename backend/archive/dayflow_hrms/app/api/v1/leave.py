from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.schemas.leave import (
    LeaveBalancesOut,
    LeaveCancelOut,
    LeaveRequestCreate,
    LeaveRequestListOut,
    LeaveRequestOut,
    LeaveTypeListOut,
)
from app.services import leave_service

leave_types_router = APIRouter(prefix="/api/v1/leave-types", tags=["leave"])
leave_router = APIRouter(prefix="/api/v1/leave", tags=["leave"])


@leave_types_router.get("", response_model=LeaveTypeListOut)
def get_leave_types(db: Session = Depends(get_db)):
    return {"items": leave_service.list_leave_types(db)}


@leave_router.get("/balances", response_model=LeaveBalancesOut)
def get_balances(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    return leave_service.get_balances(db, employee)


@leave_router.post("/requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def apply_leave(
    payload: LeaveRequestCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    request = leave_service.apply_leave(db, employee, payload)
    return {
        "leave_request_id": request.leave_request_id,
        "leave_type": request.leave_type.name,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "number_of_days": request.number_of_days,
        "status": request.status,
        "submitted_at": request.submitted_at,
    }


@leave_router.get("/requests/me", response_model=LeaveRequestListOut)
def get_my_leave_requests(
    status: Optional[str] = Query(default=None),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    requests = leave_service.list_my_requests(db, employee, status)
    items = [
        {
            "leave_request_id": r.leave_request_id,
            "leave_type": r.leave_type.name,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "number_of_days": r.number_of_days,
            "status": r.status,
            "submitted_at": r.submitted_at,
            "remarks": r.remarks,
        }
        for r in requests
    ]
    return {"items": items}


@leave_router.post("/requests/{leave_request_id}/cancel", response_model=LeaveCancelOut)
def cancel_leave(
    leave_request_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    request = leave_service.cancel_request(db, employee, leave_request_id)
    return {"leave_request_id": request.leave_request_id, "status": request.status}
