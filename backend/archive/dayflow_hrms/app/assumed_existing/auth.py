"""
======================================================================
ASSUMED PART 1 CODE — DELETE THIS FILE IN THE REAL PROJECT
======================================================================
This file exists only so Part 3 is runnable/testable on its own. In the
real Dayflow codebase, PART 1 already owns:

  - the `User` SQLAlchemy model (users table)
  - JWT creation / verification
  - the `get_current_user` FastAPI dependency
  - the `RoleChecker` / `require_role(...)` style dependency used to
    gate ADMIN / HR-only endpoints

Wherever a file in app/api/v1/*.py or app/services/*.py does:

    from app.assumed_existing.auth import get_current_user, User, UserRole

...swap that import for your real Part 1 module. Nothing in Part 3
should re-implement login, signup, password hashing, or token issuance —
this stub is intentionally minimal (just enough to decode a JWT and load
a user) so the rest of the module has something concrete to depend on.
======================================================================
"""
import enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, get_db

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    HR = "HR"
    ADMIN = "ADMIN"


class User(Base):
    """Minimal stand-in for the real Part 1 `users` table."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = Column(Integer, nullable=False, default=1)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "UNAUTHORIZED", "message": detail, "details": []}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the JWT issued at login and loads the corresponding user.
    This is the ONLY source of identity for every endpoint below — no
    route in Part 3 accepts a user id / employee id from the request
    body or query string.
    """
    if not token:
        raise _unauthorized("Not authenticated")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise _unauthorized()
    except JWTError:
        raise _unauthorized()

    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory used to gate admin/HR-only paths (e.g. document
    access override for the employee document-view endpoint)."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not have permission to perform this action.",
                        "details": [],
                    }
                },
            )
        return user

    return _checker
