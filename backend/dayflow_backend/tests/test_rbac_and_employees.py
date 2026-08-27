from tests.conftest import auth_header


def test_employee_list_requires_admin_or_hr(client, seed):
    resp = client.get("/api/v1/employees", headers=auth_header(seed["emp_user"]))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_employee_list_ok_for_hr(client, seed):
    resp = client.get("/api/v1/employees", headers=auth_header(seed["hr_user"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_items"] == 1
    assert body["items"][0]["employee_code"] == seed["employee"].employee_code


def test_unauthenticated_request_rejected(client, seed):
    resp = client.get("/api/v1/employees")
    assert resp.status_code == 401


def test_employee_patch_requires_admin(client, seed):
    emp_id = seed["employee"].employee_id
    resp = client.patch(
        f"/api/v1/employees/{emp_id}", json={"phone": "9999999999"},
        headers=auth_header(seed["hr_user"]),
    )
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/employees/{emp_id}", json={"phone": "9999999999"},
        headers=auth_header(seed["admin_user"]),
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "9999999999"
