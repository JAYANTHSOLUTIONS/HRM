# Migrations

Part 1 (auth) already owns the full database schema for this project —
`000_part1_full_schema.sql` is a copy of the schema Part 1 shipped
(`dayflow_schema.sql`), which already includes every table Part 2 needs:
`employees`, `departments`, `designations`, `employee_documents`, `holidays`,
`attendance`, `leave_types`, `leave_balances`, `leave_requests`,
`leave_request_reviews`, `salary_structures`, `salary_components`,
`audit_logs`, `notifications`.

**Part 2 requires no additional schema changes.** The SQLAlchemy models in
`app/models/` map 1:1 onto this existing schema — no new tables, no new
columns.

## Applying the schema (fresh environment)

```bash
mysql -u root -p < migrations/000_part1_full_schema.sql
mysql -u root -p dayflow_hrms < migrations/001_seed_data.sql   # optional sample data
```

If you're standing up Part 2 against a database Part 1 has already
initialized, you don't need to run anything here — just point
`DATABASE_URL` in `.env` at it.

## If you introduce real schema changes later

Add numbered `.sql` files here (`002_...sql`, `003_...sql`, ...) or switch to
Alembic (`alembic init migrations`) once the schema needs to evolve
independently per-environment. Alembic is already in `requirements.txt`
for when that day comes.
