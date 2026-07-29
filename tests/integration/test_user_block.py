"""Bloklash DARHOL kuchga kiradi (D-08, T-01-44).

=============================================================================
BU YERDA UCHTA ALOHIDA DA'VO SINALADI VA ULARNI ARALASHTIRIB BO'LMAYDI:

1. **Kesh HAQIQATAN keshlaydi.** Bloklashdan keyin kesh invalidatsiya
   QILINMASA, keyingi so'rov hali ham o'tadi (TTL tugagunicha). Bu
   "nazorat holati": usiz keshning umuman ishlayotganini bilib
   bo'lmaydi va keyingi ikki test ma'nosiz bo'lardi.
2. **Invalidatsiyadan keyin BIRINCHI so'rov rad etiladi** — 30 soniya
   kutilmaydi. D-08 ning aynan o'zi.
3. **Kesh promahida DB javob beradi** — FAIL-OPEN EMAS. Valkey o'chgan
   holatda tizim "hammaga ruxsat" rejimiga o'tmaydi.

Faqat (2) yozilganda test yashil bo'lardi, lekin u kesh umuman
ishlamayotgan holatda ham yashil bo'lardi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.deps import user_state_key
from fixtures.auth_api import ME_URL, REFRESH_URL, login, set_user_active

if TYPE_CHECKING:
    import httpx
    from fixtures.auth_users import AuthSeed
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _authorized(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> dict[str, str]:
    body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


async def test_active_user_is_accepted(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """NAZORAT HOLATI: bloklanmagan foydalanuvchi o'tadi."""
    headers = await _authorized(api_client, auth_seed)

    response = await api_client.get(ME_URL, headers=headers)

    assert response.status_code == 200
    assert response.json()["market"]["id"] == str(auth_seed.market_a_id)


async def test_cache_serves_stale_state_until_invalidated(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    api_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """NAZORAT HOLATI: kesh haqiqatan keshlaydi.

    Invalidatsiyasiz bloklash TTL tugagunicha kuchga kirmaydi — aynan shu
    sababdan yozuv yo'lida `invalidate_user_state()` MAJBURIY. Bu test
    keyingi ikkitasining ma'noli bo'lishini ta'minlaydi.
    """
    headers = await _authorized(api_client, auth_seed)
    assert (await api_client.get(ME_URL, headers=headers)).status_code == 200

    await set_user_active(api_sessionmaker, auth_seed.market_admin.user_id, is_active=False)

    assert (await api_client.get(ME_URL, headers=headers)).status_code == 200


async def test_block_takes_effect_on_the_first_request_after_invalidation(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    api_sessionmaker: async_sessionmaker[AsyncSession],
    valkey_client: Redis,
) -> None:
    """D-08: bloklash + kesh invalidatsiyasi -> KEYINGI so'rovdayoq 401.

    Hech qanday kutish YO'Q: bloklangan kassir bir soniya ham to'lov
    kirita olmasligi kerak.
    """
    headers = await _authorized(api_client, auth_seed)
    assert (await api_client.get(ME_URL, headers=headers)).status_code == 200

    await set_user_active(api_sessionmaker, auth_seed.market_admin.user_id, is_active=False)
    await valkey_client.delete(user_state_key(auth_seed.market_admin.user_id))

    response = await api_client.get(ME_URL, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "account_blocked"}


async def test_cache_miss_falls_back_to_database(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    api_sessionmaker: async_sessionmaker[AsyncSession],
    valkey_client: Redis,
) -> None:
    """Kesh bo'sh bo'lsa holat DB'dan o'qiladi — FAIL-OPEN emas."""
    headers = await _authorized(api_client, auth_seed)
    await set_user_active(api_sessionmaker, auth_seed.market_admin.user_id, is_active=False)
    await valkey_client.flushdb()

    response = await api_client.get(ME_URL, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "account_blocked"}
    # Va DB'dan o'qilgan holat keshga yozildi (keyingi so'rov arzon bo'ladi).
    assert await valkey_client.get(user_state_key(auth_seed.market_admin.user_id)) is not None


async def test_blocked_user_login_returns_invalid_credentials(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bloklangan foydalanuvchi login'da bloklanganini BILMAYDI (T-01-40)."""
    response = await login(api_client, auth_seed.blocked.phone, auth_seed.password)

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


async def test_blocked_user_refresh_is_rejected(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    api_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Uzoq umrli sessiya ham bloklashdan omon qolmaydi.

    Refresh tokenda `roles` va `mid` ATAYIN yo'q — huquqlar har `/refresh`
    da DB'dan qayta o'qiladi. Shuning uchun bloklash 15 daqiqalik access
    token tugagach EMAS, keyingi `/refresh` da darhol kuchga kiradi.
    """
    await login(api_client, auth_seed.market_admin.phone, auth_seed.password)
    await set_user_active(api_sessionmaker, auth_seed.market_admin.user_id, is_active=False)

    response = await api_client.post(REFRESH_URL)

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_refresh"}
