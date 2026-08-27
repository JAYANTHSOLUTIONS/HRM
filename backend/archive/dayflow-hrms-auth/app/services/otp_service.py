"""
OTP generation, storage, and verification for password-reset (and,
optionally, email-verification) flows.

Security properties enforced here:
- Raw OTP is never stored — only its SHA-256 hash.
- OTPs expire after settings.OTP_EXPIRE_MINUTES.
- A max number of verification attempts is enforced per OTP.
- OTPs are single-use (marked used_at on success).
- OTP *generation* is rate-limited per user to prevent spam/enumeration.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import OTPMaxAttemptsError, TokenExpiredOrInvalidError, OTPRateLimitedError
from app.core.security import generate_otp, hash_otp
from app.models.otp import OTP, OTPPurpose


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_otp(db: Session, user_id: int, purpose: OTPPurpose) -> str:
    """
    Creates a new OTP for the user, enforcing a resend cooldown against the
    most recently issued (still-active) OTP of the same purpose.
    Returns the RAW otp (to be emailed) — caller must not log/store it.
    """
    cooldown_cutoff = _utcnow() - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
    recent = db.execute(
        select(OTP)
        .where(OTP.user_id == user_id, OTP.purpose == purpose.value, OTP.used_at.is_(None))
        .order_by(OTP.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if recent and recent.created_at.replace(tzinfo=timezone.utc) > cooldown_cutoff:
        retry_after = int(
            (recent.created_at.replace(tzinfo=timezone.utc) + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS) - _utcnow()).total_seconds()
        )
        raise OTPRateLimitedError(max(retry_after, 1))

    raw_otp = generate_otp(settings.OTP_LENGTH)
    otp_row = OTP(
        user_id=user_id,
        purpose=purpose.value,
        otp_hash=hash_otp(raw_otp),
        attempts=0,
        expires_at=_utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp_row)
    db.flush()
    return raw_otp


def verify_otp(db: Session, user_id: int, purpose: OTPPurpose, raw_otp: str) -> OTP:
    """
    Validates the most recent unused, unexpired OTP for (user, purpose).
    Raises TokenExpiredOrInvalidError on mismatch/expiry and
    OTPMaxAttemptsError if the attempt cap has already been hit.
    On success, marks the OTP used (single-use) but does NOT commit —
    the caller's transaction boundary controls the commit.
    """
    otp_row = db.execute(
        select(OTP)
        .where(OTP.user_id == user_id, OTP.purpose == purpose.value, OTP.used_at.is_(None))
        .order_by(OTP.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if otp_row is None:
        raise TokenExpiredOrInvalidError("This code is invalid or has expired.")

    if otp_row.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OTPMaxAttemptsError()

    if otp_row.expires_at.replace(tzinfo=timezone.utc) < _utcnow():
        raise TokenExpiredOrInvalidError("This code has expired. Please request a new one.")

    if otp_row.otp_hash != hash_otp(raw_otp):
        otp_row.attempts += 1
        db.add(otp_row)
        db.flush()
        raise TokenExpiredOrInvalidError("This code is invalid or has expired.")

    otp_row.used_at = _utcnow()
    db.add(otp_row)
    db.flush()
    return otp_row
