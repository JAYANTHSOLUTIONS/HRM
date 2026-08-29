"""Pydantic schemas for the employee self-service (/me) endpoints."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class SelfProfileUpdate(BaseModel):
    """Fields an employee is allowed to edit on their own profile."""
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    gender: str | None = Field(default=None, pattern="^(MALE|FEMALE|OTHER|PREFER_NOT_TO_SAY)$")
    date_of_birth: date | None = None


class SelfProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    profile_picture_url: str | None = None
    department_name: str | None = None
    designation_title: str | None = None
    manager_name: str | None = None
    joining_date: date
    employment_status: str
    employment_type: str


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class CheckInResponse(BaseModel):
    attendance_id: int
    attendance_date: date
    check_in_at: datetime
    status: str
    message: str


class CheckOutResponse(BaseModel):
    attendance_id: int
    attendance_date: date
    check_in_at: datetime | None
    check_out_at: datetime
    work_hours: Decimal
    overtime_hours: Decimal
    status: str
    message: str


class AttendanceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attendance_id: int
    attendance_date: date
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    work_hours: Decimal
    overtime_hours: Decimal
    status: str
    is_corrected: bool


class WeeklySummary(BaseModel):
    week_start: date
    week_end: date
    days_present: int
    leaves_count: int
    absences: int
    total_work_hours: Decimal
    total_overtime_hours: Decimal
    records: list[AttendanceRecord]


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------

class LeaveBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_type_id: int
    leave_type_name: str
    leave_year: int
    allocated_days: Decimal
    used_days: Decimal
    remaining_days: Decimal
    requires_attachment: bool


class LeaveApplyRequest(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    remarks: str | None = Field(default=None, max_length=1000)
    attachment_path: str | None = Field(default=None, max_length=1000)

    def model_post_init(self, __context) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")


class MyLeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_request_id: int
    leave_type_name: str
    start_date: date
    end_date: date
    number_of_days: Decimal
    remarks: str | None = None
    attachment_path: str | None = None
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None = None
    review_comment: str | None = None


# ---------------------------------------------------------------------------
# Salary
# ---------------------------------------------------------------------------

class MySalaryComponentOut(BaseModel):
    name: str
    type: str
    calculation_type: str
    percentage: Decimal | None
    fixed_amount: Decimal | None
    computed_amount: Decimal


class MySalaryOut(BaseModel):
    salary_structure_id: int
    monthly_wage: Decimal
    annual_wage: Decimal
    wage_type: str
    effective_from: date
    effective_to: date | None
    components: list[MySalaryComponentOut]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class EmployeeDashboardOut(BaseModel):
    employee_id: int
    full_name: str
    department: str | None
    designation: str | None
    profile_picture_url: str | None
    today_status: str | None
    check_in_at: datetime | None
    check_out_at: datetime | None
    work_hours_today: Decimal
    this_week_present_days: int
    pending_leave_requests: int
    approved_leave_requests: int
    leave_balances: list[LeaveBalanceOut]
