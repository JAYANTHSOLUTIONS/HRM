from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class SalaryComponentIn(BaseModel):
    name: str
    type: str = Field(pattern="^(EARNING|DEDUCTION|EMPLOYER_CONTRIBUTION)$")
    calculation_type: str = Field(pattern="^(FIXED|PERCENTAGE)$")
    percentage: Decimal | None = None
    fixed_amount: Decimal | None = None

    @field_validator("percentage")
    @classmethod
    def pct_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("percentage must be between 0 and 100")
        return v


class SalaryComponentOut(BaseModel):
    name: str
    type: str
    calculation_type: str
    percentage: Decimal | None = None
    fixed_amount: Decimal | None = None
    computed_amount: Decimal


class SalaryStructureIn(BaseModel):
    monthly_wage: Decimal = Field(gt=0)
    wage_type: str = Field(default="MONTHLY", pattern="^(MONTHLY|ANNUAL|HOURLY)$")
    effective_from: date
    components: list[SalaryComponentIn] = Field(default_factory=list)


class SalaryStructureOut(BaseModel):
    salary_structure_id: int
    employee_id: int
    monthly_wage: Decimal
    annual_wage: Decimal
    wage_type: str
    effective_from: date
    effective_to: date | None = None
    is_current: bool
    components: list[SalaryComponentOut]


class SalaryHistoryOut(BaseModel):
    items: list[SalaryStructureOut]
