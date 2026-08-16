"""Qog'oz daftar importi — `POST /reports/compare/ledger` (D-17, RECON-04).

=============================================================================
⛔⛔ BU FAYL `tests/unit/test_import_validator.py` NI TAKRORLAMAYDI.

Unit testlar SOF FUNKSIYANI sinaydi (qator raqamlari, `0` ning qonuniyligi,
registrsiz dublikat). Bu yerdagi savol boshqa va u konteynersiz umuman
javob olmaydi:

  1. ALL-OR-NOTHING — bitta xato qator bo'lganda jadval BO'SH qoladimi
     (javob kodi emas, SANOQ bilan o'lchanadi);
  2. IDEMPOTENTLIK — ikkinchi fayl qator SONINI oshirmaydimi;
  3. AUDIT — bitta ommaviy amal jurnalda BITTA yig'ma iz qoldiradimi;
  4. HUQUQ — kim yozadi, kim 403 oladi (⛔ DIREKTOR ham 403);
  5. TENANT — B bozorining admini A ning rastasiga yoza oladimi.

Validator to'g'ri bo'lib, marshrut uni CHAQIRMASA unit testlar YASHIL
qolardi (`test_staff_import.py` modul docstringining aynan qoidasi).

=============================================================================
⛔ YO'L: `/reports/compare/ledger`, `/reports/three-way/ledger` EMAS.

Reja ikkinchisini yozgan edi, LEKIN `report-queries.ts::uploadLedger()`
(08-03, TO'LQIN 1) AYNAN birinchisiga boradi va u allaqachon jo'natilgan.
Sabab `app/api/v1/reports.py` ning 5-bo'limida LITERAL yozilgan; bu
08-07/08-12 da `/debtors` va `/anomalies` uchun qabul qilingan qarorning
aynan takrori.

=============================================================================
⛔⛔ AUDIT DA'VOSI IKKI QATLAMLI VA UNI BITTA SONGA SIQIB BO'LMAYDI.

`ledger_entries` `AUDITED_TABLES` da (08-02), ya'ni jadvalning O'Z DB
triggeri HAR qator uchun bittadan yozuv qoldiradi. Reja «30 qatorli
import AYNAN 1 ta `audit_log` qatori yozadi» degan edi — bu 08-02 dan
KEYIN endi to'g'ri emas va uni «to'g'rilash» uchun triggerni o'chirish
KERAK EMAS: ikki qatlam ikki BOSHQA savolga javob beradi —

    `source='db_trigger'` -> «qaysi rasta, qanday summa» (qator boshiga)
    `source='app'`        -> «bular BITTA ommaviy amaldan» (T-02-180)

Shuning uchun test IKKALASINI ham o'lchaydi: yig'ma yozuv AYNAN bitta,
qator yozuvlari esa AYNAN qatorlar soniga teng. Faqat birinchisini
o'lchash triggerning o'chib qolishini KO'RMASDI.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
import xlsxwriter
from fixtures.admin_api import IMPORTS_TEMPLATE_URL, session_headers
from fixtures.auth_api import audit_rows
from fixtures.market_domain import A_STALL_CODES, B_STALL_CODES
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import MarketScope, TenantSessionFactory
    from fixtures.market_domain import MarketDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

LEDGER_URL = "/api/v1/reports/compare/ledger"

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

LEDGER_HEADER = ["rasta kodi", "daftar summasi"]
"""Sarlavha MATNI — ⛔ PARSER UNI UMUMAN O'QIMAYDI (O-05).

Bu yerda u faqat fayl HAQIQIY shablonga o'xshashi uchun turibdi:
`xlsx_reader` birinchi qatorni sarlavha deb TASHLAYDI va ustunlarni
POZITSIYA bo'yicha oladi. Matnni o'zgartirish testni buzmasligi kerak va
`test_a_russian_header_changes_nothing` buni AYNAN o'lchaydi.
"""

A_ONLY_STALL_CODE = "100"
"""FAQAT A bozorida bor rasta kodi — cross-tenant da'vosining tayanchi.

⛔ `"2"` YARAMAYDI: u IKKALA bozorda ham mavjud (`A_STALL_CODES` va
`B_STALL_CODES`), ya'ni B admini yuborgan `"2"` uning O'Z rastasiga
yechilardi va test «tenant chegarasi ishladi» degan YOLG'ON xulosa
berardi — aslida u shunchaki boshqa rastaga yozgan bo'lardi.
"""

BULK_ROWS = 30
"""Yig'ma audit da'vosining hajmi (reja: «30 qatorli faylda ham»).

⛔ BITTA QATOR YETMASDI: «bitta import = bitta yozuv» da'vosi bitta
   qatorli faylda qator-boshiga-yozuv xatosida ham rost bo'lardi. 30 da
   esa farq 1 va 30 orasida bo'ladi va u JADVALDA ko'rinadi.
"""


# ---------------------------------------------------------------------------
# Fayl quruvchilar
# ---------------------------------------------------------------------------


def build_ledger_xlsx(
    rows: list[list[Any]],
    *,
    header: list[str] | None = None,
    sheet: str = "Daftar",
) -> bytes:
    """`XlsxWriter` bilan haqiqiy `.xlsx` quradi (repoda binar fayl YO'Q)."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet(sheet)
    worksheet.write_row(0, 0, LEDGER_HEADER if header is None else header)
    for index, row in enumerate(rows, start=1):
        worksheet.write_row(index, 0, row)
    workbook.close()
    return buffer.getvalue()


def upload(payload: bytes, name: str = "daftar.xlsx") -> dict[str, tuple[str, bytes, str]]:
    """`multipart/form-data` yuklamasi."""
    return {"file": (name, payload, XLSX_MEDIA_TYPE)}


def _day() -> str:
    """Daftar kuni — ⛔ `business_today()` DAN, `date.today()` DAN EMAS.

    Konteynerlar UTC da yuguradi, biznes kuni esa Asia/Tashkent bo'yicha
    (`test_reports_api.py::_last_closed_day()` ning aynan darsi): ikki
    manba Toshkent yarim tunidan keyingi besh soatda BIR KUN farq
    qilardi va test FLAKY bo'lardi.
    """
    return business_today().isoformat()


# ---------------------------------------------------------------------------
# Sessiyalar, tozalash va sanoqlar
# ---------------------------------------------------------------------------


@pytest.fixture
def ledger(
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> Iterator[MarketDomainSeed]:
    """Domen qatlami + HAR TESTDAN KEYIN daftar qatorlarini o'chirish.

    ⛔ TOZALASH FIXTURE'DA, TESTNING `finally` IDA EMAS
       (`test_reports_api.py::debtors` da o'rnatilgan qoida): `finally`
       bloki har testda takrorlanardi va bittasida unutilgani keyingi
       testga «bu kun uchun daftar bor» holatini sizdirardi — ya'ni
       idempotentlik testi o'z seedini emas, qo'shnisinikini o'lchardi.

    ⚠ `market_domain` ARGUMENT sifatida olinadi: pytest fixture'larni
      TESKARI tartibda yopadi, ya'ni daftar qatorlari RASTALARDAN oldin
      o'chadi. Teskari holatda `fk_ledger_entries_stall` (⛔ `ondelete`
      YO'Q — 0024) `DELETE FROM stalls` ni yiqitardi.
    """
    try:
        yield market_domain
    finally:
        sync_owner_conn.execute(
            "DELETE FROM ledger_entries WHERE market_id = ANY(%s::uuid[])",
            ([str(market.market_id) for market in market_domain.markets],),
        )


@pytest.fixture
def bulk_stalls(
    sync_owner_conn: Connection[TupleRow],
    ledger: MarketDomainSeed,
) -> Iterator[list[str]]:
    """`BULK_ROWS` ta QO'SHIMCHA rasta — yig'ma audit testining maxraji.

    ⛔ SEED OLTITA RASTA BERADI (`A_STALL_CODES`), 30 qatorli fayl esa 30
       TA BOSHQA rastani talab qiladi: fayl ichidagi takror
       `ledger_duplicate_stall` bilan rad etilardi va test import
       yo'liga UMUMAN yetib bormasdi.

    ⚠ Kodlar `L`-prefiksli: seedning raqamli kodlari bilan to'qnashmaydi
      va `stall_code_registry` triggeri ularni O'ZI band qiladi.

    Tozalash UCH QADAMDA va TARTIB MAJBURIY (`fk_ledger_entries_stall` ->
    `fk_stall_code_registry_...`): daftar qatorlari `ledger` fixture'ida
    (u KEYINROQ yopiladi, chunki bu fixture undan hosila), so'ng reyestr,
    so'ng rastalar.
    """
    market_id = ledger.market_a.market_id
    zone_id = ledger.market_a.zone_ids[0]
    codes = [f"L{index:03d}" for index in range(BULK_ROWS)]

    for code in codes:
        sync_owner_conn.execute(
            "INSERT INTO stalls (id, market_id, zone_id, code) VALUES (%s, %s, %s, %s)",
            (str(uuid4()), str(market_id), str(zone_id), code),
        )
    try:
        yield codes
    finally:
        sync_owner_conn.execute(
            "DELETE FROM ledger_entries WHERE market_id = %s", (str(market_id),)
        )
        sync_owner_conn.execute(
            "DELETE FROM stall_code_registry WHERE market_id = %s AND code = ANY(%s)",
            (str(market_id), codes),
        )
        sync_owner_conn.execute(
            "DELETE FROM stalls WHERE market_id = %s AND code = ANY(%s)",
            (str(market_id), codes),
        )


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    ledger: MarketDomainSeed,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori ADMINI — `STALL_MANAGE` BOR (D-20 ning ijobiy holati)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    ledger: MarketDomainSeed,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori DIREKTORI — `report_view` BOR, `stall_manage` YO'Q."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    ledger: MarketDomainSeed,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori KASSIRI — eng tor yuza (D-20: kassir daftar yuklamaydi)."""
    return await session_headers(api_client, two_markets.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def market_b_admin_headers(
    api_client: httpx.AsyncClient,
    ledger: MarketDomainSeed,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """B bozorining ADMINI — cross-tenant da'vosining sub'ekti."""
    market_b = two_markets.market_b
    return await session_headers(api_client, market_b.admin_phone, market_b.admin_password)


def ledger_count(market_scope: MarketScope, market_id: UUID) -> int:
    """Daftar qatorlari soni — ⛔ ILOVA roli va tenant konteksti bilan.

    Superuser bilan O'QILMAYDI: all-or-nothing da'vosi aynan ilova
    ko'radigan haqiqat ustida bo'lishi kerak (`test_staff_import.py::
    count_members` da o'rnatilgan qoida).
    """
    with market_scope(market_id) as conn:
        row = conn.execute("SELECT count(*) FROM ledger_entries").fetchone()
    assert row is not None
    return int(row[0])


def ledger_amounts(market_scope: MarketScope, market_id: UUID) -> dict[str, int]:
    """`{rasta kodi: summa}` — almashtirish da'vosining o'lchovi."""
    with market_scope(market_id) as conn:
        rows = conn.execute(
            "SELECT s.code, le.amount_soum FROM ledger_entries le "
            "JOIN stalls s ON s.market_id = le.market_id AND s.id = le.stall_id"
        ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


async def _ledger_audit_rows(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    *,
    source: str,
) -> list[Any]:
    """`ledger_entries` ustidagi `insert` yozuvlari — MANBA bo'yicha filtrlangan.

    ⛔ FILTR MAJBURIY: sessiya qurilishi (`/auth/login`) va seedning O'ZI
       ham `insert` yozuvlarini qoldiradi, ya'ni filtrsiz sanoq boshqa
       hodisalarni ham sanardi va da'vo YOLG'ON-YASHIL bo'lardi.
    """
    rows = await audit_rows(tenant_session, market_id, action="insert")
    return [row for row in rows if row.table_name == "ledger_entries" and row.source == source]


# ===========================================================================
# (a) MUVAFFAQIYAT YO'LI
# ===========================================================================


async def test_a_valid_file_writes_every_row(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """Yaroqli fayl -> 200 va qatorlar BAZADA (javob emas, SANOQ bilan)."""
    day = _day()
    payload = build_ledger_xlsx(
        [[A_STALL_CODES[0], "150000"], [A_STALL_CODES[1], "220000"]],
    )

    response = await api_client.post(
        LEDGER_URL, params={"day": day}, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"day": day, "rows": 2, "replaced": False}

    assert ledger_count(market_scope, ledger.market_a.market_id) == 2
    assert ledger_amounts(market_scope, ledger.market_a.market_id) == {
        A_STALL_CODES[0]: 150_000,
        A_STALL_CODES[1]: 220_000,
    }


async def test_zero_survives_the_whole_chain(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔⛔ `0` SUMMA UCHIDAN-UCHIGA YOZILADI — SC#5 NING ENG MUHIM HOLATI.

    Unit test validatorning `0` ni rad etmasligini o'lchaydi; bu yerdagi
    savol boshqa: qiymat MARSHRUTDAN, REPOZITORIYDAN va JADVALDAN o'tib
    bazada `0` bo'lib qoladimi. `ledger_entries` da `CHECK (> 0)` ATAYIN
    yo'q (08-02) va agar kimdir uni «tartib uchun» qo'shsa, AYNAN shu
    test qizaradi — validator esa o'zgarmagan bo'lardi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files=upload(build_ledger_xlsx([[A_STALL_CODES[0], "0"]])),
    )

    assert response.status_code == 200, response.text
    assert ledger_amounts(market_scope, ledger.market_a.market_id) == {A_STALL_CODES[0]: 0}


async def test_a_russian_header_changes_nothing(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """O-05: sarlavha TILI o'zgaradi, ustun POZITSIYALARI o'zgarmaydi.

    Ruscha shablonni yuklab olgan admin uzbekcha interfeysda import
    qilsa ham fayl ishlashi SHART — parser sarlavha matnini UMUMAN
    o'qimaydi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files=upload(
            build_ledger_xlsx(
                [[A_STALL_CODES[0], "150000"]],
                header=["номер прилавка", "сумма по тетради"],
                sheet="Тетрадь",
            )
        ),
    )

    assert response.status_code == 200, response.text
    assert ledger_count(market_scope, ledger.market_a.market_id) == 1


# ===========================================================================
# (b) ALL-OR-NOTHING — D-14
# ===========================================================================


async def test_one_bad_row_leaves_the_table_empty(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """Bitta yaroqsiz qator -> 422 va jadval BO'SH (D-14).

    ⛔ FAYL ATAYIN ARALASH: faqat xatoli qatorlardan iborat fayl «hech
       narsa yozilmadi» ni ISBOTLAY OLMASDI — yoziladigan narsaning O'ZI
       yo'q edi (`test_staff_import.py` ning aynan darsi).

    ⛔ DA'VO JAVOB KODI BILAN EMAS, SANOQ BILAN: endpoint ikkita qatorni
       yozib bo'lib, so'ng 422 qaytargan holatda ham status kodi bir xil
       bo'lardi.
    """
    market_id = ledger.market_a.market_id
    before = ledger_count(market_scope, market_id)

    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files=upload(
            build_ledger_xlsx(
                [
                    [A_STALL_CODES[0], "150000"],
                    [A_STALL_CODES[1], "220000"],
                    ["YO'Q-KOD", "300000"],
                ]
            )
        ),
    )

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert body["detail"] == "import_validation_failed"
    assert [item["code"] for item in body["errors"]] == ["ledger_stall_unknown"]
    assert body["errors"][0]["row"] == 4, "EXCEL qator raqami saqlanmagan"
    assert body["error_counts"] == {"ledger_stall_unknown": 1}

    assert ledger_count(market_scope, market_id) == before == 0


async def test_a_fractional_amount_is_refused_with_its_row(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """Kasr summa 422 beradi va jadval BO'SH qoladi (C-6: pul — butun `int`)."""
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files=upload(
            build_ledger_xlsx([[A_STALL_CODES[0], "150000"], [A_STALL_CODES[1], "220000.5"]])
        ),
    )

    assert response.status_code == 422, response.text
    assert [item["code"] for item in response.json()["detail"]["errors"]] == [
        "ledger_amount_invalid"
    ]
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0


# ===========================================================================
# (c) IDEMPOTENTLIK — Pattern 6
# ===========================================================================


async def test_the_second_file_replaces_instead_of_adding(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ IKKINCHI FAYL QATOR SONINI OSHIRMAYDI, SUMMANI ALMASHTIRADI.

    Daftar KUN ICHIDA tuzatiladi va ikkinchi fayl birinchisini
    ALMASHTIRISHI kerak (Pattern 6). `DO NOTHING` bo'lganda birinchi
    (XATO) qiymat MUZLAB qolardi va test uni AYNAN shu tarzda ushlaydi:
    sanoq to'g'ri, SUMMA esa eski bo'lardi.
    """
    market_id = ledger.market_a.market_id
    day = _day()
    first = build_ledger_xlsx([[A_STALL_CODES[0], "150000"], [A_STALL_CODES[1], "220000"]])
    second = build_ledger_xlsx([[A_STALL_CODES[0], "170000"], [A_STALL_CODES[1], "220000"]])

    created = await api_client.post(
        LEDGER_URL, params={"day": day}, headers=admin_headers, files=upload(first)
    )
    assert created.status_code == 200, created.text
    assert created.json()["replaced"] is False

    replaced = await api_client.post(
        LEDGER_URL, params={"day": day}, headers=admin_headers, files=upload(second)
    )

    assert replaced.status_code == 200, replaced.text
    assert replaced.json() == {"day": day, "rows": 2, "replaced": True}
    assert ledger_count(market_scope, market_id) == 2, "ikkinchi import YANGI qator yaratdi"
    assert ledger_amounts(market_scope, market_id) == {
        A_STALL_CODES[0]: 170_000,
        A_STALL_CODES[1]: 220_000,
    }


async def test_another_day_is_a_new_row_not_a_replacement(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """NAZORAT: BOSHQA kun ALMASHTIRMAYDI, QO'SHADI.

    Usiz yuqoridagi test «har importda mavjud qatorni ustiga yozadigan»
    (kunni umuman hisobga olmaydigan) buzuq variantdan ham bemalol
    o'tardi — va o'shanda kechagi daftar bugungisi bilan JIMGINA
    o'chirilardi.
    """
    market_id = ledger.market_a.market_id
    today = business_today()
    payload = build_ledger_xlsx([[A_STALL_CODES[0], "150000"]])

    for day in (today.isoformat(), today.replace(day=1).isoformat()):
        response = await api_client.post(
            LEDGER_URL, params={"day": day}, headers=admin_headers, files=upload(payload)
        )
        assert response.status_code == 200, response.text
        assert response.json()["replaced"] is False, day

    assert ledger_count(market_scope, market_id) == 2


# ===========================================================================
# (d) AUDIT — IKKI QATLAM, IKKI DA'VO (modul docstringi)
# ===========================================================================


async def test_one_bulk_import_writes_exactly_one_aggregate_audit_row(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    tenant_session: TenantSessionFactory,
    bulk_stalls: list[str],
    ledger: MarketDomainSeed,
) -> None:
    """30 qatorli import -> AYNAN 1 ta YIG'MA (`source='app'`) yozuv (T-02-180).

    ⛔ IKKINCHI DA'VO HAM MAJBURIY: qator-boshiga yozuvlar (trigger)
       AYNAN 30 ta. Faqat birinchisini o'lchash `0024` ning audit
       triggeri o'chib qolganini KO'RMASDI — jurnal «kimdir 30 qator
       yozdi» deb aytardi-yu, QAYSI rastaga qancha yozilganini
       aytmasdi.
    """
    market_id = ledger.market_a.market_id
    payload = build_ledger_xlsx([[code, "150000"] for code in bulk_stalls])

    response = await api_client.post(
        LEDGER_URL, params={"day": _day()}, headers=admin_headers, files=upload(payload)
    )
    assert response.status_code == 200, response.text
    assert response.json()["rows"] == BULK_ROWS

    aggregate = await _ledger_audit_rows(tenant_session, market_id, source="app")
    per_row = await _ledger_audit_rows(tenant_session, market_id, source="db_trigger")

    assert len(aggregate) == 1, f"yig'ma yozuvlar soni: {len(aggregate)}"
    assert aggregate[0].new_value == {
        "import": "ledger",
        "day": _day(),
        "rows": BULK_ROWS,
        "replaced": 0,
    }
    assert len(per_row) == BULK_ROWS, f"qator yozuvlari soni: {len(per_row)}"


async def test_the_aggregate_row_counts_the_replacements(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    tenant_session: TenantSessionFactory,
    ledger: MarketDomainSeed,
) -> None:
    """Ikkinchi import yig'ma yozuvida `replaced` SON bo'lib ko'rinadi.

    ⚠ Javobdagi `replaced` MANTIQIY, jurnaldagisi esa SON va bu farq
      ONGLI (`reports.py::ledger_import` izohi): ekran «almashtirildimi?»
      degan bitta savolga javob beradi, jurnal esa «nima o'zgardi» ga.
    """
    market_id = ledger.market_a.market_id
    day = _day()
    payload = build_ledger_xlsx([[A_STALL_CODES[0], "150000"], [A_STALL_CODES[1], "220000"]])

    for _ in range(2):
        response = await api_client.post(
            LEDGER_URL, params={"day": day}, headers=admin_headers, files=upload(payload)
        )
        assert response.status_code == 200, response.text

    aggregate = await _ledger_audit_rows(tenant_session, market_id, source="app")

    assert [row.new_value["replaced"] for row in aggregate] == [0, 2]


async def test_a_rejected_import_leaves_no_aggregate_trace(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    tenant_session: TenantSessionFactory,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ 422 OLGAN IMPORT JURNALDA IZ QOLDIRMAYDI — YOLG'ON DALIL BO'LARDI.

    «Bozor admini daftarni yukladi» yozuvi hech nima yozilmagan holatda
    paydo bo'lsa, nizoni hal qilayotgan odam CHALG'ITILARDI va bu
    jurnalning BO'SH qolishidan ham yomonroq (T-02-71).
    """
    market_id = ledger.market_a.market_id

    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files=upload(build_ledger_xlsx([["YO'Q-KOD", "150000"]])),
    )
    assert response.status_code == 422, response.text

    assert await _ledger_audit_rows(tenant_session, market_id, source="app") == []


# ===========================================================================
# (e) HUQUQ — D-20
# ===========================================================================


async def test_the_cashier_cannot_upload_a_ledger(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ KASSIR 403 — D-20 ning literal bandi (T-08-59).

    Kassirda `stall_manage` ham, `report_view` ham YO'Q: u pul YIG'ADI,
    daftarni esa ma'muriyat yuritadi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=cashier_headers,
        files=upload(build_ledger_xlsx([[A_STALL_CODES[0], "150000"]])),
    )

    assert response.status_code == 403, response.text
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0


async def test_the_director_cannot_upload_a_ledger(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ DIREKTOR HAM 403 — VA BU TESTNING ENG QIMMAT BANDI.

    Direktorda `report_view` BOR, ya'ni u hisobot yuzasining qolgan
    HAMMASINI ochadi. Agar daftar importi `REPORT_VIEW` ortida qolsa,
    bu test YASHIL BO'LMASDI — ya'ni u huquq tanlovini
    (`STALL_MANAGE`) AYNAN o'lchaydi, uni takrorlamaydi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=director_headers,
        files=upload(build_ledger_xlsx([[A_STALL_CODES[0], "150000"]])),
    )

    assert response.status_code == 403, response.text
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0


async def test_the_cashier_cannot_download_the_ledger_template(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
) -> None:
    """Shablon ham `STALL_MANAGE` ortida: u yozuv oqimining bir qismi."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "ledger"}, headers=cashier_headers
    )

    assert response.status_code == 403, response.text


async def test_the_market_admin_downloads_the_ledger_template(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT: bozor admini shablonni OLADI (aks holda yuqoridagi 403 ma'nosiz)."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "ledger"}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == XLSX_MEDIA_TYPE


# ===========================================================================
# (f) TENANT — T-08-60
# ===========================================================================


async def test_the_other_markets_admin_cannot_write_into_market_a(
    api_client: httpx.AsyncClient,
    market_b_admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ B BOZORINING ADMINI A NING RASTASIGA DAFTAR YOZA OLMAYDI (T-08-60).

    =======================================================================
    ⛔ DA'VO IKKI TOMONLAMA VA IKKALASI HAM MAJBURIY:

    (a) FAYL RAD ETILADI — `ledger_stall_unknown`. Rasta lug'ati TENANT
        sessiyasi ostida o'qiladi, ya'ni A ning kodi B uchun MAVJUD EMAS
        va javob uning boshqa bozorda BORLIGINI ham oshkor qilmaydi;
    (b) A NING JADVALI BO'SH QOLADI. Faqat status kodini tekshirish
        «yozildi, lekin boshqa bozorga» holatini o'tkazib yuborardi.
    =======================================================================

    ⚠ KOD `A_ONLY_STALL_CODE` — `"2"` YARAMAYDI: u ikkala bozorda ham bor
      va B admini uni O'Z rastasiga yozardi, test esa buni «tenant
      chegarasi ishladi» deb o'qirdi.
    """
    assert A_ONLY_STALL_CODE in A_STALL_CODES
    assert A_ONLY_STALL_CODE not in B_STALL_CODES

    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=market_b_admin_headers,
        files=upload(build_ledger_xlsx([[A_ONLY_STALL_CODE, "150000"]])),
    )

    assert response.status_code == 422, response.text
    assert [item["code"] for item in response.json()["detail"]["errors"]] == [
        "ledger_stall_unknown"
    ]
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0
    assert ledger_count(market_scope, ledger.market_b.market_id) == 0


async def test_the_other_markets_admin_writes_into_its_own_market(
    api_client: httpx.AsyncClient,
    market_b_admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """NAZORAT: B admini O'Z bozoriga bemalol yozadi.

    Usiz yuqoridagi test «B adminini butunlay bloklaydigan» buzuq
    variantdan ham bemalol o'tardi va tenant chegarasi o'rniga huquq
    nosozligi o'lchanardi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=market_b_admin_headers,
        files=upload(build_ledger_xlsx([[B_STALL_CODES[0], "150000"]])),
    )

    assert response.status_code == 200, response.text
    assert ledger_count(market_scope, ledger.market_b.market_id) == 1
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0


# ===========================================================================
# UCH DARVOZANING TARTIBI (T-08-58)
# ===========================================================================


async def test_a_file_that_is_not_xlsx_never_reaches_the_validator(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    ledger: MarketDomainSeed,
) -> None:
    """⛔ BIRINCHI DARVOZA (`_read_bounded`) KENGAYTMANI RAD ETADI.

    Da'vo `unsupported_file_type` KODI bilan o'lchanadi: agar marshrut
    `imports.py` ning uch darvozasini chetlab o'tib to'g'ridan-to'g'ri
    validatorga borsa, javob boshqa kod bilan (yoki 500 bilan) kelardi.
    """
    response = await api_client.post(
        LEDGER_URL,
        params={"day": _day()},
        headers=admin_headers,
        files={"file": ("daftar.csv", b"kod,summa\n1,150000\n", "text/csv")},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "unsupported_file_type"
    assert ledger_count(market_scope, ledger.market_a.market_id) == 0


async def test_the_day_parameter_is_mandatory(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """⛔ `?day=` SIZ SO'ROV RAD ETILADI — standart kun YO'Q.

    Standart qiymat («bugun») faylni JIMGINA noto'g'ri kunga yozardi va
    xato faqat solishtiruvda, boshqa raqamlar bilan aralashib ko'rinardi
    (`reports.py::DayDep` docstringi).
    """
    response = await api_client.post(
        LEDGER_URL,
        headers=admin_headers,
        files=upload(build_ledger_xlsx([[A_STALL_CODES[0], "150000"]])),
    )

    assert response.status_code == 422, response.text
