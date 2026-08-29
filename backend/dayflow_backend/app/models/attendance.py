from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Boolean, Date, TIMESTAMP, Enum, ForeignKey, BigInteger, Numeric, UniqueConstraint, Integer
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UpdatedAtMixin

ATTENDANCE_STATUS = ("PRESENT", "ABSENT", "HALF_DAY", "LEAVE", "HOLIDAY", "WEEKEND")


class UTCDateTime(TypeDecorator):
    """Store UTC in MySQL TIMESTAMP and expose timezone-aware UTC values."""

    impl = TIMESTAMP
    cache_ok = True

    @staticmethod
    def normalize(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_bind_param(self, value, dialect):
        normalized = self.normalize(value)
        return normalized.replace(tzinfo=None) if normalized else None

    def process_result_value(self, value, dialect):
        return self.normalize(value)


class Attendance(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),)

    attendance_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.employee_id"))
    attendance_date: Mapped[date] = mapped_column(Date)
    check_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    check_out_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    work_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(Enum(*ATTENDANCE_STATUS, name="attendance_status_enum"), default="ABSENT")
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrected_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    employee: Mapped["Employee"] = relationship()


from app.models.hr import Employee  # noqa: E402
