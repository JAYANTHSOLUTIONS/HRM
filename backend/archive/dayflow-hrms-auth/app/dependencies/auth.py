"""
Shared FastAPI dependencies for authentication/authorization.

Parts 2 and 3 should import get_current_user / require_role / require_roles
from THIS module rather than reimplementing JWT parsing, so there is a
single source of truth for "who is calling this endpoint".
"""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationRequiredError, ForbiddenError, InvalidTokenError
from app.core.jwt import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

# auto_error=False so we can raise our own standardized AUTHENTICATION_REQUIRED
# error instead of FastAPI's default 403 "Not authenticated".
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolves the current user from the Authorization: Bearer <JWT> header.

    The JWT's `role` claim is convenient for fast checks, but the User
    object returned here is loaded fresh from MySQL, which remains the
    source of truth for is_active / role / any other authorization-
    relevant field. Downstream code should prefer `user.role.name` over
    trusting a stale JWT claim for anything security-sensitive.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationRequiredError()

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        user_id = int(payload.sub)
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError() from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("This account is no longer available.")

    request.state.current_user_id = user.user_id
    request.state.current_user_role = user.role.name
    return user


def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    """Alias kept for readability at call sites that only need "any logged-in user"."""
    return current_user


def require_role(role_name: str):
    """
    Usage: `current_user: User = Depends(require_role("ADMIN"))`
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name != role_name:
            raise ForbiddenError(f"This action requires the {role_name} role.")
        return current_user

    return _dependency


def require_roles(*role_names: str):
    """
    Usage: `current_user: User = Depends(require_roles("ADMIN", "HR"))`
    """
    allowed = set(role_names)

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed:
            raise ForbiddenError(f"This action requires one of the following roles: {', '.join(sorted(allowed))}.")
        return current_user

    return _dependency
