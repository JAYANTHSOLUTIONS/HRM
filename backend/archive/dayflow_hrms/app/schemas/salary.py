from datetime import date
from typing import List

from pydantic import BaseModel

from app.assumed_existing.org_models import SalaryComponentType, WageType


class SalaryComponentOut(BaseModel):
    name: str
    type: SalaryComponentType
    amount: float


class SalaryMeOut(BaseModel):
    monthly_wage: float
    annual_wage: float
    wage_type: WageType
    effective_from: date
    components: List[SalaryComponentOut]
    net_pay_estimate: float
