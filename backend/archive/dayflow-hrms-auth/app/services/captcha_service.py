from app.core.captcha import verify_turnstile_token
from app.core.errors import CaptchaFailedError


async def verify_captcha_or_raise(captcha_token: str, remote_ip: str | None = None) -> None:
    is_valid = await verify_turnstile_token(captcha_token, remote_ip=remote_ip)
    if not is_valid:
        raise CaptchaFailedError()
