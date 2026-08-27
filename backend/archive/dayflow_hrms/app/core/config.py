"""
Application configuration.

NOTE: If PART 1 already defines a settings/config module, DELETE this file
and point the imports in this package at your existing one instead. The
values below (DB URL, JWT secret, storage backend) must be the SAME values
already used by PART 1 / PART 2 — Part 3 does not introduce a second
source of truth for any of these.
"""
import os
from functools import lru_cache


class Settings:
    """
    Values are read from the environment in __init__ (not as class-body
    constants) so that `get_settings.cache_clear()` + a changed env var
    (as tests do via monkeypatch) actually takes effect on the next call.
    """

    def __init__(self) -> None:
        # --- Database (SAME MySQL database as Part 1 / Part 2) ---
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://dayflow:dayflow@localhost:3306/dayflow_hrms",
        )

        # --- JWT (SAME auth system as Part 1) ---
        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

        # --- File storage ---
        # "local" for development, "s3" for production. The StorageService
        # abstraction in app/assumed_existing/storage_service.py hides this
        # choice from every router/service in Part 3.
        self.STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
        self.LOCAL_STORAGE_ROOT: str = os.getenv(
            "LOCAL_STORAGE_ROOT", os.path.join(os.getcwd(), "storage")
        )
        self.LOCAL_DOCUMENTS_SUBDIR: str = "documents"
        self.LOCAL_PROFILE_IMAGES_SUBDIR: str = "profile-images"

        self.S3_BUCKET: str = os.getenv("S3_BUCKET", "")
        self.S3_REGION: str = os.getenv("S3_REGION", "")
        self.S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")  # for S3-compatible providers

        # --- Upload limits ---
        self.MAX_PROFILE_PICTURE_MB: int = 5
        self.MAX_DOCUMENT_MB: int = 15

        self.ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
        self.ALLOWED_DOCUMENT_MIME_TYPES = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        # Working days used for weekly attendance summaries when the org
        # calendar service (if any) is not wired up.
        self.DEFAULT_WORKING_DAYS_PER_WEEK: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
