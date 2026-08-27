from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    department_id: int
    designation_id: int
    joining_date: date

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        result = validate_password_strength(value)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return value

    # NOTE: `role` is intentionally NOT a field on this schema. Any `role`
    # key sent by a client is silently ignored by Pydantic (extra="ignore"
    # is the default for BaseModel) — the backend always forces EMPLOYEE.


class SignupResponse(BaseModel):
    user_id: int
    employee_code: str
    email: EmailStr
    role: str
    is_email_verified: bool
    message: str


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    captcha_token: str = Field(min_length=1)


class UserSummary(BaseModel):
    user_id: int
    employee_id: int
    employee_code: str
    full_name: str
    email: EmailStr
    role: str
    profile_picture_url: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


# ---------------------------------------------------------------------------
# Refresh / logout
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Forgot / reset / change password
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    # NOTE: deliberate deviation from the spec's literal {token, new_password}
    # shape. Section 5 mandates OTP-based password reset (6-digit codes),
    # but a 6-digit code is not globally unique the way a 32-byte random
    # token is — looking it up without an account reference risks matching
    # the wrong user's OTP. `email` is required here to safely scope the
    # OTP lookup. See README "Design decisions" for the full rationale.
    email: EmailStr
    token: str = Field(min_length=1, description="6-digit OTP code delivered via email.")
    new_password: str = Field(min_length=1, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        result = validate_password_strength(value)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        result = validate_password_strength(value)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return value
