import datetime

import pytest

from app.core.errors import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
)
from app.schemas.auth import SignupRequest
from app.services import auth_service


def _make_verified_user(db_session, email="asha.singh@dayflow.dev", password="StrongPass!234"):
    payload = SignupRequest(
        first_name="Asha",
        last_name="Singh",
        email=email,
        password=password,
        department_id=1,
        designation_id=1,
        joining_date=datetime.date(2026, 9, 1),
    )
    user, raw_token = auth_service.signup(db_session, payload)
    db_session.commit()
    auth_service.verify_email(db_session, raw_token)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_succeeds_with_correct_credentials(db_session):
    user = _make_verified_user(db_session)
    authenticated = auth_service.authenticate_user(db_session, user.email, "StrongPass!234")
    assert authenticated.user_id == user.user_id
    assert authenticated.failed_login_attempts == 0


def test_login_fails_with_wrong_password(db_session):
    user = _make_verified_user(db_session)
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, user.email, "WrongPassword!123")


def test_login_fails_for_unknown_email_same_error_as_wrong_password(db_session):
    """Ensures no user-enumeration via distinct error types."""
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, "nobody@dayflow.dev", "whatever123!A")


def test_login_blocked_when_email_not_verified(db_session):
    payload = SignupRequest(
        first_name="Vik",
        last_name="Rao",
        email="vik.rao@dayflow.dev",
        password="StrongPass!234",
        department_id=1,
        designation_id=1,
        joining_date=datetime.date(2026, 9, 1),
    )
    user, _ = auth_service.signup(db_session, payload)
    db_session.commit()

    with pytest.raises(EmailNotVerifiedError):
        auth_service.authenticate_user(db_session, user.email, "StrongPass!234")


def test_account_locks_after_max_failed_attempts(db_session):
    from app.core.config import settings

    user = _make_verified_user(db_session, email="lockout@dayflow.dev")

    for _ in range(settings.FAILED_LOGIN_MAX_ATTEMPTS - 1):
        with pytest.raises(InvalidCredentialsError):
            auth_service.authenticate_user(db_session, user.email, "WrongPassword!123")
        db_session.commit()

    # The final failing attempt should trip the lock.
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, user.email, "WrongPassword!123")
    db_session.commit()

    # Now even the CORRECT password should be rejected because of the lock.
    with pytest.raises(AccountLockedError):
        auth_service.authenticate_user(db_session, user.email, "StrongPass!234")


def test_successful_login_resets_failed_attempts(db_session):
    user = _make_verified_user(db_session, email="reset@dayflow.dev")

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, user.email, "WrongPassword!123")
    db_session.commit()

    authenticated = auth_service.authenticate_user(db_session, user.email, "StrongPass!234")
    assert authenticated.failed_login_attempts == 0
    assert authenticated.locked_until is None
