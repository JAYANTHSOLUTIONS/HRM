"""
Centralized application configuration.

All environment-driven values are loaded here via pydantic-settings so the
rest of the codebase never touches os.environ directly. This keeps secrets
and tunables in one auditable place.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- Application ----
    APP_NAME: str = "Dayflow HRMS Auth Service"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database ----
    DATABASE_URL: str

    # ---- JWT ----
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ---- Turnstile CAPTCHA ----
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_VERIFY_URL: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    CAPTCHA_BYPASS: bool = False

    # ---- SMTP ----
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_NAME: str = "Dayflow HRMS"

    # ---- Frontend / CORS ----
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # ---- Security policy ----
    FAILED_LOGIN_MAX_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
