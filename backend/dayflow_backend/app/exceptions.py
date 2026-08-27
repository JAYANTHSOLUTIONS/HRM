from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Uniform application error -> {"error": {"code","message","details"}}"""

    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


# Common shortcuts -----------------------------------------------------------

def not_found(entity: str, code: str = "NOT_FOUND") -> AppError:
    return AppError(404, code, f"{entity} not found.")


def forbidden(message: str = "You are not authorized to perform this action.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def unauthorized(message: str = "Authentication required.") -> AppError:
    return AppError(401, "UNAUTHORIZED", message)


def bad_request(message: str, code: str = "VALIDATION_ERROR", details: list | None = None) -> AppError:
    return AppError(400, code, message, details)


def conflict(message: str, code: str = "CONFLICT") -> AppError:
    return AppError(409, code, message)
