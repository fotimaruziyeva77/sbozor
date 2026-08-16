"""Ikki bosqichli foydalanuvchi boshqaruvi (D-04, D-02, D-08).

=============================================================================
BU FAYLNING ENG MUHIM UCHLIGI — ROL BERISH DARAJASINING UCHTA RAD ETISHI:

    market_admin -> market_admin    403 role_not_allowed
    market_admin -> director        403 role_not_allowed
    market_admin -> platform_admin  403 role_not_allowed

Uchtasi ALOHIDA yozilgan, `pytest.mark.parametrize` bilan bitta testga
siqilmagan. Sabab: ular UCHTA BOSHQA hujumni yopadi va biri o'chib qolsa
buni nom bo'yicha ko'rish kerak. `platform_admin` — eng ko'zga tashlanadigan
holat va odatda birinchi bo'lib yopiladi; `market_admin` esa eng nozigi —
"o'ziga teng rol berish" zararsizdek tuyuladi, aslida esa bozor admini
cheksiz sonli teng huquqli admin tug'dira olishini bildiradi va D-04 ning
ikki bosqichli modelini butunlay yo'q qiladi.

Har bir rad etish IKKI narsani tekshiradi: javob kodi VA bazada qoldiq
qolmagani (yaratish umuman boshlanmagani).

TO'RTINCHISI — 01-11 da qo'shilgan va u yuqoridagi uchtasidan BOSHQA
qatlamda turadi:

    platform_admin -> platform_admin  403 role_not_allowed

Bu D-04 ning "platforma admini cheklovsiz" bandidagi YAGONA istisno
(CR-03). Uchlik faqat `is_platform_admin=False` chaqiruvchini sinagani
uchun bu yo'l uzoq vaqt hech qanday test bilan qoplanmagan edi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fixtures.admin_api import (
    AUDIT_URL,
    USERS_URL,
    audit_entries,
    new_phone,
    platform_admin_headers,
    session_headers,
)
from fixtures.auth_api import CHANGE_PASSWORD_URL, ME_URL, REFRESH_URL, login
from sbozor_core.enums import AuditAction

if TYPE_CHECKING:
    from uuid import UUID

    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

FORBIDDEN_ROLES = ("market_admin", "director", "platform_admin")
"""Bozor admini bera OLMAYDIGAN rollar (D-04) — hujjat sifatida ham qoladi."""

ONBOARDED_PASSWORD = "onboard-uzun-parol-2026"  # noqa: S105 — test ma'lumoti
"""API orqali yaratilgan foydalanuvchining majburiy almashtirishdan keyingi paroli."""


async def _market_admin_headers(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> dict[str, str]:
    """A bozori adminining sessiyasi (a'zolik bitta -> bozor avtomatik tanlanadi)."""
    return await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)


async def _create(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    roles: list[str],
    phone: str | None = None,
    full_name: str = "Test foydalanuvchi",
) -> httpx.Response:
    """`POST /api/v1/users` — testlarning eng ko'p takrorlanadigan qadami."""
    return await api_client.post(
        USERS_URL,
        json={
            "phone": phone if phone is not None else new_phone(),
            "full_name": full_name,
            "roles": roles,
            "locale": "uz-Latn",
        },
        headers=headers,
    )


async def _onboarded_headers(
    api_client: httpx.AsyncClient, phone: str, temporary: str
) -> dict[str, str]:
    """Vaqtinchalik parol -> MAJBURIY almashtirish -> sessiya (D-02 haqiqiy oqimi).

    01-11 dan boshlab `require_password_current` must-change sessiyani har
    qanday tenant endpointida 403 `password_change_required` bilan rad
    etadi. Ya'ni RBAC da'vosini sinamoqchi bo'lgan test AVVAL parolni
    almashtirishi SHART — aks holda u 403 oladi-yu, sababi huquq
    yetishmasligi emas, darvoza bo'lardi.

    Assert'ni `password_change_required` ga bo'shashtirish MUQOBIL EMAS:
    o'shanda test yashil bo'lardi va D-07 huquq matritsasi haqida hech
    narsa isbotlamasdi (aynan shu green-for-wrong-reason naqshi 01-11 da
    yopilmoqda).
    """
    temporary_headers = await session_headers(api_client, phone, temporary)
    changed = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": temporary, "new_password": ONBOARDED_PASSWORD},
        headers=temporary_headers,
    )
    assert changed.status_code == 204, changed.text
    return await session_headers(api_client, phone, ONBOARDED_PASSWORD)


def _phone_exists(conn: Connection[TupleRow], phone: str) -> bool:
    """`users` da telefon bormi — `sbozor_owner` bilan (app-rolga jadval yopiq)."""
    row = conn.execute("SELECT 1 FROM users WHERE phone_e164 = %s", (phone,)).fetchone()
    return row is not None


def _membership_count(conn: Connection[TupleRow], market_id: UUID) -> int:
    """Bozordagi a'zolik qatorlari soni."""
    row = conn.execute(
        "SELECT count(*) FROM user_market_roles WHERE market_id = %s", (str(market_id),)
    ).fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# D-04 — ikki bosqichli yaratish
# ---------------------------------------------------------------------------


async def test_market_admin_creates_cashier_and_inspector(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bozor admini AYNAN shu ikki rolni bera oladi (D-04 ikkinchi bosqichi)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    cashier = await _create(api_client, headers, roles=["cashier"])
    both = await _create(api_client, headers, roles=["cashier", "inspector"])

    assert cashier.status_code == 201, cashier.text
    assert both.status_code == 201, both.text
    assert cashier.json()["temporary_password"]
    # Ikkalasi ham HAR XIL parol oladi — vaqtinchalik parol tasodifiy.
    assert cashier.json()["temporary_password"] != both.json()["temporary_password"]


@pytest.mark.parametrize("role", FORBIDDEN_ROLES)
async def test_market_admin_cannot_assign_privileged_role_leaves_no_trace(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
    role: str,
) -> None:
    """Rad etilgan urinish bazada QOLDIQ QOLDIRMAYDI (uchala rol uchun).

    Nomlangan uchta test (pastda) javob kodini qulflaydi; bu esa
    ularning umumiy INVARIANTINI — "yaratish umuman boshlanmaydi" —
    bir joyda tekshiradi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    phone = new_phone()
    before = _membership_count(sync_owner_conn, auth_seed.market_a_id)

    response = await _create(api_client, headers, roles=[role], phone=phone)

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}
    assert not _phone_exists(sync_owner_conn, phone), f"{role}: `users` da qator qoldi"
    assert _membership_count(sync_owner_conn, auth_seed.market_a_id) == before


async def test_market_admin_cannot_create_market_admin(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """O'ZIGA TENG rol berish rad etiladi — D-04 ning eng nozik holati."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["market_admin"])

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}


async def test_market_admin_cannot_create_director(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Direktor — bozor admininING NAZORATCHISI, uni admin yarata olmaydi."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["director"])

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}


async def test_market_admin_cannot_create_platform_admin(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Platforma admini — bozordan yuqori daraja (D-06)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["platform_admin"])

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}


async def test_market_admin_cannot_smuggle_role_in_a_larger_set(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Ruxsat etilgan rol bilan ARALASHTIRIB berish ham rad etiladi.

    `["cashier", "director"]` — darvoza QISM TO'PLAM tekshiruvi bo'lgani
    uchun rad etiladi. "Ro'yxatda bittasi ruxsat etilgan" shaklidagi
    tekshiruv bu yerda jimgina o'tkazib yuborardi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["cashier", "director"])

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}


async def test_platform_admin_creates_market_admin_and_director(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-04 BIRINCHI bosqichi: platforma admini bozor rahbariyatini yaratadi."""
    headers = await platform_admin_headers(api_client, auth_seed)

    admin = await _create(api_client, headers, roles=["market_admin"])
    director = await _create(api_client, headers, roles=["director"])

    assert admin.status_code == 201, admin.text
    assert director.status_code == 201, director.text


async def test_platform_admin_cannot_assign_the_platform_admin_role(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """PLATFORMA ADMINI HAM `platform_admin` rolini bera olmaydi (CR-03, T-01-81).

    Bu D-04 ning "cheklovsiz" bandidagi YAGONA istisno va u shu yerda
    qulflanadi. Sabab tuzilmaviy: `platform_admin` — `users.is_platform_admin`
    bayrog'i, a'zolik roli EMAS. Uni `user_market_roles.roles` ga yozish
    GIBRID hisob yaratadi (rol bor, bayroq yo'q), u esa `permissions_for()`
    orqali `MARKET_VIEW_ALL` ni oladi.

    Yuqoridagi `test_market_admin_cannot_create_platform_admin` bozor
    admini yo'lini qoplaydi; darvoza AYNAN platforma admini uchun ham
    yopilganini faqat SHU test isbotlaydi — o'sha paytda mavjud
    testlarning hammasi `is_platform_admin=False` chaqiruvchi bilan
    ishlagani uchun teshik yillar davomida yashil qolgan edi.

    Qoldiqsizlik ham tekshiriladi (D-04 rad etish naqshi): rad etish
    `auth_create_user` dan OLDIN sodir bo'ladi.
    """
    headers = await platform_admin_headers(api_client, auth_seed)
    phone = new_phone()
    before = _membership_count(sync_owner_conn, auth_seed.market_a_id)

    response = await _create(api_client, headers, roles=["platform_admin"], phone=phone)

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}
    assert not _phone_exists(sync_owner_conn, phone), "`users` da qator qoldi"
    assert _membership_count(sync_owner_conn, auth_seed.market_a_id) == before


async def test_platform_admin_cannot_smuggle_the_platform_admin_role(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Ruxsat etilgan rol bilan ARALASHTIRIB berish ham rad etiladi.

    `["cashier", "platform_admin"]` — darvoza to'plamning ICHIDA qidiradi,
    ya'ni "birinchi rol ruxsat etilgan" shaklidagi tekshiruv bu yerda
    jimgina o'tkazib yuborardi.
    """
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["cashier", "platform_admin"])

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}


async def test_empty_roles_is_rejected(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """Rolsiz foydalanuvchi yaratilmaydi — 422 (kontrakt shakli buzilgan).

    403 EMAS: so'rovda huquq muammosi yo'q, so'rovning O'ZI yaroqsiz.
    Rolsiz a'zolik qatori `ck_user_market_roles_roles_not_empty` bilan
    baribir rad etilardi, lekin o'shanda javob 500 bo'lardi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=[])

    assert response.status_code == 422


async def test_unknown_role_is_rejected(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """Enum'da yo'q rol nomi DB'ga yetib bormaydi (422)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["superuser"])

    assert response.status_code == 422


async def test_phone_taken_returns_409(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """Mavjud telefon -> 409 `phone_taken` (D-01: telefon yagona identifikator)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await _create(api_client, headers, roles=["cashier"], phone=auth_seed.cashier.phone)

    assert response.status_code == 409
    assert response.json() == {"detail": "phone_taken"}


# ---------------------------------------------------------------------------
# D-02 — vaqtinchalik parol va majburiy almashtirish
# ---------------------------------------------------------------------------


async def test_created_user_must_change_password_on_first_login(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Yaratilgan foydalanuvchi vaqtinchalik parol bilan kiradi va bayroq KO'TARILGAN."""
    headers = await _market_admin_headers(api_client, auth_seed)
    phone = new_phone()
    created = await _create(api_client, headers, roles=["cashier"], phone=phone)
    assert created.status_code == 201, created.text

    response = await login(api_client, phone, created.json()["temporary_password"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["must_change_password"] is True
    assert body["roles"] == ["cashier"]
    assert body["market"]["id"] == str(auth_seed.market_a_id)


async def test_reset_password_issues_a_working_temporary_password(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-02: admin yangi vaqtinchalik parol beradi, ESKISI ishlamay qoladi."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.post(
        f"{USERS_URL}/{auth_seed.cashier.user_id}/reset-password", headers=headers
    )

    assert response.status_code == 200, response.text
    temporary = response.json()["temporary_password"]

    with_new = await login(api_client, auth_seed.cashier.phone, temporary)
    with_old = await login(api_client, auth_seed.cashier.phone, auth_seed.password)

    assert with_new.status_code == 200
    assert with_new.json()["must_change_password"] is True
    assert with_old.status_code == 401


# ---------------------------------------------------------------------------
# D-08 — bloklash va cross-tenant chegara
# ---------------------------------------------------------------------------


async def test_block_takes_effect_on_next_request(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bloklashdan keyin BIRINCHI so'rovdayoq 401 — hech qanday kutish yo'q.

    Bu 01-06 dagi `test_user_block.py` dan FARQ QILADI: u yerda kesh
    testda qo'lda bo'shatilgan edi, bu yerda esa uni ENDPOINTNING O'ZI
    bo'shatishi kerak (D-08 ning mahsulot yo'li).
    """
    admin = await _market_admin_headers(api_client, auth_seed)
    victim = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)
    assert (await api_client.get(ME_URL, headers=victim)).status_code == 200

    blocked = await api_client.post(f"{USERS_URL}/{auth_seed.cashier.user_id}/block", headers=admin)

    assert blocked.status_code == 204
    response = await api_client.get(ME_URL, headers=victim)
    assert response.status_code == 401
    assert response.json() == {"detail": "account_blocked"}


async def test_unblock_restores_access(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """NAZORAT HOLATI: tiklash ham DARHOL kuchga kiradi.

    Usiz `block` testi kesh butunlay o'chirilgan holatda ham yashil
    bo'lardi — ya'ni invalidatsiyaning ishlayotgani isbotlanmasdi.
    """
    admin = await _market_admin_headers(api_client, auth_seed)
    victim = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)
    await api_client.post(f"{USERS_URL}/{auth_seed.cashier.user_id}/block", headers=admin)
    assert (await api_client.get(ME_URL, headers=victim)).status_code == 401

    unblocked = await api_client.post(
        f"{USERS_URL}/{auth_seed.cashier.user_id}/unblock", headers=admin
    )

    assert unblocked.status_code == 204
    assert (await api_client.get(ME_URL, headers=victim)).status_code == 200


async def test_cannot_block_self(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """O'zini bloklash 400 — bozor boshqaruvsiz qolmasligi kerak."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.post(
        f"{USERS_URL}/{auth_seed.market_admin.user_id}/block", headers=headers
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "cannot_block_self"}


async def test_cross_tenant_block_and_reset_return_404(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Boshqa bozor foydalanuvchisi -> 404, 403 EMAS (T-01-51).

    403 javobining O'ZI "bunday foydalanuvchi bor" degan ma'lumotni
    oshkor qilardi. RLS ostida o'sha qator A bozori uchun MAVJUD EMAS,
    ya'ni 404 — yolg'on emas, aynan haqiqat.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    outsider = auth_seed.other_market_admin.user_id

    blocked = await api_client.post(f"{USERS_URL}/{outsider}/block", headers=headers)
    reset = await api_client.post(f"{USERS_URL}/{outsider}/reset-password", headers=headers)

    assert blocked.status_code == 404
    assert reset.status_code == 404
    assert blocked.json() == reset.json() == {"detail": "not_found"}


async def test_unknown_user_id_and_cross_tenant_are_indistinguishable(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Mavjud bo'lmagan ID va begona bozor ID'si AYNAN bir xil javob beradi.

    Javob tanasi bayt-bayt solishtiriladi: farq paydo bo'lgan kun
    enumeration teshigi jimgina ochiladi (01-06 dagi login testi bilan
    bir xil qoida).
    """
    headers = await _market_admin_headers(api_client, auth_seed)

    unknown = await api_client.post(
        f"{USERS_URL}/00000000-0000-4000-8000-000000000000/block", headers=headers
    )
    foreign = await api_client.post(
        f"{USERS_URL}/{auth_seed.other_market_admin.user_id}/block", headers=headers
    )

    assert unknown.status_code == foreign.status_code == 404
    assert unknown.content == foreign.content


# ---------------------------------------------------------------------------
# D-07 — huquq matritsasi
# ---------------------------------------------------------------------------


async def test_cashier_and_director_cannot_manage_users(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Kassir ham, DIREKTOR ham foydalanuvchi yarata olmaydi (D-07).

    Direktor bu yerda AYNAN D-04 ning birinchi bosqichi orqali yaratiladi
    (platforma admini tomonidan) — ya'ni test bir vaqtda uch narsani
    isbotlaydi: direktor yaratish ISHLAYDI, u D-02 oqimidan o'tib to'liq
    faol sessiya oladi va SHUNDAN KEYIN HAM `USER_MANAGE` huquqiga EGA
    EMAS.

    Kassir seed'dan olinadi (`must_change=false`), direktor esa
    `_onboarded_headers()` bilan parolini almashtiradi — ikkalasining ham
    so'rovi RBAC qatlamiga YETIB BORADI va javob `forbidden` bo'ladi,
    `password_change_required` EMAS (01-11 test-yaxlitligi).
    """
    platform = await platform_admin_headers(api_client, auth_seed)
    director_phone = new_phone()
    created = await _create(api_client, platform, roles=["director"], phone=director_phone)
    assert created.status_code == 201, created.text

    cashier = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)
    director = await _onboarded_headers(
        api_client, director_phone, created.json()["temporary_password"]
    )

    cashier_attempt = await _create(api_client, cashier, roles=["cashier"])
    director_attempt = await _create(api_client, director, roles=["cashier"])

    assert cashier_attempt.status_code == 403
    assert director_attempt.status_code == 403
    assert cashier_attempt.json() == {"detail": "forbidden"}
    assert director_attempt.json() == {"detail": "forbidden"}


async def test_cashier_cannot_list_users(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Kassirda `USER_VIEW` ham yo'q — u aynan `{PAYMENT_CREATE}` (D-07)."""
    headers = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)

    response = await api_client.get(USERS_URL, headers=headers)

    assert response.status_code == 403


async def test_list_users_returns_only_current_market_members(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Ro'yxatda FAQAT joriy bozor a'zolari (RLS + ikki qatlamli o'qish)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.get(USERS_URL, headers=headers)

    assert response.status_code == 200, response.text
    phones = {item["phone"] for item in response.json()["items"]}
    assert auth_seed.market_admin.phone in phones
    assert auth_seed.cashier.phone in phones
    assert auth_seed.other_market_admin.phone not in phones


# ---------------------------------------------------------------------------
# T-01-52 — vaqtinchalik parol jurnalga tushmaydi
# ---------------------------------------------------------------------------


async def test_temp_password_not_in_audit(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`insert` va `password_reset` yozuvlarida parol ham, hash ham YO'Q.

    Tekshiruv JSONB'ning MATNI bo'yicha: kalit nomini emas, qiymatning
    o'zini qidiradi. Kalit bo'yicha tekshirish "parol boshqa nom bilan
    yozib qo'yilgan" holatni o'tkazib yuborardi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    created = await _create(api_client, headers, roles=["cashier"])
    assert created.status_code == 201, created.text
    temporary = created.json()["temporary_password"]

    reset = await api_client.post(
        f"{USERS_URL}/{auth_seed.cashier.user_id}/reset-password", headers=headers
    )
    assert reset.status_code == 200, reset.text
    reset_temporary = reset.json()["temporary_password"]

    rows = await audit_entries(tenant_session, auth_seed.market_a_id)
    actions = {row.action for row in rows}
    assert str(AuditAction.INSERT) in actions
    assert str(AuditAction.PASSWORD_RESET) in actions

    serialized = repr([(row.old_value, row.new_value) for row in rows])
    assert temporary not in serialized
    assert reset_temporary not in serialized
    assert "password_hash" not in serialized
    assert "argon2" not in serialized.lower()


# ---------------------------------------------------------------------------
# №G — MAVJUD FOYDALANUVCHINING ROLLARINI TAHRIRLASH (`PATCH /{id}/roles`)
#
# =============================================================================
# BU BLOKNING ENG MUHIM DA'VOSI — D-04 DARAJASI IKKI YO'NALISHDA ISHLAYDI.
#
# Yaratish darvozasi («bozor admini direktor YARATA olmaydi») yolg'iz
# o'zi TESKARI teshikni ochiq qoldirardi: bozor admini mavjud direktorni
# yoki teng adminni BITTA so'rov bilan kassirga PASAYTIRIB, o'z
# nazoratchisini yo'q qila olardi. Shuning uchun endpoint IKKALA
# to'plamni ham darvozadan o'tkazadi — JORIYSINI ham, YANGISINI ham
# (B5/B6 juftligi aynan shuni ajratadi).
#
# IKKINCHI MUHIM DA'VO — AUDIT YOZUVI YANGI KOD EMAS. `user_market_roles`
# `0002_audit.py` dagi `AUDITED_TABLE`, ya'ni `fn_audit_row()` triggeri
# har `UPDATE` uchun `old`/`new` bilan qator qo'yadi. Ilova darajasidagi
# ikkinchi `write_app_audit()` DUBLIKAT bo'lardi va B2 uning
# YO'QLIGINI ham o'lchaydi.
# =============================================================================


def _roles_url(user_id: object) -> str:
    """`PATCH /api/v1/users/{id}/roles` — `POST` EMAS.

    `/block` va `/reset-password` — HODISALAR (yon ta'siri bor amallar);
    rollar esa resursning MAYDONI. `nvr.py` dagi `PATCH /{nvr_id}` bilan
    aynan bir xil sabab.
    """
    return f"{USERS_URL}/{user_id}/roles"


async def _roles_of(
    api_client: httpx.AsyncClient, headers: dict[str, str], user_id: object
) -> list[str]:
    """`GET /users` dan bitta a'zoning rollari — DB holatining mahsulot yo'li."""
    response = await api_client.get(USERS_URL, headers=headers)
    assert response.status_code == 200, response.text
    item = next(row for row in response.json()["items"] if row["id"] == str(user_id))
    return list(item["roles"])


async def _seed_market_admin_target(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> str:
    """A bozorida `["market_admin"]` rolli IKKINCHI hisob (B5/B6 nishoni).

    Platforma admini yaratadi — D-04 ning birinchi bosqichi. `auth_seed`
    dagi bozor adminining O'ZI nishon bo'la olmaydi: u chaqiruvchi bilan
    bir xil va so'rov 1-darvozada (`cannot_change_own_roles`) to'xtardi,
    ya'ni 3-darvoza (JORIY rollar) umuman o'lchanmasdi.
    """
    platform = await platform_admin_headers(api_client, auth_seed)
    created = await _create(api_client, platform, roles=["market_admin"])
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def test_market_admin_adds_inspector_to_a_cashier(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B1: rol qo'shish ISHLAYDI va ro'yxat IKKALA rolni qaytaradi."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id),
        json={"roles": ["cashier", "inspector"]},
        headers=headers,
    )

    assert response.status_code == 204, response.text
    assert sorted(await _roles_of(api_client, headers, auth_seed.cashier.user_id)) == [
        "cashier",
        "inspector",
    ]


async def test_role_change_is_audited_by_the_db_trigger_and_not_duplicated(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """B2: audit qatori TRIGGERDAN keladi va ilova darajasida DUBLIKAT YO'Q.

    ⚠ IKKI DA'VO BIR TESTDA ATAYIN: «yozildi» ni «ikki marta yozilmadi»
      dan ajratib bo'lmaydi — ikkinchisi birinchisining SIFATI. Alohida
      testda ikkinchisi «umuman yozilmadi» holatida ham yashil qolardi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    changed = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id),
        json={"roles": ["cashier", "inspector"]},
        headers=headers,
    )
    assert changed.status_code == 204, changed.text

    rows = await audit_entries(tenant_session, auth_seed.market_a_id)
    membership = [row for row in rows if row.table_name == "user_market_roles"]
    updates = [row for row in membership if row.action == str(AuditAction.UPDATE)]

    assert updates, "trigger `update` qatorini yozmadi"
    entry = updates[-1]
    assert entry.source == "db_trigger"
    assert entry.old_value["roles"] == ["cashier"]
    assert sorted(entry.new_value["roles"]) == ["cashier", "inspector"]
    assert entry.actor_user_id == auth_seed.market_admin.user_id

    # ⛔ ILOVA DARAJASIDAGI IKKINCHI YOZUV YO'Q — u dublikat bo'lardi.
    assert [row for row in membership if row.source == "app"] == []


async def test_cannot_change_own_roles(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """B3: o'z rolini o'zgartirish 400 va DB'da hech nima o'zgarmaydi.

    `cannot_block_self` bilan BIR XIL sinf: bozorda yagona admin o'zini
    pasaytirib qo'ysa, bozor boshqaruvsiz qoladi. Ikkinchi sabab — bu
    qoida o'z-o'zini KO'TARISH urinishini ham ifodalab bo'lmas qiladi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(auth_seed.market_admin.user_id),
        json={"roles": ["market_admin", "cashier"]},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "cannot_change_own_roles"}
    assert await _roles_of(api_client, headers, auth_seed.market_admin.user_id) == ["market_admin"]


async def test_market_admin_cannot_grant_the_director_role(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B4: YANGI to'plam darvozasi — mavjud D-04 tekshiruvi (4-qadam)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id),
        json={"roles": ["director"]},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}
    assert await _roles_of(api_client, headers, auth_seed.cashier.user_id) == ["cashier"]


async def test_market_admin_cannot_demote_an_equal_admin(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B5: JORIY rollar darvozasi (3-qadam) — D-04 ning TESKARI teshigi.

    ⚠ Bu testning yagona vazifasi — YANGI to'plam darvozasidan YASHIRIN
      farq qilish: so'ralayotgan `["cashier"]` bozor admini uchun to'liq
      ruxsat etilgan, ya'ni 4-qadam buni O'TKAZIB YUBORARDI. Rad etishni
      faqat NISHONNING joriy rollari keltirib chiqaradi.
    """
    target = await _seed_market_admin_target(api_client, auth_seed)
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(target), json={"roles": ["cashier"]}, headers=headers
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "role_not_allowed"}
    assert await _roles_of(api_client, headers, target) == ["market_admin"]


async def test_platform_admin_can_demote_the_same_market_admin(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B6: NAZORAT — AYNAN o'sha so'rov platforma adminida 204.

    Usiz B5 «endpoint hamma pasaytirishni rad etadi» holatida ham yashil
    qolardi, ya'ni darvozaning DARAJAGA bog'liqligi isbotlanmasdi.
    """
    target = await _seed_market_admin_target(api_client, auth_seed)
    platform = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(target), json={"roles": ["cashier"]}, headers=platform
    )

    assert response.status_code == 204, response.text
    assert await _roles_of(api_client, platform, target) == ["cashier"]


async def test_cross_tenant_role_change_returns_404(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B7: begona bozor a'zosi -> 404 `not_found`, 403 EMAS (T-01-51)."""
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(auth_seed.other_market_admin.user_id),
        json={"roles": ["cashier"]},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "not_found"}


async def test_new_roles_take_effect_after_refresh(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """B8: KUCHGA KIRISH LAHZASI o'lchanadi va HALOL aytiladi.

    Rollar JWT da'volarida yashaydi (`deps.py`), ya'ni pasaytirilgan
    foydalanuvchining QO'LIDAGI access token yana ≤15 daqiqa eski
    to'plam bilan ishlaydi. `/auth/refresh` esa huquqlarni HAR SAFAR
    DB'dan qayta o'qiydi — shuning uchun yangi to'plam keyingi token
    yangilanishida O'ZI kuchga kiradi va sessiyalarni bekor qilish
    KERAK EMAS. Darhol tortib olish yo'li — BLOKLASH (D-08).

    ⚠ TARTIB MUHIM: qurbon admin sessiyasidan KEYIN login qiladi, chunki
      `httpx` mijozi bitta va refresh cookie'si oxirgi loginniki bo'ladi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    victim_login = await login(api_client, auth_seed.cashier.phone, auth_seed.password)
    assert victim_login.status_code == 200, victim_login.text
    assert victim_login.json()["roles"] == ["cashier"]

    changed = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id),
        json={"roles": ["cashier", "inspector"]},
        headers=headers,
    )
    assert changed.status_code == 204, changed.text

    refreshed = await api_client.post(REFRESH_URL)

    assert refreshed.status_code == 200, refreshed.text
    assert sorted(refreshed.json()["roles"]) == ["cashier", "inspector"]


async def test_role_change_requires_user_manage(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """DARVOZA `USER_MANAGE`: direktorda `USER_VIEW` bor, bu esa yo'q (D-07)."""
    platform = await platform_admin_headers(api_client, auth_seed)
    director_phone = new_phone()
    created = await _create(api_client, platform, roles=["director"], phone=director_phone)
    assert created.status_code == 201, created.text
    director = await _onboarded_headers(
        api_client, director_phone, created.json()["temporary_password"]
    )

    response = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id),
        json={"roles": ["cashier", "inspector"]},
        headers=director,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


async def test_empty_roles_in_update_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bo'sh to'plam 422 — `CreateUserRequest` bilan AYNI shakl (`min_length=1`).

    403 EMAS: so'rovda huquq muammosi yo'q, so'rovning O'ZI yaroqsiz.
    Rolsiz a'zolik qatori `ck_user_market_roles_roles_not_empty` bilan
    baribir rad etilardi, lekin o'shanda javob 500 bo'lardi.
    """
    headers = await _market_admin_headers(api_client, auth_seed)

    response = await api_client.patch(
        _roles_url(auth_seed.cashier.user_id), json={"roles": []}, headers=headers
    )

    assert response.status_code == 422


async def test_created_user_is_visible_in_the_audit_api(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """UCHDAN-UCHIGA: yaratish yozuvi audit API'sida ko'rinadi va parolsiz.

    Bu 1- va 3-tasklarning bog'lanish nuqtasi: jurnalga YOZISH ham, uni
    KO'RISH ham bitta oqimda isbotlanadi. DB'ga to'g'ridan-to'g'ri
    qaraydigan `test_temp_password_not_in_audit` bu yo'lni qamramaydi —
    parol javob serializatsiyasida (masking) ham sizib chiqishi mumkin.
    """
    headers = await _market_admin_headers(api_client, auth_seed)
    phone = new_phone()
    created = await _create(api_client, headers, roles=["cashier"], phone=phone)
    assert created.status_code == 201, created.text

    response = await api_client.get(
        AUDIT_URL,
        params={"action": str(AuditAction.INSERT), "table_name": "users"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    entry = next(item for item in items if item["row_id"] == created.json()["id"])
    assert entry["new_value"]["phone"] == phone
    assert entry["new_value"]["roles"] == ["cashier"]
    assert "password_hash" not in entry["new_value"]
    assert created.json()["temporary_password"] not in repr(entry)
