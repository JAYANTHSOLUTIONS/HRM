from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RefreshToken(Base):
    """
    Stores only the SHA-256 hash of the refresh token, never the raw value.
    Supports rotation: each refresh issues a new row and revokes the old one.
    """
    __tablename__ = "refresh_tokens"

    token_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Chain of rotation: points at the token this one replaced, if any.
    replaced_by_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken token_id={self.token_id} user_id={self.user_id}>"
