"""
Cloudflare Turnstile server-side verification.

The frontend's CAPTCHA result is NEVER trusted. Every login request's
`captcha_token` is sent to Cloudflare's siteverify endpoint along with our
secret key, and only Cloudflare's response decides pass/fail.
"""
import httpx

from app.core.config import settings


class CaptchaVerificationError(Exception):
    """Raised when Turnstile verification fails or cannot be completed."""


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """
    Returns True if Cloudflare confirms the token is valid, False otherwise.
    Never raises for a plain "failed" verification — only for genuine
    transport/config errors, which are treated as a failure by the caller.
    """
    if settings.CAPTCHA_BYPASS:
        # Only ever set true in local/dev/test environments (see .env.example).
        return True

    if not token:
        return False

    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(settings.TURNSTILE_VERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError):
        # Fail closed: a broken CAPTCHA provider should not silently let
        # every login through.
        return False

    return bool(result.get("success", False))
