from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    String, Boolean, Date, TIMESTAMP, Enum, ForeignKey, BigInteger, SmallInteger, Numeric
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UpdatedAtMixin

LEAVE_STATUS = ("PENDING", "APPROVED", "REJECTED", "CANCELLED")


class LeaveType(Base, TimestampMixin):
    __tablename__ = "leave_types"

    leave_type_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_balance_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_attachment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LeaveBalance(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "leave_balances"

    leave_balance_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.employee_id"))
    leave_type_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("leave_types.leave_type_id"))
    leave_year: Mapped[int] = mapped_column(SmallInteger)
    allocated_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    used_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    leave_type: Mapped["LeaveType"] = relationship()

    @property
    def remaining_days(self) -> Decimal:
        return self.allocated_days - self.used_days


class LeaveRequest(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "leave_requests"

    leave_request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.employee_id"))
    leave_type_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("leave_types.leave_type_id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    number_of_days: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    remarks: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(Enum(*LEAVE_STATUS, name="leave_status_enum"), default="PENDING")
    submitted_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    employee: Mapped["Employee"] = relationship()
    leave_type: Mapped["LeaveType"] = relationship()


class LeaveRequestReview(Base):
    __tablename__ = "leave_request_reviews"

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    leave_request_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("leave_requests.leave_request_id"))
    reviewer_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    previous_status: Mapped[str] = mapped_column(Enum(*LEAVE_STATUS, name="leave_prev_status_enum"))
    new_status: Mapped[str] = mapped_column(Enum(*LEAVE_STATUS, name="leave_new_status_enum"))
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(TIMESTAMP)


from app.models.hr import Employee  # noqa: E402
