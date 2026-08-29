from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_type_id: int
    name: str
    is_balance_tracked: bool
    requires_attachment: bool
    is_active: bool


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_request_id: int
    employee_id: int
    employee_name: str | None = None
    leave_type: LeaveTypeOut
    start_date: date
    end_date: date
    number_of_days: Decimal
    remarks: str | None = None
    attachment_path: str | None = None
    status: str
    submitted_at: datetime
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None


class LeaveReviewRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)
