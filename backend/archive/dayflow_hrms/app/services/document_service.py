import io

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.assumed_existing.auth import User, UserRole
from app.assumed_existing.org_models import Employee
from app.assumed_existing.storage_service import get_storage_service
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.document import Document
from app.services.file_validation import (
    DOCUMENT_EXTENSIONS,
    safe_display_filename,
    validate_upload,
)

settings = get_settings()

_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


async def upload_my_document(
    db: Session, employee: Employee, document_type: str, file: UploadFile
) -> Document:
    content = await file.read()
    validated = validate_upload(
        content,
        declared_filename=file.filename or "",
        allowed_extensions=DOCUMENT_EXTENSIONS,
        max_size_bytes=settings.MAX_DOCUMENT_MB * 1024 * 1024,
    )

    storage = get_storage_service()
    storage_key = storage.save(
        io.BytesIO(content),
        folder=settings.LOCAL_DOCUMENTS_SUBDIR,
        extension=validated.extension,
    )

    document = Document(
        employee_id=employee.employee_id,
        document_type=document_type,
        original_filename=safe_display_filename(file.filename or "document"),
        mime_type=validated.mime_type,
        storage_key=storage_key,
        size_bytes=validated.size_bytes,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_my_documents(db: Session, employee: Employee) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.employee_id == employee.employee_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def _get_authorized_document(db: Session, document_id: int, current_user: User, employee: Employee | None) -> Document:
    document = db.query(Document).filter(Document.document_id == document_id).first()
    if document is None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status_code=404)

    is_owner = employee is not None and document.employee_id == employee.employee_id
    is_admin_or_hr = current_user.role in (UserRole.ADMIN, UserRole.HR)

    if not (is_owner or is_admin_or_hr):
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to access this document.",
            status_code=403,
        )
    return document


def stream_document(db: Session, document_id: int, current_user: User, employee: Employee | None):
    document = _get_authorized_document(db, document_id, current_user, employee)
    storage = get_storage_service()
    try:
        stream, size = storage.open_stream(document.storage_key)
    except FileNotFoundError:
        raise AppError("DOCUMENT_FILE_MISSING", "Document file is missing from storage.", status_code=404)
    return document, stream, size
