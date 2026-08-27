"""
Standardized error format for the entire API:

{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": []
  }
}

All auth-flow failures should raise `AppError` (or a subclass) so the
global exception handler in main.py can render this consistently. Do not
raise raw HTTPException from service code for domain errors — reserve
HTTPException for things FastAPI itself raises (e.g. routing).
"""
from typing import Any


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list[Any] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


# ---- Common, named errors used across the auth module ----

class CaptchaFailedError(AppError):
    def __init__(self):
        super().__init__(403, "CAPTCHA_FAILED", "CAPTCHA verification failed.")


class AccountLockedError(AppError):
    def __init__(self, minutes: int):
        super().__init__(
            403,
            "ACCOUNT_LOCKED",
            f"Too many failed attempts. Try again after {minutes} minutes.",
        )


class InvalidCredentialsError(AppError):
    def __init__(self):
        super().__init__(401, "INVALID_CREDENTIALS", "Invalid email or password.")


class EmailNotVerifiedError(AppError):
    def __init__(self):
        super().__init__(403, "EMAIL_NOT_VERIFIED", "Please verify your email before signing in.")


class AccountInactiveError(AppError):
    def __init__(self):
        super().__init__(403, "ACCOUNT_INACTIVE", "This account has been deactivated.")


class EmailAlreadyExistsError(AppError):
    def __init__(self):
        super().__init__(409, "EMAIL_ALREADY_EXISTS", "An account with this email already exists.")


class TokenExpiredOrInvalidError(AppError):
    def __init__(self, message: str = "This link has expired or was already used."):
        super().__init__(400, "TOKEN_EXPIRED_OR_INVALID", message)


class InvalidTokenError(AppError):
    def __init__(self, message: str = "The provided token is invalid or has expired."):
        super().__init__(401, "INVALID_TOKEN", message)


class AuthenticationRequiredError(AppError):
    def __init__(self):
        super().__init__(401, "AUTHENTICATION_REQUIRED", "Authentication is required to access this resource.")


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(403, "FORBIDDEN", message)


class OTPRateLimitedError(AppError):
    def __init__(self, retry_after_seconds: int):
        super().__init__(
            429,
            "OTP_RATE_LIMITED",
            f"Please wait {retry_after_seconds} seconds before requesting another code.",
        )


class OTPMaxAttemptsError(AppError):
    def __init__(self):
        super().__init__(400, "OTP_MAX_ATTEMPTS_EXCEEDED", "Maximum verification attempts exceeded. Request a new code.")
