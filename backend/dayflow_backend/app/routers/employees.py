import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_admin_or_hr
from app.models.auth import User
from app.schemas.employee import EmployeeListItem, EmployeeDetail, EmployeeUpdate
from app.schemas.common import Page
from app.services.employee_service import list_employees, get_employee_or_404, apply_employee_update
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/employees", tags=["Employees"])


def _attach_email(employee):
    employee.email = employee.user.email if employee.user else None
    if employee.profile_picture_url:
        employee.profile_picture_url = f"/api/v1/employees/{employee.employee_id}/profile-picture/raw"
    return employee


@router.get("", response_model=Page[EmployeeListItem])
def get_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    department_id: int | None = None,
    designation_id: int | None = None,
    employment_status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_hr),
):
    items, total_items = list_employees(
        db, page=page, page_size=page_size, department_id=department_id,
        designation_id=designation_id, employment_status=employment_status, search=search,
    )
    for e in items:
        _attach_email(e)
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    return {"page": page, "page_size": page_size, "total_items": total_items,
            "total_pages": total_pages, "items": items}


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: int, db: Session = Depends(get_db), _=Depends(require_admin_or_hr)):
    employee = get_employee_or_404(db, employee_id)
    return _attach_email(employee)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
def update_employee(
    employee_id: int, payload: EmployeeUpdate,
    db: Session = Depends(get_db), user: User = Depends(require_admin),
):
    employee = get_employee_or_404(db, employee_id)
    changes = apply_employee_update(employee, payload.model_dump(exclude_unset=True))
    db.flush()

    if changes:
        write_audit_log(
            db, actor_user_id=user.user_id, action="EMPLOYEE_UPDATED",
            target_entity="employees", target_id=employee.employee_id,
            old_values={k: v[0] for k, v in changes.items()},
            new_values={k: v[1] for k, v in changes.items()},
        )
    db.commit()
    db.refresh(employee)
    return _attach_email(employee)
