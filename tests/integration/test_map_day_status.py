"""`GET /api/v1/billing/map` — PLAN-XARITANING KUNLIK TO'LOV HOLATI (MARKET-06).

=============================================================================
⛔⛔ BU FAYLNING YAGONA MAVZUSI — **HOLAT QARORI**, PUL ARIFMETIKASI EMAS.

Summa qayerdan kelishini `test_billing_repo.py` 30 darvoza bilan
o'lchagan. Bu yerda o'lchanadigan narsa BOSHQA: `resolve_stall_day_money()`
bergan summa, `payments` bergan belgili to'lov va `reconciliation_cases`
bergan ochiq case bitta rasta ustida uchrashganda **qaysi rang chiqadi**.

Ustuvorlik tartibi (D-C2) ATAYIN bitta jadval:

    1. ochiq case bor                 -> mismatch
    2. amount_soum is None            -> no_billing
    3. vendor_id is None              -> free
    4. amount_soum - paid_soum <= 0   -> paid
    5. qolgan hamma holat             -> due

Har qadam ALOHIDA test bilan qulflanadi. Bitta testda ikki qadamni
o'lchash «qaysi shart ishladi?» savolini javobsiz qoldirardi.

=============================================================================
⛔ KUN — `business_today()`, VA U TESTDA MAJBURLANMAYDI.

Marshrutda `?day=` parametri YO'Q (D-C5). Ya'ni har test BUGUNGI kun
ustida ishlaydi va bugungi kun HAFTA KUNIGA bog'liq: A bozori dushanba
yopiq (`A_OPEN_WEEKDAYS`). Shuning uchun rangni o'lchaydigan har bir test
`_set_calendar()` bilan bugungi kunni **ATAYIN OCHIQ** qiladi va yopiq kun
testi uni **ATAYIN YOPIQ** qiladi. Kalendar holatini tasodifga qoldirish
testni haftaning kuniga bog'lardi (06-06 deviatsiya #6 ning aynan sinfi).

=============================================================================
⚠ CASE QATORLARI SEED CLEANUP'IGA KIRMAYDI VA BU FAYL ULARNI O'ZI TOZALAYDI.

`billing_domain.CLEANUP_ORDER` da `reconciliation_cases` YO'Q, case esa
`daily_charges` / `billing_anomalies` ga KOMPOZIT FK bilan (`ondelete`
YO'Q) bog'langan — ya'ni tozalanmagan case KEYINGI testning seed'ini
yiqitardi va nosozlik bu faylda emas, qo'shni faylda ko'rinardi
(`tests/tenancy/test_cross_tenant.py:1643-1657` da o'lchangan naqsh).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
    day_total_soum,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import seed_case
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentReason,
    PaymentKind,
    ReconciliationCaseStatus,
    ReversalReason,
)
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    import httpx
    from psycopg import Connection
    from psycopg.rows import TupleRow

MAP_URL = "/api/v1/billing/map"

MAP_ROW_KEYS = frozenset(
    {
        "stall_id",
        "state",
        "amount_soum",
        "unavailable_reason",
        "paid_soum",
        "remaining_soum",
        "open_case_id",
        "open_case_service_date",
    }
)
"""Qator kalitlarining AYNAN to'plami (D-31 — `==`, `not in` EMAS).

⛔ `stall_code` YO'Q: xarita kataklari `id` bo'yicha bog'lanadi va kod
   `GET /stalls/map` da ALLAQACHON bor. Ikkinchi manba ikki ro'yxatni bir
   kun ajratib yuborardi.

⛔ `vendor_outstanding` YO'Q (D-C6): u RASTA darajasidagi miqdor emas —
   bir sotuvchining uch rastasida takrorlanib, ko'z bilan qo'shilganda
   uch barobar ko'rinardi.

⛔ `charge_id` YO'Q: `test_billing_api.py::
   test_charge_id_is_declared_only_by_the_charge_routes` uni butun
   `/billing/*` yuzasi bo'ylab MEXANIK qo'riqlaydi.
"""

MAP_BODY_KEYS = frozenset({"service_date", "market_active", "market_open", "rows"})

PARTIAL_SOUM = 5_000
"""Qisman to'lov — bugungi to'liq pattadan (`day_total_soum()`: 17 000 yoki
22 000) KICHIK va noldan KATTA.

⛔ Bugungi summa QADALMAYDI: bu fayl `business_today()` ustida ishlaydi,
   tarif zanjiri esa `NEXT_TARIFF_VALID_FROM` da o'zgaradi — qadalgan
   `DAY_TOTAL_SOUM` 2026-09-02 dan beri o'n bitta testni JIMGINA qizartirgan
   edi (`day_total_soum` docstringi).

⚠ Qator `override_reason` bilan yoziladi: `OVERRIDE_IS_PAIRED_CHECK`
  (`(amount_soum = quote_soum) = (override_reason IS NULL)`) server
  bergan summadan har qanday chetlanishdan SABAB talab qiladi. `quote`
  ni ham 5 000 qilib qo'yish konstraytni chetlab o'tardi, lekin
  «kassir kamroq oldi» holatini SOXTALASHTIRARDI — bu yerda esa aynan
  o'sha holat o'lchanadi.
"""


class Env:
    """Uch qatlamli seed — `test_billing_api.Env` ning aynan takrori."""

    def __init__(
        self, billing: BillingDomainSeed, domain: MarketDomainSeed, base: TwoMarketSeed
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    @property
    def shift_id(self) -> UUID:
        return self.billing.market_a.open_shift_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id: UUID | None = getattr(self.billing.market_a, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id

    @property
    def stall_without_any_assignment(self) -> UUID:
        """⛔ `market_domain` NING `unassigned_stall` I — BIRORTA biriktirishsiz.

        `fixtures/market_domain.py:484-485`: `stall_ids[2]` ga birorta
        `stall_assignments` qatori yozilmaydi va bu holat SANAGA BOG'LIQ
        EMAS (boshqa ikkala «bo'shliq» rastasi vaqt o'tishi bilan
        biriktirilgan holatga o'tadi). Toifasi va tarifi esa BOR
        (`_seed_market()` har rastaga toifa davri yozadi), ya'ni bu rasta
        `free` ni `no_billing` DAN ajratadigan yagona seed elementi.
        """
        return self.domain.market_a.stall_ids[2]

    @property
    def stall_outside_the_billing_tariff_chain(self) -> UUID:
        """Billing toifa zanjiriga KIRMAGAN rasta — `tariff_missing` uchun asos.

        `billing_domain._seed_market_a()` toifa davrini faqat to'rt
        rastaga yozadi; `stall_ids[1]` ularning ichida YO'Q, ya'ni unda
        `BILLING_VALID_FROM` sanali ikkinchi toifa davri mavjud emas va
        bugungi sanaga yangi davr yozish konfliktga urilmaydi.
        """
        return self.domain.market_a.stall_ids[1]


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed + ⛔ CASE TOZALASH (modul docstringidagi ⚠).

    `day_close` CHAQIRILMAYDI: bu faylning birorta da'vosi bandlikka
    tayanmaydi (`test_billing_api.py::env` da o'rnatilgan qoida).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        try:
            yield Env(billing, market_domain, two_markets)
        finally:
            market_ids = [str(market_id) for market_id in billing.market_ids]
            # ⛔ TARIX AVVAL, CASE KEYIN: `reconciliation_case_events`
            #    case'ga kompozit FK bilan bog'langan.
            sync_owner_conn.execute(
                "DELETE FROM reconciliation_case_events WHERE market_id = ANY(%s::uuid[])",
                (market_ids,),
            )
            sync_owner_conn.execute(
                "DELETE FROM reconciliation_cases WHERE market_id = ANY(%s::uuid[])",
                (market_ids,),
            )


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Bozor admini — unda `billing_collect_view` BOR (D-C4)."""
    market_a = env.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def platform_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Platforma admini — unda `billing_collect_view` ⛔ YO'Q (D-C4).

    U SOZLASH roli: `rbac.py` unga `report_view` ni ham, `billing_collect_
    view` ni ham ATAYIN bermaydi. Bozor MAJBURIY tanlanadi — aks holda
    javob `403 market_not_selected` bo'lardi va test huquqni emas,
    sessiyaning bo'shligini o'lchagan bo'lardi.
    """
    return await session_headers(
        api_client,
        env.base.platform_admin_phone,
        SEED_PASSWORD,
        market_id=env.market_id,
    )


# ===========================================================================
# YORDAMCHILAR — hech biri mahsulot qoidasini TAKRORLAMAYDI (§S-9)
# ===========================================================================


def _set_calendar(conn: Connection[TupleRow], *, market_id: UUID, day: date, is_open: bool) -> None:
    """Bugungi kunni ATAYIN ochiq yoki yopiq qiladi (modul docstringi).

    ⚠ `ON CONFLICT` MAJBURIY: `uq_market_calendar_exceptions_market_id_
      exception_date` bir kunga ikkinchi istisnoni rad etadi va seed
      allaqachon bitta istisno yozgan bo'lishi mumkin.
    """
    conn.execute(
        "INSERT INTO market_calendar_exceptions "
        "(id, market_id, exception_date, is_open, note) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (market_id, exception_date) DO UPDATE SET is_open = EXCLUDED.is_open",
        (str(uuid4()), str(market_id), day, is_open, "map-day-status test"),
    )


def _move_to_a_category_without_a_tariff(
    conn: Connection[TupleRow], *, market_id: UUID, stall_id: UUID, day: date
) -> None:
    """Rastani BUGUNDAN tarifsiz toifaga ko'chiradi — `tariff_missing` manbai.

    ⚠ YANGI TOIFA YOZILADI, mavjudi TAHRIRLANMAYDI: A bozorining uchala
      toifasida ham tarif BOR (`A_TARIFF_AMOUNTS`) va tarifni o'chirish
      `trg_tariff_past_immutable` ga urilardi.
    """
    category_id = uuid4()
    conn.execute(
        "INSERT INTO stall_categories (id, market_id, name) VALUES (%s, %s, %s)",
        (str(category_id), str(market_id), "Tarifsiz toifa (map-day test)"),
    )
    conn.execute(
        "INSERT INTO stall_category_periods "
        "(id, market_id, stall_id, category_id, valid_from) VALUES (%s, %s, %s, %s, %s)",
        (str(uuid4()), str(market_id), str(stall_id), str(category_id), day),
    )


async def _fetch(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, object]:
    response = await client.get(MAP_URL, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def _rows_by_stall(body: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = body["rows"]
    assert isinstance(rows, list)
    return {str(row["stall_id"]): row for row in rows}


def _row(body: dict[str, object], stall_id: UUID) -> dict[str, object]:
    rows = _rows_by_stall(body)
    key = str(stall_id)
    assert key in rows, f"javobda {key} rastasining qatori yo'q — javob: {sorted(rows)}"
    return rows[key]


# ===========================================================================
# 1. JAVOBNING SHAKLI
# ===========================================================================


async def test_the_map_payload_declares_exactly_its_documented_keys(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ To'plam TENGLIGI — `MAP_ROW_KEYS` docstringidagi uch taqiq bilan."""
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=business_today(), is_open=True)

    body = await _fetch(api_client, admin_headers)

    assert set(body) == MAP_BODY_KEYS, f"javob kalitlari kutilgandan farq qiladi: {sorted(body)}"
    assert body["service_date"] == business_today().isoformat()
    assert body["market_active"] is True
    assert body["market_open"] is True

    rows = _rows_by_stall(body)
    assert rows, "faol bozorda birorta rasta qatori qaytmadi"
    for row in rows.values():
        assert set(row) == MAP_ROW_KEYS, f"qator kalitlari farq qiladi: {sorted(row)}"


# ===========================================================================
# 2. BESHALA HOLAT — HAR BIRI ALOHIDA TEST
# ===========================================================================


async def test_a_fully_paid_stall_is_blue(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T1 — bugungi tarifi to'liq yopilgan rasta `paid`."""
    today = business_today()
    total = day_total_soum(today)
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_two_occupied_slots")

    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        service_date=today,
        amount_soum=total,
        quote_soum=total,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "paid", row
    assert row["amount_soum"] == total
    assert row["paid_soum"] == total
    assert row["unavailable_reason"] is None
    # ⛔ QOLDIQ SERVERDA AYIRILADI (D-20) va katakning rangi AYNI shu
    #   songa qaraydi — klientdagi ikkinchi ayirish taqiqlanadi.
    assert row["remaining_soum"] == 0


async def test_an_unpaid_stall_is_red(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T2 — tarifi va sotuvchisi bor, to'lovi yo'q rasta `due`.

    ⚠ `paid_soum` NOL bo'lib QAYTADI, maydon TUSHIB QOLMAYDI: nol —
      NATIJA («bugun hali to'lanmadi»), uning yo'qligi emas.
    """
    today = business_today()
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_one_ai_occupied_slot")

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "due", row
    assert row["amount_soum"] == day_total_soum(today)
    assert row["paid_soum"] == 0


async def test_a_partially_paid_stall_stays_red(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T3 — ⛔ QISMAN TO'LOV KO'K QILMAYDI.

    Chegara `amount - paid <= 0`, `paid > 0` EMAS. Ikkinchisi bo'lganda
    1 so'm to'lagan rasta xaritada TO'LIQ to'langan ko'rinardi va bu
    mahsulot AYNAN fosh qilishi kerak bo'lgan holat.
    """
    today = business_today()
    total = day_total_soum(today)
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_two_occupied_slots")

    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        service_date=today,
        amount_soum=PARTIAL_SOUM,
        quote_soum=total,
        override_reason=AdjustmentReason.PARTIAL_DAY.value,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "due", row
    assert row["paid_soum"] == PARTIAL_SOUM
    assert row["amount_soum"] == total
    assert row["remaining_soum"] == total - PARTIAL_SOUM


async def test_a_stall_without_a_vendor_is_green(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T4 — ⛔ YASHIL = «sotuvchi biriktirilmagan», BANDLIK EMAS (D-C3).

    Rastada TARIF BOR, ya'ni javob `no_billing` emas: ikki holat
    ajralib turadi va aynan shu ajralish legendaning ikki satrini
    ma'noli qiladi.
    """
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=business_today(), is_open=True)
    stall_id = env.stall_without_any_assignment

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "free", row
    assert row["amount_soum"] is not None, (
        "nazorat: `free` rastasida tarif BO'LISHI shart — aks holda u "
        "`no_billing` shoxidan o'tib ketardi va test hech nimani ajratmasdi"
    )
    assert row["unavailable_reason"] is None


async def test_a_closed_day_paints_nothing(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T5a — yopiq kunda HAR BIR rasta `no_billing` / `market_closed`."""
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=business_today(), is_open=False)

    body = await _fetch(api_client, admin_headers)

    assert body["market_open"] is False
    rows = _rows_by_stall(body)
    assert rows, "yopiq kunda ham rastalar qatori QAYTADI — bo'sh javob yo'qlik bo'lardi"
    for stall_id, row in rows.items():
        assert row["state"] == "no_billing", (stall_id, row)
        assert row["unavailable_reason"] == "market_closed", (stall_id, row)
        assert row["amount_soum"] is None, (stall_id, row)
        # ⛔ NOL EMAS, `null`: hisob yo'q kunda «qolgan qarz» MA'NOSIZ va
        #   nol uni «to'liq to'langan» bilan bir xil ko'rsatardi.
        assert row["remaining_soum"] is None, (stall_id, row)


async def test_a_stall_without_a_tariff_paints_nothing(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T5b — tarifsiz rasta `no_billing` / `tariff_missing`, ochiq kunda ham.

    ⛔ IKKINCHI SABAB ALOHIDA O'LCHANADI: bitta `no_billing` testi ikkala
       sababni ham qamrasa, server har doim `market_closed` yozib
       tursa ham yashil qolardi.
    """
    today = business_today()
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall_outside_the_billing_tariff_chain
    _move_to_a_category_without_a_tariff(
        sync_owner_conn, market_id=env.market_id, stall_id=stall_id, day=today
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "no_billing", row
    assert row["unavailable_reason"] == "tariff_missing", row
    assert row["amount_soum"] is None


# ===========================================================================
# 3. USTUVORLIK VA BELGILI TO'LOV
# ===========================================================================


async def test_an_open_case_outranks_a_full_payment(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T6 — ⛔ SARIQ KO'KDAN USTUN (D-C2 ning 1-qatori).

    To'liq to'langan rasta ham ochiq nomuvofiqlik case'i bo'lsa `mismatch`
    bo'lib qoladi: «pul kelgan» degan fakt «bu pul to'g'rimi?» degan ochiq
    savolni YOPMAYDI.
    """
    today = business_today()
    total = day_total_soum(today)
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_two_occupied_slots")

    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        service_date=today,
        amount_soum=total,
        quote_soum=total,
    )
    charge_id, service_date = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
    )
    case_id = seed_case(
        sync_owner_conn,
        market_id=env.market_id,
        service_date=service_date,
        charge_id=charge_id,
        status=ReconciliationCaseStatus.NEW.value,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "mismatch", row
    assert row["open_case_id"] == str(case_id)
    assert row["open_case_service_date"] == service_date.isoformat()
    # ⚠ Pul MAYDONLARI YO'QOLMAYDI: karta ularni AYNI qatordan o'qiydi.
    assert row["paid_soum"] == total
    assert row["amount_soum"] == total


async def test_a_closed_case_does_not_paint_yellow(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T6b — SALBIY NAZORAT: `justified` case rangni O'ZGARTIRMAYDI.

    Usiz T6 «case qatori BORmi?» degan savolni o'lchardi, «case OCHIQmi?»
    degan savolni emas — va yopilgan nomuvofiqlik xaritani mangu sariq
    qoldirardi.
    """
    today = business_today()
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_one_ai_occupied_slot")

    charge_id, service_date = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
    )
    seed_case(
        sync_owner_conn,
        market_id=env.market_id,
        service_date=service_date,
        charge_id=charge_id,
        status=ReconciliationCaseStatus.JUSTIFIED.value,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "due", row
    assert row["open_case_id"] is None
    assert row["open_case_service_date"] is None


async def test_an_open_case_reaches_the_stall_through_the_anomaly_branch(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T6c — case IKKI YO'L bilan rastaga ulanadi va IKKALASI ham o'lchanadi.

    `reconciliation_cases` nishoni XOR: `anomaly_id` YOKI `charge_id`
    (DQ-5). Faqat bittasini o'lchash ikkinchi shoxni JIMGINA o'lik
    qoldirardi — `UNION ALL` ning yarmi hech qachon bajarilmasdi.
    """
    today = business_today()
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_one_ai_occupied_slot")

    anomaly_id = uuid4()
    sync_owner_conn.execute(
        "INSERT INTO billing_anomalies (id, market_id, kind, stall_id, service_date) "
        "VALUES (%s, %s, %s, %s, %s)",
        (str(anomaly_id), str(env.market_id), "no_coverage_stall", str(stall_id), today),
    )
    case_id = seed_case(
        sync_owner_conn,
        market_id=env.market_id,
        service_date=today,
        anomaly_id=anomaly_id,
        status=ReconciliationCaseStatus.IN_REVIEW.value,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "mismatch", row
    assert row["open_case_id"] == str(case_id)


async def test_a_reversed_payment_falls_back_to_red(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T7 — ⛔ STORNO BELGILI: bekor qilingan to'lov ko'kni QAYTARIB OLADI.

    `payments.amount_soum` da `CHECK (> 0)` bor, ya'ni storno manfiy
    summa bilan emas, `kind = 'reversal'` bilan yoziladi va belgi
    `_SIGNED_PAYMENT_EXPR` da tug'iladi. Xom `sum(amount_soum)` bu
    rastani MANGU ko'k qoldirardi.
    """
    today = business_today()
    total = day_total_soum(today)
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=today, is_open=True)
    stall_id = env.stall("stall_with_two_occupied_slots")

    original_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        service_date=today,
        amount_soum=total,
        quote_soum=total,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        service_date=today,
        amount_soum=total,
        quote_soum=total,
        kind=PaymentKind.REVERSAL.value,
        reverses_payment_id=original_id,
        reversal_reason=ReversalReason.WRONG_STALL.value,
    )

    row = _row(await _fetch(api_client, admin_headers), stall_id)

    assert row["state"] == "due", row
    assert row["paid_soum"] == 0, (
        "belgili yig'indi nolga tushishi SHART — aks holda storno jimgina "
        "e'tiborsiz qolardi va xarita to'lanmagan rastani ko'k ko'rsatardi"
    )
    assert row["remaining_soum"] == total


# ===========================================================================
# 4. QORALAMA BOZOR VA HUQUQ CHEGARASI
# ===========================================================================


async def test_a_draft_market_paints_no_cell_at_all(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T8 — ⛔ QORALAMA BOZORDA YOLG'ON QIZIL YO'Q.

    Qoralama bozorda `billing_close` hisob YOZMAYDI, ya'ni «bugun patta
    kutilyapti» degan har qanday rang YOLG'ON bo'lardi. Javob buni
    `market_active = false` bilan AYTADI va `rows` ni BO'SH qaytaradi —
    klient esa banner ko'rsatadi.
    """
    _set_calendar(sync_owner_conn, market_id=env.market_id, day=business_today(), is_open=True)
    sync_owner_conn.execute(
        "UPDATE markets SET is_active = false WHERE id = %s", (str(env.market_id),)
    )

    body = await _fetch(api_client, admin_headers)

    assert body["market_active"] is False
    assert body["rows"] == []
    assert body["market_open"] is None, (
        "qoralama bozorda kalendar UMUMAN so'ralmaydi — `false` yozish "
        "«o'lchanmagan» ni «yopiq» deb ko'rsatardi (D-01 intizomi)"
    )


async def test_a_principal_without_the_collect_permission_is_refused(
    api_client: httpx.AsyncClient,
    env: Env,
    platform_headers: dict[str, str],
) -> None:
    """T9 — `billing_collect_view` siz ko'ruvchi -> **403** (D-C4).

    ⛔ MEXANIZM: `require_permission(BILLING_COLLECT_VIEW)`,
       `require_any_permission()` EMAS (C-9 ning yopiq to'plami).
    """
    response = await api_client.get(MAP_URL, headers=platform_headers)

    assert response.status_code == 403, response.text


async def test_the_market_admin_reaches_the_map_layer(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """T10 — NAZORAT: huquqi BOR rolda marshrut 200 qaytaradi.

    Usiz T9 marshrut UMUMAN yo'q bo'lganda ham yashil bo'lardi (404 emas,
    403 kutilgani uchun u ushlanardi — lekin ro'yxatga kirmagan
    marshrutda ham 403 chiqishi mumkin edi).
    """
    response = await api_client.get(MAP_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
