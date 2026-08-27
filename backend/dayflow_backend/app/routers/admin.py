from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.auth import User
from app.schemas.admin import UserInviteRequest, UserInviteResponse
from app.services.admin_service import invite_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/users/invite", response_model=UserInviteResponse, status_code=201)
def invite(
    payload: UserInviteRequest, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    return invite_user(db, payload=payload, invited_by_user_id=user.user_id)
