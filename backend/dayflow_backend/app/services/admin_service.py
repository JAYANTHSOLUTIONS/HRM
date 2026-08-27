import secrets
import string
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.auth import User, Role
from app.models.hr import Employee, Department, Designation
from app.exceptions import conflict, bad_request
from app.services.employee_code import generate_employee_code
from app.services.audit_service import write_audit_log
from app.services.notification_service import notify
from app.services.email import send_invitation_email
from app.core.security import hash_password
from app.schemas.admin import UserInviteRequest

logger = logging.getLogger(__name__)


def _generate_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def invite_user(db: Session, *, payload: UserInviteRequest, invited_by_user_id: int) -> dict:
    if payload.role not in ("HR", "ADMIN"):
        raise bad_request("Only HR or ADMIN roles may be created through this endpoint.")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise conflict("An account with this email already exists.", code="EMAIL_ALREADY_EXISTS")

    role = db.query(Role).filter(Role.role_name == payload.role).first()
    if role is None:
        raise bad_request(f"Role '{payload.role}' is not configured in the system.")

    employee_code = generate_employee_code(db, payload.first_name, payload.last_name, payload.joining_date.year)
    temp_password = _generate_temp_password()

    user = User(
        employee_code=employee_code,
        email=payload.email,
        password_hash=hash_password(temp_password),
        role_id=role.role_id,
        is_email_verified=True,
        is_active=True,
    )
    db.add(user)
    db.flush()

    employee = Employee(
        user_id=user.user_id,
        employee_code=employee_code,
        first_name=payload.first_name,
        last_name=payload.last_name,
        department_id=payload.department_id,
        designation_id=payload.designation_id,
        joining_date=payload.joining_date,
        employment_status="ACTIVE",
        employment_type="FULL_TIME",
    )
    db.add(employee)
    db.flush()

    write_audit_log(
        db, actor_user_id=invited_by_user_id, action="USER_INVITED",
        target_entity="users", target_id=user.user_id,
        new_values={"email": payload.email, "role": payload.role, "employee_code": employee_code},
    )

    notify(
        db, recipient_user_id=user.user_id, type="USER_INVITED",
        title="Welcome to Dayflow",
        message="Your account has been created. Check your email for your temporary password.",
    )

    # Resolve department and designation names for the invitation email
    department_name = None
    if payload.department_id:
        dept = db.query(Department).filter(Department.department_id == payload.department_id).first()
        department_name = dept.department_name if dept else None

    designation_title = None
    if payload.designation_id:
        desig = db.query(Designation).filter(Designation.designation_id == payload.designation_id).first()
        designation_title = desig.title if desig else None

    # Send the invitation email via SMTP (Cloudflare / configured provider).
    # Email delivery failure is logged but does not block user creation.
    employee_name = f"{payload.first_name} {payload.last_name}".strip()
    try:
        send_invitation_email(
            email=payload.email,
            employee_name=employee_name,
            employee_code=employee_code,
            temp_password=temp_password,
            role=payload.role,
            department=department_name,
            designation=designation_title,
            joining_date=str(payload.joining_date),
        )
    except Exception as exc:
        logger.error(f"Invitation email to {payload.email} failed: {exc}")

    db.commit()
    db.refresh(user)

    return {
        "user_id": user.user_id,
        "employee_code": employee_code,
        "email": payload.email,
        "role": payload.role,
        "message": "Invitation sent. A system-generated temporary password has been emailed.",
    }

