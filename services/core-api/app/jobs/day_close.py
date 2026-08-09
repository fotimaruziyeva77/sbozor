"""Kun yopilishi — rasta darajasidagi hukmning materializatsiyasi (AI-05, AI-06).

=============================================================================
⛔⛔ AI-06 HISOBLANADI, YOZILMAYDI — VA BU BUTUN MODULNING ASOSI (D-19).

Kun oxirigacha tasdiqlanmagan `uncertain` «bo'sh» bo'ladi. Bu job
`zone_reviews` ga SOXTA QATOR YOZMAYDI va bunday yo'l bu faylda umuman
mavjud emas.

Yozilsa nima bo'lardi (va nega bu shunchaki «tozalik» emas):

  1. tizim «nazoratchi buni bo'sh deb tasdiqladi» deb YOLG'ON gapirardi;
  2. o'sha yolg'on `purpose = 'train'` yorlig'i bo'lib trening
     datasetiga tushardi, ya'ni model O'ZINING javob berilmagan
     holatlarida «bo'sh» deb o'rganardi — nosozlik o'z-o'zini
     mustahkamlardi;
  3. `zone_reviews` — `AUDITED_TABLES` da, ya'ni yolg'on audit jurnaliga
     ham kirardi.

O'rniga hukm `stall_slot_occupancy.resolution_source = 'default_empty'`
bo'lib YOZILADI va u HISOBLAGICH bo'lib ko'rinadi.

⚠⚠ XAVF YO'NALISHI: standart «bo'sh» -> patta YOZILMAYDI, ya'ni xato
   ORTIQCHA HISOB emas, JIMGINA YO'QOTISH. Shuning uchun chora
   «billing'ga kirib ketmasin» EMAS (u allaqachon kirmaydi), balki
   «KO'RINMAY QOLMASIN»: hisoblagich NOL bo'lganda ham qaytariladi
   (`occupancy_repo._DAY_SUMMARY`).
=============================================================================

⛔ AGREGATSIYA QOIDASI BU FAYLDA YO'Q — u `sbozor_core.occupancy` da
   (§D.11). Bu modul XOM qatorlarni sof funksiyaga BERADI va natijani
   yozadi. Qoidani shu yerga ko'chirish uni haqiqiy bazasiz sinab
   bo'lmaydigan qilardi va 120 holatli jadval testi yo'qolardi.

⛔ IKKINCHI DARAJA (slotlararo, «kamida 2 slotda band») BU YERDA HAM
   YO'Q — u BILL-01, 6-faza. Bu job kun uchun HAR SLOTNING qatorini
   yozadi va ularni birlashtirmaydi.

=============================================================================
⚠ HAR BOZOR UCHUN ALOHIDA TRANZAKSIYA (§S-5, `discovery.py:170-205`).
  Bitta tranzaksiyada ikki bozor — tenant sizib chiqishining eng qisqa
  yo'li; qolaversa bitta bozordagi nosozlik qolganlarining kunini ham
  yopilmagan qoldirardi.

⚠ JOB HECH QACHON YIQILMAYDI (`retention_daily` qoidasi): bitta
  bozorning xatosi yutiladi va `DayCloseResult.errors` ga TURI bilan
  yoziladi. Kun yopilishi KONVERGENT vazifa — ertangi yugurish o'sha
  kunni qayta hisoblay oladi (`day_close(business_date=...)`), ya'ni
  yo'qotish yo'q.

⚠ `taskiq` IMPORT QILINMAYDI (S-4, D-06) — bu modul sof `async def`.
=============================================================================

=============================================================================
BOZORLAR RO'YXATI `active_market_ids()` DAN, `occupancy_day_close_
markets()` DAN EMAS — VA BU REJADAN OG'ISH (deviatsiya, SUMMARY da).

`0018` ning `SECURITY DEFINER` funksiyasi kunni `now()` DAN oladi:

    AND e.business_date = ((now() AT TIME ZONE 'Asia/Tashkent')::date)

Bu job esa `business_date` ni ARGUMENT sifatida oladi
(`retention_daily(today=...)` da o'rnatilgan qoida: mahsulot yo'li
`business_today()` beradi, test esa AYNAN o'sha funksiyani boshqa kun
bilan chaqiradi). Ya'ni funksiyaning `event_count` ustuni har qanday
BOSHQA kun uchun NOTO'G'RI son bo'lardi — u xato bermasdi, faqat
mahsulot yo'lida jimgina chalg'itardi.

Bozorlar TO'PLAMI esa ikkalasida ham AYNAN bir xil (`WHERE m.is_active`),
ya'ni `active_market_ids()` hech nima yo'qotmaydi va u `alert_sweep`,
`retention_daily` hamda `audit_draw` ishlatadigan YAGONA RLS-chetlab
o'tuvchi yuza — yangi xavfsizlik yuzasi ochilmaydi.
=============================================================================
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import structlog
from sbozor_core.enums import ActorKind, OccupancyVerdict, ResolutionSource
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.occupancy import aggregate_stall_slot, effective_verdict
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.retention import active_market_ids
from app.repositories.occupancy_repo import OccupancyRepository, SlotRow, ZoneOutcome

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from datetime import date, time
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = structlog.get_logger(__name__)

__all__ = [
    "DAY_CLOSE_COMPONENT",
    "DayCloseResult",
    "day_close",
]


_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
_DEFAULT_EMPTY: Final[str] = ResolutionSource.DEFAULT_EMPTY.value
_NO_COVERAGE: Final[str] = ResolutionSource.NO_COVERAGE.value
"""Uchala qiymat ham ENUM DAN hosila — sanoq literalga tayanmaydi.

Hisoblagichlar shu satrlar bo'yicha filtrlanadi; literal yozilganda enum
o'zgargan kuni `default_empty` sanog'i JIMGINA nolga tushardi va D-19
ning yagona signali xatosiz yo'qolardi.
"""

DAY_CLOSE_COMPONENT: str = "day_close"
"""`system_heartbeats.component` — yugurishning YAGONA tashqi izi.

`retention.py::RETENTION_COMPONENT` bilan bir xil qoida va bir xil
sabab: satr ikki joyda literal yozilsa (bu yerda va kuzatuvda) ular bir
kun jimgina ajralib ketardi.
"""


@dataclass(slots=True)
class DayCloseResult:
    """Bitta yugurishning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`RetentionResult` qoidasi).
    """

    markets: int = 0
    slots: int = 0
    """Materializatsiya qilingan (rasta x slot) qatorlari soni."""
    stalls: int = 0
    """Qamralgan faol rastalar soni (bozorlar bo'yicha yig'indi)."""
    default_empty: int = 0
    """⛔ «Ko'rilmagani uchun bo'sh» SLOT qatorlari — D-19 ning izi.

    ⚠ Bu SLOT darajasidagi son, `day_summary().default_empty` esa RASTA
      darajasida. Ikkalasi teng bo'lishi SHART EMAS va ularni
      solishtirish xato bo'lardi: bir rasta bir kunda yetti slotga ega.
    """
    no_coverage: int = 0
    errors: list[str] = field(default_factory=list)


async def day_close(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
) -> DayCloseResult:
    """Har faol bozor uchun kunning rasta-slot hukmini materializatsiya qiladi.

    Args:
        business_date: qaysi kun yopiladi (`Asia/Tashkent`). ARGUMENT —
            modul docstringidagi bozorlar ro'yxati bandi.

    Returns:
        `DayCloseResult` — sonlar va YUTILGAN xatolarning TURLARI
        (matnlari EMAS: istisno matni ombor manzilini yoki obyekt
        kalitini tashishi mumkin, `retention.py::_swallow` qoidasi).
    """
    request_id = f"job-day-close-{business_date.isoformat()}"
    result = DayCloseResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Yugurish BOSHLANA olmadi. Iz jurnalda qoladi; kun yopilishi
        # KONVERGENT, ya'ni o'sha kunni keyin qayta hisoblash mumkin.
        log.exception("day_close_market_list_failed")
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _close_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                business_date=business_date,
                result=result,
            )
        except SQLAlchemyError as exc:
            result.errors.append(f"day_close_failed:{type(exc).__name__}")
            log.warning("day_close_failed", market_id=str(market_id), error=type(exc).__name__)

    await _write_heartbeat(sessionmaker, result)
    log.info(
        "day_close_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        stalls=result.stalls,
        slots=result.slots,
        default_empty=result.default_empty,
        no_coverage=result.no_coverage,
        errors=len(result.errors),
    )
    return result


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """`discovery.py::_system_transaction()` ning shu moduldagi jufti.

    ⚠ NUSXA EMAS, JUFT (`retention.py::_tenant_session` docstringi):
      import yo'nalishi ikki mustaqil jobni bir-biriga bog'lardi.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`audit_draw.py:466`).
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


async def _close_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    business_date: date,
    result: DayCloseResult,
) -> None:
    """Bitta bozorning kunini yopadi — O'QISH VA YOZISH BIR tranzaksiyada.

    ⚠ BO'LINMAYDI VA SABAB `audit_draw._draw_for_market` NIKIDAN FARQ
      QILADI: bu yerda poyga emas, IZCHILLIK muhim. Zona hodisalarini
      o'qib bo'lgach nazoratchi javob yozsa, ikkinchi tranzaksiya o'sha
      javobni ko'rmagan hukmni yozardi — va u keyingi yugurishgacha
      qolardi. Bitta tranzaksiya oynani yopadi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        repo = OccupancyRepository(session, market_id)

        stall_ids = await repo.active_stall_ids()
        slot_times = await repo.day_slot_times(business_date)
        outcomes = await repo.zone_outcomes(business_date)

        rows = _slot_rows(stall_ids=stall_ids, slot_times=slot_times, outcomes=outcomes)
        await repo.materialize(business_date, rows)

    result.stalls += len(stall_ids)
    result.slots += len(rows)
    result.default_empty += sum(1 for row in rows if row.resolution_source == _DEFAULT_EMPTY)
    result.no_coverage += sum(1 for row in rows if row.resolution_source == _NO_COVERAGE)


def _slot_rows(
    *,
    stall_ids: Sequence[UUID],
    slot_times: Sequence[time],
    outcomes: Sequence[ZoneOutcome],
) -> list[SlotRow]:
    """(rasta x slot) TO'LIQ to'rini quradi — qamrovsizlari BILAN BIRGA.

    =======================================================================
    ⛔ TO'R TO'LIQ VA BU D-22 NING MATERIALIZATSIYASI.

    Faqat hodisasi bor juftliklarni yozish arzonroq bo'lardi va aynan
    o'sha «arzonlik» qamrovsiz rastani hisobotdan G'OYIB qilardi:
    `no_coverage` hisoblagichi nol bo'lib turardi va direktor birorta
    kamera ko'rmaydigan rastalar borligini BILMASDI. `0018` ning
    `occupancy_day_close_markets()` docstringi ham aynan shu sababdan
    «hodisasi bor bozorlar» filtrini rad etgan (05-05, deviatsiya #8).

    ⚠ HAJM: 1000 rasta x 7 slot = kuniga 7000 qator. Bu ONGLI narx —
      `no_coverage` ni MATERIALIZATSIYA QILISH uni AUDIT QILINADIGAN
      faktga aylantiradi. Muqobili («qator yo'q = qamrov yo'q») «kun
      hali yopilmagan» bilan «kamera ko'rmaydi» ni bir xil ko'rsatardi.
    =======================================================================

    ⚠ G'OLIB ZONA `aggregate_stall_slot()` NING CHIQISHIDAN topiladi
      (`.index(...)`), qayta hisoblanmaydi: «birinchi band zonani ol»
      degan ikkinchi qoida sof funksiyaning tenglik buzish tartibidan
      ajralib ketishi mumkin bo'lardi.
    """
    by_cell: dict[tuple[UUID, time], list[ZoneOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_cell[(outcome.stall_id, outcome.slot_time)].append(outcome)

    rows: list[SlotRow] = []
    for stall_id in stall_ids:
        for slot_time in slot_times:
            cell = by_cell.get((stall_id, slot_time), [])
            pairs = [effective_verdict(o.event_verdict, o.review_verdict) for o in cell]
            verdict, source = aggregate_stall_slot(pairs)

            winner: UUID | None = None
            if verdict == _OCCUPIED:
                winner = cell[pairs.index((verdict, source))].event_id

            rows.append(
                SlotRow(
                    stall_id=stall_id,
                    slot_time=slot_time,
                    verdict=verdict,
                    resolution_source=source,
                    winning_occupancy_event_id=winner,
                )
            )
    return rows


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], result: DayCloseResult
) -> None:
    """`system_heartbeats['day_close']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ XATO YUTILADI (`retention.py::_write_heartbeat` bilan aynan bir xil
      qoida): bu yozuv PROGRESS ko'rsatkichi, yugurishning natijasi EMAS.

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, ya'ni
      `detail` ga faqat SANOQLAR yoziladi (05-08 ning qarori:
      `market_id`/`stall_id` hamma uchun ko'rinadigan joyda qolardi).
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=DAY_CLOSE_COMPONENT,
                detail={
                    "markets": result.markets,
                    "stalls": result.stalls,
                    "slots": result.slots,
                    "default_empty": result.default_empty,
                    "no_coverage": result.no_coverage,
                    "errors": len(result.errors),
                },
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    set_={"last_seen_at": func.now(), "detail": statement.excluded.detail},
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi jobni yiqita olmaydi
        log.warning("day_close_heartbeat_not_written", error=type(exc).__name__)
