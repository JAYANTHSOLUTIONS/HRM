def test_get_my_profile_requires_auth(client):
    resp = client.get("/api/v1/employees/me")
    assert resp.status_code == 401


def test_get_my_profile(client, auth_headers, seed_employee):
    resp = client.get("/api/v1/employees/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["employee_code"] == "CCAS20260002"
    assert body["first_name"] == "Asha"
    assert body["department"]["department_name"] == "Engineering"


def test_update_profile_allows_only_whitelisted_fields(client, auth_headers, seed_employee):
    resp = client.patch(
        "/api/v1/employees/me",
        headers=auth_headers,
        json={
            "phone": "9876543210",
            "address": "New address, Bengaluru",
            # attempted privilege escalation — must be silently ignored:
            "role": "ADMIN",
            "salary": 999999,
            "department_id": 999,
            "employee_code": "HACKED0001",
            "employment_status": "TERMINATED",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "9876543210"
    assert body["address"] == "New address, Bengaluru"
    assert body["employee_code"] == "CCAS20260002"  # unchanged


def test_cannot_see_another_employees_profile_via_own_token(client, auth_headers, seed_employee, seed_second_employee):
    # /employees/me always resolves from the JWT — there is no way to pass
    # a target employee id, so this is really testing that identity can't
    # be spoofed via any other channel (headers, query, body).
    resp = client.get("/api/v1/employees/me", params={"employee_id": seed_second_employee["employee"].employee_id}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["employee_code"] == seed_employee["employee"].employee_code
