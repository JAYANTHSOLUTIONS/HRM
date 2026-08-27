import datetime as dt

from app.assumed_existing.org_models import SalaryComponent, SalaryComponentType, SalaryStructure, WageType


def _seed_salary(db_session, employee_id, monthly=60000.00):
    structure = SalaryStructure(
        employee_id=employee_id,
        monthly_wage=monthly,
        annual_wage=monthly * 12,
        wage_type=WageType.MONTHLY,
        effective_from=dt.date(2026, 1, 10),
        net_pay_estimate=48699.00,
    )
    db_session.add(structure)
    db_session.flush()

    db_session.add_all(
        [
            SalaryComponent(
                salary_structure_id=structure.salary_structure_id,
                name="Basic Salary",
                type=SalaryComponentType.EARNING,
                amount=30000.00,
            ),
            SalaryComponent(
                salary_structure_id=structure.salary_structure_id,
                name="House Rent Allowance",
                type=SalaryComponentType.EARNING,
                amount=15000.00,
            ),
        ]
    )
    db_session.commit()
    return structure


def test_get_my_salary(client, db_session, auth_headers, seed_employee):
    _seed_salary(db_session, seed_employee["employee"].employee_id)

    resp = client.get("/api/v1/salary/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["monthly_wage"] == 60000.00
    assert body["wage_type"] == "MONTHLY"
    assert len(body["components"]) == 2


def test_salary_not_found_when_no_structure(client, auth_headers, seed_employee):
    resp = client.get("/api/v1/salary/me", headers=auth_headers)
    assert resp.status_code == 404


def test_cannot_view_another_employees_salary(
    client, db_session, auth_headers_second, seed_employee, seed_second_employee
):
    # Only the first employee has a salary structure on file.
    _seed_salary(db_session, seed_employee["employee"].employee_id)

    # There is no query param/body field for target employee_id on this
    # endpoint at all — the second employee's own token can only ever
    # resolve to the second employee's own (missing) salary record.
    resp = client.get("/api/v1/salary/me", headers=auth_headers_second)
    assert resp.status_code == 404


def test_salary_endpoint_has_no_write_verb(client, auth_headers):
    # PATCH/PUT/POST are simply not registered on this router.
    resp = client.post("/api/v1/salary/me", headers=auth_headers, json={"monthly_wage": 1})
    assert resp.status_code in (404, 405)
