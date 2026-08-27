import datetime

import pytest
from pydantic import ValidationError

from app.core.errors import EmailAlreadyExistsError
from app.models.role import RoleName
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.services import auth_service


def _valid_signup_payload(**overrides) -> SignupRequest:
    data = dict(
        first_name="Asha",
        last_name="Singh",
        email="asha.singh@dayflow.dev",
        password="StrongPass!234",
        department_id=1,
        designation_id=1,
        joining_date=datetime.date(2026, 9, 1),
    )
    data.update(overrides)
    return SignupRequest(**data)


def test_signup_creates_employee_role_user(db_session):
    payload = _valid_signup_payload()
    user, raw_token = auth_service.signup(db_session, payload)
    db_session.commit()

    assert user.user_id is not None
    assert user.role.name == RoleName.EMPLOYEE.value
    assert user.is_active is True
    assert user.is_email_verified is False
    assert user.employee_code.startswith("AS2026")
    assert len(raw_token) > 20


def test_signup_rejects_duplicate_email(db_session):
    payload = _valid_signup_payload()
    auth_service.signup(db_session, payload)
    db_session.commit()

    with pytest.raises(EmailAlreadyExistsError):
        auth_service.signup(db_session, _valid_signup_payload())


def test_signup_ignores_client_supplied_role(db_session):
    """Even if a client stuffs a `role` key into the JSON body, Pydantic
    silently drops it because SignupRequest has no `role` field, and the
    service layer always forces EMPLOYEE regardless."""
    raw_payload = {
        "first_name": "Vik",
        "last_name": "Rao",
        "email": "vik.rao@dayflow.dev",
        "password": "StrongPass!234",
        "department_id": 1,
        "designation_id": 1,
        "joining_date": "2026-09-01",
        "role": "ADMIN",  # attempted privilege escalation
    }
    payload = SignupRequest(**raw_payload)
    assert not hasattr(payload, "role")

    user, _ = auth_service.signup(db_session, payload)
    db_session.commit()
    assert user.role.name == RoleName.EMPLOYEE.value


def test_signup_generates_unique_sequential_employee_codes(db_session):
    user1, _ = auth_service.signup(db_session, _valid_signup_payload(email="a1@dayflow.dev"))
    db_session.commit()
    user2, _ = auth_service.signup(
        db_session,
        _valid_signup_payload(email="a2@dayflow.dev", first_name="Asha", last_name="Singh"),
    )
    db_session.commit()

    assert user1.employee_code != user2.employee_code


@pytest.mark.parametrize(
    "weak_password",
    [
        "short1!",       # too short
        "alllowercase1!",  # no uppercase
        "ALLUPPERCASE1!",  # no lowercase
        "NoDigitsHere!",   # no digit
        "NoSpecial1234",   # no special char
    ],
)
def test_signup_rejects_weak_passwords(weak_password):
    with pytest.raises(ValidationError):
        _valid_signup_payload(password=weak_password)
