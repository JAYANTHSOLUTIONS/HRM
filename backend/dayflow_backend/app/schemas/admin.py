from datetime import date
from pydantic import BaseModel, EmailStr, Field


class UserInviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = Field(pattern="^(HR|ADMIN|EMPLOYEE)$")
    department_id: int | None = None
    designation_id: int | None = None
    joining_date: date


class UserInviteResponse(BaseModel):
    user_id: int
    employee_code: str
    email: EmailStr
    role: str
    message: str
