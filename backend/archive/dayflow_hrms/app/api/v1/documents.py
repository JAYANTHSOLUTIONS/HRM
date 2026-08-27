from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.assumed_existing.auth import User, get_current_user
from app.assumed_existing.org_models import Employee
from app.core.database import get_db
from app.schemas.document import DocumentListOut, DocumentOut
from app.services import document_service

# Employee-scoped upload/list — matches spec section 5.
employee_documents_router = APIRouter(prefix="/api/v1/employees/me/documents", tags=["documents"])

# Top-level, id-addressed view/download — matches spec section 6.
# Deliberately NOT nested under /employees/me so that a single canonical
# link works for both the owning employee and an ADMIN/HR reviewer.
documents_router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _to_out(document, request: Request) -> DocumentOut:
    base = str(request.base_url).rstrip("/")
    return DocumentOut(
        document_id=document.document_id,
        document_type=document.document_type,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        uploaded_at=document.uploaded_at,
        view_url=f"{base}/api/v1/documents/{document.document_id}/view",
        download_url=f"{base}/api/v1/documents/{document.document_id}/download",
    )


@employee_documents_router.get("", response_model=DocumentListOut)
def list_my_documents(
    request: Request,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    documents = document_service.list_my_documents(db, employee)
    return {"items": [_to_out(d, request) for d in documents]}


@employee_documents_router.post("", response_model=DocumentOut)
async def upload_my_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    document = await document_service.upload_my_document(db, employee, document_type, file)
    return _to_out(document, request)


def _employee_or_none(user: User, db: Session) -> Employee | None:
    from app.assumed_existing.org_models import Employee as _Employee

    return db.query(_Employee).filter(_Employee.user_id == user.user_id).first()


@documents_router.get("/{document_id}/view")
def view_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = _employee_or_none(user, db)
    document, stream, size = document_service.stream_document(db, document_id, user, employee)
    return StreamingResponse(
        stream,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.original_filename}"',
            "Content-Length": str(size),
        },
    )


@documents_router.get("/{document_id}/download")
def download_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = _employee_or_none(user, db)
    document, stream, size = document_service.stream_document(db, document_id, user, employee)
    return StreamingResponse(
        stream,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"',
            "Content-Length": str(size),
        },
    )
