from datetime import date
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.security import validate_password_strength


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    department_id: int
    designation_id: int
    joining_date: date
    turnstile_token: str | None = Field(default=None, description="Cloudflare Turnstile token (Required)")

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        result = validate_password_strength(value)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return value


class SignupResponse(BaseModel):
    user_id: int
    employee_code: str
    email: EmailStr
    role: str
    is_email_verified: bool
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    turnstile_token: str | None = Field(default=None, description="Cloudflare Turnstile token (Required)")


class UserSummary(BaseModel):
    user_id: int
    employee_id: int
    employee_code: str
    full_name: str
    email: EmailStr
    role: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)
    turnstile_token: str | None = Field(default=None, description="Cloudflare Turnstile token (Optional)")


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    turnstile_token: str | None = Field(default=None, description="Cloudflare Turnstile token (Required)")


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    success: bool = True
    message: str
    reset_token: str


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, value: str) -> str:
        result = validate_password_strength(value)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return value


class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: dict | None = None
