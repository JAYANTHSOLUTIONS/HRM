from __future__ import annotations
from datetime import date, datetime

from sqlalchemy import (
    String, Boolean, Date, TIMESTAMP, Enum, ForeignKey, BigInteger, Integer, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UpdatedAtMixin

EMPLOYMENT_STATUS = ("ACTIVE", "INACTIVE", "RESIGNED", "TERMINATED")
EMPLOYMENT_TYPE = ("FULL_TIME", "PART_TIME", "CONTRACT", "INTERN")
GENDER = ("MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY")
DOCUMENT_TYPE = ("RESUME", "ID_PROOF", "ADDRESS_PROOF", "MEDICAL_CERTIFICATE",
                  "JOINING_DOCUMENT", "OTHER")
DOCUMENT_STATUS = ("ACTIVE", "ARCHIVED")


class Department(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(primary_key=True)
    department_name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Designation(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "designations"

    designation_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Employee(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), unique=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(Enum(*GENDER, name="gender_enum"), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.department_id"), nullable=True)
    designation_id: Mapped[int | None] = mapped_column(ForeignKey("designations.designation_id"), nullable=True)
    manager_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("employees.employee_id"), nullable=True)
    joining_date: Mapped[date] = mapped_column(Date)
    employment_status: Mapped[str] = mapped_column(
        Enum(*EMPLOYMENT_STATUS, name="employment_status_enum"), default="ACTIVE")
    employment_type: Mapped[str] = mapped_column(
        Enum(*EMPLOYMENT_TYPE, name="employment_type_enum"), default="FULL_TIME")

    user: Mapped["User"] = relationship(back_populates="employee", foreign_keys=[user_id])
    department: Mapped["Department | None"] = relationship()
    designation: Mapped["Designation | None"] = relationship()
    manager: Mapped["Employee | None"] = relationship(remote_side=[employee_id])
    resume: Mapped[EmployeeResume | None] = relationship(back_populates="employee", cascade="all, delete-orphan", uselist=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class EmployeeDocument(Base, TimestampMixin):
    __tablename__ = "employee_documents"

    document_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.employee_id"))
    document_type: Mapped[str] = mapped_column(Enum(*DOCUMENT_TYPE, name="document_type_enum"))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    status: Mapped[str] = mapped_column(Enum(*DOCUMENT_STATUS, name="document_status_enum"), default="ACTIVE")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship()


class Holiday(Base, TimestampMixin):
    __tablename__ = "holidays"

    holiday_id: Mapped[int] = mapped_column(primary_key=True)
    holiday_date: Mapped[date] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)


class EmployeeResume(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "employee_resumes"

    employee_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        primary_key=True
    )
    about: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    what_i_love: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    interests: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    certifications: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="resume")


from app.models.auth import User  # noqa: E402  (needed for relationship string resolution)
