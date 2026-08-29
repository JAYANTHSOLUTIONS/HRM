from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.auth import User
from app.schemas.salary import SalaryStructureIn, SalaryStructureOut, SalaryComponentOut, SalaryHistoryOut, SalaryListOut
from app.services.salary_service import get_current_salary, get_salary_history, get_all_salaries, create_salary_structure
from app.exceptions import not_found

router = APIRouter(prefix="/salary", tags=["Salary (Admin only)"])


def _to_out(structure) -> SalaryStructureOut:
    return SalaryStructureOut(
        salary_structure_id=structure.salary_structure_id,
        employee_id=structure.employee_id,
        monthly_wage=structure.monthly_wage,
        annual_wage=structure.annual_wage,
        wage_type=structure.wage_type,
        effective_from=structure.effective_from,
        effective_to=structure.effective_to,
        is_current=structure.is_current,
        components=[
            SalaryComponentOut(
                name=c.component_name, type=c.component_type, calculation_type=c.calculation_type,
                percentage=c.percentage_value, fixed_amount=c.fixed_amount, computed_amount=c.computed_amount,
            )
            for c in structure.components
        ],
    )


@router.get("", response_model=SalaryListOut)
def list_salaries(db: Session = Depends(get_db), _=Depends(require_admin)):
    structures = get_all_salaries(db)
    return {"items": [_to_out(s) for s in structures]}


@router.get("/{employee_id}", response_model=SalaryStructureOut)
def get_salary(employee_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    structure = get_current_salary(db, employee_id)
    if structure is None:
        raise not_found("Current salary structure for this employee")
    return _to_out(structure)


@router.get("/{employee_id}/history", response_model=SalaryHistoryOut)
def get_history(employee_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    structures = get_salary_history(db, employee_id)
    return {"items": [_to_out(s) for s in structures]}


@router.put("/{employee_id}", response_model=SalaryStructureOut)
def put_salary(
    employee_id: int, payload: SalaryStructureIn,
    db: Session = Depends(get_db), user: User = Depends(require_admin),
):
    structure = create_salary_structure(
        db, employee_id=employee_id, payload=payload, created_by_user_id=user.user_id
    )
    return _to_out(structure)
