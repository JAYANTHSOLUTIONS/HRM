import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OTPPurpose(str, enum.Enum):
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"


class OTP(Base):
    """
    Generic OTP store, used by the password-reset flow (and available for
    email verification if a project decides to use OTP instead of the
    link-based token flow).

    Only the SHA-256 hash of the 6-digit code is ever persisted.
    """
    __tablename__ = "otps"

    otp_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    purpose: Mapped[str] = mapped_column(Enum(OTPPurpose, native_enum=False, length=30), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="otps")

    def __repr__(self) -> str:
        return f"<OTP otp_id={self.otp_id} user_id={self.user_id} purpose={self.purpose}>"
