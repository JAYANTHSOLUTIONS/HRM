import io

from PIL import Image
from sqlalchemy.orm import Session

from app.models.hr import Employee
from app.exceptions import not_found, bad_request
from app.services.storage_service import get_profile_image_storage, generate_storage_key
from app.services.file_validation import validate_upload, ALLOWED_IMAGE_EXT
from app.services.audit_service import write_audit_log
from app.core.config import get_settings

settings = get_settings()

MAX_DIMENSION = 512  # px — normalize large uploads down for consistent avatar rendering


def upload_profile_picture(
    db: Session,
    *,
    employee_id: int,
    original_filename: str,
    declared_content_type: str,
    content: bytes,
    uploaded_by_user_id: int,
) -> Employee:
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise not_found("Employee")

    ext, mime_type = validate_upload(
        filename=original_filename,
        declared_content_type=declared_content_type,
        header_bytes=content[:16],
        file_size_bytes=len(content),
        max_size_bytes=settings.max_image_size_bytes,
        allowed_extensions=ALLOWED_IMAGE_EXT,
    )

    # Normalize: re-encode through Pillow (also strips any embedded scripts/metadata
    # payloads riding along in a crafted image) and cap dimensions.
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content))  # re-open after verify()
        image = image.convert("RGB") if image.mode not in ("RGB", "RGBA") else image
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        buffer = io.BytesIO()
        save_format = "JPEG" if ext in ("jpg", "jpeg") else ("PNG" if ext == "png" else "WEBP")
        image.save(buffer, format=save_format)
        normalized_bytes = buffer.getvalue()
    except Exception:
        raise bad_request("Uploaded file is not a valid, readable image.", code="INVALID_IMAGE")

    storage_key = generate_storage_key(employee_id, f"avatar.{ext}", subdir="profile-images")
    storage = get_profile_image_storage()
    storage.save(storage_key, normalized_bytes)

    # The DB column stores the STORAGE KEY, not a public URL (spec section 6/10:
    # metadata in MySQL, bytes in object storage). The router computes the
    # actual browsable URL (a protected streaming endpoint) from employee_id
    # at response time — see routers/employees.py::_serve_profile_picture_url.
    employee.profile_picture_url = storage_key

    write_audit_log(
        db, actor_user_id=uploaded_by_user_id, action="PROFILE_PICTURE_UPDATED",
        target_entity="employees", target_id=employee.employee_id,
        new_values={"storage_key": storage_key},
    )

    db.commit()
    db.refresh(employee)
    return employee
