from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: int
    employee_id: int
    document_type: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    uploaded_by: int
    uploaded_at: datetime
    view_url: str
    download_url: str

    @classmethod
    def from_model(cls, doc, view_url: str, download_url: str):
        return cls(
            document_id=doc.document_id,
            employee_id=doc.employee_id,
            document_type=doc.document_type,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.created_at,
            view_url=view_url,
            download_url=download_url,
        )


class DocumentListOut(BaseModel):
    items: list[DocumentOut]


class ProfilePictureOut(BaseModel):
    employee_id: int
    profile_picture_url: str
