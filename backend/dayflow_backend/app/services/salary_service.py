from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session, joinedload

from app.models.salary import SalaryStructure, SalaryComponent
from app.models.hr import Employee
from app.exceptions import not_found, bad_request
from app.services.audit_service import write_audit_log
from app.services.notification_service import notify
from app.schemas.salary import SalaryStructureIn


def get_current_salary(db: Session, employee_id: int) -> SalaryStructure | None:
    return (
        db.query(SalaryStructure)
        .options(joinedload(SalaryStructure.components))
        .filter(SalaryStructure.employee_id == employee_id, SalaryStructure.is_current.is_(True))
        .first()
    )


def get_salary_history(db: Session, employee_id: int) -> list[SalaryStructure]:
    return (
        db.query(SalaryStructure)
        .options(joinedload(SalaryStructure.components))
        .filter(SalaryStructure.employee_id == employee_id)
        .order_by(SalaryStructure.effective_from.desc())
        .all()
    )


def _resolve_components(monthly_wage: Decimal, components_in: list) -> list[dict]:
    resolved = []
    for c in components_in:
        if c.calculation_type == "PERCENTAGE":
            if c.percentage is None:
                raise bad_request(f"Component '{c.name}' requires a percentage value.")
            amount = (monthly_wage * c.percentage / Decimal(100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            if c.fixed_amount is None:
                raise bad_request(f"Component '{c.name}' requires a fixed_amount value.")
            amount = c.fixed_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        resolved.append({
            "component_name": c.name,
            "component_type": c.type,
            "calculation_type": c.calculation_type,
            "percentage_value": c.percentage,
            "fixed_amount": c.fixed_amount,
            "computed_amount": amount,
        })

    earnings = sum(r["computed_amount"] for r in resolved if r["component_type"] == "EARNING")
    deductions = sum(r["computed_amount"] for r in resolved if r["component_type"] == "DEDUCTION")
    if resolved and (earnings - deductions) > monthly_wage + Decimal("0.01"):
        raise bad_request(
            "Total of earning components (net of deductions) exceeds the defined monthly wage.",
            code="SALARY_COMPONENTS_EXCEED_WAGE",
        )
    return resolved


def create_salary_structure(
    db: Session, *, employee_id: int, payload: SalaryStructureIn, created_by_user_id: int
) -> SalaryStructure:
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise not_found("Employee")

    if payload.wage_type == "MONTHLY":
        annual_wage = payload.monthly_wage * 12
    elif payload.wage_type == "ANNUAL":
        annual_wage = payload.monthly_wage
    else:  # HOURLY — store as-is; annual left as monthly*12 approximation is misleading, so mirror value
        annual_wage = payload.monthly_wage * 12

    resolved_components = _resolve_components(payload.monthly_wage, payload.components)

    # Close out the previous current structure (never overwritten — spec section 16).
    previous = (
        db.query(SalaryStructure)
        .filter(SalaryStructure.employee_id == employee_id, SalaryStructure.is_current.is_(True))
        .with_for_update()
        .first()
    )
    old_values = None
    if previous is not None:
        if payload.effective_from <= previous.effective_from:
            raise bad_request(
                "effective_from must be after the current salary structure's effective_from date.",
            )
        old_values = {
            "salary_structure_id": previous.salary_structure_id,
            "monthly_wage": str(previous.monthly_wage),
            "effective_from": previous.effective_from.isoformat(),
        }
        previous.is_current = False
        previous.effective_to = payload.effective_from - timedelta(days=1)
        db.flush()

    new_structure = SalaryStructure(
        employee_id=employee_id,
        monthly_wage=payload.monthly_wage,
        annual_wage=annual_wage,
        wage_type=payload.wage_type,
        effective_from=payload.effective_from,
        effective_to=None,
        is_current=True,
        created_by=created_by_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_structure)
    db.flush()

    for comp in resolved_components:
        db.add(SalaryComponent(salary_structure_id=new_structure.salary_structure_id, **comp))
    db.flush()

    write_audit_log(
        db, actor_user_id=created_by_user_id, action="SALARY_CREATED",
        target_entity="salary_structures", target_id=new_structure.salary_structure_id,
        old_values=old_values,
        new_values={"monthly_wage": str(payload.monthly_wage), "effective_from": payload.effective_from.isoformat()},
    )

    notify(
        db, recipient_user_id=employee.user_id, type="SALARY_UPDATED",
        title="Your salary structure has been updated",
        message=f"A new salary structure is effective from {payload.effective_from}.",
    )

    db.commit()
    db.refresh(new_structure)
    return new_structure
