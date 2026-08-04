"""Kadr olish quvurining fon-vazifasi — tik (reja) va batch (kadr).

=============================================================================
BU FAYLDA NAVBAT KUTUBXONASI IMPORT QILINMAYDI (S-4, D-06).

`capture_tick` va `capture_batch` — SOF `async def` funksiyalar. Ularni
navbatga bog'laydigan yupqa qobiq `app/worker.py` da va kutubxona nomi
FAQAT o'sha faylda uchraydi. Navbatga qo'yish ham bu yerda EMAS: tik
`enqueue` chaqiruvini ARGUMENT sifatida oladi.

⚠ Buni `grep -cE "^\\s*(import|from)\\s+taskiq"` mexanik tekshiradi.
=============================================================================

=============================================================================
PITFALL 9 — TIK HAMMA BOZORLAR USTIDA ISHLAYDI, `sbozor_app` ESA
KONTEKSTSIZ BIRORTA BOZORNI KO'RMAYDI.

Bu 3-fazadagi Pitfall 13 ning KENGAYTMASI va u undan ham jimroq. Kashfiyot
jobi bitta bozor uchun chaqiriladi va uning kontekstsiz nosozligi «admin
tugmani bosdi, hech nima bo'lmadi» bo'lib ko'rinardi. Tik esa hech kim
bosmaydigan tugma: kontekstsiz u «bugun ish yo'q» deb JIM turadi, xato
bermaydi, jurnalga hech nima yozmaydi va nosozlik faqat kun oxirida —
hisobot bo'sh chiqqanda — sezilardi.

Yechim IKKI QISMDAN iborat va ikkalasi ham majburiy:

  1. `capture_due_markets()` — `SECURITY DEFINER` funksiya. U RLS'ni
     chetlab o'tadi, lekin yuzasi ATAYIN tor: FAQAT bozor identifikatori
     va muddati kelgan slotlar soni (T-04-16). Bozor NOMI ham, kamera
     ham, kadr ham YO'Q.
  2. Har bozor uchun ALOHIDA `_system_transaction()`. Bitta tranzaksiyada
     ikki bozorni aralashtirish tenant sizib chiqishining ENG QISQA yo'li
     bo'lardi: GUC'lar `SET LOCAL` bilan qo'yiladi va ikkinchi
     `set_tenant_context()` birinchisining ustiga yozilardi — o'shanda
     birinchi bozor uchun boshlangan ish IKKINCHI bozorning ma'lumotini
     ko'rardi.
=============================================================================

=============================================================================
TARTIB MUZOKARA QILINMAYDI: kadr -> sifat -> S3 `PUT` -> BAZA (§B.4).

Baza qatori obyekt BORLIGINI tasdiqlaydi. Teskari tartib 6-fazaga MAVJUD
BO'LMAGAN dalilga havola berardi va BILL-02 («har hisob dalil-kadrlarga
bog'langan») aynan buni ko'tara olmaydi. `storage.put()` yiqilganda
`snapshots` qatori UMUMAN yozilmaydi va qator `capture_storage_unavailable`
bilan yopiladi — kadr allaqachon olingan, ya'ni qayta urinish arzon.
=============================================================================

=============================================================================
KOMPENSATSIYA OYNASI CHEGARALANGAN — VA BU MAHSULOT QARORI.

Tik «hali bajarilmagan har qanday slot»ni CHEKSIZ kutmaydi:
`scheduled_at + grace < now()` bo'lgan qator BAJARILMAYDI, u `missed` deb
yopiladi. Sabab: 06:00 sloti 07:05 da olingan kadr «06:00 da rasta band
edimi?» savoliga JAVOB BERMAYDI — u boshqa savolga javob beradi va uni
6-faza dalil sifatida ishlatsa noto'g'ri hisob chiqadi. Kechikkan kadr —
yo'q kadrdan YOMONROQ.
=============================================================================

JOB JARAYONI HECH QACHON YIQILMAYDI (`discovery.py:61-65` bilan bir xil
qoida va bir xil sabab): navbat yiqilgan vazifani QAYTA yetkazishi mumkin
va qayta urinish NVR ga ikkinchi marta borardi.

⚠ JORIY VAQT ARGUMENT SIFATIDA OLINADI. Tik qaysi biznes-kunning rejasini
  materializatsiya qilishini `now` belgilaydi va uni modul funksiyasidan
  olish testni «hozir» ga bog'lab qo'yardi — yarim tun atrofida bir kun
  farq qiladigan flaky o'lchov. Taqiqlangan chaqiruvlarning LITERAL shakli
  bu izohda ATAYIN yozilmagan: mexanik darvoza faylni MATN sifatida
  o'qiydi va izohni koddan ajratmaydi.
"""

from __future__ import annotations

import asyncio
import os
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

import structlog
from sbozor_core.enums import ActorKind
from sbozor_core.models import SystemHeartbeat
from sbozor_core.models.nvr import CAPTURE_STREAM_VALUES
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_date, now_tz
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.capture_repo import CaptureRepository
from app.repositories.nvr_repo import NvrRepository
from app.repositories.snapshot_repo import SnapshotRepository
from app.security.secrets import InvalidToken, decrypt_nvr_password
from app.services.capture_errors import (
    CAPTURE_AUTH_LOCKING_CODES,
    CAPTURE_CREDENTIAL_UNREADABLE,
    CAPTURE_DEFER_CODES,
    CAPTURE_SOURCE_UNREACHABLE,
    CAPTURE_STORAGE_UNAVAILABLE,
    CAPTURE_STREAM_LIMIT,
    CAPTURE_WORKER_LOST,
    MAX_DETAIL_CHARS,
    CaptureError,
)
from app.services.frame_source import CaptureTarget, DeviceEndpoint, capture_frame
from app.services.isapi.client import RTSP_FALLBACK_PORT
from app.services.live_source import authenticated_rtsp_source
from app.services.object_key import object_key
from app.services.quality import analyze
from app.services.rtsp import rtsp_url
from app.services.storage import StorageError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
    from datetime import date, datetime, time

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.capture_repo import ClaimedRun, MissedSlot
    from app.services.frame_source import FrameSource, FrameSourcePool
    from app.services.quality import QualityThresholds
    from app.services.storage import SnapshotStorage

log = structlog.get_logger(__name__)

__all__ = [
    "CAPTURE_TICK_COMPONENT",
    "JOB_INTERNAL_ERROR",
    "SYSTEM_ACTOR_LABEL",
    "BatchRequest",
    "BatchResult",
    "CapturePolicy",
    "TickResult",
    "capture_batch",
    "capture_tick",
]


CAPTURE_TICK_COMPONENT: Final[str] = "capture_tick"
"""`system_heartbeats.component` — FOUND-06 ning eng pastki qatlami.

⚠ SATR `core-api` NING `/internal/self-check` ENDPOINTI BILAN BIR XIL
  bo'lishi shart (04-08). Ikki nusxa bo'lganda tik yurak urishini bir
  nomga yozib, tekshiruv BOSHQA nomni izlardi va «worker o'lik» degan
  DOIMIY alert chiqib turardi — ya'ni D-22 ning alert charchashi aynan
  monitoring qatlamidan boshlanardi.
"""

JOB_INTERNAL_ERROR: Final[str] = CAPTURE_WORKER_LOST
"""Kutilmagan istisno — kod nuqsoni yoki infratuzilma nosozligi.

⚠ REYESTRGA YANGI KOD QO'SHILMADI va bu ATAYIN. `capture_worker_lost`
  ning ta'rifi bu holatni AYNAN qamraydi: «kadr olish boshlandi, lekin
  tugallanmadi». Yangi kod qo'shish `CAPTURE_ERROR_CODES` ning o'n bir
  a'zosini (`04-UI-SPEC.md` §11.8 bilan mos va sanoq darvozasi bilan
  qulflangan) o'zgartirardi hamda frontendga TARJIMASIZ kod berardi.

To'liq iz `log.exception` bilan jurnalda qoladi; foydalanuvchiga esa
stack izi ham, istisno matni ham CHIQMAYDI (T-02-99).
"""

SYSTEM_ACTOR_LABEL: Final[str] = "tizim — kadr olish"
"""`audit_log.actor_label` — jurnalni O'QIYOTGAN odam uchun.

`discovery.py::SYSTEM_ACTOR_LABEL` bilan bir xil naqsh, boshqa matn:
kashfiyotni ODAM boshlaydi, tikni esa hech kim boshlamaydi — `actor_id`
bu yerda HAR DOIM `None`.
"""

_ADAPTIVE_FAILURE_FLOOR: Final[int] = 2
"""Adaptiv pasaytirish uchun kerak bo'lgan ENG KAM nosozlik soni.

Bitta nosozlik chegara alomati EMAS: u yolg'iz kameraning oflaynligi ham,
tasodifiy timeout ham bo'lishi mumkin. Ikkitasi esa naqsh.
"""

_MAIN_STREAM, _SUB_STREAM = CAPTURE_STREAM_VALUES
"""`cameras.capture_stream` ning ikkala qiymati — RO'YXATDAN OCHIB OLINADI.

`isapi/client.py` dagi jufti bilan bir xil qaror: qo'lda yozilgan literal
ro'yxatga uchinchi a'zo qo'shilgan kunda JIMGINA eskirardi.
"""

_ADAPTIVE_FAILURE_CODES: Final[frozenset[str]] = frozenset(
    {CAPTURE_STREAM_LIMIT, CAPTURE_SOURCE_UNREACHABLE}
)
"""Sessiya chegarasi alomati bo'lishi MUMKIN bo'lgan ikki kod (§A.5 — LOW).

Chegaraning wire darajasida qanday ko'rinishi o'lchanmagan: ba'zi firmware
`453`/`503` beradi, ba'zisi ulanishni JIMGINA uzadi. Shuning uchun ikkala
kod ham hisobga olinadi, LEKIN qaror faqat «kamida bittasi muvaffaqiyatli»
shartida qabul qilinadi (pastdagi `_maybe_lower_limit`).
"""


def _worker_id() -> str:
    """`capture_runs.locked_by` uchun diagnostika yorlig'i.

    Qulflash QARORI bu qiymatga TAYANMAYDI (`capture_repo.claim_due` ning
    docstringi: qaror `locked_until` ga qaraydi) — u faqat «qaysi jarayon
    ushlab turibdi?» savoliga javob beradi va konteyner qayta
    nomlanganda hech nimani buzmaydi.
    """
    return f"{socket.gethostname()}:{os.getpid()}"


def _raw(message: str) -> dict[str, Any]:
    """`error_detail` ning yagona shakli — `raw` kaliti (UI-SPEC §7.4 allowlist'i).

    `discovery.py::_raw` bilan aynan bir xil funksiya va bir xil sabab:
    chegarasiz istisno matni `jsonb` ustuniga cheksiz o'sardi (T-03-30).
    """
    return {"raw": message[:MAX_DETAIL_CHARS]}


@asynccontextmanager
async def _system_transaction(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    actor_id: UUID | None,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya — `deps.py:418-449` ning worker jufti.

    Uch farq bor va uchalasi ham ataylab:

      1. `Principal` YO'Q — `market_id` va `actor_id` argument sifatida
         keladi (tik ularni `capture_due_markets()` dan oladi);
      2. `actor_kind=ActorKind.SYSTEM` — `audit_log` da "buni odam emas,
         fon jarayoni yozdi" deb ko'rinsin;
      3. `HTTPException` YO'Q — worker'da javob beriladigan mijoz yo'q.

    ⚠ HAR CHAQIRUVDA YANGI TRANZAKSIYA VA YANGI KONTEKST. GUC'lar
      `SET LOCAL` bilan qo'yiladi, ya'ni `COMMIT` da tozalanadi. "Bir marta
      o'rnatib, keyin qayta ishlataman" yo'li fail-closed holatga tushardi
      va u JIMGINA 0 qator berardi (modul docstringi).
    """
    # SIM117 (ikki `async with` ni birlashtirish) `deps.py:434-439` dagi
    # bilan AYNAN bir xil sababdan rad etilgan: ichki blok TRANZAKSIYA
    # chegarasi va u shu yerdagi butun xavfsizlik da'vosini ushlab turadi.
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=actor_id,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


# ===========================================================================
# Kontrakt tiplari
# ===========================================================================


@dataclass(frozen=True, slots=True)
class CapturePolicy:
    """Tik va batch uchun kerak bo'lgan BARCHA sozlama — bitta obyektda.

    ⚠ `Settings` NING O'ZI UZATILMAYDI va bu `QualityThresholds` bilan
      aynan bir xil qaror: job sozlamalar obyektining butun yuzasini
      ko'rmasligi kerak, aks holda testda uni qurish uchun `DATABASE_URL`,
      `JWT_SECRET` va `NVR_CREDENTIAL_KEY` kerak bo'lardi (04-04 da
      o'lchangan). Bu tor obyekt esa bitta konstruktor chaqiruvi.
    """

    grace_seconds: int
    lease_seconds: int
    max_attempts: int
    batch_size: int
    global_concurrency: int
    quality: QualityThresholds


@dataclass(frozen=True, slots=True)
class BatchRequest:
    """Bitta `capture.batch` vazifasining butun yuki (D-04).

    ⚠ VAZIFA BIRLIGI — NVR + SLOT, KAMERA + SLOT EMAS. Konkurentlik
      chegarasi NVR ga tegishli, ya'ni semafor BITTA JARAYON ichida
      bo'lishi kerak. Kamera bo'yicha vazifa taqsimlangan qulf talab
      qilardi va u Valkey'da (davomiyliksiz kesh) yashamasdi.

    ⚠ FAQAT IDENTIFIKATORLAR. Slot vaqti va biznes-kun navbat xabariga
      solinmaydi: vazifa navbatda turgan paytda `release_expired()` qatorni
      qaytarib yuborishi mumkin va worker ESKIRGAN qiymatlar bilan kadr
      yozardi (`capture_repo.running_by_ids` docstringi).
    """

    market_id: UUID
    nvr_id: UUID
    run_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class TickResult:
    """Bitta tikning o'lchanadigan natijasi.

    `missed` — ALERTNING YAGONA MANBAI (D-20). Yo'qlik HODISA
    qoldirmaydi, ya'ni uni faqat shu ro'yxat ko'rinadigan qiladi va uni
    `04-08` iste'mol qiladi.
    """

    markets: int
    created: int
    skipped: int
    released: int
    claimed: int
    missed: tuple[MissedSlot, ...]
    batches: tuple[BatchRequest, ...]


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Bitta NVR batchining natijasi.

    `stopped_code` — `CAPTURE_AUTH_LOCKING_CODES` dagi kod tufayli batch
    to'xtatilgan bo'lsa o'sha kod. `None` — batch oxirigacha yurgan.
    """

    succeeded: int
    failed: int
    deferred: int
    stopped_code: str | None


@dataclass(frozen=True, slots=True)
class _RunContext:
    """Bitta slotni bajarish uchun yetarli minimum — ORM obyekti EMAS.

    `discovery.py::_DeviceContext` bilan aynan bir xil qaror: tranzaksiya
    YOPILGANDAN keyin ORM obyektiga tegish `expire_on_commit` sozlamasiga
    bog'lanib qolardi. Qiymatlar tranzaksiya ICHIDA ko'chiriladi va undan
    keyin hech qanday DB yo'li qolmaydi.
    """

    run_id: UUID
    camera_id: UUID
    channel_no: int
    stream_name: str
    capture_stream: str
    slot_time: time
    scheduled_at: datetime
    business_date: date


@dataclass(frozen=True, slots=True)
class _BatchContext:
    """Bitta NVR ning batchi uchun o'qilgan hamma narsa (oddiy qiymatlar)."""

    endpoint: DeviceEndpoint
    rtsp_host: str
    rtsp_port: int
    method: str
    max_concurrent: int
    stagger_ms: int
    observed_stream_limit: int | None
    runs: tuple[_RunContext, ...]


# ===========================================================================
# 1. TIK — to'rt qadam, har bozor uchun alohida tranzaksiya
# ===========================================================================


_DUE_MARKETS = text("SELECT market_id FROM capture_due_markets() ORDER BY market_id")
"""Tik ko'radigan bozorlar — `SECURITY DEFINER`, ya'ni TENANT KONTEKSTISIZ.

⚠ BU YAGONA ISTISNO va u modul docstringida asoslangan: funksiya RLS'ni
  chetlab o'tadi, lekin faqat identifikator beradi. Undan KEYINGI har bir
  so'rov odatdagidek RLS ostidan o'tadi.
"""


def _tick_request_id(day: date, moment: datetime) -> str:
    """Deterministik `request_id` — bitta tikning audit qatorlari BIR IPDA.

    `discovery.py:265-269` ning mulohazasi: tasodifiy qiymat har
    tranzaksiyada boshqa bo'lardi va bitta tikning yozuvlarini bir-biriga
    bog'lash imkonsiz bo'lardi. Tik uchun tabiiy identifikator — biznes-kun
    va DAQIQA (tik har daqiqada bir marta ishlaydi).
    """
    return f"job-capture-{day.isoformat()}-{moment.strftime('%H%M')}"


async def _due_market_ids(sessionmaker: async_sessionmaker[AsyncSession]) -> list[UUID]:
    """`capture_due_markets()` — FAQAT identifikatorlar, tenant kontekstisiz."""
    async with sessionmaker() as session, session.begin():
        result = await session.execute(_DUE_MARKETS)
        return [row.market_id for row in result]


def _group_by_nvr(market_id: UUID, runs: Sequence[ClaimedRun]) -> list[BatchRequest]:
    """Qulflab olingan qatorlarni NVR bo'yicha guruhlaydi (D-04)."""
    grouped: dict[UUID, list[UUID]] = {}
    for run in runs:
        grouped.setdefault(run.nvr_id, []).append(run.id)
    return [
        BatchRequest(market_id=market_id, nvr_id=nvr_id, run_ids=tuple(run_ids))
        for nvr_id, run_ids in grouped.items()
    ]


async def capture_tick(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    policy: CapturePolicy,
    now: datetime | None = None,
    enqueue: Callable[[BatchRequest], Awaitable[None]] | None = None,
) -> TickResult:
    """Rejani materializatsiya qiladi, yo'qlikni yozadi va ishni navbatga beradi.

    To'rt qadam va ularning tranzaksiya chegaralari (`04-PATTERNS.md` §3.3):

        0. `capture_due_markets()`     — bozorsiz, `SECURITY DEFINER`
        1. `release_expired()`         \\
        2. `ensure_plan()` + `mark_missed()`  > HAR BOZOR uchun BITTA tranzaksiya
        3. `claim_due()`               /
        4. navbatga qo'yish            — TRANZAKSIYADAN KEYIN

    ⚠ 4-QADAM TRANZAKSIYADAN KEYIN VA BU MUZOKARA QILINMAYDI. Navbatga
      qo'yish tranzaksiya ICHIDA bo'lsa, `COMMIT` yiqilganda vazifa
      ALLAQACHON yuborilgan bo'lardi va worker mavjud bo'lmagan `running`
      qatorni izlardi.

    Args:
        sessionmaker: sessiya fabrikasi. ARGUMENT, modul globali EMAS
            (`discovery.py::discover_nvr` bilan bir xil qoida).
        policy: sozlamalar — chegaralar va sifat to'plami.
        now: joriy payt. ARGUMENT: tik qaysi biznes-kunning rejasini
            materializatsiya qilishini aynan shu qiymat belgilaydi.
        enqueue: `capture.batch` ni navbatga qo'yadigan chaqiruv. `None`
            bo'lsa vazifalar FAQAT natijada qaytadi — bu testning yo'li VA
            navbat kutubxonasining bu fayldan tashqarida qolishining
            mexanizmi (S-4).

    Returns:
        `TickResult` — sonlar va `missed` slotlar ro'yxati (D-20).
    """
    moment = now if now is not None else now_tz()
    today = business_date(moment)
    request_id = _tick_request_id(today, moment)
    worker_id = _worker_id()

    try:
        market_ids = await _due_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Tik BOSHLANA olmadi. Iz jurnalda qoladi; keyingi tik (<=60 s)
        # aynan shu ishni qayta bajaradi, ya'ni yo'qotish YO'Q.
        log.exception("capture_tick_market_list_failed")
        market_ids = []

    created = skipped = released = claimed = 0
    missed: list[MissedSlot] = []
    batches: list[BatchRequest] = []

    for market_id in market_ids:
        try:
            async with _system_transaction(
                sessionmaker, market_id=market_id, actor_id=None, request_id=request_id
            ) as session:
                repo = CaptureRepository(session, market_id)

                # 1. Watchdog BIRINCHI: ijarasi tugagan `running` qator
                #    `pending` ga qaytadi va u SHU tikda qayta olinadi.
                #    Tartib teskari bo'lsa qaytgan qator bir tik kutardi.
                released += await repo.release_expired(max_attempts=policy.max_attempts)

                # 2. Materializatsiya. D-05 ning slot-muzlatishi `ensure_plan`
                #    ning ICHIDA (04-05, 1-deviatsiya): kun o'rtasida
                #    qo'shilgan VAQT bugungi rejaga tushmaydi.
                plan = await repo.ensure_plan(today, grace_seconds=policy.grace_seconds)
                created += plan.created
                skipped += plan.skipped

                # 3. Yo'qlik yozuvi — ALERTNING YAGONA manbai (D-20).
                missed.extend(await repo.mark_missed(grace_seconds=policy.grace_seconds))

                # 4. Qulflab olish (`FOR UPDATE SKIP LOCKED` + ijara).
                runs = await repo.claim_due(
                    grace_seconds=policy.grace_seconds,
                    lease_seconds=policy.lease_seconds,
                    batch=policy.batch_size,
                    worker_id=worker_id,
                )
        except SQLAlchemyError:
            # ⚠ BITTA BOZORNING NOSOZLIGI QOLGANLARINI TO'XTATMAYDI.
            #   Aks holda bitta buzilgan bozor butun o'rnatmaning kadr
            #   olishini o'chirib qo'yardi va sabab hech qayerda
            #   ko'rinmasdi (D-20 aynan shu sinfni taqiqlaydi).
            log.exception("capture_tick_market_failed", market_id=str(market_id))
            continue

        claimed += len(runs)
        market_batches = _group_by_nvr(market_id, runs)
        batches.extend(market_batches)

        # ⚠ NAVBATGA QO'YISH TRANZAKSIYADAN KEYIN (§3.3). `enqueue` ning
        #   O'ZI ham yiqilishi mumkin va u tikni to'xtatmasligi kerak:
        #   qator `running` bo'lib qoladi, ijara tugagach `release_expired`
        #   uni qaytaradi va keyingi tik qayta yuboradi.
        if enqueue is not None:
            for batch in market_batches:
                try:
                    await enqueue(batch)
                except Exception:  # noqa: BLE001 - tik yiqilmasligi SHART
                    log.exception(
                        "capture_batch_not_enqueued",
                        market_id=str(market_id),
                        nvr_id=str(batch.nvr_id),
                        runs=len(batch.run_ids),
                    )

    result = TickResult(
        markets=len(market_ids),
        created=created,
        skipped=skipped,
        released=released,
        claimed=claimed,
        missed=tuple(missed),
        batches=tuple(batches),
    )
    await _write_heartbeat(sessionmaker, result)
    log.info(
        "capture_tick_done",
        markets=result.markets,
        created=result.created,
        skipped=result.skipped,
        released=result.released,
        claimed=result.claimed,
        missed=len(result.missed),
        batches=len(result.batches),
    )
    return result


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], result: TickResult
) -> None:
    """`system_heartbeats['capture_tick']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ XATO YUTILADI (jurnalga yozib). Bu yozuv PROGRESS ko'rsatkichi,
      tikning natijasi EMAS: uning yiqilishi butun kadr olishni to'xtatishi
      mumkin emas. Aynan shu mulohaza `discovery.py::_publish_channels_found`
      va `audit.py::_write_read_audit` da ham bor.

    ⚠ TENANT KONTEKSTI YO'Q va bu ZIDDIYAT EMAS: `system_heartbeats` —
      GLOBAL jadval (`0014`), unda `market_id` ustuni yo'q va RLS
      qo'yilmagan. Kontekst o'rnatish bu yerda hech nimani himoya qilmasdi.

    ⚠⚠ `except Exception` — `SQLAlchemyError` EMAS, VA BU O'LCHANGAN
       QAROR. `discovery.py::_publish_channels_found` `SQLAlchemyError`
       bilan cheklanadi, lekin u tranzaksiya O'RTASIDA chaqiriladi va
       ulanish allaqachon o'rnatilgan bo'ladi. Bu chaqiruv esa tikning
       ENG OXIRIDA yangi ulanish ochadi va o'lchandi: baza xosti
       yechilmasa `socket.gaierror` `SQLAlchemyError` ga O'RALMAYDI —
       u to'g'ridan-to'g'ri chiqadi va butun tikni yiqitardi. Reja
       allaqachon yozilgan, batch'lar allaqachon navbatga qo'yilgan
       bo'lardi, ya'ni yiqilish faqat monitoring yozuvi tufayli bo'lardi.
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=CAPTURE_TICK_COMPONENT,
                detail={
                    "markets": result.markets,
                    "created": result.created,
                    "claimed": result.claimed,
                    "missed": len(result.missed),
                },
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    set_={
                        # ⚠ VAQT DB SOATIDAN (`capture_repo` bilan bir xil
                        #   qoida): `/internal/self-check` yurak urishining
                        #   eskirganini AYNAN o'sha soatga qarab hisoblaydi
                        #   va ikkinchi soat ikki mashinada chegarani
                        #   siljitardi.
                        "last_seen_at": func.now(),
                        "detail": statement.excluded.detail,
                    },
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi tikni yiqita olmaydi
        log.warning("capture_tick_heartbeat_not_written", error=type(exc).__name__)


# ===========================================================================
# 2. BATCH — bitta NVR, semafor + stagger
# ===========================================================================


_GLOBAL_SEMAPHORES: dict[int, asyncio.Semaphore] = {}
"""Jarayon darajasidagi global semafor — HAJM BO'YICHA keshlanadi.

⚠ MODUL DARAJASIDA VA BU MAJBURIY: semafor batch ichida qurilsa u har
  vazifa uchun YANGI bo'lardi va «butun jarayonda bir vaqtda N ta kadr»
  chegarasi UMUMAN mavjud bo'lmasdi. D-08 ning ikki darajali tuzilmasi
  aynan shunga tayanadi: per-NVR semafor bitta qurilmani, global semafor
  esa butun VPS ni himoya qiladi.

⚠ `asyncio.Semaphore` EVENT LOOP GA BOG'LANGAN. Worker jarayonida bitta
  loop bor, ya'ni bu xavfsiz; testda esa har test o'z loopini oladi —
  shuning uchun kesh `hajm -> semafor` xaritasi sifatida qurilgan va u
  yangi loopda ham AYNAN o'sha obyektni beradi. Chegara semantikasi
  o'zgarmaydi, chunki qiymat bir xil.
"""


def _global_semaphore(limit: int) -> asyncio.Semaphore:
    semaphore = _GLOBAL_SEMAPHORES.get(limit)
    if semaphore is None:
        semaphore = asyncio.Semaphore(limit)
        _GLOBAL_SEMAPHORES[limit] = semaphore
    return semaphore


class _Finisher:
    """`failed`/`defer` yozuvining YAGONA joyi — besh xato yo'li uni baham ko'radi.

    `discovery.py::_Finisher` naqshi. `done` to'plami «na muvaffaqiyat, na
    nosozlik yozilmagan» holatini imkonsiz qiladi: batch oxirida unda
    bo'lmagan har bir `run_id` ALBATTA yopiladi.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        market_id: UUID,
        request_id: str,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._market_id = market_id
        self._request_id = request_id
        self.done: set[UUID] = set()

    async def failed(self, run_id: UUID, code: str, detail: str, *, max_attempts: int) -> None:
        """Qatorni yopadi. Bu chaqiruv HECH QACHON ISTISNO KO'TARMAYDI."""
        try:
            async with _system_transaction(
                self._sessionmaker,
                market_id=self._market_id,
                actor_id=None,
                request_id=self._request_id,
            ) as session:
                await CaptureRepository(session, self._market_id).finish_failed(
                    run_id, code, _raw(detail), max_attempts=max_attempts
                )
        except SQLAlchemyError:
            # Oxirgi chegara: nosozlikni YOZA olmadik. Ijara qatorni
            # BARIBIR qaytaradi (`release_expired`), ya'ni slot yo'qolmaydi.
            log.exception("capture_failure_not_recorded", run_id=str(run_id), code=code)
        else:
            self.done.add(run_id)

    async def deferred(self, run_id: UUID, code: str, seconds: int) -> None:
        """Qatorni `pending` da QOLDIRIB kechiktiradi (T-04-35)."""
        try:
            async with _system_transaction(
                self._sessionmaker,
                market_id=self._market_id,
                actor_id=None,
                request_id=self._request_id,
            ) as session:
                await CaptureRepository(session, self._market_id).defer(run_id, seconds, code=code)
        except SQLAlchemyError:
            log.exception("capture_defer_not_recorded", run_id=str(run_id), code=code)
        else:
            self.done.add(run_id)


async def _read_batch_context(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    nvr_id: UUID,
    run_ids: Sequence[UUID],
    request_id: str,
) -> tuple[_BatchContext | None, str | None]:
    """Bitta tranzaksiyada qurilma, rekvizit, kameralar va qatorlarni o'qiydi.

    Returns:
        `(kontekst, xato_kodi)`. Ikkinchisi `None` bo'lmasa batch umuman
        boshlanmaydi va barcha qatorlar o'sha kod bilan yopiladi.
    """
    async with _system_transaction(
        sessionmaker, market_id=market_id, actor_id=None, request_id=request_id
    ) as session:
        nvr_repo = NvrRepository(session, market_id)
        device = await nvr_repo.get_device(nvr_id)
        if device is None:
            return None, CAPTURE_SOURCE_UNREACHABLE

        token = await nvr_repo.get_credential(nvr_id)
        if token is None:
            return None, CAPTURE_CREDENTIAL_UNREADABLE

        cameras = {
            camera.id: (camera.channel_no, camera.stream_name, camera.capture_stream)
            for camera in await nvr_repo.list_cameras(nvr_id)
        }
        claimed = await CaptureRepository(session, market_id).running_by_ids(run_ids)

        scheme = "https" if device.use_tls else "http"
        base_url = f"{scheme}://{device.host}:{device.port}"
        rtsp_host = device.host
        rtsp_port = device.rtsp_port or RTSP_FALLBACK_PORT
        method = device.capture_method
        max_concurrent = device.max_concurrent_captures
        stagger_ms = device.capture_stagger_ms
        observed = device.observed_stream_limit
        username = device.username

    try:
        password = decrypt_nvr_password(token)
    except InvalidToken:
        # ⚠ JURNALGA NA TOKEN, NA UNING BO'LAGI TUSHADI (`discovery.py:428-444`).
        log.error("capture_credential_decrypt_failed", market_id=str(market_id), nvr_id=str(nvr_id))
        return None, CAPTURE_CREDENTIAL_UNREADABLE

    runs: list[_RunContext] = []
    for run in claimed:
        camera = cameras.get(run.camera_id)
        if camera is None:
            # Kamera arxivlangan yoki o'chirilgan: qator qoladi (dalil),
            # lekin kadr olinmaydi. `_finish_unprocessed` uni yopadi.
            continue
        channel_no, stream_name, capture_stream = camera
        runs.append(
            _RunContext(
                run_id=run.id,
                camera_id=run.camera_id,
                channel_no=channel_no,
                stream_name=stream_name,
                capture_stream=capture_stream,
                slot_time=run.slot_time,
                scheduled_at=run.scheduled_at,
                business_date=run.business_date,
            )
        )

    return (
        _BatchContext(
            endpoint=DeviceEndpoint(base_url=base_url, username=username, password=password),
            rtsp_host=rtsp_host,
            rtsp_port=rtsp_port,
            method=method,
            max_concurrent=max_concurrent,
            stagger_ms=stagger_ms,
            observed_stream_limit=observed,
            runs=tuple(runs),
        ),
        None,
    )


async def capture_batch(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    sources: FrameSourcePool,
    *,
    policy: CapturePolicy,
    market_id: UUID,
    nvr_id: UUID,
    run_ids: Sequence[UUID],
) -> BatchResult:
    """Bitta NVR ning qulflab olingan slotlarini bajaradi.

    Har kadr uchun tartib QAT'IY (§B.4):

        kadr -> `analyze()` -> `storage.put()` -> `record()` + `finish_succeeded()`

    ⛔ `CAPTURE_AUTH_LOCKING_CODES` DAGI XATO BUTUN BATCHNI TO'XTATADI.
       Arifmetika shafqatsiz: 25 kamera x 10 tik = 250 muvaffaqiyatsiz
       autentifikatsiya va Hikvision hisobni ~5 urinishdan keyin 30
       daqiqaga QULFLAYDI — undan keyin TO'G'RI PAROL HAM ishlamaydi.
       Qolgan qatorlar o'sha kod bilan DARHOL yopiladi.

    Args:
        sources: worker jarayonining kadr-manba puli (`FrameSourcePool`).
            Klientlar shu yerdan keladi va ular batch uchun qayta
            OCHILMAYDI (`frame_source.py` ning 2-majburiyati).

    Returns:
        `BatchResult` — muvaffaqiyat/nosozlik/kechiktirish sonlari.
    """
    request_id = f"job-capture-batch-{nvr_id}"
    finisher = _Finisher(sessionmaker, market_id=market_id, request_id=request_id)

    try:
        context, blocker = await _read_batch_context(
            sessionmaker,
            market_id=market_id,
            nvr_id=nvr_id,
            run_ids=run_ids,
            request_id=request_id,
        )
    except SQLAlchemyError:
        log.exception("capture_batch_context_failed", market_id=str(market_id), nvr_id=str(nvr_id))
        context, blocker = None, JOB_INTERNAL_ERROR

    if context is None:
        code = blocker or JOB_INTERNAL_ERROR
        await _finish_unprocessed(finisher, run_ids, code, policy=policy)
        return BatchResult(succeeded=0, failed=len(run_ids), deferred=0, stopped_code=None)

    state = _BatchState()
    async with sources.for_device(context.endpoint) as frame_sources:
        await _run_all(
            sessionmaker,
            storage,
            frame_sources,
            policy=policy,
            market_id=market_id,
            context=context,
            finisher=finisher,
            state=state,
        )

    if state.stopped_code is not None:
        await _finish_unprocessed(finisher, run_ids, state.stopped_code, policy=policy)
    else:
        await _finish_unprocessed(finisher, run_ids, JOB_INTERNAL_ERROR, policy=policy)

    await _maybe_lower_limit(
        sessionmaker,
        market_id=market_id,
        nvr_id=nvr_id,
        request_id=request_id,
        context=context,
        state=state,
    )

    log.info(
        "capture_batch_done",
        market_id=str(market_id),
        nvr_id=str(nvr_id),
        succeeded=state.succeeded,
        failed=state.failed,
        deferred=state.deferred,
        stopped_code=state.stopped_code,
    )
    return BatchResult(
        succeeded=state.succeeded,
        failed=state.failed,
        deferred=state.deferred,
        stopped_code=state.stopped_code,
    )


class _BatchState:
    """Batch davomidagi o'zgaruvchan holat — sanoqlar va to'xtatish sababi."""

    __slots__ = ("adaptive_failures", "deferred", "failed", "stopped_code", "succeeded")

    def __init__(self) -> None:
        self.succeeded = 0
        self.failed = 0
        self.deferred = 0
        self.adaptive_failures = 0
        self.stopped_code: str | None = None


async def _run_all(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    frame_sources: Mapping[str, FrameSource],
    *,
    policy: CapturePolicy,
    market_id: UUID,
    context: _BatchContext,
    finisher: _Finisher,
    state: _BatchState,
) -> None:
    """Ikki darajali semafor + stagger ostida barcha slotlarni bajaradi (D-08)."""
    effective = context.max_concurrent
    if context.observed_stream_limit is not None:
        # ⚠ FAQAT PASAYTIRISH. Kuzatilgan chegara sozlamadan KATTA bo'lsa
        #   ham u sozlamani KO'TARMAYDI: admin qo'ygan qiymat yuqori
        #   chegara bo'lib qoladi.
        effective = min(effective, context.observed_stream_limit)
    effective = max(1, effective)

    nvr_semaphore = asyncio.Semaphore(effective)
    global_semaphore = _global_semaphore(policy.global_concurrency)
    stagger = context.stagger_ms / 1000.0

    async def _one(index: int, run: _RunContext) -> None:
        if index and stagger > 0:
            # Cho'qqini yumshatish: 7 slotning har biri AYNI BIR daqiqada
            # 25 kadr talab qiladi va o'rtacha yuk bu yerda yolg'on gapiradi.
            await asyncio.sleep(stagger * index)
        async with global_semaphore, nvr_semaphore:
            if state.stopped_code is not None:
                return
            await _capture_one(
                sessionmaker,
                storage,
                frame_sources,
                policy=policy,
                market_id=market_id,
                context=context,
                run=run,
                finisher=finisher,
                state=state,
            )

    await asyncio.gather(*(_one(index, run) for index, run in enumerate(context.runs)))


async def _capture_one(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    frame_sources: Mapping[str, FrameSource],
    *,
    policy: CapturePolicy,
    market_id: UUID,
    context: _BatchContext,
    run: _RunContext,
    finisher: _Finisher,
    state: _BatchState,
) -> None:
    """Bitta slot: kadr -> sifat -> S3 -> baza. HECH QACHON ISTISNO KO'TARMAYDI."""
    log_context = {
        "market_id": str(market_id),
        "camera_id": str(run.camera_id),
        "run_id": str(run.run_id),
        "slot": run.slot_time.strftime("%H%M"),
    }

    try:
        source = rtsp_url(
            context.rtsp_host,
            context.rtsp_port,
            run.channel_no,
            substream=run.capture_stream == _SUB_STREAM,
        )
        target = CaptureTarget(
            stream_name=run.stream_name,
            channel_no=run.channel_no,
            stream=run.capture_stream,
            rtsp_source=authenticated_rtsp_source(
                source, context.endpoint.username, context.endpoint.password
            ),
        )
        frame = await capture_frame(frame_sources, target, method=context.method)
        captured_at = now_tz()
        report = analyze(frame.data, policy.quality)
        key = object_key(
            market_id=market_id,
            business_date=run.business_date,
            camera_id=run.camera_id,
            slot_time=run.slot_time,
        )
        stored = await storage.put(key, frame.data)
    except CaptureError as error:
        # TANILGAN sabab — kod ALLAQACHON allowlist'dan o'tgan
        # (`CaptureError.__init__`), ya'ni u to'g'ridan-to'g'ri yoziladi.
        log.info("capture_failed", error_code=error.code, **log_context)
        await _record_failure(finisher, run.run_id, error.code, error.detail, policy=policy)
        _account(state, error.code)
        return
    except StorageError as error:
        # ⚠ `snapshots` QATORI YOZILMAYDI: kadr olindi, lekin obyekt
        #   omborda YO'Q. Qator yozilsa u mavjud bo'lmagan dalilga havola
        #   qilardi (§B.4, T-04-54). Qayta urinish ARZON — kadr allaqachon
        #   olingan, faqat yuklash takrorlanadi.
        log.warning("capture_storage_failed", error=str(error), **log_context)
        await _record_failure(
            finisher, run.run_id, CAPTURE_STORAGE_UNAVAILABLE, str(error), policy=policy
        )
        state.failed += 1
        return
    except Exception as exc:  # noqa: BLE001 - job jarayoni yiqilmasligi SHART
        log.exception("capture_crashed", **log_context)
        await _record_failure(
            finisher, run.run_id, JOB_INTERNAL_ERROR, type(exc).__name__, policy=policy
        )
        state.failed += 1
        return

    try:
        async with _system_transaction(
            sessionmaker,
            market_id=market_id,
            actor_id=None,
            request_id=f"job-capture-{run.business_date.isoformat()}-"
            f"{run.slot_time.strftime('%H%M')}",
        ) as session:
            snapshot_id = await SnapshotRepository(session, market_id).record(
                capture_run_id=run.run_id,
                camera_id=run.camera_id,
                scheduled_at=run.scheduled_at,
                captured_at=captured_at,
                slot_time=run.slot_time,
                object_key=key,
                size_bytes=stored.size_bytes,
                quality_verdict=report.verdict,
                quality_mean=report.mean,
                quality_stddev=report.stddev,
                quality_saturation=report.saturation,
                quality_thresholds_version=report.thresholds_version,
                light_mode=report.light_mode,
                capture_method=frame.method,
                etag=stored.etag,
                width=report.width,
                height=report.height,
            )
            await CaptureRepository(session, market_id).finish_succeeded(
                run.run_id, snapshot_id=snapshot_id, method=frame.method
            )
    except Exception as exc:  # noqa: BLE001 - job jarayoni yiqilmasligi SHART
        log.exception("capture_record_failed", **log_context)
        await _record_failure(
            finisher, run.run_id, JOB_INTERNAL_ERROR, type(exc).__name__, policy=policy
        )
        state.failed += 1
        return

    finisher.done.add(run.run_id)
    state.succeeded += 1
    log.info(
        "capture_succeeded",
        verdict=report.verdict,
        light_mode=report.light_mode,
        method=frame.method,
        elapsed_ms=frame.elapsed_ms,
        size_bytes=stored.size_bytes,
        **log_context,
    )


def _account(state: _BatchState, code: str) -> None:
    """Sanoqlarni va adaptiv qaror uchun hisoblagichni yangilaydi."""
    if code in CAPTURE_DEFER_CODES:
        state.deferred += 1
    else:
        state.failed += 1
    if code in _ADAPTIVE_FAILURE_CODES:
        state.adaptive_failures += 1
    if code in CAPTURE_AUTH_LOCKING_CODES:
        # ⛔ BUTUN BATCH TO'XTAYDI. Qolgan kameralarga BORILMAYDI —
        #    modul docstringidagi qulflash arifmetikasi.
        state.stopped_code = code


async def _record_failure(
    finisher: _Finisher,
    run_id: UUID,
    code: str,
    detail: str,
    *,
    policy: CapturePolicy,
) -> None:
    """`defer` va `failed` orasidagi YAGONA tarmoqlanish nuqtasi.

    ⚠ `capture_stream_limit` da `defer()` chaqiriladi, `finish_failed()`
      EMAS: NVR shunchaki BAND. Oqim bo'shagach kadr olish muvaffaqiyatli
      bo'ladi, ya'ni slotni tashlab yuborish «NVR band edi» sababini
      «kadr yo'q» ga aylantirardi.
    """
    if code in CAPTURE_DEFER_CODES:
        await finisher.deferred(run_id, code, policy.lease_seconds)
        return
    await finisher.failed(run_id, code, detail, max_attempts=policy.max_attempts)


async def _finish_unprocessed(
    finisher: _Finisher,
    run_ids: Sequence[UUID],
    code: str,
    *,
    policy: CapturePolicy,
) -> None:
    """Yopilmagan har bir qatorni `code` bilan yopadi.

    `_Finisher.done` to'plami «na muvaffaqiyat, na nosozlik yozilmagan»
    holatini imkonsiz qiladi: batch qanday tugashidan qat'i nazar HAR BIR
    `run_id` yakuniy holatga keladi.
    """
    for run_id in run_ids:
        if run_id in finisher.done:
            continue
        await finisher.failed(run_id, code, f"batch: {code}", max_attempts=policy.max_attempts)


async def _maybe_lower_limit(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    nvr_id: UUID,
    request_id: str,
    context: _BatchContext,
    state: _BatchState,
) -> None:
    """ADAPTIV PASAYTIRISH — faqat pastga va faqat qattiq shart ostida.

    ⛔ IKKI SHART VA IKKALASI HAM MAJBURIY:
       1. kamida IKKI kamera chegara alomatli kod bilan yiqildi;
       2. kamida BITTASI muvaffaqiyatli bo'ldi.

    Ikkinchi shartsiz tunnel uzilgan holat «NVR chegarasi» deb NOTO'G'RI
    talqin qilinardi: hamma kamera yiqilganda tizim chegarani `0` ga
    yaqinlashtirib, o'zini butunlay to'xtatib qo'yardi.

    ⛔ AVTOMATIK OSHIRISH YO'Q. Muvaffaqiyatdan keyin chegarani ko'tarish
       tebranish beradi: chegaraga uriladi -> pasaytiradi -> muvaffaqiyat
       -> ko'taradi -> yana uriladi. Har tsikl NVR ga muvaffaqiyatsiz
       sessiya urinishi va KADRSIZ SLOT narxida tushardi. Qiymatni
       ko'tarish — ODAMNING qarori.
    """
    if state.adaptive_failures < _ADAPTIVE_FAILURE_FLOOR or state.succeeded < 1:
        return
    current = context.observed_stream_limit
    if current is not None and current <= state.succeeded:
        return

    try:
        async with _system_transaction(
            sessionmaker, market_id=market_id, actor_id=None, request_id=request_id
        ) as session:
            await NvrRepository(session, market_id).update_device(
                nvr_id, observed_stream_limit=state.succeeded
            )
    except SQLAlchemyError:
        log.exception("capture_observed_limit_not_written", nvr_id=str(nvr_id))
        return

    log.warning(
        "capture_observed_limit_lowered",
        nvr_id=str(nvr_id),
        observed_stream_limit=state.succeeded,
        failures=state.adaptive_failures,
    )
