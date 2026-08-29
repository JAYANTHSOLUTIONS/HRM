from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.reference import DepartmentOut, DesignationOut


class ManagerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    full_name: str


class EmployeeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    employee_code: str
    full_name: str
    email: str | None = None
    department: DepartmentOut | None = None
    designation: DesignationOut | None = None
    employment_status: str
    employment_type: str
    joining_date: date
    profile_picture_url: str | None = None


class EmployeeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    profile_picture_url: str | None = None
    department: DepartmentOut | None = None
    designation: DesignationOut | None = None
    manager: ManagerOut | None = None
    joining_date: date
    employment_status: str
    employment_type: str


class EmployeeUpdate(BaseModel):
    """ADMIN-only PATCH payload. Every field optional; only present fields are applied.
    role_id / user_id / employee_code are intentionally NOT settable here."""
    department_id: int | None = None
    designation_id: int | None = None
    manager_id: int | None = None
    employment_status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE|RESIGNED|TERMINATED)$")
    employment_type: str | None = Field(default=None, pattern="^(FULL_TIME|PART_TIME|CONTRACT|INTERN)$")
    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, pattern="^(MALE|FEMALE|OTHER|PREFER_NOT_TO_SAY)$")
    joining_date: date | None = None
    first_name: str | None = None
    last_name: str | None = None
