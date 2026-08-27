from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    UserSummary,
    VerifyEmailRequest,
)
from app.services import auth_service
from app.services.captcha_service import verify_captcha_or_raise

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    user, raw_token = auth_service.signup(db, payload)
    db.commit()
    db.refresh(user)

    # Sent after commit so a slow/failed email never rolls back account creation.
    auth_service.send_signup_verification_email(user.email, payload.first_name, raw_token)

    return SignupResponse(
        user_id=user.user_id,
        employee_code=user.employee_code,
        email=user.email,
        role=user.role.name,
        is_email_verified=user.is_email_verified,
        message="Account created. Please check your email to verify your address.",
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    auth_service.verify_email(db, payload.token)
    db.commit()
    return MessageResponse(message="Email verified successfully. You can now sign in.")


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    await verify_captcha_or_raise(payload.captcha_token, remote_ip=_client_ip(request))

    user = auth_service.authenticate_user(db, payload.email, payload.password)
    access_token, raw_refresh_token = auth_service.issue_token_pair(db, user)
    db.commit()
    db.refresh(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserSummary(
            user_id=user.user_id,
            employee_id=user.user_id,
            employee_code=user.employee_code,
            full_name=user.employee_code,  # Part 2's employee profile owns full_name; placeholder until that join exists.
            email=user.email,
            role=user.role.name,
            profile_picture_url=None,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> RefreshResponse:
    access_token, _new_raw_refresh, _user = auth_service.rotate_refresh_token(db, payload.refresh_token)
    db.commit()
    return RefreshResponse(access_token=access_token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Response:
    auth_service.logout(db, payload.refresh_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    auth_service.request_password_reset(db, payload.email)
    db.commit()
    return MessageResponse(message="If an account exists for this email, an OTP has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    auth_service.reset_password(db, email=payload.email, otp_code=payload.token, new_password=payload.new_password)
    db.commit()
    return MessageResponse(message="Password has been reset. Please sign in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    auth_service.change_password(db, current_user, payload.current_password, payload.new_password)
    db.commit()
    return MessageResponse(message="Password changed successfully.")
