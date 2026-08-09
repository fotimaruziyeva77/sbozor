"""Kun yopilishi — AI-06 HISOBLANADI, YOZILMAYDI va D-22 KO'RINADI.

=============================================================================
BU FAYL UCHTA BOSHQA-BOSHQA DA'VONI O'LCHAYDI VA ULARNI ARALASHTIRMAYDI.

  1. HOSILA TO'G'RIMI — tasdiqlanmagan `uncertain` `empty` bo'ladimi,
     bir kamera «band» desa rasta band bo'ladimi, qamrovsiz rasta
     `no_coverage` bo'lib QOLADIMI;
  2. NIMA YOZILMAYDI — `zone_reviews` qatorlari soni kun yopilishidan
     OLDIN va KEYIN teng bo'ladimi (D-19);
  3. KAFOLAT TRANZITIVMI — `stall_slot_occupancy` yaroqsiz kadrga
     yetib bora oladimi (D-21).

⚠ HAR SINOV O'Z BOSHLANG'ICH HOLATINI TOZALAYDI (`clear_slots`). Seed
  `stall_slot_occupancy` ga IKKI qator yozadi (05-05) va ular
  materializatsiyaning natijasi bilan aralashib ketardi: «to'g'ri qator
  bor» degan assert seed'ning o'z qatorini ko'rib yashil qolishi
  mumkin edi. `clear_slots` ning O'ZI ham nazorat asserti bilan keladi.
=============================================================================
"""

from __future__ import annotations

from datetime import date, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from app.jobs.day_close import DAY_CLOSE_COMPONENT, day_close
from app.repositories.occupancy_repo import OccupancyRepository
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    CONFIDENCE_0_55,
    OccupancyDomainSeed,
    SeededEvent,
    add_zone_with_event,
    occupancy_rows,
)
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    OccupancyVerdict,
    ResolutionSource,
    ReviewPurpose,
    ReviewQueueKind,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

HIGH_CONFIDENCE = "0.9100"

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


# ===========================================================================
# Muhit
# ===========================================================================


class Env:
    """To'rt qatlamli seed — `test_blind_audit.Env` shakli."""

    def __init__(
        self,
        base: TwoMarketSeed,
        domain: MarketDomainSeed,
        occupancy: OccupancyDomainSeed,
    ) -> None:
        self.base = base
        self.domain = domain
        self.occupancy = occupancy

    @property
    def market_a(self) -> UUID:
        return self.base.market_a.id

    @property
    def market_b(self) -> UUID:
        return self.base.market_b.id

    @property
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def second_camera_a(self) -> UUID:
        camera_id = self.occupancy.market_a.second_camera_id
        assert camera_id is not None, "nazorat: seed'da A bozorining ikkinchi kamerasi yo'q"
        return camera_id

    @property
    def snapshot_a(self) -> UUID:
        return self.occupancy.market_a.snapshot_with_ok_quality

    @property
    def dark_snapshot_a(self) -> UUID:
        snapshot_id = self.occupancy.market_a.snapshot_with_dark_quality
        assert snapshot_id is not None, "nazorat: seed'da yaroqsiz kadr yo'q"
        return snapshot_id

    @property
    def occupied_stall(self) -> UUID:
        """Zonasi va `occupied` hodisasi BOR rasta."""
        return self.domain.market_a.stall_ids[0]

    @property
    def uncertain_stall(self) -> UUID:
        """`uncertain` hodisasi bor va JAVOBSIZ qolgan rasta (AI-06 kirishi)."""
        return self.domain.market_a.stall_ids[1]

    @property
    def uncovered_stall(self) -> UUID:
        """Birorta zonasi bo'lmagan rasta (D-22 kirishi)."""
        stall_id = self.occupancy.market_a.stall_without_zone_id
        assert stall_id is not None, "nazorat: seed'da qamrovsiz rasta yo'q"
        return stall_id

    @property
    def reviewer_id(self) -> UUID:
        """`zone_reviews.reviewer_id` — seed AYNAN shu foydalanuvchini ishlatadi."""
        return self.base.market_a.admin_user_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        yield Env(two_markets, market_domain, occupancy)


# ===========================================================================
# Yordamchilar — HAMMASI BAZADAN o'qiydi
# ===========================================================================


def clear_slots(conn: Connection[TupleRow], market_id: UUID) -> None:
    """Seed yozgan `stall_slot_occupancy` qatorlarini olib tashlaydi.

    ⚠ NAZORAT ASSERTI BILAN: tozalash ishlamasa keyingi assertlar
      seed'ning O'Z qatorini ko'rib yashil qolishi mumkin edi.

    ⚠ `stall_slot_occupancy` da o'zgarmaslik triggeri YO'Q va bu ataylab
      (05-05): jadval DALIL emas, HOSILA. `occupancy_events` va
      `zone_reviews` da esa trigger BOR — shuning uchun bu yerda ular
      TEGILMAYDI.
    """
    conn.execute("DELETE FROM stall_slot_occupancy WHERE market_id = %s", (str(market_id),))
    assert slot_rows(conn, market_id) == {}, "tozalash ishlamadi — keyingi assertlar ma'nosiz"


def slot_rows(
    conn: Connection[TupleRow], market_id: UUID, day: date = SEED_BUSINESS_DATE
) -> dict[tuple[UUID, time], tuple[str, str, UUID | None]]:
    """`(stall_id, slot_time) -> (verdict, resolution_source, winner)`."""
    rows = conn.execute(
        "SELECT stall_id, slot_time, verdict, resolution_source, winning_occupancy_event_id "
        "FROM stall_slot_occupancy WHERE market_id = %s AND business_date = %s",
        (str(market_id), day),
    ).fetchall()
    return {(row[0], row[1]): (row[2], row[3], row[4]) for row in rows}


def review_count(conn: Connection[TupleRow], market_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM zone_reviews WHERE market_id = %s", (str(market_id),)
    ).fetchone()
    assert row is not None
    return int(row[0])


def snapshot_slot_times(
    conn: Connection[TupleRow], market_id: UUID, day: date = SEED_BUSINESS_DATE
) -> set[time]:
    """Kunning slotlari — `snapshots` dan, AYNAN mahsulot yo'li ko'radigan manba."""
    rows = conn.execute(
        "SELECT DISTINCT slot_time FROM snapshots WHERE market_id = %s AND business_date = %s",
        (str(market_id), day),
    ).fetchall()
    return {row[0] for row in rows}


def event_slot_time(conn: Connection[TupleRow], event_id: UUID) -> time:
    row = conn.execute(
        "SELECT slot_time FROM occupancy_events WHERE id = %s", (str(event_id),)
    ).fetchone()
    assert row is not None, f"hodisa {event_id} topilmadi"
    slot: time = row[0]
    return slot


def answer_event(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    event_id: UUID,
    reviewer_id: UUID,
    human_verdict: str,
) -> None:
    """Hodisaga NOANIQ NAVBAT topshirig'i va INSON javobini yozadi.

    ⚠ `queue_kind = 'uncertain'` ATAYIN: ko'r audit topshirig'i
      `audit_round_id` ni TALAB qiladi (`blind_audit_needs_round`) va bu
      yordamchining vazifasi doira emas, INSON JAVOBI. `purpose` esa
      `train` — `eval` faqat ko'r auditdan kela oladi
      (`eval_needs_blind_audit`).
    """
    assignment_id = uuid4()
    conn.execute(
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
    conn.execute(
        _INSERT_REVIEW,
        (
            str(uuid4()),
            str(market_id),
            str(assignment_id),
            ReviewQueueKind.UNCERTAIN.value,
            True,
            human_verdict,
            str(reviewer_id),
            1500,
        ),
    )


async def close(
    sessionmaker: async_sessionmaker[AsyncSession], *, day: date = SEED_BUSINESS_DATE
) -> object:
    return await day_close(sessionmaker, business_date=day)


# ===========================================================================
# 1. AI-06 — TASDIQLANMAGAN `uncertain` -> `empty`, LEKIN ALOHIDA BELGI BILAN
# ===========================================================================


async def test_unreviewed_uncertain_defaults_to_empty(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Javobsiz `uncertain` -> `verdict='empty'`, `resolution_source='default_empty'`.

    ⛔ IKKI ASSERT ATAYIN AJRATILGAN. Faqat `verdict == 'empty'` ni
       tekshirish `resolution_source` ni `'ai'` deb yozadigan
       implementatsiyani ham o'tkazib yuborardi — va o'shanda hisobotda
       «ko'rilmagani uchun bo'sh» hisoblagichi ABADIY NOL bo'lib turardi:
       nosozlik «hammasi joyida» ko'rinishida bo'lardi.
    """
    clear_slots(sync_owner_conn, env.market_a)
    slot = event_slot_time(sync_owner_conn, _uncertain_event(env))

    await close(app_sessionmaker)

    verdict, source, winner = slot_rows(sync_owner_conn, env.market_a)[(env.uncertain_stall, slot)]

    assert verdict == OccupancyVerdict.EMPTY.value
    assert source == ResolutionSource.DEFAULT_EMPTY.value, (
        f"manba {source!r} — «hech kim qaramadi» belgisi yo'qoldi (D-19)"
    )
    assert winner is None


async def test_no_fake_review_row_is_written(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """⛔ `zone_reviews` qatorlari soni kun yopilishidan OLDIN va KEYIN TENG.

    Bu D-19 ning yagona mexanik o'lchovi. Soxta qator yozilsa tizim
    «nazoratchi buni bo'sh deb tasdiqladi» deb yolg'on gapirardi va
    o'sha yolg'on `purpose='train'` yorlig'i bo'lib trening datasetiga
    tushardi — ya'ni model o'zining JAVOB BERILMAGAN holatlarida «bo'sh»
    deb o'rganardi.

    ⚠ NAZORAT: shu yugurishda HAQIQATAN `default_empty` qatori tug'ilgani
      ham tekshiriladi. Usiz test hech nima qilmagan job bilan ham yashil
      bo'lardi.
    """
    clear_slots(sync_owner_conn, env.market_a)
    before = review_count(sync_owner_conn, env.market_a)

    await close(app_sessionmaker)

    after = review_count(sync_owner_conn, env.market_a)
    defaulted = [
        cell
        for cell, row in slot_rows(sync_owner_conn, env.market_a).items()
        if row[1] == ResolutionSource.DEFAULT_EMPTY.value
    ]

    assert defaulted, "nazorat: birorta `default_empty` qatori tug'ilmadi — test bo'sh yugurdi"
    assert after == before, (
        f"`zone_reviews` {before} -> {after}: kun yopilishi SOXTA javob yozdi (D-19)"
    )


async def test_default_empty_count_is_reported(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Beshala hisoblagich qaytadi — `default_empty` NOL bo'lganda HAM.

    ⛔ NOL — NATIJA, uning yo'qligi emas. Hisoblagich «bo'sh bo'lsa
       ko'rsatilmaydi» qilinsa, «bugun hammasi ko'rildi» bilan
       «hisoblagich umuman ishlamayapti» bir xil ko'rinardi.
    """
    clear_slots(sync_owner_conn, env.market_a)
    await close(app_sessionmaker)

    async with tenant_session(env.market_a) as session:
        with_default = await OccupancyRepository(session, env.market_a).day_summary(
            SEED_BUSINESS_DATE
        )

    assert with_default.default_empty > 0, "nazorat: seed'ning javobsiz `uncertain` i yo'qolgan"

    # ⚠ IKKINCHI YUGURISH — HODISASI BO'LMAGAN KUN. Beshala maydon HAMON
    #   qaytadi va hammasi nol; `stalls` esa 0, chunki o'sha kunda kadr
    #   olinmagan (`_DAY_SLOT_TIMES` docstringi).
    quiet_day = SEED_BUSINESS_DATE - timedelta(days=30)
    async with tenant_session(env.market_a) as session:
        quiet = await OccupancyRepository(session, env.market_a).day_summary(quiet_day)

    assert (
        quiet.occupied,
        quiet.empty,
        quiet.default_empty,
        quiet.no_coverage,
        quiet.human_confirmed,
        quiet.stalls,
    ) == (0, 0, 0, 0, 0, 0)


# ===========================================================================
# 2. D-22 — `no_coverage` HECH QACHON «BO'SH» EMAS
# ===========================================================================


async def test_no_coverage_is_not_counted_as_empty(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Qamrovsiz rasta ALOHIDA hisoblagichda va `empty` ga QO'SHILMAYDI.

    ⛔ UCH ASSERT UCH XIL NARSANI o'lchaydi va ular bir-birini
       ALMASHTIRMAYDI: qator YOZILADIMI, qiymati `no_coverage` MI, va
       hisoblagichlar ARALASHMAYDIMI.
    """
    clear_slots(sync_owner_conn, env.market_a)
    slots = snapshot_slot_times(sync_owner_conn, env.market_a)
    assert slots, "nazorat: seed kunida birorta kadr yo'q — qamrov to'ri qurilmasdi"

    await close(app_sessionmaker)

    rows = slot_rows(sync_owner_conn, env.market_a)
    uncovered = [rows[(env.uncovered_stall, slot)] for slot in slots]

    assert len(uncovered) == len(slots), "qamrovsiz rastaga qator YOZILMADI — u hisobotdan g'oyib"
    for verdict, source, winner in uncovered:
        assert verdict == ResolutionSource.NO_COVERAGE.value, (
            f"qamrovsiz rasta {verdict!r} deb yozildi — D-22 ning aynan taqiqi"
        )
        assert source == ResolutionSource.NO_COVERAGE.value
        assert winner is None

    async with tenant_session(env.market_a) as session:
        summary = await OccupancyRepository(session, env.market_a).day_summary(SEED_BUSINESS_DATE)

    assert summary.no_coverage >= 1
    assert (
        summary.occupied + summary.empty + summary.default_empty + summary.no_coverage
        == summary.stalls
    ), "to'rt bo'lak yig'indisi rasta soniga teng emas — biri ikkinchisiga qo'shilib ketgan"


async def test_the_grid_covers_every_captured_slot(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """⛔ MATERIALIZATSIYA `snapshots` NING BARCHA SLOTLARINI qamraydi.

    ⚠ DA'VO ALOHIDA TEST SIFATIDA YOZILGAN VA BU O'LCHANGAN ZARURIYAT:
      slotlar `occupancy_events` dan olinganda (sabotaj D) qamrov to'ri
      jimgina QISQARADI — birorta hisoblagich nolga tushmaydi, faqat
      kunning bir qismi hisobotdan G'OYIB bo'ladi. Boshqa testlar buni
      `KeyError` bilan ko'rsatardi, ya'ni SABAB emas, OQIBAT ko'rinardi.

    Farq mahsulotda ham aynan shunday: kamera qorong'i bo'lgan slotda
    hodisa YOZILMAYDI (05-08), ya'ni «hech kim ko'rmagan» slot
    o'lchovdan chiqib ketardi va `no_coverage` nol bo'lib turardi.
    """
    clear_slots(sync_owner_conn, env.market_a)
    captured = snapshot_slot_times(sync_owner_conn, env.market_a)

    await close(app_sessionmaker)

    materialized = {slot for _, slot in slot_rows(sync_owner_conn, env.market_a)}

    assert materialized == captured, (
        f"qamrov to'ri {sorted(captured - materialized)} slotini o'tkazib yubordi "
        "— kadr olingan slot HAR DOIM materializatsiyaga tushishi shart"
    )


async def test_a_slot_with_no_frames_is_absent_rather_than_empty(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Kadr olinmagan KUN uchun qator umuman yozilmaydi — «hammasi bo'sh» EMAS.

    ⚠ Bu D-22 ning ikkinchi yo'nalishi: mavjud kunning qamrovsiz rastasi
      `no_coverage` bo'ladi, mavjud BO'LMAGAN kun esa umuman qator
      bermaydi. Ikkalasini bir xil qilish (kunni «hamma rasta bo'sh» deb
      yozish) kelajakdagi har qanday kunni «yopilgan» ko'rsatardi.
    """
    quiet_day = SEED_BUSINESS_DATE - timedelta(days=30)
    assert snapshot_slot_times(sync_owner_conn, env.market_a, quiet_day) == set(), (
        "nazorat: tanlangan kunda kadr bor ekan — boshqa kun tanlansin"
    )

    await close(app_sessionmaker, day=quiet_day)

    assert slot_rows(sync_owner_conn, env.market_a, quiet_day) == {}


# ===========================================================================
# 3. AI-05 — KAMERALARARO AGREGATSIYA HAQIQIY QATORLAR USTIDA
# ===========================================================================


async def test_any_camera_occupied_wins(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Bir kamera «band» desa — rasta BAND, ikkinchisi javobsiz `uncertain` bo'lsa ham.

    ⚠ ZID QUTB ATAYIN TANLANGAN: ikkinchi zona AYNAN javobsiz
      `uncertain`, ya'ni u yolg'iz qolganda `default_empty` bo'lardi.
      Ikkala kamera ham «band» bo'lgan holat qoidani SINAMASDI.
    """
    clear_slots(sync_owner_conn, env.market_a)
    seeded = add_zone_with_event(
        sync_owner_conn,
        market_id=env.market_a,
        camera_id=env.second_camera_a,
        stall_id=env.uncertain_stall,
        snapshot_id=env.snapshot_a,
        verdict=OccupancyVerdict.OCCUPIED.value,
        confidence=HIGH_CONFIDENCE,
        center=(0.40, 0.62),
    )
    slot = event_slot_time(sync_owner_conn, seeded.event_id)

    await close(app_sessionmaker)

    verdict, source, winner = slot_rows(sync_owner_conn, env.market_a)[(env.uncertain_stall, slot)]

    assert verdict == OccupancyVerdict.OCCUPIED.value, (
        f"rasta {verdict!r} deb yozildi — «birortasi band desa band» buzilgan (D-20)"
    )
    assert source == ResolutionSource.AI.value
    assert winner == seeded.event_id, (
        "g'olib hodisa AYNAN band deb topilgan zonaniki bo'lishi shart"
    )


async def test_human_verdict_overrides_ai_for_that_zone(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Inson javobi O'SHA ZONANING AI javobini almashtiradi (D-12/D-15).

    ⛔ IKKI YO'NALISH HAM O'LCHANADI VA BU MAJBURIY: faqat «inson band
       dedi» ni sinash `resolution_source = 'human'` ni har doim yozadigan
       implementatsiyani ham o'tkazib yuborardi. Bu yerda inson AI ga ZID
       javob beradi (`occupied` -> `empty`), ya'ni natija AI dan
       chiqmasligi ISBOTLANADI.
    """
    clear_slots(sync_owner_conn, env.market_a)
    seeded = _new_stall_event(
        sync_owner_conn, env, verdict=OccupancyVerdict.OCCUPIED.value, confidence=HIGH_CONFIDENCE
    )
    answer_event(
        sync_owner_conn,
        market_id=env.market_a,
        event_id=seeded.event_id,
        reviewer_id=env.reviewer_id,
        human_verdict=OccupancyVerdict.EMPTY.value,
    )
    slot = event_slot_time(sync_owner_conn, seeded.event_id)

    await close(app_sessionmaker)

    verdict, source, winner = slot_rows(sync_owner_conn, env.market_a)[(seeded.stall_id, slot)]

    assert (verdict, source) == (OccupancyVerdict.EMPTY.value, ResolutionSource.HUMAN.value), (
        f"({verdict!r}, {source!r}) — AI javobi inson javobidan ustun chiqdi"
    )
    assert winner is None, "`occupied` bo'lmagan qatorda g'olib hodisa bo'lmasligi SHART"


async def test_a_blind_audit_answer_also_corrects_occupancy(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """D-15: ko'r audit javobi bandlikni HAM TUZATADI — faqat o'lchamaydi.

    Seed'dagi ko'r audit javobi (`blind_review_id`) `occupied` hodisaga
    `occupied` deb yozilgan, ya'ni u AI bilan MOS. Shunga qaramay manba
    `human` bo'lishi shart: `queue_kind` bo'yicha filtr qo'yilgan
    implementatsiya bu yerda `ai` yozardi va D-15 jimgina buzilardi.

    ⚠ NAVBAT TURI BO'YICHA FILTR FAQAT ANIQLIK HISOBOTIDA bor — ikki
      savol, ikki filtr.
    """
    clear_slots(sync_owner_conn, env.market_a)
    slot = event_slot_time(sync_owner_conn, env.occupancy.market_a.occupied_event_id)

    await close(app_sessionmaker)

    verdict, source, winner = slot_rows(sync_owner_conn, env.market_a)[(env.occupied_stall, slot)]

    assert verdict == OccupancyVerdict.OCCUPIED.value
    assert source == ResolutionSource.HUMAN.value, (
        f"manba {source!r} — ko'r audit javobi bandlikka YETIB BORMADI (D-15)"
    )
    assert winner == env.occupancy.market_a.occupied_event_id


# ===========================================================================
# 4. IDEMPOTENTLIK
# ===========================================================================


async def test_rerun_is_idempotent(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Ikkinchi yugurish qatorlar SONINI ham, QIYMATLARINI ham o'zgartirmaydi.

    ⚠ IKKALASI HAM TEKSHIRILADI: faqat sonni sanash `DO UPDATE` ni
      `verdict = 'empty'` yozadigan holatda ham yashil qolardi.
    """
    clear_slots(sync_owner_conn, env.market_a)

    await close(app_sessionmaker)
    first = slot_rows(sync_owner_conn, env.market_a)
    assert first, "nazorat: birinchi yugurish birorta qator yozmadi"

    await close(app_sessionmaker)
    second = slot_rows(sync_owner_conn, env.market_a)

    assert second == first, (
        "qayta hisoblash natijani o'zgartirdi — materializatsiya idempotent emas"
    )


async def test_a_later_human_answer_reaches_a_closed_day(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """⚠ IDEMPOTENTLIK «MUZLATISH» EMAS — kechikkan inson javobi YETIB BORADI.

    `ON CONFLICT DO NOTHING` bo'lganda bu test qizarardi va aynan shu
    sababdan `DO UPDATE` tanlangan: nazoratchi kechagi bandga bugun javob
    yozsa, kunning materializatsiyasi o'sha javobni AKS ETTIRISHI shart
    (D-15). Aks holda birinchi hisob MANGU qolardi.
    """
    clear_slots(sync_owner_conn, env.market_a)
    seeded = _new_stall_event(
        sync_owner_conn, env, verdict=OccupancyVerdict.UNCERTAIN.value, confidence=CONFIDENCE_0_55
    )
    slot = event_slot_time(sync_owner_conn, seeded.event_id)

    await close(app_sessionmaker)
    before = slot_rows(sync_owner_conn, env.market_a)[(seeded.stall_id, slot)]
    assert before[:2] == (OccupancyVerdict.EMPTY.value, ResolutionSource.DEFAULT_EMPTY.value)

    answer_event(
        sync_owner_conn,
        market_id=env.market_a,
        event_id=seeded.event_id,
        reviewer_id=env.reviewer_id,
        human_verdict=OccupancyVerdict.OCCUPIED.value,
    )
    await close(app_sessionmaker)

    verdict, source, winner = slot_rows(sync_owner_conn, env.market_a)[(seeded.stall_id, slot)]

    assert (verdict, source) == (OccupancyVerdict.OCCUPIED.value, ResolutionSource.HUMAN.value)
    assert winner == seeded.event_id


# ===========================================================================
# 5. TRANZITIV BILLING KAFOLATI (D-21)
# ===========================================================================


def test_winning_event_is_null_when_not_occupied(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """`verdict <> 'occupied'` bo'lgan qatorda g'olib hodisa BO'LA OLMAYDI.

    Ikkala yo'nalish ham `CHECK ((verdict='occupied') =
    (winning_occupancy_event_id IS NOT NULL))` bilan yopilgan, ya'ni
    ikkalasi ham o'lchanadi.
    """
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_slot_row(
            sync_owner_conn,
            env,
            verdict=OccupancyVerdict.EMPTY.value,
            source=ResolutionSource.AI.value,
            winner=env.occupancy.market_a.occupied_event_id,
        )

    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_slot_row(
            sync_owner_conn,
            env,
            verdict=OccupancyVerdict.OCCUPIED.value,
            source=ResolutionSource.AI.value,
            winner=None,
        )


def test_invalid_frame_cannot_reach_stall_slot_occupancy(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """⛔ KAFOLAT TRANZITIV — VA ZANJIRNING IKKALA HALQASI HAM O'LCHANADI.

        stall_slot_occupancy -> occupancy_events -> snapshots (id, is_billable)

    ⚠ FAQAT BIRINCHI HALQANI SINASH DA'VONI KUCHAYTIRIB YUBORARDI:
      «mavjud bo'lmagan hodisaga havola rad etiladi» degan gap
      «yaroqsiz kadr hisobga kira olmaydi» degani EMAS. Ikkinchi halqa —
      yaroqsiz kadrga hodisa YOZIB BO'LMASLIGI — shu yerda NAZORAT
      sifatida qayta o'lchanadi, chunki aynan u birinchisini MA'NOLI
      qiladi.
    """
    # 1-halqa: `stall_slot_occupancy` mavjud bo'lmagan hodisaga tayana olmaydi.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert_slot_row(
            sync_owner_conn,
            env,
            verdict=OccupancyVerdict.OCCUPIED.value,
            source=ResolutionSource.AI.value,
            winner=uuid4(),
        )

    # 2-halqa (NAZORAT): yaroqsiz kadrga bandlik hodisasi umuman yozilmaydi.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        add_zone_with_event(
            sync_owner_conn,
            market_id=env.market_a,
            camera_id=env.camera_a,
            stall_id=env.uncovered_stall,
            snapshot_id=env.dark_snapshot_a,
            verdict=OccupancyVerdict.OCCUPIED.value,
            confidence=HIGH_CONFIDENCE,
            center=(0.20, 0.20),
        )


# ===========================================================================
# 6. TENANT CHEGARASI VA YURAK URISHI
# ===========================================================================


async def test_the_close_stays_inside_each_market(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Har bozorning qatorlari FAQAT o'z rastalariga tegishli.

    ⚠ Job IKKALA bozorni ham yopadi (`active_market_ids()`), ya'ni
      «B bozorida qator yo'q» degan assert YOLG'ON bo'lardi. O'lchanadigan
      da'vo — A ning qatorida B ning rastasi UCHRAMASLIGI.
    """
    clear_slots(sync_owner_conn, env.market_a)
    clear_slots(sync_owner_conn, env.market_b)

    await close(app_sessionmaker)

    a_stalls = {stall_id for stall_id, _ in slot_rows(sync_owner_conn, env.market_a)}
    b_stalls = {stall_id for stall_id, _ in slot_rows(sync_owner_conn, env.market_b)}

    assert a_stalls, "A bozorining kuni yopilmadi"
    assert b_stalls, "B bozorining kuni yopilmadi — job bir bozorda to'xtab qolgan"
    assert a_stalls & b_stalls == set(), "bozorlar rastalari aralashib ketgan"


async def test_the_run_leaves_a_heartbeat(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    env: Env,
) -> None:
    """Yugurishning YAGONA tashqi izi — `system_heartbeats['day_close']`.

    ⚠ `detail` da FAQAT SANOQLAR: `system_heartbeats` GLOBAL jadval
      (RLS yo'q), ya'ni unga yozilgan `market_id`/`stall_id` hamma uchun
      ko'rinadigan joyda qolardi (05-08 ning qarori).
    """
    clear_slots(sync_owner_conn, env.market_a)
    await close(app_sessionmaker)

    row = sync_owner_conn.execute(
        "SELECT detail FROM system_heartbeats WHERE component = %s", (DAY_CLOSE_COMPONENT,)
    ).fetchone()

    assert row is not None, "yurak urishi yozilmadi"
    detail = row[0]
    assert detail["slots"] > 0
    assert detail["errors"] == 0
    for leaky in ("market_id", "stall_id", "event_id"):
        assert leaky not in detail, f"global jadvalga `{leaky}` yozilgan"


# ===========================================================================
# Ichki yordamchilar
# ===========================================================================


def _uncertain_event(env: Env) -> UUID:
    event_id = env.occupancy.market_a.uncertain_event_id
    assert event_id is not None, "nazorat: seed'da `uncertain` hodisa yo'q"
    return event_id


def _new_stall_event(
    conn: Connection[TupleRow], env: Env, *, verdict: str, confidence: str
) -> SeededEvent:
    """Qamrovsiz rastaga YANGI zona + hodisa qo'shadi.

    ⚠ `uncovered_stall` TANLANADI: uning boshqa zonasi yo'q, ya'ni
      rastaning javobi AYNAN shu zonadan chiqadi va test agregatsiya
      bilan hosila o'rtasidagi farqni ADASHTIRMAYDI.
    """
    return add_zone_with_event(
        conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=env.uncovered_stall,
        snapshot_id=env.snapshot_a,
        verdict=verdict,
        confidence=confidence,
        center=(0.18, 0.72),
    )


def _insert_slot_row(
    conn: Connection[TupleRow],
    env: Env,
    *,
    verdict: str,
    source: str,
    winner: UUID | None,
) -> None:
    """`stall_slot_occupancy` ga XOM qator — sxema qo'riqchilarini o'lchash uchun."""
    conn.execute(
        "INSERT INTO stall_slot_occupancy "
        "(id, market_id, stall_id, business_date, slot_time, verdict, "
        " resolution_source, winning_occupancy_event_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            str(uuid4()),
            str(env.market_a),
            str(env.uncovered_stall),
            SEED_BUSINESS_DATE,
            time(23, 45),
            verdict,
            source,
            None if winner is None else str(winner),
        ),
    )
