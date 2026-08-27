from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notification_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    items: List[NotificationOut]
    unread_count: int
