from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    String, Boolean, Date, TIMESTAMP, Enum, ForeignKey, BigInteger, Numeric
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

WAGE_TYPE = ("MONTHLY", "ANNUAL", "HOURLY")
COMPONENT_TYPE = ("EARNING", "DEDUCTION", "EMPLOYER_CONTRIBUTION")
CALCULATION_TYPE = ("FIXED", "PERCENTAGE")


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    salary_structure_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.employee_id"))
    monthly_wage: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    annual_wage: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    wage_type: Mapped[str] = mapped_column(Enum(*WAGE_TYPE, name="wage_type_enum"), default="MONTHLY")
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)

    components: Mapped[list["SalaryComponent"]] = relationship(
        back_populates="salary_structure", cascade="all, delete-orphan"
    )


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    salary_component_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    salary_structure_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("salary_structures.salary_structure_id"))
    component_name: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(Enum(*COMPONENT_TYPE, name="component_type_enum"))
    calculation_type: Mapped[str] = mapped_column(Enum(*CALCULATION_TYPE, name="calculation_type_enum"))
    percentage_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    computed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    salary_structure: Mapped["SalaryStructure"] = relationship(back_populates="components")
