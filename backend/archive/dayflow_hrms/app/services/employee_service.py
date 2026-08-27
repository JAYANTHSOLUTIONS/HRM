import io

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.assumed_existing.org_models import Employee
from app.assumed_existing.storage_service import get_storage_service
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.schemas.employee import EmployeeMeUpdate
from app.services.file_validation import IMAGE_EXTENSIONS, validate_upload

settings = get_settings()


def get_profile_picture_url(employee: Employee, request_base_url: str) -> str | None:
    if not employee.profile_picture_key:
        return None
    # Protected, streamed endpoint — never a raw storage path/URL.
    return f"{request_base_url.rstrip('/')}/api/v1/employees/me/profile-picture/view"


def update_my_profile(db: Session, employee: Employee, payload: EmployeeMeUpdate) -> Employee:
    # Only fields declared on EmployeeMeUpdate can ever reach here — role,
    # salary, department, designation, manager, employee_code, and
    # employment_status have no field to arrive through, so there is
    # nothing to "forget to block": they were never accepted.
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(employee, field, value)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


async def upload_profile_picture(db: Session, employee: Employee, file: UploadFile) -> Employee:
    content = await file.read()
    validated = validate_upload(
        content,
        declared_filename=file.filename or "",
        allowed_extensions=IMAGE_EXTENSIONS,
        max_size_bytes=settings.MAX_PROFILE_PICTURE_MB * 1024 * 1024,
    )

    storage = get_storage_service()

    old_key = employee.profile_picture_key
    new_key = storage.save(
        io.BytesIO(content),
        folder=settings.LOCAL_PROFILE_IMAGES_SUBDIR,
        extension=validated.extension,
    )

    employee.profile_picture_key = new_key
    db.add(employee)
    db.commit()
    db.refresh(employee)

    if old_key:
        try:
            storage.delete(old_key)
        except FileNotFoundError:
            pass

    return employee


def stream_my_profile_picture(employee: Employee):
    if not employee.profile_picture_key:
        raise AppError("NOT_FOUND", "No profile picture has been uploaded.", status_code=404)
    storage = get_storage_service()
    try:
        stream, size = storage.open_stream(employee.profile_picture_key)
    except FileNotFoundError:
        raise AppError("NOT_FOUND", "Profile picture file is missing from storage.", status_code=404)
    ext = employee.profile_picture_key.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "application/octet-stream"
    )
    return stream, size, mime
