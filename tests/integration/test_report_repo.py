"""`report_repo` — UCH DAVR HISOBOTINING ARIFMETIKASI HAQIQIY BAZADA (RECON-04).

=============================================================================
UCHTA QOIDA BU FAYLNING SHAKLINI BELGILAYDI — `test_billing_repo.py` ning
aynan uch qoidasi, chunki o'lchanayotgan narsa AYNI qatlam.

  1. ⛔ HAQIQIY `postgres:18.4`, soxta qatlam YO'Q. Tekshirilayotgan
     narsaning O'ZI — `generate_series`, `LEFT JOIN LATERAL`, `string_agg`
     va `business_date` ning GENERATED ustuni. Ularni almashtirgan test o'z
     tasavvurini o'lchagan bo'lardi.

  2. ⛔ SESSIYA TENANT KONTEKSTI BILAN (`tenant_session`). Hisobot so'rovi
     `market_id = :market_id` sharti BILAN BIRGA RLS ostida yuguradi va
     anomaliya arxivining tenant bandi (T-08-13) AYNAN shu ikki qatlamni
     o'lchaydi.

  3. ⛔ SANA BAZADAN O'QILADI, TESTDA HISOBLANMAYDI. `payments.business_date`
     va `daily_charges.business_date` — `created_at` DAN HOSILA generated
     ustunlar va ular `Asia/Tashkent` da hisoblanadi, UTC `CURRENT_DATE` da
     EMAS. Ya'ni `date.today()` bilan yozilgan davr 19:00 UTC dan keyin
     BOSHQA kunni ko'rsatardi va test kechqurun jimgina qizarardi.
     Shuning uchun davr `_business_date_of_payment()` ning javobidan
     QURILADI (`fixtures/billing_domain.py::_safe_service_date` ning aynan
     o'sha darsi).
=============================================================================
⚠ IKKI SANA IKKI SAVOLGA JAVOB BERADI VA BU FAYL AYNAN SHU FARQNI O'LCHAYDI
  (Pitfall 14):

      payments.business_date     — pul QACHON yig'ildi (kassa kuni)
      daily_charges.service_date — QAYSI KUNNING pattasi

  `test_revenue_splits_a_yesterday_charge_from_a_today_payment` da to'lovning
  O'Z `service_date` i ATAYIN KECHAGI kun qilib qo'yilgan: agar so'rov
  `payments.service_date` ga o'tib ketsa ikkala ustun ham bir kunga tushardi
  va nosozlik ko'rinmasdi.
=============================================================================
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from app.repositories.report_repo import revenue_by_day
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import AdjustmentDirection, AdjustmentReason, PaymentKind, ReversalReason

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date
    from uuid import UUID

    from app.repositories.report_repo import RevenueRow
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow

ADJUSTMENT_SOUM = 5_000
"""Tuzatish summasi — ⛔ `TARIFF_SOUM` DAN KICHIK VA UNGA TENG EMAS.

Teng bo'lganda netlangan hisob NOLGA tushardi va «tuzatish qo'llandi» bilan
«hisob umuman topilmadi» MEXANIK ravishda bir xil ko'rinardi. Kichik va
noldan farqli qiymat ikkalasini ajratadi: 15 000 − 5 000 = 10 000.
"""

_INSERT_ADJUSTMENT = (
    "INSERT INTO charge_adjustments "
    "(id, market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""Hisob tuzatishi — `test_reconciliation_repo.py:149-152` ning VERBATIM nusxasi.

⚠ NUSXA ONGLI: fixture'ga chiqarish o'sha faylning darvozasini bu faylning
  ehtiyojiga bog'lardi va SQL jadval strukturasi bilan birga o'zgaradi —
  u sxema darvozasi (`test_meta.py`) bilan allaqachon qo'riqlangan.
"""

_SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — `charge_adjustments` AUDIT OSTIDA.

Jadval `BILLING_AUDITED_TABLES` da va uning DB-triggeri `app.market_id`
GUC'idan o'qiydi. Kontekstsiz `INSERT` audit qatorini EGASIZ qoldirardi.
Blok tugagach kontekst BO'SHATILADI: `sync_owner_conn` autocommit rejimida
ishlaydi va qoldirilgan qiymat keyingi testga sizib o'tardi.
"""

_PAYMENT_BUSINESS_DATE = "SELECT business_date FROM payments WHERE id = %s"
"""To'lovning KASSA KUNI — ⛔ BAZADAN, `date.today()` DAN EMAS (3-qoida)."""


class Env:
    """Uch qatlamli seed — `test_billing_repo.Env` ning tor varianti.

    ⚠ `day_close` CHAQIRILMAYDI: davr hisobotlari `stall_slot_occupancy` ga
      UMUMAN tegmaydi — ularning kirishi yozilgan hisoblar, to'lovlar,
      tuzatishlar, anomaliyalar va case'lar. Slotlarni materializatsiya
      qilish har testga ikki `day_close` yugurishini qo'shardi va hech
      qanday da'voni kuchaytirmasdi.
    """

    def __init__(
        self, billing: BillingDomainSeed, domain: MarketDomainSeed, base: TwoMarketSeed
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — hisobotlar shu bozor uchun quriladi."""
        return self.billing.market_a

    @property
    def other(self) -> MarketBillingRows:
        """B bozori — tenant chegarasining NAZORAT tomoni."""
        return self.billing.market_b

    @property
    def market_id(self) -> UUID:
        return self.live.market_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id: UUID | None = getattr(self.live, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — klass docstringidagi sabab."""
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets)


def _business_date_of_payment(conn: Connection[TupleRow], payment_id: UUID) -> date:
    """To'lovning KASSA KUNI — generated ustunning HAQIQIY qiymati.

    ⛔ `date.today()` YOZILMAYDI: ustun `Asia/Tashkent` da hisoblanadi va
       19:00 UTC dan keyin u UTC kunidan BIR KUN OLDINDA bo'ladi. Testda
       hisoblangan sana o'sha oynada boshqa kunga tushardi va davr bir
       qatorga qisqarardi — nosozlik esa mahsulotda emas, testda bo'lardi.
    """
    row = conn.execute(_PAYMENT_BUSINESS_DATE, (str(payment_id),)).fetchone()
    assert row is not None, f"nazorat: {payment_id} to'lovi yozilmagan"
    business_date: date = row[0]
    return business_date


def _add_adjustment(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    charge_id: UUID,
    direction: AdjustmentDirection,
    amount_soum: int,
) -> UUID:
    """Bitta `charge_adjustments` qatori — tenant GUC'i BILAN (`_SET_MARKET_GUC`)."""
    adjustment_id = uuid4()
    conn.execute(_SET_MARKET_GUC, (str(market_id),))
    try:
        conn.execute(
            _INSERT_ADJUSTMENT,
            (
                str(adjustment_id),
                str(market_id),
                str(charge_id),
                direction.value,
                AdjustmentReason.TARIFF_CORRECTION.value,
                amount_soum,
                None,
            ),
        )
    finally:
        conn.execute(_SET_MARKET_GUC, ("",))
    return adjustment_id


def _by_day(rows: tuple[RevenueRow, ...]) -> dict[date, RevenueRow]:
    """`business_date -> qator` — ⛔ NAZORAT: kunlar TAKRORLANMAYDI.

    `generate_series` bir kunni ikki marta bersa (yoki `LATERAL` qator
    ko'paytirsa) lug'at jimgina qisqarardi va yig'indi testi baribir
    yashil qolardi.
    """
    indexed = {row.business_date: row for row in rows}
    assert len(indexed) == len(rows), "nazorat: bir kun IKKI qator bilan qaytdi"
    return indexed


# ===========================================================================
# 1. TUSHUM — IKKI SANA, IKKI USTUN, `generate_series` BILAN NOL KUNLAR
# ===========================================================================


async def test_revenue_keeps_a_moneyless_day_as_a_zero_row(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ TO'LOVSIZ KUN QATOR SIFATIDA CHIQADI VA IKKALA SUMMASI 0.

    =========================================================================
    ⛔ JIM KUN DAVRNING ICHIDA, CHETIDA EMAS — VA BU O'LCHOVNING O'ZAGI.

    Uch kunlik davrning BIRINCHISIDA hisob, UCHINCHISIDA to'lov bor;
    o'rtasi bo'sh. `GROUP BY` bilan yozilgan so'rov o'rtadagi kunni
    BUTUNLAY tushirib qoldirardi va direktor «o'sha kuni tizim ishlamadi»
    bilan «o'sha kuni pul yig'ilmadi» ni ajrata olmasdi. Chetdagi bo'sh kun
    bu nosozlikni KO'RSATMASDI: davr chegarasi baribir ikki qator berardi.

    ⚠ TUZATISH HAM SHU YERDA O'LCHANADI: `decrease` yo'nalishi netlangan
      hisobni 15 000 dan 10 000 ga tushiradi. Xom `daily_charges.amount_soum`
      ni o'qigan so'rov 15 000 qaytarib QIZARADI.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")

    payment_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )
    pay_day = _business_date_of_payment(sync_owner_conn, payment_id)
    silent_day = pay_day - timedelta(days=1)
    charge_day = pay_day - timedelta(days=2)

    charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
        service_date=charge_day,
    )
    _add_adjustment(
        sync_owner_conn,
        market_id=env.market_id,
        charge_id=charge_id,
        direction=AdjustmentDirection.DECREASE,
        amount_soum=ADJUSTMENT_SOUM,
    )

    async with tenant_session(env.market_id) as session:
        period = await revenue_by_day(
            session, market_id=env.market_id, from_date=charge_day, to_date=pay_day
        )

    assert [row.business_date for row in period.rows] == [charge_day, silent_day, pay_day], (
        "davr UCH kunni QATOR sifatida berishi kerak edi — `generate_series` yo'q bo'lsa "
        "jim kun butunlay tushib qolardi"
    )

    rows = _by_day(period.rows)
    silent = rows[silent_day]
    assert silent.collected_soum == 0
    assert silent.payment_count == 0
    assert silent.charged_soum == 0
    assert silent.charge_count == 0

    charged = rows[charge_day]
    assert charged.charged_soum == TARIFF_SOUM - ADJUSTMENT_SOUM
    assert charged.charge_count == 1
    assert charged.collected_soum == 0

    collected = rows[pay_day]
    assert collected.collected_soum == TARIFF_SOUM
    assert collected.payment_count == 1
    assert collected.charged_soum == 0

    assert period.total_collected_soum == TARIFF_SOUM
    assert period.total_charged_soum == TARIFF_SOUM - ADJUSTMENT_SOUM
    assert all(isinstance(row.collected_soum, int) for row in period.rows)
    assert all(isinstance(row.charged_soum, int) for row in period.rows)


async def test_revenue_lets_a_reversal_reduce_the_collected_total(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ STORNO YIG'INDINI KAMAYTIRADI — `_SIGNED_PAYMENT_EXPR` ning o'lchovi.

    =========================================================================
    ⚠ UCHTA QATOR, IKKITA EMAS — VA BU ATAYIN.

    Ikki qator (bitta to'lov + bitta storno) bilan javob NOL bo'lardi va
    «belgi qo'llandi» bilan «so'rov birorta qator topmadi» MEXANIK ravishda
    bir xil ko'rinardi. Uchta qator bilan uchta xulosa bir-biridan ajraladi:

        belgili yig'indi -> 15 000   (kutilgan)
        belgisiz yig'indi -> 45 000  (`kind` e'tiborsiz qoldirilgan)
        bo'sh natija      -> 0       (so'rov umuman topmadi)

    ⚠ `payment_count` UCHALA QATORNI sanaydi: storno — kassirning AMALI va
      u to'lovlar jurnalida ko'rinadi. Sanoqdan chiqarish hisobotdagi
      qatorlar sonini jurnalnikidan farq qiladigan qilardi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")

    first = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
        kind=PaymentKind.REVERSAL.value,
        reverses_payment_id=first,
        reversal_reason=ReversalReason.WRONG_AMOUNT.value,
    )
    pay_day = _business_date_of_payment(sync_owner_conn, first)

    async with tenant_session(env.market_id) as session:
        period = await revenue_by_day(
            session, market_id=env.market_id, from_date=pay_day, to_date=pay_day
        )

    assert len(period.rows) == 1
    row = period.rows[0]
    assert row.collected_soum == TARIFF_SOUM, (
        "belgili yig'indi kutilgan edi: 15 000 + 15 000 − 15 000. "
        "45 000 — `kind` e'tiborsiz qoldirilgan; 0 — so'rov qator topmagan"
    )
    assert row.payment_count == 3
    assert period.total_collected_soum == TARIFF_SOUM


async def test_revenue_splits_a_yesterday_charge_from_a_today_payment(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ PITFALL 14 NING AYNAN O'LCHOVI — ikki sana, ikki ustun, ikki kun.

    =========================================================================
    Kassir BUGUN kechagi qarzni to'laydi:

        to'lov  -> BUGUNGI `collected_soum`  (`payments.business_date`)
        patta   -> KECHAGI `charged_soum`    (`daily_charges.service_date`)

    ⛔ TO'LOVNING O'Z `service_date` I ATAYIN KECHAGI KUN QILIB QO'YILGAN.
       Shunda `payments.business_date` o'rniga `payments.service_date` ga
       o'tib ketgan so'rov IKKALA summani ham bitta kunga to'plardi va test
       QIZARADI. Standart qiymat bilan (`CURRENT_DATE - 1`) bu sabotaj
       o'lchanmay qolardi — sana tasodifan mos kelib qolishi mumkin edi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")

    probe = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )
    pay_day = _business_date_of_payment(sync_owner_conn, probe)
    charge_day = pay_day - timedelta(days=1)

    add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
        service_date=charge_day,
    )

    async with tenant_session(env.market_id) as session:
        period = await revenue_by_day(
            session, market_id=env.market_id, from_date=charge_day, to_date=pay_day
        )

    rows = _by_day(period.rows)
    assert rows[charge_day].charged_soum == TARIFF_SOUM
    assert rows[charge_day].collected_soum == 0, (
        "kechagi kunda PUL YIG'ILMAGAN — to'lov bugungi kassa kuniga tegishli"
    )
    assert rows[pay_day].collected_soum == TARIFF_SOUM
    assert rows[pay_day].charged_soum == 0, (
        "bugun PATTA HISOBLANMAGAN — hisob kechagi `service_date` ga yozilgan"
    )
