from __future__ import annotations
from datetime import datetime

from sqlalchemy import String, Boolean, TIMESTAMP, ForeignKey, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(1000))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
