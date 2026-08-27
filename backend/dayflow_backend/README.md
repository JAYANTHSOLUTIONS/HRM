# Dayflow HRMS — Admin/HR Backend (Part 2)

FastAPI service implementing the **Admin + HR module** of the Dayflow HRMS
backend, built on top of Part 1's MySQL schema and auth system.

> **Important — about Part 1:** only Part 1's *database schema* and *API
> design docs* were available when this was built (no Part 1 source code
> was provided). To make Part 2 actually runnable and testable, this repo
> includes a small, clearly-marked **compatibility shim**
> (`app/core/security.py`, `app/core/deps.py`) that verifies JWTs the same
> way Part 1's real auth service is documented to. It does **not**
> reimplement signup, login, refresh, password reset, email verification,
> CAPTCHA, or OTP — those stay Part 1's responsibility. When you wire this
> up against the real Part 1 service, just make sure `JWT_SECRET_KEY` /
> `JWT_ALGORITHM` in `.env` match Part 1's exactly, and delete
> `create_access_token` (only used by tests/dev to mint compatible tokens
> when Part 1 isn't running).

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (MySQL via PyMySQL) — **same database as Part 1, no Mongo, no second DB**
- JWT auth (verifies tokens issued by Part 1)
- Local filesystem storage in dev, S3-compatible object storage in prod (swap via `.env`)

## Project layout

```
app/
  core/        config, DB session, JWT verification, RBAC dependencies
  models/      SQLAlchemy models (1:1 with Part 1's existing schema — no new tables)
  schemas/     Pydantic request/response models
  services/    business logic (transactions, validation, audit, storage)
  routers/     FastAPI route handlers, one file per resource
  main.py      app assembly, error handlers, router registration
migrations/    Part 1's schema.sql (copied for convenience) + notes
storage/       local dev file storage (documents/, profile-images/)
tests/         pytest suite (SQLite-backed, no external services needed)
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: DATABASE_URL must point at the SAME MySQL DB Part 1 uses,
# JWT_SECRET_KEY/JWT_ALGORITHM must match Part 1's auth service.

# Apply schema if not already applied by Part 1:
mysql -u root -p < migrations/000_part1_full_schema.sql

uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Running tests

```bash
pytest -v
```

Tests run against an in-memory SQLite DB, so they don't need MySQL running.
One thing SQLite *can't* exercise: the MySQL trigger-based leave-overlap
protection defined in Part 1's schema (`trg_leave_requests_no_overlap_*`).
That trigger is still the authoritative guard in production; the backend
additionally does a friendly pre-check... (see `IntegrityError` handling in
`app/main.py`, which translates the trigger's `SIGNAL 45000` into a clean
`409 OVERLAPPING_LEAVE` response).

## RBAC

Enforced **only** in the backend (`app/core/deps.py::require_role`), never
trusting the frontend's route guards, per spec:

| Role | Access |
|---|---|
| **ADMIN** | everything — employee editing, salary, user invites, audit logs |
| **HR** | employee viewing, attendance viewing/correction, leave approval, dashboard, documents |
| **EMPLOYEE** | none of the above (self-service documents/profile-picture only, scoped to their own `employee_id`) |

## File uploads — how "actually working" is achieved

- MySQL never stores file bytes — only metadata (`employee_documents` /
  `employees.profile_picture_url`, which for Part 2 holds a **storage key**,
  not the literal file).
- Every upload is validated three ways before it's accepted: extension
  allow-list, declared `Content-Type`, and **actual file signature (magic
  bytes)** — see `app/services/file_validation.py`. `.exe/.bat/.sh/.js/.html`
  etc. are always rejected regardless of what the client claims.
- Storage keys are random (`employee_{id}/{uuid}_{safe-stub}.ext`) — the
  original filename is never used as the on-disk name.
- `GET /api/v1/documents/{id}/view` and `.../download` are authenticated
  streaming endpoints that set the correct `Content-Type` and
  `Content-Disposition` (`inline` vs `attachment`), so the frontend can
  point an `<img>`/`<iframe>`/PDF viewer straight at `view_url` and it just
  works, or trigger a real download via `download_url`.
- Profile pictures are served from a **separate, unauthenticated**
  `GET /api/v1/employees/{id}/profile-picture/raw` endpoint by design, so a
  plain `<img src="...">` renders without the frontend needing to attach
  an `Authorization` header (browsers can't do that on `<img>` tags).
  Storage keys are opaque/random. For stricter privacy in production, swap
  this for S3 **presigned URLs** — `services/storage_service.S3Storage`
  already has `presigned_url()` ready to use.
- Profile picture uploads are re-encoded through Pillow (strips anything
  riding along in a crafted image) and capped at 512px on the long edge.
- Switch `STORAGE_BACKEND=s3` in `.env` to move from local disk to
  S3-compatible object storage — nothing above the storage layer changes.

## Endpoints implemented

All under `/api/v1`, all requiring `Authorization: Bearer <token>` except
`/employees/{id}/profile-picture/raw`.

- `GET/PATCH /employees`, `/employees/{id}`
- `GET/POST/PATCH /departments`, `/designations`
- `POST/GET /employees/{id}/documents`, `GET/DELETE /documents/{id}`,
  `GET /documents/{id}/view|download`
- `POST /employees/{id}/profile-picture`, `GET .../profile-picture/raw`
- `GET /attendance`, `PATCH /attendance/{id}/correct`
- `GET /leave-types`, `GET /leave/requests`,
  `POST /leave/requests/{id}/approve|reject`
- `GET/PUT /salary/{employee_id}`, `GET /salary/{employee_id}/history`
- `GET /dashboard/admin`
- `POST /admin/users/invite`
- `GET /audit-logs`

Every sensitive Admin/HR write creates an `audit_logs` row
(`app/services/audit_service.py`) and, where relevant, a `notifications`
row for the affected employee.

## Things deliberately left as hooks, not fully built

- **Email delivery** (`app/services/admin_service.py::_send_invitation_email`)
  is a stub — wire it to the SMTP settings already in `.env`/`config.py`.
- **S3 credentials/bucket policy** — `S3Storage` is implemented but needs
  real bucket/IAM setup per environment.
