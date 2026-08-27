"""
Service logic for the employee self-service (/me) endpoints.
All functions take the authenticated employee_id so they never
operate on data that doesn't belong to the caller.
"""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance
from app.models.hr import Employee
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType
from app.models.salary import SalaryStructure
from app.models.auth import User
from app.exceptions import bad_request, not_found, conflict
from app.services.audit_service import write_audit_log
from app.schemas.me import LeaveApplyRequest, SelfProfileUpdate


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

EMPLOYEE_SELF_FIELDS = {"phone", "address", "gender", "date_of_birth"}


def get_my_employee(db: Session, user: User) -> Employee:
    emp = (
        db.query(Employee)
        .options(
            joinedload(Employee.department),
            joinedload(Employee.designation),
            joinedload(Employee.manager),
            joinedload(Employee.user),
        )
        .filter(Employee.user_id == user.user_id)
        .first()
    )
    if emp is None:
        raise not_found("Employee profile linked to this account")
    return emp


def build_profile_out(emp: Employee, email: str | None = None) -> dict:
    return {
        "employee_id": emp.employee_id,
        "employee_code": emp.employee_code,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "full_name": emp.full_name,
        "email": email or (emp.user.email if emp.user else None),
        "phone": emp.phone,
        "address": emp.address,
        "date_of_birth": emp.date_of_birth,
        "gender": emp.gender,
        "profile_picture_url": emp.profile_picture_url,
        "department_name": emp.department.department_name if emp.department else None,
        "designation_title": emp.designation.title if emp.designation else None,
        "manager_name": emp.manager.full_name if emp.manager else None,
        "joining_date": emp.joining_date,
        "employment_status": emp.employment_status,
        "employment_type": emp.employment_type,
    }


def update_my_profile(db: Session, emp: Employee, payload: SelfProfileUpdate) -> dict:
    changes = {}
    data = payload.model_dump(exclude_unset=True)
    for field, new_val in data.items():
        if field not in EMPLOYEE_SELF_FIELDS or new_val is None:
            continue
        old_val = getattr(emp, field)
        if str(old_val) != str(new_val):
            changes[field] = (str(old_val) if old_val is not None else None, str(new_val))
        setattr(emp, field, new_val)

    if changes:
        write_audit_log(
            db, actor_user_id=emp.user_id, action="PROFILE_SELF_UPDATED",
            target_entity="employees", target_id=emp.employee_id,
            old_values={k: v[0] for k, v in changes.items()},
            new_values={k: v[1] for k, v in changes.items()},
        )
    db.commit()
    db.refresh(emp)
    return build_profile_out(emp)


# ---------------------------------------------------------------------------
# Attendance helpers
# ---------------------------------------------------------------------------

WORK_DAY_HOURS = Decimal("8.00")
OVERTIME_THRESHOLD = Decimal("8.00")


def _compute_work_hours(check_in: datetime | None, check_out: datetime | None) -> Decimal:
    if check_in is None or check_out is None:
        return Decimal("0.00")
    delta = Decimal(str((check_out - check_in).total_seconds())) / Decimal("3600")
    return delta.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def check_in(db: Session, employee_id: int) -> Attendance:
    today = date.today()
    now = datetime.now(timezone.utc)

    existing = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.attendance_date == today)
        .with_for_update()
        .first()
    )

    if existing is not None:
        if existing.check_in_at is not None:
            raise conflict("Already checked in today.", code="ALREADY_CHECKED_IN")
        existing.check_in_at = now
        existing.status = "PRESENT"
    else:
        existing = Attendance(
            employee_id=employee_id,
            attendance_date=today,
            check_in_at=now,
            check_out_at=None,
            work_hours=Decimal("0.00"),
            overtime_hours=Decimal("0.00"),
            status="PRESENT",
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def check_out(db: Session, employee_id: int) -> Attendance:
    today = date.today()
    now = datetime.now(timezone.utc)

    record = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.attendance_date == today)
        .with_for_update()
        .first()
    )

    if record is None or record.check_in_at is None:
        raise bad_request("You have not checked in today.", code="NOT_CHECKED_IN")
    if record.check_out_at is not None:
        raise conflict("Already checked out today.", code="ALREADY_CHECKED_OUT")
    if now <= record.check_in_at:
        raise bad_request("Check-out time must be after check-in time.")

    work_hours = _compute_work_hours(record.check_in_at, now)
    overtime = max(Decimal("0.00"), work_hours - OVERTIME_THRESHOLD)

    record.check_out_at = now
    record.work_hours = work_hours
    record.overtime_hours = overtime.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    record.status = "HALF_DAY" if work_hours < Decimal("4.00") else "PRESENT"

    db.commit()
    db.refresh(record)
    return record


def get_my_attendance(db: Session, employee_id: int, week_start: date | None = None) -> dict:
    """Return weekly attendance records. Defaults to current week (Mon–Sun)."""
    today = date.today()
    if week_start is None:
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    records = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date >= week_start,
            Attendance.attendance_date <= week_end,
        )
        .order_by(Attendance.attendance_date)
        .all()
    )

    days_present = sum(1 for r in records if r.status in ("PRESENT", "HALF_DAY"))
    leaves_count = sum(1 for r in records if r.status == "LEAVE")
    absences = sum(1 for r in records if r.status == "ABSENT")
    total_work = sum((r.work_hours for r in records), Decimal("0.00"))
    total_ot = sum((r.overtime_hours for r in records), Decimal("0.00"))

    return {
        "week_start": week_start,
        "week_end": week_end,
        "days_present": days_present,
        "leaves_count": leaves_count,
        "absences": absences,
        "total_work_hours": total_work,
        "total_overtime_hours": total_ot,
        "records": records,
    }


# ---------------------------------------------------------------------------
# Leave helpers
# ---------------------------------------------------------------------------

def get_my_leave_balances(db: Session, employee_id: int) -> list:
    year = date.today().year
    balances = (
        db.query(LeaveBalance)
        .options(joinedload(LeaveBalance.leave_type))
        .filter(LeaveBalance.employee_id == employee_id, LeaveBalance.leave_year == year)
        .all()
    )
    result = []
    for b in balances:
        result.append({
            "leave_type_id": b.leave_type_id,
            "leave_type_name": b.leave_type.name if b.leave_type else str(b.leave_type_id),
            "leave_year": b.leave_year,
            "allocated_days": b.allocated_days,
            "used_days": b.used_days,
            "remaining_days": b.remaining_days,
            "requires_attachment": b.leave_type.requires_attachment if b.leave_type else False,
        })
    return result


def get_my_leave_requests(db: Session, employee_id: int, status: str | None = None) -> list:
    query = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.leave_type))
        .filter(LeaveRequest.employee_id == employee_id)
    )
    if status:
        query = query.filter(LeaveRequest.status == status.upper())
    requests = query.order_by(LeaveRequest.submitted_at.desc()).all()

    return [
        {
            "leave_request_id": r.leave_request_id,
            "leave_type_name": r.leave_type.name if r.leave_type else "",
            "start_date": r.start_date,
            "end_date": r.end_date,
            "number_of_days": r.number_of_days,
            "remarks": r.remarks,
            "status": r.status,
            "submitted_at": r.submitted_at,
            "reviewed_at": r.reviewed_at,
            "review_comment": r.review_comment,
        }
        for r in requests
    ]


def apply_leave(db: Session, employee_id: int, payload: LeaveApplyRequest, user_id: int) -> dict:
    leave_type = db.query(LeaveType).filter(
        LeaveType.leave_type_id == payload.leave_type_id,
        LeaveType.is_active.is_(True),
    ).first()
    if leave_type is None:
        raise not_found("Leave type")

    # Calculate business days (naive: all calendar days including weekends for now)
    delta = (payload.end_date - payload.start_date).days + 1
    number_of_days = Decimal(str(delta))

    # Check balance if tracked
    if leave_type.is_balance_tracked:
        year = payload.start_date.year
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == payload.leave_type_id,
            LeaveBalance.leave_year == year,
        ).with_for_update().first()
        if balance is None or balance.remaining_days < number_of_days:
            raise bad_request(
                "Insufficient leave balance for this request.",
                code="INSUFFICIENT_BALANCE",
            )

    lr = LeaveRequest(
        employee_id=employee_id,
        leave_type_id=payload.leave_type_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        number_of_days=number_of_days,
        remarks=payload.remarks,
        status="PENDING",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(lr)
    db.flush()

    write_audit_log(
        db, actor_user_id=user_id, action="LEAVE_APPLIED",
        target_entity="leave_requests", target_id=lr.leave_request_id,
        new_values={
            "leave_type_id": payload.leave_type_id,
            "start_date": str(payload.start_date),
            "end_date": str(payload.end_date),
            "number_of_days": str(number_of_days),
        },
    )
    db.commit()
    db.refresh(lr)

    return {
        "leave_request_id": lr.leave_request_id,
        "leave_type_name": leave_type.name,
        "start_date": lr.start_date,
        "end_date": lr.end_date,
        "number_of_days": lr.number_of_days,
        "remarks": lr.remarks,
        "status": lr.status,
        "submitted_at": lr.submitted_at,
        "reviewed_at": None,
        "review_comment": None,
    }


def cancel_leave(db: Session, employee_id: int, leave_request_id: int, user_id: int) -> dict:
    lr = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.leave_type))
        .filter(
            LeaveRequest.leave_request_id == leave_request_id,
            LeaveRequest.employee_id == employee_id,
        )
        .with_for_update()
        .first()
    )
    if lr is None:
        raise not_found("Leave request")
    if lr.status != "PENDING":
        raise conflict(
            f"Cannot cancel a {lr.status.lower()} request — only PENDING requests can be cancelled.",
            code="NOT_CANCELLABLE",
        )

    lr.status = "CANCELLED"
    write_audit_log(
        db, actor_user_id=user_id, action="LEAVE_CANCELLED",
        target_entity="leave_requests", target_id=lr.leave_request_id,
        old_values={"status": "PENDING"}, new_values={"status": "CANCELLED"},
    )
    db.commit()
    db.refresh(lr)

    return {
        "leave_request_id": lr.leave_request_id,
        "leave_type_name": lr.leave_type.name if lr.leave_type else "",
        "start_date": lr.start_date,
        "end_date": lr.end_date,
        "number_of_days": lr.number_of_days,
        "remarks": lr.remarks,
        "status": lr.status,
        "submitted_at": lr.submitted_at,
        "reviewed_at": lr.reviewed_at,
        "review_comment": lr.review_comment,
    }


# ---------------------------------------------------------------------------
# Salary
# ---------------------------------------------------------------------------

def get_my_salary(db: Session, employee_id: int) -> dict:
    from app.models.salary import SalaryStructure
    structure = (
        db.query(SalaryStructure)
        .options(joinedload(SalaryStructure.components))
        .filter(
            SalaryStructure.employee_id == employee_id,
            SalaryStructure.is_current.is_(True),
        )
        .first()
    )
    if structure is None:
        raise not_found("Salary structure for your account")

    return {
        "salary_structure_id": structure.salary_structure_id,
        "monthly_wage": structure.monthly_wage,
        "annual_wage": structure.annual_wage,
        "wage_type": structure.wage_type,
        "effective_from": structure.effective_from,
        "effective_to": structure.effective_to,
        "components": [
            {
                "name": c.component_name,
                "type": c.component_type,
                "calculation_type": c.calculation_type,
                "percentage": c.percentage_value,
                "fixed_amount": c.fixed_amount,
                "computed_amount": c.computed_amount,
            }
            for c in structure.components
        ],
    }


# ---------------------------------------------------------------------------
# Employee Dashboard
# ---------------------------------------------------------------------------

def get_employee_dashboard(db: Session, user: User) -> dict:
    emp = get_my_employee(db, user)
    today = date.today()

    # Today's attendance
    today_att = db.query(Attendance).filter(
        Attendance.employee_id == emp.employee_id,
        Attendance.attendance_date == today,
    ).first()

    # This week attendance (Mon–today)
    week_start = today - timedelta(days=today.weekday())
    week_records = db.query(Attendance).filter(
        Attendance.employee_id == emp.employee_id,
        Attendance.attendance_date >= week_start,
        Attendance.attendance_date <= today,
    ).all()
    week_present = sum(1 for r in week_records if r.status in ("PRESENT", "HALF_DAY"))

    # Leave counts
    pending_leaves = db.query(func.count(LeaveRequest.leave_request_id)).filter(
        LeaveRequest.employee_id == emp.employee_id,
        LeaveRequest.status == "PENDING",
    ).scalar() or 0

    approved_leaves = db.query(func.count(LeaveRequest.leave_request_id)).filter(
        LeaveRequest.employee_id == emp.employee_id,
        LeaveRequest.status == "APPROVED",
        LeaveRequest.end_date >= today,
    ).scalar() or 0

    # Leave balances
    balances = get_my_leave_balances(db, emp.employee_id)

    return {
        "employee_id": emp.employee_id,
        "full_name": emp.full_name,
        "department": emp.department.department_name if emp.department else None,
        "designation": emp.designation.title if emp.designation else None,
        "profile_picture_url": emp.profile_picture_url,
        "today_status": today_att.status if today_att else None,
        "check_in_at": today_att.check_in_at if today_att else None,
        "check_out_at": today_att.check_out_at if today_att else None,
        "work_hours_today": today_att.work_hours if today_att else Decimal("0.00"),
        "this_week_present_days": week_present,
        "pending_leave_requests": pending_leaves,
        "approved_leave_requests": approved_leaves,
        "leave_balances": balances,
    }
