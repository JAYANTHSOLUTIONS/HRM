from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attendance_id: int
    employee_id: int
    employee_name: str | None = None
    attendance_date: date
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    work_hours: Decimal
    overtime_hours: Decimal
    status: str
    is_corrected: bool


class AttendanceCorrectRequest(BaseModel):
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    reason: str = Field(min_length=3, max_length=500)


class CheckInOut(BaseModel):
    attendance_id: int
    check_in_at: datetime
    status: str


class CheckOutOut(BaseModel):
    attendance_id: int
    check_out_at: datetime
    work_hours: Decimal
    status: str
