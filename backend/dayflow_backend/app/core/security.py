"""
PART 1 COMPATIBILITY SHIM.

Part 1 owns signup / login / refresh / password-reset / email-verification /
CAPTCHA / OTP. This module intentionally does NOT reimplement any of that.

It only provides the two primitives Part 2 needs to *consume* Part 1's
auth system:

  1. Password hashing helpers (only used by the admin-invite flow to set a
     temporary password for a newly provisioned HR/Admin user — the actual
     login still happens through Part 1's /auth/login).
  2. JWT decoding using the SAME secret/algorithm Part 1 signs tokens with,
     so `get_current_user` can verify tokens issued by Part 1.

If Part 1's real implementation differs (different claim names, different
token library), update `decode_access_token` accordingly — nothing else
in Part 2 should need to change.
"""
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return pwd_context.verify(raw_password, password_hash)


class PasswordPolicyResult:
    def __init__(self, is_valid: bool, errors: list[str]):
        self.is_valid = is_valid
        self.errors = errors


def validate_password_strength(password: str) -> PasswordPolicyResult:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if not re.search(r"[^\w\s]", password):
        errors.append("Password must contain at least one special character.")
    return PasswordPolicyResult(not errors, errors)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on any invalid/expired/tampered token."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None,
                         expires_minutes: int | None = None) -> str:
    """
    Only used by local dev/testing scripts to mint a token compatible with
    Part 1's contract, in the absence of a running Part 1 service. Not used
    by any Part 2 request-handling code path.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


__all__ = [
    "JWTError", "hash_password", "verify_password", "validate_password_strength",
    "decode_access_token", "create_access_token",
]
