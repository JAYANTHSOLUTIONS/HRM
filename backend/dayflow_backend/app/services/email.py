from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_password_reset_otp(email: str, otp: str) -> bool:
    settings = get_settings()

    subject = "Password Reset OTP - Dayflow HRMS"
    body_text = f"""Password Reset OTP

Your OTP is: {otp}

This OTP expires in 5 minutes.

If you did not request this password reset, you can safely ignore this email.
"""

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background-color: #f1f4f8; color: #1c2b3a; padding: 20px; }}
        .card {{ background: #ffffff; max-width: 480px; margin: 0 auto; border-radius: 10px; border: 1px solid #d1d9e0; padding: 32px; text-align: center; }}
        .otp-box {{ background: #eff4ff; border: 1px dashed #2563eb; color: #2563eb; font-size: 32px; font-weight: 800; letter-spacing: 8px; padding: 16px; border-radius: 8px; margin: 24px 0; font-family: monospace; }}
        .footer {{ font-size: 12px; color: #6b7e94; margin-top: 24px; line-height: 1.5; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h2 style="margin-top:0; color:#1c2b3a;">Dayflow HRMS</h2>
        <p style="font-size:14px; color:#475569;">You requested a password reset for your account.</p>
        <div class="otp-box">{otp}</div>
        <p style="font-size:13px; color:#6b7e94;">This OTP is valid for <strong>5 minutes</strong>.</p>
        <div class="footer">
          If you did not request a password reset, please ignore this email.
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = email

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    # If SMTP is disabled or unconfigured in dev mode, log to console
    if not settings.SMTP_USER and settings.ENV == "development":
        logger.info(f"[DEV EMAIL MOCK] Password reset OTP for {email}: {otp}")
        print(f"\n==========================================")
        print(f"  [GMAIL SMTP MOCK] Sent to: {email}")
        print(f"  Password Reset OTP: {otp}")
        print(f"  Expires in: 5 minutes")
        print(f"==========================================\n")
        return True

    try:
        if settings.SMTP_PORT == 465 or settings.SMTP_USE_TLS:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [email], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [email], msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email} via SMTP: {e}")
        if settings.ENV == "development":
            print(f"[SMTP FALLBACK MOCK] Email error: {e}. OTP for {email} is: {otp}")
            return True
        return False
