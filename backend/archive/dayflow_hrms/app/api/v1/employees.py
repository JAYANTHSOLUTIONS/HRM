from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.schemas.employee import EmployeeMeOut, EmployeeMeUpdate
from app.services import employee_service

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


def _to_out(employee: Employee, request: Request) -> EmployeeMeOut:
    data = EmployeeMeOut.model_validate(employee)
    data.profile_picture_url = employee_service.get_profile_picture_url(employee, str(request.base_url))
    return data


@router.get("/me", response_model=EmployeeMeOut)
def get_my_profile(request: Request, employee: Employee = Depends(get_current_employee)):
    return _to_out(employee, request)


@router.patch("/me", response_model=EmployeeMeOut)
def update_my_profile(
    request: Request,
    payload: EmployeeMeUpdate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    updated = employee_service.update_my_profile(db, employee, payload)
    return _to_out(updated, request)


@router.post("/me/profile-picture", response_model=EmployeeMeOut)
async def upload_my_profile_picture(
    request: Request,
    file: UploadFile = File(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    updated = await employee_service.upload_profile_picture(db, employee, file)
    return _to_out(updated, request)


@router.get("/me/profile-picture/view")
def view_my_profile_picture(employee: Employee = Depends(get_current_employee)):
    stream, size, mime = employee_service.stream_my_profile_picture(employee)
    return StreamingResponse(
        stream,
        media_type=mime,
        headers={
            "Content-Disposition": "inline",
            "Content-Length": str(size),
        },
    )
