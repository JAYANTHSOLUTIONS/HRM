from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify(
    db: Session,
    *,
    recipient_user_id: int,
    type: str,
    title: str,
    message: str,
) -> Notification:
    n = Notification(
        recipient_user_id=recipient_user_id,
        type=type,
        title=title,
        message=message,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(n)
    db.flush()
    return n
