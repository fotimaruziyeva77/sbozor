"""Profil, til tanlovi va bozor konteksti (D-13, D-06, FOUND-04).

=============================================================================
`test_locale_enum_matches_frontend_routing` NEGA BU YERDA:

Til kodlari IKKI joyda yozilgan va ular boshqa-boshqa tillarda:
`sbozor_core.enums.Locale` (Python) va `frontend/src/i18n/routing.ts`
(TypeScript). Ular ajralib qolsa, `PATCH /me {"locale":"uz-Cyrl"}` 200
qaytaradi-yu, frontend o'sha qiymat uchun marshrutga ega bo'lmaydi va
foydalanuvchi 404 ko'radi — ya'ni nosozlik BACKEND testlarida ko'rinmaydi.
Shuning uchun tekshiruv frontend faylining O'ZINI o'qiydi, nusxasini emas.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from fixtures.admin_api import MARKETS_URL, PROFILE_URL, platform_admin_headers, session_headers
from fixtures.auth_api import SELECT_MARKET_URL, audit_rows
from sbozor_core.enums import AuditAction, Locale

if TYPE_CHECKING:
    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_TS = REPO_ROOT / "frontend" / "src" / "i18n" / "routing.ts"

_LOCALES_ARRAY = re.compile(r"locales:\s*\[(?P<body>[^\]]*)\]", re.DOTALL)


def test_locale_enum_matches_frontend_routing() -> None:
    """`Locale` enum va `routing.ts` dagi `locales` massivi AYNAN bir xil."""
    source = ROUTING_TS.read_text(encoding="utf-8")
    match = _LOCALES_ARRAY.search(source)
    assert match is not None, f"{ROUTING_TS} da `locales: [...]` topilmadi"

    frontend_locales = set(re.findall(r'"([^"]+)"', match.group("body")))
    backend_locales = {locale.value for locale in Locale}

    assert frontend_locales == backend_locales


# ---------------------------------------------------------------------------
# D-13 — profil va til
# ---------------------------------------------------------------------------


async def test_me_returns_profile_and_session_context(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`GET /api/v1/me` profil maydonlarini va sessiya kontekstini qaytaradi."""
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)

    response = await api_client.get(PROFILE_URL, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(auth_seed.market_admin.user_id)
    assert body["phone"] == auth_seed.market_admin.phone
    assert body["locale"] == str(Locale.UZ_LATN)
    assert body["roles"] == ["market_admin"]
    assert body["market_id"] == str(auth_seed.market_a_id)
    assert body["is_platform_admin"] is False
    assert body["must_change_password"] is False


async def test_me_works_before_a_market_is_selected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Platforma admini bozor tanlashdan OLDIN ham profilini ko'radi.

    Aks holda til almashtirgich bozor tanlangunicha ishlamas edi —
    ya'ni foydalanuvchi tanlash ekranini o'zi tushunmaydigan tilda
    ko'rishi mumkin bo'lardi (D-13 ning butun maqsadiga zid).
    """
    headers = await session_headers(api_client, auth_seed.platform_admin.phone, auth_seed.password)

    response = await api_client.get(PROFILE_URL, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["market_id"] is None
    assert body["is_platform_admin"] is True


async def test_patch_locale_is_persisted_in_the_profile(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Til DB'da saqlanadi: `PATCH` dan keyin `GET` yangi qiymatni beradi."""
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)

    patched = await api_client.patch(PROFILE_URL, json={"locale": "ru"}, headers=headers)

    assert patched.status_code == 200, patched.text
    assert patched.json() == {"locale": "ru"}
    assert (await api_client.get(PROFILE_URL, headers=headers)).json()["locale"] == "ru"


async def test_locale_survives_a_new_login(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Til PROFILDA, sessiyada emas — qayta kirishda ham saqlanib qoladi.

    `POST /auth/login` javobidagi `locale` ham shu manbadan o'qiladi, ya'ni
    frontend birinchi so'rovdayoq to'g'ri prefiksni biladi.
    """
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)
    await api_client.patch(PROFILE_URL, json={"locale": "uz-Cyrl"}, headers=headers)

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"phone": auth_seed.market_admin.phone, "password": auth_seed.password},
    )

    assert response.status_code == 200, response.text
    assert response.json()["locale"] == "uz-Cyrl"


async def test_unknown_locale_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`en` — 422: qo'llab-quvvatlanmaydigan til DB'ga yetib bormaydi."""
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)

    response = await api_client.patch(PROFILE_URL, json={"locale": "en"}, headers=headers)

    assert response.status_code == 422


async def test_patch_locale_writes_an_audit_row_with_old_and_new(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Audit yozuvi "nimadan nimaga" savoliga javob beradi (D-12)."""
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)

    await api_client.patch(PROFILE_URL, json={"locale": "ru"}, headers=headers)

    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action=str(AuditAction.UPDATE))
    assert len(rows) == 1
    row = rows[0]
    assert row.table_name == "users"
    assert row.source == "app"
    assert row.actor_user_id == auth_seed.market_admin.user_id
    assert row.new_value == {"locale": "ru"}


# ---------------------------------------------------------------------------
# D-06 — bozor konteksti
# ---------------------------------------------------------------------------


async def test_markets_list_depends_on_market_view_all(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Platforma admini barcha bozorlarni, bozor admini AYNAN bittasini ko'radi."""
    admin_headers = await session_headers(
        api_client, auth_seed.market_admin.phone, auth_seed.password
    )
    platform_headers = await platform_admin_headers(api_client, auth_seed)

    admin_view = await api_client.get(MARKETS_URL, headers=admin_headers)
    platform_view = await api_client.get(MARKETS_URL, headers=platform_headers)

    assert admin_view.status_code == 200, admin_view.text
    assert platform_view.status_code == 200, platform_view.text

    admin_items = admin_view.json()
    assert len(admin_items) == 1
    assert admin_items[0]["id"] == str(auth_seed.market_a_id)
    assert admin_items[0]["timezone"] == "Asia/Tashkent"

    platform_ids = {item["id"] for item in platform_view.json()}
    assert {str(auth_seed.market_a_id), str(auth_seed.market_b_id)} <= platform_ids


async def test_platform_admin_sees_the_same_list_from_either_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Ro'yxat TANLANGAN bozorga bog'liq emas — u platforma darajasidagi ko'rinish.

    Bu nazorat holati: agar `MARKET_VIEW_ALL` yo'li tasodifan tenant
    so'roviga almashsa, B bozorini tanlagan admin faqat B ni ko'rardi va
    yuqoridagi test baribir yashil qolardi.
    """
    from_a = await platform_admin_headers(api_client, auth_seed, auth_seed.market_a_id)
    from_b = await platform_admin_headers(api_client, auth_seed, auth_seed.market_b_id)

    view_a = await api_client.get(MARKETS_URL, headers=from_a)
    view_b = await api_client.get(MARKETS_URL, headers=from_b)

    assert view_a.status_code == view_b.status_code == 200
    assert {item["id"] for item in view_a.json()} == {item["id"] for item in view_b.json()}


async def test_regular_user_cannot_select_another_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """A bozori admini B bozorini tanlay olmaydi — 403 (D-06)."""
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)

    response = await api_client.post(
        SELECT_MARKET_URL,
        json={"market_id": str(auth_seed.market_b_id)},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "market_forbidden"}
