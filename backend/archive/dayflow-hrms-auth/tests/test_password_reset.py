import datetime
import re

import pytest

from app.core.errors import InvalidCredentialsError, TokenExpiredOrInvalidError
from app.schemas.auth import SignupRequest
from app.services import auth_service


def _make_verified_user(db_session, email="asha.singh@dayflow.dev"):
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
    return user


def _extract_otp(html_body: str) -> str:
    match = re.search(r"<h2>(\d{6})</h2>", html_body)
    assert match, "OTP not found in email body"
    return match.group(1)


def test_forgot_password_sends_otp_for_existing_user(db_session, _no_real_email):
    user = _make_verified_user(db_session)
    auth_service.request_password_reset(db_session, user.email)
    db_session.commit()

    assert len(_no_real_email) == 1
    assert _no_real_email[0]["to"] == user.email


def test_forgot_password_silent_for_unknown_email(db_session, _no_real_email):
    """Must not reveal account existence — no email sent, no error raised."""
    auth_service.request_password_reset(db_session, "nobody@dayflow.dev")
    db_session.commit()
    assert len(_no_real_email) == 0


def test_reset_password_with_valid_otp_succeeds(db_session, _no_real_email):
    user = _make_verified_user(db_session)
    auth_service.request_password_reset(db_session, user.email)
    db_session.commit()
    otp = _extract_otp(_no_real_email[0]["html_body"])

    auth_service.reset_password(db_session, email=user.email, otp_code=otp, new_password="NewStrongPass!987")
    db_session.commit()

    # Old password should no longer work; new one should.
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, user.email, "StrongPass!234")
    authenticated = auth_service.authenticate_user(db_session, user.email, "NewStrongPass!987")
    assert authenticated.user_id == user.user_id


def test_reset_password_with_wrong_otp_fails(db_session, _no_real_email):
    user = _make_verified_user(db_session)
    auth_service.request_password_reset(db_session, user.email)
    db_session.commit()

    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.reset_password(db_session, email=user.email, otp_code="000000", new_password="NewStrongPass!987")


def test_reset_password_otp_is_single_use(db_session, _no_real_email):
    user = _make_verified_user(db_session)
    auth_service.request_password_reset(db_session, user.email)
    db_session.commit()
    otp = _extract_otp(_no_real_email[0]["html_body"])

    auth_service.reset_password(db_session, email=user.email, otp_code=otp, new_password="NewStrongPass!987")
    db_session.commit()

    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.reset_password(db_session, email=user.email, otp_code=otp, new_password="AnotherPass!555")


def test_reset_password_revokes_existing_refresh_tokens(db_session, _no_real_email):
    user = _make_verified_user(db_session)
    _, raw_refresh = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    auth_service.request_password_reset(db_session, user.email)
    db_session.commit()
    otp = _extract_otp(_no_real_email[0]["html_body"])

    auth_service.reset_password(db_session, email=user.email, otp_code=otp, new_password="NewStrongPass!987")
    db_session.commit()

    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh)


def test_change_password_requires_correct_current_password(db_session):
    user = _make_verified_user(db_session)
    with pytest.raises(InvalidCredentialsError):
        auth_service.change_password(db_session, user, "WrongCurrent!123", "NewStrongPass!987")


def test_change_password_succeeds_and_revokes_sessions(db_session):
    user = _make_verified_user(db_session)
    _, raw_refresh = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    auth_service.change_password(db_session, user, "StrongPass!234", "NewStrongPass!987")
    db_session.commit()

    authenticated = auth_service.authenticate_user(db_session, user.email, "NewStrongPass!987")
    assert authenticated.user_id == user.user_id

    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh)
