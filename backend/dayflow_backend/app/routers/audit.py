import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.audit import AuditLog
from app.schemas.common import Page
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs (Admin only)"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_log_id: int
    actor_user_id: int | None
    action: str
    target_entity: str
    target_id: int | None
    old_values: dict | None
    new_values: dict | None
    created_at: datetime


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    target_entity: str | None = None,
    action: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(AuditLog)
    if target_entity:
        query = query.filter(AuditLog.target_entity == target_entity)
    if action:
        query = query.filter(AuditLog.action == action)

    total_items = query.order_by(None).count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    return {"page": page, "page_size": page_size, "total_items": total_items,
            "total_pages": total_pages, "items": items}
