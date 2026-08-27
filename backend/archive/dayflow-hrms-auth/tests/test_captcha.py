import pytest

from app.core.errors import CaptchaFailedError
from app.services.captcha_service import verify_captcha_or_raise


@pytest.mark.asyncio
async def test_captcha_bypass_allows_any_token(monkeypatch):
    """CAPTCHA_BYPASS=true is set globally in tests/conftest.py so unrelated
    tests don't need a live Turnstile call. This test explicitly re-verifies
    that behavior and then tests the non-bypass path."""
    await verify_captcha_or_raise("any-token")  # should not raise


@pytest.mark.asyncio
async def test_captcha_failure_raises_when_bypass_disabled(monkeypatch):
    import app.core.captcha as captcha_module

    monkeypatch.setattr(captcha_module.settings, "CAPTCHA_BYPASS", False)

    async def _fake_verify(token, remote_ip=None):
        return False

    monkeypatch.setattr(captcha_module, "verify_turnstile_token", _fake_verify)

    from app.services import captcha_service
    monkeypatch.setattr(captcha_service, "verify_turnstile_token", _fake_verify)

    with pytest.raises(CaptchaFailedError):
        await captcha_service.verify_captcha_or_raise("bad-token")


@pytest.mark.asyncio
async def test_captcha_success_when_bypass_disabled(monkeypatch):
    import app.core.captcha as captcha_module
    from app.services import captcha_service

    monkeypatch.setattr(captcha_module.settings, "CAPTCHA_BYPASS", False)

    async def _fake_verify(token, remote_ip=None):
        return True

    monkeypatch.setattr(captcha_service, "verify_turnstile_token", _fake_verify)

    await captcha_service.verify_captcha_or_raise("good-token")  # should not raise
