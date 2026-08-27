"""`recon.open` — kechagi kunning nomuvofiqliklarini navbatga qo'yadi (RECON-02).

=============================================================================
1. KUN — ARGUMENT, JOB ICHIDA HISOBLANMAYDI (D-12).

`retention_daily(today=...)`, `day_close(business_date=...)` va
`billing_close(business_date=...)` da o'rnatilgan qoidaning to'rtinchi
takrori: mahsulot yo'lida kunni QOBIQ (cron registratsiyasi, 07-14)
hisoblaydi, test esa AYNAN o'sha funksiyani BOSHQA kun bilan chaqiradi.
Job ichida bugungi kunni o'zi aniqlasa «qaysi kun tekshirildi?» savoli
testda ikkinchi manbaga ega bo'lardi va o'tmishdagi kunni qayta
tekshirish yo'li UMUMAN bo'lmasdi.

⚠ CRON REGISTRATSIYASI BU FAYLDA EMAS va bu ATAYIN: qobiq (`app/worker.py`)
  07-14 ning fayli va u BESHALA jobni bir joyda ro'yxatga oladi. Bu modul
  faqat CHAQIRILADIGAN funksiyani beradi.

=============================================================================
2. ⛔ BOZORLAR RO'YXATI IMPORT QILINADI, NUSXA OLINMAYDI (D-15/T-06-37).

`active_market_ids()` RLS'ni chetlab o'tadi, ya'ni u xavfsizlik YUZASI va
yuzaning AYNAN BITTA chaqiruv nuqtasi bo'lishi kerak. Ikkinchi nusxa
yozilganda yuzani toraytirish (masalan `is_active` dan tashqari yana bir
shart qo'shish) BIR nusxada bajarilardi va ikkinchisi jimgina eskirardi.

⚠ `_tenant_session()` esa ATAYIN TAKRORLANGAN (`retention.py` da
  o'rnatilgan farq): u xavfsizlik yuzasi emas, STRUKTURAVIY naqsh —
  import yo'nalishi ikki mustaqil jobni bir-biriga bog'lab qo'yardi.

=============================================================================
3. ⛔ HAR BOZOR UCHUN ALOHIDA TRANZAKSIYA VA ALOHIDA KONTEKST.

Bitta tranzaksiyada ikki bozor — tenant sizib chiqishining eng qisqa
yo'li; qolaversa bitta bozordagi nosozlik qolganlarining navbatini ham
BO'SH qoldirardi.

=============================================================================
4. ⛔ JOB HECH QACHON YIQILMAYDI (`alerting.py` / `billing_close.py`
   qoidasi). Bitta bozorning xatosi YUTILADI va `ReconOpenResult.errors`
   ga TURI bilan yoziladi — MATNI bilan emas: istisno matni ombor
   manzilini, telefon raqamini yoki bot tokenini tashishi mumkin
   (04-06 / T-04-59 da o'lchangan).

=============================================================================
5. ⛔ YURAK URISHI XATOLAR BO'LGANDA HAM YOZILADI. Job ISHLADI — faqat
   ba'zi bozorlar chetda qoldi va bu `detail.errors` da KO'RINADI.
   `alerting.py` ning mavjud qarori bilan aynan bir xil: yugurishning
   YO'QLIGI («cron o'lmadimi?») va yugurishning QISMAN muvaffaqiyati ikki
   BOSHQA savol va ular bitta signalga siqilmaydi.

=============================================================================
⚠ `taskiq` IMPORT QILINMAYDI (S-4) — bu modul sof `async def`.

⚠ ARIFMETIKA BU YERDA YO'Q: ikki sinfning ta'rifi ham, kechikish
  chegarasining qo'llanishi ham `app/repositories/reconciliation_repo.py`
  da. Bu modul faqat TARTIBNI, SOZLAMANI va HISOBLAGICHLARNI biladi.
=============================================================================
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.enums import ActorKind
from sbozor_core.models.notification import MarketNotificationSettings
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import Integer, bindparam, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.retention import active_market_ids
from app.repositories.reconciliation_repo import open_cases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = structlog.get_logger(__name__)

__all__ = [
    "DEFAULT_OVERDUE_DAYS",
    "RECON_OPEN_COMPONENT",
    "ReconOpenResult",
    "overdue_cutoff",
    "reconciliation_open",
]

_UUID = PgUuid(as_uuid=True)

RECON_OPEN_COMPONENT: Final[str] = "reconciliation_open"
"""`system_heartbeats.component` — yugurishning YAGONA tashqi izi.

⛔⛔ SATR UCH JOYDA O'QILADI VA UCHALASI HAM SHU KONSTANTANI IMPORT
   QILISHI SHART: bu modul uni YOZADI, `app/jobs/alerting.py` uning
   eskirganini o'lchaydi, `app/api/internal/self_check.py` esa uning
   UMUMAN yozilmaganini ko'rsatadi (`never_seen`). Ikkinchi va uchinchi
   chaqiruvchi 07-14 da qo'shiladi.

`BILLING_CLOSE_COMPONENT` / `RETENTION_COMPONENT` / `DAY_CLOSE_COMPONENT`
bilan bir xil qoida va bir xil sabab: qo'lda yozilgan literal bir kun
jimgina ajralib ketardi va «cron ro'yxatga olinmagan» holati HECH QACHON
ko'rinmasdi — endpoint komponentni MANGU `never_seen` da ko'rsatardi va
xato yo'q, jurnal yozuvi yo'q, faqat sukunat bo'lardi.
"""


def _schema_default_overdue_days() -> int:
    """Kechikish chegarasining kod standarti — ⛔ SXEMADAN HOSILA, literal EMAS.

    =======================================================================
    ⛔ QIYMAT SHU YERDA QAYTA YOZILMAYDI. Uning yagona manbai —
       `MarketNotificationSettings.overdue_days` ning `server_default` i
       (A3, `models/notification.py` da sabablangan). Python tomonda
       ikkinchi literal yozilganda ikki standart JIMGINA ajralib ketardi:
       sozlama qatori BOR bozor bir chegarani, sozlamasi YO'Q bozor
       boshqasini olardi va ikkalasi ham «standart» deb atalardi (D-32
       ning aynan sinfi).

    ⚠ SHAKL BUZILSA FUNKSIYA YIQILADI, NOLGA TUSHMAYDI: jim standart
      qiymat chegarani bir kun jimgina o'chirib qo'yardi va navbat
      shovqinga aylanardi.
    =======================================================================
    """
    default = MarketNotificationSettings.__table__.c.overdue_days.server_default
    literal = getattr(getattr(default, "arg", None), "text", None)
    if literal is None:
        raise RuntimeError(
            "`market_notification_settings.overdue_days` ustunida o'qib "
            "bo'ladigan `server_default` yo'q — kechikish chegarasining kod "
            "standarti SXEMADAN olinadi va uni bu yerda literal bilan "
            "almashtirish ikkinchi standart yaratardi."
        )
    return int(literal)


DEFAULT_OVERDUE_DAYS: Final[int] = _schema_default_overdue_days()
"""Sozlama qatori YO'Q bozorlar uchun kechikish chegarasi (A3).

⚠ QATOR MAJBURIY EMAS (`market_notification_settings` PK — `market_id`,
  1:1 va u YO'Q bo'lishi QONUNIY): har bozor uchun majburiy qator
  wizard'ga yana bir qadam qo'shardi va 300 rastali bozorda hech qanday
  qiymat bermasdi. Shuning uchun o'quvchi `COALESCE` bilan shu qiymatga
  tushadi.
"""


def overdue_cutoff(business_date: date, overdue_days: int) -> date:
    """Kechikish chegarasi — ⛔ QOIDANING YAGONA TA'RIFI (D-19, WR-06).

    =========================================================================
    ⛔⛔ IKKINCHI AYIRISH IFODASI KODDA YOZILMAYDI.

    `recon.open` (case tug'ilishi) va BOT-03 (sotuvchi eslatmasi) —
    ikki MUSTAQIL job, lekin ular BIR savolga javob beradi: «qaysi
    kundan eskisi kechikkan hisoblanadi?». 07-fazada bu savolga ikki
    joyda javob berilardi (`reconciliation_repo` va `digest_repo` ning
    o'z ayirish ifodalari) va ikkalasi bir xil FORMULA bo'lsa ham,
    ularga kelgan `business_date` MAHSULOTDA bir kunga farq qilardi
    (WR-06). Formula bitta joyga yig'ilganda ham bu yetmasdi — shuning
    uchun chegara endi JOB QATLAMIDA hisoblanadi va repo qatlamiga
    TAYYOR `cutoff` bo'lib tushadi.

    ⛔ REPO QATLAMI ENDI CHEGARANI HISOBLAMAYDI, QO'LLAYDI. Ya'ni
       «qaysi kundan?» savolining javobi `_OVERDUE_CHARGES` va
       `overdue_vendors()` ga ARGUMENT bo'lib boradi va ikkala
       mexanizmning javobi STRUKTURAVIY ravishda bir xil bo'ladi.

    ⚠ FUNKSIYA SHU MODULDA, `notification_meta` DA EMAS: `DEFAULT_
      OVERDUE_DAYS` reyestrda (sxemadan hosila), chegara ARIFMETIKASI
      esa `recon.open` ning o'z qoidasi va `notifications.py` uni SHU
      YERDAN import qiladi. Yo'nalish ATAYIN shu tomonga — teskarisi
      reyestr modulini job mantig'iga bog'lardi.
    =========================================================================

    Args:
        business_date: qaysi kunning holati baholanyapti. ⛔ IKKALA job
            ham QOBIQDAN bir xil kun oladi (`business_today() - 1`) —
            tenglik `test_overdue_reminder_shares_the_knob_with_case_
            opening` da, qobiqlardan yuritib o'lchanadi.
        overdue_days: bozorning chegarasi —
            `market_notification_settings.overdue_days`.

    Returns:
        Eng kech «kechikkan» sanaladigan kun. Taqqoslash chaqiruvchida
        ⛔ `<=` bilan qilinadi (`_OVERDUE_CHARGES` va `overdue_vendors()`
        ikkalasida ham): `<` yozilganda chegaradagi kun bir mexanizmda
        case ochib, ikkinchisida eslatma BERMASDI.
    """
    return business_date - timedelta(days=overdue_days)


_MARKET_OVERDUE_DAYS = text(
    """
    SELECT COALESCE(
               (SELECT s.overdue_days
                  FROM market_notification_settings s
                 WHERE s.market_id = :market_id),
               :fallback
           )::int AS overdue_days
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("fallback", type_=Integer()),
)
"""Bozorning kechikish chegarasi — ⛔ `COALESCE` BILAN, ikki so'rov bilan EMAS.

«Avval qator bormi deb qara, keyin o'qi» shakli ikki borish talab qilardi
va oradagi oynada sozlama o'zgarsa job ESKI qiymat bilan ishlardi. Bir
so'rov ikkala shoxni ham beradi.

⛔ CHEGARA BOT-03 BILAN AYNAN BIR KNOB (D-19): sotuvchi eslatmasi va case
   tug'ilishi BIR sozlamadan oziqlanadi. Ikki alohida sozlama ajralib
   ketardi va sotuvchi eslatma OLMAGAN qarz uchun case ochilardi — u
   ogohlantirilmagan holda navbatga tushardi.
"""


@dataclass(slots=True)
class ReconOpenResult:
    """Bitta yugurishning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`BillingCloseResult` qoidasi):
    HAMMA maydon HAR DOIM qaytariladi va chaqiruvchi «nega case yo'q?»
    savoliga javobni YONIDA topadi.
    """

    markets: int = 0
    """Ko'rib chiqilgan FAOL bozorlar soni — xato bergani ham SHU SONDA."""
    anomaly_cases: int = 0
    """SINF B — «ro'yxatga olinmagan savdo» uchun ochilgan YANGI case'lar."""
    unpaid_cases: int = 0
    """SINF A — «band, lekin to'lovsiz» uchun ochilgan YANGI case'lar.

    ⚠ IKKI SANOQ HECH QACHON QO'SHILMAYDI (C-12 naqshi): ular IKKI
      BOSHQA savoldan chiqadi va ularning NISBATI RECON-01 ning butun
      mazmuni. Bitta songa siqilsa «sotuvchi biriktirilmagan» bilan
      «sotuvchi to'lamagan» mexanik ravishda bir xil ko'rinardi.
    """
    skipped_existing: int = 0
    """Case ALLAQACHON bor edi — KONVERGENTLIKNING o'lchovi, xato emas."""
    errors: list[str] = field(default_factory=list)
    """⛔ XATO MATNI EMAS, TURI (`_swallow()` docstringi)."""


async def reconciliation_open(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
) -> ReconOpenResult:
    """Har faol bozor uchun kunning nomuvofiqliklarini navbatga qo'yadi.

    Args:
        business_date: qaysi kun tekshiriladi (`Asia/Tashkent`). ⛔ ARGUMENT
            — fayl docstringining 1-bandi. Qobiq (07-14) unga KECHAGI kunni
            beradi va o'sha hisob QOBIQDA bajariladi.

    Returns:
        `ReconOpenResult` — sonlar va YUTILGAN xatolarning TURLARI.
    """
    request_id = f"job-recon-open-{business_date.isoformat()}"
    result = ReconOpenResult()

    try:
        # ⛔ D-15: bozorlar ro'yxatining YAGONA chetlab o'tuvchi yuzasi.
        #   IMPORT QILINADI, nusxa yozilmaydi (fayl docstringining 2-bandi).
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Yugurish BOSHLANA olmadi. Iz jurnalda qoladi; job KONVERGENT,
        # ya'ni o'sha kunni keyin qayta tekshirish mumkin.
        log.exception("reconciliation_open_market_list_failed")
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _open_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                business_date=business_date,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 - bir bozor qolganlarini to'xtatmaydi
            # ⛔ `SQLAlchemyError` EMAS, `Exception`: repo qatlami buzilgan
            #   ma'lumotda `ValueError` beradi (masalan hisobdan katta
            #   kamaytirish -> manfiy qoldiq) va o'sha istisno BAZA xatosi
            #   emas. Torroq blok bilan bitta bozorning nuqsoni butun
            #   navbatni bo'sh qoldirardi.
            _swallow(result, "reconciliation_open_failed", exc, market_id=market_id)

    await _write_heartbeat(sessionmaker, result)
    log.info(
        "reconciliation_open_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        anomaly_cases=result.anomaly_cases,
        unpaid_cases=result.unpaid_cases,
        skipped_existing=result.skipped_existing,
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
    """`billing_close.py::_tenant_session()` ning shu moduldagi JUFTI.

    ⚠ NUSXA EMAS, JUFT (`retention.py` da o'rnatilgan qoida): import
      yo'nalishi ikki mustaqil jobni bir-biriga bog'lardi va biri
      o'zgarganda ikkinchisi jimgina o'zgarardi.

    ⛔ `actor_kind = SYSTEM` va `actor_id = None` — `reconciliation_cases`
       AUDIT ostida (`AUDITED_TABLES`) va DB-triggeri AYNAN shu GUC'lardan
       o'qiydi. Kontekstsiz case tug'ilishi audit jurnalida EGASIZ
       qolardi, holbuki «case qachon va nima sababdan paydo bo'ldi?»
       savoli nizoda (D-02) dalil bo'ladi.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`billing_close.py` naqshi).
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


async def _open_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    business_date: date,
    result: ReconOpenResult,
) -> None:
    """Bitta bozorning bir kuni — sozlamani o'qish VA yozish BIR tranzaksiyada.

    ⚠ SANOQLAR TRANZAKSIYA YOPILGANDAN KEYIN QO'SHILADI. Blok ichida
      qo'shilsa `COMMIT` ning o'zi yiqilgan holatda hisoblagich YOZILMAGAN
      case'larni sanardi — va o'sha son `system_heartbeats.detail` ga
      tushib, kunlik dayjestda ko'rinardi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        overdue_days = await _overdue_days(session, market_id=market_id)
        opened = await open_cases(
            session,
            market_id=market_id,
            business_date=business_date,
            # ⛔ CHEGARA SHU YERDA HISOBLANADI, REPO ICHIDA EMAS (WR-06):
            #   `overdue_cutoff()` — qoidaning YAGONA ta'rifi va BOT-03
            #   ham AYNAN shu funksiyani chaqiradi.
            cutoff=overdue_cutoff(business_date, overdue_days),
        )

    result.anomaly_cases += opened.anomaly_cases
    result.unpaid_cases += opened.unpaid_cases
    result.skipped_existing += opened.skipped_existing


async def _overdue_days(session: AsyncSession, *, market_id: UUID) -> int:
    """Bozorning kechikish chegarasi — `_MARKET_OVERDUE_DAYS` ning qobig'i."""
    row = await session.execute(
        _MARKET_OVERDUE_DAYS, {"market_id": market_id, "fallback": DEFAULT_OVERDUE_DAYS}
    )
    return int(row.scalar_one())


def _swallow(result: ReconOpenResult, event: str, exc: Exception, *, market_id: UUID) -> None:
    """Xatoni YUTADI va uni SANOQQA aylantiradi — MATNINI EMAS, TURINI.

    `alerting.py::_swallow()` ning aynan shakli va aynan sababi: istisno
    matni ombor manzilini, sotuvchining telefonini yoki bot tokenini
    tashishi mumkin (04-06 va T-04-59 ning o'lchovlari). Turi esa
    ma'muriyatga «nima sinfdagi nosozlik?» degan javobni beradi va hech
    qanday shaxsiy ma'lumot tashimaydi.
    """
    name = type(exc).__name__
    result.errors.append(f"{event}:{name}")
    log.warning(event, market_id=str(market_id), error=name)


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], result: ReconOpenResult
) -> None:
    """`system_heartbeats['reconciliation_open']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ `except Exception` — `SQLAlchemyError` EMAS. Sabab 04-07 da
      o'lchangan: yangi ulanish ochilganda `socket.gaierror`
      `SQLAlchemyError` ga O'RALMAYDI va butun jobni ENG OXIRIDA
      yiqitardi.

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, ya'ni
      `detail` ga FAQAT SANOQLAR yoziladi. `market_id`, sotuvchi yoki
      rasta kodi bu yerga tushsa u hamma uchun ko'rinadigan joyda
      qolardi.
    """
    detail: dict[str, Any] = {
        "markets": result.markets,
        "anomaly_cases": result.anomaly_cases,
        "unpaid_cases": result.unpaid_cases,
        "skipped_existing": result.skipped_existing,
        "errors": len(result.errors),
    }
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=RECON_OPEN_COMPONENT, detail=detail
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    set_={"last_seen_at": func.now(), "detail": statement.excluded.detail},
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi jobni yiqita olmaydi
        log.warning("reconciliation_open_heartbeat_not_written", error=type(exc).__name__)
