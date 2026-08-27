from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.schemas.salary import SalaryMeOut
from app.services import salary_service

router = APIRouter(prefix="/api/v1/salary", tags=["salary"])


@router.get("/me", response_model=SalaryMeOut)
def get_my_salary(employee: Employee = Depends(get_current_employee), db: Session = Depends(get_db)):
    return salary_service.get_my_salary(db, employee)
