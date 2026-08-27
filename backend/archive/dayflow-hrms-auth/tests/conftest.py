"""
Test configuration.

Uses an in-memory SQLite database for speed/isolation in unit tests, even
though production runs on MySQL only. This is safe here because none of
the auth logic relies on MySQL-specific SQL — it's all SQLAlchemy ORM.
Set RUN_AGAINST_MYSQL=1 and provide TEST_DATABASE_URL to instead run the
same suite against a real MySQL instance for full parity confidence
before release.
"""
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "test-turnstile-secret")
os.environ.setdefault("CAPTCHA_BYPASS", "true")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_EMAIL", "test@dayflow.dev")
os.environ.setdefault("SMTP_PASSWORD", "unused")

from app.db.base import Base  # noqa: E402
from app.models.role import Role, RoleName  # noqa: E402


@pytest.fixture()
def db_session():
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    engine_kwargs = {}
    if test_db_url.startswith("sqlite"):
        engine_kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    engine = create_engine(test_db_url, **engine_kwargs)

    if test_db_url.startswith("sqlite"):
        # Enforce FK constraints in SQLite (off by default) to mirror MySQL/InnoDB behavior.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    for role_name in RoleName:
        session.add(Role(name=role_name.value))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _no_real_email(monkeypatch):
    """Prevent any test from attempting a real SMTP connection."""
    import app.services.email_service as email_service

    sent_emails = []

    def _fake_send_email(to_email, subject, html_body, text_body=None):
        sent_emails.append({"to": to_email, "subject": subject, "html_body": html_body})

    monkeypatch.setattr(email_service, "send_email", _fake_send_email)
    return sent_emails
