"""
Authorization dependencies consumed by every Part 2 router.

get_current_user(): decodes the Bearer JWT issued by Part 1, loads the
corresponding active user (+ role, + employee profile) from MySQL.

require_role(*roles): dependency factory — 403s unless current_user's role
is one of the given roles. This is where backend RBAC enforcement lives;
the frontend's route guards are cosmetic only, per spec section 2.
"""
from fastapi import Depends, Header
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import decode_access_token, JWTError
from app.models.auth import User
from app.exceptions import unauthorized, forbidden


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized("Missing or malformed Authorization header.")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise unauthorized("Invalid or expired access token.")

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthorized("Malformed access token.")

    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.employee))
        .filter(User.user_id == int(user_id))
        .first()
    )
    if user is None or not user.is_active:
        raise unauthorized("This account is no longer active.")

    return user


def require_role(*allowed_roles: str):
    allowed = {r.upper() for r in allowed_roles}

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_name.upper() not in allowed:
            raise forbidden(
                f"This action requires one of roles: {', '.join(sorted(allowed))}."
            )
        return current_user

    return _dependency


require_admin = require_role("ADMIN")
require_admin_or_hr = require_role("ADMIN", "HR")
require_any_role = require_role("ADMIN", "HR", "EMPLOYEE")
