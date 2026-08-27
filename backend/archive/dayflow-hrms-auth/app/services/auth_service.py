"""
Core authentication business logic. Endpoints in app/api/auth.py stay thin
and delegate everything here so the logic is unit-testable in isolation
from FastAPI/HTTP concerns.
"""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    AccountInactiveError,
    AccountLockedError,
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TokenExpiredOrInvalidError,
)
from app.core.jwt import create_access_token
from app.core.security import (
    generate_raw_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.email_verification_token import EmailVerificationToken
from app.models.otp import OTPPurpose
from app.models.refresh_token import RefreshToken
from app.models.role import Role, RoleName
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.services import otp_service
from app.services.audit_service import AuthEvent, record_auth_event
from app.services.email_service import (
    send_password_changed_notice,
    send_password_reset_otp_email,
    send_verification_email,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Employee code generation
# ---------------------------------------------------------------------------
# Part 2 owns the canonical employee-profile record, but the `users` table
# needs a unique employee_code at creation time for the login response
# contract. We generate a placeholder-safe, collision-checked code here;
# Part 2's employee service may reconcile/replace this format later, but
# must not change the `employee_code` column name or uniqueness contract.

def _generate_employee_code(db: Session, first_name: str, last_name: str, joining_date) -> str:
    initials = (re.sub(r"[^A-Za-z]", "", first_name)[:1] + re.sub(r"[^A-Za-z]", "", last_name)[:1]).upper()
    year = joining_date.year

    prefix = f"{initials}{year}"
    existing = db.execute(
        select(User.employee_code).where(User.employee_code.like(f"{prefix}%"))
    ).scalars().all()

    max_serial = 0
    for code in existing:
        suffix = code[len(prefix):]
        if suffix.isdigit():
            max_serial = max(max_serial, int(suffix))

    next_serial = str(max_serial + 1).zfill(4)
    return f"{prefix}{next_serial}"


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

def signup(db: Session, payload: SignupRequest) -> tuple[User, str]:
    """
    Creates a new EMPLOYEE-role user. Role is never taken from the client.
    Returns (user, raw_verification_token). Caller commits the transaction.
    """
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyExistsError()

    employee_role = db.execute(select(Role).where(Role.name == RoleName.EMPLOYEE.value)).scalar_one_or_none()
    if employee_role is None:
        # Roles must be seeded via migration; this indicates a deployment error.
        raise RuntimeError("EMPLOYEE role is not seeded in the roles table.")

    employee_code = _generate_employee_code(db, payload.first_name, payload.last_name, payload.joining_date)

    user = User(
        role_id=employee_role.role_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        employee_code=employee_code,
        is_active=True,
        is_email_verified=False,
        failed_login_attempts=0,
    )
    db.add(user)
    db.flush()  # populate user.user_id within the open transaction

    raw_token = generate_raw_token()
    verification_token = EmailVerificationToken(
        user_id=user.user_id,
        token_hash=hash_token(raw_token),
        expires_at=_utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS),
    )
    db.add(verification_token)
    db.flush()

    # NOTE: Part 2/3's employee-profile row (department_id, designation_id,
    # joining_date, first_name, last_name) should be created in the SAME
    # transaction here once that model exists. Left as an explicit
    # integration point per the "Part 1 does not own HR profile" contract.

    record_auth_event(AuthEvent.SIGNUP, user.user_id, {"email": user.email})
    return user, raw_token


def send_signup_verification_email(email: str, first_name: str, raw_token: str) -> None:
    send_verification_email(email, first_name, raw_token)


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def verify_email(db: Session, raw_token: str) -> User:
    token_hash = hash_token(raw_token)
    token_row = db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_row is None or token_row.used_at is not None or token_row.expires_at.replace(tzinfo=timezone.utc) < _utcnow():
        raise TokenExpiredOrInvalidError("This verification link has expired or was already used.")

    user = db.get(User, token_row.user_id)
    if user is None:
        raise TokenExpiredOrInvalidError()

    token_row.used_at = _utcnow()
    user.is_email_verified = True
    db.add_all([token_row, user])
    db.flush()

    record_auth_event(AuthEvent.EMAIL_VERIFIED, user.user_id)
    return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Implements the full login validation chain (steps 3-8 of the spec):
    find user, check active, check lock, verify password, check email
    verified, reset failed attempts on success.

    Never reveals via error message/timing whether the email exists —
    both "no such user" and "wrong password" raise InvalidCredentialsError.
    """
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None:
        # Still run the hasher to keep response timing similar to the
        # "user exists but wrong password" path, mitigating user enumeration
        # via timing side-channel.
        hash_password(password)
        raise InvalidCredentialsError()

    if not user.is_active:
        raise AccountInactiveError()

    if user.locked_until is not None and user.locked_until.replace(tzinfo=timezone.utc) > _utcnow():
        minutes_remaining = max(1, int((user.locked_until.replace(tzinfo=timezone.utc) - _utcnow()).total_seconds() // 60) + 1)
        raise AccountLockedError(minutes_remaining)

    if not verify_password(password, user.password_hash):
        _register_failed_login(db, user)
        record_auth_event(AuthEvent.LOGIN_FAILED, user.user_id, {"reason": "bad_password"})
        raise InvalidCredentialsError()

    if not user.is_email_verified:
        raise EmailNotVerifiedError()

    # Success: reset failed-attempt counters.
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.flush()

    record_auth_event(AuthEvent.LOGIN_SUCCESS, user.user_id)
    return user


def _register_failed_login(db: Session, user: User) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.FAILED_LOGIN_MAX_ATTEMPTS:
        user.locked_until = _utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
    db.add(user)
    db.flush()


def issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    """Creates a new access token + refresh token pair. Stores only the
    refresh token's hash. Returns (access_token, raw_refresh_token)."""
    access_token = create_access_token(user_id=user.user_id, role=user.role.name)

    raw_refresh = generate_raw_token()
    refresh_row = RefreshToken(
        user_id=user.user_id,
        token_hash=hash_token(raw_refresh),
        expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_row)
    db.flush()

    return access_token, raw_refresh


# ---------------------------------------------------------------------------
# Refresh token rotation
# ---------------------------------------------------------------------------

def rotate_refresh_token(db: Session, raw_refresh_token: str) -> tuple[str, str, User]:
    """
    Validates the presented refresh token and rotates it: the old token is
    revoked and replaced by a newly issued one. Returns
    (new_access_token, new_raw_refresh_token, user).
    """
    token_hash = hash_token(raw_refresh_token)
    token_row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_row is None:
        raise TokenExpiredOrInvalidError("Invalid refresh token.")

    if token_row.revoked_at is not None:
        # Reuse of a revoked/rotated token is a strong signal of token
        # theft — revoke the whole chain for this user as a precaution.
        _revoke_all_refresh_tokens(db, token_row.user_id)
        raise TokenExpiredOrInvalidError("This refresh token has already been used.")

    if token_row.expires_at.replace(tzinfo=timezone.utc) < _utcnow():
        raise TokenExpiredOrInvalidError("Refresh token has expired.")

    user = db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise TokenExpiredOrInvalidError("Account is not available.")

    # Rotate: revoke old, issue new.
    new_access_token, new_raw_refresh = issue_token_pair(db, user)
    token_row.revoked_at = _utcnow()
    token_row.replaced_by_hash = hash_token(new_raw_refresh)
    db.add(token_row)
    db.flush()

    return new_access_token, new_raw_refresh, user


def _revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    rows = db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    ).scalars().all()
    now = _utcnow()
    for row in rows:
        row.revoked_at = now
        db.add(row)
    db.flush()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def logout(db: Session, raw_refresh_token: str) -> None:
    token_hash = hash_token(raw_refresh_token)
    token_row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = _utcnow()
        db.add(token_row)
        db.flush()

    record_auth_event(AuthEvent.LOGOUT, token_row.user_id if token_row else None)


# ---------------------------------------------------------------------------
# Forgot / reset password (OTP-based)
# ---------------------------------------------------------------------------

def request_password_reset(db: Session, email: str) -> None:
    """
    Always succeeds from the caller's perspective (generic message returned
    by the API layer regardless of outcome). Internally: if the account
    exists, generate + email an OTP; if not, do nothing detectable.
    """
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        return

    try:
        raw_otp = otp_service.create_otp(db, user.user_id, OTPPurpose.PASSWORD_RESET)
    except Exception:
        # Rate-limited or other internal condition — do not leak this to
        # the caller; the endpoint always returns the generic message.
        return

    send_password_reset_otp_email(user.email, user.employee_code, raw_otp)


def reset_password(db: Session, email: str | None, otp_code: str, new_password: str, user_id: int | None = None) -> User:
    """
    Validates the OTP and resets the password. `user_id` may be supplied
    directly when known (e.g. resolved earlier in the request); otherwise
    `email` is required to look up the account.

    Revokes all existing refresh tokens for the user on success.
    """
    if user_id is None:
        if not email:
            raise TokenExpiredOrInvalidError("This code is invalid or has expired.")
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise TokenExpiredOrInvalidError("This code is invalid or has expired.")
        user_id = user.user_id
    else:
        user = db.get(User, user_id)
        if user is None:
            raise TokenExpiredOrInvalidError("This code is invalid or has expired.")

    otp_service.verify_otp(db, user_id, OTPPurpose.PASSWORD_RESET, otp_code)

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.flush()

    _revoke_all_refresh_tokens(db, user.user_id)
    send_password_changed_notice(user.email, user.employee_code)
    record_auth_event(AuthEvent.PASSWORD_RESET, user.user_id)
    return user


# ---------------------------------------------------------------------------
# Change password (authenticated)
# ---------------------------------------------------------------------------

def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError()

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.flush()

    _revoke_all_refresh_tokens(db, user.user_id)
    send_password_changed_notice(user.email, user.employee_code)
    record_auth_event(AuthEvent.PASSWORD_CHANGED, user.user_id)
