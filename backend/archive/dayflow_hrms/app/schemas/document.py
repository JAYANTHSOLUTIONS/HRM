from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: int
    document_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    view_url: str
    download_url: str


class DocumentListOut(BaseModel):
    items: List[DocumentOut]


class ProfilePictureOut(BaseModel):
    profile_picture_url: str
