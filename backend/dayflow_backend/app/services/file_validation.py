"""
Defense-in-depth upload validation: extension + declared MIME type + actual
file signature (magic bytes) must ALL agree before a file is accepted.
Never trust Content-Type alone (spec section 7).
"""
import imghdr
from app.exceptions import bad_request

ALLOWED_DOCUMENT_EXT = {"pdf", "doc", "docx"}
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}

_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

# Magic-byte signatures we check against the *actual* file content.
_SIGNATURES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],  # bytes 8-12 == b"WEBP", checked separately
    # DOC/DOCX are ZIP (docx) or OLE2 (doc) containers — checked below.
    "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "docx": [b"PK\x03\x04"],
}

_DANGEROUS_EXT = {"exe", "bat", "sh", "js", "html", "htm", "svg", "cmd", "msi", "com", "vbs", "ps1"}


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _signature_matches(kind: str, header: bytes) -> bool:
    if kind == "webp":
        return header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    for sig in _SIGNATURES.get(kind, []):
        if header.startswith(sig):
            return True
    return False


def validate_upload(
    filename: str,
    declared_content_type: str,
    header_bytes: bytes,
    file_size_bytes: int,
    max_size_bytes: int,
    allowed_extensions: set[str],
) -> tuple[str, str]:
    """
    Returns (extension, resolved_mime_type) or raises AppError(400).
    `header_bytes` should be at least the first 16 bytes of the file.
    """
    ext = _extension_of(filename)

    if ext in _DANGEROUS_EXT:
        raise bad_request(
            f"File type '.{ext}' is not permitted for security reasons.",
            code="UNSUPPORTED_FILE_TYPE",
        )

    if ext not in allowed_extensions:
        raise bad_request(
            f"File type '.{ext}' is not supported. Allowed: {', '.join(sorted(allowed_extensions))}.",
            code="UNSUPPORTED_FILE_TYPE",
        )

    if file_size_bytes <= 0:
        raise bad_request("Uploaded file is empty.", code="EMPTY_FILE")

    if file_size_bytes > max_size_bytes:
        raise bad_request(
            f"File exceeds the maximum allowed size of {max_size_bytes // (1024*1024)} MB.",
            code="FILE_TOO_LARGE",
        )

    expected_mime = _MIME_BY_EXT[ext]

    # Content-Type sanity check (soft — declared type is informative only,
    # the magic-byte check below is authoritative).
    if declared_content_type and not declared_content_type.startswith(expected_mime.split("/")[0]):
        # allow octet-stream from generic clients, but nothing wildly mismatched
        if declared_content_type not in (expected_mime, "application/octet-stream"):
            raise bad_request(
                "Declared file type does not match the file extension.",
                code="MIME_MISMATCH",
            )

    sig_kind = "docx" if ext == "docx" else ("doc" if ext == "doc" else ext)
    if sig_kind in _SIGNATURES or sig_kind == "webp":
        if not _signature_matches(sig_kind, header_bytes):
            raise bad_request(
                "The file's actual content does not match its declared type "
                "(failed file-signature check).",
                code="FILE_SIGNATURE_MISMATCH",
            )
    else:
        # Fallback for any type not in our signature table.
        guessed = imghdr.what(None, h=header_bytes)
        if ext in ALLOWED_IMAGE_EXT and guessed is None:
            raise bad_request("Could not verify image contents.", code="FILE_SIGNATURE_MISMATCH")

    return ext, expected_mime
