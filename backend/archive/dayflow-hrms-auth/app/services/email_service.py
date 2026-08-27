"""
Minimal SMTP email service.

Kept deliberately simple (stdlib smtplib) so Part 1 has zero extra
infrastructure dependencies. If the project later wants a transactional
email provider (SES, SendGrid, Postmark), swap the internals of
`send_email` only — the public function signatures used by auth_service.py
should stay stable for Parts 2/3.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("dayflow.email")


def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    """
    Sends an email. Failures are logged, not raised, for flows where we
    must not reveal to the caller whether an account exists (forgot
    password) — but see auth_service for how this is used so failures are
    still surfaced to operators via logs/monitoring.
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.SMTP_EMAIL}>"
    message["To"] = to_email

    if text_body:
        message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_EMAIL and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_EMAIL, [to_email], message.as_string())
    except Exception:
        logger.exception("Failed to send email to %s (subject=%r)", to_email, subject)


def send_verification_email(to_email: str, first_name: str, raw_token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
    html = f"""
    <p>Hi {first_name},</p>
    <p>Welcome to Dayflow HRMS. Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_url}">Verify my email</a></p>
    <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
    <p>If you did not create this account, you can safely ignore this email.</p>
    """
    send_email(to_email, "Verify your Dayflow HRMS account", html)


def send_password_reset_otp_email(to_email: str, first_name: str, otp: str) -> None:
    html = f"""
    <p>Hi {first_name},</p>
    <p>Use the following one-time code to reset your Dayflow HRMS password:</p>
    <h2>{otp}</h2>
    <p>This code expires in {settings.OTP_EXPIRE_MINUTES} minutes and can only be used once.</p>
    <p>If you did not request a password reset, you can safely ignore this email.</p>
    """
    send_email(to_email, "Your Dayflow HRMS password reset code", html)


def send_password_changed_notice(to_email: str, first_name: str) -> None:
    html = f"""
    <p>Hi {first_name},</p>
    <p>This is a confirmation that your Dayflow HRMS account password was just changed.</p>
    <p>If this wasn't you, please contact your HR administrator immediately.</p>
    """
    send_email(to_email, "Your Dayflow HRMS password was changed", html)
