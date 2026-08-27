"""
Idempotent role-seeding script. The Alembic migration already inserts the
three roles on first deploy; this script exists as a convenience for
re-seeding a database that was created out-of-band (e.g. `Base.metadata.create_all`
in a throwaway dev/test environment) without running full migrations.

Usage:
    python -m scripts.seed_roles
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.role import Role, RoleName


def seed_roles() -> None:
    db = SessionLocal()
    try:
        for role_name in RoleName:
            existing = db.execute(select(Role).where(Role.name == role_name.value)).scalar_one_or_none()
            if existing is None:
                db.add(Role(name=role_name.value))
        db.commit()
        print("Roles seeded: ADMIN, HR, EMPLOYEE")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
