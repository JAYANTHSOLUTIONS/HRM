import datetime as dt


def test_get_leave_types(client, auth_headers, seed_employee):
    resp = client.get("/api/v1/leave-types", headers=auth_headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()["items"]]
    assert "Paid Leave" in names


def test_get_leave_balances(client, auth_headers, seed_employee):
    resp = client.get("/api/v1/leave/balances", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    item = body["items"][0]
    assert item["allocated_days"] == 24
    assert item["remaining_days"] == 24


def test_apply_leave_computes_days_serverside(client, auth_headers, seed_employee):
    lt_id = seed_employee["leave_type"].leave_type_id
    resp = client.post(
        "/api/v1/leave/requests",
        headers=auth_headers,
        json={
            "leave_type_id": lt_id,
            "start_date": "2026-09-10",  # Thu
            "end_date": "2026-09-12",  # Sat -> counts Thu, Fri = 2 business days
            "remarks": "Family trip",
            "number_of_days": 999,  # must be ignored
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["number_of_days"] != 999


def test_overlapping_leave_is_rejected(client, auth_headers, seed_employee):
    lt_id = seed_employee["leave_type"].leave_type_id
    first = client.post(
        "/api/v1/leave/requests",
        headers=auth_headers,
        json={"leave_type_id": lt_id, "start_date": "2026-09-10", "end_date": "2026-09-12"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/leave/requests",
        headers=auth_headers,
        json={"leave_type_id": lt_id, "start_date": "2026-09-11", "end_date": "2026-09-13"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "OVERLAPPING_LEAVE_REQUEST"


def test_cancel_pending_leave(client, auth_headers, seed_employee):
    lt_id = seed_employee["leave_type"].leave_type_id
    created = client.post(
        "/api/v1/leave/requests",
        headers=auth_headers,
        json={"leave_type_id": lt_id, "start_date": "2026-10-01", "end_date": "2026-10-01"},
    ).json()

    cancel = client.post(
        f"/api/v1/leave/requests/{created['leave_request_id']}/cancel", headers=auth_headers
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"

    second_cancel = client.post(
        f"/api/v1/leave/requests/{created['leave_request_id']}/cancel", headers=auth_headers
    )
    assert second_cancel.status_code == 409
    assert second_cancel.json()["error"]["code"] == "CANNOT_CANCEL"


def test_cannot_cancel_another_employees_leave(
    client, auth_headers, auth_headers_second, seed_employee, seed_second_employee
):
    lt_id = seed_employee["leave_type"].leave_type_id
    created = client.post(
        "/api/v1/leave/requests",
        headers=auth_headers,
        json={"leave_type_id": lt_id, "start_date": "2026-11-01", "end_date": "2026-11-01"},
    ).json()

    resp = client.post(
        f"/api/v1/leave/requests/{created['leave_request_id']}/cancel", headers=auth_headers_second
    )
    assert resp.status_code == 404  # not found in this employee's own scope
