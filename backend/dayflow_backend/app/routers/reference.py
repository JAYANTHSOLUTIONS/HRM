"""Departments & designations — read for Admin/HR, write for Admin only."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_admin_or_hr
from app.models.hr import Department, Designation
from app.schemas.reference import (
    DepartmentOut, DepartmentCreate, DepartmentUpdate, DepartmentList,
    DesignationOut, DesignationCreate, DesignationUpdate, DesignationList,
)
from app.exceptions import not_found, conflict
from app.services.audit_service import write_audit_log

router = APIRouter(tags=["Reference Data"])


@router.get("/departments", response_model=DepartmentList)
def list_departments(db: Session = Depends(get_db), _=Depends(require_admin_or_hr)):
    items = db.query(Department).order_by(Department.department_name).all()
    return {"items": items}


@router.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), user=Depends(require_admin)):
    if db.query(Department).filter(Department.department_name == payload.department_name).first():
        raise conflict("A department with this name already exists.")
    dept = Department(department_name=payload.department_name)
    db.add(dept)
    db.flush()
    write_audit_log(db, actor_user_id=user.user_id, action="DEPARTMENT_CREATED",
                     target_entity="departments", target_id=dept.department_id,
                     new_values={"department_name": payload.department_name})
    db.commit()
    db.refresh(dept)
    return dept


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
def update_department(department_id: int, payload: DepartmentUpdate,
                       db: Session = Depends(get_db), user=Depends(require_admin)):
    dept = db.query(Department).filter(Department.department_id == department_id).first()
    if dept is None:
        raise not_found("Department")
    old_values = {"department_name": dept.department_name, "is_active": dept.is_active}
    if payload.department_name is not None:
        dept.department_name = payload.department_name
    if payload.is_active is not None:
        dept.is_active = payload.is_active
    db.flush()
    write_audit_log(db, actor_user_id=user.user_id, action="DEPARTMENT_UPDATED",
                     target_entity="departments", target_id=dept.department_id,
                     old_values=old_values, new_values=payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/designations", response_model=DesignationList)
def list_designations(db: Session = Depends(get_db), _=Depends(require_admin_or_hr)):
    items = db.query(Designation).order_by(Designation.title).all()
    return {"items": items}


@router.post("/designations", response_model=DesignationOut, status_code=201)
def create_designation(payload: DesignationCreate, db: Session = Depends(get_db), user=Depends(require_admin)):
    if db.query(Designation).filter(Designation.title == payload.title).first():
        raise conflict("A designation with this title already exists.")
    designation = Designation(title=payload.title)
    db.add(designation)
    db.flush()
    write_audit_log(db, actor_user_id=user.user_id, action="DESIGNATION_CREATED",
                     target_entity="designations", target_id=designation.designation_id,
                     new_values={"title": payload.title})
    db.commit()
    db.refresh(designation)
    return designation


@router.patch("/designations/{designation_id}", response_model=DesignationOut)
def update_designation(designation_id: int, payload: DesignationUpdate,
                        db: Session = Depends(get_db), user=Depends(require_admin)):
    designation = db.query(Designation).filter(Designation.designation_id == designation_id).first()
    if designation is None:
        raise not_found("Designation")
    old_values = {"title": designation.title, "is_active": designation.is_active}
    if payload.title is not None:
        designation.title = payload.title
    if payload.is_active is not None:
        designation.is_active = payload.is_active
    db.flush()
    write_audit_log(db, actor_user_id=user.user_id, action="DESIGNATION_UPDATED",
                     target_entity="designations", target_id=designation.designation_id,
                     old_values=old_values, new_values=payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(designation)
    return designation
