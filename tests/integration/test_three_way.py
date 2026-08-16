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
from dataclasses import dataclass, fields
from datetime import time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
import xlsxwriter
from app.repositories.report_repo import ThreeWayReport, three_way
from app.services.xlsx_export import COMPARE_EXPORT_COLUMNS
from app.services.xlsx_reader import read_rows
from fixtures.admin_api import IMPORTS_TEMPLATE_URL, session_headers
from fixtures.auth_api import audit_rows
from fixtures.billing_domain import (
    TARIFF_SOUM,
    add_billable_frame,
    add_daily_charge,
    add_payment,
    add_zone_with_event_on,
    billing_domain_before_day_close,
)
from fixtures.market_domain import A_STALL_CODES, B_STALL_CODES
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import OccupancyVerdict, ResolutionSource
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures import MarketScope, TenantSessionFactory
    from fixtures.billing_domain import BillingDomainSeed, MarketBillingRows
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


# ===========================================================================
# UCH TOMONLAMA SOLISHTIRUV — `three_way()` (08-16)
#
# =========================================================================
# ⛔⛔ SEED IKKI QATLAMLI VA IKKALASI HAM MAJBURIY.
#
# Daftar importi (yuqoridagi bo'limlar) faqat `ledger_entries` ni talab
# qiladi. Solishtiruv esa UCH manbani yonma-yon qo'yadi, ya'ni test
# `daily_charges` + `payments` (tizim) va `stall_slot_occupancy`
# (AI-kutilgan) qatorlarini ham yozishi kerak. Faqat daftarni seed
# qilgan test uchala ustunni ham «0 va bo'sh» holida ko'rardi va farq
# sinflarining BIRORTASI ham tug'ilmasdi.
#
# =========================================================================
# ⛔⛔ KUN BAZADAN OLINADI (`_compare_day`), `date.today()` DAN EMAS.
#
# `test_report_repo.py` ning 3-qoidasi: `daily_charges.business_date`
# `created_at` DAN hosila generated ustun va u `Asia/Tashkent` da
# hisoblanadi, konteyner esa UTC da yuguradi. Testda hisoblangan kun
# Toshkent yarim tunidan keyingi besh soatda BOSHQA kunga tushardi.
# ===========================================================================

COMPARE_LEDGER_SOUM = 30_000
"""Daftardagi «ortiqcha» summa — ⛔ `TARIFF_SOUM` NING KARRASI EMAS.

`2 x 15 000` bo'lganda «daftar ikki marta yozilgan» bilan «daftar ortiq»
mexanik ravishda bir xil ko'rinardi. 30 000 esa 15 000 dan aniq katta va
u hech qanday karra bilan tasodifan chiqmaydi.
"""

LATE_TARIFF_SOUM = 25_000
"""⛔ SOLISHTIRUV KUNIDAN KEYIN kuchga kiradigan tarif (Open Question 3).

`TARIFF_SOUM` (15 000) va `NEXT_DAY_TARIFF_SOUM` (20 000) DAN FARQLI
bo'lishi SHART: seedning ikkala mavjud qatoridan biri tasodifan
tanlanganda ham natija BOSHQA son bo'lishi kerak, aks holda «qaysi
tarif olindi?» savoli javobsiz qolardi.
"""

_SLOTS: tuple[time, ...] = DEFAULT_SNAPSHOT_SLOTS
"""Kadr slotlari — ⛔ MODELDAN, testda O'YLAB TOPILMAYDI.

Har `occupy()` chaqiruvi O'Z kadrini yozadi va bir kunda bitta kamera
uchun bitta slot AYNAN BIR MARTA ishlatilishi kerak. Ro'yxatni testda
qo'lda yozish `DEFAULT_SNAPSHOT_SLOTS` o'zgargan kuni jimgina ajralib
ketardi (`fixtures/billing_domain.py::_SLOT_A` ning aynan qoidasi).
"""

_INSERT_LEDGER_ROW = (
    "INSERT INTO ledger_entries (id, market_id, business_date, stall_id, amount_soum, imported_by) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)
_INSERT_SLOT_ROW = (
    "INSERT INTO stall_slot_occupancy "
    "(id, market_id, stall_id, business_date, slot_time, verdict, "
    " resolution_source, winning_occupancy_event_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_LATE_TARIFF = (
    "INSERT INTO tariffs (id, market_id, category_id, amount_soum, valid_from) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""⛔ `ledger_entries` AUDIT TRIGGERI OSTIDA (`0024`), ya'ni GUC MAJBURIY.

`test_report_repo.py::_SET_MARKET_GUC` ning aynan nusxasi va aynan
sababi: kontekstsiz `INSERT` audit qatorini EGASIZ qoldirardi. Blok
tugagach qiymat BO'SHATILADI — `sync_owner_conn` autocommit rejimida
ishlaydi va qoldirilgan qiymat keyingi testga sizib o'tardi.
"""


def _compare_day(conn: Connection[TupleRow]) -> date:
    """Solishtiruv kuni — ⛔ BAZANING «kechasi», `date.today()` EMAS.

    ⛔ `business_today()` HAM TO'G'RIDAN-TO'G'RI ISHLATILMAYDI: u
       `Asia/Tashkent` da hisoblanadi va UTC `CURRENT_DATE` dan BIR KUN
       oldinda bo'lishi mumkin, `ck_daily_charges_service_date_not_in_
       future` esa `service_date <= business_date` ni talab qiladi
       (`fixtures/billing_domain.py::_safe_service_date` ning aynan
       darsi). `CURRENT_DATE - 1` ikkala shartni ham bajaradi: u
       hisob yozish uchun xavfsiz VA marshrutning «kecha» chegarasidan
       oshmaydi.
    """
    row = conn.execute("SELECT CURRENT_DATE - 1").fetchone()
    assert row is not None
    day: date = row[0]
    return day


@dataclass(frozen=True)
class CompareEnv:
    """Solishtiruvning seedi — uch manba va ularning bozori."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed
    day: date

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — solishtiruv shu bozor uchun quriladi."""
        return self.billing.market_a

    @property
    def other(self) -> MarketBillingRows:
        """B bozori — tenant chegarasining NAZORAT tomoni."""
        return self.billing.market_b

    @property
    def market_id(self) -> UUID:
        return self.live.market_id

    def stall(self, index: int) -> UUID:
        """A bozorining `index`-rastasi — seed RO'YXATIDAN, so'rovsiz."""
        return self.domain.market_a.stall_ids[index]

    def billed_stall(self, index: int) -> UUID:
        """⛔ BILLING TOIFASI BERILGAN rasta — tarif izlash yo'li uchun.

        `billing_domain._seed_market_a()` toifa davrini FAQAT to'rtta
        rastaga beradi (`billed_stalls`); qolgan ikkitasida esa
        `market_domain` ning O'Z toifasi qoladi va uning tarifi BOSHQA
        son (`A_TARIFF_AMOUNTS`). Bu O'LCHANDI: hisobsiz band rasta
        12 000 qaytardi, 15 000 emas. Ya'ni tarif izlash yo'lini
        o'lchaydigan test AYNAN shu ro'yxatdan rasta olishi kerak — aks
        holda u `market_domain` ning tarifini o'lchab, «noto'g'ri tarif»
        degan YOLG'ON xulosa berardi.
        """
        return (self.stall(3), self.stall(4), self.stall(0), self.stall(5))[index]


@pytest.fixture
def compare(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[CompareEnv]:
    """Billing + bandlik + daftar uchun bo'sh maydon.

    ⛔ `billing_domain_before_day_close` TANLANDI, `billing_domain` EMAS:
       ikkinchisi `day_close` ni SEED KUNIGA (`SEED_BUSINESS_DATE`,
       kelajakda) yugurtiradi va solishtiruv kuniga birorta slot qatori
       bermasdi. Bu variant esa `stall_slot_occupancy` ni BO'SH qoldiradi,
       ya'ni har test kerakli hukmni O'ZI yozadi va «o'lchanmagan» holati
       (qator YO'Q) ham ifodalanadi.

    ⚠ TOZALASH TARTIBI: daftar va slot qatorlari `occupancy_rows`
      yopilishidan OLDIN o'chadi — `stall_slot_occupancy` g'olib hodisaga
      FK bilan tayanadi (`ondelete` YO'Q).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        market_ids = [str(market_id) for market_id in billing.market_ids]
        try:
            yield CompareEnv(billing, market_domain, two_markets, _compare_day(sync_owner_conn))
        finally:
            sync_owner_conn.execute(
                "DELETE FROM ledger_entries WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM stall_slot_occupancy WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            # ⛔ BOZOR AVVAL QORALAMAGA TUSHIRILADI — `add_late_tariff()`
            #    qatorining `valid_from` i BUGUN va `0008` faol bozorda
            #    bunday qatorni O'CHIRISHNI `23514` bilan rad etadi
            #    (`cleanup_billing_domain()` ning aynan birinchi qadami va
            #    aynan sababi). Bayroq bir necha satr keyin baribir
            #    tushiriladi, ya'ni bu semantik jihatdan HALOL.
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])", (market_ids,)
            )
            # ⚠ SUMMA BO'YICHA: `LATE_TARIFF_SOUM` boshqa birorta seedda
            #   uchramaydi (5 000 / 8 000 / 12 000 / 15 000 / 20 000), ya'ni
            #   bu shart faqat SHU testlar yozgan qatorlarni tanlaydi.
            sync_owner_conn.execute(
                "DELETE FROM tariffs WHERE market_id = ANY(%s::uuid[]) AND amount_soum = %s",
                (market_ids, LATE_TARIFF_SOUM),
            )


def write_ledger_row(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    day: date,
    stall_id: UUID,
    amount_soum: int,
    imported_by: UUID,
) -> None:
    """Bitta daftar qatori — marshrutni chetlab, TO'G'RIDAN-TO'G'RI.

    ⚠ Import marshruti bu yerda ATAYIN ISHLATILMAYDI: u yuqoridagi
      bo'limlarda ALLAQACHON o'lchangan va uni har solishtiruv testida
      qayta yugurtirish `three_way()` ning nosozligini import
      nosozligidan ajratib bo'lmaydigan qilardi.
    """
    conn.execute(_SET_MARKET_GUC, (str(market_id),))
    try:
        conn.execute(
            _INSERT_LEDGER_ROW,
            (str(uuid4()), str(market_id), day, str(stall_id), amount_soum, str(imported_by)),
        )
    finally:
        conn.execute(_SET_MARKET_GUC, ("",))


def write_slot(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_id: UUID,
    day: date,
    verdict: str,
    resolution_source: str,
    winning_event_id: UUID | None = None,
    slot: time = _SLOTS[0],
) -> None:
    """Bitta `stall_slot_occupancy` qatori — hukm ARGUMENT bilan.

    ⛔ `occupied` uchun g'olib hodisa MAJBURIY
       (`occupied_has_winning_event`), qolgan hukmlar uchun esa u `NULL`
       BO'LISHI SHART. Ikkala yo'nalish ham konstraytda, ya'ni bu
       yordamchi noto'g'ri chaqirilsa seedning O'ZI yiqiladi.
    """
    conn.execute(
        _INSERT_SLOT_ROW,
        (
            str(uuid4()),
            str(market_id),
            str(stall_id),
            day,
            slot,
            verdict,
            resolution_source,
            None if winning_event_id is None else str(winning_event_id),
        ),
    )


def occupy(
    conn: Connection[TupleRow],
    env: CompareEnv,
    *,
    stall_id: UUID,
    center: tuple[float, float],
    slot_index: int = 0,
) -> None:
    """Rastani solishtiruv kunida BAND qiladi — kadr, zona, hodisa, slot.

    ⛔ ZANJIR TO'LIQ QURILADI, chunki `stall_slot_occupancy` uni TALAB
       QILADI: `occupied` hukmi YAROQLI kadrga osilgan hodisaga ishora
       qilishi shart (D-21 langari). Mavjud seed hodisasini qayta
       ishlatish arzonroq bo'lardi, lekin u BOSHQA KUNGA tegishli va
       o'shanda seedning o'zi «hodisaning kuni = slotning kuni»
       invariantini buzardi.

    ⚠ `slot_index` HAR CHAQIRUVDA BOSHQA bo'lishi kerak: bitta kamera
      bitta kunda bitta slotga BITTA kadr yozadi va ikkinchisi
      `uq_capture_runs_...` bilan rad etilardi. Zona VERSIYASI ham shu
      indeksdan quriladi (`uq_camera_zones_..._version`), ya'ni seed
      rastasining mavjud `version = 1` zonasi bilan to'qnashmaydi.
    """
    nvr_row = conn.execute(
        # ⚠ `capture_runs` DAN — `nvr_domain` ro'yxatining TARTIBIDAN emas
        #   (`fixtures/billing_domain.py::_nvr_of` ning aynan qoidasi).
        "SELECT nvr_id, camera_id FROM capture_runs WHERE market_id = %s ORDER BY nvr_id LIMIT 1",
        (str(env.market_id),),
    ).fetchone()
    assert nvr_row is not None, "nazorat: A bozorida `capture_runs` qatori yo'q"
    nvr_id, camera_id = nvr_row
    slot = _SLOTS[slot_index]

    _, snapshot_id = add_billable_frame(
        conn,
        market_id=env.market_id,
        nvr_id=nvr_id,
        camera_id=camera_id,
        slot=slot,
        day=env.day,
        is_market_open=True,
    )
    _, event_id = add_zone_with_event_on(
        conn,
        market_id=env.market_id,
        camera_id=camera_id,
        stall_id=stall_id,
        snapshot_id=snapshot_id,
        business_date=env.day,
        slot=slot,
        center=center,
        version=90 + slot_index,
    )
    write_slot(
        conn,
        market_id=env.market_id,
        stall_id=stall_id,
        day=env.day,
        verdict=OccupancyVerdict.OCCUPIED.value,
        resolution_source=ResolutionSource.AI.value,
        winning_event_id=event_id,
        slot=slot,
    )


def charge_and_pay(
    conn: Connection[TupleRow],
    env: CompareEnv,
    *,
    stall_id: UUID,
    paid_soum: int | None,
) -> None:
    """Kunning TIZIM tomoni: patta hisobi va (ixtiyoriy) to'lov.

    ⛔ `paid_soum is None` — «hisob bor, to'lov YO'Q» va u O'LCHANGAN
       nol: tizim ustunidagi `0` haqiqiy nol (UI-SPEC §10.4), ya'ni u
       AI-kutilgan ustunining bo'sh katagi bilan ARALASHTIRILMAYDI.

    ⚠ `quote_soum = paid_soum` — ⛔ `TARIFF_SOUM` EMAS va bu SXEMA
      talabidan: `ck_payments_override_is_paired` server summasidan
      chetlangan to'lovdan `override_reason` ni MAJBURIY qiladi
      (o'lchandi: `CheckViolation`). Sababni to'qib yozish testga
      solishtiruvga umuman aloqasi yo'q ikkinchi holat (chetlanish
      sababi) kiritardi; teng qo'yish esa «server shu summani so'radi»
      degan halol, sodda holatni beradi.
    """
    add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
        service_date=env.day,
    )
    if paid_soum is None:
        return
    add_payment(
        conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
        service_date=env.day,
        amount_soum=paid_soum,
        quote_soum=paid_soum,
    )


def add_late_tariff(conn: Connection[TupleRow], env: CompareEnv) -> None:
    """Solishtiruv kunidan KEYIN kuchga kiradigan tarif qatori (Open Question 3).

    ⛔ `valid_from = day + 1`: u o'tgan kunning kutilgan summasiga
       TA'SIR QILMASLIGI kerak. Qator qo'shilmasa (e) testi hech nimani
       o'lchamasdi — «bugungi tarif» va «o'sha kunning tarifi» bir xil
       son bo'lardi.
    """
    conn.execute(
        _INSERT_LATE_TARIFF,
        (
            str(uuid4()),
            str(env.market_id),
            str(env.live.category_id),
            LATE_TARIFF_SOUM,
            env.day + timedelta(days=1),
        ),
    )


def _code_of(conn: Connection[TupleRow], stall_id: UUID) -> str:
    """Rasta kodi — ⛔ BAZADAN, seed ro'yxatining TARTIBIDAN emas.

    `test_report_repo.py::_STALL_CODE` da o'rnatilgan qoida: qo'shni
    faylning ro'yxat tartibiga tayangan test u qayta tartiblangan kuni
    BOSHQA obyektni o'lchardi va buni SEZMASDI ham.
    """
    row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(stall_id),)).fetchone()
    assert row is not None, f"nazorat: {stall_id} rastasi yo'q"
    code: str = row[0]
    return code


def by_code(report: ThreeWayReport) -> dict[str, Any]:
    """`rasta kodi -> qator` — ⛔ NAZORAT: kod TAKRORLANMAYDI.

    Bitta rastani ikki qator bilan qaytargan so'rov (masalan `LEFT JOIN`
    ko'paytirgan bo'lsa) lug'atda JIMGINA qisqarardi va sanoq testi
    baribir yashil qolardi.
    """
    indexed = {row.stall_code: row for row in report.rows}
    assert len(indexed) == len(report.rows), "nazorat: bitta rasta IKKI qator bilan qaytdi"
    return indexed


# ===========================================================================
# (g) UCH USTUN VA ULARNING MANBALARI (D-18)
# ===========================================================================


async def test_the_three_columns_come_from_three_independent_sources(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔ HAR USTUN O'Z MANBASIDAN — UCHALASI HAM BOSHQA-BOSHQA SON.

    =======================================================================
    ⛔ UCH SON ATAYIN UCH XIL: daftar 30 000, tizim 10 000, AI-kutilgan
       15 000. Ikkitasi teng bo'lganda ustunlar aralashib ketgan so'rov
       ham YASHIL qolardi — masalan tizim ustuniga tarif yozilgan bo'lsa.
    """
    stall_id = compare.stall(0)
    occupy(sync_owner_conn, compare, stall_id=stall_id, center=(0.31, 0.71))
    charge_and_pay(sync_owner_conn, compare, stall_id=stall_id, paid_soum=10_000)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=stall_id,
        amount_soum=COMPARE_LEDGER_SOUM,
        imported_by=compare.live.cashier_id,
    )

    async with tenant_session(compare.market_id) as session:
        report = await three_way(session, market_id=compare.market_id, business_date=compare.day)

    assert report.day == compare.day
    assert report.has_ledger is True

    row = by_code(report)[A_STALL_CODES[0]]
    assert row.ledger_soum == COMPARE_LEDGER_SOUM
    assert row.system_soum == 10_000
    assert row.ai_expected_soum == TARIFF_SOUM


async def test_an_unmeasured_ai_column_is_never_the_same_as_a_measured_zero(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔⛔ `None` VA `0` — IKKI XIL NARSA VA FARQ SHU TESTDA (D-10, §10.4).

    =======================================================================
    ⛔ IKKALA HOLAT BITTA TESTDA VA BU ATAYIN: alohida yozilgan ikki test
       «ikkalasi ham `0` qaytadi» degan regressiyada BITTASI yashil
       qolib, ikkinchisi qizarardi — o'quvchi esa ularni bog'lamasdi.
       Yonma-yon assert esa nosozlikni bitta jumla qilib ko'rsatadi.

        `0`    = «AI rastani BO'SH dedi»                  (O'LCHANGAN)
        `None` = «o'sha kun uchun bandlik ma'lumoti yo'q» (O'LCHANMAGAN)

    ⛔ UCHINCHI HOLAT HAM SHU YERDA: `default_empty` — «HECH KIM
       QARAMADI» (AI-06/D-19). U `empty` hukmi bilan YOZILADI, lekin
       manbasi dalil EMAS, ya'ni u ham O'LCHANMAGAN. Uni `0` qilish
       «tizim bo'sh dedi» degan YOLG'ON o'lchov bo'lardi.
    """
    measured_empty, unmeasured, never_looked = (
        compare.stall(0),
        compare.stall(1),
        compare.stall(2),
    )

    # (1) O'LCHANGAN bo'sh — dalil bor (`ai`), hukm `empty`.
    write_slot(
        sync_owner_conn,
        market_id=compare.market_id,
        stall_id=measured_empty,
        day=compare.day,
        verdict=OccupancyVerdict.EMPTY.value,
        resolution_source=ResolutionSource.AI.value,
    )
    # (2) O'LCHANMAGAN — slot qatori UMUMAN yo'q; rasta faqat daftarda.
    # (3) HECH KIM QARAMADI — `default_empty` (AI-06/D-19).
    write_slot(
        sync_owner_conn,
        market_id=compare.market_id,
        stall_id=never_looked,
        day=compare.day,
        verdict=OccupancyVerdict.EMPTY.value,
        resolution_source=ResolutionSource.DEFAULT_EMPTY.value,
    )

    for stall_id in (measured_empty, unmeasured, never_looked):
        write_ledger_row(
            sync_owner_conn,
            market_id=compare.market_id,
            day=compare.day,
            stall_id=stall_id,
            amount_soum=0,
            imported_by=compare.live.cashier_id,
        )

    async with tenant_session(compare.market_id) as session:
        report = await three_way(session, market_id=compare.market_id, business_date=compare.day)

    rows = by_code(report)
    assert rows[A_STALL_CODES[0]].ai_expected_soum == 0, (
        "AI rastani BO'SH dedi — bu O'LCHANGAN nol va u bo'sh katakka aylanmaydi"
    )
    assert rows[A_STALL_CODES[1]].ai_expected_soum is None, (
        "o'sha kun uchun slot qatori YO'Q — bu O'LCHANMAGAN va u `0` bo'lolmaydi"
    )
    assert rows[A_STALL_CODES[2]].ai_expected_soum is None, (
        "`default_empty` — «hech kim qaramadi» (AI-06/D-19), «bo'sh» EMAS"
    )
    assert rows[A_STALL_CODES[0]].ai_expected_soum != rows[A_STALL_CODES[1]].ai_expected_soum


async def test_the_report_carries_four_counters_and_no_total_field(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔⛔ MAYDONLAR TO'PLAMI TENGLIGI — «jami farq» MAYDONI TUG'ILMAYDI.

    =======================================================================
    ⛔ `hasattr(..., "total_diff")` YETMASDI: u faqat BITTA nomni
       qo'riqlardi va `combined_diff` deb atalgan maydon jimgina o'tib
       ketardi. To'plam tengligi esa HAR QANDAY yangi maydonni ushlaydi
       — shu jumladan foydali ko'ringanini ham, chunki qo'shish qarori
       ONGLI bo'lishi va shu qatorda ko'rinishi kerak (D-18).
    """
    async with tenant_session(compare.market_id) as session:
        report = await three_way(session, market_id=compare.market_id, business_date=compare.day)

    assert {field.name for field in fields(report)} == {
        "day",
        "has_ledger",
        "rows",
        "ledger_over_count",
        "system_over_count",
        "ai_mismatch_count",
        "matched_count",
    }


async def test_a_day_without_a_ledger_returns_no_rows_at_all(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔⛔ DAFTAR YO'Q KUN — `has_ledger is False` VA `rows` BO'SH (§10.6).

    =======================================================================
    ⛔ TIZIM VA BANDLIK QATORLARI BOR, ya'ni «ma'lumot yo'q» emas:
       hisoblar ham, to'lov ham, band slot ham yozilgan. Shunga qaramay
       javob BO'SH bo'lishi kerak — daftar yuklanmagan kunda uch ustunli
       jadval «hamma farq 0» bilan chizilsa u MUVAFFAQIYATLI solishtiruv
       bo'lib ko'rinardi va IMZOLANARDI (SC#5 jimgina yo'qolardi).

    ⚠ NAZORAT: `has_ledger` ro'yxat uzunligidan HOSILA emas — bu yerda
      ikkalasi ham tekshiriladi, chunki `rows` ni bo'shatib `has_ledger`
      ni `True` qoldirgan implementatsiya ekranda BOSHQA holatni
      ko'rsatardi.
    """
    stall_id = compare.stall(0)
    occupy(sync_owner_conn, compare, stall_id=stall_id, center=(0.33, 0.62))
    charge_and_pay(sync_owner_conn, compare, stall_id=stall_id, paid_soum=TARIFF_SOUM)

    async with tenant_session(compare.market_id) as session:
        report = await three_way(session, market_id=compare.market_id, business_date=compare.day)

    assert report.has_ledger is False
    assert report.rows == ()
    assert report.matched_count == 0
    assert report.ledger_over_count == 0
    assert report.system_over_count == 0
    assert report.ai_mismatch_count == 0


async def test_yesterdays_expectation_uses_yesterdays_tariff(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔⛔ O'TGAN KUNNING AI-KUTILGANI O'SHA KUNNING TARIFIDAN (Open Question 3).

    =======================================================================
    ⛔ IKKALA YO'L HAM BITTA TESTDA VA IKKALASI HAM MAJBURIY:

      (1) HISOBI BOR rasta — summa `daily_charges.tariff_amount_soum`
          dan, ya'ni kun yopilishida MUZLATILGAN nusxadan (D-09). Tarif
          qatori KEYIN tahrirlansa ham bu son o'zgarmaydi;
      (2) HISOBI YO'Q, lekin BAND rasta — summa `tariffs` dan
          `valid_from <= kun` qoidasi bilan. Bu yo'l bo'lmasa
          biriktirilmagan band rasta (BILL-04/D-28) BO'SH katak olardi
          va u «bandlik o'lchanmagan» bo'lib O'QILARDI — holbuki
          bandlik AYNAN o'lchangan.

    ⛔ IKKALASI HAM `LATE_TARIFF_SOUM` (25 000) NI BERMASLIGI KERAK.
       «Bugungi tarif» ga o'tgan implementatsiya ikkala qatorda ham
       25 000 qaytarardi va uch ustundan ikkitasi bir savolga IKKI XIL
       javob berardi.
    """
    charged_stall, uncharged_stall = compare.billed_stall(2), compare.billed_stall(3)

    occupy(sync_owner_conn, compare, stall_id=charged_stall, center=(0.28, 0.68))
    occupy(
        sync_owner_conn,
        compare,
        stall_id=uncharged_stall,
        center=(0.62, 0.34),
        slot_index=1,
    )
    charge_and_pay(sync_owner_conn, compare, stall_id=charged_stall, paid_soum=TARIFF_SOUM)
    add_late_tariff(sync_owner_conn, compare)

    for stall_id in (charged_stall, uncharged_stall):
        write_ledger_row(
            sync_owner_conn,
            market_id=compare.market_id,
            day=compare.day,
            stall_id=stall_id,
            amount_soum=TARIFF_SOUM,
            imported_by=compare.live.cashier_id,
        )

    async with tenant_session(compare.market_id) as session:
        report = await three_way(session, market_id=compare.market_id, business_date=compare.day)

    rows = by_code(report)
    charged_row = rows[_code_of(sync_owner_conn, charged_stall)]
    uncharged_row = rows[_code_of(sync_owner_conn, uncharged_stall)]

    assert charged_row.ai_expected_soum == TARIFF_SOUM, (
        "hisobi bor rastaning kutilgani MUZLATILGAN tarifdan olinishi kerak edi"
    )
    assert uncharged_row.ai_expected_soum == TARIFF_SOUM, (
        "hisobsiz band rastaning kutilgani O'SHA KUNNING tarifidan olinishi kerak edi"
    )
    assert charged_row.ai_expected_soum != LATE_TARIFF_SOUM


# ===========================================================================
# (h) MARSHRUTLAR — `GET /reports/compare` va `/compare.xlsx` (08-16)
#
# =========================================================================
# ⛔⛔ YO'L `/compare`, REJA AYTGAN `/three-way` EMAS.
#
# `report-queries.ts` (08-03, TO'LQIN 1) AYNAN shu ikki yo'lga boradi:
# `${REPORTS_PATH}/compare?day=` (:253) va `${REPORTS_PATH}/compare.xlsx
# ?day=` (:383). Bu 08-07 (`/debtors`), 08-12 (`/debtors.xlsx`) va 08-14
# (`/compare/ledger`) da qabul qilingan qarorning TO'RTINCHI takrori:
# SERVER KLIENTNI KUZATADI. Boshqa nom tanlansa nosozlik JIMGINA
# bo'lardi — 08-18 ning komponent testlari mock bilan yashil qolardi va
# 404 faqat jonli ekranda ko'rinardi.
# ===========================================================================

COMPARE_URL = "/api/v1/reports/compare"
COMPARE_EXPORT_URL = "/api/v1/reports/compare.xlsx"

COMPARE_RESPONSE_KEYS = {
    "day",
    "has_ledger",
    "rows",
    "ledger_over_count",
    "system_over_count",
    "ai_mismatch_count",
    "matched_count",
}
"""⛔ JAVOB O'RAMI — `api-types.ts::threeWayReportSchema` NING JUFTI.

Klient uni `z.strictObject` bilan o'qiydi, ya'ni ORTIQCHA maydon ham,
yetishmayotgani ham PARSE CHEGARASIDA yiqiladi va direktor hisobot
o'rniga bo'sh ekran ko'radi. Reyestr shu yerda IKKINCHI MARTA yozilgan
(`test_reports_api.py::_keys` naqshi) — javob modelidan olingan to'plam
o'zi bilan o'zini tekshirardi.
"""

COMPARE_ROW_KEYS = {"stall_code", "ledger_soum", "system_soum", "ai_expected_soum", "diff_class"}
"""⛔ QATOR — `threeWayRowSchema` NING JUFTI VA UNDA `vendor_name` YO'Q.

⛔⛔ ISM JSON YUZASIGA CHIQMAYDI, `.xlsx` HUJJATIGA ESA CHIQADI — va bu
    ikki BOSHQA yuza, ikki BOSHQA qaror (D-07 ning aynan shakli):
    ekrandagi jadval rasta kesimida ishlaydi va unga ism KERAK EMAS,
    imzolanadigan hujjatda esa «kimdan so'raladi?» savoli qog'ozda
    javob olishi kerak. Ismni JSON ga «qulaylik uchun» qo'shish klient
    `strictObject` ini buzardi VA marshrutni `PERSONAL_ROUTES` ga
    tortardi (`audit_read` har hisobot ochilishida yozilardi).
"""


def _compare_params(day: date) -> dict[str, str]:
    """`?day=` — ⛔ MAJBURIY, standart YO'Q (`DayDep` qoidasi)."""
    return {"day": day.isoformat()}


@pytest.fixture
def compare_row_limit(api_app: FastAPI, test_settings: Settings) -> Iterator[None]:
    """`report_max_rows = 1` — ⛔ 50 000 QATOR SEED QILINMAYDI.

    `test_reports_api.py::tiny_row_limit` ning aynan nusxasi va aynan
    sababi: o'lchanayotgan narsa SON emas, SHOX — chegaradan oshgan
    javob **422** bo'ladimi yoki JIMGINA kesiladimi. Shox chegaraning
    istalgan qiymatida bir xil.

    ⚠ NUSXA ONGLI: `tiny_row_limit` ni import qilish bu faylni qo'shni
      integratsiya modulining fixture grafiga bog'lardi
      (`test_reports_api.py:106-108` da o'rnatilgan qoida).
    """
    api_app.state.settings = test_settings.model_copy(update={"report_max_rows": 1})
    try:
        yield
    finally:
        api_app.state.settings = test_settings


@pytest.fixture
async def compare_director_headers(
    api_client: httpx.AsyncClient, compare: CompareEnv
) -> dict[str, str]:
    """A bozori DIREKTORI — `report_view` VA `vendor_view` BOR."""
    return await session_headers(api_client, compare.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def compare_cashier_headers(
    api_client: httpx.AsyncClient, compare: CompareEnv
) -> dict[str, str]:
    """A bozori KASSIRI — unda `report_view` YO'Q (UI-SPEC §5.6)."""
    return await session_headers(api_client, compare.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def compare_market_b_headers(
    api_client: httpx.AsyncClient, compare: CompareEnv
) -> dict[str, str]:
    """B bozorining DIREKTORI — cross-tenant da'vosining sub'ekti."""
    return await session_headers(api_client, compare.base.market_b.director_phone, SEED_PASSWORD)


def seed_one_matching_stall(conn: Connection[TupleRow], env: CompareEnv) -> UUID:
    """Uchala manba ham MOS bo'lgan bitta rasta — marshrut testlarining asosi.

    ⚠ `match` holati ATAYIN: marshrut testlari YUZANI o'lchaydi (huquq,
      chegara, bayt), farq sinflarini emas — ular quyida O'Z seedi bilan
      o'lchanadi. Eng sodda holat javobning shaklini eng aniq ko'rsatadi.
    """
    stall_id = env.billed_stall(2)
    occupy(conn, env, stall_id=stall_id, center=(0.29, 0.64))
    charge_and_pay(conn, env, stall_id=stall_id, paid_soum=TARIFF_SOUM)
    write_ledger_row(
        conn,
        market_id=env.market_id,
        day=env.day,
        stall_id=stall_id,
        amount_soum=TARIFF_SOUM,
        imported_by=env.live.cashier_id,
    )
    return stall_id


async def test_the_compare_route_answers_with_the_client_contract_shape(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔ JSON JAVOBI KLIENT `strictObject` I BILAN AYNAN TENG.

    =======================================================================
    ⛔ TO'PLAM TENGLIGI, «kerakli maydonlar bor» EMAS: `z.strictObject`
       ORTIQCHA maydonni ham RAD ETADI, ya'ni «qulaylik uchun» qo'shilgan
       `total_diff` yoki `vendor_name` butun sahifani PARSE chegarasida
       yiqitardi va nosozlik faqat jonli ekranda ko'rinardi.
    """
    stall_id = seed_one_matching_stall(sync_owner_conn, compare)

    response = await api_client.get(
        COMPARE_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == COMPARE_RESPONSE_KEYS
    assert payload["day"] == compare.day.isoformat()
    assert payload["has_ledger"] is True

    code = _code_of(sync_owner_conn, stall_id)
    row = next(item for item in payload["rows"] if item["stall_code"] == code)
    assert set(row) == COMPARE_ROW_KEYS
    assert row["ledger_soum"] == TARIFF_SOUM
    assert row["system_soum"] == TARIFF_SOUM
    assert row["ai_expected_soum"] == TARIFF_SOUM


async def test_a_matched_row_carries_no_diff_class_at_all(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ MOS QATORNING `diff_class` I `null` — `"match"` SATRI EMAS.

    =======================================================================
    ⛔ SABAB KLIENT REYESTRIDA: `api-types.ts::DIFF_CLASSES` AYNAN UCH
       A'ZO (`ledger_over`, `system_over`, `ai_mismatch`) va `match` unda
       ATAYIN YO'Q. Server `"match"` yuborsa klient uni NOMA'LUM qiymat
       deb ZAXIRA YORLIQ chizardi — ya'ni 287 ta mos qator badge olardi
       va 13 ta HAQIQIY farq ular ostida KO'MILIB ketardi (§13.4).

    ⚠ Server tomonida sinf NOM bilan qoladi (`report_repo.DIFF_MATCH`) —
      `matched_count` aynan shunga tayanadi. O'girish BIR joyda, javob
      qurilayotganda bajariladi.
    """
    seed_one_matching_stall(sync_owner_conn, compare)

    response = await api_client.get(
        COMPARE_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["matched_count"] == 1
    classes = {row["diff_class"] for row in payload["rows"]}
    assert "match" not in classes, (
        "«match» satri sim ustiga chiqdi — klient uni noma'lum sinf deb ZAXIRA "
        "yorliq bilan chizardi va mos qator badge olardi (§13.4)"
    )
    assert None in classes


async def test_today_is_refused_because_the_system_day_is_not_closed_yet(
    api_client: httpx.AsyncClient,
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔ `day = bugun` -> **422 `report_period_future`** (UI-SPEC §10.2).

    Bugungi tizim summasi hali yopilmagan (D+1 04:10) va daftar ham kun
    oxirida yig'iladi, ya'ni «bugun» ni solishtirish HAR DOIM farq
    ko'rsatardi va uchala sinf ham SOXTA bo'lardi.
    """
    response = await api_client.get(
        COMPARE_URL, params={"day": _day()}, headers=compare_director_headers
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "report_period_future"


async def test_the_cashier_reaches_neither_compare_surface(
    api_client: httpx.AsyncClient,
    compare_cashier_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔ KASSIR IKKALA MARSHRUTDAN HAM 403 (D-04, UI-SPEC §5.6).

    ⚠ IKKALA YUZA BIRGA o'lchanadi: `.xlsx` ni unutish eng xavfli
      teshikni ochardi — fayl tizimdan CHIQIB ketadi (08-12 darsi).
    """
    for url in (COMPARE_URL, COMPARE_EXPORT_URL):
        response = await api_client.get(
            url, params=_compare_params(compare.day), headers=compare_cashier_headers
        )
        assert response.status_code == 403, f"{url}: {response.text}"


async def test_a_day_over_the_row_limit_is_refused_not_truncated(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
    compare_row_limit: None,
) -> None:
    """⛔⛔ CHEGARADAN OSHGAN KUN **422 `report_too_large`** (R-8, T-08-73).

    =======================================================================
    ⛔ SAHIFALASH ATAYIN YO'Q: solishtiruv KUNLIK va u chop etilib
       IMZOLANADI — sahifalangan hujjatni imzolab bo'lmaydi. Jimgina
       kesish esa undan ham yomon: imzo chekilgan varaqdan tushib qolgan
       rastalarni hech kim SEZMASDI.

    ⚠ IKKALA YUZA HAM: ekranda kesilgan ro'yxat tuzatiladi, faylga
      tushgani esa IMZOLANADI va tarqaladi.
    """
    seed_one_matching_stall(sync_owner_conn, compare)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=compare.billed_stall(0),
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )

    for url in (COMPARE_URL, COMPARE_EXPORT_URL):
        response = await api_client.get(
            url, params=_compare_params(compare.day), headers=compare_director_headers
        )
        assert response.status_code == 422, f"{url}: {response.text}"
        assert response.json()["detail"] == "report_too_large"


async def test_the_export_ends_with_two_blank_signature_lines(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ IMZO QATORLARI FAYLNING PASTIDA VA ISMLAR BO'SH (D-19, §12.6).

    =======================================================================
    ⛔ FAYL BAYTLARI QAYTA O'QILADI (`xlsx_reader.read_rows` — MAHSULOT
       o'quvchisi): quruvchining o'z funksiyasini chaqirib tekshirish
       o'zini o'zi bilan solishtirish bo'lardi va buzilgan ZIP ham
       YASHIL qolardi (08-12 da o'rnatilgan qoida).

    ⛔ ISM OLDINDAN TO'LDIRILMAYDI: tizim KIM imzolashini BILMAYDI va
       bilmagan narsasini yozmaydi. Sessiyadagi odamning ismini qo'yish
       «u imzoladi» degan YOLG'ON dalil bo'lardi — hujjat qog'ozda,
       BOSHQA odam tomonidan imzolanishi mumkin (T-08-74).
    """
    seed_one_matching_stall(sync_owner_conn, compare)

    response = await api_client.get(
        COMPARE_EXPORT_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(XLSX_MEDIA_TYPE)

    rows = read_rows(response.content, expected_columns=COMPARE_EXPORT_COLUMNS)
    executor, approver = rows[-2].values, rows[-1].values

    for line in (executor, approver):
        assert isinstance(line[0], str), f"imzo qatori faylda TOPILMADI: {line!r}"
        assert "___" in line[0], f"imzo uchun bo'sh joy yo'q: {line[0]!r}"
        assert all(cell is None for cell in line[1:]), (
            f"imzo qatoridan keyin qiymat yozilgan: {line!r} — ism OLDINDAN TO'LDIRILMAYDI (D-19)"
        )


async def test_an_unmeasured_expectation_is_a_blank_cell_in_the_file(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ O'LCHANMAGAN KUTILGAN — BO'SH KATAK, `0` EMAS (D-10, T-08-70).

    Bo'sh katak IMZOLANADIGAN varaqda «bandlik o'lchanmagan» degan
    HALOL javob beradi; `0` esa «AI rastani bo'sh dedi» degan
    O'LCHANGAN da'vo bo'lib o'qilardi va u nizoda dalil bo'lib
    ishlatilardi.

    ⚠ NAZORAT: daftarning `0` i AYNI qatorda va u BO'SH EMAS — ya'ni
      test «hamma katak bo'sh» degan buzilishda ham qizaradi.
    """
    unmeasured = compare.billed_stall(2)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=unmeasured,
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )

    response = await api_client.get(
        COMPARE_EXPORT_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )

    assert response.status_code == 200, response.text
    rows = read_rows(response.content, expected_columns=COMPARE_EXPORT_COLUMNS)
    code = _code_of(sync_owner_conn, unmeasured)
    data = next(row.values for row in rows if row.values[0] == code)

    assert data[4] is None, (
        f"AI-kutilgan katagi BO'SH bo'lishi kerak edi, qiymat: {data[4]!r} — "
        "o'lchanmagan miqdor o'lchangan bo'lib chizilardi (D-10)"
    )
    # ⚠ `"0"` SATR: `xlsx_reader._cell_text()` HAR katakni matnga
    #   keltiradi (`float` -> butun -> `str`), ya'ni bu yerda taqqoslash
    #   MATN bo'yicha bo'ladi. Muhim bo'lgan farq shu: `"0"` — KATAKDA
    #   BOR, `None` — katak BO'SH.
    assert data[2] == "0", "daftar summasi O'LCHANGAN nol va u bo'sh katak EMAS"


async def test_the_export_names_the_vendor_and_the_json_never_does(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ ISM FAYLDA BOR, JSON DA YO'Q — IKKI YUZA, IKKI QAROR.

    Bu test ikki da'voni BIRGA ushlaydi va aynan shu sababdan kuchli:
    ismni JSON ga ko'chirgan o'zgarish (klient `strictObject` ini
    buzardi) ham, uni fayldan olib tashlagan o'zgarish (hujjat «kimdan
    so'raladi?» savoliga javob bermay qolardi) ham QIZARADI.
    """
    seed_one_matching_stall(sync_owner_conn, compare)

    exported = await api_client.get(
        COMPARE_EXPORT_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )
    listed = await api_client.get(
        COMPARE_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )

    assert exported.status_code == 200, exported.text
    assert listed.status_code == 200, listed.text

    rows = read_rows(exported.content, expected_columns=COMPARE_EXPORT_COLUMNS)
    names = {row.values[1] for row in rows if isinstance(row.values[1], str)}
    assert any(name.startswith("Aliyev") for name in names), (
        f"hujjatda sotuvchi ismi yo'q: {sorted(names)}"
    )

    assert "vendor_name" not in listed.text, (
        "sotuvchi ismi JSON yuzasiga chiqdi — klient `strictObject` i uni RAD "
        "ETARDI va butun sahifa parse chegarasida yiqilardi"
    )


# ===========================================================================
# (i) FARQ SINFLARI — HAR BIRI ALOHIDA SEED BILAN (§10.5, D-18)
#
# =========================================================================
# ⛔⛔ HAR SINF UCHUN ALOHIDA HOLAT VA U «ko'proq test» EMAS, O'LCHOV.
#
# To'rt sinfni bitta seedda o'lchash sanoqlarni bir-biriga BOG'LARDI:
# `ledger_over` ni `system_over` deb hisoblagan implementatsiya
# yig'indisi to'g'ri bo'lgan holatda ham YASHIL qolardi. Alohida
# holatda esa har sanoq AYNAN BITTA bo'lishi kerak va QOLGAN UCHTASI
# NOL — ya'ni sinflarning ARALASHUVI ham o'lchanadi.
# ===========================================================================


async def _diff_classes(
    tenant_session: TenantSessionFactory, env: CompareEnv
) -> tuple[ThreeWayReport, dict[str, int]]:
    """Hisobot va uning to'rt sanog'i — testlarning UMUMIY oxirgi qadami."""
    async with tenant_session(env.market_id) as session:
        report = await three_way(session, market_id=env.market_id, business_date=env.day)
    return report, {
        "ledger_over": report.ledger_over_count,
        "system_over": report.system_over_count,
        "ai_mismatch": report.ai_mismatch_count,
        "match": report.matched_count,
    }


async def test_a_ledger_larger_than_the_system_is_a_loss_suspicion(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔ DAFTAR > TIZIM -> `ledger_over` (§10.5: «Yo'qotish shubhasi»).

    Qog'ozda 30 000 yozilgan, tizimda esa 15 000 ko'ringan — ya'ni
    15 000 so'm yig'ilgan, lekin tizimga KIRITILMAGAN. Mahsulot AYNAN
    shu holatni fosh qilish uchun mavjud (D-02).
    """
    stall_id = compare.billed_stall(0)
    charge_and_pay(sync_owner_conn, compare, stall_id=stall_id, paid_soum=TARIFF_SOUM)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=stall_id,
        amount_soum=COMPARE_LEDGER_SOUM,
        imported_by=compare.live.cashier_id,
    )

    report, counts = await _diff_classes(tenant_session, compare)

    assert counts == {"ledger_over": 1, "system_over": 0, "ai_mismatch": 0, "match": 0}
    assert by_code(report)[_code_of(sync_owner_conn, stall_id)].diff_class == "ledger_over"


async def test_a_system_larger_than_the_ledger_is_a_bookkeeping_gap(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔ TIZIM > DAFTAR -> `system_over` (§10.5: «Daftar kamchiligi»).

    ⛔⛔ DAFTARDA BU RASTA UMUMAN YO'Q va aynan shu holat sinfning
        MAVJUD BO'LISH SABABI: kun uchun daftar YUKLANGAN, ya'ni u
        o'sha kunning TO'LIQ qog'oz yozuvi va unda ko'rinmagan rasta
        «qog'ozda hech nima yig'ilmagan» degani. Daftar summasini
        `None` qilib qo'ygan implementatsiya bu sinfni HECH QACHON
        hisoblab chiqara olmasdi.
    """
    paid_stall, ledger_stall = compare.billed_stall(0), compare.billed_stall(1)
    charge_and_pay(sync_owner_conn, compare, stall_id=paid_stall, paid_soum=TARIFF_SOUM)
    # ⚠ Daftar BOSHQA rastaga yoziladi — kun uchun daftar MAVJUD, lekin
    #   to'lov qilingan rasta unda YO'Q.
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=ledger_stall,
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )

    report, counts = await _diff_classes(tenant_session, compare)

    assert counts["system_over"] == 1
    assert counts["ledger_over"] == 0
    assert by_code(report)[_code_of(sync_owner_conn, paid_stall)].diff_class == "system_over"


async def test_an_occupied_but_unpaid_stall_is_an_occupancy_gap(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔ AI-KUTILGAN ≠ TIZIM -> `ai_mismatch` (§10.5: «Bandlik farqi»).

    ⛔ SBOZOR NING YADRO HOLATI: rasta BAND, qog'ozda ham, tizimda ham
       pul YO'Q. Daftar va tizim MOS (ikkalasi ham 0), ya'ni birinchi
       ikki sinf JIM qoladi — «band, lekin to'lovsiz» ni FAQAT uchinchi
       manba ko'radi.
    """
    stall_id = compare.billed_stall(0)
    occupy(sync_owner_conn, compare, stall_id=stall_id, center=(0.27, 0.63))
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=stall_id,
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )

    report, counts = await _diff_classes(tenant_session, compare)

    row = by_code(report)[_code_of(sync_owner_conn, stall_id)]
    assert (row.ledger_soum, row.system_soum) == (0, 0), (
        "nazorat: daftar va tizim MOS bo'lishi kerak — aks holda birinchi ikki "
        "sinf ishga tushib, uchinchisi umuman o'lchanmasdi"
    )
    assert row.ai_expected_soum == TARIFF_SOUM
    assert counts == {"ledger_over": 0, "system_over": 0, "ai_mismatch": 1, "match": 0}


async def test_a_matching_stall_stays_in_the_table_as_the_denominator(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare: CompareEnv,
) -> None:
    """⛔⛔ MOS QATOR `rows` DA QOLADI — YASHIRILMAYDI (§10.5, 07 G-32).

    «300 rastadan 287 tasi mos» — MAXRAJ imzolanadigan hujjatda
    MAJBURIY. Mos qatorlarni filtrlab tashlagan javob 13 qatorli varaq
    berardi va u «bozorda 13 ta rasta bor» bo'lib o'qilardi.
    """
    stall_id = seed_one_matching_stall(sync_owner_conn, compare)

    report, counts = await _diff_classes(tenant_session, compare)

    assert counts["match"] == 1
    row = by_code(report)[_code_of(sync_owner_conn, stall_id)]
    assert row.diff_class == "match", "mos qator ro'yxatdan TUSHIB QOLDI"
    assert (row.ledger_soum, row.system_soum, row.ai_expected_soum) == (
        TARIFF_SOUM,
        TARIFF_SOUM,
        TARIFF_SOUM,
    )


async def test_four_classes_in_one_market_stay_four_independent_counters(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    compare_director_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ TO'RT SANOQ MUSTAQIL VA ULARNI QO'SHIB BO'LMAYDI (D-18).

    =======================================================================
    ⛔ DA'VO UCH QATLAMLI VA UCHALASI HAM MAJBURIY:

      1. HAR SANOQ AYNAN BITTA — sinflar bir-biriga OQIB O'TMAYDI;
      2. JAVOBDA YIG'INDI MAYDONI YO'Q — to'plam tengligi bilan
         (`total_diff` ham, `combined_diff` ham, boshqa nom ham);
      3. ⛔⛔ TO'RT SANOQNING YIG'INDISI `len(rows)` GA TENG EMAS.

    Uchinchisi eng qimmat va u ATAYIN o'lchanadi: seedda BESHINCHI
    rasta bor — daftar va tizimi MOS, AI-kutilgani esa O'LCHANMAGAN.
    Bunday qator na farq DA'VO QILADI, na moslik, ya'ni birorta
    sanoqqa tushmaydi. Tenglikni «tiklashga» urinish uni
    `matched_count` ga qo'shishni talab qilardi — ya'ni imzolanadigan
    varaqda «uchala manba mos» degan YOLG'ON maxrajni shishirardi
    (D-10 ning bevosita buzilishi).
    =======================================================================
    """
    over_stall, under_stall = compare.billed_stall(0), compare.billed_stall(1)
    mismatch_stall, match_stall = compare.billed_stall(2), compare.billed_stall(3)
    unmeasured_stall = compare.stall(1)

    # (a) daftar ortiq
    charge_and_pay(sync_owner_conn, compare, stall_id=over_stall, paid_soum=TARIFF_SOUM)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=over_stall,
        amount_soum=COMPARE_LEDGER_SOUM,
        imported_by=compare.live.cashier_id,
    )
    # (b) tizim ortiq — daftarda YO'Q
    charge_and_pay(sync_owner_conn, compare, stall_id=under_stall, paid_soum=TARIFF_SOUM)
    # (c) bandlik farqi — band, lekin to'lovsiz
    occupy(sync_owner_conn, compare, stall_id=mismatch_stall, center=(0.26, 0.61), slot_index=0)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=mismatch_stall,
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )
    # (d) mos
    occupy(sync_owner_conn, compare, stall_id=match_stall, center=(0.64, 0.36), slot_index=1)
    charge_and_pay(sync_owner_conn, compare, stall_id=match_stall, paid_soum=TARIFF_SOUM)
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=match_stall,
        amount_soum=TARIFF_SOUM,
        imported_by=compare.live.cashier_id,
    )
    # (e) SINFSIZ — AI o'lchanmagan, daftar va tizim MOS
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=unmeasured_stall,
        amount_soum=0,
        imported_by=compare.live.cashier_id,
    )

    report, counts = await _diff_classes(tenant_session, compare)

    assert counts == {"ledger_over": 1, "system_over": 1, "ai_mismatch": 1, "match": 1}, (
        f"sinflar bir-biriga oqib o'tdi: {counts}"
    )
    assert len(report.rows) == 5
    assert sum(counts.values()) != len(report.rows), (
        "to'rt sanoqning yig'indisi qatorlar soniga TENG bo'lib qoldi — demak "
        "o'lchanmagan AI-kutilganli qator birorta sinfga QO'SHILGAN va u "
        "imzolanadigan varaqda maxrajni SHISHIRADI (D-10)"
    )

    response = await api_client.get(
        COMPARE_URL, params=_compare_params(compare.day), headers=compare_director_headers
    )
    assert response.status_code == 200, response.text
    assert set(response.json()) == COMPARE_RESPONSE_KEYS, (
        "javobga yig'indi maydoni qo'shildi — uch sinf uch TURLI harakatni "
        "talab qiladi va ularni bitta songa siqish solishtiruvni foydasiz qilardi"
    )


async def test_the_other_markets_director_sees_none_of_market_a_stalls(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    compare_market_b_headers: dict[str, str],
    compare: CompareEnv,
) -> None:
    """⛔⛔ B BOZORINING DIREKTORI A NING KUNIDA A NING RASTALARINI KO'RMAYDI.

    =======================================================================
    ⛔ NAZORAT HOLATI MAJBURIY: B ning O'Z daftar qatori ham yoziladi va
       javobda u KO'RINISHI shart. Faqat «A ning kodi yo'q» degan assert
       bo'sh javobda ham YASHIL bo'lardi — ya'ni «marshrut umuman
       ishlamadi» bilan «tenant chegarasi ishladi» ni ajratmasdi.

    ⚠ `A_ONLY_STALL_CODE` ATAYIN: `"2"` IKKALA bozorda ham mavjud, ya'ni
      u bilan yozilgan test B ning O'Z rastasini ko'rib «sizib chiqdi»
      degan YOLG'ON xulosa berardi.
    =======================================================================
    """
    a_stall = compare.stall(2)
    assert _code_of(sync_owner_conn, a_stall) == A_ONLY_STALL_CODE, (
        "nazorat: seedning rasta tartibi o'zgargan"
    )
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.market_id,
        day=compare.day,
        stall_id=a_stall,
        amount_soum=COMPARE_LEDGER_SOUM,
        imported_by=compare.live.cashier_id,
    )

    b_stall = compare.domain.market_b.stall_ids[0]
    write_ledger_row(
        sync_owner_conn,
        market_id=compare.other.market_id,
        day=compare.day,
        stall_id=b_stall,
        amount_soum=TARIFF_SOUM,
        imported_by=compare.other.cashier_id,
    )

    response = await api_client.get(
        COMPARE_URL, params=_compare_params(compare.day), headers=compare_market_b_headers
    )

    assert response.status_code == 200, response.text
    codes = {row["stall_code"] for row in response.json()["rows"]}

    assert codes == {_code_of(sync_owner_conn, b_stall)}, (
        f"B ning javobida BEGONA rastalar bor: {sorted(codes)}"
    )
    assert A_ONLY_STALL_CODE not in codes
    assert B_STALL_CODES[0] in codes, "nazorat: B ning O'Z qatori ham chiqmadi"
