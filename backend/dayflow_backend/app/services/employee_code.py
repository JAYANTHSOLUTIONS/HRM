"""
employee_code format (per wireframe note):
CC + first-two-letters-of-first-name + first-two-letters-of-last-name
+ year-of-joining + serial-number-of-joining-that-year (4 digits).
Example: CCAS20260001
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auth import User


def generate_employee_code(db: Session, first_name: str, last_name: str, joining_year: int) -> str:
    initials = (first_name[:2] + last_name[:2]).upper().ljust(4, "X")
    prefix = f"CC{initials}{joining_year}"

    count = (
        db.query(func.count(User.user_id))
        .filter(User.employee_code.like(f"{prefix}%"))
        .scalar()
    ) or 0
    serial = str(count + 1).zfill(4)
    return f"{prefix}{serial}"
