# Dayflow HRMS — Part 3: Employee Self-Service Module

FastAPI backend for the employee-facing APIs, built to sit on top of the
**same** FastAPI app, MySQL database, SQLAlchemy models, and JWT auth as
Part 1 (auth) and Part 2 (admin/HR) — no second database, no second auth
system.

## ⚠️ Before you run this

**This deliverable does not have your real Part 1 / Part 2 code**, because
it wasn't provided. Everything under `app/assumed_existing/` is a
minimal, clearly-marked stand-in:

| File | Stands in for | Delete it and import your real... |
|---|---|---|
| `app/assumed_existing/auth.py` | `User` model, JWT decode, `get_current_user` | Part 1 auth module |
| `app/assumed_existing/org_models.py` | `Employee`, `Department`, `Designation`, `SalaryStructure`, `SalaryComponent` | Part 2 models |
| `app/assumed_existing/storage_service.py` | shared file storage service | Part 2's storage service, if it already has one |

Every import of these across `app/api/`, `app/services/`, and
`app/models/__init__.py` needs to be repointed at your real modules
during merge. Nothing in Part 3 re-implements login, signup, or admin
functionality — it only *depends on* them.

**I was not able to `pip install` or run `pytest` in the sandbox this was
built in (no network access).** All files pass `python -m py_compile`
(no syntax errors), and I traced every test in `tests/` against the
service logic by hand, but you should run the suite for real before
trusting it:

```bash
pip install -r requirements.txt
pytest -v
```

## What's implemented

All 20 sections of the spec, section-by-section:

- **Identity** (`app/api/deps.py::get_current_employee`) — every
  employee route derives the employee from `JWT -> users.user_id ->
  employees.user_id`. No route accepts `employee_id` from the client.
- **Profile** — `GET/PATCH /api/v1/employees/me`. The PATCH body schema
  (`EmployeeMeUpdate`) only *has* `phone` and `address` fields — role,
  salary, department, designation, manager, employee_code, and
  employment_status can't be sent because there's no field for them to
  land in, not because of an if-check that could be missed.
- **Profile picture** — validated by file signature (magic bytes), not
  just declared MIME type; stored via the storage service under a
  server-generated key; served through a protected, authenticated
  streaming endpoint (`GET /employees/me/profile-picture/view`), never a
  raw URL.
- **Documents** — upload, list, and two streaming endpoints
  (`/documents/{id}/view` with `Content-Disposition: inline`,
  `/documents/{id}/download` with `attachment`), both authorization
  checked (`document.employee_id == current_user` OR admin/HR).
- **Attendance** — `today`, `check-in`, `check-out`, `me?range=`. A DB
  unique constraint on `(employee_id, attendance_date)` makes double
  check-in structurally impossible, not just app-layer checked.
  `work_hours` is always server-computed from server timestamps.
- **Leave** — types, balances, apply (server-computed
  `number_of_days`, attachment-required validation, overlap check),
  history, cancel (PENDING-only). The Alembic migration also adds a
  MySQL trigger as the final overlap guard against concurrent writers.
- **Salary** — read-only, single GET, no write verb registered at all.
- **Dashboard** — aggregates the above, scoped to the caller.
- **Notifications** — list + mark-read, with an ownership check on
  mark-read.
- **Errors** — uniform `{"error": {"code", "message", "details"}}` shape
  via `app/core/exceptions.py`, installed as global FastAPI exception
  handlers.

## Merging into the real app

```python
# your existing main.py
from app.api.v1 import employee_module_router
from app.core.exceptions import install_exception_handlers

app.include_router(employee_module_router)
install_exception_handlers(app)  # skip if Part 1/2 already normalizes errors
```

Then delete `app/main.py` and `app/assumed_existing/` from this
deliverable, repoint the imports listed in the table above, and run the
Alembic migration (`migrations/versions/part3_0001_employee_self_service.py`)
after setting its `down_revision` to your current head.

## API examples

**Check in / check out**
```bash
curl -X POST https://api.dayflow.dev/api/v1/attendance/check-in \
  -H "Authorization: Bearer $TOKEN"

curl -X POST https://api.dayflow.dev/api/v1/attendance/check-out \
  -H "Authorization: Bearer $TOKEN"
```

**Apply for leave**
```bash
curl -X POST https://api.dayflow.dev/api/v1/leave/requests \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"leave_type_id": 1, "start_date": "2026-09-10", "end_date": "2026-09-12", "remarks": "Family trip"}'
```

**Upload a document**
```bash
curl -X POST https://api.dayflow.dev/api/v1/employees/me/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "document_type=ID_PROOF" -F "file=@passport.pdf"
```

**Upload profile picture, then display it**
```bash
curl -X POST https://api.dayflow.dev/api/v1/employees/me/profile-picture \
  -H "Authorization: Bearer $TOKEN" -F "file=@avatar.jpg"
# response.profile_picture_url -> use directly as <img src="...">
# (it's a protected streaming URL; the browser must send the same bearer
#  token / session cookie your frontend already attaches to API calls)
```

## Known simplifications to revisit

- `_business_days_inclusive` in `leave_service.py` counts Mon–Fri as
  chargeable leave days and ignores public holidays — swap in a real
  org-calendar service once one exists.
- `total_working_days` in the weekly attendance summary is hardcoded to
  5 — same fix.
- `recent_activity` in the dashboard is always `[]` until an
  activity/audit-log table exists.
- The overlap pre-check + MySQL trigger combination narrows but doesn't
  perfectly eliminate every race window on extremely rare concurrent
  double-submits; if that matters for your load, consider a proper
  `(employee_id, daterange)` exclusion mechanism.
