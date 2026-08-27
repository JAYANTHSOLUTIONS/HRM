import io

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin_or_hr
from app.models.auth import User
from app.schemas.document import DocumentOut, DocumentListOut, ProfilePictureOut
from app.services import document_service, profile_picture_service
from app.services.storage_service import get_profile_image_storage
from app.services.employee_service import get_employee_or_404
from app.exceptions import forbidden, not_found

router = APIRouter(tags=["Documents"])


def _can_manage_employee(current_user: User, employee_id: int) -> bool:
    """Admin/HR can act on any employee; an EMPLOYEE may only act on themself."""
    role = current_user.role_name.upper()
    if role in ("ADMIN", "HR"):
        return True
    return current_user.employee is not None and current_user.employee.employee_id == employee_id


def _view_download_urls(document_id: int) -> tuple[str, str]:
    return (f"/api/v1/documents/{document_id}/view", f"/api/v1/documents/{document_id}/download")


@router.post("/employees/{employee_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    employee_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_employee(current_user, employee_id):
        raise forbidden("You may only upload documents for your own profile.")

    content = await file.read()
    doc = document_service.upload_document(
        db,
        employee_id=employee_id,
        document_type=document_type,
        original_filename=file.filename or "upload",
        declared_content_type=file.content_type or "",
        content=content,
        uploaded_by_user_id=current_user.user_id,
    )
    view_url, download_url = _view_download_urls(doc.document_id)
    return DocumentOut.from_model(doc, view_url, download_url)


@router.get("/employees/{employee_id}/documents", response_model=DocumentListOut)
def list_documents(
    employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if not _can_manage_employee(current_user, employee_id):
        raise forbidden("You may only view documents for your own profile.")
    get_employee_or_404(db, employee_id)
    docs = document_service.list_documents_for_employee(db, employee_id)
    items = []
    for d in docs:
        view_url, download_url = _view_download_urls(d.document_id)
        items.append(DocumentOut.from_model(d, view_url, download_url))
    return {"items": items}


@router.get("/documents/{document_id}/view")
def view_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Authenticated streaming endpoint. Serves the file inline with the
    correct Content-Type so the frontend can render images/PDFs directly."""
    doc = document_service.get_document_or_404(db, document_id)
    if not document_service.can_access_document(current_user, doc):
        raise forbidden("You are not authorized to view this document.")

    content = document_service.read_document_bytes(doc)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = document_service.get_document_or_404(db, document_id)
    if not document_service.can_access_document(current_user, doc):
        raise forbidden("You are not authorized to download this document.")

    content = document_service.read_document_bytes(doc)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin_or_hr)):
    document_service.delete_document(db, document_id=document_id, deleted_by_user_id=user.user_id)
    return None


# ---------------------------------------------------------------------------
# Profile picture
# ---------------------------------------------------------------------------

@router.post("/employees/{employee_id}/profile-picture", response_model=ProfilePictureOut)
async def upload_profile_picture(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_employee(current_user, employee_id):
        raise forbidden("You may only update your own profile picture.")

    content = await file.read()
    employee = profile_picture_service.upload_profile_picture(
        db, employee_id=employee_id, original_filename=file.filename or "avatar.jpg",
        declared_content_type=file.content_type or "", content=content,
        uploaded_by_user_id=current_user.user_id,
    )
    return ProfilePictureOut(
        employee_id=employee.employee_id,
        profile_picture_url=f"/api/v1/employees/{employee.employee_id}/profile-picture/raw",
    )


@router.get("/employees/{employee_id}/profile-picture/raw")
def get_profile_picture_raw(employee_id: int, db: Session = Depends(get_db)):
    """
    Unauthenticated by design so a plain <img src="..."> works without the
    frontend needing to attach an Authorization header for image tags.
    Storage keys are random/opaque; for stricter privacy in production, swap
    this for S3 presigned URLs (see services/storage_service.S3Storage).
    """
    employee = get_employee_or_404(db, employee_id)
    if not employee.profile_picture_url:
        raise not_found("Profile picture")

    storage = get_profile_image_storage()
    if not storage.exists(employee.profile_picture_url):
        raise not_found("Profile picture file")

    content = storage.read(employee.profile_picture_url)
    ext = employee.profile_picture_url.rsplit(".", 1)[-1].lower()
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "application/octet-stream"
    )
    return StreamingResponse(io.BytesIO(content), media_type=media_type)
