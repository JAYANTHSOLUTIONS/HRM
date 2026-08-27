from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list = []


class ErrorResponse(BaseModel):
    error: ErrorDetail
