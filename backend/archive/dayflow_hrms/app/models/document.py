from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """
    Metadata only — the actual bytes live in whatever StorageService
    backend is configured (local disk in dev, S3-compatible in prod).
    `storage_key` is server-generated (see storage_service.save) and is
    NEVER a filesystem path or a client-supplied filename.
    """

    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False, index=True)

    document_type = Column(String(100), nullable=False)  # e.g. "ID_PROOF", "SICK_CERTIFICATE"
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    size_bytes = Column(Integer, nullable=False)

    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
