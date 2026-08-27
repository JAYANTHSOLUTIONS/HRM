from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_sender_address(settings) -> str:
    from_addr = settings.SMTP_FROM or ""
    if ("dayflow.dev" in from_addr or not from_addr) and settings.SMTP_USER and "@" in settings.SMTP_USER and not settings.SMTP_USER.endswith("@smtp-brevo.com"):
        return settings.SMTP_USER
    return from_addr or "no-reply@dayflow.dev"


def send_password_reset_otp(email: str, otp: str) -> bool:
    settings = get_settings()
    sender = _get_sender_address(settings)

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
    msg["From"] = sender
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
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [email], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [email], msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email} via SMTP: {e}")
        if settings.ENV == "development":
            print(f"[SMTP FALLBACK MOCK] Email error: {e}. OTP for {email} is: {otp}")
            return True
        return False


def send_invitation_email(
    email: str,
    employee_name: str,
    employee_code: str,
    temp_password: str,
    role: str,
    department: str | None = None,
    designation: str | None = None,
    joining_date: str | None = None,
) -> bool:
    """Send an invitation email to a newly created employee with their credentials and employment details."""
    settings = get_settings()
    sender = _get_sender_address(settings)

    dept_display = department or "Unassigned"
    desig_display = designation or "Unassigned"
    join_display = joining_date or "—"

    subject = "Welcome to Dayflow — Your Account Is Ready"
    body_text = f"""Welcome to Dayflow HRMS, {employee_name}!

Your account has been created. Here are your details:

Employee Code: {employee_code}
Role: {role}
Department: {dept_display}
Designation: {desig_display}
Joining Date: {join_display}

Your temporary login credentials:
  Email: {email}
  Password: {temp_password}

Please sign in and change your password immediately after your first login.

If you have any questions, contact your HR administrator.

— Dayflow HRMS
"""

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; background-color: #f1f4f8; color: #1c2b3a; padding: 20px; margin: 0; }}
        .card {{ background: #ffffff; max-width: 560px; margin: 0 auto; border-radius: 12px; border: 1px solid #d1d9e0; padding: 36px; }}
        .header {{ text-align: center; margin-bottom: 28px; }}
        .header h1 {{ margin: 0; font-size: 22px; color: #1c2b3a; }}
        .header p {{ margin: 8px 0 0; font-size: 14px; color: #64748b; }}
        .welcome {{ background: linear-gradient(135deg, #eff6ff, #f0f9ff); border: 1px solid #bfdbfe; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 24px; }}
        .welcome h2 {{ margin: 0 0 6px; font-size: 18px; color: #1e40af; }}
        .welcome p {{ margin: 0; font-size: 14px; color: #475569; }}
        .details-grid {{ display: table; width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
        .detail-row {{ display: table-row; }}
        .detail-label {{ display: table-cell; padding: 10px 12px; font-size: 13px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9; width: 140px; }}
        .detail-value {{ display: table-cell; padding: 10px 12px; font-size: 13px; color: #1c2b3a; font-weight: 600; border-bottom: 1px solid #f1f5f9; }}
        .cred-box {{ background: #fefce8; border: 1px dashed #ca8a04; border-radius: 10px; padding: 20px; margin-bottom: 24px; }}
        .cred-box h3 {{ margin: 0 0 14px; font-size: 14px; color: #854d0e; text-transform: uppercase; letter-spacing: 0.5px; }}
        .cred-item {{ margin-bottom: 10px; }}
        .cred-item-label {{ font-size: 12px; color: #92400e; margin-bottom: 2px; }}
        .cred-item-value {{ font-size: 15px; color: #78350f; font-weight: 700; font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace; letter-spacing: 0.5px; word-break: break-all; }}
        .warning {{ background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 12px 16px; font-size: 12px; color: #9a3412; margin-bottom: 24px; line-height: 1.5; }}
        .warning strong {{ color: #7c2d12; }}
        .footer {{ text-align: center; font-size: 12px; color: #94a3b8; margin-top: 24px; padding-top: 20px; border-top: 1px solid #f1f5f9; line-height: 1.5; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>Dayflow HRMS</h1>
          <p>Employee Onboarding Invitation</p>
        </div>

        <div class="welcome">
          <h2>Welcome aboard, {employee_name}!</h2>
          <p>Your account has been created and is ready to use.</p>
        </div>

        <div class="details-grid">
          <div class="detail-row">
            <div class="detail-label">Employee Code</div>
            <div class="detail-value">{employee_code}</div>
          </div>
          <div class="detail-row">
            <div class="detail-label">Role</div>
            <div class="detail-value">{role}</div>
          </div>
          <div class="detail-row">
            <div class="detail-label">Department</div>
            <div class="detail-value">{dept_display}</div>
          </div>
          <div class="detail-row">
            <div class="detail-label">Designation</div>
            <div class="detail-value">{desig_display}</div>
          </div>
          <div class="detail-row">
            <div class="detail-label">Joining Date</div>
            <div class="detail-value">{join_display}</div>
          </div>
        </div>

        <div class="cred-box">
          <h3>🔑 Your Login Credentials</h3>
          <div class="cred-item">
            <div class="cred-item-label">Email</div>
            <div class="cred-item-value">{email}</div>
          </div>
          <div class="cred-item">
            <div class="cred-item-label">Temporary Password</div>
            <div class="cred-item-value">{temp_password}</div>
          </div>
        </div>

        <div class="warning">
          <strong>⚠️ Important:</strong> Please sign in and change your password immediately after your first login.
          Do not share your credentials with anyone.
        </div>

        <div class="footer">
          This is an automated message from Dayflow HRMS.<br>
          If you did not expect this email, please contact your HR administrator.
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    # If SMTP is disabled or unconfigured in dev mode, log to console
    if not settings.SMTP_USER and settings.ENV == "development":
        logger.info(f"[DEV EMAIL MOCK] Invitation sent to {email}")
        print(f"\n{'=' * 50}")
        print(f"  [SMTP MOCK] Invitation Email")
        print(f"  From: {sender}")
        print(f"  To: {email}")
        print(f"  Employee: {employee_name}")
        print(f"  Code: {employee_code}")
        print(f"  Role: {role}")
        print(f"  Department: {dept_display}")
        print(f"  Designation: {desig_display}")
        print(f"  Joining Date: {join_display}")
        print(f"  Temp Password: {temp_password}")
        print(f"{'=' * 50}\n")
        return True

    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [email], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [email], msg.as_string())
        logger.info(f"Invitation email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invitation email to {email} via SMTP: {e}")
        if settings.ENV == "development":
            print(f"[SMTP FALLBACK MOCK] Email error: {e}. Invitation for {email}: password={temp_password}")
            return True
        return False
