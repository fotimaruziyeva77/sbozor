"""`sbozor_core.logging` — sir filtri va so'rov konteksti.

Loglar ilova chegarasidan CHIQADI (stdout -> Docker -> Sentry), shuning uchun
ular sir sizishining eng oson yo'li. Qamralgan tahdid: T-01-16.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import UUID

import pytest
import structlog
from sbozor_core.logging import (
    CENSORED,
    SENSITIVE_KEYS,
    bind_request_context,
    censor_secrets,
    clear_request_context,
    configure_logging,
)

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
MARKET_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """Global structlog konfiguratsiyasi testlar orasida oqib ketmasin."""
    yield
    clear_request_context()
    structlog.reset_defaults()


# --------------------------------------------------------------------------
# T-01-16: sir filtri
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["password", "password_hash", "token", "access_token", "refresh_token", "jwt_secret"],
)
def test_censor_secrets_masks_required_keys(key: str) -> None:
    """Rejadagi majburiy kalitlar ro'yxati."""
    result = censor_secrets(None, "info", {"event": "auth", key: "haqiqiy-sir"})
    assert result[key] == CENSORED


def test_censor_secrets_is_case_insensitive() -> None:
    result = censor_secrets(None, "info", {"event": "auth", "Authorization": "Bearer abc"})
    assert result["Authorization"] == CENSORED


def test_censor_secrets_keeps_non_sensitive_fields() -> None:
    result = censor_secrets(
        None,
        "info",
        {"event": "login", "phone": "+998901234567", "market_id": str(MARKET_ID)},
    )
    assert result["event"] == "login"
    assert result["phone"] == "+998901234567"
    assert result["market_id"] == str(MARKET_ID)


def test_sensitive_keys_are_lowercase() -> None:
    """Taqqoslash `key.lower()` bilan — reyestrdagi kalit ham kichik bo'lishi shart."""
    assert all(key == key.lower() for key in SENSITIVE_KEYS)


def test_sensitive_keys_cover_nvr_credentials() -> None:
    """Spec §5: RTSP parollari shifrlangan saqlanadi — log'da ham chiqmasin."""
    assert "rtsp_password" in SENSITIVE_KEYS


# --------------------------------------------------------------------------
# Uchdan-uchi: JSON chiqish + bog'langan kontekst
# --------------------------------------------------------------------------


def test_log_line_is_json_with_context_and_censored_secret(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("info")
    clear_request_context()
    bind_request_context("req-42", user_id=USER_ID, market_id=MARKET_ID)

    structlog.get_logger().info("login_attempt", password="maxfiy", phone="+998901234567")

    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)

    assert payload["event"] == "login_attempt"
    assert payload["password"] == CENSORED
    assert payload["phone"] == "+998901234567"
    assert payload["request_id"] == "req-42"
    assert payload["user_id"] == str(USER_ID)
    assert payload["market_id"] == str(MARKET_ID)
    assert payload["level"] == "info"
    assert "timestamp" in payload


def test_clear_request_context_removes_bound_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Eski bozor identifikatori keyingi so'rov log'ida qolib ketmasligi kerak."""
    configure_logging("info")
    bind_request_context("req-1", market_id=MARKET_ID)
    clear_request_context()

    structlog.get_logger().info("keyingi_sorov")

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "market_id" not in payload
    assert "request_id" not in payload


def test_configure_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("warning")

    logger = structlog.get_logger()
    logger.info("korinmaydi")
    logger.warning("korinadi")

    lines = [line for line in capsys.readouterr().out.strip().splitlines() if line.startswith("{")]
    events = [json.loads(line)["event"] for line in lines]
    assert "korinmaydi" not in events
    assert "korinadi" in events
