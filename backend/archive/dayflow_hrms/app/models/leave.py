import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LeaveRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class LeaveType(Base):
    __tablename__ = "leave_types"

    leave_type_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_balance_tracked = Column(Boolean, nullable=False, default=True)
    requires_attachment = Column(Boolean, nullable=False, default=False)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    leave_balance_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    allocated_days = Column(Float, nullable=False, default=0.0)
    used_days = Column(Float, nullable=False, default=0.0)

    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id])


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    leave_request_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    number_of_days = Column(Float, nullable=False)  # server-computed only
    remarks = Column(Text, nullable=True)
    attachment_document_id = Column(Integer, ForeignKey("documents.document_id"), nullable=True)

    status = Column(Enum(LeaveRequestStatus), nullable=False, default=LeaveRequestStatus.PENDING, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id])
