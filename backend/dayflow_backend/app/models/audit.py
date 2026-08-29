from __future__ import annotations
from datetime import datetime

from sqlalchemy import String, TIMESTAMP, ForeignKey, BigInteger, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_log_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target_entity: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
