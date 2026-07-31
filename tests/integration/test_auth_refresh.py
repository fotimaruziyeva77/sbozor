"""Refresh rotatsiyasi va reuse detection (D-03, T-01-41).

=============================================================================
NEGA ROTATSIYA VA REUSE DETECTION BIRGA SINALADI:

Yolg'iz rotatsiya hech nima bermaydi — u faqat tokenni almashtiradi.
Qiymati AYNAN reuse aniqlashda: bekor qilingan `jti` qaytib kelishi
"kimdir tokenni nusxa ko'chirgan" degan YAGONA ishonchli signal. O'shanda
BUTUN OILA bekor qilinadi, ya'ni o'g'irlangan token 30 kun emas, KEYINGI
ishlatilishida o'ladi va haqiqiy foydalanuvchi ham qaytadan login
qilishga majbur bo'ladi (o'g'irlik sezilishi kerak).

Shuning uchun reuse testi UCH narsani birga tekshiradi:
  1. eski token 401 beradi;
  2. ENG YANGI (haqiqiy) token ham 401 beradi — oila bekor qilingan;
  3. `audit_log` da `refresh_reuse_detected` yozuvi paydo bo'ladi.
Faqat (1) tekshirilganda oddiy "bekor qilingan token" mantiqi ham testdan
o'tib ketardi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.security.tokens import REFRESH_COOKIE_NAME
from fixtures.auth_api import (
    LOGOUT_URL,
    REFRESH_URL,
    audit_rows,
    login,
    refresh_token_row,
)
from sbozor_core.security import decode_token

if TYPE_CHECKING:
    import httpx
    from app.settings import Settings
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _login_admin(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> str:
    """Login qiladi va joriy refresh cookie qiymatini qaytaradi."""
    response = await login(api_client, auth_seed.market_admin.phone, auth_seed.password)
    assert response.status_code == 200, response.text
    cookie = api_client.cookies.get(REFRESH_COOKIE_NAME)
    assert cookie is not None
    return cookie


def _jti(token: str, settings: Settings) -> str:
    return decode_token(
        token,
        expected_type="refresh",
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    ).jti


async def test_refresh_rotates_the_cookie(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, test_settings: Settings
) -> None:
    """Har `/refresh` da YANGI `jti` beriladi (eskisi qayta ishlatilmaydi)."""
    old_cookie = await _login_admin(api_client, auth_seed)

    response = await api_client.post(REFRESH_URL)

    assert response.status_code == 200, response.text
    new_cookie = api_client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_cookie is not None
    assert new_cookie != old_cookie
    assert _jti(new_cookie, test_settings) != _jti(old_cookie, test_settings)


async def test_refresh_returns_roles_and_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Huquqlar DB'dan QAYTA o'qiladi (refresh tokenda `roles`/`mid` yo'q)."""
    await _login_admin(api_client, auth_seed)

    body = (await api_client.post(REFRESH_URL)).json()

    assert body["roles"] == ["market_admin"]
    # `is_active` — MAJBURIY maydon (02-03). `/refresh` javobi ham
    # `MarketRef` ni qaytaradi, ya'ni uchala oqim (login / select-market /
    # refresh) bir xil shakl bilan qulflanadi.
    assert body["market"] == {
        "id": str(auth_seed.market_a_id),
        "name": auth_seed.market_a_name,
        "is_active": True,
    }


async def test_refresh_extends_expiry(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    test_settings: Settings,
    api_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """D-03 sliding: yangi tokenning `expires_at` i eskisidan KATTA."""
    old_cookie = await _login_admin(api_client, auth_seed)
    old_row = await refresh_token_row(api_sessionmaker, _jti(old_cookie, test_settings))

    await api_client.post(REFRESH_URL)

    new_cookie = api_client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_cookie is not None
    new_row = await refresh_token_row(api_sessionmaker, _jti(new_cookie, test_settings))

    assert old_row is not None
    assert new_row is not None
    assert new_row.expires_at > old_row.expires_at


async def test_refresh_reuse_detection(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """O'g'irlangan token qayta ishlatilsa BUTUN oila o'ladi (T-01-41)."""
    stolen = await _login_admin(api_client, auth_seed)

    rotated = await api_client.post(REFRESH_URL)
    assert rotated.status_code == 200
    fresh = api_client.cookies.get(REFRESH_COOKIE_NAME)
    assert fresh is not None

    # 1. O'g'irlangan (allaqachon rotatsiya qilingan) token qaytib keldi.
    replayed = await api_client.post(
        REFRESH_URL, headers={"Cookie": f"{REFRESH_COOKIE_NAME}={stolen}"}
    )
    assert replayed.status_code == 401
    assert replayed.json() == {"detail": "invalid_refresh"}
    # Brauzerdagi o'lik cookie ham tozalanadi.
    assert REFRESH_COOKIE_NAME in (replayed.headers.get("set-cookie") or "")

    # 2. ENG YANGI, haqiqiy token ham endi ishlamaydi — oila bekor qilingan.
    after = await api_client.post(REFRESH_URL, headers={"Cookie": f"{REFRESH_COOKIE_NAME}={fresh}"})
    assert after.status_code == 401

    # 3. Hodisa auditda AYNAN BIR MARTA iz qoldirgan.
    #    Oila o'lgandan keyingi urinishlar (yuqoridagi 2-qadam) yangi
    #    signal yozmaydi — bitta o'g'irlik = bitta ogohlantirish.
    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action="refresh_reuse_detected")
    assert len(rows) == 1
    assert rows[0].actor_user_id == auth_seed.market_admin.user_id
    assert rows[0].source == "app"


async def test_logout_kills_the_family(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, tenant_session: TenantSessionFactory
) -> None:
    """Logout'dan keyin refresh cookie ishlamaydi va audit yozuvi qoladi."""
    cookie = await _login_admin(api_client, auth_seed)

    logged_out = await api_client.post(LOGOUT_URL)
    assert logged_out.status_code == 204

    replay = await api_client.post(
        REFRESH_URL, headers={"Cookie": f"{REFRESH_COOKIE_NAME}={cookie}"}
    )
    assert replay.status_code == 401

    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action="logout")
    assert len(rows) == 1


async def test_logout_without_cookie_is_idempotent(api_client: httpx.AsyncClient) -> None:
    """Cookie'siz logout ham 204 — foydalanuvchi xato ko'rmasligi kerak."""
    response = await api_client.post(LOGOUT_URL)
    assert response.status_code == 204


async def test_access_token_is_not_accepted_as_refresh(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Tur almashtirish rad etiladi (T-01-13): access token refresh o'rniga ishlamaydi."""
    body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()

    response = await api_client.post(
        REFRESH_URL,
        headers={"Cookie": f"{REFRESH_COOKIE_NAME}={body['access_token']}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_refresh"}


async def test_refresh_without_cookie_is_401(api_client: httpx.AsyncClient) -> None:
    """Cookie umuman bo'lmasa 401 — anonim sessiya uzaytirish yo'li yo'q."""
    response = await api_client.post(REFRESH_URL)
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_refresh"}


async def test_forged_refresh_token_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Boshqa sir bilan imzolangan token rad etiladi (T-01-12 ning HTTP tomoni)."""
    await _login_admin(api_client, auth_seed)

    response = await api_client.post(
        REFRESH_URL,
        headers={"Cookie": f"{REFRESH_COOKIE_NAME}=yaroqsiz.token.qiymati"},
    )

    assert response.status_code == 401
