"""
Test fixtures use an in-memory SQLite database (fast, no external deps).
MySQL-only features (the leave-overlap triggers defined in Part 1's
dayflow_schema.sql) are NOT exercised here — those require running the
tests against real MySQL. Everything else (RBAC, validation, transactions,
computed fields) is fully covered against SQLite.
"""
import os
import sys
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.auth import Role, User
from app.models.hr import Department, Designation, Employee
from app.models.leave import LeaveType

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed(db_session):
    admin_role = Role(role_name="ADMIN")
    hr_role = Role(role_name="HR")
    employee_role = Role(role_name="EMPLOYEE")
    db_session.add_all([admin_role, hr_role, employee_role])
    db_session.flush()

    dept = Department(department_name="Engineering")
    designation = Designation(title="Software Engineer")
    db_session.add_all([dept, designation])
    db_session.flush()

    admin_user = User(employee_code="CCAD20260001", email="admin@dayflow.dev",
                       password_hash="x", role_id=admin_role.role_id, is_active=True)
    hr_user = User(employee_code="CCHR20260001", email="hr@dayflow.dev",
                    password_hash="x", role_id=hr_role.role_id, is_active=True)
    emp_user = User(employee_code="CCEM20260001", email="employee@dayflow.dev",
                     password_hash="x", role_id=employee_role.role_id, is_active=True)
    db_session.add_all([admin_user, hr_user, emp_user])
    db_session.flush()

    employee = Employee(
        user_id=emp_user.user_id, employee_code=emp_user.employee_code,
        first_name="Asha", last_name="Singh", department_id=dept.department_id,
        designation_id=designation.designation_id, joining_date=date(2026, 2, 1),
        employment_status="ACTIVE", employment_type="FULL_TIME",
    )
    db_session.add(employee)
    db_session.flush()

    paid_leave = LeaveType(name="Paid Time Off", is_balance_tracked=True, requires_attachment=False, is_active=True)
    db_session.add(paid_leave)
    db_session.commit()

    return {
        "admin_user": admin_user, "hr_user": hr_user, "emp_user": emp_user,
        "employee": employee, "department": dept, "designation": designation,
        "leave_type": paid_leave,
    }


def auth_header(user: User) -> dict:
    token = create_access_token(subject=str(user.user_id))
    return {"Authorization": f"Bearer {token}"}
