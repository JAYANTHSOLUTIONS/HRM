from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.hr import Employee
from app.models.auth import User
from app.exceptions import not_found


def list_employees(
    db: Session,
    *,
    page: int,
    page_size: int,
    department_id: int | None = None,
    designation_id: int | None = None,
    employment_status: str | None = None,
    search: str | None = None,
):
    query = db.query(Employee).options(
        joinedload(Employee.department), joinedload(Employee.designation), joinedload(Employee.user)
    )

    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if designation_id is not None:
        query = query.filter(Employee.designation_id == designation_id)
    if employment_status is not None:
        query = query.filter(Employee.employment_status == employment_status)
    if search:
        like = f"%{search}%"
        query = query.join(User, Employee.user_id == User.user_id, isouter=True).filter(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.employee_code.ilike(like),
                User.email.ilike(like),
            )
        )

    total_items = query.order_by(None).with_entities(func.count(Employee.employee_id)).scalar()
    items = (
        query.order_by(Employee.employee_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_items


def get_employee_or_404(db: Session, employee_id: int) -> Employee:
    emp = (
        db.query(Employee)
        .options(
            joinedload(Employee.department),
            joinedload(Employee.designation),
            joinedload(Employee.manager),
            joinedload(Employee.user),
        )
        .filter(Employee.employee_id == employee_id)
        .first()
    )
    if emp is None:
        raise not_found("Employee")
    return emp


PATCHABLE_FIELDS = {
    "department_id", "designation_id", "manager_id", "employment_status",
    "employment_type", "phone", "address", "date_of_birth", "gender",
    "joining_date", "first_name", "last_name",
}


def apply_employee_update(employee: Employee, payload: dict) -> dict:
    """Applies only whitelisted fields; returns {field: (old, new)} for audit diff."""
    changes: dict = {}
    for field, new_value in payload.items():
        if field not in PATCHABLE_FIELDS or new_value is None:
            continue
        old_value = getattr(employee, field)
        if str(old_value) != str(new_value):
            changes[field] = (str(old_value) if old_value is not None else None, str(new_value))
        setattr(employee, field, new_value)
    return changes
