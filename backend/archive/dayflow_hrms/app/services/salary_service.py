from sqlalchemy.orm import Session

from app.assumed_existing.org_models import Employee, SalaryComponent, SalaryStructure
from app.core.exceptions import AppError


def get_my_salary(db: Session, employee: Employee) -> dict:
    structure = (
        db.query(SalaryStructure)
        .filter(SalaryStructure.employee_id == employee.employee_id)
        .order_by(SalaryStructure.effective_from.desc())
        .first()
    )
    if structure is None:
        raise AppError("SALARY_NOT_FOUND", "No salary structure is on file for you.", status_code=404)

    components = (
        db.query(SalaryComponent)
        .filter(SalaryComponent.salary_structure_id == structure.salary_structure_id)
        .all()
    )

    net_pay_estimate = structure.net_pay_estimate
    if net_pay_estimate is None:
        earnings = sum(float(c.amount) for c in components if c.type.value == "EARNING")
        deductions = sum(float(c.amount) for c in components if c.type.value == "DEDUCTION")
        net_pay_estimate = round(earnings - deductions, 2)

    return {
        "monthly_wage": float(structure.monthly_wage),
        "annual_wage": float(structure.annual_wage),
        "wage_type": structure.wage_type,
        "effective_from": structure.effective_from,
        "components": [{"name": c.name, "type": c.type, "amount": float(c.amount)} for c in components],
        "net_pay_estimate": float(net_pay_estimate),
    }
