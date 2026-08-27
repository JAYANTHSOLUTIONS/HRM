from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import User
from app.models.password_reset_token import PasswordResetToken
from app.services.email import send_password_reset_otp


def generate_secure_otp(length: int = 6) -> str:
    """Generate cryptographically secure N-digit OTP using secrets module."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_token(value: str) -> str:
    """SHA-256 hash for storing OTP and reset tokens securely in database."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_otp(db: Session, email: str) -> None:
    """
    Generate 6-digit OTP, hash before DB storage, set 5-min expiration,
    and send email. Includes enumeration protection.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Enumeration protection: return generic success without revealing email non-existence
        return

    # Invalidate previous unused OTP tokens for this user
    now = datetime.now(timezone.utc)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.user_id,
        PasswordResetToken.used_at.is_(None)
    ).update({"used_at": now}, synchronize_session=False)

    otp = generate_secure_otp(6)
    otp_hashed = hash_token(otp)
    expires = now + timedelta(minutes=5)

    reset_record = PasswordResetToken(
        user_id=user.user_id,
        token_hash=otp_hashed,
        created_at=now,
        expires_at=expires,
        used_at=None
    )
    db.add(reset_record)
    db.commit()

    # Send OTP email via SMTP
    send_password_reset_otp(email, otp)


def verify_otp(db: Session, email: str, otp: str) -> str:
    """
    Verify 6-digit OTP hash, check 5-minute expiration & 5 attempts max.
    Returns a short-lived (10 min) reset token upon successful verification.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )

    now = datetime.now(timezone.utc)
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.user_id,
        PasswordResetToken.used_at.is_(None)
    ).order_by(PasswordResetToken.created_at.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )

    # Check 5-minute expiration
    record_exp = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if now > record_exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new OTP."
        )

    if record.attempts >= 5:
        record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invalid OTP attempts. Please request a new OTP."
        )

    if not secrets.compare_digest(record.token_hash, hash_token(otp)):
        record.attempts += 1
        if record.attempts >= 5:
            record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )

    # Invalidate the verified OTP
    record.used_at = now

    # Generate 10-minute short-lived reset token
    reset_token = secrets.token_urlsafe(32)
    reset_token_hash = hash_token(reset_token)
    reset_token_expires = now + timedelta(minutes=10)

    token_record = PasswordResetToken(
        user_id=user.user_id,
        token_hash=reset_token_hash,
        created_at=now,
        expires_at=reset_token_expires,
        used_at=None
    )
    db.add(token_record)
    db.commit()

    return reset_token


def reset_password_with_token(db: Session, reset_token: str, new_password: str) -> None:
    """
    Validate reset token, check 10-min expiration, hash new password using Argon2,
    and update user record.
    """
    now = datetime.now(timezone.utc)
    token_hashed = hash_token(reset_token)

    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hashed,
        PasswordResetToken.used_at.is_(None)
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    record_exp = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if now > record_exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new password reset."
        )

    user = record.user
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Update password using Argon2
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    record.used_at = now

    db.commit()
