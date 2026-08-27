"""Sotuvchilar API'sining xulqi — MARKET-04 va D-09/D-12 ning ENDPOINT isboti.

=============================================================================
BU FAYLNING ENG QIMMAT DA'VOSI — RAD ETILGAN SO'ROV JURNALGA YOZMASLIGI.

`test_vendor_read_is_audited` "o'qish qayd etiladi" ni ko'rsatadi, lekin
uning O'ZI hech nimani himoya qilmaydi: `audit_read` ni endpoint imzosining
BOSHIGA ko'chirsak ham u yashil qolardi. Darvozani AYNAN
`test_forbidden_read_is_not_audited` ushlab turadi — u 403 dan KEYIN `read`
yozuvlari SONI o'zgarmaganini talab qiladi, ya'ni e'lon tartibining
(`require_permission` -> `audit_read`) bevosita isboti.

Ikkalasi birga o'qiladi: birinchisisiz ikkinchisi "audit umuman
ishlamayapti" holatida ham yashil bo'lardi.
=============================================================================

TELEFON MASKALANMAYDI (UI-SPEC §8.6 [QAROR], T-02-77) — javobda u to'liq
keladi va bu SINALADI. Aks holda kimdir "xavfsizlik uchun" yulduzcha
qo'shsa, admin sotuvchiga qo'ng'iroq qila olmay qolardi va sabab
mahsulot qarorida emas, bitta commit'da ko'milib ketardi.

SANALAR `market_today` FIXTURE'IDAN HISOBLANADI, SOBIT YOZILMAYDI (02-07
deviatsiya #1). Seed'ning biriktirish sanalari (`HANDOVER_DAY`, `GAP_*`)
BU FAYLDA umuman ishlatilmaydi: ular sobit va "bugun kimga biriktirilgan"
javobi kalendar bo'yicha SURILADI — ya'ni ularga tayangan test bir necha
kundan keyin sababsiz qizarardi. Bu yerdagi har bir biriktirish testning
O'ZI tomonidan, bugundan hisoblab yoziladi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import ASSIGNMENTS_URL, VENDORS_URL, session_headers
from fixtures.auth_api import audit_rows
from fixtures.market_domain import A_STALL_CODES_BY_SORT, A_VENDOR_PHONES
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction

if TYPE_CHECKING:
    from datetime import date

    import httpx
    from fixtures import MarketDomainSeed, TenantSessionFactory
    from fixtures.market_domain import MarketDomainRows
    from fixtures.two_markets import TwoMarketSeed

TABLE_VENDORS = "vendors"
"""`audit_log.table_name` — o'qish yozuvi aynan shu resursga tegishli."""

NEW_PHONE = "+998909990101"
"""Testlar YARATADIGAN sotuvchining telefoni — seed diapazonlaridan TASHQARIDA.

`A_VENDOR_PHONES` `+99890111...` ni, `two_markets._next_phone()` esa
`+99897...` ni ishlatadi. Bu raqam ikkalasiga ham tegmaydi, ya'ni
"yangi sotuvchi qo'shildi" testlari kutilmagan 409 olmaydi.
"""

RAW_PHONE = "90 123 45 67"
NORMALIZED_PHONE = "+998901234567"
"""D-12: chegara normalizatsiyasining kirish va chiqish shakli.

Milliy shakl ATAYIN bo'sh joylar bilan: `+998901234567` yuborilsa
normalizatsiya umuman ishlamagan holatda ham test yashil qolardi.
"""

INVALID_PHONE = "12345"
"""`phonenumbers.is_valid_number()` rad etadigan raqam (uzunlik ham, prefiks ham)."""


# ---------------------------------------------------------------------------
# Sessiyalar va yordamchilar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`VENDOR_VIEW` + `VENDOR_MANAGE`).

    `market_domain` ATAYIN argument sifatida olinadi: domen qatlami
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi so'rov bo'sh
    reestrni ko'rardi.
    """
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def other_market_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """B bozori adminining sessiyasi — D-12 nazorat holati uchun."""
    market_b = two_markets.market_b
    return await session_headers(api_client, market_b.admin_phone, market_b.admin_password)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori kassirining sessiyasi — `VENDOR_VIEW` YO'Q (D-07)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori direktorining sessiyasi — ko'radi, lekin boshqarmaydi (D-07)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.director_phone, SEED_PASSWORD)


async def _vendor_reads(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
) -> list[Any]:
    """`action='read'` + `table_name='vendors'` yozuvlari — MAHSULOT yo'li bilan.

    Superuser bilan O'QILMAYDI: audit ekrani (D-11) aynan shu yo'ldan
    ma'lumot oladi, ya'ni test mahsulot yo'lini sinaydi.
    """
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return [row for row in rows if row.table_name == TABLE_VENDORS]


async def _create_vendor(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    full_name: str,
    phone: str,
) -> httpx.Response:
    return await client.post(
        VENDORS_URL, json={"full_name": full_name, "phone": phone}, headers=headers
    )


def _free_stalls(rows: MarketDomainRows) -> tuple[UUID, ...]:
    """Seed'da BIRORTA biriktirish davri yo'q rastalar.

    Indeks bo'yicha tanlanmaydi (`stall_ids[2]` kabi): seed tartibi
    o'zgarganda bunday tanlov jimgina BAND rastaga tushib, testni
    409 `assignment_period_overlaps` bilan yiqitardi va sabab
    biriktirish mantiqiga o'xshab ko'rinardi.
    """
    busy = {rows.handover_stall_id, rows.gap_stall_id}
    return tuple(stall_id for stall_id in rows.stall_ids if stall_id not in busy)


async def _assign(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    stall_id: UUID,
    vendor_id: UUID,
    from_date: date,
) -> httpx.Response:
    return await client.post(
        ASSIGNMENTS_URL,
        json={
            "stall_id": str(stall_id),
            "vendor_id": str(vendor_id),
            "from_date": from_date.isoformat(),
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# D-09 — shaxsiy ma'lumotning har bir o'qilishi jurnalda
# ---------------------------------------------------------------------------


async def test_vendor_read_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """`GET /vendors` -> `action='read'`, `table_name='vendors'`, `reason='vendor_view'`.

    SO'ROV ATAYIN KURSOR BILAN yuboriladi: `_describe()` dan `cursor` ni
    chiqarib tashlash da'vosi kursorsiz so'rovda o'z-o'zidan bajarilardi
    (`exclude_none=True` uni baribir tashlab yuborardi) — ya'ni darvoza
    umuman sinalmasdi. Kursor mavjud bo'lgandagina "u jurnalga tushmadi"
    haqiqiy da'vo bo'ladi.
    """
    market_id = two_markets.market_a.id

    first = await api_client.get(VENDORS_URL, params={"limit": 1}, headers=admin_headers)
    assert first.status_code == 200, first.text
    cursor = first.json()["next_cursor"]
    assert cursor, "uchta sotuvchi bor, lekin `limit=1` kursor bermadi"

    before = await _vendor_reads(tenant_session, market_id)
    response = await api_client.get(
        VENDORS_URL, params={"limit": 1, "cursor": cursor}, headers=admin_headers
    )
    assert response.status_code == 200, response.text

    after = await _vendor_reads(tenant_session, market_id)
    assert len(after) == len(before) + 1, "o'qish AYNAN bitta yozuv qoldirishi kerak"

    row = after[-1]
    assert row.source == "app", "`SELECT` uchun trigger yo'q — yozuvni ilova qiladi"
    assert row.actor_user_id == two_markets.market_a.admin_user_id
    value = row.new_value
    assert value["reason"] == "vendor_view"
    assert value["result_count"] == len(response.json()["items"])
    assert value["filters"]["limit"] == 1
    assert "cursor" not in value["filters"], (
        "opaque kursor jurnalga tushdi — u o'qiyotgan odamga hech nima aytmaydi"
    )


async def test_forbidden_read_is_not_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    cashier_headers: dict[str, str],
) -> None:
    """403 olgan kassir hech narsani o'qimagan — yozuv ham bo'lmasligi kerak.

    BU TEST E'LON TARTIBINING BEVOSITA ISBOTI (T-02-71). `audit_read`
    `require_permission` dan OLDIN turganda jurnalda "kassir sotuvchilar
    reestrini o'qidi" degan YOLG'ON DALIL paydo bo'lardi va nizoni hal
    qilishda aynan shu yozuvga tayanadigan odam chalg'itilardi.
    """
    market_id = two_markets.market_a.id
    before = len(await _vendor_reads(tenant_session, market_id))

    rejected = await api_client.get(VENDORS_URL, headers=cashier_headers)

    assert rejected.status_code == 403, rejected.text
    assert rejected.json() == {"detail": "forbidden"}
    assert len(await _vendor_reads(tenant_session, market_id)) == before, (
        "rad etilgan so'rov jurnalga yolg'on dalil qoldirdi"
    )


async def test_vendor_detail_read_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """Yakka sotuvchi kartochkasi ham jurnalga tushadi — ro'yxatgina emas.

    Faqat ro'yxat qamralganda "bittalab varaqlash" usuli auditdan
    butunlay chetda qolardi: yuzta so'rov bilan butun reestrni o'qib
    olish mumkin bo'lardi-yu, jurnalda birorta iz qolmasdi.
    """
    market_id = two_markets.market_a.id
    vendor_id = market_domain.market_a.vendor_ids[0]
    before = len(await _vendor_reads(tenant_session, market_id))

    response = await api_client.get(f"{VENDORS_URL}/{vendor_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    rows = await _vendor_reads(tenant_session, market_id)
    assert len(rows) == before + 1
    value = rows[-1].new_value
    assert value["reason"] == "vendor_view"
    assert value["result_count"] == 1
    assert value["filters"] == {"vendor_id": str(vendor_id)}


# ---------------------------------------------------------------------------
# D-12 — telefon: normalizatsiya va BOZOR ICHIDA unikalik
# ---------------------------------------------------------------------------


async def test_same_phone_in_another_market_is_accepted(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    other_market_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: unikalik BOZOR ICHIDA, global EMAS (D-12, T-02-44).

    Usiz keyingi test (`test_phone_is_unique_per_market`) `UNIQUE(phone_e164)`
    GLOBAL qilib qo'yilgan holatda ham yashil bo'lardi — 409 baribir
    kelardi. Bir odam ikki bozorda savdo qilishi mumkin va MVP uni ikki
    alohida qator sifatida ko'radi.
    """
    in_a = await _create_vendor(
        api_client, admin_headers, full_name="Ikki Bozorli", phone=NEW_PHONE
    )
    assert in_a.status_code == 201, in_a.text

    in_b = await _create_vendor(
        api_client, other_market_headers, full_name="Ikki Bozorli", phone=NEW_PHONE
    )

    assert in_b.status_code == 201, in_b.text
    assert in_b.json()["id"] != in_a.json()["id"], "ikki bozorda ikki ALOHIDA qator kutilgan"


async def test_phone_is_unique_per_market(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Shu bozorda band raqam -> **409** `vendor_phone_taken` (D-12).

    Raqam seed'dan olinadi (`A_VENDOR_PHONES[0]`), testda qayta
    yozilmaydi: seed qiymati o'zgarsa test ergashishi kerak, aks holda u
    jimgina "hech kimga tegishli bo'lmagan" raqamni sinab 201 olardi.
    """
    response = await _create_vendor(
        api_client, admin_headers, full_name="Takroriy Raqam", phone=A_VENDOR_PHONES[0]
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "vendor_phone_taken"


async def test_phone_is_normalized_to_e164(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Milliy shakl E.164 ga keltiriladi — CHEGARADA, endpoint ichida emas.

    Javob AYNAN o'qish yo'lidan quriladi, ya'ni bu tekshiruv saqlangan
    qiymatni ham qamraydi: normalizatsiya faqat javob uchun qilinganda
    keyingi `GET` boshqa shakl ko'rsatardi.
    """
    created = await _create_vendor(
        api_client, admin_headers, full_name="Normal Shakl", phone=RAW_PHONE
    )
    assert created.status_code == 201, created.text
    assert created.json()["phone"] == NORMALIZED_PHONE

    vendor_id = created.json()["id"]
    fetched = await api_client.get(f"{VENDORS_URL}/{vendor_id}", headers=admin_headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["phone"] == NORMALIZED_PHONE


async def test_invalid_phone_returns_422(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """O'qib bo'lmaydigan raqam -> **422** (409 EMAS: shakl xatosi, konflikt emas)."""
    response = await _create_vendor(
        api_client, admin_headers, full_name="Yaroqsiz Raqam", phone=INVALID_PHONE
    )

    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Reestr: sahifalash va bugungi rastalar agregati
# ---------------------------------------------------------------------------


async def test_vendor_list_is_keyset_paginated(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """`limit=1` + `cursor`: keyingi sahifa TAKRORLAMAYDI va o'tkazib yubormaydi.

    Kutilgan TARTIB testda qayta qurilmaydi — u to'liq ro'yxatdan
    olinadi. F.I.Sh. bo'yicha saralash kolatsiyaga bog'liq va uni
    Python'da qayta hisoblash ikkinchi, ajralib ketadigan haqiqat manbai
    bo'lardi (02-08 da o'rnatilgan qoida).
    """
    everything = await api_client.get(VENDORS_URL, params={"limit": 200}, headers=admin_headers)
    assert everything.status_code == 200, everything.text
    expected = [item["id"] for item in everything.json()["items"]]
    assert len(expected) >= 3, "seed uchta sotuvchi berishi kerak"
    assert everything.json()["next_cursor"] is None, "hammasi sig'di, kursor bo'lmasligi kerak"

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(len(expected)):
        params: dict[str, str] = {"limit": "1"}
        if cursor is not None:
            params["cursor"] = cursor
        page = await api_client.get(VENDORS_URL, params=params, headers=admin_headers)
        assert page.status_code == 200, page.text
        items = page.json()["items"]
        assert len(items) == 1
        seen.append(items[0]["id"])
        cursor = page.json()["next_cursor"]

    assert seen == expected, "keyset sahifalash tartibni buzdi yoki qator takrorladi"
    assert cursor is None, "oxirgi sahifadan keyin kursor qolmasligi kerak"


async def test_vendor_list_includes_stall_codes(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """`stall_codes` — BUGUN biriktirilgan rastalar, `code_sort` TARTIBIDA.

    Kutilgan tartib qo'lda yozilgan `A_STALL_CODES_BY_SORT` dan
    filtrlanadi: kodlar ATAYIN shunday tanlanganki, matn tartibi
    (`100, 3, 55, 7`) inson-raqamli tartibdan (`3, 7, 55, 100`) FARQ
    QILADI. Bir xil bo'lganda `code_sort` umuman ishlamaganda ham test
    yashil bo'lardi.

    Biriktirishlar SHU TESTDA, bugundan hisoblab yoziladi — seed'ning
    sobit sanalariga tayanish "bugun kimga biriktirilgan" javobini
    kalendar bilan birga surib yuborardi (modul docstringi).
    """
    rows = market_domain.market_a
    codes_by_stall = dict(zip(rows.stall_ids, rows.stall_codes, strict=True))
    stalls = _free_stalls(rows)
    assert len(stalls) >= 3, "seed kamida uchta bo'sh rasta berishi kerak"

    created = await _create_vendor(
        api_client, admin_headers, full_name="Ko'p Rastali", phone=NEW_PHONE
    )
    assert created.status_code == 201, created.text
    vendor_id = UUID(created.json()["id"])

    for stall_id in stalls:
        assigned = await _assign(
            api_client,
            admin_headers,
            stall_id=stall_id,
            vendor_id=vendor_id,
            from_date=market_today,
        )
        assert assigned.status_code == 201, assigned.text

    chosen = {codes_by_stall[stall_id] for stall_id in stalls}
    expected = [code for code in A_STALL_CODES_BY_SORT if code in chosen]

    response = await api_client.get(f"{VENDORS_URL}/{vendor_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stall_count"] == len(stalls)
    assert body["stall_codes"] == expected


async def test_vendor_name_is_editable_without_resending_the_phone(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """`PATCH` faqat berilgan maydonni yozadi — telefon O'ZGARMAY qoladi.

    Telefon `exclude_unset` bilan himoyalanmagan bo'lsa, ismni tuzatuvchi
    so'rov uni `NULL` bilan qayta yozardi (`NOT NULL` -> 500) yoki
    eskirgan qiymatni tiklab qo'yardi.
    """
    vendor_id = market_domain.market_a.vendor_ids[0]
    before = await api_client.get(f"{VENDORS_URL}/{vendor_id}", headers=admin_headers)
    assert before.status_code == 200, before.text
    phone = before.json()["phone"]

    response = await api_client.patch(
        f"{VENDORS_URL}/{vendor_id}", json={"full_name": "Aliev Vali"}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["full_name"] == "Aliev Vali"
    assert response.json()["phone"] == phone, "PATCH telefonni jimgina o'zgartirdi"


# ---------------------------------------------------------------------------
# Tenant izolyatsiyasi va huquqlar
# ---------------------------------------------------------------------------


async def test_cross_tenant_vendor_returns_404(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """A tokeni + B bozorining `vendor_id` si -> **404**, va aynan 403 EMAS.

    `status != 403` ALOHIDA assert qilinadi: faqat `== 404` bo'lganda
    kimdir javobni 403 ga o'zgartirsa, xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (qator MAVJUDLIGINI tasdiqlash — T-02-67) hech
    qayerda ko'rinmasdi.

    O'QISH YOZUVI HAM QOLMAYDI: begona sotuvchi O'QILMAGAN, ya'ni
    jurnalda "A admini B ning sotuvchisini ko'rdi" degan yozuv YOLG'ON
    dalil bo'lardi.
    """
    market_id = two_markets.market_a.id
    foreign_vendor = market_domain.market_b.vendor_ids[0]
    before = len(await _vendor_reads(tenant_session, market_id))

    response = await api_client.get(f"{VENDORS_URL}/{foreign_vendor}", headers=admin_headers)

    assert response.status_code != 403, "403 qator MAVJUDLIGINI tasdiqlaydi (T-02-67)"
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"
    assert len(await _vendor_reads(tenant_session, market_id)) == before


async def test_director_can_view_but_not_manage_vendors(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
) -> None:
    """Direktor reestrni KO'RADI, lekin sotuvchi qo'sha OLMAYDI (D-07, T-02-76).

    NAZORAT HOLATI (`GET` -> 200) MAJBURIY: usiz test direktorning
    sessiyasi umuman ishlamayotgan holatda ham yashil bo'lardi (har
    ikkala so'rov ham 403 berardi) va D-07 ning aynan mazmuni — "faqat
    yozish taqiqlangan" — sinovsiz qolardi.
    """
    allowed = await api_client.get(VENDORS_URL, headers=director_headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["items"], "direktor uchun sotuvchilar ro'yxati bo'sh qaytdi"

    forbidden = await _create_vendor(
        api_client, director_headers, full_name="Direktor Qo'shdi", phone=NEW_PHONE
    )

    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["detail"] == "forbidden"
