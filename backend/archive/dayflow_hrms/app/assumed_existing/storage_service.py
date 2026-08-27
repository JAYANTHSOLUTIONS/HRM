"""
======================================================================
ASSUMED PART 2 CODE (shared storage service) — merge, don't duplicate
======================================================================
The spec is explicit: "Store actual image using the document/storage
service from PART 2" and "Never allow path traversal" / "Generate
storage keys server-side." If Part 2 already has a StorageService with
this shape, delete this file and import that one. If it doesn't exist
yet, this implementation is safe to keep as-is (local + pluggable S3).

Design:
  - Callers never build filesystem paths themselves. They call
    `storage.save(...)` and get back an opaque `storage_key`
    (e.g. "documents/3f9e2b7c-....pdf") which is what gets persisted
    in MySQL — never an absolute path, never a client-supplied name.
  - `storage.open_stream(storage_key)` re-derives the real path from the
    key, always joined under the storage root, and refuses to resolve
    outside of it (blocks "../../etc/passwd" style traversal even if a
    corrupted/tampered key ever reached this layer).
======================================================================
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Tuple

from app.core.config import get_settings

settings = get_settings()


class StorageError(Exception):
    pass


class LocalStorageService:
    """Development backend: writes under LOCAL_STORAGE_ROOT."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.LOCAL_STORAGE_ROOT).resolve()
        (self.root / settings.LOCAL_DOCUMENTS_SUBDIR).mkdir(parents=True, exist_ok=True)
        (self.root / settings.LOCAL_PROFILE_IMAGES_SUBDIR).mkdir(parents=True, exist_ok=True)

    def _safe_path(self, storage_key: str) -> Path:
        # storage_key is always server-generated (folder + uuid + extension),
        # but we still resolve-and-verify to defend in depth against any
        # future code path that forgets that invariant.
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise StorageError("Resolved path escapes storage root")
        return candidate

    def save(self, file_obj: BinaryIO, folder: str, extension: str) -> str:
        """Writes file_obj to disk under a server-generated name and
        returns the storage_key to persist in the DB."""
        extension = extension.lstrip(".").lower()
        filename = f"{uuid.uuid4().hex}.{extension}"
        storage_key = f"{folder}/{filename}"
        dest = self._safe_path(storage_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        file_obj.seek(0)
        with open(dest, "wb") as out:
            out.write(file_obj.read())
        return storage_key

    def open_stream(self, storage_key: str) -> Tuple[BinaryIO, int]:
        path = self._safe_path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        size = path.stat().st_size
        return open(path, "rb"), size

    def delete(self, storage_key: str) -> None:
        path = self._safe_path(storage_key)
        if path.is_file():
            os.remove(path)


class S3StorageService:
    """
    Production backend. Requires boto3. Intentionally thin — this is the
    interface the rest of Part 3 depends on; wire up real credentials /
    bucket policy in Part 2's infra config, not here.
    """

    def __init__(self):
        import boto3  # local import so local dev doesn't require boto3

        self.bucket = settings.S3_BUCKET
        kwargs = {}
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        if settings.S3_REGION:
            kwargs["region_name"] = settings.S3_REGION
        self.client = boto3.client("s3", **kwargs)

    def save(self, file_obj: BinaryIO, folder: str, extension: str) -> str:
        extension = extension.lstrip(".").lower()
        storage_key = f"{folder}/{uuid.uuid4().hex}.{extension}"
        file_obj.seek(0)
        self.client.upload_fileobj(file_obj, self.bucket, storage_key)
        return storage_key

    def open_stream(self, storage_key: str):
        obj = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        return obj["Body"], obj["ContentLength"]

    def delete(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)


def get_storage_service():
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageService()
    return LocalStorageService()
