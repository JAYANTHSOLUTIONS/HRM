"""
PART 1 owns these tables. They are mapped here (read-mostly) purely so
Part 2 can declare foreign keys / relationships and query user/role data.
Do NOT add signup/login business logic here.
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy import String, Boolean, SmallInteger, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UpdatedAtMixin


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(primary_key=True)
    role_name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id"))
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

    role: Mapped["Role"] = relationship(back_populates="users")
    employee: Mapped["Employee | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="Employee.user_id"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def role_name(self) -> str:
        return self.role.role_name if self.role else ""
