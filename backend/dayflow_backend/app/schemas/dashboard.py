from pydantic import BaseModel


class RecentActivityItem(BaseModel):
    action: str
    target_entity: str
    target_id: int | None = None
    actor_name: str | None = None
    created_at: str


class AdminDashboardOut(BaseModel):
    total_employees: int
    active_employees: int
    present_today: int
    absent_today: int
    on_leave_today: int
    pending_leave_requests: int
    recent_activity: list[RecentActivityItem]
