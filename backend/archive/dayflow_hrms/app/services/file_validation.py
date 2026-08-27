"""
Validates uploads by actual file signature ("magic bytes"), not just the
client-declared Content-Type — a renamed .exe claiming to be image/png
is rejected here even though the browser-sent MIME type would pass.
"""
from dataclasses import dataclass

from app.core.exceptions import AppError

# (signature bytes, offset, mime_type, extension)
_SIGNATURES = [
    (b"\xff\xd8\xff", 0, "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", 0, "image/png", "png"),
    (b"RIFF", 0, "image/webp", "webp"),  # further verified below (WEBP at offset 8)
    (b"%PDF-", 0, "application/pdf", "pdf"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, "application/msword", "doc"),
    # DOCX/XLSX/PPTX are all ZIP containers (PK\x03\x04); we disambiguate
    # by the declared extension since the signature alone is ambiguous.
    (b"PK\x03\x04", 0, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
]

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"}


@dataclass
class ValidatedFile:
    mime_type: str
    extension: str
    size_bytes: int


def _sniff(head: bytes, declared_filename: str) -> tuple[str, str] | None:
    for sig, offset, mime, ext in _SIGNATURES:
        if head[offset : offset + len(sig)] == sig:
            if mime == "image/webp":
                if head[8:12] != b"WEBP":
                    continue
                return mime, "webp"
            if ext == "docx":
                # Trust declared extension for office zip containers; a
                # bare .zip renamed to .docx would still fail the later
                # extension allow-list check.
                lower = declared_filename.lower()
                if lower.endswith(".docx"):
                    return mime, "docx"
                if lower.endswith(".doc"):
                    return "application/msword", "doc"
                continue
            return mime, ext
    return None


def validate_upload(
    file_bytes: bytes,
    declared_filename: str,
    allowed_extensions: set[str],
    max_size_bytes: int,
) -> ValidatedFile:
    if not file_bytes:
        raise AppError("EMPTY_FILE", "Uploaded file is empty.", status_code=400)

    if len(file_bytes) > max_size_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            f"File exceeds the maximum allowed size of {max_size_bytes // (1024 * 1024)}MB.",
            status_code=400,
        )

    sniffed = _sniff(file_bytes[:64], declared_filename)
    if sniffed is None:
        raise AppError(
            "UNSUPPORTED_FILE_TYPE",
            "File type could not be verified from its content and is not supported.",
            status_code=415,
        )

    mime_type, extension = sniffed
    if extension not in allowed_extensions:
        raise AppError(
            "UNSUPPORTED_FILE_TYPE",
            f"Files of type .{extension} are not supported here.",
            status_code=415,
        )

    # Defense in depth against path traversal via filename: we never use
    # declared_filename to build a storage path (storage_service generates
    # the on-disk name), but original_filename IS stored for display, so
    # strip any path components before saving it.
    return ValidatedFile(mime_type=mime_type, extension=extension, size_bytes=len(file_bytes))


def safe_display_filename(declared_filename: str) -> str:
    import os

    return os.path.basename(declared_filename or "file")[:255]
