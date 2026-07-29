"""Majburiy parol almashtirish SERVER TOMONIDA kuchga kiradi (D-02, CR-01).

=============================================================================
BU FAYL AYNAN BITTA SAVOLGA JAVOB BERADI:

    `must_change_password = true` bo'lgan foydalanuvchi TO'LIQ yaroqli
    sessiya olsa-da, o'sha sessiya bilan NIMA QILA OLADI?

Javob: FAQAT parolni almashtirishi va chiqishi. Boshqa hech narsa.

Bu 01-VERIFICATION.md dagi CR-01 ning yopilishi. Undan oldin bayroq
DB'dan o'qilar, javoblarda qaytarilar va frontendda tekshirilardi — lekin
serverda BIRONTA ham taqqoslash yo'q edi, ya'ni brauzerni chetlab o'tgan
har qanday to'g'ridan-to'g'ri API so'rovi darvozani umuman ko'rmasdi.
=============================================================================

DARVOZA TESTI IKKI TOMONLAMA BO'LISHI SHART — VA U SHUNDAY:

Faqat "403 keldi" ni tekshirish YETARLI EMAS: o'sha 403 huquq
yetishmasligidan (`forbidden`) ham kelishi mumkin va o'shanda test
darvozani emas, RBAC ni sinagan bo'lardi. Shuning uchun bu yerdagi
foydalanuvchi ATAYIN `market_admin` — unda `USER_MANAGE`, `USER_VIEW` va
`AUDIT_VIEW` huquqlarining UCHALASI HAM BOR. Ya'ni:

  * parol almashtirilmagan holatda 403 `password_change_required`;
  * AYNAN o'sha token bilan, parol almashtirilgandan keyin 200/201.

Ikkinchi yarmisiz birinchisi "bu odamning huquqi yo'q ekan" degan
tushuntirishga ham mos kelardi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fixtures.admin_api import (
    AUDIT_URL,
    USERS_URL,
    bearer,
    new_phone,
    platform_admin_headers,
    session_headers,
)
from fixtures.auth_api import CHANGE_PASSWORD_URL, LOGOUT_URL, ME_URL, login

if TYPE_CHECKING:
    import httpx
    from fixtures.auth_users import AuthSeed

GATED = {"detail": "password_change_required"}
"""Darvozaning javobi — `forbidden` DAN FARQ QILISHI shart (test-yaxlitligi)."""

NEW_PASSWORD = "yangi-uzun-parol-2026"  # noqa: S105 — test ma'lumoti


async def _create_cashier(api_client: httpx.AsyncClient, headers: dict[str, str]) -> httpx.Response:
    """`POST /api/v1/users` — bozor admini BERA OLADIGAN rol bilan (D-04).

    Rol ATAYIN `cashier`: agar u ruxsat etilmagan rol bo'lganda, darvoza
    olib tashlangan holatda ham javob 403 bo'lardi va test darvozani emas,
    D-04 ni sinagan bo'lib qolardi.
    """
    return await api_client.post(
        USERS_URL,
        json={
            "phone": new_phone(),
            "full_name": "Darvoza sinovi",
            "roles": ["cashier"],
            "locale": "uz-Latn",
        },
        headers=headers,
    )


async def _create_market_admin(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> tuple[str, str]:
    """Platforma admini yangi bozor adminini yaratadi -> `(telefon, vaqtinchalik parol)`.

    Foydalanuvchi MAHSULOT YO'LIDAN tug'iladi (`POST /api/v1/users`), ya'ni
    `must_change_password = true` bayrog'ini test emas, D-02 ning o'zi
    qo'yadi. Seed'dan olingan tayyor foydalanuvchi bu zanjirni (vaqtinchalik
    parol -> bayroq -> darvoza) chetlab o'tardi.
    """
    platform = await platform_admin_headers(api_client, auth_seed)
    phone = new_phone()
    created = await api_client.post(
        USERS_URL,
        json={
            "phone": phone,
            "full_name": "Yangi bozor admini",
            "roles": ["market_admin"],
            "locale": "uz-Latn",
        },
        headers=platform,
    )
    assert created.status_code == 201, created.text
    return phone, created.json()["temporary_password"]


async def _token(api_client: httpx.AsyncClient, phone: str, password: str) -> str:
    response = await login(api_client, phone, password)
    assert response.status_code == 200, response.text
    assert response.json()["market"] is not None, "bozor avtomatik tanlanmadi — token `mid` siz"
    return str(response.json()["access_token"])


# ---------------------------------------------------------------------------
# Darvoza YOPIQ
# ---------------------------------------------------------------------------


async def test_must_change_user_is_locked_out_of_every_gated_endpoint(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """O'qish ham, yozuv ham, jurnal ham — uchtasi ham 403 `password_change_required`.

    Uchala endpoint ALOHIDA tekshiriladi, chunki ular darvozaga UCH XIL
    yo'ldan keladi: `GET /users` — `require_permission(USER_VIEW)`,
    `POST /users` — `require_permission(USER_MANAGE)` + `TenantSessionDep`,
    `GET /audit` — `require_permission(AUDIT_VIEW)` + o'qish auditi. Bittasi
    darvozasiz qolsa qolganlari buni ko'rsatmasdi.
    """
    phone, temporary = await _create_market_admin(api_client, auth_seed)
    headers = bearer(await _token(api_client, phone, temporary))

    listed = await api_client.get(USERS_URL, headers=headers)
    created = await _create_cashier(api_client, headers)
    audit = await api_client.get(AUDIT_URL, headers=headers)

    assert listed.status_code == created.status_code == audit.status_code == 403
    assert listed.json() == GATED
    assert created.json() == GATED
    assert audit.json() == GATED


async def test_the_gate_precedes_the_permission_check(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Huquqi YETMAYDIGAN must-change foydalanuvchi ham darvoza javobini oladi.

    `auth_seed.must_change` — nazoratchi, unda `USER_VIEW` YO'Q, ya'ni
    darvozasiz javob `forbidden` bo'lardi. Bu test tartibni qulflaydi:
    darvoza RBAC dan OLDIN hal bo'ladi. Aynan shu tartib
    `test_audit_read.py` va `test_users_api.py` dagi RBAC testlarini
    must-change foydalanuvchisidan ajratishga majbur qildi (T-01-83).
    """
    headers = await session_headers(api_client, auth_seed.must_change.phone, auth_seed.password)

    response = await api_client.get(USERS_URL, headers=headers)

    assert response.status_code == 403
    assert response.json() == GATED, "darvoza RBAC dan keyin ishlayapti"


async def test_session_endpoint_is_gated_too(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Huquq TALAB QILMAYDIGAN tenant endpointi (`GET /auth/me`) ham yopiq.

    `/auth/me` da `require_permission` YO'Q — u faqat `TenantSessionDep`
    ga tayanadi. Ya'ni bu test darvozaning AYNAN tenant sessiyasiga
    ulanganini isbotlaydi, huquq fabrikasiga emas.
    """
    headers = await session_headers(api_client, auth_seed.must_change.phone, auth_seed.password)

    response = await api_client.get(ME_URL, headers=headers)

    assert response.status_code == 403
    assert response.json() == GATED


# ---------------------------------------------------------------------------
# Darvoza OCHIQ qoladigan yo'llar
# ---------------------------------------------------------------------------


async def test_change_password_stays_open(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Parol almashtirish YO'LI yopilmaydi — aks holda darvoza abadiy qulf bo'lardi."""
    phone, temporary = await _create_market_admin(api_client, auth_seed)
    headers = bearer(await _token(api_client, phone, temporary))

    response = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": temporary, "new_password": NEW_PASSWORD},
        headers=headers,
    )

    assert response.status_code == 204, response.text


async def test_logout_stays_open(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """Chiqish ham ochiq: qulflangan sessiyani tark etish imkoni qolishi kerak."""
    phone, temporary = await _create_market_admin(api_client, auth_seed)
    headers = bearer(await _token(api_client, phone, temporary))

    response = await api_client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 204, response.text


# ---------------------------------------------------------------------------
# Darvoza OCHILADI — nazorat holati (usiz yuqoridagilar RBAC bilan chalkashardi)
# ---------------------------------------------------------------------------


async def test_the_same_token_works_after_the_password_change(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """AYNAN O'SHA access token bilan darvoza ochiladi (kesh invalidatsiyasi).

    Token almashtirilmaydi — ya'ni test ikki narsani birga isbotlaydi:
      * 403 ning sababi HUQUQ EMAS edi (huquq token ichida, u o'zgarmadi);
      * `must_change_password` keshi (`user:state:{id}`, 30 s TTL) parol
        almashtirilgach DARHOL bekor qilinadi — TTL kutilmaydi.

    Ikkinchisisiz darvoza to'g'ri ishlab tursa ham foydalanuvchi parolni
    almashtirgandan keyin yana 30 soniya qulf ortida qolardi.
    """
    phone, temporary = await _create_market_admin(api_client, auth_seed)
    headers = bearer(await _token(api_client, phone, temporary))
    assert (await api_client.get(USERS_URL, headers=headers)).status_code == 403

    changed = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": temporary, "new_password": NEW_PASSWORD},
        headers=headers,
    )
    assert changed.status_code == 204, changed.text

    listed = await api_client.get(USERS_URL, headers=headers)
    audit = await api_client.get(AUDIT_URL, headers=headers)
    created = await _create_cashier(api_client, headers)

    assert listed.status_code == 200, listed.text
    assert audit.status_code == 200, audit.text
    assert created.status_code == 201, created.text


async def test_a_fresh_session_after_the_change_is_not_gated(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Yangi parol bilan qayta kirgan sessiya ham ochiq (bayroq DB'da o'chgan)."""
    phone, temporary = await _create_market_admin(api_client, auth_seed)
    temporary_headers = bearer(await _token(api_client, phone, temporary))
    changed = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": temporary, "new_password": NEW_PASSWORD},
        headers=temporary_headers,
    )
    assert changed.status_code == 204, changed.text

    reopened = await login(api_client, phone, NEW_PASSWORD)

    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["must_change_password"] is False
    headers = bearer(reopened.json()["access_token"])
    assert (await api_client.get(USERS_URL, headers=headers)).status_code == 200


# ---------------------------------------------------------------------------
# D-02 + D-08 — admin parolni tiklaganda darvoza DARHOL yopiladi
# ---------------------------------------------------------------------------


async def test_admin_password_reset_locks_the_live_session_immediately(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Parol tiklangach qurbonning MAVJUD access tokeni keyingi so'rovdayoq qulflanadi.

    Refresh tokenlarni bekor qilish YETARLI EMAS: access token yana 15
    daqiqa yaroqli qoladi. Ya'ni "parolim boshqasiga ma'lum" shubhasi bilan
    tiklangan hisob, darvozasiz, o'sha 15 daqiqada hech narsa yo'qotmasdi.

    Tekshiruv `GET /auth/me` bo'yicha ATAYIN: unda huquq talabi yo'q, ya'ni
    javob kodi faqat darvozaga bog'liq. `test_users_api.py` dagi bloklash
    testi bilan bir xil shakl — farqi bloklashda 401, bu yerda 403.
    """
    admin = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)
    victim = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)
    assert (await api_client.get(ME_URL, headers=victim)).status_code == 200

    reset = await api_client.post(
        f"{USERS_URL}/{auth_seed.cashier.user_id}/reset-password", headers=admin
    )

    assert reset.status_code == 200, reset.text
    response = await api_client.get(ME_URL, headers=victim)
    assert response.status_code == 403
    assert response.json() == GATED
