"""Sotuvchining kunma-kun to'lov tarixi HAQIQIY BAZADA (261006).

=============================================================================
⛔⛔ NEGA BU FAYL BOR — PROD'DA O'LCHANGAN XATO.

    Tarixning birinchi versiyasi holatni «o'sha kuni hisob / o'sha kuni
    to'lov» dan chiqarardi. Unit testlar yashil edi, haqiqiy bazada esa
    qarzi nolga tushirilgan bozorda (36 sotuvchi) 261 kun «to'lanmagan»
    yoki «qisman» ko'rindi: kassir bugungi pattani va eski qarzni BITTA
    to'lov bilan oladi (`payments.py`: `as_of = business_today()`), ya'ni
    to'lov kunga bog'lanmaydi (C-4).

    Bu fayl o'sha xatoni QAYTA tug'diradigan holatlarni o'lchaydi:
    holat `FIFO_OLDEST_SERVICE_DATE_FIRST` (D-24) dan chiqishi va tarix
    qarz kartasi (`receivables()`) bilan ZIDLASHMASLIGI kerak.

⛔ HAQIQIY `postgres:18.4`: RLS, audit triggeri va `CHECK` o'lchanadi.

⚠ Yordamchilar `test_debt_settlement.py` dagi bilan bir xil va ATAYIN
  takrorlangan: test modullari bir-birini import qilmaydi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.debt_settlement import settle_market
from app.repositories.billing_repo import vendor_outstanding
from app.repositories.report_repo import VendorHistory, receivables, vendor_day_history
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_daily_charge,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import cleanup_notification_domain
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    PaymentKind,
    PaymentMethod,
    ReversalReason,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

_PATTA = 15_000
"""Bir kunlik hisob — testlarning o'z summasi (seed tarifiga bog'lanmaydi)."""

_REQUEST_ID = "pytest-vendor-history"

_SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — tuzatish qatorini yozish uchun."""

_INSERT_PAYMENT_AT = (
    "INSERT INTO payments "
    "(id, market_id, stall_id, vendor_id, service_date, amount_soum, quote_soum, kind, "
    " method, reverses_payment_id, reversal_reason, idempotency_key, request_fingerprint, "
    " cashier_id, created_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
    " now() - make_interval(days => %s))"
)


@dataclass(frozen=True)
class Env:
    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    @property
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    @property
    def stall_ids(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids

    @property
    def director_id(self) -> UUID:
        return self.base.market_a.director_user_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[Env]:
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets)


@pytest.fixture
def recon(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[Env]:
    """Kechirish yo'li case'larga tegadi — ular billing qatorlaridan OLDIN o'chadi."""
    try:
        yield env
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(env.billing.market_ids))


def _today(conn: Connection[TupleRow]) -> date:
    """Bazaning bugungi biznes-kuni — `business_date` ifodasi bilan AYNI mintaqa."""
    row = conn.execute("SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date").fetchone()
    assert row is not None
    value: date = row[0]
    return value


def _charge(conn: Connection[TupleRow], env: Env, day: date, *, amount: int = _PATTA) -> UUID:
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[0],
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
        amount_soum=amount,
        service_date=day,
    )
    return charge_id


def _pay(
    conn: Connection[TupleRow],
    env: Env,
    today: date,
    *,
    amount: int,
    days_ago: int = 0,
    reverses: UUID | None = None,
) -> UUID:
    """To'lov yoki storno — `days_ago` kun oldin YOZILGAN (`service_date` ham o'sha kun)."""
    payment_id = uuid4()
    conn.execute(
        _INSERT_PAYMENT_AT,
        (
            str(payment_id),
            str(env.market_id),
            str(env.stall_ids[0]),
            str(env.vendor_id),
            today - timedelta(days=days_ago),
            amount,
            amount,
            PaymentKind.REVERSAL.value if reverses is not None else PaymentKind.PAYMENT.value,
            PaymentMethod.CASH.value,
            None if reverses is None else str(reverses),
            None if reverses is None else ReversalReason.WRONG_AMOUNT.value,
            f"history-{payment_id}",
            "history-fingerprint",
            str(env.cashier_id),
            days_ago,
        ),
    )
    return payment_id


def _adjust(
    conn: Connection[TupleRow], env: Env, charge_id: UUID, *, reason: AdjustmentReason, amount: int
) -> None:
    conn.execute(_SET_MARKET, (str(env.market_id),))
    try:
        conn.execute(
            "INSERT INTO charge_adjustments "
            "(market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                str(env.market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                reason.value,
                amount,
                str(env.director_id),
            ),
        )
    finally:
        conn.execute(_SET_MARKET, ("",))


async def _history(
    tenant_session: TenantSessionFactory, env: Env, *, from_date: date, to_date: date
) -> VendorHistory:
    async with tenant_session(env.market_id) as session:
        return await vendor_day_history(
            session,
            market_id=env.market_id,
            vendor_id=env.vendor_id,
            from_date=from_date,
            to_date=to_date,
        )


def _by_day(history: VendorHistory) -> dict[date, Any]:
    return {row.service_date: row for row in history.rows}


# ===========================================================================
# 1. HOLAT FIFO DAN — O'SHA KUNGI TO'LOVDAN EMAS
# ===========================================================================


async def test_status_follows_fifo_not_the_days_own_payment(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Uch kun hisob, pul esa BOSHQA kuni (hisobsiz kunda) olingan.

    Eski versiya uchala kunni ham «to'lanmagan» derdi — o'sha kunlari
    to'lov yo'q edi. FIFO esa pulni eng eski kundan boshlab taqsimlaydi.
    """
    today = _today(sync_owner_conn)
    for n in (5, 4, 3):
        _charge(sync_owner_conn, env, today - timedelta(days=n))
    _pay(sync_owner_conn, env, today, amount=20_000, days_ago=1)

    history = await _history(
        tenant_session, env, from_date=today - timedelta(days=6), to_date=today - timedelta(days=1)
    )
    days = _by_day(history)

    oldest = days[today - timedelta(days=5)]
    assert (oldest.status, oldest.covered_soum, oldest.paid_soum) == ("paid", _PATTA, 0), (
        "o'sha kuni to'lov YO'Q, lekin FIFO uni keyingi pul bilan yopgan — «to'landi»"
    )
    middle = days[today - timedelta(days=4)]
    assert (middle.status, middle.covered_soum, middle.unpaid_soum) == ("partial", 5_000, 10_000)
    newest = days[today - timedelta(days=3)]
    assert (newest.status, newest.unpaid_soum) == ("unpaid", _PATTA)
    cash_day = days[today - timedelta(days=1)]
    assert (cash_day.status, cash_day.paid_soum, cash_day.charged_soum) == ("advance", 20_000, 0)

    assert [row.service_date for row in history.rows] == sorted(days, reverse=True), (
        "eng yangi kun birinchi"
    )


async def test_history_never_contradicts_the_debt_card(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """⛔ ASOSIY INVARIANT: tarix va qarz kartasi BIR XIL sonni aytadi.

    `outstanding_soum` — `vendor_outstanding()` (BILL-03) bilan, eng eski
    qizil kun — `receivables().oldest_unpaid_date` bilan teng.
    """
    today = _today(sync_owner_conn)
    for n in (5, 4, 3):
        _charge(sync_owner_conn, env, today - timedelta(days=n))
    _pay(sync_owner_conn, env, today, amount=20_000, days_ago=1)
    from_date, to_date = today - timedelta(days=6), today - timedelta(days=1)

    history = await _history(tenant_session, env, from_date=from_date, to_date=to_date)
    async with tenant_session(env.market_id) as session:
        balances = await vendor_outstanding(
            session, market_id=env.market_id, as_of=to_date + timedelta(days=1)
        )
        card = [
            row
            for row in await receivables(
                session, market_id=env.market_id, from_date=from_date, to_date=to_date
            )
            if row.vendor_id == env.vendor_id
        ]

    assert history.outstanding_soum == balances[env.vendor_id] == 25_000
    assert sum(row.unpaid_soum for row in history.rows) == history.outstanding_soum
    (card_row,) = card
    assert card_row.outstanding_soum == history.outstanding_soum
    oldest_red = min(row.service_date for row in history.rows if row.unpaid_soum > 0)
    assert card_row.oldest_unpaid_date == oldest_red, (
        "kartadagi «eng eski qarz kuni» va tarixdagi eng eski qizil kun ZID"
    )
    for row in history.rows:
        assert row.charged_soum - row.waived_soum == row.covered_soum + row.unpaid_soum, (
            f"{row.service_date}: hisob − kechirim ≠ qoplangan + qarz"
        )


# ===========================================================================
# 2. PROD HOLATI: QARZ KECHIRILGACH BIRORTA HAM QIZIL KUN QOLMAYDI
# ===========================================================================


async def test_after_debt_settlement_no_day_is_left_unpaid(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ 261006 DA PROD'DA KO'RINGAN XATONING AYNAN O'ZI.

    Qarz `settle_market()` bilan nolga tushirildi, tarix esa o'sha
    kunlarni «to'lanmagan» ko'rsatdi. Endi kechirilgan qism FIFO qoldig'i
    tushgan kunlarda «kechirilgan» bo'ladi, qolgani «to'landi».
    """
    today = _today(sync_owner_conn)
    for n in (5, 4, 3):
        _charge(sync_owner_conn, recon, today - timedelta(days=n))
    _pay(sync_owner_conn, recon, today, amount=20_000, days_ago=4)
    async with tenant_session(recon.market_id, recon.director_id, request_id=_REQUEST_ID) as s:
        await settle_market(
            s, market_id=recon.market_id, before=today, actor_user_id=recon.director_id
        )

    history = await _history(
        tenant_session,
        recon,
        from_date=today - timedelta(days=6),
        to_date=today - timedelta(days=1),
    )
    days = _by_day(history)

    assert [row.status for row in history.rows if row.status in {"unpaid", "partial"}] == []
    assert history.outstanding_soum == 0
    assert days[today - timedelta(days=5)].status == "paid"
    middle = days[today - timedelta(days=4)]
    assert (middle.status, middle.covered_soum, middle.waived_soum) == ("waived", 5_000, 10_000), (
        "qisman to'langan, qolgani kechirilgan kun — «kechirilgan», «to'landi» EMAS"
    )
    assert middle.paid_soum == 20_000, "o'sha kuni kassaga tushgan pul FAKT sifatida ko'rinadi"
    newest = days[today - timedelta(days=3)]
    assert (newest.status, newest.waived_soum, newest.covered_soum) == ("waived", _PATTA, 0)


# ===========================================================================
# 3. FAKTLAR: STORNO MINUS, TUZATISH KECHIRIM EMAS, DAVR TAQSIMLASHNI KESMAYDI
# ===========================================================================


async def test_a_reversed_payment_is_not_counted_as_money(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Birinchi versiya `sum(amount_soum)` yozgan edi: storno IKKINCHI to'lov bo'lib qo'shilardi."""
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, env, today - timedelta(days=2))
    paid = _pay(sync_owner_conn, env, today, amount=_PATTA, days_ago=2)
    _pay(sync_owner_conn, env, today, amount=_PATTA, days_ago=2, reverses=paid)

    history = await _history(
        tenant_session, env, from_date=today - timedelta(days=3), to_date=today - timedelta(days=1)
    )
    (row,) = history.rows

    assert (row.paid_soum, row.payment_count) == (0, 1)
    assert (row.status, row.unpaid_soum) == ("unpaid", _PATTA)


async def test_a_correction_is_not_shown_as_a_waiver(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Hisob tuzatilgan (kamera xatosi) — bu «direktor kechirdi» EMAS."""
    today = _today(sync_owner_conn)
    charge = _charge(sync_owner_conn, env, today - timedelta(days=2))
    _adjust(sync_owner_conn, env, charge, reason=AdjustmentReason.LATE_REVIEW, amount=5_000)
    _pay(sync_owner_conn, env, today, amount=10_000, days_ago=2)

    history = await _history(
        tenant_session, env, from_date=today - timedelta(days=3), to_date=today - timedelta(days=1)
    )
    (row,) = history.rows

    assert (row.charged_soum, row.waived_soum) == (10_000, 0)
    assert (row.status, row.covered_soum, row.unpaid_soum) == ("paid", 10_000, 0)


async def test_debt_older_than_the_period_still_eats_the_payment(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """⛔ TAQSIMLASH DAVR BILAN KESILMAYDI.

    Davrdan tashqaridagi eski qarz davr ichidagi to'lovni FIFO bo'yicha
    oladi. Kesilgan taqsimlash uni ko'rmasdi va davr kunini «to'landi»
    derdi — karta esa qarz ko'rsatardi.
    """
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, env, today - timedelta(days=10))
    _charge(sync_owner_conn, env, today - timedelta(days=3))
    _pay(sync_owner_conn, env, today, amount=_PATTA, days_ago=3)

    history = await _history(
        tenant_session, env, from_date=today - timedelta(days=5), to_date=today - timedelta(days=1)
    )
    (row,) = history.rows

    assert (row.paid_soum, row.covered_soum) == (_PATTA, 0), (
        "o'sha kuni to'langan pul eng eski (davrdan tashqaridagi) kunga ketgan"
    )
    assert (row.status, history.outstanding_soum) == ("unpaid", _PATTA)
