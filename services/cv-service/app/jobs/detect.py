"""`detect` — bitta kadr, barcha zona hodisalari (§3.4, AI-02, RESEARCH §E.13).

Analog: `core-api/app/jobs/capture.py` (1142 q.) + `discovery.py:170-205`.

=============================================================================
⛔ 1. JOB JARAYONI HECH QACHON YIQILMAYDI — VA BU YERDA U KUCHLIROQ SHART.

`discovery.py:61-65` dagi sabab (navbat yiqilgan vazifani QAYTA yetkazishi
mumkin) shu yerda ham amal qiladi. Lekin bu jobda IKKINCHI, kuchliroq
sabab bor va u SXEMADAN keladi:

    `occupancy_events` da XATO USTUNI YO'Q.

Jadval — O'ZGARMAS hodisa jurnali (D-12): unda `status`, `error_code` yoki
`attempts` yo'q va bo'lishi ham mumkin emas. Ya'ni `discovery_runs` /
`capture_runs` dagi «nosozlik bazada ko'rinadi» yo'li bu yerda UMUMAN
mavjud emas. Aniqlashning yiqilishi FAQAT ikki joyda ko'rinadi:

    1. JURNAL (`log.exception`, Sentry);
    2. `system_heartbeats['cv_detect']` ning ESKIRISHI -> `/internal/
       self-check` (`EXPECTED_COMPONENTS`, 05-02).

Boshqa hech qanday signal YO'Q. Shuning uchun quyidagi har bir `except`
bandi jurnalga NIMA bo'lganini yozadi va hech biri jim o'tmaydi.

=============================================================================
⛔ 2. YAROQSIZ KADR — IKKI QATLAM, VA IKKINCHISI BIRINCHISIDAN OMON QOLADI.

    (a) KODDA: `quality_verdict <> 'ok'` bo'lsa bu job HECH NIMA qilmaydi
        va `log.info` bilan chiqadi. Bu KUTILGAN yo'l, xato EMAS.
        Bundan oldin `core-api` uni umuman navbatga qo'ymaydi
        (`cv_queue.enqueue_detect` chaqiruvining sharti) — ya'ni filtr
        aslida IKKI marta ishlaydi.
    (b) SXEMADA: `occupancy_events -> snapshots (id, is_billable)` kompozit
        FK + `CHECK (snapshot_is_billable)` (D-21). Yaroqsiz kadr uchun
        kerak bo'lgan `(id, true)` juftligi JADVALDA UMUMAN MAVJUD EMAS.

Kod qatlami «oldindan filtrlash mumkin bo'lgan xatoni imkonsiz xatoga
aylantirishdan yaxshiroq» degan qoidaning bajarilishi; sxema qatlami esa
kafolatning O'ZI. Birinchisi olib tashlansa ikkinchisi baribir rad etadi.

=============================================================================
⛔ 3. ZONASIZ KAMERA — XATO EMAS, `no_coverage` NING MANBAI (D-22).

Kameraning faol `camera_zones` qatori bo'lmasa hech nima yozilmaydi va
job MUVAFFAQIYATLI tugaydi. Buni «xato» deb belgilash 05-12 dagi
`no_coverage` materializatsiyasini ma'nosiz qilardi: qamrovsiz rasta
QONUNIY holat va u hisobotda ALOHIDA ko'rsatiladi, «bo'sh» ga
QO'SHILMAYDI.

=============================================================================
⚠ 4. `market_id` — XABAR OYNANI OCHADI, QIYMATLAR ESA QATORDAN OLINADI.

T-05-33 («soxta `snapshot_id` xabari») ning mexanizmi shu yerda aniq
yozilishi kerak, chunki u REJADA aytilganidan bir qadam nozikroq:

  * RLS ostida `snapshots` ni tenant KONTEKSTISIZ o'qib bo'lmaydi (0 qator),
    ya'ni `market_id` ni «faqat qatordan olish» mumkin emas — kontekstni
    ochish uchun u OLDIN kerak. Shuning uchun navbat xabari `market_id` ni
    ham olib yuradi.
  * Lekin xabardagi qiymat FAQAT OYNANI OCHADI. Yozuvga ketadigan hamma
    narsa — `market_id` ning O'ZI ham — `_SnapshotContext` ga QATORDAN
    o'qiladi. Boshqa bozorning `snapshot_id` si bilan yuborilgan xabar
    RLS tufayli 0 qator ko'radi va job hech nima yozmaydi.
  * Qolgan yuza: navbatga yoza oladigan tomon MAVJUD (market_id,
    snapshot_id) juftligi uchun aniqlashni QAYTA ishga tushira oladi. U
    idempotent (`ON CONFLICT DO NOTHING`), ya'ni yangi qator tug'ilmaydi.

=============================================================================
⚠ 5. MODELDAN KEYINGI CHOK — `sv.Detections` (D-02).

`detect_frame` ARGUMENT sifatida kiradi va uning tipi
`Callable[[bytes, tuple[int, int]], Detections]`. Bu D-02 ning ruxsat
etilgan yagona in'ektsiya nuqtasi va u shu yerda NOMMA-NOM yozilgan:

  * mahsulot yo'lida u `session_detector(DetectorSession(...))` — ONNX
    grafi haqiqatan yuritiladi;
  * integratsiya testida u sintetik `sv.Detections` qaytaradi, ya'ni
    ORKESTRATSIYA (tranzaksiya chegaralari, idempotentlik, sxema
    kafolatlari) modelsiz to'liq o'lchanadi.

⚠⚠ CHOKNING USTIDAGI SAVOL — «model to'g'ri javob berdimi?» — BU YERDA HAM
   O'LCHANMAYDI va hech qayerda yopilmaydi (D-01). `05-VALIDATION.md` ning
   ikki qatlamli bo'linishi: bu fayl MEXANIKANI quradi, ANIQLIKNI emas.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import cv2
import numpy as np
import structlog
from sbozor_core.enums import OccupancyVerdict
from sbozor_core.models.occupancy import CameraZone
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.models.snapshot import Snapshot
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from supervision import Detections, Position

from app.db import system_transaction
from app.detector.annotate import EVIDENCE_PREFIX, annotate_zone
from app.detector.postprocess import raw_to_detections
from app.detector.zones import (
    DEFAULT_REQUIRE_ALL_ANCHORS,
    DEFAULT_TRIGGERING_ANCHORS,
    UncertaintyThresholds,
    polygon_to_pixels,
    zone_verdict,
)
from app.repositories.occupancy_writer import OccupancyWriter, ZoneEvent
from app.services.storage import FrameAbsent, StorageError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, time
    from pathlib import Path
    from uuid import UUID

    import numpy.typing as npt
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.detector.session import DetectorSession
    from app.services.storage import CvStorageClient

__all__ = [
    "CONFIDENCE_THRESHOLD",
    "CV_DETECT_COMPONENT",
    "DETECT_FRAME_ABSENT",
    "DETECT_STORAGE_UNAVAILABLE",
    "JOB_INTERNAL_ERROR",
    "MODEL_VERSION",
    "REQUIRE_ALL_ANCHORS",
    "THRESHOLDS_VERSION",
    "TRIGGERING_ANCHORS",
    "UNCERTAIN_THRESHOLDS",
    "DetectFrame",
    "assert_model_version_matches",
    "detect",
    "evidence_key",
    "session_detector",
]

log = structlog.get_logger(__name__)

CV_DETECT_COMPONENT: Final = "cv_detect"
"""`system_heartbeats.component` — `EXPECTED_COMPONENTS` dagi nom bilan AYNAN BIR XIL.

Nom 05-02 da reyestrga qo'shilgan va bugungacha `never_seen` holatida
turibdi. Bu fayl uni birinchi marta YOZADIGAN qiladi.

⚠ SATR IKKI KOD BAZASIDA TAKRORLANADI (`core-api` ning `self_check.py` si
  va shu yer) va uni umumiy paketga chiqarish MUMKIN EMAS: reyestr
  «kim BO'LISHI KERAK?» degan savolga javob beradi va u yozuvchidan
  MUSTAQIL bo'lishi shart (aks holda komponentni o'chirish uni kutilganlar
  ro'yxatidan ham olib tashlardi va sukunat «hammasi joyida» bo'lardi).
"""

MODEL_VERSION: Final = "rfdetr-large-1.9.1"
"""`occupancy_events.model_version` — KALITNING BIR QISMI.

`UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)` — ya'ni
ikkinchi model (§E.15 dagi `timm` kesim klassifikatori) O'SHA kadr va
O'SHA zona uchun O'Z qatorini yozadi va eskisini o'chirmaydi. Shuning
uchun bu satr ARTEFAKT o'zgarganda o'zgarishi SHART.

⚠ ARTEFAKT BILAN BOG'LANISH MEXANIK: `assert_model_version_matches()`
  `CV_MODEL_PATH` faylining nomi shu satrning boshi ekanini ISHGA
  TUSHISHDA tekshiradi. Usiz `rfdetr-medium.onnx` ga o'tish jimgina
  eski nom bilan yozilardi va «qaysi model yaxshiroq?» savolini
  o'lchaydigan narsaning o'zi buzilardi.

⚠ QOLGAN BO'SHLIQ OCHIQ: kutubxona versiyasi (`1.9.1`) qismini hech nima
  mexanik tekshirmaydi — u eksport RETSEPTIGA tegishli va
  `ops/models/README.md` ning mas'uliyatida qoladi.
"""

THRESHOLDS_VERSION: Final = 1
"""`occupancy_events.thresholds_version` — D-11 ning qator darajasidagi langari.

`snapshots.quality_thresholds_version` naqshining aynan o'zi: verdikt
YOZISH PAYTIDA qo'yiladi va hech qachon qayta baholanmaydi. Chegarani
o'zgartirish O'TMISHDAGI hukmlarni RETROAKTIV o'zgartirardi.

⚠ SON O'ZGARSA, QUYIDAGI `UNCERTAIN_THRESHOLDS` HAM O'ZGARISHI SHART VA
  TESKARISI HAM. Ular JUFTLIK: qator «men qaysi chegaralar bilan hukm
  qilindim?» degan savolga aynan shu son orqali javob beradi.
"""

UNCERTAIN_THRESHOLDS: Final = UncertaintyThresholds(uncertain_low=0.30, uncertain_high=0.60)
"""`uncertain` oynasining ikki cheti — `[LOW confidence]`, VA BU YASHIRILMAYDI.

Qiymatlar REAL KARMANA KADRLARIDAN O'LCHANMAGAN (D-01: haqiqat hali yo'q).
Ular 4-fazadagi sifat chegaralari bilan bir xil maqomda: QOIDANING SHAKLI
ma'lumotsiz ham himoyalanadi, RAQAMLAR esa taqsimotdan chiqariladi.

Sozlash yo'li ATAYIN SQL: hodisalar `confidence` NING O'ZINI saqlaydi
(05-07 ning qarori), ya'ni `percentile_cont` bilan chegara tanlash uchun
qayta aniqlash KERAK EMAS. O'zgartirilganda `THRESHOLDS_VERSION` oshadi.
"""

CONFIDENCE_THRESHOLD: Final = 0.20
"""Xom chiqishdan `sv.Detections` ga o'tishdagi filtr — `uncertain` DAN PAST.

⚠ U `UNCERTAIN_THRESHOLDS.uncertain_low` DAN PAST BO'LISHI SHART va
  sabab arifmetik: bu filtr qutini BUTUNLAY tashlab yuboradi, ya'ni undan
  yuqori qo'yilsa `uncertain` oynasining pastki qismi HECH QACHON
  uchramasdi — nazoratchi navbati jimgina kambag'allashardi va buni hech
  kim sezmasdi. Shart `_assert_threshold_order()` da tekshiriladi.
"""

TRIGGERING_ANCHORS: Final[tuple[Position, ...]] = DEFAULT_TRIGGERING_ANCHORS
REQUIRE_ALL_ANCHORS: Final = DEFAULT_REQUIRE_ALL_ANCHORS
"""Ankor sozlamasi — `zones.py` NING STANDARTIDAN olinadi, qayta yozilmaydi.

05-07 o'lchagan: `supervision` ning O'Z standarti `require_all_anchors=True`
(AND) va u D-09 ning maqsadiga ZID ishlaydi. `zones.py` shu sababdan
ongli ravishda `False` (OR) ni standart qildi. Bu yerda qiymat
TAKRORLANMAYDI — u IMPORT qilinadi, aks holda ikki modul bir kun jimgina
ajralib ketardi.

⚠ `False` (OR) NING TO'G'RILIGI HAMON `[LOW confidence]`: OR ostida
  qo'shni rastaning saveti yolg'on-musbat berishi mumkin. Javobni faqat
  real Karmana kadri aytadi (`05-HUMAN-UAT`).
"""

DETECT_FRAME_ABSENT: Final = "detect_frame_absent"
"""Kadr omborda YO'Q — TANILGAN sabab (retention supurgan yoki obyekt yozilmagan)."""

DETECT_STORAGE_UNAVAILABLE: Final = "detect_storage_unavailable"
"""Ombor javob bermadi — infratuzilma nosozligi, kod nuqsoni EMAS."""

JOB_INTERNAL_ERROR: Final = "detect_internal_error"
"""Kutilmagan istisno — kod nuqsoni. To'liq iz `log.exception` bilan jurnalda."""

_MAX_DETAIL_CHARS: Final = 500
"""Jurnalga chiqadigan tafsilotning chegarasi (`discovery.py:160-167` naqshi)."""

DetectFrame = Callable[[bytes, tuple[int, int]], Detections]
"""D-02 NING CHOKI — VA U TIP SIFATIDA NOMLANGAN.

Alias `TYPE_CHECKING` ostida EMAS, ish paytida ham mavjud: chok
in'ektsiya nuqtasi, ya'ni uni chaqiruvchi (worker, test) o'z
funksiyasini shu tipga MOSLIGINI ko'rsatish uchun import qila olishi
kerak. `TYPE_CHECKING` ostidagi alias esa faqat annotatsiyada yashardi
va chokni «tasodifiy shaklga» aylantirardi.
"""


def _assert_threshold_order() -> None:
    """`CONFIDENCE_THRESHOLD` `uncertain_low` dan PAST ekanini IMPORT paytida tekshiradi.

    ⚠ MODUL DARAJASIDA VA BU ATAYIN: shart buzilganda nosozlik «noaniq
      navbat kutilganidan kamroq» degan STATISTIK alomat bilan chiqardi va
      uni oylar davomida hech kim modelga emas, «rastalar haqiqatan aniq
      ekan» degan xulosaga yozardi.
    """
    if UNCERTAIN_THRESHOLDS.uncertain_low <= CONFIDENCE_THRESHOLD:
        raise ValueError(
            f"CONFIDENCE_THRESHOLD={CONFIDENCE_THRESHOLD} >= "
            f"uncertain_low={UNCERTAIN_THRESHOLDS.uncertain_low}: "
            "quti filtri `uncertain` oynasining pastki qismini BUTUNLAY "
            "kesib tashlardi va nazoratchi navbati jimgina kambag'allashardi."
        )


_assert_threshold_order()


def assert_model_version_matches(model_path: Path) -> None:
    """`CV_MODEL_PATH` fayl nomi `MODEL_VERSION` ning boshi ekanini tekshiradi.

    Chaqiruv joyi — `worker.py::WORKER_STARTUP`, ya'ni nomuvofiqlik
    KONTEYNER KO'TARILISHIDA ochiladi (`Settings._validate_model_file`
    bilan bir xil qaror va bir xil sabab: birinchi kadrga qoldirilgan
    tekshiruv ertalab 06:00 da, hech kim qaramayotgan paytda chiqardi).

    Raises:
        ValueError: artefakt nomi bilan `MODEL_VERSION` mos kelmasa.
    """
    stem = model_path.stem
    if not MODEL_VERSION.startswith(stem):
        raise ValueError(
            f"CV_MODEL_PATH nomi (`{stem}`) `MODEL_VERSION` "
            f"(`{MODEL_VERSION}`) bilan mos emas. `model_version` — "
            "`occupancy_events` KALITINING bir qismi: artefakt o'zgarib "
            "nom o'zgarmasa, ikki xil model bir xil nom bilan yozilardi va "
            "«qaysi model yaxshiroq?» savolini o'lchash imkonsiz bo'lardi."
        )


def session_detector(session: DetectorSession) -> DetectFrame:
    """`DetectorSession` ni D-02 chokiga o'raydi — MAHSULOT yo'lidagi yagona shakl.

    ⚠ BU FUNKSIYA `detect()` NING ICHIDA EMAS va bu ataylab: `detect()`
      ONNX ni, tenzorlarni va `raw_to_detections` ni UMUMAN bilmaydi. U
      faqat `sv.Detections` bilan ishlaydi, ya'ni chok bitta, ko'rinadigan
      va nomlangan joyda turadi.
    """

    def _detect(frame_bytes: bytes, frame_size: tuple[int, int]) -> Detections:
        tensor = session.preprocess(frame_bytes)
        dets, labels = session.run(tensor)
        return raw_to_detections(
            dets,
            labels,
            # ⚠ ASL KADR O'LCHAMI, GRAF KIRISHINIKI EMAS: qutilar
            #   NORMALANGAN `cxcywh` bo'lib chiqadi, ya'ni ular istalgan
            #   shkalaga tushadi. Zona poligoni ham AYNAN shu shkalada
            #   piksellashtiriladi — ikki xil shkala qo'yilsa verdikt
            #   ISTISNOSIZ, jimgina noto'g'ri bo'lardi.
            frame_size=frame_size,
            confidence_threshold=CONFIDENCE_THRESHOLD,
        )

    return _detect


def evidence_key(*, market_id: UUID, business_date: date, snapshot_id: UUID) -> str:
    """Dalil rasmining S3 kaliti — ASL KADR YO'LIDAN BUTUNLAY AJRATILGAN.

    Prefiks `EVIDENCE_PREFIX` (05-07 ning KOD konstantasi), keyin
    `snapshots` ning kun bo'yicha bo'linishi bilan BIR XIL shakl:
    bitta kunning dalillari bitta prefiks ostida qoladi va retention
    (`core-api`) ularni ham kun bo'yicha topa oladi.
    """
    return f"{EVIDENCE_PREFIX}{market_id}/{business_date.isoformat()}/{snapshot_id}.jpg"


@dataclass(frozen=True, slots=True)
class _SnapshotContext:
    """Kadr qatoridan olingan hamma narsa — ORM OBYEKTI EMAS, oddiy qiymatlar.

    `discovery.py:334-358` (`_DeviceContext`) naqshi: tranzaksiya
    YOPILGANDAN keyin ORM obyektiga tegish `expire_on_commit` sozlamasiga
    bog'lanib qolardi (`make_sessionmaker` uni `False` qiladi, lekin bu
    IKKINCHI joydagi sozlama va u bir kun o'zgarishi mumkin).

    ⚠ `market_id` HAM SHU YERDA VA U QATORDAN O'QILGAN — modul
      docstringining 4-bandi.
    """

    market_id: UUID
    camera_id: UUID
    object_key: str
    business_date: date
    slot_time: time
    quality_verdict: str
    is_billable: bool


@dataclass(frozen=True, slots=True)
class _ZoneContext:
    """Faol zona qatori — bu ham ORM obyekti EMAS."""

    id: UUID
    stall_id: UUID
    version: int
    polygon: list[Any]


def _request_id(snapshot_id: UUID) -> str:
    """Deterministik `request_id` — bitta kadrning HAMMA yozuvi BIR IPDA.

    `discovery.py:265-269` ning mulohazasi: tasodifiy qiymat har
    tranzaksiyada boshqa bo'lardi va bitta kadr uchun yozilgan o'nlab
    hodisani bir-biriga bog'lash imkonsiz bo'lardi. `snapshot_id` esa
    aynan shu kadrni nomlaydi.
    """
    return f"job-detect-{snapshot_id}"


async def _read_snapshot(session: AsyncSession, snapshot_id: UUID) -> _SnapshotContext | None:
    """Kadr qatorini o'qiydi. `None` — qator KO'RINMAYDI (RLS yoki o'chirilgan)."""
    row = (
        await session.execute(
            select(
                Snapshot.market_id,
                Snapshot.camera_id,
                Snapshot.object_key,
                Snapshot.business_date,
                Snapshot.slot_time,
                Snapshot.quality_verdict,
                Snapshot.is_billable,
            ).where(Snapshot.id == snapshot_id)
        )
    ).one_or_none()
    if row is None:
        return None
    return _SnapshotContext(
        market_id=row.market_id,
        camera_id=row.camera_id,
        object_key=row.object_key,
        business_date=row.business_date,
        slot_time=row.slot_time,
        quality_verdict=row.quality_verdict,
        is_billable=row.is_billable,
    )


async def _read_active_zones(
    session: AsyncSession, *, market_id: UUID, camera_id: UUID
) -> list[_ZoneContext]:
    """Shu kameraning FAOL zonalari — `ix_camera_zones_active` ning issiq yo'li.

    ⚠ `is_active` FILTRI MAJBURIY: eskirgan versiyalar jadvalda QOLADI
      (D-07 — tahrir `UPDATE` emas, yangi qator) va ularni ham olish
      bitta rasta uchun ikki hodisa yozardi. `UNIQUE (market_id,
      snapshot_id, camera_zone_id, model_version)` ularni to'sib
      QOLMAYDI: `camera_zone_id` boshqa.
    """
    rows = (
        await session.execute(
            select(CameraZone.id, CameraZone.stall_id, CameraZone.version, CameraZone.polygon)
            .where(
                CameraZone.market_id == market_id,
                CameraZone.camera_id == camera_id,
                CameraZone.is_active.is_(True),
            )
            .order_by(CameraZone.stall_id, CameraZone.id)
        )
    ).all()
    return [
        _ZoneContext(id=row.id, stall_id=row.stall_id, version=row.version, polygon=row.polygon)
        for row in rows
    ]


def _decode(frame_bytes: bytes) -> npt.NDArray[np.uint8]:
    """JPEG baytlarini BGR massivga ochadi.

    ⚠ `cv2.imdecode` BUZUQ KIRISHDA ISTISNO TASHLAMAYDI — u `None`
      qaytaradi (05-07 da `preprocess()` uchun o'lchangan). `None` ni
      keyingi qadamga o'tkazish `AttributeError` bilan ANIQ BO'LMAGAN
      joyda yiqilardi.
    """
    decoded = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError("kadr baytlarini dekodlash mumkin emas (cv2.imdecode -> None)")
    frame: npt.NDArray[np.uint8] = decoded.astype(np.uint8, copy=False)
    return frame


def _zone_events(
    zones: Sequence[_ZoneContext],
    detections: Detections,
    *,
    frame_size: tuple[int, int],
    context: dict[str, Any],
) -> tuple[list[ZoneEvent], list[tuple[_ZoneContext, npt.NDArray[np.int64], ZoneEvent]]]:
    """Har zona uchun verdikt — BITTA ZONANING YIQILISHI QOLGANLARINI TO'XTATMAYDI.

    ⚠ HAR ZONA O'Z `try` I ICHIDA VA BU `capture_tick` NING «bitta
      bozorning nosozligi qolganlarini to'xtatmaydi» qarorining aynan
      o'zi, bir daraja pastda. Aks holda bitta buzuq poligon (masalan
      05-06 dan oldin yozilgan qator) o'sha kameraning BARCHA rastalarini
      hisobdan chiqarardi va hisobot ularni «bo'sh» emas, UMUMAN yo'q
      qilib ko'rsatardi.

    Returns:
        `(hamma hodisa, dalil rasmiga tushadigan zonalar)`.
    """
    width, height = frame_size
    events: list[ZoneEvent] = []
    flagged: list[tuple[_ZoneContext, npt.NDArray[np.int64], ZoneEvent]] = []

    for zone in zones:
        try:
            polygon_px = polygon_to_pixels(
                np.asarray(zone.polygon, dtype=np.float64), width, height
            )
            verdict, confidence = zone_verdict(
                detections,
                polygon_px,
                thresholds=UNCERTAIN_THRESHOLDS,
                anchors=TRIGGERING_ANCHORS,
                require_all_anchors=REQUIRE_ALL_ANCHORS,
            )
        except Exception:  # noqa: BLE001 - bitta zona butun kadrni yiqita olmaydi
            log.exception("detect_zone_failed", camera_zone_id=str(zone.id), **context)
            continue

        event = ZoneEvent(
            camera_zone_id=zone.id,
            zone_version=zone.version,
            verdict=str(verdict),
            confidence=confidence,
        )
        events.append(event)
        if verdict in (OccupancyVerdict.OCCUPIED, OccupancyVerdict.UNCERTAIN):
            flagged.append((zone, polygon_px, event))

    return events, flagged


def _draw_evidence(
    frame: npt.NDArray[np.uint8],
    flagged: Sequence[tuple[_ZoneContext, npt.NDArray[np.int64], ZoneEvent]],
) -> bytes:
    """Belgilangan zonalarni ASL KADRNING NUSXASIGA chizadi va JPEG qaytaradi.

    ⚠ `annotate_zone()` HAR CHAQIRUVDA NUSXA OLADI (05-07 ning o'lchangan
      qarori: `PolygonZoneAnnotator.annotate()` sahnani JOYIDA bo'yaydi).
      Ya'ni quyidagi zanjirda `frame` ning O'ZI hech qachon o'zgarmaydi va
      ko'r auditning dalil zanjiri uzilmaydi (T-05-32).
    """
    canvas = frame
    for zone, polygon_px, event in flagged:
        canvas = annotate_zone(
            canvas,
            polygon_px,
            # Yorliq nazoratchi UCHUN: rasta, verdikt va ishonch.
            label=f"{zone.stall_id.hex[:8]} {event.verdict} {event.confidence:.2f}",
        )
    ok, buffer = cv2.imencode(".jpg", canvas)
    if not ok:
        raise ValueError("dalil rasmini JPEG ga kodlash mumkin emas (cv2.imencode -> False)")
    return bytes(buffer.tobytes())


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession], detail: dict[str, int]
) -> None:
    """`system_heartbeats['cv_detect']` — ALOHIDA, QISQA tranzaksiya.

    ⚠ XATO YUTILADI (jurnalga yozib). Bu yozuv PROGRESS ko'rsatkichi,
      aniqlashning natijasi EMAS: uning yiqilishi bandlik dalilini
      bekor qila olmaydi. `capture.py:542-592` va
      `discovery.py::_publish_channels_found` bilan bir xil mulohaza.

    ⚠ TENANT KONTEKSTI YO'Q va bu ZIDDIYAT EMAS: `system_heartbeats` —
      GLOBAL jadval (`0014`), unda `market_id` ustuni yo'q va RLS
      qo'yilmagan.

    ⚠⚠ `detail` GA FAQAT SANOQLAR TUSHADI — `market_id`, `snapshot_id`
       yoki `camera_id` EMAS. Jadval global, ya'ni unga yozilgan har
       qanday tenant identifikatori RLS'siz jadvalda, hamma uchun
       ko'rinadigan joyda qolardi.

    ⚠⚠ `except Exception` — `SQLAlchemyError` EMAS (`capture.py:556-564`
       da O'LCHANGAN qaror): bu chaqiruv jobning ENG OXIRIDA yangi
       ulanish ochadi va baza xosti yechilmasa `socket.gaierror`
       `SQLAlchemyError` ga O'RALMAYDI.
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(
                component=CV_DETECT_COMPONENT, detail=detail
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    set_={
                        # ⚠ VAQT DB SOATIDAN: `/internal/self-check`
                        #   eskirganlikni AYNAN o'sha soatga qarab
                        #   hisoblaydi va ikkinchi soat ikki mashinada
                        #   chegarani siljitardi.
                        "last_seen_at": func.now(),
                        "detail": statement.excluded.detail,
                    },
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi ishni to'xtata olmaydi
        log.warning("detect_heartbeat_not_written", error=type(exc).__name__)


async def detect(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: CvStorageClient,
    detect_frame: DetectFrame,
    *,
    market_id: UUID,
    snapshot_id: UUID,
) -> None:
    """Bitta kadr -> barcha faol zonalar uchun bandlik hodisalari.

    Ketma-ketlik (tranzaksiya chegaralari bilan):

        1. kadr qatori + faol zonalar          (1-tranzaksiya, O'QISH)
        2. `quality_verdict <> 'ok'` -> CHIQISH (hodisa yozilmaydi)
        3. S3 dan baytlar                      (tranzaksiyadan TASHQARIDA)
        4. detektsiyalar + har zona verdicti    (sof hisob)
        5. `occupancy_events` ga bitta `INSERT` (2-tranzaksiya, YOZISH)
        6. dalil rasmi                          (tranzaksiyadan TASHQARIDA)
        7. yurak urishi                         (3-tranzaksiya, ALOHIDA)

    ⚠ 3-QADAM TRANZAKSIYADAN TASHQARIDA VA BU MUZOKARA QILINMAYDI:
      ombor javob bermay qolsa ochiq tranzaksiya `read_timeout` (15 s)
      davomida ulanishni ushlab turardi va 25 ta parallel kadr pulni
      butunlay yeb qo'yardi.

    ⛔ BU FUNKSIYA HECH QACHON ISTISNO KO'TARMAYDI (modul docstringi, 1-band).

    Args:
        sessionmaker: sessiya fabrikasi. ARGUMENT, modul globali EMAS.
        storage: ochiq ombor klienti (worker `WORKER_STARTUP` da ochadi).
        detect_frame: D-02 CHOKI — modul docstringining 5-bandi.
        market_id: tenant oynasini OCHADIGAN qiymat (4-band). Yozuvga
            ketadigan `market_id` `_SnapshotContext` dan olinadi.
        snapshot_id: aniqlanadigan kadr.
    """
    request_id = _request_id(snapshot_id)
    context: dict[str, Any] = {"market_id": str(market_id), "snapshot_id": str(snapshot_id)}

    try:
        await _run(
            sessionmaker,
            storage,
            detect_frame,
            market_id=market_id,
            snapshot_id=snapshot_id,
            request_id=request_id,
            context=context,
        )
    except FrameAbsent:
        # TANILGAN sabab: obyekt omborda yo'q. Retention uni allaqachon
        # supurgan bo'lishi mumkin (455 kunlik arxiv) — bu XATO EMAS.
        log.info("detect_skipped", error_code=DETECT_FRAME_ABSENT, **context)
    except StorageError as error:
        # ⚠ `str(error)` XAVFSIZ: `_failure()` faqat amal + istisno turi +
        #   status beradi va uning sirsizligi test bilan qulflangan.
        log.warning(
            "detect_failed",
            error_code=DETECT_STORAGE_UNAVAILABLE,
            detail=str(error)[:_MAX_DETAIL_CHARS],
            **context,
        )
    except Exception as exc:  # noqa: BLE001 - job jarayoni yiqilmasligi SHART
        log.exception(
            "detect_crashed",
            error_code=JOB_INTERNAL_ERROR,
            detail=type(exc).__name__,
            **context,
        )


async def _run(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: CvStorageClient,
    detect_frame: DetectFrame,
    *,
    market_id: UUID,
    snapshot_id: UUID,
    request_id: str,
    context: dict[str, Any],
) -> None:
    """`detect()` ning tanasi — istisnolarni CHAQIRUVCHI tutadi.

    ⚠ AJRATISH ATAYIN: xato ushlash zanjiri BITTA joyda turadi va u
      quyidagi har bir `return` yo'lida takrorlanmaydi
      (`discovery.py::_run_and_finish` bilan bir xil shakl).
    """
    async with system_transaction(
        sessionmaker, market_id=market_id, request_id=request_id
    ) as session:
        snapshot = await _read_snapshot(session, snapshot_id)
        if snapshot is None:
            # Qator KO'RINMAYDI: boshqa bozorning kadri (T-05-33) yoki
            # o'chirilgan bozor. Bu XATO EMAS — RLS ning to'g'ri javobi.
            log.info("detect_snapshot_not_visible", **context)
            return
        if snapshot.quality_verdict != "ok":
            # ⛔ KUTILGAN YO'L (modul docstringi, 2-band) — `log.info`.
            log.info("detect_skipped_unbillable", verdict=snapshot.quality_verdict, **context)
            return
        zones = await _read_active_zones(
            session, market_id=snapshot.market_id, camera_id=snapshot.camera_id
        )

    if not zones:
        # ⛔ XATO EMAS — `no_coverage` ning manbai (modul docstringi, 3-band).
        log.info("detect_no_active_zones", camera_id=str(snapshot.camera_id), **context)
        await _write_heartbeat(sessionmaker, {"zones": 0, "written": 0, "flagged": 0})
        return

    frame_bytes = await storage.get(snapshot.object_key)
    frame = _decode(frame_bytes)
    height, width = frame.shape[:2]
    detections = detect_frame(frame_bytes, (width, height))

    events, flagged = _zone_events(zones, detections, frame_size=(width, height), context=context)

    async with system_transaction(
        sessionmaker, market_id=snapshot.market_id, request_id=request_id
    ) as session:
        written = await OccupancyWriter(session, snapshot.market_id).record(
            events,
            snapshot_id=snapshot_id,
            business_date=snapshot.business_date,
            slot_time=snapshot.slot_time,
            model_version=MODEL_VERSION,
            thresholds_version=THRESHOLDS_VERSION,
        )

    if flagged:
        await storage.put_evidence(
            evidence_key(
                market_id=snapshot.market_id,
                business_date=snapshot.business_date,
                snapshot_id=snapshot_id,
            ),
            _draw_evidence(frame, flagged),
        )

    await _write_heartbeat(
        sessionmaker, {"zones": len(zones), "written": written, "flagged": len(flagged)}
    )
    log.info(
        "detect_done",
        zones=len(zones),
        events=len(events),
        written=written,
        flagged=len(flagged),
        **context,
    )
