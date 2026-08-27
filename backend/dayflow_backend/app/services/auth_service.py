import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.exceptions import conflict, bad_request
from app.models.auth import Role, User
from app.models.email_verification_token import EmailVerificationToken
from app.models.hr import Employee
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.services.employee_code import generate_employee_code
from app.schemas.auth import SignupRequest

settings = get_settings()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def signup(db: Session, payload: SignupRequest) -> tuple[User, str]:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise conflict("An account with this email already exists.", code="EMAIL_ALREADY_EXISTS")

    role = db.query(Role).filter(Role.role_name == "EMPLOYEE").first()
    if role is None:
        raise bad_request("EMPLOYEE role is not configured in the system.", code="ROLE_NOT_CONFIGURED")

    employee_code = generate_employee_code(
        db, payload.first_name, payload.last_name, payload.joining_date.year
    )
    user = User(
        employee_code=employee_code,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.role_id,
        is_email_verified=False,
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        Employee(
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
    )

    raw_token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=user.user_id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=getattr(settings, "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", 24)),
        )
    )
    db.flush()
    return user, raw_token


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise bad_request("Incorrect email or password.", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise bad_request("This account is inactive.", code="ACCOUNT_INACTIVE")
    if not user.is_email_verified:
        raise bad_request("Please verify your email before signing in.", code="EMAIL_NOT_VERIFIED")
    return user


def issue_session(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.user_id), {"role": user.role_name})
    raw_refresh = secrets.token_urlsafe(32)
    db.add(
        RefreshToken(
            user_id=user.user_id,
            token_hash=_hash_token(raw_refresh),
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    db.flush()
    return access_token, raw_refresh


def refresh_session(db: Session, raw_refresh_token: str) -> str:
    token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == _hash_token(raw_refresh_token),
        RefreshToken.revoked_at.is_(None),
    ).first()
    if token is None or token.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise bad_request("Invalid or expired refresh token.", code="INVALID_REFRESH_TOKEN")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise bad_request("This account is inactive.", code="ACCOUNT_INACTIVE")
    access_token, _ = issue_session(db, user)
    token.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return access_token


def verify_email(db: Session, raw_token: str) -> None:
    token = db.query(EmailVerificationToken).filter_by(token_hash=_hash_token(raw_token)).first()
    now = datetime.now(timezone.utc)
    if token is None or token.used_at is not None or token.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise bad_request("This verification link has expired or was already used.", code="TOKEN_EXPIRED_OR_INVALID")
    user = db.get(User, token.user_id)
    if user is None:
        raise bad_request("This verification link is invalid.", code="TOKEN_EXPIRED_OR_INVALID")
    token.used_at = now
    user.is_email_verified = True
    db.flush()


def request_password_reset(db: Session, email: str) -> None:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.user_id,
        token_hash=_hash_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(minutes=30),
    ))
    db.flush()


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token = db.query(PasswordResetToken).filter_by(token_hash=_hash_token(raw_token)).first()
    now = datetime.now(timezone.utc)
    if token is None or token.used_at is not None or token.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise bad_request("This reset token is invalid or expired.", code="TOKEN_EXPIRED_OR_INVALID")
    user = db.get(User, token.user_id)
    if user is None:
        raise bad_request("This reset token is invalid.", code="TOKEN_EXPIRED_OR_INVALID")
    user.password_hash = hash_password(new_password)
    token.used_at = now
    db.flush()
