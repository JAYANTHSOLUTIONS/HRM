import datetime

import pytest

from app.core.errors import AuthenticationRequiredError, ForbiddenError, InvalidTokenError
from app.core.jwt import create_access_token
from app.dependencies.auth import get_current_user, require_role, require_roles
from app.schemas.auth import SignupRequest
from app.services import auth_service


class _FakeCredentials:
    def __init__(self, token: str):
        self.credentials = token


class _FakeRequest:
    def __init__(self):
        self.state = type("State", (), {})()


def _make_verified_user(db_session, email="asha.singh@dayflow.dev", role_name="EMPLOYEE"):
    payload = SignupRequest(
        first_name="Asha",
        last_name="Singh",
        email=email,
        password="StrongPass!234",
        department_id=1,
        designation_id=1,
        joining_date=datetime.date(2026, 9, 1),
    )
    user, raw_token = auth_service.signup(db_session, payload)
    db_session.commit()
    auth_service.verify_email(db_session, raw_token)
    db_session.commit()
    db_session.refresh(user)

    if role_name != "EMPLOYEE":
        from sqlalchemy import select

        from app.models.role import Role

        role = db_session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        user.role_id = role.role_id
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return user


def test_get_current_user_returns_user_for_valid_token(db_session):
    user = _make_verified_user(db_session)
    token = create_access_token(user_id=user.user_id, role="EMPLOYEE")

    resolved = get_current_user(_FakeRequest(), _FakeCredentials(token), db_session)
    assert resolved.user_id == user.user_id


def test_get_current_user_rejects_missing_credentials(db_session):
    with pytest.raises(AuthenticationRequiredError):
        get_current_user(_FakeRequest(), None, db_session)


def test_get_current_user_rejects_garbage_token(db_session):
    with pytest.raises(InvalidTokenError):
        get_current_user(_FakeRequest(), _FakeCredentials("not.a.jwt"), db_session)


def test_get_current_user_rejects_token_for_deleted_user(db_session):
    # A token minted for a user_id that doesn't exist in the DB.
    token = create_access_token(user_id=999999, role="EMPLOYEE")
    with pytest.raises(InvalidTokenError):
        get_current_user(_FakeRequest(), _FakeCredentials(token), db_session)


def test_require_role_allows_matching_role(db_session):
    admin = _make_verified_user(db_session, email="admin@dayflow.dev", role_name="ADMIN")
    dependency = require_role("ADMIN")
    resolved = dependency(current_user=admin)
    assert resolved.user_id == admin.user_id


def test_require_role_blocks_non_matching_role(db_session):
    employee = _make_verified_user(db_session, email="emp@dayflow.dev", role_name="EMPLOYEE")
    dependency = require_role("ADMIN")
    with pytest.raises(ForbiddenError):
        dependency(current_user=employee)


def test_require_roles_allows_any_of_the_listed_roles(db_session):
    hr_user = _make_verified_user(db_session, email="hr@dayflow.dev", role_name="HR")
    dependency = require_roles("ADMIN", "HR")
    resolved = dependency(current_user=hr_user)
    assert resolved.user_id == hr_user.user_id


def test_require_roles_blocks_role_not_in_list(db_session):
    employee = _make_verified_user(db_session, email="emp2@dayflow.dev", role_name="EMPLOYEE")
    dependency = require_roles("ADMIN", "HR")
    with pytest.raises(ForbiddenError):
        dependency(current_user=employee)
