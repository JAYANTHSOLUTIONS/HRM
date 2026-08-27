# Dayflow HRMS Backend

## Architecture decision

Dayflow is organized as a **modular monolith**: one FastAPI application, one MySQL database, one SQLAlchemy metadata registry, and one migration history. Authentication, Admin/HR, and Employee Self-Service are bounded modules inside that application.

A microservice split is not appropriate yet because the current folders share the same business domains but use different model bases, settings, table names, JWT implementations, and migration histories. Splitting them now would create distributed transactions and versioning problems without a stable service boundary.

## Canonical application

`dayflow_backend/` is the canonical application because it owns the broad Admin/HR API and the shared HR schema.

Target layout:

```text
backend/
  dayflow_backend/                 # canonical deployable application
    app/
      main.py                      # the only FastAPI entry point
      api/
        auth.py                    # authentication and account lifecycle
        admin.py                   # admin operations
        employees.py                # HR employee management
        attendance.py
        leave.py
        salary.py
        dashboard.py
        documents.py
        notifications.py           # employee self-service notifications
        audit.py
      core/                        # one config, DB session, security policy
      models/                      # one shared SQLAlchemy model registry
      schemas/
      services/
    migrations/                    # one migration chain
    tests/
  storage/

  archive/
    dayflow-hrms-auth/             # archived auth source
    dayflow_hrms/                  # archived employee source
```

The archived source folders must not be deployed as additional copies of the API. Their `main.py` files are retained for reference only.

## Migration order

1. Keep `dayflow_backend` as the only application and database owner.
2. Port the tested authentication implementation from `dayflow-hrms-auth` into `dayflow_backend/app/api`, `core`, `models`, `schemas`, and `services`.
3. Port only missing Employee Self-Service behavior from `dayflow_hrms`, adapting it to the canonical models and table names. Do not copy its `assumed_existing` compatibility layer.
4. Consolidate configuration into one `.env` and use one JWT secret/algorithm everywhere.
5. Replace the separate migration histories with one reviewed Alembic chain. Never run the `dayflow_hrms` placeholder migration against production.
6. Run the complete test suite, then archive or delete the two temporary source folders.

## Current development commands

Admin/HR API:

```powershell
Set-Location backend/dayflow_backend
uvicorn app.main:app --reload
```

The system exposes only the canonical app on port `8000`, with all modules under `/api/v1`.

## Definition of done

The consolidation is complete when:

- only `dayflow_backend/app/main.py` creates a `FastAPI` instance;
- every router imports the same config, database session, `Base`, and security helpers;
- one migration command creates the complete schema;
- auth, Admin/HR, and Employee Self-Service tests pass together;
- the temporary app folders no longer contain deployable entry points.
