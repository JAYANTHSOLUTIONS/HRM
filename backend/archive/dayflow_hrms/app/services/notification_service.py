from sqlalchemy.orm import Session

from app.assumed_existing.auth import User
from app.core.exceptions import AppError
from app.models.notification import Notification


def list_my_notifications(db: Session, user: User, unread_only: bool = False):
    query = db.query(Notification).filter(Notification.user_id == user.user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    items = query.order_by(Notification.created_at.desc()).all()
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.user_id, Notification.is_read.is_(False)
    ).count()
    return items, unread_count


def mark_as_read(db: Session, user: User, notification_id: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.notification_id == notification_id)
        .first()
    )
    if notification is None:
        raise AppError("NOTIFICATION_NOT_FOUND", "Notification not found.", status_code=404)

    # An employee may only ever mark their OWN notifications — this check
    # is what stops one employee from marking another user's notification.
    if notification.user_id != user.user_id:
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to modify this notification.",
            status_code=403,
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
