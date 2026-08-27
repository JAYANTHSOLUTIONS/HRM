from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.leave import LeaveRequestStatus


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_type_id: int
    name: str
    is_balance_tracked: bool
    requires_attachment: bool


class LeaveTypeListOut(BaseModel):
    items: List[LeaveTypeOut]


class LeaveBalanceItem(BaseModel):
    leave_type: str
    allocated_days: float
    used_days: float
    remaining_days: float


class LeaveBalancesOut(BaseModel):
    year: int
    items: List[LeaveBalanceItem]


# `employee_id` is deliberately NOT a field here — identity comes from
# the JWT (see api/deps.py::get_current_employee). `number_of_days` is
# also not accepted from the client; the service layer computes it.
class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    remarks: Optional[str] = Field(default=None, max_length=1000)
    attachment_document_id: Optional[int] = None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class LeaveRequestOut(BaseModel):
    leave_request_id: int
    leave_type: str
    start_date: date
    end_date: date
    number_of_days: float
    status: LeaveRequestStatus
    submitted_at: datetime


class LeaveRequestListItem(LeaveRequestOut):
    remarks: Optional[str] = None


class LeaveRequestListOut(BaseModel):
    items: List[LeaveRequestListItem]


class LeaveCancelOut(BaseModel):
    leave_request_id: int
    status: LeaveRequestStatus
