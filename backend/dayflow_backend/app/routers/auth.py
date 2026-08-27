from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.models.refresh_token import RefreshToken
from app.core.deps import get_current_user
from app.schemas.auth import (
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
    StandardResponse,
    UserSummary,
    VerifyEmailRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services import auth_service, otp as otp_service
from app.services.turnstile import verify_turnstile

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    # Cloudflare Turnstile Verification (Required for Signup)
    verify_turnstile(payload.turnstile_token)

    user, _verification_token = auth_service.signup(db, payload)
    db.commit()
    db.refresh(user)
    return SignupResponse(
        user_id=user.user_id,
        employee_code=user.employee_code,
        email=user.email,
        role=user.role_name,
        is_email_verified=user.is_email_verified,
        message="Account created. Please check your email to verify your address.",
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    # Cloudflare Turnstile Verification (Required for Login)
    verify_turnstile(payload.turnstile_token)

    user = auth_service.authenticate(db, payload.email, payload.password)
    access_token, refresh_token = auth_service.issue_session(db, user)
    db.commit()
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,
        user=UserSummary(
            user_id=user.user_id,
            employee_id=user.employee.employee_id,
            employee_code=user.employee_code,
            full_name=user.employee.full_name,
            email=user.email,
            role=user.role_name,
        ),
    )


@router.get("/me", response_model=UserSummary)
def get_current_user_profile(user: User = Depends(get_current_user)) -> UserSummary:
    """Get authenticated user profile."""
    return UserSummary(
        user_id=user.user_id,
        employee_id=user.employee.employee_id if user.employee else user.user_id,
        employee_code=user.employee_code,
        full_name=user.employee.full_name if user.employee else user.email,
        email=user.email,
        role=user.role_name,
    )


@router.post("/forgot-password", response_model=StandardResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Request password reset OTP.
    1. Validates Cloudflare Turnstile CAPTCHA.
    2. Generates secure 6-digit OTP using secrets module.
    3. Hashes OTP before saving to DB with 5-min expiration.
    4. Sends OTP via Gmail SMTP.
    5. Returns generic response to prevent email enumeration.
    """
    verify_turnstile(payload.turnstile_token)
    otp_service.request_otp(db, payload.email)
    return StandardResponse(
        success=True,
        message="If an account exists for this email, a password reset OTP has been sent."
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)) -> VerifyOTPResponse:
    """
    Verify 6-digit OTP code.
    1. Validates OTP hash, 5-minute expiration, and max 5 attempts.
    2. Invalidates OTP after verification.
    3. Generates short-lived (10-minute) reset_token for reset password stage.
    """
    reset_token = otp_service.verify_otp(db, payload.email, payload.otp)
    return VerifyOTPResponse(
        success=True,
        message="OTP verified successfully. You may now reset your password.",
        reset_token=reset_token
    )


@router.post("/reset-password", response_model=StandardResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Reset password using reset_token.
    1. Validates reset_token and 10-minute expiration.
    2. Confirms new password matches confirm_password.
    3. Hashes new password using Argon2.
    4. Updates user in DB & invalidates reset token.
    """
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match."
        )

    otp_service.reset_password_with_token(db, payload.reset_token, payload.new_password)
    return StandardResponse(
        success=True,
        message="Password reset successfully. Please sign in with your new password."
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    verify_turnstile(payload.turnstile_token)
    auth_service.verify_email(db, payload.token)
    db.commit()
    return MessageResponse(message="Email verified successfully. You can now sign in.")


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> RefreshResponse:
    access_token = auth_service.refresh_session(db, payload.refresh_token)
    db.commit()
    return RefreshResponse(access_token=access_token, expires_in=15 * 60)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Response:
    token = db.query(RefreshToken).filter_by(token_hash=auth_service._hash_token(payload.refresh_token)).first()
    if token is not None:
        from datetime import datetime, timezone
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
