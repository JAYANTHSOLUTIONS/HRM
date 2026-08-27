import datetime as dt
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app import models  # noqa: E402  (registers all tables on Base.metadata)
from app.assumed_existing.auth import User, UserRole  # noqa: E402
from app.assumed_existing.org_models import Department, Designation, Employee  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.leave import LeaveBalance, LeaveType  # noqa: E402


@pytest.fixture()
def tmp_storage_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("LOCAL_STORAGE_ROOT", d)
        get_settings.cache_clear()
        yield d
        get_settings.cache_clear()


@pytest.fixture()
def db_session(tmp_storage_dir):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    app.dependency_overrides.clear()


def _make_token(user_id: int) -> str:
    payload = {"sub": str(user_id)}
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture()
def seed_employee(db_session):
    """Employee #1 — the primary test actor."""
    dept = Department(department_name="Engineering")
    designation = Designation(title="Software Engineer")
    db_session.add_all([dept, designation])
    db_session.flush()

    user = User(email="asha@dayflow.dev", hashed_password="x", role=UserRole.EMPLOYEE, is_active=1)
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        user_id=user.user_id,
        employee_code="CCAS20260002",
        first_name="Asha",
        last_name="Singh",
        email="asha@dayflow.dev",
        joining_date=dt.date(2026, 2, 1),
        department_id=dept.department_id,
        designation_id=designation.designation_id,
    )
    db_session.add(employee)

    leave_type = LeaveType(name="Paid Leave", is_balance_tracked=True, requires_attachment=False)
    db_session.add(leave_type)
    db_session.flush()

    balance = LeaveBalance(
        employee_id=employee.employee_id,
        leave_type_id=leave_type.leave_type_id,
        year=dt.date.today().year,
        allocated_days=24,
        used_days=0,
    )
    db_session.add(balance)
    db_session.commit()

    return {"user": user, "employee": employee, "leave_type": leave_type}


@pytest.fixture()
def seed_second_employee(db_session):
    """A second, unrelated employee — used to prove data isolation."""
    user = User(email="ravi@dayflow.dev", hashed_password="x", role=UserRole.EMPLOYEE, is_active=1)
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        user_id=user.user_id,
        employee_code="CCRK20260003",
        first_name="Ravi",
        last_name="Kumar",
        email="ravi@dayflow.dev",
        joining_date=dt.date(2026, 3, 1),
    )
    db_session.add(employee)
    db_session.commit()
    return {"user": user, "employee": employee}


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def auth_headers(seed_employee):
    token = _make_token(seed_employee["user"].user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_second(seed_second_employee):
    token = _make_token(seed_second_employee["user"].user_id)
    return {"Authorization": f"Bearer {token}"}
