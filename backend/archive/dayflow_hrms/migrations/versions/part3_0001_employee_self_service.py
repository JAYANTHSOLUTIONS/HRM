"""add employee self-service tables (attendance, leave, documents, notifications)

Revision ID: part3_0001
Revises: <SET_TO_YOUR_CURRENT_HEAD>
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "part3_0001"
down_revision = "<SET_TO_YOUR_CURRENT_HEAD>"  # <-- point this at Part 1/2's latest revision
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attendances",
        sa.Column("attendance_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.employee_id"), nullable=False, index=True),
        sa.Column("attendance_date", sa.Date, nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("PRESENT", "ABSENT", "ON_LEAVE", "HALF_DAY", name="attendancestatus"),
            nullable=False,
            server_default="PRESENT",
        ),
        sa.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
    )

    op.create_table(
        "leave_types",
        sa.Column("leave_type_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("is_balance_tracked", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("requires_attachment", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "leave_balances",
        sa.Column("leave_balance_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.employee_id"), nullable=False, index=True),
        sa.Column("leave_type_id", sa.Integer, sa.ForeignKey("leave_types.leave_type_id"), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("allocated_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("used_days", sa.Float, nullable=False, server_default="0"),
    )

    op.create_table(
        "documents",
        sa.Column("document_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.employee_id"), nullable=False, index=True),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "leave_requests",
        sa.Column("leave_request_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.employee_id"), nullable=False, index=True),
        sa.Column("leave_type_id", sa.Integer, sa.ForeignKey("leave_types.leave_type_id"), nullable=False, index=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("number_of_days", sa.Float, nullable=False),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column("attachment_document_id", sa.Integer, sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="leaverequeststatus"),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.false(), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # If Part 2 hasn't already added a profile_picture_key column to
    # employees, add it here:
    # op.add_column("employees", sa.Column("profile_picture_key", sa.String(500), nullable=True))

    # Final line of defense against overlapping leave requests under
    # concurrent writers (MySQL 8+: emulate an exclusion constraint via a
    # trigger, since native range-overlap exclusion constraints aren't
    # available in MySQL the way they are in Postgres).
    op.execute(
        """
        CREATE TRIGGER trg_leave_requests_no_overlap
        BEFORE INSERT ON leave_requests
        FOR EACH ROW
        BEGIN
            DECLARE conflict_count INT;
            SELECT COUNT(*) INTO conflict_count
            FROM leave_requests
            WHERE employee_id = NEW.employee_id
              AND status IN ('PENDING', 'APPROVED')
              AND start_date <= NEW.end_date
              AND end_date >= NEW.start_date;
            IF conflict_count > 0 THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'OVERLAPPING_LEAVE_REQUEST';
            END IF;
        END
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_leave_requests_no_overlap")
    op.drop_table("notifications")
    op.drop_table("leave_requests")
    op.drop_table("documents")
    op.drop_table("leave_balances")
    op.drop_table("leave_types")
    op.drop_table("attendances")
