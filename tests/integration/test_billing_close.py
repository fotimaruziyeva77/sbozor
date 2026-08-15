"""`billing_close` — KUN YOPILISHINING PUL YARMI, HAQIQIY BAZADA (06-07).

=============================================================================
⛔⛔ BU FAYLNING SHAKLINI BELGILAYDIGAN BIRINCHI FAKT: KUN O'TMISHDA BO'LISHI
    SHART, VA U SEEDNING KUNI EMAS.

`ck_daily_charges_service_date_not_in_future` (`0020`) `service_date <=
business_date` ni talab qiladi, `business_date` esa `created_at` DAN
HOSILA, ya'ni HAR DOIM «bugun». `SEED_BUSINESS_DATE` (2026-09-01) —
QADALGAN sana va u bugundan KEYIN: o'sha kunga hisob ham,
`billing_anomalies` qatori ham YOZIB BO'LMAYDI (ikkinchisida ham AYNAN
shu `CHECK` bor).

Ya'ni `billing_close(SEED_BUSINESS_DATE)` ni o'lchash «hamma yozuv
`CheckViolation` bilan yiqiladi» degan holatni o'lchagan bo'lardi —
mahsulot yo'lini emas. 06-06 shu faktni `write_charge()` uchun
`_open_past_day()` bilan hal qilgan; bu fayl uni BUTUN KUN uchun hal
qiladi: `PastDay` o'tmishdagi OCHIQ kunga kadr va hodisa yozadi, so'ng
AYNAN o'sha kun `day_close` -> `billing_close` zanjiridan o'tadi.

=============================================================================
⛔ SLOT QATORLARI `day_close` ORQALI TUG'ILADI (C-3), qo'lda `INSERT`
   TAQIQLANADI. Aynan shu qoida Pitfall 2 ni o'lchanadigan qiladi: birinchi
   test `day_close` ni ATAYIN CHAQIRMAYDI va job'ning «yashil, lekin bo'sh»
   javobini `no_slot_rows` bilan AJRATADI.

⛔ SESSIYA TENANT KONTEKSTI BILAN — job uni O'ZI o'rnatadi. Test
   `set_tenant_context()` ni oldindan qo'ymaydi: `market_is_open()` INVOKER
   va fail-closed, ya'ni kontekstsiz HAMMA KUN yopiq bo'lardi va yopiq-kun
   testi JIMGINA yashil qolardi (Pitfall 9).

⛔ SOXTA QATLAM YO'Q: `ON CONFLICT DO NOTHING`, qisman UNIQUE indeks va
   `market_is_open()` — o'lchanayotgan narsaning O'ZI.
=============================================================================
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.billing_close import BILLING_CLOSE_COMPONENT, billing_close
from app.jobs.day_close import day_close
from fixtures.billing_domain import (
    BILLING_VALID_FROM,
    NEXT_DAY_TARIFF_SOUM,
    NEXT_TARIFF_VALID_FROM,
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    add_billable_frame,
    add_zone_with_event_on,
    billing_domain_before_day_close,
)
from fixtures.market_domain import A_OPEN_WEEKDAYS, MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import OccupancyDomainSeed, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    ActorKind,
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    OccupancyVerdict,
    ReviewPurpose,
    ReviewQueueKind,
)
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_SLOT_A = DEFAULT_SNAPSHOT_SLOTS[0]
_SLOT_B = DEFAULT_SNAPSHOT_SLOTS[1]

_INSERT_ASSIGNMENT = (
    "INSERT INTO review_assignments "
    "(id, market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)
_INSERT_REVIEW = (
    "INSERT INTO zone_reviews "
    "(id, market_id, review_assignment_id, queue_kind, shown_ai_verdict, "
    " human_verdict, reviewer_id, decision_ms) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_CALENDAR_EXCEPTION = (
    "INSERT INTO market_calendar_exceptions (id, market_id, exception_date, is_open, note) "
    "VALUES (%s, %s, %s, %s, %s)"
)
SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — FAQAT `audit_log` ni O'QISH uchun.

`audit_read` policy'si tenant-scoped va u jadval EGASIGA ham qo'llanadi
(`FORCE`). Kontekstsiz sanoq 0 bo'lardi va audit da'vosi BO'SH ROST bo'lib
qolardi (`test_billing_immutable.py:89-96` da o'lchangan tuzoq).

⚠ QOLGAN so'rovlarga QO'YILMAYDI va o'qishdan keyin BO'SHATILADI: job
  o'z kontekstini O'ZI o'rnatadi va testning sessiya darajasidagi
  qiymati mahsulot yo'lini niqoblab qo'yardi (Pitfall 9).
"""
"""Nusxa ONGLI — `test_billing_repo.py:106-124` da o'rnatilgan qoida: ikki
SQL satri jadval strukturasi bilan birga o'zgaradi va u sxema darvozasi
(`test_billing_domain_meta.py`) bilan ALLAQACHON qo'riqlangan. Ularni
umumiy fixture'ga chiqarish qo'shni faylning darvozasini bu faylning
ehtiyojiga bog'lardi.
"""


# ===========================================================================
# MUHIT
# ===========================================================================


class Env:
    """Besh qatlamli seed — `test_billing_repo.Env` shakli."""

    def __init__(
        self,
        billing: BillingDomainSeed,
        domain: MarketDomainSeed,
        base: TwoMarketSeed,
        occupancy: OccupancyDomainSeed,
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base
        self.occupancy = occupancy

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — to'liq holat qamrovi."""
        return self.billing.market_a

    @property
    def market_id(self) -> UUID:
        return self.live.market_id

    @property
    def other_market_id(self) -> UUID:
        return self.billing.market_b.market_id

    @property
    def reviewer_id(self) -> UUID:
        return self.base.market_a.admin_user_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id: UUID | None = getattr(self.live, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id

    @property
    def never_assigned_stall(self) -> UUID:
        """⛔ D-28 NING YAGONA IFODALANADIGAN HOLATI O'TMISHDAGI KUNDA.

        Seedning `stall_occupied_without_assignment` i biriktirish
        BO'SHLIG'INI `[SEED_BUSINESS_DATE, +7)` oralig'iga qo'yadi, ya'ni
        u KELAJAKDA. O'tmishdagi kunda o'sha rasta BIRIKTIRILGAN.

        `market_domain` esa `unassigned_stall_id` ga BIRORTA biriktirish
        yozmaydi (`market_domain.py:486-487`) — ya'ni u HAR QANDAY kunda
        sotuvchisiz va aynan shu holat D-28 ning kirishi.
        """
        stall_id = self.domain.market_a.unassigned_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da biriktirilmagan rasta yo'q"
        return stall_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI.

    ⚠ `billing_domain` (async) varianti ATAYIN ISHLATILMAYDI: u
      `SEED_BUSINESS_DATE` uchun `day_close` yugurtiradi, bu fayl esa
      O'TMISHDAGI kun bilan ishlaydi (modul docstringining birinchi bandi)
      — ya'ni o'sha ikki yugurish har testga narx qo'shib, birorta da'voga
      xizmat qilmasdi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets, occupancy)


# ===========================================================================
# O'TMISHDAGI KUN — TESTDA TUG'ILGAN QATORLARNING EGASI
# ===========================================================================


def _open_past_days(conn: Connection[TupleRow], count: int) -> list[date]:
    """O'tmishdagi eng yaqin `count` ta OCHIQ kun (A bozorining jadvali bo'yicha).

    =========================================================================
    ⛔ `CURRENT_DATE - 1` YETARLI EMAS: A bozori DUSHANBA yopiq
       (`A_OPEN_WEEKDAYS`), ya'ni testni «kecha» ga qadash uni HAFTA KUNIGA
       bog'lardi va seshanba kuni yugurganda nosozlik KODDA emas,
       KALENDARDA bo'lardi (`test_billing_repo.py::_open_past_day` da
       o'lchangan flaky sinf).

    ⚠ NAZORAT ASSERTI BILAN: kun `BILLING_VALID_FROM` dan OLDIN tushsa
      tarif ham, toifa davri ham hali mavjud emas va butun fayl «tarif
      yo'q» shoxini o'lchagan bo'lardi.
    """
    row = conn.execute("SELECT CURRENT_DATE - 1").fetchone()
    assert row is not None
    day: date = row[0]

    days: list[date] = []
    while len(days) < count:
        if day.isoweekday() in A_OPEN_WEEKDAYS:
            days.append(day)
        day -= timedelta(days=1)

    assert min(days) >= BILLING_VALID_FROM, (
        f"tanlangan kunlar {min(days)} tarif zanjiridan ({BILLING_VALID_FROM}) OLDIN — "
        "seed bu kunda hali narxga ega emas va fayl boshqa shoxni o'lchagan bo'lardi"
    )
    return days


def expected_tariff(day: date) -> int:
    """Shu kundagi seed tarifi — LITERAL EMAS, ZANJIRDAN HOSILA (D-09).

    Seed ikki qatorli tarif zanjiri yozadi (`TARIFF_SOUM` @
    `BILLING_VALID_FROM`, `NEXT_DAY_TARIFF_SOUM` @ `NEXT_TARIFF_VALID_FROM`).
    Test qadalgan sonni yozsa u kalendar `NEXT_TARIFF_VALID_FROM` dan
    o'tgan kuni JIMGINA noto'g'ri bo'lardi.
    """
    return TARIFF_SOUM if day < NEXT_TARIFF_VALID_FROM else NEXT_DAY_TARIFF_SOUM


class PastDay:
    """O'TMISHDAGI kunning kadr/hodisa qatlami — VA ULARNING EGASI.

    =========================================================================
    ⛔ NEGA ALOHIDA EGA KERAK (`test_billing_repo.LateReview` ning sababi):
       `cleanup_billing_domain()` `occupancy_events`, `snapshots` va
       `capture_runs` ni O'Z ID'lari bo'yicha o'chiradi va bu yerda
       tug'ilgan qatorlarni BILMAYDI. Tozalanmasa u FK buzilishi bilan
       yiqilardi va nosozlik SEEDDA ko'rinardi, holbuki u TESTNIKI.

    ⛔ TOZALASH BILLING QATORLARIDAN BOSHLANADI va bu TARTIB masalasi:
       `charge_evidence`, `billing_anomalies` va `stall_slot_occupancy`
       shu yerda tug'ilgan hodisalarga TAYANADI. pytest fixture'larni
       teskari tartibda yopadi, ya'ni bu tozalash seed'nikidan OLDIN
       yuguradi — o'sha qatorlarni seed'ga qoldirish FK xatosi berardi.
    =========================================================================
    """

    __slots__ = ("_conn", "_events", "_exceptions", "_market_id", "_reviews", "_rows", "_zones")

    def __init__(self, conn: Connection[TupleRow], market_ids: tuple[UUID, ...]) -> None:
        self._conn = conn
        self._market_id = market_ids
        self._rows: list[tuple[str, UUID]] = []
        self._events: list[UUID] = []
        self._zones: list[UUID] = []
        self._reviews: list[UUID] = []
        self._exceptions: list[UUID] = []

    def frame(
        self, *, market_id: UUID, camera_id: UUID, slot: Any, day: date, is_market_open: bool = True
    ) -> UUID:
        """Kadr — `capture_runs` + YAROQLI `snapshots`. Qaytaradi `snapshot_id`."""
        nvr_id = _nvr_of(self._conn, market_id)
        run_id, snapshot_id = add_billable_frame(
            self._conn,
            market_id=market_id,
            nvr_id=nvr_id,
            camera_id=camera_id,
            slot=slot,
            day=day,
            is_market_open=is_market_open,
        )
        self._rows.append(("snapshots", snapshot_id))
        self._rows.append(("capture_runs", run_id))
        return snapshot_id

    def occupied(
        self,
        *,
        market_id: UUID,
        camera_id: UUID,
        stall_id: UUID,
        snapshot_id: UUID,
        day: date,
        slot: Any,
        center: tuple[float, float],
        version: int,
    ) -> UUID:
        """Zona + AI «band» hodisasi. Qaytaradi `occupancy_event_id`.

        ⚠ `version` HAR CHAQIRUVDA BOSHQA: seedda o'sha (kamera, rasta)
          juftligiga zona ALLAQACHON bo'lishi mumkin
          (`uq_camera_zones_market_id_camera_id_stall_id_version`).
        """
        zone_id, event_id = add_zone_with_event_on(
            self._conn,
            market_id=market_id,
            camera_id=camera_id,
            stall_id=stall_id,
            snapshot_id=snapshot_id,
            business_date=day,
            slot=slot,
            center=center,
            version=version,
        )
        self._zones.append(zone_id)
        self._events.append(event_id)
        return event_id

    def answer(self, *, market_id: UUID, event_id: UUID, human_verdict: str) -> None:
        """Nazoratchining javobi — NOANIQ navbat topshirig'i + `zone_reviews`."""
        assignment_id = uuid4()
        self._conn.execute(
            _INSERT_ASSIGNMENT,
            (
                str(assignment_id),
                str(market_id),
                str(event_id),
                None,
                ReviewQueueKind.UNCERTAIN.value,
                ReviewPurpose.TRAIN.value,
            ),
        )
        self._conn.execute(
            _INSERT_REVIEW,
            (
                str(uuid4()),
                str(market_id),
                str(assignment_id),
                ReviewQueueKind.UNCERTAIN.value,
                True,
                human_verdict,
                str(_reviewer_of(self._conn, market_id)),
                1500,
            ),
        )
        self._reviews.append(assignment_id)

    def close_day(self, *, market_id: UUID, day: date) -> None:
        """Kalendar istisnosi — shu kunni AYNAN shu bozor uchun yopiq qiladi (D-10)."""
        exception_id = uuid4()
        self._conn.execute(
            _INSERT_CALENDAR_EXCEPTION,
            (str(exception_id), str(market_id), day, False, "billing_close testi — yopiq kun"),
        )
        self._exceptions.append(exception_id)

    def cleanup(self) -> None:
        """Billing hosilalari -> javoblar -> hodisalar -> zonalar -> kadrlar."""
        markets = [str(market_id) for market_id in self._market_id]
        self._conn.execute(
            "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])", (markets,)
        )
        for table in (
            "charge_evidence",
            "charge_adjustments",
            "billing_anomalies",
            "daily_charges",
            "stall_slot_occupancy",
        ):
            self._conn.execute(
                f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
                (markets,),
            )

        if self._reviews:
            ids = [str(value) for value in self._reviews]
            self._conn.execute(
                "DELETE FROM zone_reviews WHERE review_assignment_id = ANY(%s::uuid[])", (ids,)
            )
            self._conn.execute("DELETE FROM review_assignments WHERE id = ANY(%s::uuid[])", (ids,))
        if self._events:
            self._conn.execute(
                "DELETE FROM occupancy_events WHERE id = ANY(%s::uuid[])",
                ([str(value) for value in self._events],),
            )
        if self._zones:
            self._conn.execute(
                "DELETE FROM camera_zones WHERE id = ANY(%s::uuid[])",
                ([str(value) for value in self._zones],),
            )
        for table, row_id in self._rows:
            self._conn.execute(
                f"DELETE FROM {table} WHERE id = %s",  # noqa: S608
                (str(row_id),),
            )
        if self._exceptions:
            self._conn.execute(
                "DELETE FROM market_calendar_exceptions WHERE id = ANY(%s::uuid[])",
                ([str(value) for value in self._exceptions],),
            )


def _nvr_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Bozorning NVR'i — `capture_runs` DAN (`billing_domain._nvr_of` qoidasi)."""
    row = conn.execute(
        "SELECT nvr_id FROM capture_runs WHERE market_id = %s ORDER BY nvr_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, f"{market_id} da `capture_runs` qatori yo'q"
    nvr_id: UUID = row[0]
    return nvr_id


def _reviewer_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """`zone_reviews.reviewer_id` — bozorning admin foydalanuvchisi."""
    row = conn.execute(
        "SELECT user_id FROM user_market_roles "
        "WHERE market_id = %s AND 'market_admin' = ANY(roles) "
        "ORDER BY user_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, f"{market_id} da `market_admin` rolli foydalanuvchi yo'q"
    reviewer_id: UUID = row[0]
    return reviewer_id


class Scenario:
    """O'tmishdagi kunning TO'LIQ holat qamrovi — nomma-nom.

    =========================================================================
    OLTI RASTA, OLTI BOSHQA JAVOB (A bozori):

      `billable_ai`      2 slotda AI «band»           -> HISOB, nazoratchisiz
      `billable_human`   1 slotda «band» + inson      -> HISOB, tasdiqlangan
      `one_slot`         1 slotda AI «band»           -> hisob YO'Q (D-04)
      `unassigned`       2 slotda «band», sotuvchisiz -> ANOMALIYA (D-28)
      qolgan ikkitasi    hodisasiz                    -> ANOMALIYA (D-05)

    ⛔ `billable_human` NING BORLIGI D-14 NING DA'VOSINI TRIVIAL BO'LMAGAN
       QILADI: usiz `resolved_without_reviewer == charged` bo'lardi va
       sanoq HECH NIMANI ajratmasdi.

    ⚠ B BOZORIGA HAM KADR YOZILADI (hodisasiz): `no_slot_rows` — BUTUN
      YUGURISHNING sanog'i, ya'ni B materializatsiya qilinmasa u
      `day_close` dan KEYIN ham nolga tushmasdi va Pitfall 2 ning
      da'vosini o'lchab bo'lmasdi.
    =========================================================================
    """

    __slots__ = ("billable_ai", "billable_human", "day", "events_ai", "one_slot", "unassigned")

    def __init__(self, env: Env, past: PastDay, day: date) -> None:
        self.day = day
        self.billable_ai = env.stall("stall_with_two_occupied_slots")
        self.billable_human = env.stall("stall_with_one_human_confirmed_occupied_slot")
        self.one_slot = env.stall("stall_with_one_ai_occupied_slot")
        self.unassigned = env.never_assigned_stall

        market_id = env.market_id
        camera_a = env.occupancy.market_a.camera_id
        camera_b = env.occupancy.market_a.second_camera_id
        assert camera_b is not None, "nazorat: A bozorining ikkinchi kamerasi yo'q"

        snap_a = past.frame(market_id=market_id, camera_id=camera_a, slot=_SLOT_A, day=day)
        snap_b = past.frame(market_id=market_id, camera_id=camera_b, slot=_SLOT_B, day=day)

        self.events_ai = (
            past.occupied(
                market_id=market_id,
                camera_id=camera_a,
                stall_id=self.billable_ai,
                snapshot_id=snap_a,
                day=day,
                slot=_SLOT_A,
                center=(0.20, 0.20),
                version=11,
            ),
            past.occupied(
                market_id=market_id,
                camera_id=camera_b,
                stall_id=self.billable_ai,
                snapshot_id=snap_b,
                day=day,
                slot=_SLOT_B,
                center=(0.25, 0.25),
                version=12,
            ),
        )

        human_event = past.occupied(
            market_id=market_id,
            camera_id=camera_a,
            stall_id=self.billable_human,
            snapshot_id=snap_a,
            day=day,
            slot=_SLOT_A,
            center=(0.30, 0.30),
            version=13,
        )
        past.answer(
            market_id=market_id,
            event_id=human_event,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
        )

        past.occupied(
            market_id=market_id,
            camera_id=camera_a,
            stall_id=self.one_slot,
            snapshot_id=snap_a,
            day=day,
            slot=_SLOT_A,
            center=(0.40, 0.40),
            version=14,
        )

        for camera_id, snapshot_id, slot, center, version in (
            (camera_a, snap_a, _SLOT_A, (0.55, 0.55), 15),
            (camera_b, snap_b, _SLOT_B, (0.60, 0.60), 16),
        ):
            past.occupied(
                market_id=market_id,
                camera_id=camera_id,
                stall_id=self.unassigned,
                snapshot_id=snapshot_id,
                day=day,
                slot=slot,
                center=center,
                version=version,
            )

        # B bozori — KADR BOR, HODISA YO'Q (sinf docstringidagi ⚠).
        past.frame(
            market_id=env.other_market_id,
            camera_id=env.occupancy.market_b.camera_id,
            slot=_SLOT_A,
            day=day,
        )


@pytest.fixture
def past(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[PastDay]:
    """⚠ `env` GA BOG'LANGAN va bu TARTIB uchun: pytest fixture'larni teskari
    tartibda yopadi, ya'ni bu tozalash billing seedinikidan OLDIN yuguradi.
    """
    owner = PastDay(sync_owner_conn, (env.market_id, env.other_market_id))
    try:
        yield owner
    finally:
        owner.cleanup()


@pytest.fixture
def scenario(sync_owner_conn: Connection[TupleRow], env: Env, past: PastDay) -> Scenario:
    """O'tmishdagi kunning to'liq holat qamrovi (`Scenario` docstringi)."""
    return Scenario(env, past, _open_past_days(sync_owner_conn, 1)[0])


# ===========================================================================
# BAZADAN O'QIYDIGAN YORDAMCHILAR
# ===========================================================================


def charges(conn: Connection[TupleRow], market_id: UUID, day: date) -> dict[UUID, tuple[Any, ...]]:
    """`{stall_id: (amount_soum, tariff_amount_soum, created_at)}`."""
    rows = conn.execute(
        "SELECT stall_id, amount_soum, tariff_amount_soum, created_at FROM daily_charges "
        "WHERE market_id = %s AND service_date = %s",
        (str(market_id), day),
    ).fetchall()
    return {row[0]: (row[1], row[2], row[3]) for row in rows}


def anomalies(conn: Connection[TupleRow], market_id: UUID, day: date) -> list[tuple[Any, ...]]:
    """`(stall_id, kind, occupancy_event_id, snapshot_id)` — kun kesimida."""
    rows = conn.execute(
        "SELECT stall_id, kind, occupancy_event_id, snapshot_id FROM billing_anomalies "
        "WHERE market_id = %s AND service_date = %s ORDER BY kind, stall_id",
        (str(market_id), day),
    ).fetchall()
    return [tuple(row) for row in rows]


def adjustments(conn: Connection[TupleRow], market_id: UUID) -> list[tuple[Any, ...]]:
    """`(charge_id, direction, reason_code, amount_soum, actor_user_id)`."""
    rows = conn.execute(
        "SELECT charge_id, direction, reason_code, amount_soum, actor_user_id "
        "FROM charge_adjustments WHERE market_id = %s ORDER BY reason_code",
        (str(market_id),),
    ).fetchall()
    return [tuple(row) for row in rows]


# ===========================================================================
# 1. ⛔ PITFALL 2 — «YASHIL, LEKIN BO'SH» HOLATI «ISHLADI» DAN AJRALADI
# ===========================================================================


async def test_a_run_before_day_close_reports_no_slot_rows_instead_of_silence(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """⛔ BU FAYLNING ENG QIMMAT TESTI — C-3 NING BUTUN MAZMUNI.

    =========================================================================
    IKKI HOLAT MEXANIK RAVISHDA AJRALISHI SHART:

      (1) `day_close` HALI yugurmagan  -> `charged == 0` VA `no_slot_rows > 0`
      (2) `day_close` yugurgan         -> `charged > 0`  VA `no_slot_rows == 0`

    Ikkalasida ham `errors` BO'SH. Agar (1) da `no_slot_rows` ham 0
    bo'lganda edi, «job ishladi va hech kim band emas» bilan «biz umuman
    ko'rmadik» BIR XIL javob berardi — va aynan shu holat 20:30 dagi cron
    bilan HAR KUNI takrorlanardi (D-13 ning o'lchangan oqibati).

    ⚠ (1) DAGI SON NAZORAT BILAN: `no_slot_rows` ikkala bozorning FAOL
      rastalari soniga TENG bo'lishi kerak, «noldan katta» emas — aks
      holda bitta rastani sanagan xato ham yashil qolardi.
    =========================================================================
    """
    active = _active_stall_count(sync_owner_conn, (env.market_id, env.other_market_id))

    before = await billing_close(app_sessionmaker, business_date=scenario.day)

    assert before.charged == 0, "materializatsiyasiz hisob yozildi"
    assert before.no_slot_rows == active, (
        f"«ko'rmadik» sanog'i {before.no_slot_rows}, faol rastalar {active} — "
        "sukunat «hammasi joyida» dan AJRALMADI (Pitfall 2)"
    )
    assert before.errors == [], f"kutilmagan xato: {before.errors}"
    assert charges(sync_owner_conn, env.market_id, scenario.day) == {}

    await day_close(app_sessionmaker, business_date=scenario.day)
    after = await billing_close(app_sessionmaker, business_date=scenario.day)

    assert after.charged > 0, "materializatsiyadan keyin ham hisob yozilmadi"
    assert after.no_slot_rows == 0, (
        f"materializatsiyadan keyin ham {after.no_slot_rows} rasta «ko'rilmagan» — "
        "maxraj `day_close` ning to'plamidan AJRALIB KETGAN"
    )
    assert after.errors == [], f"kutilmagan xato: {after.errors}"


def _active_stall_count(conn: Connection[TupleRow], market_ids: tuple[UUID, ...]) -> int:
    """Ikkala bozorning `active` rastalari — `_ACTIVE_STALL_IDS` ning jufti."""
    row = conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = ANY(%s::uuid[]) AND status = 'active'",
        ([str(market_id) for market_id in market_ids],),
    ).fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# 2. D-06 — QAYTA YUGURISH YOZILGAN HISOBGA TEGMAYDI
# ===========================================================================


async def test_a_second_run_touches_nothing(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """Ikki marta yugurish -> qator soni ham, summa ham, `created_at` ham O'ZGARMAYDI.

    ⛔ `created_at` HAM SOLISHTIRILADI: `ON CONFLICT DO UPDATE` shakli
       summani o'zgartirmasdan ham qatorni QAYTA YOZARDI va faqat summa
       tekshirilganda test buni SEZMASDI (`06-PATTERNS.md` Gotcha 1).
    """
    await day_close(app_sessionmaker, business_date=scenario.day)
    first = await billing_close(app_sessionmaker, business_date=scenario.day)
    snapshot_before = charges(sync_owner_conn, env.market_id, scenario.day)

    second = await billing_close(app_sessionmaker, business_date=scenario.day)
    snapshot_after = charges(sync_owner_conn, env.market_id, scenario.day)

    assert first.charged > 0, "birinchi yugurish hech nima yozmadi — nazorat buzildi"
    assert second.charged == 0, f"qayta yugurish {second.charged} yangi hisob yozdi"
    assert second.skipped_existing == first.charged, (
        f"«allaqachon bor» sanog'i {second.skipped_existing}, kutilgani {first.charged}"
    )
    assert snapshot_after == snapshot_before, "qayta yugurish yozilgan hisobga TEGDI (D-06/D-07)"


# ===========================================================================
# 3. D-10 — YOPIQ KUNDA HISOB YO'Q, HODISA ESA YO'QOLMAYDI
# ===========================================================================


async def test_a_closed_day_writes_anomalies_and_no_charges(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
    past: PastDay,
) -> None:
    """Yopiq kunda savdo ko'rindi -> `closed_day_occupied`, `daily_charges` BO'SH.

    ⚠ KUN KALENDAR ISTISNOSI BILAN YOPILADI, HAFTA KUNI BILAN EMAS:
      dushanbaga qadash testni «qaysi qatlam yopdi?» savoliga javobsiz
      qoldirardi (`CLOSED_BUSINESS_DATE` docstringidagi qoida).
    """
    day = _open_past_days(sync_owner_conn, 1)[0]
    stall_id = env.stall("stall_with_two_occupied_slots")
    camera_id = env.occupancy.market_a.camera_id

    snapshot_id = past.frame(
        market_id=env.market_id,
        camera_id=camera_id,
        slot=_SLOT_A,
        day=day,
        is_market_open=False,
    )
    past.occupied(
        market_id=env.market_id,
        camera_id=camera_id,
        stall_id=stall_id,
        snapshot_id=snapshot_id,
        day=day,
        slot=_SLOT_A,
        center=(0.70, 0.70),
        version=21,
    )
    past.close_day(market_id=env.market_id, day=day)

    await day_close(app_sessionmaker, business_date=day)
    result = await billing_close(app_sessionmaker, business_date=day)

    closed = [
        row
        for row in anomalies(sync_owner_conn, env.market_id, day)
        if row[1] == "closed_day_occupied"
    ]
    assert charges(sync_owner_conn, env.market_id, day) == {}, "yopiq kunda hisob yozildi (D-10)"
    assert result.anomalies_closed_day > 0, "yopiq kundagi savdo JIMGINA yo'qoldi"
    assert len(closed) >= 1, "`closed_day_occupied` qatori yozilmadi"
    assert closed[0][0] == stall_id
    assert closed[0][2] is not None and closed[0][3] is not None, (
        "yopiq kun anomaliyasi DALILSIZ yozildi (D-29)"
    )


# ===========================================================================
# 4/5. D-28 va D-05 — IKKI ANOMALIYA, IKKI ALOHIDA SANOQ (C-12)
# ===========================================================================


async def test_the_three_anomaly_kinds_never_share_a_counter(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """D-28 dalil BILAN, D-05 dalil SIZ — va sanoqlar ARALASHMAYDI.

    =========================================================================
    ⛔ D-05 «BAND, LEKIN TO'LOVSIZ» EMAS. «Ko'ra olmadik» ni BILL-04 ga
       qo'shish KO'R NUQTADAN TUSHUM DA'VOSI TO'QISH bo'lardi — 0-fazadagi
       ~10 % qamrovsizlik aynan shu bayroq ostida ko'rinadi.

    ⛔ SHUNING UCHUN DA'VO IKKI TOMONLAMA: `unassigned_occupied` qatorida
       dalil BOR (D-29), `no_coverage_stall` da esa `occupancy_event_id`
       `NULL` (C-12) — va o'sha rasta `anomalies_unassigned` sanog'iga
       TUSHMAYDI.
    =========================================================================
    """
    await day_close(app_sessionmaker, business_date=scenario.day)
    result = await billing_close(app_sessionmaker, business_date=scenario.day)

    rows = anomalies(sync_owner_conn, env.market_id, scenario.day)
    unassigned = [row for row in rows if row[1] == AnomalyKind.UNASSIGNED_OCCUPIED.value]
    no_coverage = [row for row in rows if row[1] == AnomalyKind.NO_COVERAGE_STALL.value]

    assert len(unassigned) == 1, f"D-28 uchun {len(unassigned)} qator yozildi"
    assert unassigned[0][0] == scenario.unassigned
    assert unassigned[0][2] is not None, "`unassigned_occupied` DALILSIZ yozildi (D-29)"
    assert unassigned[0][3] is not None, "`unassigned_occupied` da kadr yo'q (D-29)"
    assert scenario.unassigned not in charges(sync_owner_conn, env.market_id, scenario.day), (
        "sotuvchisiz rastaga hisob yozildi (D-28)"
    )

    assert no_coverage, "qamrovsiz rasta uchun anomaliya yozilmadi (D-05)"
    assert all(row[2] is None and row[3] is None for row in no_coverage), (
        "`no_coverage_stall` DALIL bilan yozildi — «ko'ra olmadik» YOLG'ON bo'lardi (C-12)"
    )
    assert {row[0] for row in no_coverage}.isdisjoint({scenario.unassigned}), (
        "bir rasta ikkala anomaliyada ham — sanoqlar ARALASHDI"
    )
    assert result.anomalies_unassigned == len(unassigned)
    assert result.anomalies_no_coverage >= len(no_coverage)


async def test_a_second_run_does_not_recount_the_same_anomalies(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """⛔ WR-03: anomaliya sanog'i YOZUVGA ergashadi, URINISHGA emas.

    =========================================================================
    ⛔⛔ JOB KONVERGENT — «QAYTA YUGURISH NORMAL HOLAT» (D-06/D-13).

    `write_anomaly()` konfliktda `None` qaytaradi, ya'ni ikkinchi
    yugurishda YANGI qator yozilmaydi. Sanoqlar esa SHARTSIZ oshardi:

        await write_anomaly(...)
        result.anomalies_no_coverage += 1     # yozildimi — tekshirilmaydi

    Natijada bir kunning har qayta yugurishi o'sha anomaliyalarni QAYTA
    sanardi. Son `system_heartbeats.detail` ga tushadi va uni
    `/internal/self-check` bilan kunlik daydjest o'qiydi — ya'ni
    BILL-04 ning YAGONA tashqi kuzatuvi oshirib ko'rsatardi.

    `charged` bu qoidani ALLAQACHON bajarardi (`if charge_id is None:
    skipped_existing += 1`), anomaliyalar esa YO'Q — nomuvofiqlik bitta
    faylning ichida edi.

    ⛔ QATOR SONI HAM O'LCHANADI: faqat sanoqni tekshirish «ikkinchi
       yugurish anomaliyani UMUMAN yozmadi» bilan «yozdi, lekin
       sanamadi» ni AJRATMASDI (D-30).

    ⚠ NAZORAT: birinchi yugurishning sanog'i NOLDAN KATTA. Usiz «har
      doim nol» ham bu testni qanoatlantirardi.
    =========================================================================
    """
    await day_close(app_sessionmaker, business_date=scenario.day)
    first = await billing_close(app_sessionmaker, business_date=scenario.day)
    rows_before = anomalies(sync_owner_conn, env.market_id, scenario.day)

    second = await billing_close(app_sessionmaker, business_date=scenario.day)
    rows_after = anomalies(sync_owner_conn, env.market_id, scenario.day)

    assert first.anomalies_unassigned > 0, "nazorat: birinchi yugurish anomaliya sanamadi"
    assert first.anomalies_no_coverage > 0, "nazorat: qamrovsiz rasta sanog'i nol"
    assert len(rows_after) == len(rows_before), "qayta yugurish YANGI anomaliya yozdi"

    assert (
        second.anomalies_unassigned,
        second.anomalies_no_coverage,
        second.anomalies_closed_day,
    ) == (0, 0, 0), (
        "qayta yugurish YOZILMAGAN anomaliyalarni sanadi — "
        f"{second.anomalies_unassigned}/{second.anomalies_no_coverage}/"
        f"{second.anomalies_closed_day}"
    )


# ===========================================================================
# 6. D-14 — NAZORATCHISIZ HAL QILINGAN RASTALAR O'LCHANADI
# ===========================================================================


async def test_charges_without_a_reviewer_are_counted_not_hidden(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """Ikki hisob yoziladi, ulardan FAQAT BITTASI nazoratchisiz.

    ⛔ DA'VO TRIVIAL EMAS: stsenariyda inson tasdiqlagan hisob ham bor,
       ya'ni `resolved_without_reviewer == charged` bo'lsa test QIZARADI.
       Bittagina AI hisobi bilan ikkala son teng bo'lardi va sanoq hech
       nimani ajratmasdi (D-14 ning butun mazmuni — MIQDOR).
    """
    await day_close(app_sessionmaker, business_date=scenario.day)
    result = await billing_close(app_sessionmaker, business_date=scenario.day)

    written = charges(sync_owner_conn, env.market_id, scenario.day)
    assert set(written) == {scenario.billable_ai, scenario.billable_human}, (
        f"kutilgan ikki rasta o'rniga: {sorted(str(key) for key in written)}"
    )
    assert result.charged == 2
    assert result.resolved_without_reviewer == 1, (
        f"nazoratchisiz hisoblar soni {result.resolved_without_reviewer} — "
        "inson tasdiqlagan hisob ham shu sanoqqa tushgan bo'lishi mumkin"
    )
    assert result.skipped_unbilled >= 1, "«ko'rdik, lekin band emas» holati sanalmadi (D-04)"

    amount, tariff_amount, _ = written[scenario.billable_ai]
    assert amount == expected_tariff(scenario.day)
    assert tariff_amount == amount, "tarif summasi hisob summasidan ajralib ketdi (D-09)"


# ===========================================================================
# 6a. ⛔ PITFALL 5(c) — KECH KELGAN TASDIQ
# ===========================================================================


async def test_a_late_review_writes_an_adjustment_and_never_edits_the_charge(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
    past: PastDay,
) -> None:
    """Hisob O'ZGARMAYDI, kamaytirish `charge_adjustments` ga YOZILADI (D-07).

    =========================================================================
    UCH CHAQIRUV, UCH BOSHQA DA'VO:

      1. `billing_close` hisob yozadi;
      2. nazoratchi ikkala slotni «bo'sh» deb belgilaydi, `day_close`
         qayta yuguradi -> `billing_close` hisobga TEGMAYDI va bitta
         `late_review` tuzatishi yozadi;
      3. yana bir chaqiruv -> IKKINCHI tuzatish YOZILMAYDI (idempotent).

    ⛔ AUDIT QATORI DB-TRIGGERIDAN: `charge_adjustments`
       `BILLING_AUDITED_TABLES` da, ya'ni `write_app_audit()` chaqirilmaydi
       va ilova qatlamidagi ikkinchi yozuv DUBLIKAT bo'lardi.
    =========================================================================
    """
    await day_close(app_sessionmaker, business_date=scenario.day)
    await billing_close(app_sessionmaker, business_date=scenario.day)
    before = charges(sync_owner_conn, env.market_id, scenario.day)
    assert scenario.billable_ai in before, "nazorat: hisob yozilmagan"

    for event_id in scenario.events_ai:
        past.answer(
            market_id=env.market_id,
            event_id=event_id,
            human_verdict=OccupancyVerdict.EMPTY.value,
        )
    await day_close(app_sessionmaker, business_date=scenario.day)
    late = await billing_close(app_sessionmaker, business_date=scenario.day)

    after = charges(sync_owner_conn, env.market_id, scenario.day)
    written = adjustments(sync_owner_conn, env.market_id)

    assert after == before, "kech tasdiq YOZILGAN HISOBNI o'zgartirdi (D-07)"
    assert late.adjustments_late_review == 1, (
        f"kech tasdiq uchun {late.adjustments_late_review} tuzatish yozildi"
    )
    assert len(written) == 1, f"kutilgan bitta tuzatish o'rniga: {written}"
    charge_id, direction, reason_code, amount, actor = written[0]
    assert direction == AdjustmentDirection.DECREASE.value
    assert reason_code == AdjustmentReason.LATE_REVIEW.value
    assert amount == before[scenario.billable_ai][0], "tuzatish TO'LIQ summani qoplamadi"
    assert actor is None, "tizim yozgan tuzatishga ODAM biriktirildi"

    # ⚠ TENANT KONTEKSTI `audit_log` NI O'QISH UCHUN SHART: `audit_read`
    #   policy'si tenant-scoped va u jadval EGASIGA ham qo'llanadi
    #   (`FORCE`). Kontekstsiz so'rov 0 qator berardi va bu da'vo
    #   MAHSULOT nosozligiga o'xshab qizarardi
    #   (`test_billing_immutable.py::SET_MARKET` da o'lchangan tuzoq).
    sync_owner_conn.execute(SET_MARKET, (str(env.market_id),))
    try:
        audit = sync_owner_conn.execute(
            "SELECT actor_kind, actor_user_id FROM audit_log "
            "WHERE table_name = 'charge_adjustments' AND row_id = %s",
            (str(_adjustment_id_of(sync_owner_conn, charge_id)),),
        ).fetchall()
    finally:
        sync_owner_conn.execute(SET_MARKET, ("",))

    assert audit, "DB-trigger `charge_adjustments` uchun audit qatorini yozmadi"
    assert audit[0][0] == ActorKind.SYSTEM.value, (
        f"audit qatori {audit[0][0]!r} aktori bilan yozildi — tizim yozuvi ODAMGA biriktirildi"
    )
    assert audit[0][1] is None, "tizim yozuvining audit qatorida `actor_user_id` bor"

    third = await billing_close(app_sessionmaker, business_date=scenario.day)
    assert third.adjustments_late_review == 0, "uchinchi chaqiruv IKKINCHI tuzatishni yozdi"
    assert len(adjustments(sync_owner_conn, env.market_id)) == 1, (
        "idempotentlik buzildi — qisman UNIQUE indeks ishlamadi"
    )


def _adjustment_id_of(conn: Connection[TupleRow], charge_id: UUID) -> UUID:
    """Tuzatish qatorining `id` si — audit `row_id` bilan solishtirish uchun."""
    row = conn.execute(
        "SELECT id FROM charge_adjustments WHERE charge_id = %s ORDER BY created_at LIMIT 1",
        (str(charge_id),),
    ).fetchone()
    assert row is not None
    adjustment_id: UUID = row[0]
    return adjustment_id


# ===========================================================================
# 8. YURAK URISHI — YO'QLIGI KO'RINADIGAN BO'LISHINING BIRINCHI YARMI
# ===========================================================================


async def test_the_run_writes_a_heartbeat_with_counters_only(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
) -> None:
    """`system_heartbeats['billing_close']` — `detail` da FAQAT sanoqlar.

    ⛔ `system_heartbeats` GLOBAL jadval (`market_id` ustuni YO'Q), ya'ni
       unga yozilgan har qanday tenant qiymati HAMMA uchun ko'rinadigan
       joyda qolardi. Shuning uchun `detail` ning HAR qiymati butun son
       bo'lishi tekshiriladi — nom bo'yicha inkor da'vo (`"market_id" not
       in detail`) yangi maydonni JIMGINA o'tkazib yuborardi.
    """
    await billing_close(app_sessionmaker, business_date=scenario.day)

    row = sync_owner_conn.execute(
        "SELECT detail FROM system_heartbeats WHERE component = %s",
        (BILLING_CLOSE_COMPONENT,),
    ).fetchone()

    assert row is not None, "`billing_close` yurak urishini YOZMADI"
    detail: dict[str, Any] = row[0]
    assert detail, "yurak urishi BO'SH `detail` bilan yozildi"
    assert all(isinstance(value, int) for value in detail.values()), (
        f"`detail` da sanoq bo'lmagan qiymat bor: {detail}"
    )
    assert "charged" in detail and "no_slot_rows" in detail, (
        f"Pitfall 2 ning ikkala sanog'i ham `detail` da bo'lishi kerak: {sorted(detail)}"
    )


# ===========================================================================
# 9. QORALAMA -> FAOL ZANJIRI — «FAOLLASHGACH BILLING HISOB YOZADI»
# ===========================================================================


_SET_MARKET_ACTIVE = "UPDATE markets SET is_active = %s WHERE id = %s"
"""`PastDay.cleanup()` dagi AYNI chaqiruv shakli — `sbozor_owner` bilan.

Nusxa ONGLI: bu satr `markets` jadvalining bitta ustuniga tegadi va u
`0013_market_delete_guard` triggeri bilan allaqachon qo'riqlangan. Uni
umumiy fixture'ga chiqarish tozalash yo'lini test ehtiyojiga bog'lardi.
"""


async def test_a_draft_market_is_skipped_and_activation_starts_the_daily_charge(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """Qoralama bozorda hisob YO'Q; AYNI bozor faollashgach AYNI kunga hisob BOR.

    =========================================================================
    ⛔ 1. BU TEST ENDPOINTNI EMAS, OQIBATNI O'LCHAYDI.

    `POST /markets/{id}/activate` ning O'ZI allaqachon uchta MUSTAQIL da'vo
    bilan qamralgan: `test_wizard_flow.py:354-366` (draft -> active),
    `:875-885` (takror -> 409 `market_is_active`) va `:1106-1132` (audit
    yozuvi). `market_activate()` esa AYNAN shu ustunni o'zgartiradi, ya'ni
    bu yerda endpointni ikkinchi marta chaqirish reyestrning O'LCHANMAGAN
    bandini (billing zanjiri) allaqachon o'lchangan bandi bilan
    ALMASHTIRARDI.

    O'lchanmagan band aynan shu edi: №B ning qabul mezoni «faollashgach
    billing kunlik hisob yozadi» deydi, `is_active` esa bu faylda faqat
    `PastDay.cleanup()` da — tozalash uchun, DA'VO uchun emas — uchrardi.

    -------------------------------------------------------------------------
    ⛔ 2. SUKUNAT NOSOZLIKDAN AJRATILADI.

    Birinchi yarimda `charges == {}` bilan BIRGA `result.errors == []` ham
    tasdiqlanadi. Usiz yiqilgan job ham «qoralama filtri ishladi» deb
    yashil qolardi — bu faylning Pitfall 2 bandi bilan AYNI sinfdagi xato:
    «ishladi va hech nima yozilmadi» «biz umuman ko'rmadik» dan mexanik
    ravishda ajralishi shart.

    -------------------------------------------------------------------------
    ⚠ 3. O'TMISHDAGI KUN — TEST QULAYLIGI, MAHSULOT XULQI EMAS.

    Mahsulotda `BILLING_CLOSE_CRON = "10 4 * * *"` faqat KECHAGI kunni
    yopadi, ya'ni faollashtirishdan OLDINGI kunlar hech qachon yopilmaydi
    va retroaktiv hisob YO'LI umuman yo'q. Testning ikkinchi yarmi
    `retention.py:162-164` dagi `WHERE is_active` FILTRINI o'lchaydi,
    retroaktiv hisobni EMAS.

    -------------------------------------------------------------------------
    ⚠ TOZALASH QO'LDA QILINMAYDI: `PastDay.cleanup()` (`:373-376`)
      teardown'da ikkala bozorni `is_active = false` ga qaytaradi, ya'ni bu
      test o'zidan keyin holat qoldirmaydi. Ikkinchi «tiklovchi» flip
      qo'shish o'sha tozalashning ustiga yozardi va uni ortiqcha ko'rsatib
      qo'yardi.
    =========================================================================
    """
    # (1) QORALAMA — usta yakunlanmagan bozorning holati.
    sync_owner_conn.execute(_SET_MARKET_ACTIVE, (False, str(env.market_id)))

    await day_close(app_sessionmaker, business_date=scenario.day)
    draft_run = await billing_close(app_sessionmaker, business_date=scenario.day)

    assert charges(sync_owner_conn, env.market_id, scenario.day) == {}, (
        "QORALAMA bozorga kunlik hisob yozildi — `WHERE is_active` filtri ishlamadi"
    )
    assert draft_run.errors == [], (
        f"sukunat FILTRDAN emas, NOSOZLIKDAN kelib chiqdi: {draft_run.errors}"
    )

    # (2) FAOLLASHTIRISH — `market_activate()` AYNAN shu ustunni ko'taradi.
    sync_owner_conn.execute(_SET_MARKET_ACTIVE, (True, str(env.market_id)))

    await day_close(app_sessionmaker, business_date=scenario.day)
    live_run = await billing_close(app_sessionmaker, business_date=scenario.day)

    written = charges(sync_owner_conn, env.market_id, scenario.day)

    assert written, (
        "faollashtirilgan bozorga AYNI kun uchun birorta hisob yozilmadi — "
        "«faollashgach billing kunlik hisob yozadi» zanjiri UZILGAN (№B)"
    )
    assert live_run.charged > 0, (
        f"hisob qatorlari bor, lekin yugurish {live_run.charged} deb hisobot berdi"
    )
    assert live_run.errors == [], f"kutilmagan xato: {live_run.errors}"

    # NAZORAT: hisob AYNAN o'lchanayotgan kunga tegishli va tarif zanjiridan
    # hosila (D-09) — qadalgan son kalendar tarif chegarasidan o'tgan kuni
    # JIMGINA noto'g'ri bo'lardi.
    assert scenario.billable_ai in written, (
        "ikki slotda band bo'lgan rasta faollashgandan keyin ham hisobga tushmadi"
    )
    assert written[scenario.billable_ai][1] == expected_tariff(scenario.day)
