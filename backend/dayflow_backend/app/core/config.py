"""
Application configuration, loaded from environment variables / .env.

NOTE: JWT_SECRET_KEY and JWT_ALGORITHM MUST be identical to whatever
Part 1 (auth module) uses to sign access tokens, since Part 2 only
*verifies* tokens issued by Part 1 — it never issues its own.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "development"

    # Database
    DATABASE_URL: str = "mysql+pymysql://dayflow_user:change_me@localhost:3306/dayflow_hrms"

    # JWT (shared contract with Part 1)
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # File storage
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_DOCUMENTS_DIR: str = "storage/documents"
    LOCAL_PROFILE_IMAGES_DIR: str = "storage/profile-images"
    MAX_DOCUMENT_SIZE_MB: int = 10
    MAX_IMAGE_SIZE_MB: int = 5

    # S3
    S3_BUCKET: str = "dayflow-hrms-documents"
    S3_REGION: str = "ap-south-1"
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "no-reply@dayflow.dev"
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = False

    # Cloudflare Turnstile CAPTCHA
    TURNSTILE_ENABLED: bool = True
    TURNSTILE_SITE_KEY: str = "1x00000000000000000000AA"
    TURNSTILE_SECRET_KEY: str = "1x000000000000000000000000000000AA"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8443"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_document_size_bytes(self) -> int:
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
