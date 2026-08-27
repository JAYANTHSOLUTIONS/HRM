"""
End-to-end tests that go through the actual FastAPI app + HTTP layer
(signup -> verify -> login -> refresh -> logout), with the DB session
overridden to the SQLite test fixture and captcha bypassed.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _extract_verification_token(html_body: str) -> str:
    match = re.search(r"token=([^\"'&\s]+)", html_body)
    assert match, "verification token not found in email body"
    return match.group(1)


def test_full_signup_login_refresh_logout_flow(client, _no_real_email):
    signup_payload = {
        "first_name": "Asha",
        "last_name": "Singh",
        "email": "asha.singh@dayflow.dev",
        "password": "StrongPass!234",
        "department_id": 1,
        "designation_id": 1,
        "joining_date": "2026-09-01",
    }
    signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    body = signup_resp.json()
    assert body["role"] == "EMPLOYEE"
    assert body["is_email_verified"] is False

    assert len(_no_real_email) == 1
    raw_token = _extract_verification_token(_no_real_email[0]["html_body"])

    verify_resp = client.post("/api/v1/auth/verify-email", json={"token": raw_token})
    assert verify_resp.status_code == 200

    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha.singh@dayflow.dev",
            "password": "StrongPass!234",
            "captcha_token": "bypass-token",
        },
    )
    assert login_resp.status_code == 200
    login_body = login_resp.json()
    assert login_body["user"]["role"] == "EMPLOYEE"
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    logout_resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 204

    # The refresh token used at logout time is the ORIGINAL one, which the
    # /refresh call above already rotated out, so this must be rejected
    # anyway — but this call also verifies the endpoint requires auth.
    unauth_logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert unauth_logout.status_code == 401
    assert unauth_logout.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_signup_role_field_is_ignored_over_http(client, _no_real_email):
    payload = {
        "first_name": "Vik",
        "last_name": "Rao",
        "email": "vik.rao@dayflow.dev",
        "password": "StrongPass!234",
        "department_id": 1,
        "designation_id": 1,
        "joining_date": "2026-09-01",
        "role": "ADMIN",
    }
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 201
    assert resp.json()["role"] == "EMPLOYEE"


def test_duplicate_signup_returns_409(client, _no_real_email):
    payload = {
        "first_name": "Dup",
        "last_name": "User",
        "email": "dup@dayflow.dev",
        "password": "StrongPass!234",
        "department_id": 1,
        "designation_id": 1,
        "joining_date": "2026-09-01",
    }
    first = client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_with_wrong_password_returns_standard_error_shape(client, _no_real_email):
    signup_payload = {
        "first_name": "Wr",
        "last_name": "Pass",
        "email": "wrongpass@dayflow.dev",
        "password": "StrongPass!234",
        "department_id": 1,
        "designation_id": 1,
        "joining_date": "2026-09-01",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)
    raw_token = _extract_verification_token(_no_real_email[0]["html_body"])
    client.post("/api/v1/auth/verify-email", json={"token": raw_token})

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@dayflow.dev", "password": "TotallyWrong!1", "captcha_token": "x"},
    )
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "INVALID_CREDENTIALS"
    assert "message" in error
    assert "details" in error


def test_forgot_password_always_returns_generic_message(client, _no_real_email):
    resp_known = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@dayflow.dev"})
    assert resp_known.status_code == 200
    assert "If an account exists" in resp_known.json()["message"]


def test_validation_error_shape(client):
    # Missing required fields -> 422 with our standardized error envelope.
    resp = client.post("/api/v1/auth/signup", json={"email": "not-an-email"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) > 0
