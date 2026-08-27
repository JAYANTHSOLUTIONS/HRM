from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.assumed_existing.org_models import EmploymentStatus, EmploymentType, Gender


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department_id: int
    department_name: str


class DesignationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    designation_id: int
    title: str


class ManagerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    full_name: str


class EmployeeMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    profile_picture_url: Optional[str] = None
    department: Optional[DepartmentOut] = None
    designation: Optional[DesignationOut] = None
    manager: Optional[ManagerOut] = None
    joining_date: date
    employment_status: EmploymentStatus
    employment_type: EmploymentType


# ---------------------------------------------------------------------
# Update — this whitelist IS the security control. Any field the
# employee is not allowed to touch (role, salary, department,
# designation, manager, employee_code, employment_status) simply has no
# place to be sent, even if the client includes it in the JSON body —
# unknown fields are ignored by Pydantic model_validate/from json unless
# the caller inspects extras, and the service layer only ever reads the
# attributes declared here.
# ---------------------------------------------------------------------
class EmployeeMeUpdate(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="ignore")
