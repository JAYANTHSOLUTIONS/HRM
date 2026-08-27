from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.attendance import AttendanceStatus
from app.models.leave import LeaveRequestStatus


class DashboardProfile(BaseModel):
    full_name: str
    profile_picture_url: Optional[str] = None


class DashboardTodayAttendance(BaseModel):
    status: Optional[AttendanceStatus] = None
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None


class DashboardCurrentLeave(BaseModel):
    leave_request_id: int
    leave_type: str
    start_date: str
    end_date: str
    status: LeaveRequestStatus


class DashboardLeaveBalanceItem(BaseModel):
    leave_type: str
    remaining_days: float


class DashboardRecentLeaveRequest(BaseModel):
    leave_request_id: int
    leave_type: str
    status: LeaveRequestStatus
    start_date: str
    end_date: str


class DashboardSalarySummary(BaseModel):
    monthly_wage: Optional[float] = None


class DashboardActivityItem(BaseModel):
    type: str
    message: str
    at: datetime


class DashboardMeOut(BaseModel):
    profile: DashboardProfile
    today_attendance: DashboardTodayAttendance
    current_leave: Optional[DashboardCurrentLeave] = None
    leave_balance_summary: List[DashboardLeaveBalanceItem]
    recent_leave_requests: List[DashboardRecentLeaveRequest]
    salary_summary: DashboardSalarySummary
    recent_activity: List[DashboardActivityItem]
