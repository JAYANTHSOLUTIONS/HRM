"""
Employee self-service router — /me endpoints.

All routes require a valid JWT and will operate only on the
authenticated employee's own data. ADMIN/HR users who also
have an employee profile can use these endpoints too.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import User
from app.schemas.me import (
    SelfProfileOut, SelfProfileUpdate,
    CheckInResponse, CheckOutResponse, WeeklySummary,
    LeaveBalanceOut, LeaveApplyRequest, MyLeaveRequestOut,
    MySalaryOut, EmployeeDashboardOut,
)
from app.services import me_service
from app.exceptions import forbidden

router = APIRouter(prefix="/me", tags=["Employee Self-Service"])


def _require_employee_profile(user: User) -> User:
    """Raise 403 if the authenticated user has no linked employee profile."""
    if user.employee is None:
        raise forbidden("Your account does not have a linked employee profile.")
    return user


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("", response_model=SelfProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SelfProfileOut:
    """Return the authenticated employee's own profile."""
    _require_employee_profile(user)
    emp = me_service.get_my_employee(db, user)
    return SelfProfileOut(**me_service.build_profile_out(emp))


@router.patch("", response_model=SelfProfileOut)
def update_my_profile(
    payload: SelfProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SelfProfileOut:
    """Update own limited profile fields: phone, address, gender, date_of_birth."""
    _require_employee_profile(user)
    emp = me_service.get_my_employee(db, user)
    result = me_service.update_my_profile(db, emp, payload)
    return SelfProfileOut(**result)


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

@router.post("/attendance/check-in", response_model=CheckInResponse, status_code=201)
def check_in(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheckInResponse:
    """Clock in for today. Creates an attendance record if one doesn't exist."""
    _require_employee_profile(user)
    record = me_service.check_in(db, user.employee.employee_id)
    return CheckInResponse(
        attendance_id=record.attendance_id,
        attendance_date=record.attendance_date,
        check_in_at=record.check_in_at,
        status=record.status,
        message="Checked in successfully.",
    )


@router.post("/attendance/check-out", response_model=CheckOutResponse)
def check_out(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheckOutResponse:
    """Clock out for today. Computes and stores work hours."""
    _require_employee_profile(user)
    record = me_service.check_out(db, user.employee.employee_id)
    return CheckOutResponse(
        attendance_id=record.attendance_id,
        attendance_date=record.attendance_date,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        work_hours=record.work_hours,
        overtime_hours=record.overtime_hours,
        status=record.status,
        message=f"Checked out. Work hours today: {record.work_hours}h.",
    )


@router.get("/attendance", response_model=WeeklySummary)
def get_my_attendance(
    week_start: date | None = Query(
        default=None,
        description="ISO date (YYYY-MM-DD). Defaults to current Monday.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklySummary:
    """Weekly attendance view. Includes daily records and totals."""
    _require_employee_profile(user)
    result = me_service.get_my_attendance(db, user.employee.employee_id, week_start)
    return WeeklySummary(**result)


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------

@router.get("/leave/balances", response_model=list[LeaveBalanceOut])
def get_my_leave_balances(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LeaveBalanceOut]:
    """Return current-year leave balances (Paid / Sick / Unpaid etc.)."""
    _require_employee_profile(user)
    balances = me_service.get_my_leave_balances(db, user.employee.employee_id)
    return [LeaveBalanceOut(**b) for b in balances]


@router.get("/leave/requests", response_model=list[MyLeaveRequestOut])
def get_my_leave_requests(
    status: str | None = Query(
        default=None,
        pattern="^(PENDING|APPROVED|REJECTED|CANCELLED)$",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MyLeaveRequestOut]:
    """Return own leave request history, optionally filtered by status."""
    _require_employee_profile(user)
    requests = me_service.get_my_leave_requests(db, user.employee.employee_id, status)
    return [MyLeaveRequestOut(**r) for r in requests]


@router.post("/leave/requests", response_model=MyLeaveRequestOut, status_code=201)
def apply_for_leave(
    payload: LeaveApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MyLeaveRequestOut:
    """Submit a new leave request (Paid / Sick / Unpaid)."""
    _require_employee_profile(user)
    result = me_service.apply_leave(db, user.employee.employee_id, payload, user.user_id)
    return MyLeaveRequestOut(**result)


@router.delete("/leave/requests/{leave_request_id}", response_model=MyLeaveRequestOut)
def cancel_my_leave(
    leave_request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MyLeaveRequestOut:
    """Cancel a pending leave request. Only the owner can cancel."""
    _require_employee_profile(user)
    result = me_service.cancel_leave(db, user.employee.employee_id, leave_request_id, user.user_id)
    return MyLeaveRequestOut(**result)


# ---------------------------------------------------------------------------
# Salary (read-only for employee)
# ---------------------------------------------------------------------------

@router.get("/salary", response_model=MySalaryOut)
def get_my_salary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MySalaryOut:
    """Return the employee's current salary structure (read-only)."""
    _require_employee_profile(user)
    result = me_service.get_my_salary(db, user.employee.employee_id)
    return MySalaryOut(**result)


# ---------------------------------------------------------------------------
# Employee Dashboard (registered under /dashboard/employee in main.py)
# ---------------------------------------------------------------------------

employee_dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@employee_dashboard_router.get("/employee", response_model=EmployeeDashboardOut)
def employee_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EmployeeDashboardOut:
    """Summary card data for the employee home dashboard."""
    _require_employee_profile(user)
    result = me_service.get_employee_dashboard(db, user)
    return EmployeeDashboardOut(**result)
