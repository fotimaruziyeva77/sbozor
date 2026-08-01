"""Rasta yuzasidagi shaxsiy ma'lumot o'qishining audit izi — D-09 / CR-02.

=============================================================================
BU FAYLNING YARMI — NAZORAT HOLATLARI, VA ULAR IXTIYORIY EMAS.

"O'qish jurnalga tushdi" da'vosi YOLG'IZ O'ZI deyarli hech nima demaydi:
u `audit_read` ni butun `GET` yuzasiga yopishtirilgan holatda ham yashil
bo'lardi. O'shanda jurnal har xarita ochilishida, har rad etilgan
so'rovda va har 404 da qator olardi — ya'ni HAQIQIY o'qish hodisasi
shovqin ichida ko'milib ketardi va D-09 yozuvi nizoni hal qilishga
yaramay qolardi (`app/security/audit.py:240-245` da ATAYIN rad etilgan
"blanket middleware" holati).

Shuning uchun to'rtta ijobiy da'vo yoniga to'rtta rad etish holati
qo'yiladi: 403, ikkita 404 (noma'lum va begona rasta) va `GET /map`.
Ular birgalikda "audit BOR" emas, "audit AYNAN SHU YERDA bor va boshqa
joyda yo'q" degan ancha kuchli da'voni qulflaydi.
=============================================================================

SANALARGA TAYANILMAYDI. Seed'ning biriktirish sanalari (`HANDOVER_DAY`,
`GAP_*`) SOBIT, "bugun kimga biriktirilgan" javobi esa kalendar bo'yicha
SURILADI. Bu fayldagi birorta assertion sotuvchi TOPILISHIGA bog'liq
emas: audit yozuvi natijaning MAZMUNIDAN mustaqil — u "kim nima so'radi"
savoliga javob beradi, "nima topildi" savoliga emas (`test_vendors_api.py`
modul docstringida o'rnatilgan qoida).

FON VAZIFASINI KUTISH MEXANIZMI O'YLAB TOPILMAYDI. `audit_read` yozuvni
`BackgroundTasks` orqali yuboradi, `httpx.ASGITransport` esa fon
vazifalarini javob qaytarilishidan OLDIN bajaradi — ya'ni `await
client.get(...)` tugagach yozuv allaqachon bazada. `test_vendors_api.py`
va `test_audit_read.py` AYNAN shu bilan ishlaydi va bu yerda o'sha usul
takrorlanadi, yangisi qo'shilmaydi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import STALLS_URL, session_headers
from fixtures.auth_api import audit_rows
from fixtures.market_domain import A_VENDOR_NAMES
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction

if TYPE_CHECKING:
    import httpx
    from fixtures import MarketDomainSeed, TenantSessionFactory
    from fixtures.two_markets import TwoMarketSeed

TABLE_STALLS = "stalls"
"""`audit_log.table_name` — rasta yuzasidagi o'qishlarning resursi.

`vendors` EMAS, garchi o'qilgan maydon sotuvchining nomi bo'lsa ham:
jurnalni o'qiyotgan odam "rasta reestri kim tomonidan ko'rildi?"
savoliga javob izlaydi va bu marshrutlar rasta ostida yashaydi.
"""

STALL_VIEW = "stall_view"
ASSIGNMENTS_VIEW = "stall_assignments_view"
"""Ikki `reason` ATAYIN har xil — "reestr varaqlandi" va "bitta rastaning
sotuvchi tarixi ochildi" ikki xil hodisa. Bir xil qiymat bilan jurnal bu
farqni ko'rsata olmasdi."""

SEARCH_FRAGMENT = A_VENDOR_NAMES[1].split()[0]
"""Seed sotuvchisining familiyasi — `q` filtri uchun.

Seed konstantasidan OLINADI, testda qayta yozilmaydi: ism o'zgarsa test
ergashishi kerak. Fragment ATAYIN sotuvchi ismi (rasta kodi emas) —
`stall_repo._STALL_ROWS` uni `v.full_name ILIKE :q_any` bilan qidiradi,
ya'ni bu SHAXSIY MA'LUMOT bo'yicha qidiruv va jurnalning butun ma'nosi
aynan shuni qayd etishda.
"""


# ---------------------------------------------------------------------------
# Sessiyalar va yordamchilar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`MARKET_DATA_VIEW` + `VENDOR_VIEW`).

    `market_domain` ATAYIN argument sifatida olinadi: domen qatlami
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi so'rov bo'sh
    reestrni ko'rardi.
    """
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori kassirining sessiyasi — ikkala o'qish huquqi ham YO'Q (D-07)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.cashier_phone, SEED_PASSWORD)


async def _stall_reads(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
) -> list[Any]:
    """`action='read'` + `table_name='stalls'` yozuvlari — MAHSULOT yo'li bilan.

    Superuser bilan O'QILMAYDI: audit ekrani (D-11) aynan shu yo'ldan
    ma'lumot oladi, ya'ni test mahsulot yo'lini sinaydi
    (`test_vendors_api.py::_vendor_reads` bilan bir xil qoida).
    """
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return [row for row in rows if row.table_name == TABLE_STALLS]


def _busy_stall(seed: MarketDomainSeed) -> UUID:
    """Biriktirish TARIXI bor rasta (almashinuv stsenariysi).

    Indeks bo'yicha tanlanmaydi: seed tartibi o'zgarganda bunday tanlov
    jimgina biriktirilmagan rastaga tushib, tarix testini `items == []`
    holatida ham yashil qoldirardi.
    """
    stall_id = seed.market_a.handover_stall_id
    assert stall_id is not None, "seed almashinuv rastasini bermadi"
    return stall_id


# ---------------------------------------------------------------------------
# D-09 — uchala marshrutning o'qish izi
# ---------------------------------------------------------------------------


async def test_stall_list_read_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """`GET /stalls` -> `action='read'`, `table_name='stalls'`, `reason='stall_view'`.

    Javobda `vendor_name` bor, ya'ni ro'yxatning O'ZI shaxsiy ma'lumot
    yuzasi — 02-VERIFICATION ning 4-bo'shlig'i (CR-02) aynan shu
    marshrutdan boshlangan edi.
    """
    market_id = two_markets.market_a.id
    before = await _stall_reads(tenant_session, market_id)

    response = await api_client.get(STALLS_URL, params={"limit": 5}, headers=admin_headers)
    assert response.status_code == 200, response.text

    after = await _stall_reads(tenant_session, market_id)
    assert len(after) == len(before) + 1, "o'qish AYNAN bitta yozuv qoldirishi kerak"

    row = after[-1]
    assert row.source == "app", "`SELECT` uchun trigger yo'q — yozuvni ilova qiladi"
    assert row.actor_user_id == two_markets.market_a.admin_user_id
    value = row.new_value
    assert value["reason"] == STALL_VIEW
    assert value["result_count"] == len(response.json()["items"])
    assert value["filters"]["limit"] == 5


async def test_search_text_is_recorded_in_the_read_row(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """Sotuvchi ismi bo'yicha qidiruv XOM HOLDA jurnalga tushadi.

    `stall_repo._STALL_ROWS` `q` ni `v.full_name ILIKE :q_any` bilan
    qidiradi, ya'ni bu KO'RISH emas, IZLASH: "kim kimni qidirdi" savoli
    D-09 yozuvining eng qimmatli qismi. Qidiruv matnini tashlab yuborish
    yozuvni "kimdir reestrni ochdi" darajasiga tushirardi.

    NATIJA TOPILISHIGA TAYANILMAYDI: seed'ning biriktirish sanalari sobit
    va "bugun kim biriktirilgan" javobi kalendar bilan suriladi. Yozuv esa
    natijaning mazmunidan MUSTAQIL — u so'rovni qayd etadi.
    """
    market_id = two_markets.market_a.id
    before = len(await _stall_reads(tenant_session, market_id))

    response = await api_client.get(
        STALLS_URL, params={"q": SEARCH_FRAGMENT}, headers=admin_headers
    )
    assert response.status_code == 200, response.text

    rows = await _stall_reads(tenant_session, market_id)
    assert len(rows) == before + 1
    filters = rows[-1].new_value["filters"]
    assert filters["q"] == SEARCH_FRAGMENT, "shaxsiy ma'lumot bo'yicha qidiruv jurnalga tushmadi"
    assert "cursor" not in filters, (
        "opaque kursor jurnalga tushdi — u o'qiyotgan odamga hech nima aytmaydi"
    )


async def test_stall_detail_read_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """Rasta kartochkasi (TELEFON qaytaradi) ham jurnalga tushadi.

    Faqat ro'yxat qamralganda "bittalab varaqlash" usuli auditdan butunlay
    chetda qolardi: yuzta so'rov bilan butun reestrni telefonlari bilan
    o'qib olish mumkin bo'lardi-yu, jurnalda birorta iz qolmasdi.
    """
    market_id = two_markets.market_a.id
    stall_id = _busy_stall(market_domain)
    before = len(await _stall_reads(tenant_session, market_id))

    response = await api_client.get(f"{STALLS_URL}/{stall_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    assert "phone" in response.json(), "kartochka telefon maydonini qaytarmadi — test eskirgan"
    rows = await _stall_reads(tenant_session, market_id)
    assert len(rows) == before + 1
    value = rows[-1].new_value
    assert value["reason"] == STALL_VIEW
    assert value["result_count"] == 1
    assert value["filters"] == {"stall_id": str(stall_id)}


async def test_assignment_history_read_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """Biriktirish TARIXI — sotuvchi F.I.Sh. ning ketma-ketligi, ya'ni D-09 qamrovida.

    `reason` ro'yxatnikidan FARQ QILISHI shu yerda qulflanadi: bir xil
    qiymat bilan jurnal "reestr varaqlandi" va "bitta rastaning kim
    tomonidan ishlanganini kim so'radi" ni ajrata olmasdi.
    """
    market_id = two_markets.market_a.id
    stall_id = _busy_stall(market_domain)
    before = len(await _stall_reads(tenant_session, market_id))

    response = await api_client.get(f"{STALLS_URL}/{stall_id}/assignments", headers=admin_headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items, "almashinuv rastasining tarixi bo'sh qaytdi — seed eskirgan"
    rows = await _stall_reads(tenant_session, market_id)
    assert len(rows) == before + 1
    value = rows[-1].new_value
    assert value["reason"] == ASSIGNMENTS_VIEW
    assert value["result_count"] == len(items)
    assert value["filters"] == {"stall_id": str(stall_id)}


# ---------------------------------------------------------------------------
# NAZORAT HOLATLARI — audit AYNAN shu yerda va boshqa joyda YO'Q
# ---------------------------------------------------------------------------


async def test_forbidden_read_is_not_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    cashier_headers: dict[str, str],
) -> None:
    """403 olgan kassir hech narsani o'qimagan — yozuv ham bo'lmasligi kerak.

    BU TEST E'LON TARTIBINING BEVOSITA ISBOTI (T-02-147). Bu yerda
    tartibni FastAPI ning O'ZI kafolatlaydi: `VENDOR_VIEW` marshrut
    DEKORATORIDA e'lon qilingan va dekorator darajasidagi bog'liqliklar
    imzo parametrlaridan OLDIN hal bo'ladi, ya'ni 403 `audit_read` gacha
    yetib bormaydi.

    Usiz jurnalda "kassir rasta reestrini (sotuvchi nomlari bilan)
    o'qidi" degan YOLG'ON DALIL paydo bo'lardi — bu jurnalning BO'SH
    qolishidan ham yomonroq.
    """
    market_id = two_markets.market_a.id
    before = len(await _stall_reads(tenant_session, market_id))

    rejected = await api_client.get(STALLS_URL, headers=cashier_headers)

    assert rejected.status_code == 403, rejected.text
    assert rejected.json() == {"detail": "forbidden"}
    assert len(await _stall_reads(tenant_session, market_id)) == before, (
        "rad etilgan so'rov jurnalga yolg'on dalil qoldirdi"
    )


async def test_unknown_stall_writes_no_read_row(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """Mavjud bo'lmagan rasta (404) o'qish yozuvi qoldirmaydi.

    404 yo'li huquq darvozasidan MUVAFFAQIYATLI o'tadi (adminda ikkala
    huquq ham bor), ya'ni bu yerda darvozani boshqa mexanizm ushlaydi:
    `HTTPException` ko'tarilganda FastAPI yangi javob quradi va unda fon
    vazifasi yo'q. Ikkinchi qatlam AYNAN shu holatda sinaladi.
    """
    market_id = two_markets.market_a.id
    before = len(await _stall_reads(tenant_session, market_id))

    response = await api_client.get(f"{STALLS_URL}/{uuid4()}", headers=admin_headers)

    assert response.status_code == 404, response.text
    assert len(await _stall_reads(tenant_session, market_id)) == before


async def test_cross_tenant_stall_writes_no_read_row(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """A tokeni + B bozorining rastasi -> 404 va jurnalda IZ YO'Q.

    NOMA'LUM ID HOLATIDAN ALOHIDA test: begona rasta MAVJUD, ya'ni
    "A admini B ning rastasini ko'rdi" degan yozuv nizoni hal qilayotgan
    odamni jiddiy chalg'itardi. `status != 403` alohida tekshiriladi —
    403 o'sha rasta MAVJUDLIGINI tasdiqlardi (T-02-55).

    IKKALA yo'l ham (`/{id}` va `/{id}/assignments`) tekshiriladi: ular
    404 ni HAR XIL mexanizm bilan beradi (`detail() is None` va
    `stall_exists()`), ya'ni bittasi ikkinchisining isboti emas.
    """
    market_id = two_markets.market_a.id
    foreign_stall = market_domain.market_b.stall_ids[0]
    before = len(await _stall_reads(tenant_session, market_id))

    detail = await api_client.get(f"{STALLS_URL}/{foreign_stall}", headers=admin_headers)
    history = await api_client.get(
        f"{STALLS_URL}/{foreign_stall}/assignments", headers=admin_headers
    )

    assert detail.status_code != 403, "403 rasta MAVJUDLIGINI tasdiqlaydi (T-02-55)"
    assert detail.status_code == 404, detail.text
    assert history.status_code == 404, history.text
    assert len(await _stall_reads(tenant_session, market_id)) == before


async def test_map_read_is_not_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    admin_headers: dict[str, str],
) -> None:
    """`GET /stalls/map` — MUVAFFAQIYATLI, lekin jurnalga YOZILMAYDI (T-02-148).

    Bu eng muhim nazorat holati: usiz yuqoridagi to'rtta test `audit_read`
    butun `GET` yuzasiga yopishtirilgan holatda ham yashil bo'lardi.
    `MapCell` da faqat `id`, `code`, `status`, `has_vendor` bor —
    sotuvchining na nomi, na telefoni, ya'ni bu marshrut shaxsiy ma'lumot
    qaytarmaydi va D-09 uni qamramaydi.

    Auditni bu yerga ham qo'yish jurnalni HAR xarita ochilishida shovqin
    bilan to'ldirardi va haqiqiy o'qish hodisasini ko'mib yuborardi.
    """
    market_id = two_markets.market_a.id
    before = len(await _stall_reads(tenant_session, market_id))

    response = await api_client.get(f"{STALLS_URL}/map", headers=admin_headers)

    assert response.status_code == 200, response.text
    assert response.json()["zones"], "xarita bo'sh qaytdi — nazorat holati ma'nosini yo'qotdi"
    assert len(await _stall_reads(tenant_session, market_id)) == before, (
        "shaxsiy maydoni yo'q marshrut ham jurnalga yozdi — audit haddan tashqari keng"
    )
