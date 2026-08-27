from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.assumed_existing.auth import User
from app.assumed_existing.org_models import Employee, SalaryStructure
from app.models.leave import LeaveRequest, LeaveRequestStatus
from app.services import attendance_service, employee_service, leave_service


def get_dashboard(db: Session, employee: Employee, user: User, request_base_url: str) -> dict:
    today = attendance_service.get_today(db, employee)

    today_leave = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee.employee_id,
            LeaveRequest.status == LeaveRequestStatus.APPROVED,
            LeaveRequest.start_date <= datetime.now(timezone.utc).date(),
            LeaveRequest.end_date >= datetime.now(timezone.utc).date(),
        )
        .first()
    )

    balances = leave_service.get_balances(db, employee)["items"]

    recent_requests = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == employee.employee_id)
        .order_by(LeaveRequest.submitted_at.desc())
        .limit(5)
        .all()
    )

    structure = (
        db.query(SalaryStructure)
        .filter(SalaryStructure.employee_id == employee.employee_id)
        .order_by(SalaryStructure.effective_from.desc())
        .first()
    )

    return {
        "profile": {
            "full_name": f"{employee.first_name} {employee.last_name}",
            "profile_picture_url": employee_service.get_profile_picture_url(employee, request_base_url),
        },
        "today_attendance": {
            "status": today.status if today else None,
            "check_in_at": today.check_in_at if today else None,
            "check_out_at": today.check_out_at if today else None,
        },
        "current_leave": (
            {
                "leave_request_id": today_leave.leave_request_id,
                "leave_type": today_leave.leave_type.name,
                "start_date": today_leave.start_date.isoformat(),
                "end_date": today_leave.end_date.isoformat(),
                "status": today_leave.status,
            }
            if today_leave
            else None
        ),
        "leave_balance_summary": [
            {"leave_type": b["leave_type"], "remaining_days": b["remaining_days"]} for b in balances
        ],
        "recent_leave_requests": [
            {
                "leave_request_id": r.leave_request_id,
                "leave_type": r.leave_type.name,
                "status": r.status,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
            }
            for r in recent_requests
        ],
        "salary_summary": {"monthly_wage": float(structure.monthly_wage) if structure else None},
        "recent_activity": [],  # wire up once an activity/audit log table exists
    }
