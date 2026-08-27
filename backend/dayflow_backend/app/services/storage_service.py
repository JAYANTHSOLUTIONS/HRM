"""
Storage abstraction: MySQL only ever stores a `storage_key` / `storage_path`
string (spec section 6). The actual bytes live on local disk in dev, and in
S3-compatible object storage in production. Swap STORAGE_BACKEND=s3 in .env
to switch — router/service code above this layer never changes.
"""
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalFilesystemStorage(StorageBackend):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Prevent path traversal: resolve and ensure it stays under base_dir.
        target = (self.base_dir / key).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError("Invalid storage key.")
        return target

    def save(self, key: str, content: bytes) -> None:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)

    def read(self, key: str) -> bytes:
        target = self._resolve(key)
        with open(target, "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        if target.exists():
            target.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()


class S3Storage(StorageBackend):
    """S3-compatible object storage for production. Requires boto3."""

    def __init__(self):
        import boto3  # imported lazily so local dev doesn't need boto3 installed

        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )

    def save(self, key: str, content: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)

    def read(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def presigned_url(self, key: str, expires_seconds: int = 300) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_seconds
        )


def get_document_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalFilesystemStorage(settings.LOCAL_DOCUMENTS_DIR)


def get_profile_image_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalFilesystemStorage(settings.LOCAL_PROFILE_IMAGES_DIR)


def generate_storage_key(employee_id: int, original_filename: str, subdir: str = "") -> str:
    """
    Never uses the original filename as the on-disk name (spec section 8).
    Example: employee_4/8f9d2a1c_resume.pdf
    """
    ext = ""
    if "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1].lower()
    unique = uuid.uuid4().hex[:12]
    safe_stub = "".join(c for c in Path(original_filename).stem if c.isalnum() or c in ("-", "_"))[:40] or "file"
    prefix = f"{subdir}/" if subdir else ""
    return f"{prefix}employee_{employee_id}/{unique}_{safe_stub}{ext}"
