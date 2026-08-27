def test_check_in_then_check_out(client, auth_headers):
    resp = client.post("/api/v1/attendance/check-in", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PRESENT"
    assert body["check_in_at"] is not None

    today = client.get("/api/v1/attendance/today", headers=auth_headers)
    assert today.status_code == 200
    assert today.json()["check_in_at"] is not None
    assert today.json()["check_out_at"] is None

    out = client.post("/api/v1/attendance/check-out", headers=auth_headers)
    assert out.status_code == 200
    out_body = out.json()
    assert out_body["check_out_at"] is not None
    assert out_body["work_hours"] >= 0


def test_double_check_in_is_rejected(client, auth_headers):
    first = client.post("/api/v1/attendance/check-in", headers=auth_headers)
    assert first.status_code == 200

    second = client.post("/api/v1/attendance/check-in", headers=auth_headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_CHECKED_IN"


def test_check_out_without_check_in_is_rejected(client, auth_headers):
    resp = client.post("/api/v1/attendance/check-out", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "NOT_CHECKED_IN"


def test_client_cannot_control_work_hours_or_timestamps(client, auth_headers):
    # The check-in/check-out endpoints take no body at all, so there is no
    # field through which a client could inject attendance_date,
    # check_in_at, or work_hours.
    resp = client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers,
        json={"attendance_date": "2000-01-01", "check_in_at": "2000-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    assert resp.json()["check_in_at"].startswith("20")
    assert "2000-01-01" not in resp.json()["check_in_at"]
