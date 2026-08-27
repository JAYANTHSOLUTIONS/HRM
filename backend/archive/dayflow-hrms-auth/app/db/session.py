"""
SQLAlchemy engine + session management for MySQL (InnoDB, utf8mb4).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# pool_pre_ping avoids stale-connection errors after MySQL idle timeouts.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=settings.DEBUG,
    connect_args={"charset": "utf8mb4"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    FastAPI dependency that yields a DB session and guarantees it is closed.
    Parts 2 and 3 should import this same dependency for consistency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
