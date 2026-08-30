import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_admin_or_hr, get_current_user
from app.models.auth import User
from app.schemas.employee import EmployeeListItem, EmployeeDetail, EmployeeUpdate
from app.schemas.resume import ResumeOut, ResumeUpdate
from app.schemas.common import Page
from app.services.employee_service import (
    list_employees, get_employee_or_404, apply_employee_update,
    get_employee_resume, update_employee_resume
)
from app.services.audit_service import write_audit_log
from app.exceptions import forbidden

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


@router.get("/{employee_id}/resume", response_model=ResumeOut)
def get_resume(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeOut:
    """Get an employee's resume. Employees can view their own; HR/Admin can view anyone's."""
    is_employee = current_user.role_name.upper() == "EMPLOYEE"
    if is_employee:
        if not current_user.employee or current_user.employee.employee_id != employee_id:
            raise forbidden("You are only allowed to view your own resume.")
            
    resume = get_employee_resume(db, employee_id)
    return resume


@router.patch("/{employee_id}/resume", response_model=ResumeOut)
def update_resume(
    employee_id: int,
    payload: ResumeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeOut:
    """Update an employee's resume. Only the employee themselves can edit their resume."""
    if not current_user.employee or current_user.employee.employee_id != employee_id:
        raise forbidden("You are only allowed to edit your own resume.")
        
    resume = update_employee_resume(db, employee_id, payload.model_dump(exclude_unset=True))
    
    # Optional: Log the audit event
    write_audit_log(
        db, actor_user_id=current_user.user_id, action="EMPLOYEE_RESUME_UPDATED",
        target_entity="employee_resumes", target_id=employee_id,
        old_values={}, new_values=payload.model_dump(exclude_unset=True)
    )
    db.commit()
    
    return resume
