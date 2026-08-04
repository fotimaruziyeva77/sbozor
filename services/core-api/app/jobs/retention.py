"""Saqlash siyosati — siqish, arxivdan chiqarish va yetim obyekt supurgisi (CAM-07, D-18).

=============================================================================
TO'RT QAROR — VA ULARNING HAMMASI SHU FAYLNING SHAKLINI BELGILAYDI.

1. NAVBAT KUTUBXONASI IMPORT QILINMAYDI (S-4, D-06).

   Bu modul — sof `async def`. `taskiq` FAQAT `app/worker.py` da ko'rinadi
   va u yerda yupqa qobiq shaklida. Sabab `worker.py` ning modul
   docstringida to'liq yozilgan: mexanizm almashtirilsa ko'chirish narxi
   O'SHA fayl bo'lishi kerak, saqlash siyosati emas.

2. ⛔ QATOR HECH QACHON O'CHIRILMAYDI.

   455 kundan keyin OBYEKT arxivdan chiqariladi, `snapshots` QATORI esa
   joyida qoladi: `storage_tier='purged'`, `object_deleted_at` to'ldiriladi
   va u «kadr mavjud edi, arxivdan <sana> da chiqarildi» deb HALOL
   ko'rsatiladi.

   Sabab 6-fazada (BILL-02): `daily_charges` dalil-kadrga bog'lanadi, ya'ni
   qatorni yo'q qilish hisob yozuvining dalil havolasini uzardi. Shuning
   uchun bu modulda qator yo'qotadigan SQL ham, `snapshot_repo` ning bunday
   metodi ham YO'Q — `SnapshotRepository` da bunday metod umuman mavjud
   emas (`snapshot_repo.py` ning 1-qoidasi), ya'ni taqiq KELISHUV emas,
   STRUKTURA.

   `is_billable` ham O'ZGARMAYDI: u hosila ustun, texnik jihatdan ham
   yozib bo'lmaydi — lekin qoidaning mazmuni kengroq: o'sha paytda qilingan
   hisob retroaktiv bekor qilinmaydi.

3. ⛔ SIQISH MANBAI — FAQAT `full` QATLAM, VA BU QAT'IY SHART (Pitfall 13).

   JPEG qayta kodlash YO'QOTISHLI. Ikki marta siqilgan kadr ikki marta
   buziladi va avlod yo'qotishi TO'PLANADI. `retention_candidates(...,
   tier=COMPRESSIBLE_TIER)` bu holatni STRUKTURAVIY to'sadi: `compressed`
   qator predikatga umuman tushmaydi. Shart «tozalik» emas, DARVOZA.

4. VAQT IN'EKTSIYA QILINADI — `today: date | None = None`.

   Ikki sabab va ikkalasi ham majburiy:

     * loyiha qoidasi (`sbozor_core/timeutil.py`): konteynerlar UTC
       soatida ishlaydi va mahalliy 00:00-04:59 oralig'ida stdlib ning
       sana funksiyasi OLDINGI kunni qaytaradi — retention esa aynan
       03:20 da ishlaydi, ya'ni u AYNAN shu oynaning ichida;
     * testlanuvchanlik: 90 kunni kutmasdan isbotlashning butun mexanizmi
       shu argument (`retention_full_days=0` + `today=<bugun>`).

   Shuning uchun bu modulning ichida joriy sanani stdlib dan olish
   TAQIQLANGAN va uning o'rnini `business_today()` egallaydi.
=============================================================================

=============================================================================
NEGA BU YERDA CRON QABUL QILINADI, KADR OLISHDA ESA YO'Q (§D.10).

Farq nozik va u yozib qo'yilishi kerak:

    | Xususiyat            | Kadr olish sloti      | Retention          |
    |----------------------|-----------------------|--------------------|
    | Vazifa turi          | VAQT NUQTASI          | KONVERGENT         |
    | Bir kun o'tkazilsa   | ma'lumot YO'QOLADI    | ertaga o'zi tutadi |
    | Planer xotira holati | HALOKATLI             | AHAMIYATSIZ        |

Retention predikati HOLAT ustida («`full` va 90 kundan eski hamma narsani
siq»), vaqt ustida emas. Shuning uchun o'tkazib yuborilgan yugurish
ertangi yugurish tomonidan to'liq qoplanadi va `taskiq` ning xotiradagi
cron holati bu yerda hech nimani buzmaydi.
=============================================================================

=============================================================================
KICHRAYTIRISH YO'Q — FAQAT QAYTA KODLASH.

CAM-07 «siqilgan» deydi, «kichraytirilgan» emas. O'lchamni kamaytirish:

  * geometriyani buzadi — 5-fazadagi zona poligonlari kadr piksellariga
    bog'langan va ular bilan mos kelmay qolardi;
  * kelajakda CV ni ARXIV ustida qayta ishga tushirish imkonini butunlay
    yo'qotadi (fine-tune qilingan model eski kadrlarni qayta baholay
    olmasdi).

Shuning uchun bu modulda `Image` ning o'lcham o'zgartiruvchi metodlari
UMUMAN chaqirilmaydi va matn darvozasi buni tekshiradi.
=============================================================================

=============================================================================
KALIT O'ZGARMAYDI — SIQILGAN VERSIYA O'SHA KALITNING USTIGA YOZILADI.

`object_key` — 6-fazadagi dalil havolasining O'ZI. Yangi kalit yozish
(masalan `.../0630-compressed.jpg`) eski havolani uzardi va «kadr bor,
lekin uni ko'rsatib bo'lmaydi» holatini tug'dirardi. `mark_compressed()`
ham aynan shu sababdan FAQAT hajmni yangilaydi.
=============================================================================
"""

from __future__ import annotations

import io
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Final

import structlog
from PIL import Image, UnidentifiedImageError
from sbozor_core.enums import ActorKind
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.models.snapshot import Snapshot
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.snapshot_repo import (
    COMPRESSIBLE_TIER,
    PURGEABLE_TIERS,
    RetentionCandidate,
    SnapshotRepository,
)
from app.services.object_key import KEY_PREFIX_FOR_DAY
from app.services.storage import StorageError, orphan_keys

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.services.storage import SnapshotStorage

log = structlog.get_logger(__name__)

__all__ = [
    "RETENTION_COMPONENT",
    "RetentionPolicy",
    "RetentionResult",
    "active_market_ids",
    "disk_usage_percent",
    "retention_daily",
]


RETENTION_COMPONENT: Final[str] = "retention"
"""`system_heartbeats.component` — `alert_sweep` ning `retention_stale` manbai.

⚠ SATR IKKI JOYDA O'QILADI: bu modul uni YOZADI, `app/jobs/alerting.py`
  esa uning eskirganini o'lchaydi. Ikkalasi ham SHU konstantani import
  qiladi — qo'lda yozilgan literal bir kun jimgina ajralib ketardi va
  `retention_stale` alerti HECH QACHON tug'ilmasdi (xato yo'q, jurnal
  yozuvi yo'q, faqat sukunat).
"""

_JOB_REQUEST_ID_PREFIX: Final[str] = "job-retention-"
"""Deterministik `request_id` prefiksi — bitta yugurishning audit qatorlari BIR IPDA.

`capture.py::_tick_request_id` bilan bir xil qoida: tasodifiy qiymat har
tranzaksiyada boshqa bo'lardi va bitta yugurishning yozuvlarini bog'lash
imkonsiz bo'lardi.
"""

_ACTIVE_MARKETS = text(
    "SELECT market_id FROM auth_list_markets_full() WHERE is_active ORDER BY market_id"
)
"""Retention ko'radigan bozorlar — `SECURITY DEFINER`, TENANT KONTEKSTISIZ.

=============================================================================
NEGA `capture_due_markets()` EMAS — VA BU O'LCHANGAN FARQ.

`capture_due_markets()` ning ta'rifi «QAYSI BOZORDA HOZIR ISH BOR»: uning
uchala disjunkti ham bugungi kadr olish rejasiga qaraydi. Retention esa
03:20 da, kadr olish oynasidan TASHQARIDA ishlaydi va uning ishi bugungi
rejaga UMUMAN bog'liq emas — u 90 va 455 kun oldingi kadrlarni ko'radi.

Ikkalasini bog'lash JIM NOSOZLIK berardi: tik rejani materializatsiya
qilib bo'lgan bozor `capture_due_markets()` dan CHIQMAYDI (ikkinchi
disjunkt `NOT EXISTS bugungi reja` yolg'onga aylanadi), ya'ni retention
o'sha bozorni umuman ko'rmasdi. Xato yo'q, jurnal yozuvi yo'q — faqat
disk asta-sekin to'lardi va nosozlik oylar keyin ko'rinardi.

`auth_list_markets_full()` — `capture_due_markets()` ning QO'SHNISI va
u ham `SECURITY DEFINER` + `STABLE`, ya'ni yuzasi tor: bozor
KONFIGURATSIYASI (id, nom, mintaqa, faollik) va bironta tenant ma'lumoti
emas. Undan KEYINGI har bir so'rov odatdagidek RLS ostidan o'tadi.
=============================================================================
"""


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Retention uchun kerak bo'lgan BARCHA sozlama — bitta obyektda.

    ⚠ `Settings` NING O'ZI UZATILMAYDI va bu `CapturePolicy` (04-07) hamda
      `QualityThresholds` (04-04) bilan aynan bir xil qaror: job sozlamalar
      obyektining butun yuzasini ko'rmasligi kerak. Shunda uni testda
      qurish uchun `DATABASE_URL`/`JWT_SECRET`/`NVR_CREDENTIAL_KEY` kerak
      bo'lmaydi va `retention_full_days=0` bilan o'lchash BITTA qatorga
      tushadi — 90 kunni kutmasdan isbotlashning butun mexanizmi shu.

    Tarjima (`Settings` -> `RetentionPolicy`) `app/worker.py` da, bu yerda
    emas.
    """

    full_days: int
    """`full` qatlamda saqlash muddati (D-18 standarti: 90)."""

    compressed_days: int
    """`compressed` qatlamda QO'SHIMCHA muddat (D-18 standarti: 365).

    ⚠ Arxivdan chiqarish chegarasi — `full_days + compressed_days` = 455
      kun, `compressed_days` ning O'ZI emas. Ikkala qiymat ham `Settings`
      da va D-18 ning butun mazmuni shu: buyurtmachi javobiga qarab BITTA
      SON o'zgaradi, kod emas.
    """

    jpeg_quality: int
    """Qayta kodlash sifati (Pillow shkalasi)."""

    batch_size: int
    """Bitta yugurishda, bitta bozorda, bitta qadamda ko'riladigan qator soni."""

    disk_path: str = "/"
    """Disk to'lishini o'lchaydigan yo'l — `alert_sweep` bilan bir xil manba."""


@dataclass(slots=True)
class RetentionResult:
    """Bitta yugurishning O'LCHANADIGAN natijasi.

    ⛔ NOL QIYMAT — NATIJA, UNING YO'QLIGI EMAS (`DaySummary` bilan bir xil
    qoida). Har maydon HAR DOIM to'ldiriladi, ya'ni «bugun hech nima
    siqilmadi» bilan «siqish umuman ishlamadi» bir xil ko'rinmaydi:
    birinchisida `errors == 0`, ikkinchisida yo'q.
    """

    markets: int = 0
    compressed: int = 0
    purged: int = 0
    orphans_deleted: int = 0
    bytes_saved: int = 0
    not_smaller: int = 0
    """Qayta kodlash hajmni KAMAYTIRMAGAN kadrlar soni.

    Ular baribir `compressed` deb belgilanadi (pastdagi `_recompress`
    docstringi), aks holda ular HAR KECHA qayta urinilardi va har safar
    yana bir avlod yo'qotardi.
    """

    errors: list[str] = field(default_factory=list)
    """Yutilgan xatolarning TURLARI — matnlari EMAS.

    Istisno matni ombor manzilini yoki obyekt kalitini tashishi mumkin
    (04-06 ning o'lchovi: `EndpointConnectionError` to'liq URL beradi).
    Diagnostika uchun tur va sanoq yetadi.
    """


async def retention_daily(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    *,
    policy: RetentionPolicy,
    today: date | None = None,
) -> RetentionResult:
    """Uch qadam: siqish, arxivdan chiqarish va yetim obyekt supurgisi.

    ⚠ JOB HECH QACHON YIQILMAYDI. Bitta kadrning (yoki bitta bozorning)
      xatosi qolganlarini to'xtatmaydi: u `log.warning` bilan yutiladi va
      `RetentionResult.errors` ga yoziladi. Sabab konvergentlikda —
      bugungi yugurishda o'tkazib yuborilgan kadr ertaga o'sha predikatga
      qaytadan tushadi, ya'ni yo'qotish YO'Q. Yiqilgan job esa BUTUN
      o'rnatmaning saqlash siyosatini to'xtatardi.

    Args:
        sessionmaker: sessiya fabrikasi. ARGUMENT, modul globali EMAS
            (`discovery.py::discover_nvr` bilan bir xil qoida).
        storage: ochiq ombor qobig'i (worker resursi, `worker.py`).
        policy: muddatlar, sifat va partiya hajmi.
        today: hisob boshlanadigan biznes-kun. ARGUMENT — modul
            docstringining 4-qarori.

    Returns:
        `RetentionResult` — sonlar va yutilgan xato TURLARI.
    """
    day = today if today is not None else business_today()
    request_id = f"{_JOB_REQUEST_ID_PREFIX}{day.isoformat()}"

    result = RetentionResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Yugurish BOSHLANA olmadi. Iz jurnalda qoladi; ertangi yugurish
        # AYNAN shu ishni bajaradi (konvergentlik), ya'ni yo'qotish yo'q.
        log.exception("retention_market_list_failed")
        market_ids = []

    result.markets = len(market_ids)

    for market_id in market_ids:
        await _compress_market(
            sessionmaker,
            storage,
            market_id=market_id,
            request_id=request_id,
            day=day,
            policy=policy,
            result=result,
        )
        await _purge_market(
            sessionmaker,
            storage,
            market_id=market_id,
            request_id=request_id,
            day=day,
            policy=policy,
            result=result,
        )
        await _sweep_orphans(
            sessionmaker,
            storage,
            market_id=market_id,
            request_id=request_id,
            day=day,
            result=result,
        )

    await _write_heartbeat(sessionmaker, result)
    log.info(
        "retention_daily_done",
        markets=result.markets,
        compressed=result.compressed,
        purged=result.purged,
        orphans_deleted=result.orphans_deleted,
        bytes_saved=result.bytes_saved,
        not_smaller=result.not_smaller,
        errors=len(result.errors),
    )
    return result


# ===========================================================================
# Bozorlar ro'yxati va tranzaksiya chegarasi
# ===========================================================================


async def active_market_ids(sessionmaker: async_sessionmaker[AsyncSession]) -> list[UUID]:
    """Faol bozorlar — FAQAT identifikator, tenant kontekstisiz.

    =========================================================================
    ⚠⚠ OMMAVIY VA `app/jobs/alerting.py` UNI IMPORT QILADI — NEGA NUSXA EMAS.

    Bu chaqiruv `SECURITY DEFINER` funksiyaga boradi, ya'ni u RLS'ni CHETLAB
    O'TADI. Xavfsizlik yuzasi esa AYNAN BITTA chaqiruv nuqtasiga ega
    bo'lishi kerak: yuzani toraytirish (masalan `is_active` dan tashqari
    yana bir shart qo'shish) kelajakda BITTA qatorlik o'zgarish bo'lib
    qolsin va u ikkinchi, unutilgan nusxada eskirmasin.

    ⚠ BU `_tenant_session` DAN FARQ QILADI va farq ataylab: o'sha kontekst
      menejeri xavfsizlik YUZASI emas, STRUKTURAVIY naqsh — u
      `discovery.py`, `capture.py` va bu ikki modulda ATAYIN takrorlangan
      (jobning O'ZI hech kimga bog'lanmasligi uchun). Chetlab o'tuvchi
      so'rov esa takrorlanmaydi.
    =========================================================================
    """
    async with sessionmaker() as session, session.begin():
        result = await session.execute(_ACTIVE_MARKETS)
        return [row.market_id for row in result]


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN qisqa tranzaksiya.

    `jobs/discovery.py::_system_transaction()` va `jobs/capture.py` dagi
    jufti bilan AYNAN bir xil uch farq: `Principal` yo'q, `actor_kind` —
    `SYSTEM`, `HTTPException` yo'q (worker'da javob beriladigan mijoz yo'q).

    ⚠ NUSXA EMAS, JUFT. Import yo'nalishi `retention -> discovery` bo'lardi
      va u ikki mustaqil jobni bir-biriga bog'lardi (kashfiyot o'zgarganda
      saqlash siyosati ham qayta ko'rilishi kerak bo'lardi). Shakl bir xil,
      egasi boshqa — `capture.py` da ham aynan shunday.

    ⚠ HAR CHAQIRUVDA YANGI TRANZAKSIYA VA YANGI KONTEKST. GUC'lar
      `SET LOCAL` bilan qo'yiladi va `COMMIT` da tozalanadi.

    ⚠⚠ TRANZAKSIYA QISQA VA OMBOR CHAQIRUVI UNING ICHIDA EMAS. Bitta kadrni
       qayta kodlash ombordan o'qish + yozishni talab qiladi va ular bitta
       partiyada 200 marta takrorlanadi. Ularni tranzaksiya ichiga solish
       Postgres ulanishini daqiqalar davomida ushlab turardi va
       `capture_tick` ning har daqiqalik ishiga bevosita raqobat bo'lardi.
       Shuning uchun har qadam IKKI tranzaksiya oladi: nomzodlarni o'qish
       va natijani yozish.
    """
    # SIM117 `discovery.py:194-196` dagi bilan bir xil sababdan rad etilgan:
    # ichki blok TRANZAKSIYA chegarasi.
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


# ===========================================================================
# 1-QADAM — SIQISH
# ===========================================================================


async def _compress_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    *,
    market_id: UUID,
    request_id: str,
    day: date,
    policy: RetentionPolicy,
    result: RetentionResult,
) -> None:
    """`full` qatlamdagi eski kadrlarni qayta kodlaydi.

    ⛔ NOMZODLAR FAQAT `COMPRESSIBLE_TIER` DAN — modul docstringining
       3-qarori. Bu satrni `PURGEABLE_TIERS` ga kengaytirish ikki marta
       siqishni ochib yuborardi.
    """
    older_than = day - timedelta(days=policy.full_days)

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            candidates = await SnapshotRepository(session, market_id).retention_candidates(
                older_than=older_than,
                tier=COMPRESSIBLE_TIER,
                limit=policy.batch_size,
            )
    except SQLAlchemyError as exc:
        _swallow(result, "retention_compress_candidates_failed", exc, market_id=market_id)
        return

    if not candidates:
        return

    # ⚠ OMBOR ISHI TRANZAKSIYADAN TASHQARIDA (`_tenant_session` docstringi).
    compressed: list[tuple[RetentionCandidate, int]] = []
    for candidate in candidates:
        outcome = await _recompress(storage, candidate, quality=policy.jpeg_quality)
        if outcome is None:
            result.errors.append("recompress_failed")
            continue
        new_size, changed = outcome
        if not changed:
            result.not_smaller += 1
        compressed.append((candidate, new_size))

    if not compressed:
        return

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            repo = SnapshotRepository(session, market_id)
            for candidate, new_size in compressed:
                if await repo.mark_compressed(candidate.id, size_bytes=new_size):
                    result.compressed += 1
                    result.bytes_saved += max(candidate.size_bytes - new_size, 0)
    except SQLAlchemyError as exc:
        _swallow(result, "retention_compress_mark_failed", exc, market_id=market_id)


async def _recompress(
    storage: SnapshotStorage,
    candidate: RetentionCandidate,
    *,
    quality: int,
) -> tuple[int, bool] | None:
    """Bitta kadrni qayta kodlaydi va O'SHA KALITNING USTIGA yozadi.

    ⚠ KICHRAYTIRISH YO'Q — modul docstringining tegishli bo'limi. Faqat
      qayta kodlash, ya'ni piksel o'lchamlari O'ZGARMAYDI va 5-fazadagi
      zona poligonlari joyida qoladi.

    ⚠ NATIJA KATTAROQ CHIQSA OBYEKT TEGILMAYDI, LEKIN QATOR BARIBIR
      `compressed` DEB BELGILANADI. Ikkinchi qism majburiy: aks holda
      o'sha kadr HAR KECHA qayta urinilardi va har safar yana bir avlod
      yo'qotardi — ya'ni «ehtiyotkorlik» aynan o'zi oldini olayotgan
      zararni keltirardi. Hodisa jurnalga chiqadi va sanoqda ko'rinadi.

    Returns:
        `(yangi_hajm, obyekt_qayta_yozildimi)` yoki xatoda `None`.
    """
    try:
        original = await storage.get(candidate.object_key)
    except StorageError as exc:
        log.warning("retention_read_failed", error=type(exc).__name__)
        return None

    try:
        encoded = _encode(original, quality=quality)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Buzuq arxiv obyekti — siyosat uni «tuzatolmaydi». Kadr `full`
        # bo'lib qoladi va 455 kundan keyin arxivdan chiqariladi
        # (`PURGEABLE_TIERS` da `full` ATAYIN bor).
        log.warning("retention_decode_failed", error=type(exc).__name__)
        return None

    if len(encoded) >= len(original):
        log.info(
            "retention_recompress_not_smaller",
            before=len(original),
            after=len(encoded),
        )
        return len(original), False

    try:
        put = await storage.put(candidate.object_key, encoded)
    except StorageError as exc:
        log.warning("retention_write_failed", error=type(exc).__name__)
        return None

    return put.size_bytes, True


def _encode(data: bytes, *, quality: int) -> bytes:
    """JPEG -> JPEG qayta kodlash, o'lchamlar O'ZGARMAGAN holda.

    `optimize=True` Huffman jadvallarini kadr uchun qayta hisoblaydi,
    `progressive=True` esa skanlarni qayta tartiblaydi — ikkalasi ham
    piksel ma'lumotiga TEGMAYDI va ikkalasi ham hajmni kamaytiradi.
    Sifatni tushiradigan yagona parametr — `quality`.
    """
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        # JPEG palitrali va alfa kanalli rejimlarni saqlay olmaydi. Kul
        # rang (`L`) va `CMYK` ATAYIN o'zgartirilmaydi: ularni `RGB` ga
        # o'girish hajmni OSHIRARDI va IR-tundagi kadrlarning aksariyati
        # aynan kul rang.
        source = image if image.mode in {"RGB", "L", "CMYK", "YCbCr"} else image.convert("RGB")
        buffer = io.BytesIO()
        source.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


# ===========================================================================
# 2-QADAM — ARXIVDAN CHIQARISH (obyekt ketadi, QATOR QOLADI)
# ===========================================================================


async def _purge_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    *,
    market_id: UUID,
    request_id: str,
    day: date,
    policy: RetentionPolicy,
    result: RetentionResult,
) -> None:
    """`full_days + compressed_days` dan oshgan kadrlarning OBYEKTINI o'chiradi.

    ⚠ NOMZODLAR `PURGEABLE_TIERS` NING HAR IKKALA A'ZOSIDAN olinadi va bu
      `snapshot_repo.py::PURGEABLE_TIERS` ning O'Z docstringidagi sababdir:
      siqish bosqichini o'tkazib yuborgan kadr (ombor xatosi, buzuq obyekt,
      `retention_full_days` juda katta) ham 455 kundan keyin arxivdan
      chiqarilishi kerak. Faqat `compressed` ni olish ularni MANGU saqlab
      qolardi — jimgina, chunki hech qanday xato chiqmasdi.

    ⛔ QATOR O'CHIRILMAYDI (modul docstringining 2-qarori). `mark_purged()`
       ikkita ustunni yangilaydi, boshqa hech nima qilmaydi.
    """
    older_than = day - timedelta(days=policy.full_days + policy.compressed_days)

    candidates: list[RetentionCandidate] = []
    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            repo = SnapshotRepository(session, market_id)
            for tier in PURGEABLE_TIERS:
                candidates.extend(
                    await repo.retention_candidates(
                        older_than=older_than, tier=tier, limit=policy.batch_size
                    )
                )
    except SQLAlchemyError as exc:
        _swallow(result, "retention_purge_candidates_failed", exc, market_id=market_id)
        return

    if not candidates:
        return

    try:
        # ⚠ `delete_many` `Quiet` ISHLATMAYDI (04-06 ning o'lchovi:
        #   `Quiet=True` bilan SeaweedFS javobda na `Deleted`, na `Errors`
        #   qaytaradi). Ya'ni bu chaqiruv HAQIQIY sanoq beradi va qisman
        #   nosozlikda YIQILADI — «hammasi o'chdi» degan har kechalik
        #   yolg'on shu bilan yopiladi.
        await storage.delete_many([candidate.object_key for candidate in candidates])
    except StorageError as exc:
        # Fail-closed: obyekt o'chmagan bo'lsa qator `purged` deb
        # BELGILANMAYDI. Teskarisi «kadr arxivdan chiqarildi» deb yozib,
        # obyektni omborda qoldirardi — ya'ni baza yolg'on gapirardi.
        _swallow(result, "retention_purge_delete_failed", exc, market_id=market_id)
        return

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            repo = SnapshotRepository(session, market_id)
            for candidate in candidates:
                if await repo.mark_purged(candidate.id):
                    result.purged += 1
    except SQLAlchemyError as exc:
        _swallow(result, "retention_purge_mark_failed", exc, market_id=market_id)


# ===========================================================================
# 3-QADAM — YETIM OBYEKT SUPURGISI (AYNAN BITTA KUN)
# ===========================================================================


_ORPHAN_SWEEP_LAG_DAYS: Final[int] = 1
"""Supurgi KECHAGI kunni ko'radi, bugungisini EMAS.

Bugungi kun HALI YOZILAYAPTI: `capture_batch` avval obyektni yozadi, keyin
`snapshots` qatorini (§B.4 ning qat'iy tartibi). Ikkisining orasida
turgan obyekt bugungi prefiksda YETIM bo'lib ko'rinadi va supurgi uni
o'chirsa, bir soniyadan keyin yoziladigan baza qatori MAVJUD BO'LMAGAN
obyektga havola qilardi — ya'ni supurgi aynan o'zi himoya qilishi kerak
bo'lgan dalil zanjirini uzardi.
"""


async def _sweep_orphans(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    *,
    market_id: UUID,
    request_id: str,
    day: date,
    result: RetentionResult,
) -> None:
    """Omborda bor, bazada yo'q obyektlarni o'chiradi — FAQAT bitta kun.

    ⚠ «OMBOR BO'YLAB QIDIRUV» EMAS (04-06 ning chegarasi): `orphan_keys`
      FAQAT `KEY_PREFIX_FOR_DAY()` ning chiqishini qabul qiladi va erkin
      prefiksni `ValueError` bilan rad etadi. Butun omborni skanlash 455
      kunlik arxivda million obyektga aylanardi va u kunlik jobning
      byudjetiga umuman sig'masdi.

    ⚠ `purged` QATORLAR `expected` GA KIRMAYDI va bu ATAYIN: ularning
      obyekti O'CHIRILGAN bo'lishi kerak. Omborda qolgan nusxa — o'chirish
      yarim yo'lda uzilganining alomati va u AYNAN yetim.
    """
    target = day - timedelta(days=_ORPHAN_SWEEP_LAG_DAYS)
    prefix = KEY_PREFIX_FOR_DAY(market_id=market_id, business_date=target)

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            rows = await session.execute(
                select(Snapshot.object_key).where(
                    Snapshot.market_id == market_id,
                    Snapshot.business_date == target,
                    Snapshot.object_deleted_at.is_(None),
                )
            )
            expected = {row.object_key for row in rows}
    except SQLAlchemyError as exc:
        _swallow(result, "retention_orphan_expected_failed", exc, market_id=market_id)
        return

    try:
        orphans = await orphan_keys(storage, prefix=prefix, expected=expected)
        if orphans:
            result.orphans_deleted += await storage.delete_many(orphans)
    except StorageError as exc:
        _swallow(result, "retention_orphan_sweep_failed", exc, market_id=market_id)


# ===========================================================================
# Yurak urishi va xato yutish
# ===========================================================================


def _swallow(
    result: RetentionResult,
    event: str,
    exc: Exception,
    *,
    market_id: UUID,
) -> None:
    """Xatoni YUTADI va uni SANOQQA aylantiradi.

    ⚠ ISTISNO MATNI JURNALGA YOZILMAYDI, faqat TURI. 04-06 o'lchagan:
      `EndpointConnectionError` matni to'liq URL'ni — bucket va OBYEKT
      KALITI bilan — tashiydi. Kalit esa bozor identifikatorini va kamera
      identifikatorini o'z ichiga oladi.
    """
    name = type(exc).__name__
    result.errors.append(f"{event}:{name}")
    log.warning(event, market_id=str(market_id), error=name)


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], result: RetentionResult
) -> None:
    """`system_heartbeats['retention']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ XATO YUTILADI. Bu yozuv PROGRESS ko'rsatkichi, yugurishning natijasi
      EMAS — `capture.py::_write_heartbeat` bilan aynan bir xil qoida va
      aynan bir xil `except Exception` (o'sha yerda o'lchangan: yangi
      ulanish ochilganda `socket.gaierror` `SQLAlchemyError` ga
      O'RALMAYDI).

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval.
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=RETENTION_COMPONENT,
                detail={
                    "markets": result.markets,
                    "compressed": result.compressed,
                    "purged": result.purged,
                    "orphans_deleted": result.orphans_deleted,
                    "errors": len(result.errors),
                },
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    # ⚠ VAQT DB SOATIDAN: `alert_sweep` eskirishni AYNAN
                    #   o'sha soatga qarab hisoblaydi.
                    set_={"last_seen_at": func.now(), "detail": statement.excluded.detail},
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi jobni yiqita olmaydi
        log.warning("retention_heartbeat_not_written", error=type(exc).__name__)


def disk_usage_percent(path: str) -> float:
    """Diskning band ulushi (0..100) — `alert_sweep` ning `disk_pressure` manbai.

    ⚠ SHU MODULDA, chunki disk to'lishi SAQLASH SIYOSATINING bevosita
      natijasi (§D.11: bir bozor barqaror holatda ~16 GB) va u yerda
      chegara ham, o'lchov ham bitta joyda turishi kerak. `alerting.py`
      uni IMPORT qiladi, qayta yozmaydi.
    """
    usage = shutil.disk_usage(path)
    if usage.total <= 0:  # pragma: no cover - `statvfs` nol bermaydi
        return 0.0
    return round(usage.used / usage.total * 100, 2)
