"""
======================================================================
ASSUMED PART 2 CODE — DELETE THIS FILE IN THE REAL PROJECT
======================================================================
Minimal stand-ins for the `employees`, `departments`, `designations`,
and `salary_structures` tables that PART 2 (Admin/HR) already owns.
Swap every:

    from app.assumed_existing.org_models import Employee, Department, ...

for the real import path once this is merged into the actual codebase.
The columns here are the ones Part 3 actually reads/writes — your real
Employee model almost certainly has more (created_by, audit fields,
etc.); that's fine, Part 3 only touches what's listed below.
======================================================================
"""
import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String(255), nullable=False)


class Designation(Base):
    __tablename__ = "designations"

    designation_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False, index=True)

    employee_code = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    address = Column(String(500), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)

    # Storage KEY, not a URL — the URL is derived at response time via the
    # protected /employees/me/profile-picture (view) endpoint.
    profile_picture_key = Column(String(500), nullable=True)

    department_id = Column(Integer, ForeignKey("departments.department_id"), nullable=True)
    designation_id = Column(Integer, ForeignKey("designations.designation_id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    joining_date = Column(Date, nullable=False)
    employment_status = Column(Enum(EmploymentStatus), nullable=False, default=EmploymentStatus.ACTIVE)
    employment_type = Column(Enum(EmploymentType), nullable=False, default=EmploymentType.FULL_TIME)

    department = relationship("Department", foreign_keys=[department_id])
    designation = relationship("Designation", foreign_keys=[designation_id])
    manager = relationship("Employee", remote_side=[employee_id], foreign_keys=[manager_id])


class WageType(str, enum.Enum):
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"
    HOURLY = "HOURLY"


class SalaryStructure(Base):
    """Owned/edited by Admin (Part 2). Part 3 is READ-ONLY against this."""

    __tablename__ = "salary_structures"

    salary_structure_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False, index=True)
    monthly_wage = Column(Numeric(12, 2), nullable=False)
    annual_wage = Column(Numeric(12, 2), nullable=False)
    wage_type = Column(Enum(WageType), nullable=False, default=WageType.MONTHLY)
    effective_from = Column(Date, nullable=False)
    net_pay_estimate = Column(Numeric(12, 2), nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id])


class SalaryComponentType(str, enum.Enum):
    EARNING = "EARNING"
    DEDUCTION = "DEDUCTION"


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    salary_component_id = Column(Integer, primary_key=True, index=True)
    salary_structure_id = Column(
        Integer, ForeignKey("salary_structures.salary_structure_id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    type = Column(Enum(SalaryComponentType), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
