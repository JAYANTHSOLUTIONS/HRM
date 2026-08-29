from datetime import date
from tests.conftest import auth_header


def test_salary_requires_admin(client, seed):
    emp_id = seed["employee"].employee_id
    payload = {
        "monthly_wage": 50000,
        "wage_type": "MONTHLY",
        "effective_from": "2026-10-01",
        "components": [
            {"name": "Basic Salary", "type": "EARNING", "calculation_type": "PERCENTAGE", "percentage": 50},
            {"name": "Employee PF", "type": "DEDUCTION", "calculation_type": "PERCENTAGE", "percentage": 12},
        ],
    }
    resp = client.put(f"/api/v1/salary/{emp_id}", json=payload, headers=auth_header(seed["hr_user"]))
    assert resp.status_code == 403

    resp = client.put(f"/api/v1/salary/{emp_id}", json=payload, headers=auth_header(seed["admin_user"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_current"] is True
    assert float(body["monthly_wage"]) == 50000.0
    basic = next(c for c in body["components"] if c["name"] == "Basic Salary")
    assert float(basic["computed_amount"]) == 25000.0

    # Employee views their own salary read-only via GET /api/v1/me/salary
    me_resp = client.get("/api/v1/me/salary", headers=auth_header(seed["emp_user"]))
    assert me_resp.status_code == 200
    me_body = me_resp.json()
    assert float(me_body["monthly_wage"]) == 50000.0
    assert len(me_body["components"]) == 2

    # Admin lists all salaries via GET /api/v1/salary
    list_resp = client.get("/api/v1/salary", headers=auth_header(seed["admin_user"]))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 1


def test_leave_approve_requires_pending(client, db_session, seed):
    from app.models.leave import LeaveRequest, LeaveBalance
    from datetime import datetime, timezone

    lb = LeaveBalance(
        employee_id=seed["employee"].employee_id, leave_type_id=seed["leave_type"].leave_type_id,
        leave_year=2026, allocated_days=10, used_days=0,
    )
    db_session.add(lb)
    db_session.flush()

    lr = LeaveRequest(
        employee_id=seed["employee"].employee_id, leave_type_id=seed["leave_type"].leave_type_id,
        start_date=date(2026, 10, 5), end_date=date(2026, 10, 6), number_of_days=2,
        status="PENDING", submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(lr)
    db_session.commit()

    resp = client.post(
        f"/api/v1/leave/requests/{lr.leave_request_id}/approve", json={"comment": "OK"},
        headers=auth_header(seed["hr_user"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # second approval attempt -> 409 ALREADY_REVIEWED
    resp2 = client.post(
        f"/api/v1/leave/requests/{lr.leave_request_id}/approve", json={"comment": "again"},
        headers=auth_header(seed["hr_user"]),
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "ALREADY_REVIEWED"
