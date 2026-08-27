from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.assumed_existing.auth import User, get_current_user
from app.core.database import get_db
from app.schemas.notification import NotificationListOut, NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def get_my_notifications(
    unread_only: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, unread_count = notification_service.list_my_notifications(db, user, unread_only)
    return {"items": items, "unread_count": unread_count}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.mark_as_read(db, user, notification_id)
