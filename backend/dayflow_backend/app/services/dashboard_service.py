from datetime import date

from sqlalchemy import func

from sqlalchemy.orm import Session, joinedload

from app.models.hr import Employee
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest
from app.models.audit import AuditLog
from app.models.auth import User


def get_admin_dashboard(db: Session):
    today = date.today()

    total_employees = db.query(func.count(Employee.employee_id)).scalar() or 0
    active_employees = (
        db.query(func.count(Employee.employee_id))
        .filter(Employee.employment_status == "ACTIVE")
        .scalar()
        or 0
    )

    present_today = (
        db.query(func.count(Attendance.attendance_id))
        .filter(Attendance.attendance_date == today, Attendance.status == "PRESENT")
        .scalar()
        or 0
    )
    absent_today = (
        db.query(func.count(Attendance.attendance_id))
        .filter(Attendance.attendance_date == today, Attendance.status == "ABSENT")
        .scalar()
        or 0
    )
    on_leave_today = (
        db.query(func.count(Attendance.attendance_id))
        .filter(Attendance.attendance_date == today, Attendance.status == "LEAVE")
        .scalar()
        or 0
    )

    pending_leave_requests = (
        db.query(func.count(LeaveRequest.leave_request_id))
        .filter(LeaveRequest.status == "PENDING")
        .scalar()
        or 0
    )

    recent_activity_rows = (
        db.query(AuditLog, User.email)
        .outerjoin(User, AuditLog.actor_user_id == User.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    recent_activity = [
        {
            "action": log.action,
            "target_entity": log.target_entity,
            "target_id": log.target_id,
            "actor_name": actor_email,
            "created_at": log.created_at.isoformat(),
        }
        for log, actor_email in recent_activity_rows
    ]

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "present_today": present_today,
        "absent_today": absent_today,
        "on_leave_today": on_leave_today,
        "pending_leave_requests": pending_leave_requests,
        "recent_activity": recent_activity,
    }
