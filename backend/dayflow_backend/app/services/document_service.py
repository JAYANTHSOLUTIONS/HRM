from sqlalchemy.orm import Session, joinedload

from app.models.hr import EmployeeDocument, Employee
from app.exceptions import not_found, bad_request
from app.services.storage_service import get_document_storage, generate_storage_key
from app.services.file_validation import validate_upload, ALLOWED_DOCUMENT_EXT
from app.services.audit_service import write_audit_log
from app.core.config import get_settings

settings = get_settings()

VALID_DOCUMENT_TYPES = {
    "RESUME", "ID_PROOF", "ADDRESS_PROOF", "MEDICAL_CERTIFICATE", "JOINING_DOCUMENT", "OTHER"
}


def list_documents_for_employee(db: Session, employee_id: int) -> list[EmployeeDocument]:
    return (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee_id, EmployeeDocument.status == "ACTIVE")
        .order_by(EmployeeDocument.created_at.desc())
        .all()
    )


def get_document_or_404(db: Session, document_id: int) -> EmployeeDocument:
    doc = db.query(EmployeeDocument).filter(EmployeeDocument.document_id == document_id).first()
    if doc is None:
        raise not_found("Document")
    return doc


def upload_document(
    db: Session,
    *,
    employee_id: int,
    document_type: str,
    original_filename: str,
    declared_content_type: str,
    content: bytes,
    uploaded_by_user_id: int,
) -> EmployeeDocument:
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise not_found("Employee")

    if document_type not in VALID_DOCUMENT_TYPES:
        raise bad_request(f"document_type must be one of: {', '.join(sorted(VALID_DOCUMENT_TYPES))}")

    ext, mime_type = validate_upload(
        filename=original_filename,
        declared_content_type=declared_content_type,
        header_bytes=content[:16],
        file_size_bytes=len(content),
        max_size_bytes=settings.max_document_size_bytes,
        allowed_extensions=ALLOWED_DOCUMENT_EXT,
    )

    storage_key = generate_storage_key(employee_id, original_filename, subdir="documents")
    storage = get_document_storage()
    storage.save(storage_key, content)

    doc = EmployeeDocument(
        employee_id=employee_id,
        document_type=document_type,
        original_filename=original_filename,
        storage_path=storage_key,
        mime_type=mime_type,
        file_size_bytes=len(content),
        uploaded_by=uploaded_by_user_id,
        status="ACTIVE",
    )
    db.add(doc)
    db.flush()

    write_audit_log(
        db, actor_user_id=uploaded_by_user_id, action="DOCUMENT_UPLOADED",
        target_entity="employee_documents", target_id=doc.document_id,
        new_values={"document_type": document_type, "original_filename": original_filename},
    )

    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, *, document_id: int, deleted_by_user_id: int) -> None:
    doc = get_document_or_404(db, document_id)
    doc.status = "ARCHIVED"
    db.flush()

    write_audit_log(
        db, actor_user_id=deleted_by_user_id, action="DOCUMENT_DELETED",
        target_entity="employee_documents", target_id=doc.document_id,
        old_values={"status": "ACTIVE"}, new_values={"status": "ARCHIVED"},
    )
    db.commit()


def read_document_bytes(doc: EmployeeDocument) -> bytes:
    storage = get_document_storage()
    if not storage.exists(doc.storage_path):
        raise not_found("Document file")
    return storage.read(doc.storage_path)


def can_access_document(current_user, doc: EmployeeDocument) -> bool:
    """ADMIN/HR can access any document; an EMPLOYEE may only access their own."""
    role = current_user.role_name.upper()
    if role in ("ADMIN", "HR"):
        return True
    employee = current_user.employee
    return employee is not None and employee.employee_id == doc.employee_id
