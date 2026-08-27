"""
Central place where "who is making this request" gets resolved.
Every employee-facing router in Part 3 depends on `get_current_employee`
(never on a path/body `employee_id`), which is what satisfies the
security requirement in the spec:

    "Every employee request must identify the employee from:
     authenticated JWT user -> users.user_id -> employees.user_id.
     Never trust employee_id from frontend request body."
"""
from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.assumed_existing.auth import User, get_current_user
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.core.exceptions import AppError


def get_current_employee(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == current_user.user_id).first()
    if employee is None:
        raise AppError(
            code="EMPLOYEE_PROFILE_NOT_FOUND",
            message="No employee profile is linked to this account.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return employee
