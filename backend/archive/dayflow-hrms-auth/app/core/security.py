"""
Password hashing, secure token/OTP generation, and hashing helpers.

Design notes:
- Passwords are hashed with Argon2 (via passlib) — memory-hard, resistant
  to GPU cracking, and the current OWASP-recommended default.
- Raw opaque tokens (email verification, password reset, refresh tokens)
  are generated with `secrets.token_urlsafe` and only their SHA-256 hash
  is ever persisted. The raw value is sent to the user exactly once
  (via email or in the login response for refresh tokens) and cannot be
  recovered from the database afterward.
- OTPs are 6-digit codes generated with `secrets.randbelow` (CSPRNG), and
  only their SHA-256 hash is stored.
"""
import hashlib
import re
import secrets
from dataclasses import dataclass

from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        # Any malformed-hash edge case must fail closed, not raise 500.
        return False


@dataclass
class PasswordPolicyResult:
    is_valid: bool
    errors: list[str]


def validate_password_strength(password: str) -> PasswordPolicyResult:
    """
    Enforces: minimum length (configurable) + recommends upper/lower/
    digit/special. Per spec, length is the hard minimum; the character
    class rules are treated as required for a "strong" password since the
    example passwords in the spec ("StrongPass!234") satisfy all of them.
    """
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if not re.search(r"[^\w\s]", password):
        errors.append("Password must contain at least one special character.")

    return PasswordPolicyResult(is_valid=len(errors) == 0, errors=errors)


# ---------------------------------------------------------------------------
# Opaque token generation/hashing (email verification, password reset,
# refresh tokens)
# ---------------------------------------------------------------------------

def generate_raw_token(n_bytes: int = 32) -> str:
    """URL-safe, cryptographically secure random token."""
    return secrets.token_urlsafe(n_bytes)


def hash_token(raw_token: str) -> str:
    """SHA-256 hash of a raw token, hex-encoded, for storage/lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# OTP generation/hashing
# ---------------------------------------------------------------------------

def generate_otp(length: int | None = None) -> str:
    """Cryptographically secure numeric OTP, zero-padded to `length` digits."""
    length = length or settings.OTP_LENGTH
    upper_bound = 10 ** length
    value = secrets.randbelow(upper_bound)
    return str(value).zfill(length)


def hash_otp(raw_otp: str) -> str:
    return hashlib.sha256(raw_otp.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
