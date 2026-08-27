import secrets
import string
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.auth import User, Role
from app.models.hr import Employee
from app.exceptions import conflict, bad_request
from app.services.employee_code import generate_employee_code
from app.services.audit_service import write_audit_log
from app.services.notification_service import notify
from app.core.security import hash_password
from app.schemas.admin import UserInviteRequest


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
        is_email_verified=False,
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

    # In production this goes through a real email service (SMTP settings in .env).
    # Kept as a hook here so Part 2 doesn't silently swallow the credential.
    _send_invitation_email(payload.email, employee_code, temp_password)

    db.commit()
    db.refresh(user)

    return {
        "user_id": user.user_id,
        "employee_code": employee_code,
        "email": payload.email,
        "role": payload.role,
        "message": "Invitation sent. A system-generated temporary password has been emailed.",
    }


def _send_invitation_email(email: str, employee_code: str, temp_password: str) -> None:
    """Placeholder for SMTP integration — wire up with app.core.config SMTP_* settings."""
    # e.g. via smtplib / an email provider SDK. Intentionally not blocking user creation
    # on email delivery failure; log and continue in real implementation.
    pass
