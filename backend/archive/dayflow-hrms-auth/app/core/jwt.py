"""
JWT access-token creation and verification.

The JWT is deliberately minimal: sub (user_id), role, jti, iat, exp.
Never embed password hashes, salary, or any other private HR data in the
token — Parts 2/3 must re-fetch anything sensitive from the database using
the user_id in `sub`.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


class TokenError(Exception):
    """Raised for any invalid/expired/malformed JWT."""


@dataclass
class AccessTokenPayload:
    sub: str
    role: str
    jti: str
    iat: int
    exp: int


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError("Invalid or expired token.") from exc

    try:
        return AccessTokenPayload(
            sub=payload["sub"],
            role=payload["role"],
            jti=payload["jti"],
            iat=payload["iat"],
            exp=payload["exp"],
        )
    except KeyError as exc:
        raise TokenError("Malformed token payload.") from exc
