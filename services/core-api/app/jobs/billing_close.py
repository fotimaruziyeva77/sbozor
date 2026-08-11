"""Kun yopilishining PUL yarmi — kunlik patta hisobi (BILL-01, BILL-02, BILL-04).

=============================================================================
1. KUN — ARGUMENT, `now()` DAN OLINMAYDI (D-12).

`retention_daily(today=...)` va `day_close(business_date=...)` da
o'rnatilgan qoidaning uchinchi takrori: mahsulot yo'lida kunni QOBIQ
(`worker.py::billing_close_task`) hisoblaydi, test esa AYNAN o'sha
funksiyani BOSHQA kun bilan chaqiradi. Job ichida `business_today()`
chaqirilsa «qaysi kun yopildi?» savoli testda ikkinchi manbaga ega
bo'lardi va o'tmishdagi kunni qayta hisoblash yo'li UMUMAN bo'lmasdi.

=============================================================================
2. CRON `occupancy.day_close` DAN KEYIN — VA BU O'LCHANGAN, USLUBIY EMAS (C-3).

`stall_slot_occupancy` ning YAGONA yozuvchisi — `occupancy_repo.
materialize()`, uni esa faqat `day_close` chaqiradi va u D kuni uchun
D + 1 ning 03:40 da yuguradi (`worker.py::DAY_CLOSE_CRON`). Ya'ni D
kunining kechqurunida (20:30) slot jadvalida o'sha kun uchun ⛔ NOL qator
bor: `billable_stalls()` bo'sh ro'yxat qaytarardi, job HECH NIMA yozmasdi
va ⛔ XATO HAM BERMASDI. Sukunat «hammasi joyida» bilan bir xil ko'rinardi.

Shuning uchun `BILLING_CLOSE_CRON = "10 4 * * *"` va qobiq KECHAGI kunni
yopadi.

⚠ TARTIB KAFOLATI CRON JADVALIGA TAYANMAYDI. Bu job bandlikka faqat
  O'QISH uchun tegadi va IDEMPOTENT — noto'g'ri tartibda yugursa ham
  qayta yugurish tuzatadi (`DAY_CLOSE_CRON` ning «KONVERGENT» bandi).
  Cron satri faqat NARXNI kamaytiradi, KAFOLATNI emas.

⚠ SUKUNAT ENDI AJRALADI: slot qatori umuman bo'lmagan rasta
  `no_slot_rows` ga sanaladi (Pitfall 2), «ko'rdik, lekin band emas»
  esa `skipped_unbilled` ga. Ikkisini bitta songa siqish yuqoridagi jim
  nosozlikni qaytarardi.

=============================================================================
3. IDEMPOTENTLIK — `ON CONFLICT DO NOTHING`, QAYTA YUGURISH HISOBGA TEGMAYDI.

`daily_charges` ning idempotentlik kaliti `(market_id, stall_id,
service_date)` va `write_charge()` konfliktda `None` qaytaradi (D-06).
Yozilgan hisob O'ZGARMAS (D-07): `0020` unga `UPDATE`/`DELETE` triggerini
ulaydi, ya'ni «tuzatish» faqat `charge_adjustments` orqali mumkin.

⚠ QAYTA YUGURISH NORMAL HOLAT, tiklanish amali EMAS: nazoratchi kechagi
  bandga bugun javob yozsa `day_close` qayta yuguradi va shu job ham
  qayta chaqiriladi.

=============================================================================
4. `market_is_open()` TENANT KONTEKSTI OSTIDA — KONTEKSTSIZ HAMMA KUN YOPIQ.

Funksiya ATAYIN `SECURITY DEFINER` EMAS va fail-closed
(`migrations/entities/functions.py`): `set_tenant_context()` o'rnatilmagan
sessiyada RLS unga 0 qator ko'rsatadi va u HAR KUNNI yopiq deb qaytaradi.
O'shanda bu job birorta hisob yozmasdi va nosozlik faqat oyning oxirida,
tushum nolga tushganda ko'rinardi.

⛔ SHUNING UCHUN HAR BOZORNING ISHI `_tenant_session()` ICHIDA. Kontekst
   yo'qolganda xato CHIQMAYDI — hisobot jimgina bo'shaydi. Sabotaj
   `tests/integration/test_billing_close.py` da o'lchangan.

=============================================================================
5. KECH KELGAN TASDIQ — YO'Q HISOBNI YARATADI, MAVJUDINI BEKOR QILMAYDI.

Uch band, uchalasi ham ALOHIDA xulq (`06-RESEARCH.md` Pitfall 5):

  * qayta yugurish YO'Q hisobni YARATADI — nazoratchi «band» deb
    tasdiqlagach rasta hisob shartiga yetadi va D-06 kaliti uni bir marta
    yozadi;
  * mavjud hisobni BEKOR QILA OLMAYDI — `daily_charges` o'zgarmas (D-07);
  * kamaytirish FAQAT `charge_adjustments` orqali —
    `direction = 'decrease'`, `reason_code = 'late_review'`,
    `actor_user_id = NULL` (tizim).

⛔ BU SHOX BILL-02 NING YAGONA PRODUCER'I. 6-fazada `charge_adjustments`
   ga yozadigan birorta marshrut yoki UI yuzasi YO'Q (UI-SPEC §11.3 uni
   faqat O'QIYDI), ya'ni producer'siz mexanizm test ichida qolardi va
   «ishlab turgan yo'l» bo'lmasdi.

⚠ AUDIT QATORI DB-TRIGGERIDAN KELADI (`charge_adjustments`
  `BILLING_AUDITED_TABLES` da) — `write_app_audit()` bu faylda
  CHAQIRILMAYDI va u DUBLIKAT bo'lardi.

=============================================================================
⚠ HAR BOZOR UCHUN ALOHIDA TRANZAKSIYA (`day_close.py` ning qoidasi):
  bitta tranzaksiyada ikki bozor — tenant sizib chiqishining eng qisqa
  yo'li; qolaversa bitta bozordagi nosozlik qolganlarining kunini ham
  yopilmagan qoldirardi.

⚠ JOB HECH QACHON YIQILMAYDI va HECH BIR SHOX `raise` QILMAYDI (mahsulot
  qoidasi #5, D-14): bitta bozorning xatosi YUTILADI va
  `BillingCloseResult.errors` ga TURI bilan yoziladi.

⚠ `taskiq` IMPORT QILINMAYDI (S-4, D-06) — bu modul sof `async def`.

⚠ PUL MANTIG'I BU YERDA YO'Q: hisob sharti, summa va yozish
  `app/repositories/billing_repo.py` (06-06) dan CHAQIRILADI. Bu modul
  faqat TARTIBNI va HISOBLAGICHLARNI biladi.
=============================================================================
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import structlog
from sbozor_core.enums import ActorKind, AnomalyKind, OccupancyVerdict
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import Date, bindparam, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.retention import active_market_ids
from app.repositories.billing_repo import (
    ExistingCharge,
    billable_stalls,
    event_snapshots,
    market_day_charges,
    resolve_stall_day_money,
    write_anomaly,
    write_charge,
    write_evidence,
    write_late_review_adjustment,
)
from app.repositories.occupancy_repo import OccupancyRepository

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.billing_repo import SlotEvidenceRow, StallDayMoney, StallSlotVerdict

log = structlog.get_logger(__name__)

__all__ = [
    "BILLING_CLOSE_COMPONENT",
    "BillingCloseResult",
    "billing_close",
]

_UUID = PgUuid(as_uuid=True)
_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
"""Qiymat ENUM DAN — `day_close.py:111-119` da o'rnatilgan qoida."""

BILLING_CLOSE_COMPONENT: str = "billing_close"
"""`system_heartbeats.component` — yugurishning YAGONA tashqi izi.

⛔⛔ SATR UCH JOYDA O'QILADI VA UCHALASI HAM SHU KONSTANTANI IMPORT
   QILADI: bu modul uni YOZADI, `app/jobs/alerting.py` uning eskirganini
   o'lchaydi (`billing_close_stale`), `app/api/internal/self_check.py`
   esa uning UMUMAN yozilmaganini ko'rsatadi (`never_seen`).

`RETENTION_COMPONENT` / `DAY_CLOSE_COMPONENT` bilan bir xil qoida va bir
xil sabab: qo'lda yozilgan literal bir kun jimgina ajralib ketardi va
«cron ro'yxatga olinmagan» holati HECH QACHON ko'rinmasdi — xato yo'q,
jurnal yozuvi yo'q, faqat sukunat.
"""

_MARKET_IS_OPEN = text(
    "SELECT market_is_open(:market_id, :business_date) AS market_open"
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
)
"""Kalendar javobi — ⛔ DB FUNKSIYASI, ilova qatlamida QAYTA HISOBLANMAYDI.

Haftalik jadval + istisno qatori mantig'i `market_is_open()` da yashaydi
(2-faza) va uni bu yerda takrorlash IKKINCHI HAQIQAT MANBAI bo'lardi:
direktor kalendar sahifasida bitta javob, patta hisobida boshqasini
ko'rardi va ikkalasi ham «to'g'ri» bo'lardi.

⛔ CHAQIRUV `_tenant_session()` ICHIDA (fayl docstringining 4-bandi):
   funksiya INVOKER va fail-closed.
"""


@dataclass(slots=True)
class BillingCloseResult:
    """Bitta yugurishning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`DayCloseResult` qoidasi):
    HAMMA maydon HAR DOIM qaytariladi. Chaqiruvchi «nega hisob yo'q?»
    savoliga javobni YONIDA topadi va ikkinchi so'rov yubormaydi.
    """

    markets: int = 0
    charged: int = 0
    """YANGI yozilgan `daily_charges` qatorlari soni."""
    skipped_existing: int = 0
    """Hisob ALLAQACHON bor edi (D-06 kaliti konfliktga urildi)."""
    skipped_unbilled: int = 0
    """⛔ «KO'RDIK, LEKIN BAND EMAS» — slot qatorlari BOR, D-04 sharti bajarilmadi.

    ⚠ `no_slot_rows` DAN AJRALGAN va bu farq BUTUN Pitfall 2 NING
      MAZMUNI: bu son «job ishladi va rasta hisobga tushmadi» degani,
      qo'shnisi esa «biz umuman ko'rmadik». Ikkisi bitta songa siqilsa
      `day_close` dan OLDIN yugurgan job «hamma rasta bo'sh» degan YOLG'ON
      hisobot berardi va u to'g'ri hisobotdan MEXANIK ravishda
      ajralmasdi.
    """
    no_slot_rows: int = 0
    """⛔ MATERIALIZATSIYA QILINMAGAN faol rastalar soni (Pitfall 2, C-3).

    ⚠ MAXRAJ — `OccupancyRepository.active_stall_ids()`, ya'ni AYNAN
      `day_close` materializatsiya qiladigan to'plam. Bozorning BARCHA
      rastalari olinsa `closed`/`maintenance` rastalar HAR KUNI shu
      sanoqqa tushardi (ular ATAYIN materializatsiya qilinmaydi,
      `_ACTIVE_STALL_IDS` docstringi) va Pitfall 2 ning signali doimiy
      shovqinga aylanardi.
    """
    anomalies_unassigned: int = 0
    """`unassigned_occupied` — band, lekin sotuvchi biriktirilmagan (D-28)."""
    anomalies_closed_day: int = 0
    """`closed_day_occupied` — yopiq kunda savdo ko'rindi (D-10)."""
    anomalies_no_coverage: int = 0
    """`no_coverage_stall` — ⛔ BILL-04 ANOMALIYASI EMAS (D-05).

    Uchala sanoq ALOHIDA va ular HECH QACHON qo'shilmaydi (C-12): «ko'ra
    olmadik» ni «band, lekin to'lovsiz» ga qo'shish KO'R NUQTADAN TUSHUM
    DA'VOSI TO'QISH bo'lardi.
    """
    resolved_without_reviewer: int = 0
    """⛔ D-14 NING O'LCHANADIGAN MIQDORI — nazoratchisiz yozilgan hisoblar.

    Noaniqlik kunni BLOKLAMAYDI, lekin nechta rasta odam ko'zisiz hal
    qilinganini YASHIRMAYDI ham. Son yozilgan hisoblarga tegishli:
    `human_confirmed_occupied` bo'lmagan HAR yangi hisob shu yerga
    sanaladi.
    """
    adjustments_late_review: int = 0
    """Kech kelgan tasdiq uchun yozilgan `charge_adjustments` qatorlari."""
    errors: list[str] = field(default_factory=list)
    """⛔ XATO MATNI EMAS, TURI (S-1): istisno matni ombor manzilini yoki
    obyekt kalitini tashishi mumkin (`retention.py::_swallow` qoidasi).

    ⚠ ISTISNO: `billing_close_tariff_missing:<stall_code>` — bu yerda kod
      ATAYIN yoziladi. `stall_code` sir emas, ombor manzili emas va
      ma'muriyat uni tuzatishi uchun QAYSI rasta ekanini bilishi SHART.
      Bu holat `skipped_unbilled` ga TUSHMAYDI: rasta band edi va hisob
      YOZILISHI kerak edi — u jimgina yutilsa tushum yo'qolardi.
    """


async def billing_close(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
) -> BillingCloseResult:
    """Har faol bozor uchun kunning patta hisobini yozadi.

    Args:
        business_date: qaysi kun yopiladi (`Asia/Tashkent`). ⛔ ARGUMENT —
            fayl docstringining 1-bandi.

    Returns:
        `BillingCloseResult` — sonlar va YUTILGAN xatolarning TURLARI.
    """
    request_id = f"job-billing-close-{business_date.isoformat()}"
    result = BillingCloseResult()

    try:
        # ⛔ D-15: bozorlar ro'yxatining YAGONA RLS-chetlab o'tuvchi yuzasi.
        #   Yangi `SECURITY DEFINER` funksiya QO'SHILMAYDI va mavjudlaridan
        #   boshqasi ishlatilmaydi — yuza AYNAN BITTA chaqiruv nuqtasida
        #   qolishi kerak (`retention.py::active_market_ids` docstringi).
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Yugurish BOSHLANA olmadi. Iz jurnalda qoladi; job KONVERGENT,
        # ya'ni o'sha kunni keyin qayta hisoblash mumkin.
        log.exception("billing_close_market_list_failed")
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
            result.errors.append(f"billing_close_failed:{type(exc).__name__}")
            log.warning("billing_close_failed", market_id=str(market_id), error=type(exc).__name__)

    await _write_heartbeat(sessionmaker, result)
    log.info(
        "billing_close_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        charged=result.charged,
        skipped_existing=result.skipped_existing,
        skipped_unbilled=result.skipped_unbilled,
        no_slot_rows=result.no_slot_rows,
        anomalies_unassigned=result.anomalies_unassigned,
        anomalies_closed_day=result.anomalies_closed_day,
        anomalies_no_coverage=result.anomalies_no_coverage,
        resolved_without_reviewer=result.resolved_without_reviewer,
        adjustments_late_review=result.adjustments_late_review,
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
    """`day_close.py::_tenant_session()` ning shu moduldagi JUFTI.

    ⚠ NUSXA EMAS, JUFT (`retention.py` da o'rnatilgan qoida): import
      yo'nalishi ikki mustaqil jobni bir-biriga bog'lardi va biri
      o'zgarganda ikkinchisi jimgina o'zgarardi.

    ⛔ `actor_kind = SYSTEM` va `actor_id = None` — `charge_adjustments`
       ning DB-audit triggeri AYNAN shu GUC'lardan o'qiydi, ya'ni kech
       tasdiq tuzatishi audit jurnalida «tizim» bo'lib qoladi.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`day_close.py:220-222`).
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
    result: BillingCloseResult,
) -> None:
    """Bitta bozorning bir kuni — ⛔ O'QISH VA YOZISH BIR tranzaksiyada.

    ⚠ SABAB `day_close.py::_close_market` NIKI BILAN AYNAN BIR XIL:
      bu yerda poyga emas, IZCHILLIK muhim. Slot qatorlarini o'qib
      bo'lgach nazoratchi javob yozsa va `day_close` qayta yugursa,
      ikkinchi tranzaksiya o'sha javobni ko'rmagan hisobni yozardi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        market_open = await _market_open(session, market_id=market_id, business_date=business_date)
        verdicts = await billable_stalls(session, market_id=market_id, service_date=business_date)

        if not market_open:
            # ⛔ D-10 — YOPIQ KUNDA HISOB YOZILMAYDI, LEKIN HODISA
            #   JIMGINA YO'QOLMAYDI. Erta `return` ATAYIN: yopiq kunda
            #   «materializatsiya qilinmagan rasta» degan savolning O'ZI
            #   ma'nosiz (kadr olinishi ham shart emas), ya'ni
            #   `no_slot_rows` bu shoxda SANALMAYDI.
            await _write_closed_day_anomalies(
                session,
                market_id=market_id,
                business_date=business_date,
                verdicts=verdicts,
                result=result,
            )
            return

        # ⛔ Pitfall 2 — MAXRAJ `day_close` NIKI BILAN AYNAN BIR XIL
        #   manbadan (`BillingCloseResult.no_slot_rows` docstringi).
        active_stalls = await OccupancyRepository(session, market_id).active_stall_ids()
        materialised = {verdict.stall_id for verdict in verdicts}
        result.no_slot_rows += sum(1 for stall_id in active_stalls if stall_id not in materialised)

        # ⛔ D-16 — SUMMA BITTA FUNKSIYADAN. Bir chaqiruv butun bozorni
        #   beradi: rasta-rasta chaqirish 1000 rastada 1000 so'rov bo'lardi
        #   va `market_is_open()` ham har safar qayta hisoblanardi.
        money_by_stall = {
            money.stall_id: money
            for money in await resolve_stall_day_money(
                session, market_id=market_id, as_of=business_date
            )
        }
        existing = await market_day_charges(
            session, market_id=market_id, service_date=business_date
        )

        for verdict in verdicts:
            await _close_stall(
                session,
                market_id=market_id,
                business_date=business_date,
                verdict=verdict,
                money=money_by_stall.get(verdict.stall_id),
                charge=existing.get(verdict.stall_id),
                result=result,
            )


async def _close_stall(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
    verdict: StallSlotVerdict,
    money: StallDayMoney | None,
    charge: ExistingCharge | None,
    result: BillingCloseResult,
) -> None:
    """Bir rastaning bir kuni — BESH SHOX, har biri ALOHIDA hisoblagich bilan.

    ⛔ HECH BIR SHOX `raise` QILMAYDI (D-14): noaniqlik ham, tarifning
       yo'qligi ham, biriktirishning yo'qligi ham KUNNI BLOKLAMAYDI.
    """
    decision = verdict.decision

    # (1) D-05 — QAMROVSIZ. ⛔ BU BILL-04 ANOMALIYASI EMAS va u hisob
    #     shartidan OLDIN tekshiriladi: qamrovsiz rasta «band emas» degan
    #     javobga ham, «band» degan javobga ham EGA EMAS.
    if decision.no_coverage_only:
        # ⛔ SANOQ YOZUVGA ERGASHADI, URINISHGA EMAS (WR-03): `write_anomaly()`
        #   konfliktda `None` qaytaradi va job KONVERGENT — «qayta yugurish
        #   NORMAL holat». Shartsiz `+= 1` ikkinchi yugurishda o'sha
        #   anomaliyani QAYTA sanardi va son `system_heartbeats.detail` ga
        #   tushib, `/internal/self-check` bilan kunlik daydjestda
        #   OSHIRIB ko'rsatilardi — BILL-04 ning yagona tashqi kuzatuvi.
        #   `charged` bu qoidani ALLAQACHON bajaradi (`skipped_existing`).
        anomaly_id = await write_anomaly(
            session,
            market_id=market_id,
            stall_id=verdict.stall_id,
            service_date=business_date,
            kind=AnomalyKind.NO_COVERAGE_STALL,
            occupancy_event_id=None,
            snapshot_id=None,
        )
        if anomaly_id is not None:
            result.anomalies_no_coverage += 1
        return

    # (2) KO'RDIK, LEKIN BAND EMAS — va shu yerda KECH KELGAN TASDIQ shoxi.
    if not decision.billable:
        result.skipped_unbilled += 1
        await _late_review(session, market_id=market_id, charge=charge, result=result)
        return

    if money is None:
        # ⚠ AMALDA YETIB BO'LMAYDIGAN: `resolve_stall_day_money()` bozorning
        #   HAR rastasini qaytaradi, `billable_stalls()` esa faqat slot
        #   qatori borlarini. Shox baribir yozilgan — jimgina `continue`
        #   qilish rasta ikki so'rov orasida o'chirilgan holatni
        #   KO'RINMAS qilardi.
        result.errors.append(f"billing_close_money_missing:{verdict.stall_code}")
        return

    # (3) D-28 — BAND, LEKIN SOTUVCHI YO'Q. Hisob YOZILMAYDI: «kimdir
    #     qarzdor, lekin kim ekani noma'lum» yozuvi qarz hisobotini
    #     buzardi (`write_charge()` docstringi).
    if money.vendor_id is None:
        # ⛔ SANOQ YOZUVGA ERGASHADI (WR-03) — sabab (1) shoxida yozilgan.
        #   Bu yerda ikkinchi sabab ham bor: dalil topilmasa
        #   `_write_anomaly_with_evidence()` `errors` ga kod yozib ERTA
        #   qaytadi, ya'ni shartsiz `+= 1` YOZILMAGAN anomaliyani sanardi.
        written = await _write_anomaly_with_evidence(
            session,
            market_id=market_id,
            stall_id=verdict.stall_id,
            business_date=business_date,
            kind=AnomalyKind.UNASSIGNED_OCCUPIED,
            rows=verdict.rows,
            result=result,
        )
        if written:
            result.anomalies_unassigned += 1
        return

    # (4) TARIF YO'Q — ⛔ JIMGINA YUTILMAYDI (`errors` docstringidagi ⚠).
    if money.amount_soum is None:
        result.errors.append(f"billing_close_tariff_missing:{verdict.stall_code}")
        return

    # (5) HISOB.
    charge_id = await write_charge(
        session,
        market_id=market_id,
        stall_id=verdict.stall_id,
        service_date=business_date,
        money=money,
    )
    if charge_id is None:
        # ⚠ `None` XATO EMAS (Pitfall 3): hisob ALLAQACHON bor va qayta
        #   yugurish unga TEGMAYDI (D-06/D-07).
        result.skipped_existing += 1
        return

    result.charged += 1
    await write_evidence(session, market_id=market_id, charge_id=charge_id, slot_rows=verdict.rows)
    if not decision.human_confirmed_occupied:
        # ⛔ D-14 — YASHIRILADIGAN emas, O'LCHANADIGAN miqdor.
        result.resolved_without_reviewer += 1


async def _late_review(
    session: AsyncSession,
    *,
    market_id: UUID,
    charge: ExistingCharge | None,
    result: BillingCloseResult,
) -> None:
    """Pitfall 5(c) — hisob BOR, lekin rasta endi hisob shartiga yetmaydi.

    ⛔ SHOX FAQAT «KO'RDIK VA BAND EMAS» HOLATIDA ISHLAYDI, qamrovsizlikda
       EMAS (chaqiruv nuqtasi (1) shoxidan KEYIN turadi). «Ko'ra olmadik»
       sababli yozilgan hisobni kamaytirish tushumni KO'R NUQTA hisobiga
       jimgina o'chirardi — D-05 ning aynan teskarisi.

    ⚠ HOLAT FAQAT INSON ARALASHUVIDAN TUG'ILADI: `occupancy_events`
      SHARTSIZ o'zgarmas (`0018`), ya'ni slot `occupied` dan `empty` ga
      faqat `zone_reviews` javobi bilan o'ta oladi.
    """
    if charge is None:
        return
    adjustment_id = await write_late_review_adjustment(session, market_id=market_id, charge=charge)
    if adjustment_id is not None:
        result.adjustments_late_review += 1


async def _write_closed_day_anomalies(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
    verdicts: list[StallSlotVerdict],
    result: BillingCloseResult,
) -> None:
    """D-10 — yopiq kunda ko'ringan savdo DALIL bilan yoziladi.

    ⚠ FAQAT BANDLIK TOPILGAN RASTALAR: yopiq kunda bo'sh rasta hech
      qanday savolni tug'dirmaydi va uni ham yozish anomaliya
      hisobotini bo'sh qatorlar bilan to'ldirardi.
    """
    for verdict in verdicts:
        if verdict.decision.occupied_slots == 0:
            continue
        # ⛔ SANOQ YOZUVGA ERGASHADI (WR-03) — sabab yuqoridagi ikki shoxda.
        written = await _write_anomaly_with_evidence(
            session,
            market_id=market_id,
            stall_id=verdict.stall_id,
            business_date=business_date,
            kind=AnomalyKind.CLOSED_DAY_OCCUPIED,
            rows=verdict.rows,
            result=result,
        )
        if written:
            result.anomalies_closed_day += 1


async def _write_anomaly_with_evidence(
    session: AsyncSession,
    *,
    market_id: UUID,
    stall_id: UUID,
    business_date: date,
    kind: AnomalyKind,
    rows: tuple[SlotEvidenceRow, ...],
    result: BillingCloseResult,
) -> bool:
    """D-29 — «band, lekin to'lovsiz» da'vosi KADR bilan keladi.

    ⛔ DALILSIZ ANOMALIYA YOZILMAYDI: `write_anomaly()` uni `ValueError`
       bilan rad etardi va u bu jobda ISTISNO bo'lib chiqardi. Shuning
       uchun g'olib hodisa topilmasa shox `errors` ga KOD yozadi va
       davom etadi — jimgina o'tkazib yuborish «anomaliya yo'q» degan
       yolg'on hisobot berardi.

    ⚠ G'OLIB HODISA `stall_slot_occupancy.winning_occupancy_event_id` DAN
      (D-08 ning muzlatilgan pointeri), qayta hisoblanmaydi. Tartib
      `_BILLABLE_SLOT_ROWS` ning `ORDER BY ... slot_time` idan keladi,
      ya'ni bir xil kirish har safar BIR XIL kadrni beradi.

    Returns:
        `True` — YANGI qator yozildi; `False` — dalil topilmadi YOKI
        anomaliya bu kunga ALLAQACHON yozilgan (konvergent qayta
        yugurish). ⛔ Chaqiruvchi sanoqni AYNAN shu javobga bog'laydi
        (WR-03): shartsiz `+= 1` qayta yugurishda sonni oshirib
        yuborardi va u `system_heartbeats.detail` ga tushardi.
    """
    winner = next(
        (
            row.winning_occupancy_event_id
            for row in rows
            if row.verdict == _OCCUPIED and row.winning_occupancy_event_id is not None
        ),
        None,
    )
    snapshot_id = None
    if winner is not None:
        snapshot_id = (await event_snapshots(session, market_id=market_id, event_ids=[winner])).get(
            winner
        )

    if winner is None or snapshot_id is None:
        result.errors.append(f"billing_close_anomaly_without_evidence:{kind.value}")
        return False

    anomaly_id = await write_anomaly(
        session,
        market_id=market_id,
        stall_id=stall_id,
        service_date=business_date,
        kind=kind,
        occupancy_event_id=winner,
        snapshot_id=snapshot_id,
    )
    return anomaly_id is not None


async def _market_open(session: AsyncSession, *, market_id: UUID, business_date: date) -> bool:
    """`market_is_open()` — TENANT KONTEKSTI ostida (fayl docstringining 4-bandi)."""
    row = await session.execute(
        _MARKET_IS_OPEN, {"market_id": market_id, "business_date": business_date}
    )
    return bool(row.scalar_one())


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], result: BillingCloseResult
) -> None:
    """`system_heartbeats['billing_close']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ XATO YUTILADI (`day_close.py::_write_heartbeat` bilan aynan bir xil
      qoida): bu yozuv PROGRESS ko'rsatkichi, yugurishning natijasi EMAS.

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, ya'ni
      `detail` ga FAQAT SANOQLAR yoziladi. `market_id`, `stall_id` yoki
      rasta kodi bu yerga tushsa u hamma uchun ko'rinadigan joyda qolardi.
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=BILLING_CLOSE_COMPONENT,
                detail={
                    "markets": result.markets,
                    "charged": result.charged,
                    "skipped_existing": result.skipped_existing,
                    "skipped_unbilled": result.skipped_unbilled,
                    "no_slot_rows": result.no_slot_rows,
                    "anomalies_unassigned": result.anomalies_unassigned,
                    "anomalies_closed_day": result.anomalies_closed_day,
                    "anomalies_no_coverage": result.anomalies_no_coverage,
                    "resolved_without_reviewer": result.resolved_without_reviewer,
                    "adjustments_late_review": result.adjustments_late_review,
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
        log.warning("billing_close_heartbeat_not_written", error=type(exc).__name__)
