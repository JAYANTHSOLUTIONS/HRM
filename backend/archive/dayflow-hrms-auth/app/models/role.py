import enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleName(str, enum.Enum):
    ADMIN = "ADMIN"
    HR = "HR"
    EMPLOYEE = "EMPLOYEE"


class Role(Base):
    """
    Fixed set of roles: ADMIN, HR, EMPLOYEE.

    Seeded once via migration/seed script. Public signup is only ever
    permitted to attach RoleName.EMPLOYEE — enforced in the service layer,
    never trusted from client input.
    """
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role role_id={self.role_id} name={self.name!r}>"
