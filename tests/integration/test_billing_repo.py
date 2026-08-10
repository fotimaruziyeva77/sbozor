"""`billing_repo` — FAZANING PUL MANTIG'I HAQIQIY BAZADA (BILL-01…BILL-05).

=============================================================================
UCHTA QOIDA BU FAYLNING SHAKLINI BELGILAYDI.

  1. ⛔ HAQIQIY `postgres:18.4`, soxta qatlam YO'Q. Tekshirilayotgan
     narsaning O'ZI — SQL, `market_is_open()` funksiyasi va `ON CONFLICT`
     semantikasi; ularni almashtirgan test o'z tasavvurini o'lchagan
     bo'lardi.

  2. ⛔ SLOT QATORLARI `day_close` ORQALI TUG'ILADI (C-3). Qo'lda `INSERT`
     arzonroq bo'lardi va aynan o'sha arzonlik Pitfall 2 ni testdan
     yashirardi. Shuning uchun bandlikka tayanadigan guruhlar
     `billing_domain` (async) variantidan, qolganlari esa
     `billing_domain_before_day_close` dan yuguradi — ikkinchisi har
     testga ikki `day_close` yugurishini qo'shmaydi (06-05 da o'rnatilgan
     qoida).

  3. ⛔ SESSIYA TENANT KONTEKSTI BILAN (`tenant_session`). `market_is_open()`
     ATAYIN `SECURITY DEFINER` emas va fail-closed: kontekstsiz u HAR
     KUNNI yopiq deb qaytarardi va yopiq-kun testi JIMGINA yashil qolardi
     (Pitfall 9).
=============================================================================
⚠ SANALAR IKKI OILAGA BO'LINADI VA ULAR ARALASHTIRILMAYDI:

    SEED_BUSINESS_DATE (2026-09-01) — BANDLIK va TARIF sanasi. Qadalgan,
        chunki slot/kadr zanjiri unga bog'langan.
    CURRENT_DATE - N                 — HISOB va TO'LOV sanasi.
        `ck_daily_charges_service_date_not_in_future` ni `business_date`
        (`created_at` dan hosila, ya'ni HAR DOIM bugun) cheklaydi, ya'ni
        qadalgan kelajak sanasi `CheckViolation` bilan yiqilardi (06-05).
=============================================================================
"""

from __future__ import annotations

from dataclasses import fields
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from app.jobs.day_close import day_close
from app.repositories.billing_repo import (
    PendingStall,
    billable_stalls,
    pending_projection,
    resolve_stall_day_money,
    vendor_charge_allocation,
    vendor_outstanding,
    write_anomaly,
    write_charge,
    write_evidence,
)
from app.services.billing_errors import MARKET_CLOSED, TARIFF_MISSING
from fixtures.billing_domain import (
    CLOSED_BUSINESS_DATE,
    HIGH_CONFIDENCE,
    NEXT_DAY_TARIFF_SOUM,
    NEXT_TARIFF_VALID_FROM,
    SEED_BUSINESS_DATE,
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    add_daily_charge,
    add_payment,
    billing_domain,
    billing_domain_before_day_close,
)
from fixtures.market_domain import (
    A_OPEN_WEEKDAYS,
    A_STALL_CODES_BY_SORT,
    A_TARIFF_AMOUNTS,
    HANDOVER_DAY,
    MarketDomainSeed,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import add_zone_with_event, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.billing import ALLOCATION_RULE
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    OccupancyVerdict,
    PaymentKind,
    ResolutionSource,
    ReversalReason,
    ReviewPurpose,
    ReviewQueueKind,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from datetime import date

    from app.repositories.billing_repo import SlotEvidenceRow, StallDayMoney, StallSlotVerdict
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sbozor_core.billing import ChargeCreditAllocation
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
"""Inson javobi — `test_day_close.py:60-70` ning AYNAN shakli.

⚠ NUSXA ONGLI: `answer_event()` `test_day_close.py` ning ICHIDA yashaydi va
  fixture'ga chiqarilmagan. Uni «umumiy qilish» o'sha faylning o'z
  darvozasini bu faylning ehtiyojiga bog'lardi; ikki SQL satri esa
  jadval strukturasi bilan birga o'zgaradi va u sxema darvozasi
  (`test_billing_domain_meta.py`) bilan allaqachon qo'riqlangan.
"""


class Env:
    """Beshta qatlamli seed — `test_billing_immutable.Env` shakli."""

    def __init__(
        self, billing: BillingDomainSeed, domain: MarketDomainSeed, base: TwoMarketSeed
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base

    @property
    def reviewer_id(self) -> UUID:
        """`zone_reviews.reviewer_id` — seed AYNAN shu foydalanuvchini ishlatadi."""
        return self.base.market_a.admin_user_id

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — to'liq holat qamrovi (oltala rasta stsenariysi)."""
        return self.billing.market_a

    @property
    def other(self) -> MarketBillingRows:
        """B bozori — cross-tenant nazorati VA tarifsiz toifaning yagona egasi."""
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
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI.

    Pul yechimi (`resolve_stall_day_money`), qoldiq va taqsimlash
    bandlikka UMUMAN tegmaydi: ularning kirishi tarif zanjiri,
    biriktirishlar, kalendar va yozilgan qatorlar. Ikkinchi variantni bu
    yerda ishlatish har testga ikki `day_close` yugurishini qo'shardi.
    """
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
async def env_with_slots(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> AsyncIterator[Env]:
    """MATERIALIZATSIYA QILINGAN slotlar bilan — `day_close` MAHSULOT yo'lidan.

    ⛔ Slot qatorlarini qo'lda `INSERT` qilish TAQIQLANADI (C-3): o'shanda
       «job yugurdi, hech nima yozmadi» holati (Pitfall 2) testda UMUMAN
       ko'rinmasdi va bandlik darvozasi hech qachon haqiqiy kirish bilan
       sinalmasdi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        async with billing_domain(
            sync_owner_conn, app_sessionmaker, two_markets, market_domain, occupancy
        ) as billing:
            yield Env(billing, market_domain, two_markets)


def _one(rows: list[StallDayMoney]) -> StallDayMoney:
    """AYNAN BITTA natija — nazorat asserti bilan.

    `rows[0]` yozish testni jimgina zaiflashtirardi: filtr ishlamay qolib
    butun reyestr qaytganda ham birinchi qator «to'g'ri» bo'lishi mumkin.
    """
    assert len(rows) == 1, f"aynan bitta rasta kutilgan edi, kelgani: {len(rows)}"
    return rows[0]


# ===========================================================================
# 1. TARIXIY TARIF (D-09) — «KEYIN TAHRIRLANSA RETROAKTIV O'ZGARMAYDI»
# ===========================================================================


async def test_resolve_uses_the_tariff_valid_on_that_day(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-09: `as_of` kunidagi narx olinadi, ERTANGI narx OLINMAYDI.

    =========================================================================
    Seed tarif zanjiri ATAYIN ikki qatorli va summalar FARQLI (15 000 /
    20 000): teng bo'lganda «qaysi qator tanlandi?» savoliga javob
    beradigan yagona signal yo'qolardi.

    ⛔ `tariff_id` HAM solishtiriladi, summa yolg'iz emas: summa tasodifan
       mos kelishi mumkin, `tariff_id` esa qaysi QATOR o'qilganini AYNAN
       ko'rsatadi va aynan u hisob bilan birga saqlanadi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")

    async with tenant_session(env.market_id) as session:
        today = _one(
            await resolve_stall_day_money(
                session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_id=stall_id
            )
        )
        tomorrow = _one(
            await resolve_stall_day_money(
                session,
                market_id=env.market_id,
                as_of=NEXT_TARIFF_VALID_FROM,
                stall_id=stall_id,
            )
        )

    assert today.amount_soum == TARIFF_SOUM
    assert today.tariff_id == env.live.tariff_id
    assert today.unavailable_reason is None
    assert today.market_open is True

    assert tomorrow.amount_soum == NEXT_DAY_TARIFF_SOUM
    assert tomorrow.tariff_id == env.live.next_tariff_id, (
        "D + 1 da IKKINCHI tarif qatori kutilgan edi — `valid_from <= :as_of` "
        "sharti kelajakdagi qatorni to'sib qo'ygan bo'lishi mumkin"
    )


# ===========================================================================
# 2. SUMMA YO'Q BO'LGAN IKKI HOLAT — JUFTLANGAN INVARIANT (UI-SPEC §9.4)
# ===========================================================================


async def test_resolve_reports_a_closed_day_without_an_amount(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-10: yopiq kunda summa YO'Q va sabab NOMLANGAN.

    ⛔ Sabab `market_is_open()` DB funksiyasidan keladi — kalendar
       mantig'i bu yerda ham, `billing_repo` da ham TAKRORLANMAYDI (S-4).
       Seed kunni AYNAN kalendar istisnosi bilan yopadi (hafta kuni
       bo'yicha u OCHIQ), ya'ni test haftalik jadvalni emas, istisnoni
       o'lchaydi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")

    async with tenant_session(env.market_id) as session:
        money = _one(
            await resolve_stall_day_money(
                session,
                market_id=env.market_id,
                as_of=CLOSED_BUSINESS_DATE,
                stall_id=stall_id,
            )
        )

    assert money.market_open is False
    assert money.amount_soum is None
    assert money.unavailable_reason == MARKET_CLOSED


async def test_resolve_reports_a_missing_tariff_without_an_amount(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """Tarifsiz toifada summa TAXMIN QILINMAYDI — «yo'q summa yo'q summa».

    ⚠ HOLAT B BOZORIDAN OLINADI va bu ZARURAT, uslub emas: `market_domain`
      A bozorining HAR rastasiga toifa davri yozadi va uchala toifaning
      ham tarifi bor. B bozorida esa IKKI toifa, BITTA tarif — ikkinchi
      toifa ATAYIN tarifsiz (`market_domain.py:503`), ya'ni «tarif yo'q»
      shoxi faqat shu yerda ifodalanadi.
    """
    market_id = env.other.market_id
    stall_id = env.domain.market_b.stall_ids[1]

    async with tenant_session(market_id) as session:
        money = _one(
            await resolve_stall_day_money(
                session, market_id=market_id, as_of=SEED_BUSINESS_DATE, stall_id=stall_id
            )
        )

    assert money.market_open is True, "nazorat: B bozori bu kunda OCHIQ bo'lishi kerak"
    assert money.amount_soum is None
    assert money.unavailable_reason == TARIFF_MISSING
    assert money.tariff_id is None


# ===========================================================================
# 3. BIRIKTIRISH — BO'SHLIQ VA ALMASHINUV KUNI (D-28, OQ-5)
# ===========================================================================


async def test_resolve_returns_no_vendor_inside_an_assignment_gap(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """Bo'shliq XATO EMAS — u BILL-04/D-28 anomaliyasining MANBAI.

    ⛔ Funksiya ISTISNO KO'TARMAYDI va summani ham yo'qotmaydi: rasta
       band bo'lishi mumkin va o'sha holat aynan «ro'yxatga olinmagan
       savdo» yozuvini tug'diradi. Istisno ko'tarilsa butun kun yopilishi
       BITTA biriktirilmagan rasta tufayli yiqilardi.
    """
    stall_id = env.stall("stall_occupied_without_assignment")

    async with tenant_session(env.market_id) as session:
        money = _one(
            await resolve_stall_day_money(
                session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_id=stall_id
            )
        )

    assert money.vendor_id is None
    assert money.amount_soum == TARIFF_SOUM, (
        "summa BIRIKTIRISHGA bog'liq emas — u tarifdan keladi; ikkalasini "
        "bog'lash «sotuvchisiz rasta uchun tarif yo'q» degan YOLG'ON berardi"
    )


async def test_resolve_gives_the_handover_day_to_the_new_vendor(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """OQ-5 / D-10: almashinuv KUNI YANGI sotuvchiga tegishli (`[)`).

    =========================================================================
    ⛔ KAFOLAT SO'ROVDA EMAS, KONVENTSIYADA: `[)` chegarasi FAQAT
       `sbozor_core.periods` da yashaydi (`periods.py:19-33`) va
       `sa.period @> :as_of` uni AYNAN qayta ishlatadi. Ikkinchi
       konventsiya (`[]`) yozilganda almashinuv kunida IKKI sotuvchi
       topilardi va patta ikki marta yozilardi.

    ⚠ Bu kunda A bozori HAFTA KUNI bo'yicha yopiq (dushanba), ya'ni summa
      yo'q — test ATAYIN faqat `vendor_id` ni o'lchaydi. Ikkala da'voni
      bitta testga qo'shish «qaysi qoida qizardi?» savolini javobsiz
      qoldirardi.
    """
    handover_stall = env.domain.market_a.handover_stall_id
    assert handover_stall is not None, "nazorat: seedda almashinuv rastasi yo'q"
    old_vendor, new_vendor = env.domain.market_a.vendor_ids[0], env.domain.market_a.vendor_ids[1]

    async with tenant_session(env.market_id) as session:
        on_day = _one(
            await resolve_stall_day_money(
                session,
                market_id=env.market_id,
                as_of=HANDOVER_DAY,
                stall_id=handover_stall,
            )
        )
        day_before = _one(
            await resolve_stall_day_money(
                session,
                market_id=env.market_id,
                as_of=HANDOVER_DAY - timedelta(days=1),
                stall_id=handover_stall,
            )
        )

    assert on_day.vendor_id == new_vendor
    assert day_before.vendor_id == old_vendor


async def test_overlapping_assignments_are_structurally_impossible(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """OQ-5 ning IKKINCHI yarmi — `LIMIT 1` da `ORDER BY` NEGA KERAK EMAS.

    =========================================================================
    ⛔ SABOTAJ SHAKLI: agar bir kunda ikki biriktirish IFODALANADIGAN
       bo'lsa, `resolve_stall_day_money()` qaysi sotuvchini berishi
       ANIQLANMAGAN bo'lardi va nizoda javob DALIL QIYMATINI yo'qotardi
       (D-02). Test buni «tartib qo'shamiz» bilan emas, kafolatning O'ZINI
       o'lchash bilan yopadi: `ex_stall_assignments_no_overlap`
       (`models/market.py:619-625`) ustma-ust davrni RAD ETADI.

    ⚠ Da'vo `23P01` (`ExclusionViolation`) bilan, istisno klassining nomi
      bilan EMAS: konstrayt shaklini jimgina almashtirish (masalan oddiy
      `UNIQUE` ga) SQLSTATE ni o'zgartiradi va test qizaradi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    other_vendor = env.domain.market_a.vendor_ids[1]

    with pytest.raises(psycopg.errors.ExclusionViolation) as excinfo:
        sync_owner_conn.execute(
            "INSERT INTO stall_assignments (id, market_id, stall_id, vendor_id, period) "
            "VALUES (%s, %s, %s, %s, daterange(%s, NULL, '[)'))",
            (
                str(uuid4()),
                str(env.market_id),
                str(stall_id),
                str(other_vendor),
                SEED_BUSINESS_DATE,
            ),
        )

    assert excinfo.value.sqlstate == "23P01"


# ===========================================================================
# 4. TARTIB VA FILTR — SERVERDA (`code_sort`), PREFIKS EMAS
# ===========================================================================


async def test_resolve_orders_the_market_by_human_numeric_code(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """Tartib `stalls.code_sort` bo'yicha — KLIENTDA emas (UI-SPEC §7.3).

    Oddiy `ORDER BY code` «10, 100, 2, 3, 55, 7» berardi va kassir
    qidirayotgan rasta ko'z bilan topilmaydigan joyga tushardi. Kutilgan
    tartib seedda BIR MARTA e'lon qilingan (`A_STALL_CODES_BY_SORT`) va
    test uni QAYTA yozmaydi.
    """
    from fixtures.market_domain import A_STALL_CODES_BY_SORT

    async with tenant_session(env.market_id) as session:
        rows = await resolve_stall_day_money(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE
        )

    assert tuple(row.stall_code for row in rows) == A_STALL_CODES_BY_SORT


async def test_resolve_matches_a_stall_code_exactly_not_by_prefix(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """`stall_code` filtri ANIQ MOSLIK — prefiks semantikasi BU BO'G'INDA yo'q.

    Seedda «10» va «100» kodlari BIRGA yashaydi, ya'ni prefiks semantikasi
    «10» so'roviga IKKI qator qaytarardi va «qaysi rastaning summasi?»
    savoli javobsiz qolardi. Ko'p moslik BITTA qavat yuqorida
    (`pending_projection`) hal qilinadi.
    """
    async with tenant_session(env.market_id) as session:
        rows = await resolve_stall_day_money(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_code="10"
        )

    assert [row.stall_code for row in rows] == ["10"]


async def test_resolve_does_not_leak_another_market(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """Cross-tenant nazorati — B bozorining rastasi A kontekstida KO'RINMAYDI.

    ⚠ Bo'sh natija «rasta yo'q» degan HALOL javob: `stall_id` filtri
      mavjud, lekin RLS + `market_id` predikati qatorni bermaydi.
    """
    foreign_stall = env.domain.market_b.stall_ids[0]

    async with tenant_session(env.market_id) as session:
        rows = await resolve_stall_day_money(
            session,
            market_id=env.market_id,
            as_of=SEED_BUSINESS_DATE,
            stall_id=foreign_stall,
        )

    assert rows == []


def _service_day(conn: Connection[TupleRow], offset: int) -> date:
    """`CURRENT_DATE - offset` — hisob/to'lov sanalari uchun YAGONA manba.

    Fayl docstringidagi ikkinchi sana oilasi: `daily_charges.business_date`
    `created_at` dan hosila, ya'ni qadalgan kelajak sanasi
    `ck_daily_charges_service_date_not_in_future` ga urilardi (06-05).
    """
    row = conn.execute("SELECT CURRENT_DATE - %s::int", (offset,)).fetchone()
    assert row is not None
    day: date = row[0]
    return day


def _open_past_day(conn: Connection[TupleRow]) -> date:
    """O'TMISHDAGI eng yaqin OCHIQ kun — A bozorining haftalik jadvali bo'yicha.

    =========================================================================
    ⛔ NEGA `CURRENT_DATE - 1` YETARLI EMAS: A bozori DUSHANBA yopiq
       (`A_OPEN_WEEKDAYS`). Testni «kecha» ga qadash uni HAFTA KUNIGA
       bog'lardi va u seshanba kuni yugurganda yopiq kun tufayli
       `write_charge()` ni yiqitardi — nosozlik esa kodda emas, KALENDARDA
       bo'lardi va sabab ko'rinmasdi (flaky test sinfi).

    ⚠ A bozorining YAGONA kalendar istisnosi `CLOSED_BUSINESS_DATE`
      (kelajakda), ya'ni o'tmishdagi ochiq kun uchun hafta kuni yetarli.
    """
    day = _service_day(conn, 1)
    while day.isoweekday() not in A_OPEN_WEEKDAYS:
        day -= timedelta(days=1)
    return day


class LateReview:
    """Testda TUG'ILGAN zona/hodisa/javob qatorlarining EGASI.

    =========================================================================
    ⛔ NEGA ALOHIDA EGA KERAK: `cleanup_billing_domain()` `occupancy_events`
       va `snapshots` ni O'Z ID'lari bo'yicha o'chiradi va u testda
       qo'shilgan qatorlarni BILMAYDI. Ular tozalanmasa tozalash FK
       buzilishi bilan yiqilardi va nosozlik SEEDDA ko'rinardi, holbuki u
       TESTNIKI.

    ⚠ Bozor QORALAMAGA qaytariladi: `0018` `zone_reviews` va
      `occupancy_events` ga SHARTSIZ o'zgarmaslik qo'riqchisini qo'yadi va
      `DELETE` uchun yagona istisno — qoralama bozor
      (`cleanup_occupancy_domain()` aynan shu qadamni bajaradi).
    """

    def __init__(self, conn: Connection[TupleRow], market_id: UUID, reviewer_id: UUID) -> None:
        self._conn = conn
        self._market_id = market_id
        self._reviewer_id = reviewer_id
        self._assignments: list[UUID] = []
        self._events: list[UUID] = []
        self._zones: list[UUID] = []

    def add_occupied_zone(
        self, *, camera_id: UUID, stall_id: UUID, snapshot_id: UUID, center: tuple[float, float]
    ) -> UUID:
        """Yangi zona + AI «band» hodisasi. Qaytaradi: `occupancy_event_id`."""
        seeded = add_zone_with_event(
            self._conn,
            market_id=self._market_id,
            camera_id=camera_id,
            stall_id=stall_id,
            snapshot_id=snapshot_id,
            verdict=OccupancyVerdict.OCCUPIED.value,
            confidence=HIGH_CONFIDENCE,
            center=center,
        )
        self._zones.append(seeded.zone_id)
        self._events.append(seeded.event_id)
        return seeded.event_id

    def answer(self, *, event_id: UUID, human_verdict: str) -> None:
        """Hodisaga NOANIQ navbat topshirig'i va INSON javobini yozadi."""
        assignment_id = uuid4()
        self._conn.execute(
            _INSERT_ASSIGNMENT,
            (
                str(assignment_id),
                str(self._market_id),
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
                str(self._market_id),
                str(assignment_id),
                ReviewQueueKind.UNCERTAIN.value,
                True,
                human_verdict,
                str(self._reviewer_id),
                1500,
            ),
        )
        self._assignments.append(assignment_id)

    def cleanup(self) -> None:
        """FK tartibida: javob -> topshiriq -> hodisa -> zona."""
        self._conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(self._market_id),)
        )
        ids = [str(value) for value in self._assignments]
        if ids:
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


@pytest.fixture
def late_review(sync_owner_conn: Connection[TupleRow], env_with_slots: Env) -> Iterator[LateReview]:
    """⚠ `env_with_slots` GA BOG'LANGAN va bu TARTIB uchun: pytest fixture'larni
    TESKARI tartibda yopadi, ya'ni bu tozalash billing/bandlik seedidan
    OLDIN yuguradi va FK zanjiri buzilmaydi.
    """
    owner = LateReview(sync_owner_conn, env_with_slots.market_id, env_with_slots.reviewer_id)
    try:
        yield owner
    finally:
        owner.cleanup()


def _verdict_for(rows: list[StallSlotVerdict], stall_id: UUID) -> StallSlotVerdict:
    """Rasta bo'yicha natija — TOPILMASA nazorat asserti bilan yiqiladi.

    ⛔ `next((r for r in rows if ...), None)` shaklidagi jimgina `None`
       G-6 ni BO'SH ROST qilardi: «hisob yo'q» da'vosi rasta ro'yxatga
       umuman kirmagani uchun ham rost bo'lib chiqardi.
    """
    for row in rows:
        if row.stall_id == stall_id:
            return row
    raise AssertionError(f"{stall_id} rastasi natijada yo'q — slot qatorlari yozilmagan")


# ===========================================================================
# 5. G-6 — D-04 PREDIKATI UCH HOLATDA (C-6)
#
# ⛔ UCH ALOHIDA NOMLANGAN TEST, BITTA PARAMETRLI TEST EMAS: uch holat uch
#    BOSHQA nosozlikni ushlaydi va ular bitta nomga siqilganda «qaysi holat
#    qizardi?» savoli qizil chiqishdan KO'RINMASDI.
# ===========================================================================


async def test_two_ai_occupied_slots_are_billable(
    tenant_session: TenantSessionFactory, env_with_slots: Env
) -> None:
    """(1) Ikki slotda AI-`occupied` -> hisob YOZILADI (BILL-01 ning asosiy yo'li)."""
    env = env_with_slots
    stall_id = env.stall("stall_with_two_occupied_slots")

    async with tenant_session(env.market_id) as session:
        rows = await billable_stalls(
            session, market_id=env.market_id, service_date=SEED_BUSINESS_DATE
        )

    verdict = _verdict_for(rows, stall_id)
    assert verdict.decision.occupied_slots == 2
    assert verdict.decision.billable is True


async def test_one_ai_occupied_slot_with_human_empty_elsewhere_is_not_billable(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    env_with_slots: Env,
    late_review: LateReview,
) -> None:
    """(2) ⛔⛔ C-6 NING BUTUN SABABI — BITTA TESTDA.

    =========================================================================
    HOLAT: rasta BIR slotda AI-`occupied`, BOSHQA slotda nazoratchi
    «BO'SH» degan. Ya'ni:

        occupied_slots = 1
        «biror slotda inson javobi bormi?» = TRUE   <- MAVJUD hisobot ustuni
        «AYNI slotda inson bandlikni tasdiqladimi?» = FALSE  <- D-04 ning sharti

    `occupancy_repo.py:369` dagi ustun BIRINCHI savolga javob beradi va
    D-04 uni qayta ishlatsa hisob YOZILARDI — holbuki HECH KIM bandlikni
    tasdiqlamagan. Bu aynan D-02 ning nizo sinfi: sotuvchi TO'LAMAGAN
    patta uchun qarzdor bo'lardi.

    ⛔ TEST IKKALA SONNI HAM O'LCHAYDI (sabotaj ushbu faylda MEXANIK
       bo'lsin): «insonli slot bor» — ROST, «insonli BAND slot bor» —
       YOLG'ON. Predikat noto'g'ri ustunga almashtirilganda birinchi son
       o'zgarmaydi, ikkinchisi esa qaror bilan birga qizaradi.
    """
    env = env_with_slots
    stall_id = env.stall("stall_with_one_ai_occupied_slot")

    # IKKINCHI slotga zona + hodisa (AI «band» deydi) va unga INSON «bo'sh» javobi.
    event_id = late_review.add_occupied_zone(
        camera_id=_second_camera_of(sync_owner_conn, env),
        stall_id=stall_id,
        snapshot_id=_second_snapshot_of(env),
        center=(0.12, 0.86),
    )
    late_review.answer(event_id=event_id, human_verdict=OccupancyVerdict.EMPTY.value)
    await day_close(app_sessionmaker, business_date=SEED_BUSINESS_DATE)

    async with tenant_session(env.market_id) as session:
        rows = await billable_stalls(
            session, market_id=env.market_id, service_date=SEED_BUSINESS_DATE
        )

    verdict = _verdict_for(rows, stall_id)
    human_anywhere = any(
        row.resolution_source == ResolutionSource.HUMAN.value for row in verdict.rows
    )
    human_on_an_occupied_slot = any(
        row.verdict == OccupancyVerdict.OCCUPIED.value
        and row.resolution_source == ResolutionSource.HUMAN.value
        for row in verdict.rows
    )

    assert verdict.decision.occupied_slots == 1
    assert human_anywhere is True, (
        "nazorat: inson javobi materializatsiya qilinmagan — holat umuman "
        "qurilmagan va da'vo BO'SH ROST bo'lardi"
    )
    assert human_on_an_occupied_slot is False
    assert verdict.decision.billable is False, (
        "C-6: nazoratchi BOSHQA slotda «bo'sh» degan bo'lsa hisob YOZILMAYDI"
    )


async def test_one_human_confirmed_occupied_slot_is_billable(
    tenant_session: TenantSessionFactory, env_with_slots: Env
) -> None:
    """(3) Bitta slot, lekin AYNI slotda inson bandlikni TASDIQLAGAN -> hisob BOR."""
    env = env_with_slots
    stall_id = env.stall("stall_with_one_human_confirmed_occupied_slot")

    async with tenant_session(env.market_id) as session:
        rows = await billable_stalls(
            session, market_id=env.market_id, service_date=SEED_BUSINESS_DATE
        )

    verdict = _verdict_for(rows, stall_id)
    assert verdict.decision.occupied_slots == 1
    assert any(
        row.verdict == OccupancyVerdict.OCCUPIED.value
        and row.resolution_source == ResolutionSource.HUMAN.value
        for row in verdict.rows
    )
    assert verdict.decision.billable is True


def _second_camera_of(conn: Connection[TupleRow], env: Env) -> UUID:
    """A bozorining IKKINCHI kamerasi — `camera_zones` DAN, ro'yxat indeksidan EMAS.

    Seed ikkinchi kadrni AYNAN o'sha kameraga yozadi
    (`billing_domain._add_billable_frame`), ya'ni «ikkinchi slotda yaroqli
    kadr» faqat shu kamerada mavjud.
    """
    row = conn.execute(
        "SELECT camera_id FROM snapshots WHERE market_id = %s AND id = %s",
        (str(env.market_id), str(_second_snapshot_of(env))),
    ).fetchone()
    assert row is not None, "nazorat: ikkinchi yaroqli kadr topilmadi"
    camera_id: UUID = row[0]
    return camera_id


def _second_snapshot_of(env: Env) -> UUID:
    snapshot_id = env.live.second_billable_snapshot_id
    assert snapshot_id is not None, "nazorat: seedda ikkinchi yaroqli kadr yo'q"
    return snapshot_id


# ===========================================================================
# 6. HISOB YOZISH — IDEMPOTENTLIK VA D-28 (D-06, D-07)
# ===========================================================================


async def _money_for(
    tenant_session: TenantSessionFactory, env: Env, stall_id: UUID, day: date
) -> StallDayMoney:
    async with tenant_session(env.market_id) as session:
        return _one(
            await resolve_stall_day_money(
                session, market_id=env.market_id, as_of=day, stall_id=stall_id
            )
        )


async def test_a_second_write_leaves_the_existing_charge_untouched(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-06/D-07: ikkinchi yozuv `None` qaytaradi va QATORGA TEGMAYDI.

    =========================================================================
    ⛔ HOLAT BILAN O'LCHANADI, `rowcount` bilan EMAS: `amount_soum` HAM,
       `created_at` HAM o'zgarmagan bo'lishi kerak. 05-12 dagi «qayta
       yugurish idempotentmi?» testining zaifligi aynan shu edi — u faqat
       qator SONINI ko'rgan va `DO UPDATE` bilan ham yashil qolardi.

    ⚠ `None` XATO EMAS (Pitfall 3): `ON CONFLICT DO NOTHING` konfliktda
      hech nima QAYTARMAYDI va chaqiruvchi buni «allaqachon bor» deb
      sanaydi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    day = _open_past_day(sync_owner_conn)
    money = await _money_for(tenant_session, env, stall_id, day)

    async with tenant_session(env.market_id) as session:
        first = await write_charge(
            session,
            market_id=env.market_id,
            stall_id=stall_id,
            service_date=day,
            money=money,
        )
    before = sync_owner_conn.execute(
        "SELECT amount_soum, tariff_id, created_at FROM daily_charges WHERE id = %s",
        (str(first),),
    ).fetchone()

    async with tenant_session(env.market_id) as session:
        second = await write_charge(
            session,
            market_id=env.market_id,
            stall_id=stall_id,
            service_date=day,
            money=money,
        )

    rows = sync_owner_conn.execute(
        "SELECT count(*) FROM daily_charges WHERE market_id = %s AND stall_id = %s "
        "AND service_date = %s",
        (str(env.market_id), str(stall_id), day),
    ).fetchone()
    after = sync_owner_conn.execute(
        "SELECT amount_soum, tariff_id, created_at FROM daily_charges WHERE id = %s",
        (str(first),),
    ).fetchone()

    assert first is not None
    assert second is None
    assert rows is not None and rows[0] == 1
    assert before is not None and after is not None
    assert before == after, "yozilgan hisob O'ZGARMAS — summa ham, tug'ilgan vaqti ham"
    assert before[0] == TARIFF_SOUM
    assert before[1] == env.live.tariff_id, "D-09: `tariff_id` HAM saqlanadi"


async def test_write_charge_refuses_a_charge_without_a_vendor(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-28: «kimdir qarzdor, lekin kim ekani noma'lum» yozuvi IMKONSIZ.

    ⛔ `ValueError` — `IntegrityError` EMAS: xato TURI saqlanishi kerak,
       aks holda 06-07 uni `billing_close_failed` deb yozib qo'yardi va
       dasturchi xatosi ish vaqti nosozligiga aylanardi.
    """
    stall_id = env.stall("stall_occupied_without_assignment")
    # ⚠ BO'SHLIQ AYNAN `SEED_BUSINESS_DATE` DA: seed davrlarni
    #   `[BILLING_VALID_FROM, D)` va `[D + 7, ∞)` qilib yozadi, ya'ni o'tmishdagi
    #   ixtiyoriy kunda rasta BIRIKTIRILGAN bo'lib chiqardi va nazorat asserti
    #   testni «holat qurilmagan» deb to'xtatardi.
    day = SEED_BUSINESS_DATE
    money = await _money_for(tenant_session, env, stall_id, day)
    assert money.vendor_id is None, "nazorat: rasta bu kunda biriktirilgan bo'lmasligi kerak"

    with pytest.raises(ValueError, match="D-28"):
        async with tenant_session(env.market_id) as session:
            await write_charge(
                session,
                market_id=env.market_id,
                stall_id=stall_id,
                service_date=day,
                money=money,
            )

    rows = sync_owner_conn.execute(
        "SELECT count(*) FROM daily_charges WHERE market_id = %s AND stall_id = %s",
        (str(env.market_id), str(stall_id)),
    ).fetchone()
    assert rows is not None and rows[0] == 0


async def test_a_charge_service_date_is_the_slot_day_not_its_business_date(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """G-2 ning REPO YARMI — Pitfall 1 ning ikki ustuni AJRALGAN.

    =========================================================================
    ⛔ IKKI USTUN, IKKI MA'NO:

        daily_charges.service_date   -> HISOBLANAYOTGAN kun (argumentdan)
        daily_charges.business_date  -> QATOR YOZILGAN kun (GENERATED)

    Ular bir xil bo'lib qolsa (masalan kimdir `business_date` ni
    `service_date` dan hosila qilsa) `ON CONFLICT` normal ish oqimida —
    job D kunini D+1 da yopadi — TO'QNASHMASDI va o'sha rasta-kunga
    IKKINCHI hisob yozilardi. Shuning uchun test ikkalasining FARQINI
    ochiq da'vo qiladi.

    ⚠ TO'LIQ G-2 («har yozilgan hisob uchun o'sha kunda kamida bitta slot
      qatori bor») shu SEED bilan ifodalab BO'LMAYDI: slot kuni
      `SEED_BUSINESS_DATE` = kelajak, hisob esa
      `ck_daily_charges_service_date_not_in_future` bo'yicha kelajakka
      yozilmaydi. To'liq invariant `test_phase6_criteria.py` (06-14) ning
      ishi — 06-05 uni allaqachon o'sha yerga biriktirgan.
    """
    stall_id = env.stall("stall_with_one_ai_occupied_slot")
    day = _open_past_day(sync_owner_conn)
    money = await _money_for(tenant_session, env, stall_id, day)

    async with tenant_session(env.market_id) as session:
        charge_id = await write_charge(
            session,
            market_id=env.market_id,
            stall_id=stall_id,
            service_date=day,
            money=money,
        )

    row = sync_owner_conn.execute(
        "SELECT service_date, business_date FROM daily_charges WHERE id = %s",
        (str(charge_id),),
    ).fetchone()
    today = _service_day(sync_owner_conn, 0)

    assert row is not None
    assert row[0] == day
    assert row[1] == today
    assert row[0] != row[1], (
        "ikki ustun BIR XIL kun bo'lib qoldi — `business_date` ning audit "
        "ma'nosi yo'qolgan va D-06 ning idempotentlik kaliti buzilgan"
    )


# ===========================================================================
# 7. DALIL — MUZLATILGAN NUSXA (D-08, C-7)
# ===========================================================================


async def _slot_rows_for(
    tenant_session: TenantSessionFactory, env: Env, stall_id: UUID
) -> tuple[SlotEvidenceRow, ...]:
    async with tenant_session(env.market_id) as session:
        rows = await billable_stalls(
            session, market_id=env.market_id, service_date=SEED_BUSINESS_DATE
        )
    return _verdict_for(rows, stall_id).rows


async def test_frozen_evidence_survives_a_day_close_rerun(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    env_with_slots: Env,
    late_review: LateReview,
) -> None:
    """D-08/C-7: `day_close` qayta yugurib slotni O'ZGARTIRSA HAM dalil o'sha.

    =========================================================================
    ⛔ SABOTAJ TESTNING ICHIDA: nazoratchi kech javob yozadi, `day_close`
       qayta yuguradi va slot qatorining `winning_occupancy_event_id` i
       **o'zgaradi**. Bu O'LCHANADI (nazorat asserti) — aks holda
       «dalil o'zgarmadi» da'vosi hech nima o'zgarmagani uchun ham rost
       bo'lardi.

    ⛔ Muzlatilgan pointer — `occupancy_event_id` (`occupancy_events`
       shartsiz o'zgarmas), `stall_slot_occupancy_id` esa faqat AUDIT
       havolasi: o'sha qator MUTABLE (`_MATERIALIZE_SLOT` `DO UPDATE`).
    """
    env = env_with_slots
    stall_id = env.stall("stall_with_two_occupied_slots")
    day = _open_past_day(sync_owner_conn)
    money = await _money_for(tenant_session, env, stall_id, day)
    slot_rows = await _slot_rows_for(tenant_session, env, stall_id)

    async with tenant_session(env.market_id) as session:
        charge_id = await write_charge(
            session, market_id=env.market_id, stall_id=stall_id, service_date=day, money=money
        )
        assert charge_id is not None
        written = await write_evidence(
            session, market_id=env.market_id, charge_id=charge_id, slot_rows=slot_rows
        )

    assert written == 2, "ikkala band slot ham dalil qatorini berishi kerak"
    before = _evidence_rows(sync_owner_conn, charge_id)

    # ---- KECH KELGAN TASDIQ: nazoratchi bitta slotni «bo'sh» qiladi.
    flipped = next(row for row in slot_rows if row.winning_occupancy_event_id is not None)
    assert flipped.winning_occupancy_event_id is not None
    late_review.answer(
        event_id=flipped.winning_occupancy_event_id,
        human_verdict=OccupancyVerdict.EMPTY.value,
    )
    await day_close(app_sessionmaker, business_date=SEED_BUSINESS_DATE)

    changed = sync_owner_conn.execute(
        "SELECT winning_occupancy_event_id FROM stall_slot_occupancy WHERE id = %s",
        (str(flipped.stall_slot_occupancy_id),),
    ).fetchone()
    assert changed is not None and changed[0] is None, (
        "nazorat: slot qatori O'ZGARMADI — sabotaj sistemaga yetib bormagan va "
        "«dalil muzlagan» da'vosi hech nimani o'lchamasdi"
    )

    assert _evidence_rows(sync_owner_conn, charge_id) == before


def _evidence_rows(conn: Connection[TupleRow], charge_id: UUID | None) -> list[tuple[UUID, ...]]:
    """Dalil zanjiri — `occupancy_events` orqali `snapshots` ga yetgan holda.

    `JOIN` ATAYIN: `snapshot_id` NUSXA sifatida saqlanadi va u haqiqiy
    kadrga yetishi kerak — nusxaning O'ZI to'g'ri bo'lsa-yu, kadr yo'q
    bo'lsa nizoda ko'rsatadigan rasm bo'lmasdi.
    """
    return [
        tuple(row)
        for row in conn.execute(
            "SELECT ce.stall_slot_occupancy_id, ce.occupancy_event_id, ce.snapshot_id "
            "FROM charge_evidence ce "
            "JOIN occupancy_events ev ON ev.id = ce.occupancy_event_id "
            "JOIN snapshots sn ON sn.id = ce.snapshot_id "
            "WHERE ce.charge_id = %s ORDER BY ce.stall_slot_occupancy_id",
            (str(charge_id),),
        ).fetchall()
    ]


async def test_write_evidence_is_idempotent(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env_with_slots: Env,
) -> None:
    """Job qayta yugurishi dublikat dalil YARATMAYDI (`ON CONFLICT DO NOTHING`).

    Dublikat qator «nechta slotda band edi?» sanog'ini SHISHIRARDI va
    hisobotdagi bandlik foizi jimgina o'sib ketardi.
    """
    env = env_with_slots
    stall_id = env.stall("stall_with_two_occupied_slots")
    day = _open_past_day(sync_owner_conn)
    money = await _money_for(tenant_session, env, stall_id, day)
    slot_rows = await _slot_rows_for(tenant_session, env, stall_id)

    async with tenant_session(env.market_id) as session:
        charge_id = await write_charge(
            session, market_id=env.market_id, stall_id=stall_id, service_date=day, money=money
        )
        assert charge_id is not None, "nazorat: birinchi yozuv hisob tug'dirishi kerak"
        first = await write_evidence(
            session, market_id=env.market_id, charge_id=charge_id, slot_rows=slot_rows
        )
        second = await write_evidence(
            session, market_id=env.market_id, charge_id=charge_id, slot_rows=slot_rows
        )

    assert first == 2
    assert second == 0
    assert len(_evidence_rows(sync_owner_conn, charge_id)) == 2


# ===========================================================================
# 8. ANOMALIYA — JUFTLANGAN SHART IKKI QATLAMDA (C-12, D-05, D-29)
# ===========================================================================


async def test_a_no_coverage_anomaly_refuses_an_evidence_pointer(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """C-12: «ko'ra olmadik» da'vosi KO'RILGAN kadr bilan kela olmaydi.

    ⛔ ILOVA QATLAMI `CHECK` DAN OLDIN RAD ETADI va bu ikki qatlamning
       BIRINCHISI: `CHECK` ni `IntegrityError` bilan ushlash xato TURINI
       yo'qotardi. Ikkinchi qatlam (`no_coverage_is_paired`) sxemada va u
       xom SQL yo'lini ham yopadi.
    """
    stall_id = env.stall("stall_with_only_no_coverage_slots")
    day = _open_past_day_from(env)

    with pytest.raises(ValueError, match="C-12"):
        async with tenant_session(env.market_id) as session:
            await write_anomaly(
                session,
                market_id=env.market_id,
                stall_id=stall_id,
                service_date=day,
                kind=AnomalyKind.NO_COVERAGE_STALL,
                occupancy_event_id=env.live.event_ids[0],
                snapshot_id=env.live.snapshot_ids[0],
            )


async def test_an_unassigned_anomaly_refuses_a_missing_evidence_pointer(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-29 ning teskari yarmi: «band, lekin to'lovsiz» da'vosi DALILSIZ yozilmaydi.

    Bu mahsulotning YAGONA qiymati (`PROJECT.md` Core Value): rasm-dalilsiz
    da'vo sotuvchi bilan nizoda hech nimani isbotlamasdi.
    """
    stall_id = env.stall("stall_occupied_without_assignment")
    day = _open_past_day_from(env)

    with pytest.raises(ValueError, match="D-29"):
        async with tenant_session(env.market_id) as session:
            await write_anomaly(
                session,
                market_id=env.market_id,
                stall_id=stall_id,
                service_date=day,
                kind=AnomalyKind.UNASSIGNED_OCCUPIED,
            )


async def test_a_rerun_does_not_duplicate_an_anomaly(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """Uchala turdagi anomaliya ham idempotent (`ON CONFLICT DO NOTHING`).

    ⚠ IJOBIY NAZORAT MAJBURIY: rad etish testlari `write_anomaly()` ni
      butunlay yiqilgan holatda ham yashil qoldirardi.
    """
    stall_id = env.stall("stall_with_only_no_coverage_slots")
    day = _open_past_day_from(env)

    async with tenant_session(env.market_id) as session:
        first = await write_anomaly(
            session,
            market_id=env.market_id,
            stall_id=stall_id,
            service_date=day,
            kind=AnomalyKind.NO_COVERAGE_STALL,
        )
        second = await write_anomaly(
            session,
            market_id=env.market_id,
            stall_id=stall_id,
            service_date=day,
            kind=AnomalyKind.NO_COVERAGE_STALL,
        )

    rows = sync_owner_conn.execute(
        "SELECT count(*) FROM billing_anomalies WHERE market_id = %s AND stall_id = %s",
        (str(env.market_id), str(stall_id)),
    ).fetchone()

    assert first is not None
    assert second is None
    assert rows is not None and rows[0] == 1


def _open_past_day_from(env: Env) -> date:
    """Anomaliya sanasi — `ck_billing_anomalies_service_date_not_in_future` uchun.

    ⚠ Anomaliya kalendarga tayanmaydi (u YOPIQ kunda ham yoziladi), ya'ni
      bu yerda hafta kunini tanlash SHART EMAS — faqat kelajak bo'lmasin.
    """
    return env.domain.market_a.operating_since


# ===========================================================================
# 9. QOLDIQ — HISOBLANADIGAN, SAQLANMAYDIGAN (BILL-03, C-4, C-5)
# ===========================================================================

_INSERT_ADJUSTMENT = (
    "INSERT INTO charge_adjustments "
    "(id, market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""Tuzatish qatori — `amount_soum` HAR DOIM MUSBAT, belgi `direction` da (C-5).

⚠ `delta_soum` nomli ustun YO'Q va bo'lmaydi: `test_meta.py` ning moliyaviy
  darvozasi `amount_soum > 0` regeksini AYNAN shu nomda izlaydi.
"""


def _adjust(
    conn: Connection[TupleRow],
    *,
    env: Env,
    charge_id: UUID,
    direction: AdjustmentDirection,
    amount_soum: int,
) -> None:
    conn.execute(
        _INSERT_ADJUSTMENT,
        (
            str(uuid4()),
            str(env.market_id),
            str(charge_id),
            direction.value,
            AdjustmentReason.TARIFF_CORRECTION.value,
            amount_soum,
            str(env.base.market_a.admin_user_id),
        ),
    )


def _pay(
    conn: Connection[TupleRow],
    *,
    env: Env,
    stall_id: UUID,
    amount_soum: int,
    kind: PaymentKind = PaymentKind.PAYMENT,
    reverses_payment_id: UUID | None = None,
) -> UUID:
    """To'lov (yoki STORNO) qatori — `quote_soum` summaga TENG.

    ⚠ `payments` da `CHECK ((amount_soum = quote_soum) = (override_reason IS
      NULL))` bor: kvotani summadan ajratish `override_reason` ni TALAB
      qilardi va bu boshqa (D-19) da'voning holati bo'lardi.
    """
    return add_payment(
        conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
        amount_soum=amount_soum,
        quote_soum=amount_soum,
        kind=kind.value,
        reverses_payment_id=reverses_payment_id,
        reversal_reason=None if kind is PaymentKind.PAYMENT else ReversalReason.WRONG_STALL.value,
    )


async def _outstanding(tenant_session: TenantSessionFactory, env: Env) -> int:
    async with tenant_session(env.market_id) as session:
        balances = await vendor_outstanding(
            session, market_id=env.market_id, vendor_ids=[env.live.vendor_id]
        )
    return balances.get(env.live.vendor_id, 0)


async def test_outstanding_is_charges_plus_adjustments_minus_payments(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """BILL-03: qoldiq SO'ROV va u QO'LDA hisoblangan LITERAL son bilan solishtiriladi.

    =========================================================================
    30 000 (ikki hisob) − 5 000 (chegirma) − 10 000 (to'lov) = ⛔ 15 000.

    ⛔ SAQLANGAN BALANS USTUNI HECH QAYERDA YO'Q va u qo'shilmaydi: drift
       nizoga aylanadi va aynan shu nizo SBOZOR mavjud bo'lish sababidir
       (D-02). Literal son ATAYIN: hisob-kitobni testda qayta yozish
       so'rovning O'ZINI takrorlardi va u hech nimani o'lchamasdi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    first_charge, _ = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
        service_date=_service_day(sync_owner_conn, 2),
    )
    add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
        service_date=_service_day(sync_owner_conn, 1),
    )
    _adjust(
        sync_owner_conn,
        env=env,
        charge_id=first_charge,
        direction=AdjustmentDirection.DECREASE,
        amount_soum=5_000,
    )
    _pay(sync_owner_conn, env=env, stall_id=stall_id, amount_soum=10_000)

    assert await _outstanding(tenant_session, env) == 15_000


async def test_a_reversal_increases_the_outstanding_amount(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """D-23: storno YANGI QATOR va u qoldiqni QAYTA KO'TARADI.

    ⛔ `payments` APPEND-ONLY: xato to'lov O'CHIRILMAYDI va TAHRIRLANMAYDI,
       u manfiy belgili qator bilan qoplanadi. Belgi USTUNDA emas,
       KO'RINISHDA (`kind = 'reversal'` -> `-amount_soum`), chunki
       `CHECK (amount_soum > 0)` manfiy qiymatni umuman ifodalab
       bo'lmaydigan qiladi (C-5).
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
    )
    payment_id = _pay(sync_owner_conn, env=env, stall_id=stall_id, amount_soum=TARIFF_SOUM)
    assert await _outstanding(tenant_session, env) == 0

    _pay(
        sync_owner_conn,
        env=env,
        stall_id=stall_id,
        amount_soum=TARIFF_SOUM,
        kind=PaymentKind.REVERSAL,
        reverses_payment_id=payment_id,
    )

    assert await _outstanding(tenant_session, env) == TARIFF_SOUM


async def test_an_overpayment_yields_a_negative_outstanding_amount(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """OQ-4/A4: AVANS ruxsat etiladi va natija MANFIY bo'lib qoladi.

    ⛔ KATTALIKKA AYLANTIRILMAYDI (`abs` bu modulda umuman yo'q): ortiqcha
       to'lovni bloklash kassirni pulni UMUMAN YOZMASLIKKA majburlardi —
       ya'ni himoya o'zi himoya qilayotgan yozuvni yo'q qilardi. Ekranda u
       «Avans» bo'lib ko'rinadi (UI-SPEC §9.6).
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
    )
    _pay(sync_owner_conn, env=env, stall_id=stall_id, amount_soum=20_000)

    assert await _outstanding(tenant_session, env) == -5_000


# ===========================================================================
# 10. D-24 — «QAYSI KUNNING PATTASI TO'LANDI?» NING TASDIQI (G-13, G-14)
#
# ⛔ UCH ALOHIDA NOMLANGAN TEST: bir to'lov N kunga, qisman to'lov va ikki
#    hosila ko'rinishning TENGLIGI uch BOSHQA nosozlikni ushlaydi.
# ===========================================================================


def _three_unpaid_days(conn: Connection[TupleRow], env: Env) -> tuple[date, date, date]:
    """Sotuvchiga uch KETMA-KET kunlik to'lanmagan hisob (15 000 x 3).

    ⚠ Uchala hisob ham BITTA rastada: kunlar bo'yicha tartib
      («qaysi kun oldin yopiladi?») aynan shu bilan o'lchanadi. Bir kunda
      IKKI RASTA holati 06-01 ning jadval testida (`stall_code` tenglik
      uzgichi) alohida qamralgan.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    days = (
        _service_day(conn, 3),
        _service_day(conn, 2),
        _service_day(conn, 1),
    )
    for day in days:
        add_daily_charge(
            conn,
            market_id=env.market_id,
            stall_id=stall_id,
            vendor_id=env.live.vendor_id,
            tariff_id=env.live.tariff_id,
            service_date=day,
        )
    return days


async def _allocation(tenant_session: TenantSessionFactory, env: Env) -> ChargeCreditAllocation:
    async with tenant_session(env.market_id) as session:
        return await vendor_charge_allocation(
            session, market_id=env.market_id, vendor_id=env.live.vendor_id
        )


async def test_a_single_payment_across_days_settles_the_oldest_first(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ D-24 NING JAVOBI — PROZA EMAS, RO'YXAT.

    =========================================================================
    Uch kunlik qarz (15 000 x 3) va AYNAN BITTA 45 000 to'lov — bu
    `[Qarzni ham olish]` oqimining o'zi (UI-SPEC §9.6). `payments.charge_id`
    YO'Q (C-4) va `service_date` yolg'iz javob BERMAYDI: u BUGUN bo'lib
    qoladi, to'langan kunlar esa ESKI.

    ⛔ JAVOB NOMLANGAN QOIDADAN keladi — `FIFO_OLDEST_SERVICE_DATE_FIRST` —
       va test yopilgan kunlarning RO'YXATINI, TARTIBI bilan da'vo qiladi.

    ⛔ HECH NIMA SAQLANMAYDI: taqsimlash jadvali ham, `allocated_*` ustuni
       ham yo'q (D-07/BILL-03). Funksiya HOSILA ko'rinish qaytaradi.
    """
    days = _three_unpaid_days(sync_owner_conn, env)
    _pay(
        sync_owner_conn,
        env=env,
        stall_id=env.stall("stall_with_two_occupied_slots"),
        amount_soum=45_000,
    )

    allocation = await _allocation(tenant_session, env)

    assert allocation.rule == ALLOCATION_RULE
    assert [row.service_date for row in allocation.rows if row.settled] == list(days)
    assert allocation.unpaid_soum == 0
    assert allocation.advance_soum == 0


async def test_a_partial_payment_across_days_leaves_the_newest_unpaid(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """QISMAN to'lov — eng qadimgi kun YOPILADI, eng yangisi TEGILMAYDI.

    20 000 kredit: `D-3` to'liq (15 000), `D-2` qisman (5 000), `D-1` — 0.
    ⛔ Uchala qator ham qaytariladi (NOL — NATIJA): «tegilmagan kun»
       ro'yxatdan TUSHIB QOLSA kassir uni to'langan deb o'qishi mumkin edi.
    """
    oldest, middle, newest = _three_unpaid_days(sync_owner_conn, env)
    _pay(
        sync_owner_conn,
        env=env,
        stall_id=env.stall("stall_with_two_occupied_slots"),
        amount_soum=20_000,
    )

    allocation = await _allocation(tenant_session, env)
    by_day = {row.service_date: row for row in allocation.rows}

    assert by_day[oldest].settled is True
    assert by_day[oldest].paid_soum == TARIFF_SOUM
    assert by_day[middle].paid_soum == 5_000
    assert by_day[middle].settled is False
    assert by_day[newest].paid_soum == 0
    assert allocation.unpaid_soum == 25_000


async def test_the_allocation_matches_vendor_outstanding(
    sync_owner_conn: Connection[TupleRow], tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ G-14: IKKI HOSILA KO'RINISH AJRALIB KETA OLMAYDI.

    =========================================================================
    `Σ unpaid_soum` (FIFO ko'rinish) ⛔ `vendor_outstanding()` (hisoblanadigan
    qoldiq) bilan AYNAN bir xil son berishi shart. Aks holda ekrandagi qarz
    bilan hisobotdagi qarz bir kun farq qilardi va IKKALASI HAM «to'g'ri»
    bo'lardi — bu loyihada takroran topilgan sinf.

    Mexanizm: belgili to'lov ifodasi (`_SIGNED_PAYMENT_EXPR`) AYNAN BITTA
    `text()` konstantasi va ikkala funksiya SHUNI ishlatadi.
    """
    _three_unpaid_days(sync_owner_conn, env)
    _pay(
        sync_owner_conn,
        env=env,
        stall_id=env.stall("stall_with_two_occupied_slots"),
        amount_soum=20_000,
    )

    allocation = await _allocation(tenant_session, env)
    outstanding = await _outstanding(tenant_session, env)

    assert outstanding > 0, "nazorat: avans holati bu da'voning shartidan tashqarida"
    assert sum(row.unpaid_soum for row in allocation.rows) == outstanding


# ===========================================================================
# 11. PROYEKSIYA (BILL-05, D-16, D-17, D-31)
# ===========================================================================

PENDING_STALL_FIELDS = {
    "stall_code",
    "service_date",
    "market_open",
    "amount_soum",
    "amount_unavailable_reason",
    "outstanding_soum",
    "total_due_soum",
}
"""UI-SPEC §9.2 ning AYNAN yetti kaliti — TESTDA literal, mahsulotdan EMAS.

⛔ Mahsulot konstantasidan import qilish darvozani o'zi tekshirayotgan
   qiymatga bog'lardi va sakkizinchi maydon JIMGINA qo'shilardi (05-15 da
   o'rnatilgan qoida).
"""


def test_pending_projection_exposes_exactly_seven_fields() -> None:
    """D-31: TO'PLAM TENGLIGI, inkor tasdiq EMAS.

    `not.toContain("charge_id")` faqat AYNAN o'sha nomni ushlardi va
    `chargeId` jimgina o'tib ketardi. To'plam tengligi esa HAR QANDAY
    yangi maydonni ushlaydi — `charge_id`, `tariff_id`, `vendor_id`,
    `occupied_slots`, `balance_soum` (G-22 ning beshala qatori).
    """
    assert {item.name for item in fields(PendingStall)} == PENDING_STALL_FIELDS


async def test_the_projection_amount_equals_the_money_resolution(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """⛔ D-16 NING O'LCHOVI: ikki chaqiruvchi — BIR NATIJA.

    Kassir ko'radigan summa (`pending_projection`) va kechqurun yoziladigan
    summa (`resolve_stall_day_money`) AYNAN BIR funksiyadan keladi. Ikki
    alohida implementatsiya ularni ajratib yuborardi va sotuvchi «men
    boshqa summa to'lagandim» deganda ikkala yozuv ham «to'g'ri» bo'lardi.
    """
    async with tenant_session(env.market_id) as session:
        money = _one(
            await resolve_stall_day_money(
                session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_code="7"
            )
        )
        projection = await pending_projection(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_code="7"
        )

    assert projection.stall is not None
    assert projection.stall.amount_soum == money.amount_soum
    assert projection.stall.total_due_soum == money.amount_soum, (
        "qarzsiz sotuvchida `total_due_soum` bugungi pattaga TENG — qo'shish "
        "amali `sbozor_core.billing.total_due_soum()` dan keladi (§9.6)"
    )


async def test_an_ambiguous_prefix_returns_matches_without_an_amount(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """UI-SPEC §8.2/§8.3 ning SERVER yarmi — va ikkinchi chaqiruv TUGAYDI.

    =========================================================================
    «1» prefiksi seedda IKKI kodga mos keladi («10» va «100»), ya'ni summa
    HISOBLANMAYDI: yo'q summa — yo'q summa (§9.4), taxminiy summa
    ko'rsatilmaydi.

    ⛔ IKKINCHI CHAQIRUV: kassir «10» ni tanlaydi. Sof prefiks semantikasi
       o'sha ro'yxatni QAYTA berardi (chunki «10» ham «100» ning prefiksi)
       va oqim HECH QACHON `ready` holatiga yetmasdi. Shuning uchun ANIQ
       moslik USTUN va bu test aynan shu tugashni o'lchaydi.
    """
    async with tenant_session(env.market_id) as session:
        ambiguous = await pending_projection(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_code="1"
        )
        exact = await pending_projection(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE, stall_code="10"
        )

    assert ambiguous.stall is None
    assert ambiguous.matches == ("10", "100")
    assert exact.matches == ()
    assert exact.stall is not None
    assert exact.stall.stall_code == "10"


async def test_the_market_projection_returns_zero_as_a_result(
    tenant_session: TenantSessionFactory, env: Env
) -> None:
    """UI-SPEC §9.5 — bozor kesimi; ⛔ NOL HAM NATIJA.

    =========================================================================
    Uchala son HAR DOIM qaytariladi. `outstanding_soum` bu seedda AYNAN
    NOL (birorta hisob yozilmagan) va u NATIJA sifatida qaytadi — «hisobot
    yo'q» degan javob direktorni ma'lumot yo'qolgan deb o'ylashga
    majburlardi.

    Kutilayotgan summa BOZOR DOMENIDAN hosila: to'rt rasta billing
    toifasida (15 000), «10» va «100» esa `market_domain` ning ikkinchi va
    uchinchi toifasida qoladi (billing seed ularga toifa davri
    yozmaydi — `billing_domain.py:812-819`).
    """
    async with tenant_session(env.market_id) as session:
        projection = await pending_projection(
            session, market_id=env.market_id, as_of=SEED_BUSINESS_DATE
        )

    assert projection.stall is None
    assert projection.matches == ()
    assert projection.market is not None
    assert projection.market.pending_stall_count == len(A_STALL_CODES_BY_SORT)
    assert projection.market.pending_amount_soum == (
        4 * TARIFF_SOUM + A_TARIFF_AMOUNTS[1] + A_TARIFF_AMOUNTS[2]
    )
    assert projection.market.outstanding_soum == 0
    assert projection.market.fetched_at.tzinfo is not None
