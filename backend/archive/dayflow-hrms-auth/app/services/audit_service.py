"""
Thin audit-logging hook for authentication events.

Part 2 will implement the actual persistent audit_logs table/service. To
avoid coupling this module to that not-yet-built implementation, we log
structured events through the standard `logging` module under the
"dayflow.audit" logger name. Part 2 can attach a logging.Handler to this
logger (or replace `record_auth_event` wholesale) to persist these events
without any changes needed in auth_service.py call sites.
"""
import enum
import logging
from typing import Any

logger = logging.getLogger("dayflow.audit")


class AuthEvent(str, enum.Enum):
    SIGNUP = "SIGNUP"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"


def record_auth_event(event: AuthEvent, user_id: int | None, metadata: dict[str, Any] | None = None) -> None:
    logger.info(
        "auth_event",
        extra={
            "event": event.value,
            "user_id": user_id,
            "metadata": metadata or {},
        },
    )
