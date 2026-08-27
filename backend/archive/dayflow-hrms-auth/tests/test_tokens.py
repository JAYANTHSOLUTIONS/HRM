import datetime

import pytest

from app.core.errors import TokenExpiredOrInvalidError
from app.core.jwt import decode_access_token
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


def test_issue_token_pair_produces_valid_jwt(db_session):
    user = _make_verified_user(db_session)
    access_token, raw_refresh = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    payload = decode_access_token(access_token)
    assert payload.sub == str(user.user_id)
    assert payload.role == "EMPLOYEE"
    assert len(raw_refresh) > 20


def test_refresh_token_rotation_issues_new_token_and_revokes_old(db_session):
    user = _make_verified_user(db_session)
    _, raw_refresh = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    new_access, new_refresh, refreshed_user = auth_service.rotate_refresh_token(db_session, raw_refresh)
    db_session.commit()

    assert refreshed_user.user_id == user.user_id
    assert new_refresh != raw_refresh

    # Reusing the OLD (now-revoked) refresh token must fail.
    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh)


def test_reusing_revoked_refresh_token_revokes_entire_chain(db_session):
    """Detecting reuse of a rotated-out token should burn all active
    refresh tokens for that user as a theft-mitigation measure."""
    user = _make_verified_user(db_session)
    _, raw_refresh_1 = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    _, raw_refresh_2, _ = auth_service.rotate_refresh_token(db_session, raw_refresh_1)
    db_session.commit()

    # Attacker replays the original (now revoked) token.
    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh_1)
    db_session.commit()

    # The legitimately rotated token should ALSO now be revoked.
    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh_2)


def test_logout_revokes_refresh_token(db_session):
    user = _make_verified_user(db_session)
    _, raw_refresh = auth_service.issue_token_pair(db_session, user)
    db_session.commit()

    auth_service.logout(db_session, raw_refresh)
    db_session.commit()

    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, raw_refresh)


def test_invalid_refresh_token_raises(db_session):
    with pytest.raises(TokenExpiredOrInvalidError):
        auth_service.rotate_refresh_token(db_session, "not-a-real-token")
