"""`sbozor_core.security` — JWT chiqarish va tekshirish (Pattern 3).

Token BUTUNLAY foydalanuvchi nazoratida bo'lgan kirish — shuning uchun
dekodlash chegarasi bu fazadagi eng zich test qilinadigan joy.

Qamralgan tahdidlar:
* T-01-12 — `alg` almashtirish (`none`, HS512): algoritm token header'idan
  HECH QACHON olinmaydi
* T-01-13 — access <-> refresh aralashuvi: `typ` claim'i majburiy
* T-01-14 — qisqa HMAC siri: ogohlantirish emas, `InvalidKeyError`
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest

from sbozor_core.security import (
    ALG,
    TokenClaims,
    decode_token,
    encode_access,
    encode_refresh,
)

SECRET = "s" * 48
SHORT_SECRET = "s" * 31
ISSUER = "sbozor"
AUDIENCE = "sbozor-api"

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
MARKET_ID = UUID("22222222-2222-2222-2222-222222222222")
FAMILY_ID = UUID("33333333-3333-3333-3333-333333333333")
ROLES = ["market_admin", "cashier"]


def _access(**overrides: Any) -> str:
    kwargs: dict[str, Any] = {
        "user_id": USER_ID,
        "market_id": MARKET_ID,
        "roles": ROLES,
        "is_platform_admin": False,
        "secret": SECRET,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "ttl_minutes": 15,
    }
    kwargs.update(overrides)
    return encode_access(**kwargs)


def _refresh(**overrides: Any) -> str:
    kwargs: dict[str, Any] = {
        "user_id": USER_ID,
        "secret": SECRET,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "ttl_days": 30,
        "family_id": FAMILY_ID,
    }
    kwargs.update(overrides)
    return encode_refresh(**kwargs)


def _decode(token: str, expected_type: str = "access", **overrides: Any) -> TokenClaims:
    kwargs: dict[str, Any] = {
        "expected_type": expected_type,
        "secret": SECRET,
        "issuer": ISSUER,
        "audience": AUDIENCE,
    }
    kwargs.update(overrides)
    return decode_token(token, **kwargs)


def _b64url(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _raw_claims(token: str) -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(
        token,
        SECRET,
        algorithms=[ALG],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    return payload


# --------------------------------------------------------------------------
# Baxtli yo'l
# --------------------------------------------------------------------------


def test_algorithm_constant_is_hs256() -> None:
    assert ALG == "HS256"


def test_access_token_round_trip() -> None:
    claims = _decode(_access())

    assert claims.user_id == USER_ID
    assert claims.market_id == MARKET_ID
    assert claims.roles == ROLES
    assert claims.is_platform_admin is False
    assert claims.token_type == "access"
    assert claims.jti


def test_access_token_without_market_is_decoded_as_none() -> None:
    """D-06: platforma admini hali bozor tanlamagan holat."""
    claims = _decode(_access(market_id=None, is_platform_admin=True))

    assert claims.market_id is None
    assert claims.is_platform_admin is True


def test_access_sub_claim_is_string_not_uuid_object() -> None:
    """PyJWT 2.10+ `sub` ni `str` deb talab qiladi."""
    payload = _raw_claims(_access())
    assert payload["sub"] == str(USER_ID)
    assert isinstance(payload["sub"], str)


def test_access_claim_names_match_research_table() -> None:
    payload = _raw_claims(_access())
    assert payload["iss"] == ISSUER
    assert payload["aud"] == AUDIENCE
    assert payload["typ"] == "access"
    assert payload["mid"] == str(MARKET_ID)
    assert payload["roles"] == ROLES
    assert payload["pa"] is False
    assert {"exp", "iat", "jti"} <= set(payload)


def test_access_ttl_is_applied() -> None:
    payload = _raw_claims(_access(ttl_minutes=15))
    assert payload["exp"] - payload["iat"] == 15 * 60


def test_refresh_token_round_trip() -> None:
    claims = _decode(_refresh(), expected_type="refresh")

    assert claims.user_id == USER_ID
    assert claims.token_type == "refresh"
    assert claims.family_id == str(FAMILY_ID)


def test_refresh_ttl_is_applied() -> None:
    payload = _raw_claims(_refresh(ttl_days=30))
    assert payload["exp"] - payload["iat"] == 30 * 24 * 60 * 60


def test_refresh_jti_is_unique_per_call() -> None:
    """Rotatsiya va reuse-detect aynan `jti` ga tayanadi."""
    first = _decode(_refresh(), expected_type="refresh")
    second = _decode(_refresh(), expected_type="refresh")
    assert first.jti != second.jti


def test_refresh_jti_can_be_supplied_by_caller() -> None:
    """01-06 rotatsiyasi `jti` ni oldindan yozib, keyin token beradi."""
    known = uuid4().hex
    claims = _decode(_refresh(jti=known), expected_type="refresh")
    assert claims.jti == known


def test_refresh_does_not_carry_roles_or_market() -> None:
    """Huquqlar har `/refresh` da DB'dan QAYTA o'qiladi, tokendan emas."""
    payload = _raw_claims(_refresh())
    assert "roles" not in payload
    assert "mid" not in payload
    assert "pa" not in payload

    claims = _decode(_refresh(), expected_type="refresh")
    assert claims.market_id is None
    assert claims.roles == []
    assert claims.is_platform_admin is False


# --------------------------------------------------------------------------
# T-01-13: tur almashtirish
# --------------------------------------------------------------------------


def test_access_token_rejected_when_refresh_expected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_access(), expected_type="refresh")


def test_refresh_token_rejected_when_access_expected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_refresh(), expected_type="access")


def test_wrong_token_type_message_is_explicit() -> None:
    with pytest.raises(jwt.InvalidTokenError, match="token type"):
        _decode(_access(), expected_type="refresh")


# --------------------------------------------------------------------------
# T-01-12: alg almashtirish
# --------------------------------------------------------------------------


def test_alg_none_token_is_rejected() -> None:
    """Imzosiz token — klassik `alg=none` hujumi."""
    now = int(datetime.now(UTC).timestamp())
    header = _b64url({"alg": "none", "typ": "JWT"})
    body = _b64url(
        {
            "sub": str(USER_ID),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + 900,
            "jti": uuid4().hex,
            "typ": "access",
            "mid": str(MARKET_ID),
            "roles": ["platform_admin"],
            "pa": True,
        }
    )
    forged = f"{header}.{body}."

    with pytest.raises(jwt.InvalidTokenError):
        _decode(forged)


def test_token_signed_with_other_algorithm_is_rejected() -> None:
    """HS512 bilan imzolangan token HS256 ro'yxatiga tushmaydi."""
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": str(USER_ID),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": uuid4().hex,
            "typ": "access",
            "mid": str(MARKET_ID),
            "roles": ["platform_admin"],
            "pa": True,
        },
        SECRET,
        algorithm="HS512",
    )

    with pytest.raises(jwt.InvalidTokenError):
        _decode(forged)


def test_tampered_signature_is_rejected() -> None:
    header, body, _signature = _access().split(".")
    with pytest.raises(jwt.InvalidTokenError):
        _decode(f"{header}.{body}.aaaaaaaaaaaaaaaaaaaaaaaaaaaa")


def test_token_signed_with_other_secret_is_rejected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_access(secret="d" * 48))


# --------------------------------------------------------------------------
# T-01-14: kalit uzunligi
# --------------------------------------------------------------------------


def test_encode_access_rejects_short_secret() -> None:
    """RFC 7518: HS256 uchun minimal kalit — 32 bayt. Ogohlantirish EMAS, xato."""
    with pytest.raises(jwt.exceptions.InvalidKeyError):
        _access(secret=SHORT_SECRET)


def test_encode_refresh_rejects_short_secret() -> None:
    with pytest.raises(jwt.exceptions.InvalidKeyError):
        _refresh(secret=SHORT_SECRET)


def test_decode_rejects_short_secret() -> None:
    """`enforce_minimum_key_length=True` — dekodlashda ham xato."""
    token = _access()
    with pytest.raises(jwt.exceptions.InvalidKeyError):
        _decode(token, secret=SHORT_SECRET)


def test_exactly_thirty_two_byte_secret_is_accepted() -> None:
    secret = "k" * 32
    claims = _decode(_access(secret=secret), secret=secret)
    assert claims.user_id == USER_ID


# --------------------------------------------------------------------------
# Standart claim tekshiruvlari
# --------------------------------------------------------------------------


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    expired = jwt.encode(
        {
            "sub": str(USER_ID),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": past,
            "exp": past + timedelta(minutes=15),
            "jti": uuid4().hex,
            "typ": "access",
            "mid": str(MARKET_ID),
            "roles": ROLES,
            "pa": False,
        },
        SECRET,
        algorithm=ALG,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        _decode(expired)


def test_wrong_issuer_is_rejected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_access(issuer="boshqa-tizim"))


def test_wrong_audience_is_rejected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_access(audience="boshqa-api"))


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "iss", "aud", "jti"])
def test_missing_required_claim_is_rejected(missing: str) -> None:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(USER_ID),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": uuid4().hex,
        "typ": "access",
        "mid": str(MARKET_ID),
        "roles": ROLES,
        "pa": False,
    }
    del payload[missing]
    token = jwt.encode(payload, SECRET, algorithm=ALG)

    with pytest.raises(jwt.InvalidTokenError):
        _decode(token)


def test_token_claims_is_frozen() -> None:
    claims = _decode(_access())
    with pytest.raises(AttributeError):
        claims.user_id = uuid4()  # type: ignore[misc]
