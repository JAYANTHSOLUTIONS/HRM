# Dayflow HRMS — Authentication & Security Service (Part 1)

> "Every workday, perfectly aligned."

This is **Part 1** of the Dayflow HRMS backend: the authentication and
security foundation that Part 2 (Admin/HR) and Part 3 (Employee) plug into.
It owns identity (`users`, `roles`, tokens) — **not** HR profile data
(name, department, salary, etc.), which belongs to Part 2/3's employee
module.

---

## 1. Tech stack

- Python 3.12+, FastAPI, Uvicorn
- SQLAlchemy 2.x + Alembic, **MySQL 8.0+ only** (InnoDB, utf8mb4)
- Pydantic v2
- `python-jose` for JWT, `passlib[argon2]` for password hashing
- `httpx` for Cloudflare Turnstile server-side verification
- `smtplib` (stdlib) for email delivery

## 2. Project structure

```
app/
├── main.py                 # FastAPI app, CORS, global error handlers
├── core/
│   ├── config.py           # pydantic-settings, loads .env
│   ├── security.py         # password hashing, token/OTP generation & hashing
│   ├── jwt.py               # JWT encode/decode
│   ├── captcha.py           # Turnstile siteverify client
│   └── errors.py            # AppError + standardized error subclasses
├── db/
│   ├── session.py           # engine, SessionLocal, get_db()
│   └── base.py              # shared Declarative Base + model registry
├── models/                  # SQLAlchemy ORM models
├── schemas/auth.py          # Pydantic request/response schemas
├── api/auth.py              # /api/v1/auth/* endpoints (thin, delegate to services)
├── services/
│   ├── auth_service.py      # core business logic (signup/login/tokens/reset)
│   ├── otp_service.py       # OTP generation/validation
│   ├── email_service.py     # SMTP sending
│   ├── captcha_service.py   # CAPTCHA verify-or-raise wrapper
│   └── audit_service.py     # logging hook for Part 2's audit_logs table
└── dependencies/auth.py     # get_current_user, require_role, require_roles

alembic/                     # migrations (initial schema hand-written; see note below)
scripts/seed_roles.py        # idempotent role seeder for non-migration setups
tests/                       # pytest suite (unit + API integration)
```

## 3. Setup

```bash
cp .env.example .env
# edit .env: DATABASE_URL, JWT_SECRET_KEY, TURNSTILE_SECRET_KEY, SMTP_*

pip install -r requirements.txt

# Create the MySQL database first (CREATE DATABASE dayflow CHARACTER SET utf8mb4;)
alembic upgrade head          # creates tables AND seeds ADMIN/HR/EMPLOYEE roles

uvicorn app.main:app --reload
```

Docs: `http://localhost:8000/docs` · Health check: `GET /health`

### Docker

```bash
docker compose up --build
```

This starts MySQL 8.0 + the API, runs `alembic upgrade head` automatically,
and serves on `http://localhost:8000`.

## 4. Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use an **in-memory SQLite** database for speed/isolation (all logic
is plain SQLAlchemy ORM, no MySQL-specific SQL, so this is safe for unit
testing). To run the same suite against a real MySQL instance before a
release:

```bash
RUN_AGAINST_MYSQL=1 TEST_DATABASE_URL=mysql+pymysql://user:pass@localhost/dayflow_test pytest -v
```

## 5. Design decisions & deviations from the literal spec

These are called out explicitly so Parts 2/3 and reviewers aren't
surprised:

1. **`reset-password` requires `email` in addition to `token`.**
   The spec's OTP section (§5) mandates 6-digit OTP codes for password
   reset, but its endpoint section (§13) shows only `{token, new_password}`.
   A 6-digit code is not globally unique the way a 32-byte random token is
   — looking it up without an account reference risks matching a
   *different* user's currently-active OTP. `ResetPasswordRequest` therefore
   requires `email` to safely scope the OTP lookup. `forgot-password` still
   returns the same generic, account-existence-safe message either way.

2. **`employee_code` generation lives here, temporarily.**
   The `users` table needs a unique `employee_code` at signup time for the
   login response contract, but full employee-profile ownership (name,
   department, designation) belongs to Part 2/3. This module generates a
   collision-checked code (`<initials><year><4-digit-serial>`, e.g.
   `AS20260001`) as a placeholder. Part 2's employee service may extend or
   reconcile this format, but must not change the `employee_code` column
   name or its uniqueness constraint — other modules already depend on it.

3. **`full_name` in the login response is a placeholder.**
   Since first/last name lives in Part 2/3's employee profile table (not
   yet implemented), `UserSummary.full_name` currently echoes
   `employee_code`. Part 2 should join against `employees` here once that
   table exists — the response *shape* (`full_name: str`) is already
   correct and stable for frontend integration.

4. **Refresh-token reuse detection.** If a refresh token that has already
   been rotated-out (revoked) is presented again, the entire active
   refresh-token chain for that user is revoked immediately. This is a
   standard mitigation against refresh-token theft/replay and forces a
   fresh login — it is stricter than the spec explicitly requires but is
   a widely-recommended practice for rotation-based refresh flows.

5. **Alembic migration was hand-written, not autogenerated.** This sandbox
   has no network/database access, so `alembic revision --autogenerate`
   could not be run against a live MySQL instance. The migration in
   `alembic/versions/20260822_0001_initial_auth_schema.py` was written to
   mirror the SQLAlchemy models exactly, but **run `alembic upgrade head`
   against a real MySQL 8.0 database and sanity-check the generated schema
   before relying on it in production** (and consider running
   `alembic check` after installing dependencies).

6. **Dependencies were not installed/run in this sandbox** (no network
   egress available). All files pass `python -m py_compile` and were
   carefully reviewed for correctness, and the test suite is written to
   pass once dependencies are installed — but please run `pip install -r
   requirements.txt && pytest -v` yourself before deploying, since this is
   the first real execution the code will get.

## 6. Security notes for Parts 2/3

- Use `get_current_user`, `require_role("ADMIN")`, `require_roles("ADMIN",
  "HR")` from `app.dependencies.auth` — don't re-parse JWTs yourselves.
- The JWT's `role` claim is convenient but the `User` object returned by
  `get_current_user` is loaded fresh from MySQL on every request; treat
  the database, not the JWT, as the source of truth for anything
  authorization-critical (e.g. re-check `is_active`).
- Never log passwords, password hashes, raw tokens, or raw OTPs. The
  codebase does not do this anywhere — please keep it that way in Parts 2/3.
- Audit events are emitted via `app.services.audit_service.record_auth_event`
  through the standard `logging` module under the `dayflow.audit` logger.
  Attach a handler (or replace the function) to persist these once the
  `audit_logs` table exists — no auth_service.py changes should be needed.

## 7. API reference

All endpoints are prefixed with `/api/v1`.

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | No | Create an EMPLOYEE account (role is never accepted from the client) |
| POST | `/auth/verify-email` | No | Verify email via emailed token |
| POST | `/auth/login` | No | CAPTCHA + password login → access + refresh tokens |
| POST | `/auth/refresh` | No | Rotate refresh token → new access token |
| POST | `/auth/logout` | Yes | Revoke a refresh token |
| POST | `/auth/forgot-password` | No | Request OTP for password reset (always generic response) |
| POST | `/auth/reset-password` | No | Reset password using `{email, token (OTP), new_password}` |
| POST | `/auth/change-password` | Yes | Change password while logged in |

See `docs/dayflow-auth.postman_collection.json` for ready-to-run examples
of every endpoint, or `/docs` for interactive OpenAPI docs once running.

All errors use:

```json
{ "error": { "code": "ERROR_CODE", "message": "...", "details": [] } }
```
