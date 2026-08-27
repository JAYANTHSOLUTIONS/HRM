import enum

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    ON_LEAVE = "ON_LEAVE"
    HALF_DAY = "HALF_DAY"


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (
        # One attendance row per employee per calendar date — this is what
        # makes double check-in impossible at the DB layer, not just the
        # application layer.
        UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
    )

    attendance_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False, index=True)

    attendance_date = Column(Date, nullable=False)  # server-derived, never client-supplied
    check_in_at = Column(DateTime(timezone=True), nullable=True)  # UTC
    check_out_at = Column(DateTime(timezone=True), nullable=True)  # UTC
    work_hours = Column(Float, nullable=False, default=0.0)  # server-computed only
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)

    employee = relationship("Employee", foreign_keys=[employee_id])
