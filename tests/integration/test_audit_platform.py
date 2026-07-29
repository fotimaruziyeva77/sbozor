"""Platforma-global audit o'qish yo'li — `GET /api/v1/audit/platform` (Gap 5).

=============================================================================
BU FAYL UCHTA MUSTAQIL DA'VONI QULFLAYDI:

1. **YO'L BOR** (FOUND-03, Gap 5): `market_id IS NULL` yozuvlar — avvalo
   `login_failed` — nihoyat MAHSULOT yo'lidan o'qiladi. Ilgari ular NA
   `sbozor_app`, NA `sbozor_owner` roliga ko'rinardi va faqat klaster
   superuseri bilan tekshirilardi (01-06 -> 01-07 -> 01-09 zanjirida uch
   marta ochiq bo'shliq deb qayd etilgan).
2. **YO'L TOR** (CR-03): darvoza `users.is_platform_admin` BAYROG'IGA
   qaraydi, `platform_admin` ROLIGA emas. Farq nazariy emas: rol a'zolik
   qatoridan ham keladi, bayroq esa faqat platforma tayinlashidan.
3. **KO'RGANI YOZILADI** (D-09): platforma jurnalini ochish `action='read'`,
   `reason='platform_audit_view'` yozuvini hosil qiladi — tenant yo'lidan
   FARQ QILADIGAN `reason` bilan.

MARSHRUT `EXEMPT_ROUTES` DA, YA'NI CROSS-TENANT MATRITSASI UNGA QO'LLANMAYDI.
Istisno qonuniy (endpoint tenant RESURSI emas — u aynan bozorga tegishli
BO'LMAGAN qatorlarni beradi), lekin u matritsaning 401/403 da'volarini ham
olib tashlaydi. Shuning uchun ular BU YERDA qayta tiklangan:
`test_missing_token_is_rejected`, `test_market_admin_is_forbidden`,
`test_hybrid_platform_role_is_forbidden`. Ularsiz marshrut "istisno" degan
so'z bilan butunlay sinovsiz qolardi.
=============================================================================

DALIL HAR DOIM MAHSULOT OQIMIDAN TUG'ILADI: `market_id IS NULL` qatori
qo'lda INSERT qilinmaydi, u NOTO'G'RI PAROL bilan login urinishidan
paydo bo'ladi. Qo'lda qo'yilgan qator "funksiya NULL qatorni qaytaradi"
degan da'voni isbotlardi (u 01-14 da allaqachon isbotlangan), bu yerdagi
savol esa boshqacha: MAHSULOT yozgan yozuv MAHSULOT o'qish yo'lidan
ko'rinadimi.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fixtures.admin_api import (
    AUDIT_URL,
    USERS_URL,
    bearer,
    insert_audit_probe,
    new_phone,
    platform_admin_headers,
    session_headers,
)
from fixtures.auth_api import audit_rows, login
from sbozor_core.enums import AuditAction

if TYPE_CHECKING:
    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

PLATFORM_AUDIT_URL = f"{AUDIT_URL}/platform"

FORBIDDEN = {"detail": "forbidden"}
"""Bayroq darvozasining javobi."""

GATED = {"detail": "password_change_required"}
"""D-02 darvozasining javobi — `FORBIDDEN` DAN FARQ QILISHI shart.

Ikkalasi ham 403, lekin sabablari butunlay boshqacha va frontend ularga
turlicha javob beradi (biri "huquqingiz yo'q", ikkinchisi "parolni
almashtiring"). Testlar aynan `detail` ni tekshiradi, aks holda darvoza
va RBAC bir-birini yashirib qo'yardi (T-01-83 darsi).
"""

READ_REASON = "platform_audit_view"

PAGE_LIMIT = 200
"""So'rovlarda ATAYIN maksimal sahifa.

`market_id IS NULL` qatorlar butun test SESSIYASI davomida to'planadi
(jadval append-only, o'chirish yo'li yo'q) va ularni boshqa testlar ham
yozadi. Standart 50 lik sahifa bilan test "qidirilgan qator yo'q" deb
yiqilishi mumkin edi — sabab izolyatsiya emas, sahifa hajmi bo'lardi.
"""


async def _failed_login(api_client: httpx.AsyncClient) -> str:
    """Noto'g'ri parol bilan urinib `market_id IS NULL` qator hosil qiladi.

    Telefon HAR CHAQIRUVDA yangi: `login_failed` yozuvlari o'chirilmaydi va
    sessiya davomida to'planadi, ya'ni qat'iy marker bo'lmasa test boshqa
    testning qatorini ko'rib "o'tdi" deb qolardi.

    Javob 401 ekani ALOHIDA tekshiriladi: agar login biror sababga ko'ra
    muvaffaqiyatli bo'lib qolsa, `login_failed` qatori umuman yozilmasdi va
    keyingi assert "endpoint bo'sh qaytardi" deb noto'g'ri sababdan
    yiqilardi.
    """
    phone = new_phone()
    response = await login(api_client, phone, "butunlay-notogri-parol")
    assert response.status_code == 401, response.text
    return phone


def _phones(body: dict[str, Any]) -> set[str]:
    """Javobdagi `login_failed` yozuvlarining telefonlari."""
    return {
        item["new_value"]["phone"]
        for item in body["items"]
        if isinstance(item.get("new_value"), dict) and "phone" in item["new_value"]
    }


async def _platform_read_rows(
    tenant_session: TenantSessionFactory, auth_seed: AuthSeed
) -> list[Any]:
    """A bozoridagi `reason='platform_audit_view'` o'qish yozuvlari.

    Yozuv `principal.market_id` bilan tushadi, ya'ni bozor TANLAGAN
    platforma admini uchun u A bozorining jurnaliga yoziladi va oddiy
    tenant yo'lidan (ilova roli + RLS) o'qiladi — mahsulot qanday o'qisa,
    test ham shunday.
    """
    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action=str(AuditAction.READ))
    return [row for row in rows if (row.new_value or {}).get("reason") == READ_REASON]


# ---------------------------------------------------------------------------
# Gap 5 — yo'l BOR
# ---------------------------------------------------------------------------


async def test_platform_admin_sees_the_failed_login_row(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`login_failed` yozuvi platforma admini uchun KO'RINADI — Gap 5 ning yopilishi.

    Bu faylning asosiy da'vosi: FOUND-03 ning "kim tizimga kirishga
    urinmoqda" savoli nihoyat javobli. Yozuv `market_id IS NULL` bilan
    tushadi, ya'ni uni HECH QANDAY tenant konteksti ko'rmaydi — yagona
    yo'l shu endpoint.
    """
    phone = await _failed_login(api_client)
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.get(
        PLATFORM_AUDIT_URL, params={"limit": PAGE_LIMIT}, headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert phone in _phones(body), (
        "yangi yozilgan `login_failed` qatori platforma auditida ko'rinmadi — Gap 5 ochiq"
    )
    matched = [
        item
        for item in body["items"]
        if isinstance(item.get("new_value"), dict) and item["new_value"].get("phone") == phone
    ]
    assert len(matched) == 1
    assert matched[0]["action"] == str(AuditAction.LOGIN_FAILED)
    assert matched[0]["source"] == "app"
    assert matched[0]["new_value"]["reason"] == "unknown_phone"


async def test_platform_admin_without_a_selected_market_can_read(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bozor TANLAMAGAN platforma admini ham 200 oladi, 409 EMAS.

    Endpoint `AuthSessionDep` ga tayanadi, `TenantSessionDep` ga emas —
    o'qiladigan qatorlarning tenant konteksti umuman yo'q. Bu qaror shu
    yerda qulflanadi: kimdir uni "boshqa endpointlar kabi" tenant
    sessiyasiga o'tkazsa, bozor tanlamagan admin `market_not_selected`
    olardi va platforma darajasidagi hodisalarni ko'rish uchun ma'nosiz
    ravishda biror bozorni tanlashga majbur bo'lardi.
    """
    phone = await _failed_login(api_client)
    headers = await session_headers(api_client, auth_seed.platform_admin.phone, auth_seed.password)

    response = await api_client.get(
        PLATFORM_AUDIT_URL, params={"limit": PAGE_LIMIT}, headers=headers
    )

    assert response.status_code != 409, "bozor tanlanmagani uchun rad etildi — tenant sessiyasi?"
    assert response.status_code == 200, response.text
    assert phone in _phones(response.json())


async def test_tenant_rows_are_never_returned(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Javobda A bozorining (`market_id NOT NULL`) qatorlari YO'Q.

    Endpoint "RLS'siz butun jurnalni o'qish" vositasiga aylanib
    ketmasligi kerak: funksiyaning sharti LITERAL `market_id IS NULL`.
    Nazorat holati MAJBURIY (`platform_marker`): usiz javob butunlay
    bo'sh bo'lganda ham test yashil bo'lardi va hech nimani isbotlamasdi.
    """
    tenant_marker = f"tenant-{uuid4().hex}"
    insert_audit_probe(
        sync_owner_conn,
        auth_seed.market_a_id,
        table_name="probe_table",
        new_value=json.dumps({"marker": tenant_marker}),
    )
    platform_marker = await _failed_login(api_client)
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.get(
        PLATFORM_AUDIT_URL, params={"limit": PAGE_LIMIT}, headers=headers
    )

    assert response.status_code == 200, response.text
    assert platform_marker in _phones(response.json()), "nazorat qatori ham ko'rinmadi"
    assert tenant_marker not in response.text, (
        "A bozorining audit qatori platforma javobida ko'rindi — funksiya sharti buzilgan"
    )


# ---------------------------------------------------------------------------
# CR-03 — yo'l TOR: bayroq, rol EMAS
# ---------------------------------------------------------------------------


async def test_market_admin_is_forbidden(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`is_platform_admin = false` -> 403, `AUDIT_VIEW` huquqi BOR bo'lsa ham.

    Bozor admini ATAYIN tanlandi: unda `AUDIT_VIEW` bor va u
    `GET /api/v1/audit` ni bemalol o'qiydi. Ya'ni 403 ning yagona sababi
    — bayroq. Kassir bilan sinalganda javob huquq yetishmasligidan ham
    kelishi mumkin edi va test darvozani emas, RBAC ni sinagan bo'lardi.
    """
    headers = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)
    tenant = await api_client.get(AUDIT_URL, headers=headers)

    response = await api_client.get(PLATFORM_AUDIT_URL, headers=headers)

    assert tenant.status_code == 200, "nazorat: bozor admini o'z jurnalini ko'ra olishi kerak"
    assert response.status_code == 403
    assert response.json() == FORBIDDEN


async def test_hybrid_platform_role_is_forbidden(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`roles=['platform_admin']` + `is_platform_admin=false` -> 403 (CR-03, T-01-91).

    BU FAYLNING ENG MUHIM TESTI. Darvoza rolga qaraganda bu hisob o'tib
    ketardi: unda `platform_admin` roli BOR (a'zolik qatorida) va shu
    orqali barcha platforma-huquqlari hisoblanadi. Bayroq esa `false`.

    Bunday hisobni 01-11 dan keyin API orqali yaratib bo'lmaydi
    (`_assert_roles_assignable` `platform_admin` ni har doim rad etadi),
    shuning uchun u seed'da to'g'ridan-to'g'ri yoziladi — aynan shu
    regressiya yo'lini ochiq qoldirmaslik uchun.

    Agar bu test bir kun qizarsa, demak darvoza `require_roles(...)` yoki
    biror huquqqa qaytarilgan va platforma-global jurnal bozor darajasida
    "qo'lga kiritiladigan" qiymatga bog'lanib qolgan.
    """
    headers = await session_headers(
        api_client, auth_seed.hybrid_platform_role.phone, auth_seed.password
    )

    response = await api_client.get(PLATFORM_AUDIT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json() == FORBIDDEN


async def test_missing_token_is_rejected(api_client: httpx.AsyncClient) -> None:
    """Tokensiz so'rov 401 — cross-tenant matritsasi bu marshrutni qamramaydi."""
    response = await api_client.get(PLATFORM_AUDIT_URL)

    assert response.status_code == 401


async def test_must_change_platform_admin_is_gated(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Vaqtinchalik parolli platforma admini avval parolni almashtiradi (D-02, T-01-92).

    Bayroq `true` bo'lgani darvozani ochib yubormaydi: `require_platform_admin`
    `CurrentPasswordDep` ga bog'langan, ya'ni D-02 tekshiruvi bayroq
    tekshiruvidan OLDIN hal bo'ladi.

    Holat MAHSULOT OQIMIDAN tug'iladi (bozor admini parolni tiklaydi),
    seed bayrog'ini qo'lda burab emas: zanjirning o'zi (tiklash ->
    `must_change_password=true` -> kesh invalidatsiyasi -> darvoza) shu
    testda qamraladi.

    `detail` MAJBURIY tekshiriladi: javob `forbidden` bo'lib qolsa,
    foydalanuvchi "huquqingiz yo'q" xabarini ko'rib parolni almashtirish
    ekraniga umuman yo'naltirilmasdi.
    """
    admin = await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)
    reset = await api_client.post(
        f"{USERS_URL}/{auth_seed.platform_admin.user_id}/reset-password", headers=admin
    )
    assert reset.status_code == 200, reset.text

    reopened = await login(
        api_client, auth_seed.platform_admin.phone, reset.json()["temporary_password"]
    )
    assert reopened.status_code == 200, reopened.text

    response = await api_client.get(
        PLATFORM_AUDIT_URL, headers=bearer(reopened.json()["access_token"])
    )

    assert response.status_code == 403
    assert response.json() == GATED, "darvoza bayroq tekshiruvidan keyin ishlayapti"


# ---------------------------------------------------------------------------
# D-09 — ko'rgani YOZILADI
# ---------------------------------------------------------------------------


async def test_viewing_the_platform_log_writes_a_read_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """O'qish yozuvi `reason='platform_audit_view'` bilan tushadi.

    `reason` tenant yo'lidagi `audit_view` DAN FARQ QILISHI shart: jurnalni
    o'qiyotgan odam "bozor admini o'z jurnalini ochdi" va "platforma
    admini platforma-global hodisalarni ko'rdi" ni ajrata olishi kerak.

    `filters` va `result_count` ham tekshiriladi — usiz yozuv "o'qildi"
    deyishdan nariga o'tmasdi va "kim butun jurnalni yuklab oldi" savoliga
    javob bermasdi.
    """
    headers = await platform_admin_headers(api_client, auth_seed)
    before = await _platform_read_rows(tenant_session, auth_seed)

    response = await api_client.get(
        PLATFORM_AUDIT_URL, params={"limit": PAGE_LIMIT}, headers=headers
    )
    assert response.status_code == 200, response.text

    after = await _platform_read_rows(tenant_session, auth_seed)
    assert len(after) == len(before) + 1
    row = after[-1]
    assert row.table_name == "audit_log"
    assert row.source == "app"
    assert row.actor_user_id == auth_seed.platform_admin.user_id
    assert row.new_value["result_count"] == len(response.json()["items"])
    assert row.new_value["filters"] == {"limit": PAGE_LIMIT}


async def test_rejected_request_writes_no_read_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """403 olgan hisob hech narsani o'qimagan — yozuv ham bo'lmasligi kerak.

    Ikki qatlam birga ishlaydi: `require_platform_admin` `audit_read` dan
    OLDIN e'lon qilingan (FastAPI dependency'larni shu tartibda hal
    qiladi), va yozuv `BackgroundTasks` orqali ketadi — u esa faqat
    MUVAFFAQIYATLI javobga biriktiriladi.

    Jurnaldagi YOLG'ON dalil ("bozor admini platforma jurnalini o'qidi")
    jurnalning bo'sh qolishidan ham yomonroq: nizoni hal qilayotgan odam
    aynan shu yozuvga tayanadi.
    """
    market_admin = await session_headers(
        api_client, auth_seed.market_admin.phone, auth_seed.password
    )
    before = len(await _platform_read_rows(tenant_session, auth_seed))

    rejected = await api_client.get(PLATFORM_AUDIT_URL, headers=market_admin)

    assert rejected.status_code == 403
    assert len(await _platform_read_rows(tenant_session, auth_seed)) == before


# ---------------------------------------------------------------------------
# Sahifalash — tenant yo'li bilan AYNAN bir xil semantika
# ---------------------------------------------------------------------------


async def test_keyset_pagination_does_not_repeat_the_boundary_row(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`limit=1` + `cursor`: chegara qatori keyingi sahifada TAKRORLANMAYDI.

    Kursor OPAQUE — test uning ichini o'qimaydi, faqat javobdan olib
    keyingi so'rovga qaytaradi. Kodlash `audit_repo` bilan bir xil
    (`encode_cursor`/`decode_cursor`), ya'ni ikkala endpoint mijoz uchun
    bir xil xulq ko'rsatadi.
    """
    await _failed_login(api_client)
    headers = await platform_admin_headers(api_client, auth_seed)

    first = await api_client.get(PLATFORM_AUDIT_URL, params={"limit": 1}, headers=headers)
    assert first.status_code == 200, first.text
    assert len(first.json()["items"]) == 1
    cursor = first.json()["next_cursor"]
    assert cursor, "keyingi sahifa bor, lekin kursor berilmadi"

    second = await api_client.get(
        PLATFORM_AUDIT_URL, params={"limit": PAGE_LIMIT, "cursor": cursor}, headers=headers
    )

    assert second.status_code == 200, second.text
    ids = [item["id"] for item in second.json()["items"]]
    assert first.json()["items"][0]["id"] not in ids, "kursor chegara qatorini TAKRORLADI"
    assert ids == sorted(ids, reverse=True), "tartib `at DESC, id DESC` emas"


async def test_malformed_cursor_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Buzuq kursor 422 — jimgina birinchi sahifaga QAYTMAYDI (tenant yo'li bilan bir xil)."""
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.get(
        PLATFORM_AUDIT_URL, params={"cursor": "not-a-cursor"}, headers=headers
    )

    assert response.status_code == 422


async def test_limit_above_the_maximum_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`limit=500` -> 422 (T-01-57: chegarasiz so'rov o'z-o'ziga DoS)."""
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.get(PLATFORM_AUDIT_URL, params={"limit": 500}, headers=headers)

    assert response.status_code == 422
