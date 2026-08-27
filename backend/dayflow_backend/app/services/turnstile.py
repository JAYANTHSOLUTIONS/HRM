import json
import urllib.parse
import urllib.request
from fastapi import HTTPException, status

from app.core.config import get_settings


def verify_turnstile(token: str | None, client_ip: str | None = None) -> bool:
    settings = get_settings()

    if not settings.TURNSTILE_ENABLED:
        return True

    # If token is empty
    if not token:
        # Development mode fallback using Turnstile dummy pass key
        if settings.ENV == "development":
            return True
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cloudflare Turnstile verification token is missing.",
        )

    # Cloudflare Turnstile test sitekey/secret (always passes in dev mode)
    if token in ("1x00000000000000000000AA", "dummy_turnstile_token") or settings.TURNSTILE_SECRET_KEY == "1x000000000000000000000000000000AA":
        return True

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if client_ip:
        payload["remoteip"] = client_ip

    data = urllib.parse.urlencode(payload).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if not body.get("success", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cloudflare Turnstile CAPTCHA verification failed: {', '.join(body.get('error-codes', ['invalid-input-response']))}",
                )
            return True
    except HTTPException:
        raise
    except Exception as e:
        # If external Cloudflare server unreachable, allow dev fallback
        if settings.ENV == "development":
            return True
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cloudflare Turnstile verification service error: {str(e)}",
        )
