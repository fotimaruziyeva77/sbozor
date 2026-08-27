"""`detect` orkestratsiyasi — HAQIQIY Postgres, SINTETIK detektsiyalar.

=============================================================================
⚠⚠ QAMROV CHEGARASI — OCHIQ VA U YOPILMAYDI (D-01/D-02).

Bu fayl chokning PASTIDAGI hamma narsani o'lchaydi: tranzaksiya
chegaralari, tenant konteksti, idempotentlik, D-21 langari, `business_date`
ning nusxalanishi, yurak urishi va «job hech qachon yiqilmaydi» qoidasi.

Chokning USTIDAGI savol — «RF-DETR band rastani band deb topdimi?» — bu
yerda O'LCHANMAYDI va hech qayerda yopilmaydi. `detect_frame` sintetik
`sv.Detections` qaytaradi, ya'ni «model to'g'ri javob berdi» degan da'vo bu
to'plamning YASHILLIGIDAN KELIB CHIQMAYDI.

Chok D-02 ning ruxsat etilgan yagona in'ektsiya nuqtasi va u
`app/jobs/detect.py` ning modul docstringida (5-band) nomma-nom yozilgan.

=============================================================================
⚠ BAZA HAQIQIY VA U SHART: RLS, kompozit FK (D-21) va o'zgarmaslik
  triggerlari FAQAT PostgreSQL da mavjud. Sxemasiz muhitda bu fayl
  QATTIQ yiqiladi (`tests/conftest.py::SETUP_HINT`), `skip` QILMAYDI.
=============================================================================
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import cv2
import numpy as np
import pytest
from conftest import SEED_FRAME_HEIGHT, SEED_FRAME_WIDTH, FrameSeed, read_events
from fixtures.detections import detections_at
from sqlalchemy import text

from app.db import system_transaction
from app.detector.annotate import EVIDENCE_PREFIX
from app.jobs import detect as detect_module
from app.jobs.detect import (
    CV_DETECT_COMPONENT,
    MODEL_VERSION,
    THRESHOLDS_VERSION,
    UNCERTAIN_THRESHOLDS,
    detect,
)
from app.services.storage import StorageError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from supervision import Detections

# ---------------------------------------------------------------------------
# Sintetik kirish — GEOMETRIK FAKT bo'yicha nomlangan (§S-9)
# ---------------------------------------------------------------------------

BOX_IN_LEFT_HALF: tuple[float, float, float, float] = (0.20, 0.40, 0.30, 0.60)
"""Kadrning CHAP yarmidagi quti — seed zonasi AYNAN chap yarim.

⚠ NOM VERDIKT AYTMAYDI. «Zonani band qiladigan quti» deb nomlash testni
  tekshirilayotgan qoidaning aks-sadosiga aylantirardi: bunday quti
  yasash uchun qoidaning SHARTINI bilish kerak bo'lardi va shart
  noto'g'ri bo'lsa ham test yashil qolardi (05-02 ning §S-9 majburiyati).
"""

CONFIDENCE_ABOVE_UNCERTAIN_HIGH = 0.87
"""`uncertain_high` (0.60) dan YUQORI — chegara ARIFMETIKASI test ichida ochiq."""


def _jpeg_bytes() -> bytes:
    """Haqiqiy JPEG — `cv2.imdecode` uni ocha olishi SHART.

    ⚠ `b"not a jpeg"` YARAMAYDI: `detect` kadrni HAQIQATAN dekodlaydi
      (o'lcham dalil rasmiga va piksellashtirishga kerak), ya'ni soxta
      baytlar `ValueError` bilan «job yiqilmadi» yo'liga tushib,
      testning maqsadini o'zgartirib yuborardi.
    """
    frame = np.zeros((SEED_FRAME_HEIGHT, SEED_FRAME_WIDTH, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", frame)
    assert ok
    return bytes(buffer.tobytes())


class _RecordingStorage:
    """Baytlarni beradigan va yozilganini QAYD QILADIGAN ombor.

    ⚠ `CvStorageClient` NING SOXTA AMALGA OSHIRILISHI EMAS: u S3 ga
      umuman bormaydi va `get` dan boshqa hech nimani modellashtirmaydi.
      Uning vazifasi — `detect` ga kadr baytlarini KIRITISH va dalil
      rasmi qaysi KALIT bilan yozilganini o'lchash. Haqiqiy S3 muloqoti
      `core-api` ning `-m sim` to'plamida allaqachon o'lchangan.
    """

    def __init__(self, payload: bytes | None = None) -> None:
        self.payload = payload if payload is not None else _jpeg_bytes()
        self.evidence: list[str] = []
        self.read_keys: list[str] = []

    async def get(self, key: str) -> bytes:
        self.read_keys.append(key)
        return self.payload

    async def put_evidence(self, key: str, data: bytes, **_kw: Any) -> str:
        assert key.startswith(EVIDENCE_PREFIX)
        assert data
        self.evidence.append(key)
        return '"etag"'


class _UnreachableStorage:
    """Har chaqiruvda `StorageError` — ombor uzilgan holat."""

    async def get(self, key: str) -> bytes:
        raise StorageError(f"ombor `GET` amali yiqildi: EndpointConnectionError ({key[:0]})")

    async def put_evidence(self, key: str, data: bytes, **_kw: Any) -> str:
        raise StorageError("ombor `PUT` amali yiqildi: EndpointConnectionError")


def _detections_in_left_half(confidence: float = CONFIDENCE_ABOVE_UNCERTAIN_HIGH) -> Any:
    def _detect_frame(_frame: bytes, frame_size: tuple[int, int]) -> Detections:
        return detections_at([BOX_IN_LEFT_HALF], confidences=[confidence], frame_size=frame_size)

    return _detect_frame


def _no_detections() -> Any:
    def _detect_frame(_frame: bytes, frame_size: tuple[int, int]) -> Detections:
        return detections_at([], frame_size=frame_size)

    return _detect_frame


def _exploding_detector() -> Any:
    def _detect_frame(_frame: bytes, _size: tuple[int, int]) -> Detections:
        raise RuntimeError("sun'iy nosozlik — detektor chokining ichida")

    return _detect_frame


async def _heartbeat_seen_at(sessionmaker: async_sessionmaker[AsyncSession]) -> Any:
    async with sessionmaker() as session, session.begin():
        return (
            await session.execute(
                text("SELECT last_seen_at FROM system_heartbeats WHERE component = :component"),
                {"component": CV_DETECT_COMPONENT},
            )
        ).scalar_one_or_none()


async def _heartbeat_detail(sessionmaker: async_sessionmaker[AsyncSession]) -> Any:
    """Yurak urishining `detail` i — «job O'Z YO'LINI OXIRIGACHA bosib o'tdimi?».

    ⚠⚠ BU YORDAMCHI SABOTAJ BILAN TUG'ILDI (2026-08-09). `ON CONFLICT DO
       NOTHING` -> `DO UPDATE SET verdict='empty'` ga almashtirilganda
       `test_rerun_creates_no_duplicate` YASHIL QOLGAN edi, chunki:

         `DO UPDATE` -> `BEFORE UPDATE` o'zgarmaslik triggeri `RAISE`
         -> `detect()` ning `except Exception` i uni YUTADI
         -> qatorlar O'ZGARMAGAN -> «dublikat yo'q» da'vosi bajarildi.

       Ya'ni o'sha test IDEMPOTENTLIKNI emas, SXEMANING himoyasini
       o'lchayotgan edi va ikkalasini ajrata olmasdi. Yurak urishi
       jobning OXIRIDA yoziladi, ya'ni uning `detail` i «yo'l oxirigacha
       bosib o'tildi» degan yagona ichki signal.
    """
    async with sessionmaker() as session, session.begin():
        return (
            await session.execute(
                text("SELECT detail FROM system_heartbeats WHERE component = :component"),
                {"component": CV_DETECT_COMPONENT},
            )
        ).scalar_one_or_none()


# ===========================================================================
# 1. YAROQSIZ KADR — HODISA UMUMAN TUG'ILMAYDI
# ===========================================================================


async def test_dark_snapshot_produces_no_events(
    db_sessionmaker: async_sessionmaker[AsyncSession], dark_frame_seed: FrameSeed
) -> None:
    """`quality_verdict='dark'` -> 0 qator VA ISTISNO YO'Q (kutilgan yo'l)."""
    storage = _RecordingStorage()

    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=dark_frame_seed.market_id,
        snapshot_id=dark_frame_seed.snapshot_id,
    )

    assert await read_events(db_sessionmaker, dark_frame_seed.market_id) == []
    # ⚠ OMBORGA UMUMAN BORILMAGAN: filtr S3 chaqiruvidan OLDIN turadi,
    #   ya'ni yaroqsiz kadr uchun 500 KB o'qish ham bo'lmaydi.
    assert storage.read_keys == []


async def test_the_schema_rejects_an_event_for_an_unbillable_frame(
    db_sessionmaker: async_sessionmaker[AsyncSession], dark_frame_seed: FrameSeed
) -> None:
    """⛔ IKKINCHI QATLAM (D-21): kod filtri CHETLAB O'TILSA HAM DB rad etadi.

    Bu test yuqoridagining TAKRORI EMAS. Birinchisi KOD qatlamini
    (`quality_verdict != 'ok'` -> chiqish) o'lchaydi; bu esa o'sha
    filtrni butunlay chetlab o'tib, `INSERT` ni to'g'ridan-to'g'ri
    uradi. Ikkinchi qatlamsiz birinchisining olib tashlanishi JIMGINA
    o'tardi.
    """
    async with system_transaction(
        db_sessionmaker,
        market_id=dark_frame_seed.market_id,
        request_id=f"cv-test-fence-{dark_frame_seed.market_id}",
    ) as session:
        with pytest.raises(Exception) as excinfo:
            await session.execute(
                text(
                    "INSERT INTO occupancy_events (market_id, snapshot_id, camera_zone_id, "
                    " business_date, slot_time, verdict, confidence, model_version, "
                    " thresholds_version, zone_version) "
                    "VALUES (:market_id, :snapshot_id, :zone_id, CURRENT_DATE, '06:00', "
                    " 'occupied', 0.9, 'x', 1, 1)"
                ),
                {
                    "market_id": dark_frame_seed.market_id,
                    "snapshot_id": dark_frame_seed.snapshot_id,
                    "zone_id": dark_frame_seed.zone_ids[0],
                },
            )

    assert "fk_occupancy_events_snapshot_billable" in str(excinfo.value)


# ===========================================================================
# 2. TO'LIQ YO'L — QIYMATLAR VA ULARNING MANBASI
# ===========================================================================


async def test_events_carry_confidence_and_versions(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Har qatorda `confidence`, uchala versiya va langar TO'LDIRILGAN."""
    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    rows = await read_events(db_sessionmaker, frame_seed.market_id)
    assert len(rows) == len(frame_seed.zone_ids)
    for row in rows:
        assert row["model_version"] == MODEL_VERSION
        assert row["thresholds_version"] == THRESHOLDS_VERSION
        assert row["zone_version"] == 1
        assert row["snapshot_is_billable"] is True
        assert Decimal("0") <= row["confidence"] <= Decimal("1")
    assert {row["verdict"] for row in rows} == {"occupied"}
    assert {row["confidence"] for row in rows} == {
        Decimal(repr(CONFIDENCE_ABOVE_UNCERTAIN_HIGH)).quantize(Decimal("0.0001"))
    }


async def test_an_empty_zone_still_records_its_measurement(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """`empty` verdikti ham QATOR yozadi — «hodisa yo'q» va «bo'sh» BOSHQA narsa.

    Yozilmasa 05-12 «bu zona bugun ko'rilmadi» (`no_coverage`) bilan
    «ko'rildi va bo'sh edi» ni ajrata olmasdi — D-22 ning butun mazmuni
    aynan shu farqda.
    """
    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _no_detections(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    rows = await read_events(db_sessionmaker, frame_seed.market_id)
    assert len(rows) == len(frame_seed.zone_ids)
    assert {row["verdict"] for row in rows} == {"empty"}
    # `0.0` AYNAN BITTA narsani anglatadi: zonada o'lchanadigan hech nima
    # BO'LMAGAN (05-07 ning `zone_verdict` docstringi).
    assert {row["confidence"] for row in rows} == {Decimal("0.0000")}


async def test_business_date_matches_snapshot_row(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """`business_date` va `slot_time` `snapshots` DAN nusxalanadi — LITERAL solishtiruv.

    Mustaqil hisoblash yarim tunda bir kun farq qilardi (Pitfall 3): kadr
    `snapshots` da 09-01 ga, dalil esa 09-02 ga tushardi.
    """
    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    async with system_transaction(
        db_sessionmaker,
        market_id=frame_seed.market_id,
        request_id=f"cv-test-dates-{frame_seed.market_id}",
    ) as session:
        snapshot = (
            await session.execute(
                text("SELECT business_date, slot_time FROM snapshots WHERE id = :id"),
                {"id": frame_seed.snapshot_id},
            )
        ).one()

    rows = await read_events(db_sessionmaker, frame_seed.market_id)
    assert rows
    for row in rows:
        assert row["business_date"] == snapshot.business_date
        assert row["slot_time"] == snapshot.slot_time


async def test_business_date_comes_from_the_row_and_not_from_today(
    db_sessionmaker: async_sessionmaker[AsyncSession], past_frame_seed: FrameSeed
) -> None:
    """⚠⚠ YUQORIDAGI TEST YOLG'IZ O'ZI YETARLI EMAS — VA BU O'LCHANGAN.

    Sabotaj (2026-08-09): `detect` da `snapshot.business_date` ->
    `date.today()`. Natija — 17 testning HAMMASI YASHIL QOLDI. Sabab
    oddiy: seed kadri BUGUNGI, `business_date` esa `scheduled_at` dan
    hosila, ya'ni ikkala kod ham bir xil sanani berardi.

    Pitfall 3 aynan shu haqda: xato YARIM TUNDA — kadr 23:59 da
    olinganda va `detect` 00:01 da ishlaganda — tug'iladi, ya'ni uni
    bugungi kadr bilan qo'riqlab bo'lmaydi. Bu test kadrni UCH KUN
    orqaga suradi va farqni HAR QANDAY soatda ko'rinadigan qiladi.
    """
    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=past_frame_seed.market_id,
        snapshot_id=past_frame_seed.snapshot_id,
    )

    async with system_transaction(
        db_sessionmaker,
        market_id=past_frame_seed.market_id,
        request_id=f"cv-test-past-{past_frame_seed.market_id}",
    ) as session:
        snapshot_date = (
            await session.execute(
                text("SELECT business_date FROM snapshots WHERE id = :id"),
                {"id": past_frame_seed.snapshot_id},
            )
        ).scalar_one()
        today = (await session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

    assert snapshot_date != today, (
        "seed kadri BUGUNGI bo'lib qoldi — bu test o'z farqini yo'qotdi "
        "va u endi hech nimani qo'riqlamaydi."
    )
    rows = await read_events(db_sessionmaker, past_frame_seed.market_id)
    assert rows
    assert {row["business_date"] for row in rows} == {snapshot_date}


# ===========================================================================
# 3. IDEMPOTENTLIK
# ===========================================================================


async def test_rerun_creates_no_duplicate(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Bir xil `snapshot_id` ikki marta — qator soni O'ZGARMAYDI.

    ⚠ IKKINCHI YUGURISH BOSHQA VERDIKT BERADI (`empty`), lekin qator
      YANGILANMAYDI ham: `ON CONFLICT DO NOTHING` — `DO UPDATE` EMAS.
      Bu D-12 ning («AI natijasi hech qachon o'zgartirilmaydi») kod
      tomondagi yarmi; DB tomondagi yarmi — o'zgarmaslik triggeri.
    """
    storage = _RecordingStorage()
    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )
    first = await read_events(db_sessionmaker, frame_seed.market_id)

    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _no_detections(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )
    second = await read_events(db_sessionmaker, frame_seed.market_id)

    assert len(second) == len(first)
    assert second == first

    # ⚠⚠ QUYIDAGI IKKI DA'VOSIZ BU TEST HECH NIMANI QO'RIQLAMAYDI — VA BU
    #    O'LCHANGAN (`_heartbeat_detail` docstringi). Yuqoridagi
    #    solishtiruv `DO UPDATE` ostida ham yashil qoladi, chunki
    #    o'zgarmaslik triggeri UPDATE ni rad etadi va `detect()` istisnoni
    #    yutadi. Yurak urishining `detail` i esa AYNAN farqni ko'rsatadi:
    #    yiqilgan yugurish unga umuman yetib bormaydi.
    detail = await _heartbeat_detail(db_sessionmaker)
    assert detail is not None
    assert detail["zones"] == len(frame_seed.zone_ids)
    assert detail["written"] == 0, (
        "ikkinchi yugurish `written=0` bilan tugashi kerak edi. Boshqa "
        "qiymat (yoki eskirgan `detail`) ikkinchi yugurish O'Z YO'LINI "
        "OXIRIGACHA bosib o'tmaganini bildiradi."
    )


# ===========================================================================
# 4. TENANT KONTEKSTI — JOB UNI O'ZI O'RNATADI
# ===========================================================================


async def test_the_job_sets_its_own_tenant_context(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """⚠⚠ MEXANIZMNI XULQ BILAN O'LCHAYDI, KOD O'QIB EMAS.

    Kontekstsiz `SELECT` RLS ostida 0 qator beradi va ISTISNO BERMAYDI
    (Pitfall 13). Ya'ni `system_transaction()` olib tashlansa `detect`
    kadrni «topa olmasdi» va JIMGINA hech nima yozmasdi — hisobotda bu
    «bozor bo'sh edi» dan farq qilmasdi.

    Test shuni ko'rsatadi: AYNAN O'SHA `snapshot_id` kontekstsiz o'qilganda
    KO'RINMAYDI, `detect` esa uni topadi va yozadi.
    """
    async with db_sessionmaker() as session, session.begin():
        without_context = (
            await session.execute(
                text("SELECT count(*) FROM snapshots WHERE id = :id"),
                {"id": frame_seed.snapshot_id},
            )
        ).scalar_one()
    assert without_context == 0, (
        "kontekstsiz o'qish qatorni KO'RDI — RLS o'chgan yoki ulanish "
        "roli `BYPASSRLS`. Bu holatda quyidagi da'vo hech nimani o'lchamaydi."
    )

    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert len(await read_events(db_sessionmaker, frame_seed.market_id)) == len(frame_seed.zone_ids)


async def test_a_message_naming_another_market_writes_nothing(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """T-05-33: soxta `market_id` bilan yuborilgan xabar HECH NIMA yozmaydi.

    Xabardagi `market_id` faqat OYNANI ochadi; kadr o'sha oynada
    ko'rinmasa job to'xtaydi. Ya'ni boshqa bozorning kadriga bandlik
    dalili yopishtirib bo'lmaydi.
    """
    storage = _RecordingStorage()

    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=uuid4(),
        snapshot_id=frame_seed.snapshot_id,
    )

    assert storage.read_keys == []
    assert await read_events(db_sessionmaker, frame_seed.market_id) == []


# ===========================================================================
# 5. QAMROVSIZ KAMERA — XATO EMAS
# ===========================================================================


async def test_zoneless_camera_writes_nothing(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Faol zona bo'lmasa hech nima yozilmaydi va bu XATO EMAS (D-22).

    ⚠ ZONALAR `is_active = false` QILINADI, O'CHIRILMAYDI: tahrir yangi
      qator (D-07) va eskisi joyida qoladi. Test aynan shu holatni
      yasaydi — «kontur bor edi, endi faol emas».
    """
    async with system_transaction(
        db_sessionmaker,
        market_id=frame_seed.market_id,
        request_id=f"cv-test-deactivate-{frame_seed.market_id}",
    ) as session:
        await session.execute(
            text("UPDATE camera_zones SET is_active = false WHERE market_id = :market_id"),
            {"market_id": frame_seed.market_id},
        )

    storage = _RecordingStorage()
    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert await read_events(db_sessionmaker, frame_seed.market_id) == []
    # Kadr ham O'QILMAYDI: zonasiz kadrni yuklash bekorga 500 KB bo'lardi.
    assert storage.read_keys == []


# ===========================================================================
# 6. JOB HECH QACHON YIQILMAYDI
# ===========================================================================


async def test_unexpected_exception_does_not_crash_the_job(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Detektor chokining ichidagi sun'iy istisno — job MUVAFFAQIYATLI tugaydi.

    ⚠ XULQIY TEST: `pytest.raises` YO'Q. `detect()` ning kontrakti aynan
      shu — u ISTISNO KO'TARMAYDI (modul docstringi, 1-band), chunki
      navbat yiqilgan vazifani QAYTA yetkazishi mumkin.
    """
    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _exploding_detector(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert await read_events(db_sessionmaker, frame_seed.market_id) == []


async def test_storage_failure_does_not_crash_the_job(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Ombor uzilgan — job jim yiqilmaydi, ISTISNO ham ko'tarmaydi."""
    await detect(
        db_sessionmaker,
        _UnreachableStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert await read_events(db_sessionmaker, frame_seed.market_id) == []


async def test_a_broken_polygon_does_not_lose_the_other_zones(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Bitta zona yiqilsa QOLGANLARI yoziladi — `capture_tick` qarorining takrori.

    Buzuq poligon (ikki tepalik) `polygon_to_pixels()` da `ValueError`
    beradi. Zonalar bo'yicha `try` bo'lmasa o'sha kameraning BARCHA
    rastalari hisobdan chiqardi va hisobot ularni «bo'sh» emas, UMUMAN
    yo'q qilib ko'rsatardi.
    """
    async with system_transaction(
        db_sessionmaker,
        market_id=frame_seed.market_id,
        request_id=f"cv-test-broken-{frame_seed.market_id}",
    ) as session:
        # ⚠ `polygon_min_vertices` `CHECK` i uch tepalikdan kamini rad
        #   etadi, ya'ni buzuqlikni SHAKL bilan emas, DIAPAZON bilan
        #   yasaymiz: 0..1 dan tashqaridagi koordinata `polygon_to_pixels`
        #   da `ValueError` beradi va DB uni taqiqlamaydi.
        await session.execute(
            text("UPDATE camera_zones SET polygon = CAST(:polygon AS jsonb)  WHERE id = :id"),
            {
                "id": frame_seed.zone_ids[0],
                "polygon": "[[0.0, 0.0], [1.5, 0.0], [1.5, 1.0], [0.0, 1.0]]",
            },
        )

    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    rows = await read_events(db_sessionmaker, frame_seed.market_id)
    assert [row["camera_zone_id"] for row in rows] == [frame_seed.zone_ids[1]]


# ===========================================================================
# 7. YURAK URISHI
# ===========================================================================


async def test_heartbeat_is_written(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """`cv_detect` yurak urishi YOZILADI — `/internal/self-check` uni ko'radi.

    05-02 komponentni `EXPECTED_COMPONENTS` ga qo'shgan va u bugungacha
    `never_seen` holatida turgan edi.
    """
    before = await _heartbeat_seen_at(db_sessionmaker)

    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    after = await _heartbeat_seen_at(db_sessionmaker)
    assert after is not None
    if before is not None:
        assert after >= before


async def test_heartbeat_failure_does_not_stop_the_job(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    frame_seed: FrameSeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yurak urishi ataylab yiqitildi — HODISALAR BARIBIR YOZILADI.

    Yurak urishi PROGRESS ko'rsatkichi, aniqlashning natijasi EMAS.
    Uning yiqilishi bandlik dalilini bekor qila olmasligi kerak
    (`capture.py:542-592` bilan bir xil qaror).
    """

    async def _explode(*_args: Any, **_kw: Any) -> None:
        raise RuntimeError("sun'iy nosozlik — yurak urishi yozuvi")

    monkeypatch.setattr(detect_module, "_write_heartbeat", _explode)

    await detect(
        db_sessionmaker,
        _RecordingStorage(),  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert len(await read_events(db_sessionmaker, frame_seed.market_id)) == len(frame_seed.zone_ids)


# ===========================================================================
# 8. DALIL RASMI — ALOHIDA PREFIKS (T-05-32)
# ===========================================================================


async def test_evidence_is_written_under_its_own_prefix_only(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Dalil rasmi ASL KADR KALITIGA HECH QACHON yozilmaydi."""
    storage = _RecordingStorage()

    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _detections_in_left_half(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert storage.evidence, "belgilangan zona bor edi, lekin dalil rasmi yozilmadi"
    for key in storage.evidence:
        assert key.startswith(EVIDENCE_PREFIX)
        assert key != frame_seed.object_key
    assert storage.read_keys == [frame_seed.object_key]


async def test_no_evidence_when_every_zone_is_empty(
    db_sessionmaker: async_sessionmaker[AsyncSession], frame_seed: FrameSeed
) -> None:
    """Hamma zona `empty` bo'lsa dalil rasmi UMUMAN yozilmaydi.

    175 kadr/kun/bozor da bo'sh rastalarning rasmini saqlash arxivni
    bekorga ikki barobarlashtirardi; nazoratchi esa faqat `occupied` va
    `uncertain` ni ko'radi.
    """
    storage = _RecordingStorage()

    await detect(
        db_sessionmaker,
        storage,  # type: ignore[arg-type]
        _no_detections(),
        market_id=frame_seed.market_id,
        snapshot_id=frame_seed.snapshot_id,
    )

    assert storage.evidence == []


# ===========================================================================
# 9. CHEGARALARNING ARIFMETIKASI — TESTNING O'Z QUYI CHEGARASI
# ===========================================================================


def test_the_synthetic_confidence_is_above_the_occupied_threshold() -> None:
    """⚠ TESTNING O'Z KIRISHI TEKSHIRILADI.

    Yuqoridagi testlar `occupied` kutadi. Agar `UNCERTAIN_THRESHOLDS`
    bir kun `0.87` dan yuqoriga ko'tarilsa, ular `uncertain` olib
    yiqilardi — va sabab «kod buzildi» emas, «test kirishi eskirdi»
    bo'lardi. Bu test farqni DARHOL nomlaydi.
    """
    assert UNCERTAIN_THRESHOLDS.uncertain_high <= CONFIDENCE_ABOVE_UNCERTAIN_HIGH
