"""
SQLAlchemy engine / session.

NOTE: If PART 1 / PART 2 already define `Base`, `engine`, and `get_db`,
DELETE this file and import theirs everywhere instead
(`from app.core.database import Base, get_db` becomes whatever your real
module path is). Every model in this deliverable (app/models/*.py) must
bind to the SAME `Base` as your existing `employees`, `users`,
`departments`, and `designations` tables, or SQLAlchemy will not see them
as part of the same metadata / the same MySQL schema.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
