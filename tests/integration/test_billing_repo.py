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

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from app.repositories.billing_repo import resolve_stall_day_money
from app.services.billing_errors import MARKET_CLOSED, TARIFF_MISSING
from fixtures.billing_domain import (
    CLOSED_BUSINESS_DATE,
    NEXT_DAY_TARIFF_SOUM,
    NEXT_TARIFF_VALID_FROM,
    SEED_BUSINESS_DATE,
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    billing_domain_before_day_close,
)
from fixtures.market_domain import HANDOVER_DAY, MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from app.repositories.billing_repo import StallDayMoney
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow


class Env:
    """Beshta qatlamli seed — `test_billing_immutable.Env` shakli."""

    def __init__(self, billing: BillingDomainSeed, domain: MarketDomainSeed) -> None:
        self.billing = billing
        self.domain = domain

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
        yield Env(billing, market_domain)


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
    import psycopg

    stall_id = env.stall("stall_with_two_occupied_slots")
    other_vendor = env.domain.market_a.vendor_ids[1]

    with pytest.raises(psycopg.errors.ExclusionViolation) as excinfo:
        sync_owner_conn.execute(
            "INSERT INTO stall_assignments (id, market_id, stall_id, vendor_id, period) "
            "VALUES (%s, %s, %s, %s, daterange(%s, NULL, '[)'))",
            (
                str(UUID(int=0x5B0209)),
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
