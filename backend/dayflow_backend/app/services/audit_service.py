from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    target_entity: str,
    target_id: int | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Append-only. Caller is responsible for commit (usually as part of the
    same transaction as the business-logic change)."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_entity=target_entity,
        target_id=target_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry
