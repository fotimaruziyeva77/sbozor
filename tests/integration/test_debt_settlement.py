"""`debt_settlement` — o'tgan davr qarzlarini yopish HAQIQIY BAZADA (260925-kvq).

Buyurtmachi qarori: chegara kunidan OLDINGI qarzlar to'langan deb hisoblanadi,
o'sha davrning hal qilinmagan ishlari yopiladi, chegara kunidan boshlab tizim
odatdagidek ishlaydi.

=============================================================================
⛔ HAQIQIY `postgres:18.4`: RLS, audit triggeri, `CHECK` va FK o'lchanadi —
   kechirish qatori aynan o'sha to'siqlardan o'tishi kerak.

⛔ CHEGARA KUNI — BAZANING bugungi biznes-kuni (`Asia/Tashkent`).
   `payments.business_date` `created_at` dan hosila, ya'ni «eski to'lov»
   faqat `created_at` ni o'tmishga qo'yib yoziladi (`_pay()`); bugungi
   to'lov esa oddiy `now()` bilan.

⚠ Tozalash tartibi `test_reconciliation_repo.py` dagi bilan bir xil: case'lar
  billing qatorlaridan OLDIN o'chadi (`recon` fixture'i `env` ni oladi).
=============================================================================
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.debt_settlement import (
    SETTLEMENT_CASE_STATUS,
    SettlementInvariantError,
    market_directors,
    pick_decision_maker,
    plan_market_settlement,
    settle_market,
    settlement_note,
)
from app.jobs.reconciliation import overdue_cutoff
from app.repositories.billing_repo import vendor_charge_allocation, vendor_outstanding
from app.repositories.reconciliation_repo import open_cases
from app.repositories.user_repo import MarketUser
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_daily_charge,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import (
    cleanup_notification_domain,
    seed_case,
    seed_no_coverage_anomaly,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    PaymentKind,
    PaymentMethod,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
    ReversalReason,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_PATTA = 15_000
"""Bir kunlik hisob — testlarning o'z summasi (seed tarifiga bog'lanmaydi)."""

_REQUEST_ID = "pytest-settle-debts"

_NEW = ReconciliationCaseStatus.NEW.value
_IN_REVIEW = ReconciliationCaseStatus.IN_REVIEW.value
_JUSTIFIED = ReconciliationCaseStatus.JUSTIFIED.value

_SCRIPT = Path(__file__).resolve().parents[2] / "ops" / "scripts" / "settle_debts.py"

_SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — FAQAT `audit_log` ni o'qish uchun."""

_INSERT_PAYMENT_AT = (
    "INSERT INTO payments "
    "(id, market_id, stall_id, vendor_id, service_date, amount_soum, quote_soum, kind, "
    " method, reverses_payment_id, reversal_reason, idempotency_key, request_fingerprint, "
    " cashier_id, created_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
    " now() - make_interval(days => %s))"
)
"""To'lov — `created_at` O'TMISHGA qo'yilishi mumkin (`business_date` undan hosila)."""


# ===========================================================================
# Fixture'lar — `test_reconciliation_repo.py::env` naqshi
# ===========================================================================


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
    """Case'lar billing qatorlaridan OLDIN o'chadi (FK `ondelete` YO'Q)."""
    try:
        yield env
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(env.billing.market_ids))


# ===========================================================================
# Yordamchilar
# ===========================================================================


def _today(conn: Connection[TupleRow]) -> date:
    """Bazaning bugungi biznes-kuni — `business_date` ifodasi bilan AYNI mintaqa."""
    row = conn.execute("SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date").fetchone()
    assert row is not None
    value: date = row[0]
    return value


def _charge(
    conn: Connection[TupleRow], env: Env, day: date, *, stall: int = 0, amount: int = _PATTA
) -> UUID:
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[stall],
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
    """To'lov yoki storno — `days_ago` kun oldin YOZILGAN (`business_date`)."""
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
            f"settle-{payment_id}",
            "settle-fingerprint",
            str(env.cashier_id),
            days_ago,
        ),
    )
    return payment_id


async def _settle(tenant_session: TenantSessionFactory, env: Env, before: date) -> Any:
    async with tenant_session(env.market_id, env.director_id, request_id=_REQUEST_ID) as session:
        return await settle_market(
            session, market_id=env.market_id, before=before, actor_user_id=env.director_id
        )


async def _outstanding(
    tenant_session: TenantSessionFactory, market_id: UUID, *, as_of: date | None = None
) -> dict[UUID, int]:
    async with tenant_session(market_id) as session:
        return await vendor_outstanding(session, market_id=market_id, as_of=as_of)


def _adjustments(conn: Connection[TupleRow], market_id: UUID) -> list[tuple[Any, ...]]:
    return list(
        conn.execute(
            "SELECT a.charge_id, a.direction, a.reason_code, a.amount_soum, a.actor_user_id, a.id "
            "FROM charge_adjustments a JOIN daily_charges c "
            "ON c.market_id = a.market_id AND c.id = a.charge_id "
            "WHERE a.market_id = %s ORDER BY c.service_date",
            (str(market_id),),
        ).fetchall()
    )


def _payment_count(conn: Connection[TupleRow], market_id: UUID) -> int:
    row = conn.execute("SELECT count(*) FROM payments WHERE market_id = %s", (str(market_id),))
    fetched = row.fetchone()
    assert fetched is not None
    return int(fetched[0])


def _case_status(conn: Connection[TupleRow], case_id: UUID) -> tuple[Any, ...]:
    row = conn.execute(
        "SELECT status, resolution_note, assignee_user_id FROM reconciliation_cases WHERE id = %s",
        (str(case_id),),
    ).fetchone()
    assert row is not None
    return tuple(row)


def _events(conn: Connection[TupleRow], case_id: UUID) -> list[tuple[Any, ...]]:
    return list(
        conn.execute(
            "SELECT from_status, to_status, actor_user_id, note "
            "FROM reconciliation_case_events WHERE case_id = %s ORDER BY created_at",
            (str(case_id),),
        ).fetchall()
    )


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("settle_debts_script", _SCRIPT)
    assert spec is not None and spec.loader is not None, f"{_SCRIPT} topilmadi"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ===========================================================================
# 1. QARZ KECHIRILADI — SOXTA TO'LOVSIZ, AUDIT BILAN
# ===========================================================================


async def test_unpaid_old_debt_is_waived_without_writing_payments(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    charges = [_charge(sync_owner_conn, recon, today - timedelta(days=n)) for n in (5, 4, 3)]
    payments_before = _payment_count(sync_owner_conn, recon.market_id)

    result = await _settle(tenant_session, recon, today)

    assert result.adjustments_written == 3
    rows = _adjustments(sync_owner_conn, recon.market_id)
    assert [row[0] for row in rows] == charges
    for _, direction, reason, amount, actor, _ in rows:
        assert direction == AdjustmentDirection.DECREASE.value
        assert reason == AdjustmentReason.DIRECTOR_WAIVER.value
        assert amount == _PATTA
        assert actor == recon.director_id, "«kim qaror qildi?» — bozor direktori"
    assert _payment_count(sync_owner_conn, recon.market_id) == payments_before, (
        "soxta to'lov yozilmasligi kerak edi"
    )

    outstanding = await _outstanding(tenant_session, recon.market_id, as_of=today)
    assert outstanding.get(recon.vendor_id, 0) == 0


async def test_every_waiver_is_audited_with_the_director_as_actor(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, recon, today - timedelta(days=2))

    await _settle(tenant_session, recon, today)

    ((*_, adjustment_id),) = _adjustments(sync_owner_conn, recon.market_id)
    # `audit_read` policy'si tenant-scoped va jadval EGASIGA ham qo'llanadi
    # (`test_billing_close.py::SET_MARKET` bilan bir xil sabab).
    sync_owner_conn.execute(_SET_MARKET, (str(recon.market_id),))
    try:
        audit = sync_owner_conn.execute(
            "SELECT actor_user_id, actor_kind, action, request_id FROM audit_log "
            "WHERE table_name = 'charge_adjustments' AND row_id = %s",
            (str(adjustment_id),),
        ).fetchall()
    finally:
        sync_owner_conn.execute(_SET_MARKET, ("",))
    assert audit == [(recon.director_id, "user", "insert", _REQUEST_ID)]


# ===========================================================================
# 2. FIFO — ESKI TO'LOV ESKI KUNLARNI YOPADI, FAQAT QOLDIQ KECHIRILADI
# ===========================================================================


async def test_old_payments_cover_the_oldest_days_and_only_the_remainder_is_waived(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    oldest, middle, newest = (
        _charge(sync_owner_conn, recon, today - timedelta(days=n)) for n in (5, 4, 3)
    )
    _pay(sync_owner_conn, recon, today, amount=20_000, days_ago=4)

    result = await _settle(tenant_session, recon, today)

    waived = {row[0]: row[3] for row in _adjustments(sync_owner_conn, recon.market_id)}
    assert oldest not in waived, "eng eski kun to'liq to'langan — kechirilmaydi"
    assert waived == {middle: 10_000, newest: _PATTA}
    assert result.plan.waived_soum == 25_000
    (vendor,) = [row for row in result.plan.vendors if row.vendor_id == recon.vendor_id]
    assert (vendor.old_due_soum, vendor.old_credit_soum, vendor.advance_soum) == (45_000, 20_000, 0)


# ===========================================================================
# 3. BUGUNGI TO'LOV BUGUNGA QOLADI, AVANS O'ZGARMAYDI
# ===========================================================================


async def test_todays_payment_is_not_spent_on_old_debt(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    old = _charge(sync_owner_conn, recon, today - timedelta(days=2))
    _pay(sync_owner_conn, recon, today, amount=_PATTA)  # bugun yozilgan

    result = await _settle(tenant_session, recon, today)

    assert {row[0]: row[3] for row in _adjustments(sync_owner_conn, recon.market_id)} == {
        old: _PATTA
    }, "eski hisob TO'LIQ kechirilishi kerak — bugungi pul unga ketmaydi"
    (vendor,) = [row for row in result.plan.vendors if row.vendor_id == recon.vendor_id]
    assert vendor.new_credit_soum == _PATTA

    # Bugungi patta (kechasi `billing_close` yozadi) bugungi pul bilan yopiladi.
    _charge(sync_owner_conn, recon, today, stall=1)
    async with tenant_session(recon.market_id) as session:
        allocation = await vendor_charge_allocation(
            session, market_id=recon.market_id, vendor_id=recon.vendor_id
        )
    (today_row,) = [row for row in allocation.rows if row.service_date == today]
    assert today_row.settled, "bugungi to'lov bugungi pattani yopishi kerak edi"
    assert allocation.unpaid_soum == 0


async def test_an_old_advance_is_left_untouched(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, recon, today - timedelta(days=3))
    _charge(sync_owner_conn, recon, today - timedelta(days=2))
    _pay(sync_owner_conn, recon, today, amount=50_000, days_ago=3)

    result = await _settle(tenant_session, recon, today)

    assert result.adjustments_written == 0
    (vendor,) = [row for row in result.plan.vendors if row.vendor_id == recon.vendor_id]
    assert vendor.advance_soum == 20_000
    outstanding = await _outstanding(tenant_session, recon.market_id, as_of=today)
    assert outstanding[recon.vendor_id] == -20_000, "avans oldinga o'tishi kerak"


async def test_a_reversal_today_of_an_old_payment_belongs_to_the_old_period(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, recon, today - timedelta(days=4))
    _charge(sync_owner_conn, recon, today - timedelta(days=3))
    old_payment = _pay(sync_owner_conn, recon, today, amount=30_000, days_ago=4)
    _pay(sync_owner_conn, recon, today, amount=30_000, reverses=old_payment)  # bugun bekor
    _pay(sync_owner_conn, recon, today, amount=_PATTA)  # bugungi patta

    result = await _settle(tenant_session, recon, today)

    assert result.plan.waived_soum == 30_000, "bekor qilingan eski pul eski qarzni yopmaydi"
    (vendor,) = [row for row in result.plan.vendors if row.vendor_id == recon.vendor_id]
    assert (vendor.old_credit_soum, vendor.new_credit_soum) == (0, _PATTA), (
        "storno ASL to'lovning kuniga tegishli — bugungi pattadan ayrilmaydi"
    )


# ===========================================================================
# 4. CHEGARA KUNI VA KEYINI TEGILMAYDI; BOSHQA BOZOR TEGILMAYDI
# ===========================================================================


async def test_the_boundary_day_is_not_settled(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, recon, today - timedelta(days=1))
    todays = _charge(sync_owner_conn, recon, today, stall=1)
    todays_case = seed_case(
        sync_owner_conn, market_id=recon.market_id, service_date=today, charge_id=todays
    )

    await _settle(tenant_session, recon, today)

    assert todays not in {row[0] for row in _adjustments(sync_owner_conn, recon.market_id)}
    assert _case_status(sync_owner_conn, todays_case)[0] == _NEW
    outstanding = await _outstanding(tenant_session, recon.market_id)
    assert outstanding[recon.vendor_id] == _PATTA, "bugungi patta to'lanmagan bo'lib qoladi"


async def test_the_other_market_is_untouched(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    other = recon.billing.market_b
    other_charge, _ = add_daily_charge(
        sync_owner_conn,
        market_id=other.market_id,
        stall_id=recon.domain.market_b.stall_ids[0],
        vendor_id=other.vendor_id,
        tariff_id=other.tariff_id,
        amount_soum=_PATTA,
        service_date=today - timedelta(days=3),
    )
    other_case = seed_case(
        sync_owner_conn,
        market_id=other.market_id,
        service_date=today - timedelta(days=3),
        charge_id=other_charge,
    )
    _charge(sync_owner_conn, recon, today - timedelta(days=3))

    await _settle(tenant_session, recon, today)

    assert _adjustments(sync_owner_conn, other.market_id) == []
    assert _case_status(sync_owner_conn, other_case)[0] == _NEW
    outstanding = await _outstanding(tenant_session, other.market_id)
    assert outstanding[other.vendor_id] == _PATTA


# ===========================================================================
# 5. ISHLAR — «ASOSSIZ», IZOH, TARIX, DIREKTOR
# ===========================================================================


async def test_pending_cases_before_the_boundary_are_closed_with_history(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    unpaid_day = today - timedelta(days=4)
    unpaid_case = seed_case(
        sync_owner_conn,
        market_id=recon.market_id,
        service_date=unpaid_day,
        charge_id=_charge(sync_owner_conn, recon, unpaid_day),
    )
    review_day = today - timedelta(days=3)
    review_case = seed_case(
        sync_owner_conn,
        market_id=recon.market_id,
        service_date=review_day,
        charge_id=_charge(sync_owner_conn, recon, review_day),
        status=_IN_REVIEW,
    )
    anomaly_day = today - timedelta(days=2)
    anomaly_case = seed_case(
        sync_owner_conn,
        market_id=recon.market_id,
        service_date=anomaly_day,
        anomaly_id=seed_no_coverage_anomaly(
            sync_owner_conn,
            market_id=recon.market_id,
            stall_id=recon.stall_ids[1],
            service_date=anomaly_day,
        ),
    )
    closed_day = today - timedelta(days=5)
    closed_case = seed_case(
        sync_owner_conn,
        market_id=recon.market_id,
        service_date=closed_day,
        charge_id=_charge(sync_owner_conn, recon, closed_day),
        status=_JUSTIFIED,
        resolution_note="nazoratchi qarori",
    )

    result = await _settle(tenant_session, recon, today)

    assert result.cases_closed == 3
    unpaid_note = settlement_note(today, ReconciliationSubjectKind.OCCUPIED_UNPAID.value)
    anomaly_note = settlement_note(today, ReconciliationSubjectKind.ANOMALY.value)
    assert today.strftime("%d.%m.%Y") in unpaid_note
    for case_id, from_status, note in (
        (unpaid_case, _NEW, unpaid_note),
        (review_case, _IN_REVIEW, unpaid_note),
        (anomaly_case, _NEW, anomaly_note),
    ):
        assert _case_status(sync_owner_conn, case_id) == (
            SETTLEMENT_CASE_STATUS,
            note,
            recon.director_id,
        )
        assert _events(sync_owner_conn, case_id) == [
            (from_status, SETTLEMENT_CASE_STATUS, recon.director_id, note)
        ], "har o'tish AYNAN bitta tarix qatori yozadi"

    assert _case_status(sync_owner_conn, closed_case)[:2] == (_JUSTIFIED, "nazoratchi qarori")
    assert _events(sync_owner_conn, closed_case) == [], "yopilgan ishga tegilmaydi"


async def test_recon_open_opens_nothing_for_the_settled_period(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    for n in (5, 4, 3):
        _charge(sync_owner_conn, recon, today - timedelta(days=n))
    cutoff = overdue_cutoff(today, 3)

    async with tenant_session(recon.market_id) as session:
        opened = await open_cases(
            session, market_id=recon.market_id, business_date=today, cutoff=cutoff
        )
    assert opened.unpaid_cases == 3, "sanity: kechirishdan oldin ishlar ochiladi"

    result = await _settle(tenant_session, recon, today)
    assert result.cases_closed == 3

    async with tenant_session(recon.market_id) as session:
        again = await open_cases(
            session, market_id=recon.market_id, business_date=today, cutoff=cutoff
        )
    assert (again.unpaid_cases, again.anomaly_cases) == (0, 0)
    async with tenant_session(recon.market_id) as session:
        plan = await plan_market_settlement(session, market_id=recon.market_id, before=today)
    assert plan.is_empty


# ===========================================================================
# 6. KONVERGENTLIK VA QURUQ YUGURISH (skriptning o'z yo'li)
# ===========================================================================


async def test_a_second_run_writes_nothing(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    today = _today(sync_owner_conn)
    _charge(sync_owner_conn, recon, today - timedelta(days=2))

    first = await _settle(tenant_session, recon, today)
    second = await _settle(tenant_session, recon, today)

    assert (first.adjustments_written, second.adjustments_written) == (1, 0)
    assert second.cases_closed == 0
    assert len(_adjustments(sync_owner_conn, recon.market_id)) == 1


async def test_the_script_dry_run_saves_nothing_and_apply_saves(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    recon: Env,
    capsys: pytest.CaptureFixture[str],
) -> None:
    today = _today(sync_owner_conn)
    day = today - timedelta(days=4)
    case_id = seed_case(
        sync_owner_conn,
        market_id=recon.market_id,
        service_date=day,
        charge_id=_charge(sync_owner_conn, recon, day),
    )
    script = _load_script()

    dry = await script._settle_one(
        app_sessionmaker, market_id=recon.market_id, before=today, phone=None, apply=False
    )
    assert (dry.adjustments_written, dry.cases_closed) == (1, 1), "hisobot yozish natijasi"
    assert _adjustments(sync_owner_conn, recon.market_id) == []
    assert _case_status(sync_owner_conn, case_id)[0] == _NEW
    assert "hech narsa saqlanmadi" in capsys.readouterr().out

    applied = await script._settle_one(
        app_sessionmaker, market_id=recon.market_id, before=today, phone=None, apply=True
    )
    assert (applied.adjustments_written, applied.cases_closed) == (1, 1)
    assert len(_adjustments(sync_owner_conn, recon.market_id)) == 1
    assert _case_status(sync_owner_conn, case_id)[0] == SETTLEMENT_CASE_STATUS
    assert "SAQLANDI" in capsys.readouterr().out


async def test_an_already_negative_charge_stops_the_market_with_a_clear_error(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """Hisobdan katta `decrease` (xom SQL bilan yozilgan) — taxmin emas, to'xtash."""
    today = _today(sync_owner_conn)
    charge_id = _charge(sync_owner_conn, recon, today - timedelta(days=2))
    sync_owner_conn.execute(_SET_MARKET, (str(recon.market_id),))
    try:
        sync_owner_conn.execute(
            "INSERT INTO charge_adjustments "
            "(id, market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                str(uuid4()),
                str(recon.market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.TARIFF_CORRECTION.value,
                _PATTA + 5_000,
                str(recon.director_id),
            ),
        )
    finally:
        sync_owner_conn.execute(_SET_MARKET, ("",))

    with pytest.raises(SettlementInvariantError, match="manfiy"):
        await _settle(tenant_session, recon, today)
    assert len(_adjustments(sync_owner_conn, recon.market_id)) == 1, "hech narsa yozilmasligi kerak"


# ===========================================================================
# 7. QAROR EGASI — TAXMIN QILINMAYDI
# ===========================================================================


async def test_the_decision_maker_is_the_markets_director(
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    async with tenant_session(recon.market_id) as session:
        directors = await market_directors(session, market_id=recon.market_id)

    assert [director.user_id for director in directors] == [recon.director_id]
    assert pick_decision_maker(directors, None).user_id == recon.director_id
    phone = recon.base.market_a.director_phone
    assert pick_decision_maker(directors, phone).user_id == recon.director_id
    with pytest.raises(LookupError):
        pick_decision_maker(directors, "+998 97 765 43 21")


def test_two_directors_without_a_phone_are_refused() -> None:
    first = MarketUser(
        user_id=uuid4(),
        phone="+998901111111",
        full_name="A",
        roles=("director",),
        is_active=True,
        must_change_password=False,
        locale="uz-Latn",
        created_at=datetime.now(UTC),
    )
    second = replace(first, user_id=uuid4(), phone="+998902222222")
    with pytest.raises(LookupError):
        pick_decision_maker([first, second], None)
    with pytest.raises(LookupError):
        pick_decision_maker([], None)
    assert pick_decision_maker([first, second], "+998 90 222 22 22") == second
