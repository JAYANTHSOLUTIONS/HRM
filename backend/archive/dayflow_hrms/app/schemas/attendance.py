from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.models.attendance import AttendanceStatus


class AttendanceTodayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attendance_date: date
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None
    work_hours: float
    status: AttendanceStatus


class CheckInOut(BaseModel):
    attendance_date: date
    check_in_at: datetime
    status: AttendanceStatus


class CheckOutOut(BaseModel):
    attendance_date: date
    check_in_at: datetime
    check_out_at: datetime
    work_hours: float
    status: AttendanceStatus


class AttendanceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attendance_date: date
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None
    work_hours: float
    status: AttendanceStatus


class AttendanceSummary(BaseModel):
    count_of_days_present: int
    leaves_used: int
    total_working_days: int


class AttendanceRangeOut(BaseModel):
    range: Literal["daily", "weekly"]
    week_start: Optional[date] = None
    week_end: Optional[date] = None
    summary: AttendanceSummary
    items: List[AttendanceItem]
