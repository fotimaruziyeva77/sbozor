"""CamAgent kadrlarini sbozor hisobiga qabul qiladi.

=============================================================================
NEGA BU MARSHRUT BOR
=============================================================================

sbozor kadrlarni O'ZI oladi: `capture_tick` rejani materializatsiya
qiladi, worker NVR'ga ulanib rasm oladi va sifatini tahlil qiladi. Bu
yo'l bozor tarmog'iga TUNNEL talab qiladi.

CamAgent obyektlarida tunnel YO'Q вЂ” u yerda kadrni AGENT oladi va
tashqariga o'zi yuboradi. Kadr sbozor S3'iga tushadi, lekin `snapshots`
jadvaliga TUSHMAYDI: ya'ni `/uz/snapshots` bo'sh qoladi, zona chizib
bo'lmaydi va bandlik tahlili boshlanmaydi.

Bu marshrut o'sha bo'shliqni yopadi: gateway kadr S3'ga yozilgach shu
yerga xabar beradi, core-api esa uni O'Z sifat tahlilidan o'tkazib
`capture_runs` + `snapshots` yozadi.

=============================================================================
в›”в›” SIFAT TAHLILI SHU YERDA, GATEWAY'DA EMAS
=============================================================================

`quality_verdict` dan `snapshots.is_billable` GENERATED ustun sifatida
hisoblanadi вЂ” ya'ni verdikt PUL qaroriga bevosita ta'sir qiladi.
Chegaralar (`QualityThresholds`) va ularning versiyasi sbozor tomonida
yashaydi va vaqt o'tishi bilan o'zgaradi.

Agar gateway o'z verdiktini yuborsa, ikkita chegara to'plami paydo
bo'lardi va ular jimgina ajralib ketardi: bir xil kadr ikki tizimda
har xil baholanardi. Shuning uchun gateway FAKT yuboradi (kadr qayerda,
qachon, qaysi kameradan), BAHO esa shu yerda beriladi.

=============================================================================
вљ  IDEMPOTENT вЂ” AGENT QAYTA YUBORISHI MUMKIN
=============================================================================

Agent tarmoq uzilganda navbatdan qayta yuboradi (CLAUDE.md 6-bo'lim:
idempotency kaliti deterministik). Shuning uchun `capture_runs` ham,
`snapshots` ham `ON CONFLICT` bilan yoziladi: takroriy xabar ikkinchi
qator YARATMAYDI va `is_billable` ikki marta sanalmaydi.
"""

from __future__ import annotations

import hmac
from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sbozor_core.tenancy import ActorKind, set_tenant_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services import storage as storage_mod
from app.services.cv_queue import enqueue_detect
from app.services.quality import QUALITY_THRESHOLDS_VERSION, VERDICT_OK, analyze
from app.services.review_seed import seed_snapshot
from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal/camagent", include_in_schema=False)

_UNAUTHORIZED = "unauthorized"
_UNAVAILABLE = "unavailable"


# ===========================================================================
# AUTENTIFIKATSIYA вЂ” `bot.py` bilan BIR XIL naqsh
# ===========================================================================


def _presented_token(request: Request) -> str:
    """вљ  Sarlavha yo'q bo'lsa BO'SH SATR: ikkala yo'l ham
    `compare_digest` ga boradi va vaqt bo'yicha farq qilmaydi."""
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


async def _require_service_token(request: Request) -> None:
    settings: Settings = request.app.state.settings
    expected = getattr(settings, "camagent_service_token", None)
    expected = expected.get_secret_value() if expected else ""
    if not expected:
        log.warning("camagent_internal_token_not_configured", path=request.url.path)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_UNAVAILABLE)
    if not hmac.compare_digest(_presented_token(request).encode(), expected.encode()):
        log.warning("camagent_internal_token_rejected", path=request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)


ServiceToken = Annotated[None, Depends(_require_service_token)]


# ===========================================================================
# SO'ROV
# ===========================================================================


class SnapshotIn(BaseModel):
    """Gateway yuboradigan FAKTLAR вЂ” baho emas."""

    market_id: UUID
    camera_serial: str = Field(min_length=1, max_length=128)
    channel_no: int = Field(ge=1, le=64)
    object_key: str = Field(min_length=1, max_length=512)
    size_bytes: int = Field(gt=0)
    captured_at: datetime
    slot_time: str = Field(default="", pattern=r"^(\d{2}:\d{2}(:\d{2})?)?$")
    """Jadval sloti — AGENT jadvalidan, MAHALLIY vaqtda.

    ⛔ BO'SH BO'LISHI MUMKIN va o'shanda u `scheduled_at` dan BOZOR
       MINTAQASIDA hisoblanadi (260829). Gateway UTC'da ishlaydi va
       jadval sloti bo'lmagan kadrga (qo'lda `snapshot_now`) UTC soatini
       qo'yardi: Karmanada `06:18` da olingan kadr jadvalda `01:18`
       ustuni bo'lib chiqdi va operator uni tanimadi.
    """
    scheduled_at: datetime
    late: bool = False


class SnapshotOut(BaseModel):
    snapshot_id: UUID | None = None
    quality_verdict: str
    duplicate: bool = False


@router.post("/snapshot", response_model=SnapshotOut)
async def accept_snapshot(
    payload: SnapshotIn,
    _: ServiceToken,
    request: Request,
) -> SnapshotOut:
    """Agent olgan kadrni sbozor hisobiga qo'shadi.

    в›” KADR BAYTLARI S3'DAN O'QILADI, so'rov tanasida kelmaydi: 400 KB
       JPEG'ni JSON ichida yuborish base64 tufayli 33% o'sardi va
       `client_max_body_size` ni ikkala tomonda ham qayta sozlashni
       talab qilardi. Gateway kadrni ALLAQACHON S3'ga yozgan вЂ” bu yerda
       faqat kalit keladi.
    """
    settings: Settings = request.app.state.settings
    market_id = str(payload.market_id)

    # в›” TENANT KONTEKSTI QO'LDA O'RNATILADI (`jobs/capture.py` naqshi).
    #   Bu marshrutda `Principal` YO'Q вЂ” so'rovchi ODAM emas, SERVIS.
    #   RLS esa `app.market_id` GUC'siz 0 qator beradi, ya'ni kontekstsiz
    #   kamera topilmasdi va kadr jimgina yo'qolardi.
    sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        request.app.state.engine, expire_on_commit=False
    )
    async with sessionmaker() as session, session.begin():
        await set_tenant_context(
            session,
            market_id=payload.market_id,
            actor_id=None,
            actor_kind=ActorKind.SYSTEM,
            request_id=f"camagent:{payload.object_key[:64]}",
        )
        natija = await _accept(session, request, settings, payload, market_id)

    # =====================================================================
    # ⛔ CV NAVBATIGA — TRANZAKSIYA YOPILGANDAN KEYIN (`jobs/capture.py`
    #    naqshi, `04-PATTERNS.md` §3.3 4-qadam). Ikki sabab:
    #
    #    (a) ichkarida bo'lsa CV navbatining nosozligi (Valkey uzilgan)
    #        `COMMIT` ni yiqitardi va KADR OLISH ham yiqilardi — holbuki
    #        obyekt allaqachon S3 da va dalil YO'QOLMAGAN;
    #    (b) xabar `COMMIT` dan OLDIN chiqsa `cv-service` hali MAVJUD
    #        BO'LMAGAN `snapshots` qatorini izlardi va «ko'rinmadi» deb
    #        chiqib ketardi.
    #
    # ⚠ FAQAT YANGI va `ok` kadr uchun. Takroriy xabar (agent tarmoq
    #   uzilganda qayta yuboradi) navbatni bekorga to'ldirardi; yaroqsiz
    #   kadrda esa `occupancy_events` ning kompozit FK'si `(id, true)`
    #   juftligini TALAB qiladi va u jadvalda umuman yo'q (D-21) — ya'ni
    #   oldindan filtrlanadigan xato IMKONSIZ xatoga aylanardi.
    #
    # ⚠ Xatosi YUTILADI (`cv_queue.py` docstringi), shuning uchun bu
    #   yerda `try` YO'Q va bu ATAYIN: ikkinchi qatlam «qaysi biri
    #   yutdi?» savolini tug'dirardi.
    # =====================================================================
    if (
        natija.snapshot_id is not None
        and not natija.duplicate
        and natija.quality_verdict == VERDICT_OK
    ):
        await enqueue_detect(market_id=payload.market_id, snapshot_id=natija.snapshot_id)

    return natija


async def _accept(session, request, settings, payload, market_id) -> SnapshotOut:
    # 1. Kamera вЂ” seriya + kanal bo'yicha. Sinxronizatsiya (`sbozor_sync`)
    #    uni allaqachon yaratgan bo'lishi kerak; topilmasa kadr YO'QOLMAYDI,
    #    lekin hisobga ham kirmaydi va sabab jurnalga tushadi.
    qator = (
        await session.execute(
            text("""
        SELECT c.id, c.nvr_id
          FROM cameras c
          JOIN nvr_devices d ON d.id = c.nvr_id AND d.market_id = c.market_id
         WHERE c.market_id = :market_id
           AND d.serial_number = :serial
           AND c.channel_no = :channel
         LIMIT 1
    """),
            {
                "market_id": market_id,
                "serial": payload.camera_serial,
                "channel": payload.channel_no,
            },
        )
    ).first()
    if qator is None:
        log.warning(
            "camagent_snapshot_camera_not_found",
            market_id=market_id,
            serial=payload.camera_serial,
            channel=payload.channel_no,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="camera_not_found")
    camera_id, nvr_id = qator[0], qator[1]

    # 2. Kadr baytlari вЂ” sifat tahlili uchun.
    try:
        baytlar = await _read_object(settings, payload.object_key)
    except Exception as exc:  # noqa: BLE001
        log.warning("camagent_snapshot_read_failed", key=payload.object_key, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="object_unreadable"
        ) from exc

    # в›” CHEGARALAR SOZLAMADAN, standart qiymatlardan EMAS: operator
    #   ularni `.env` orqali o'zgartirishi mumkin va CamAgent kadrlari
    #   ham AYNI chegara bilan baholanishi shart вЂ” aks holda bir xil
    #   kadr ikki yo'lda har xil verdikt olardi.
    hisobot = analyze(baytlar, settings.quality_thresholds())

    # 3. `capture_runs` вЂ” `snapshots.capture_run_id` NOT NULL.
    #    Idempotentlik `(market_id, camera_id, business_date, slot_time)`
    #    unique cheklovi orqali.
    # ⚠ MINTAQA BOZORNIKI, QATTIQ YOZILGAN EMAS. `markets.timezone`
    #   ustuni bor va u bo'yicha `capture_repo._ENSURE_PLAN` reja
    #   quradi — bu yerda boshqa mintaqa ishlatilsa, bir xil kadr ikki
    #   xil `business_date` ga tushib, reja bilan JUFTLASHMASDI.
    mintaqa = (
        await session.execute(text("SELECT timezone FROM markets WHERE id = :m"), {"m": market_id})
    ).scalar_one_or_none() or "Asia/Tashkent"

    # ⛔ SLOT — ENG YAQIN JADVAL SLOTI, XOM SOAT EMAS (260829).
    #
    #   Kadr slot vaqtida TANIQ olinmaydi: agent `07:00` slotini
    #   `07:00:05` da yakunlaydi va 16 kamera 16 xil soniyada tugaydi.
    #   Xom vaqt ishlatilsa jadvalda `07:00:00`, `07:00:01` … deb 16 ta
    #   ALOHIDA ustun paydo bo'lardi va rejadagi `07:00` sloti «olinmadi»
    #   bo'lib turaverardi — o'lchangan.
    #
    # ⚠ Oyna ATAYIN keng (10 daqiqa): sekin obyektda 40 kamera ketma-ket
    #   olinadi va oxirgisi bir necha daqiqa kechikadi. Oynadan tashqari
    #   qolgan kadr esa haqiqatan REJAGA KIRMAGAN — u shunday ko'rinishi
    #   kerak, yashirilmasligi.
    if not payload.slot_time:
        yaqin = (
            await session.execute(
                text("""
            SELECT s.slot_time
              FROM snapshot_schedule_slots s
              JOIN snapshot_schedules sc
                ON sc.id = s.schedule_id AND sc.market_id = s.market_id
             WHERE sc.market_id = :m
               AND sc.period @> (:t AT TIME ZONE :tz)::date
             ORDER BY abs(extract(epoch FROM
                       (s.slot_time - (:t AT TIME ZONE :tz)::time)))
             LIMIT 1
        """),
                {"m": market_id, "t": payload.scheduled_at, "tz": mintaqa},
            )
        ).scalar_one_or_none()
    else:
        yaqin = None

    slot = _slot(payload.slot_time)
    if slot is None and yaqin is not None:
        farq = abs(
            (
                datetime.combine(date.min, yaqin)
                - datetime.combine(date.min, _mahalliy(payload.scheduled_at, mintaqa))
            ).total_seconds()
        )
        if farq <= 600:
            slot = yaqin
    run = (
        await session.execute(
            text("""
        INSERT INTO capture_runs
            (market_id, camera_id, nvr_id, slot_time, scheduled_at, status,
             attempts, started_at, finished_at, capture_method, is_market_open)
        VALUES (:market_id, :camera_id, :nvr_id,
                COALESCE(:slot, date_trunc('minute',
                          :scheduled_at AT TIME ZONE :tz)::time),
                :scheduled_at,
                'succeeded', 1, :captured_at, :captured_at, 'isapi',
                market_is_open(:market_id, (:scheduled_at AT TIME ZONE :tz)::date))
        ON CONFLICT ON CONSTRAINT uq_capture_runs_market_id_camera_id_business_date_slot_time
        DO UPDATE SET status = 'succeeded', finished_at = EXCLUDED.finished_at
        RETURNING id, snapshot_id
    """),
            {
                "market_id": market_id,
                "camera_id": camera_id,
                "nvr_id": nvr_id,
                "slot": slot,
                "scheduled_at": payload.scheduled_at,
                "tz": mintaqa,
                "captured_at": payload.captured_at,
            },
        )
    ).first()
    run_id, mavjud_snapshot = run[0], run[1]
    if mavjud_snapshot is not None:
        return SnapshotOut(
            snapshot_id=mavjud_snapshot, quality_verdict=hisobot.verdict, duplicate=True
        )

    # 4. `snapshots` вЂ” sifat verdikti bilan.
    snap = (
        await session.execute(
            text("""
        INSERT INTO snapshots
            (market_id, capture_run_id, camera_id, scheduled_at, captured_at,
             slot_time, object_key, size_bytes, width, height,
             quality_verdict, quality_mean, quality_stddev, quality_saturation,
             quality_thresholds_version, light_mode, capture_method)
        VALUES (:market_id, :run_id, :camera_id, :scheduled_at, :captured_at,
                COALESCE(:slot, date_trunc('minute',
                          :scheduled_at AT TIME ZONE :tz)::time),
                :object_key, :size_bytes, :width, :height,
                :verdict, :mean, :stddev, :saturation, :tv, :light, 'isapi')
        ON CONFLICT (market_id, object_key) DO NOTHING
        RETURNING id
    """),
            {
                "market_id": market_id,
                "run_id": run_id,
                "camera_id": camera_id,
                "scheduled_at": payload.scheduled_at,
                "captured_at": payload.captured_at,
                "slot": slot,
                "tz": mintaqa,
                "object_key": payload.object_key,
                "size_bytes": payload.size_bytes,
                "width": hisobot.width,
                "height": hisobot.height,
                "verdict": hisobot.verdict,
                "mean": hisobot.mean,
                "stddev": hisobot.stddev,
                "saturation": hisobot.saturation,
                "tv": QUALITY_THRESHOLDS_VERSION,
                "light": hisobot.light_mode,
            },
        )
    ).first()
    if snap is None:  # takroriy `object_key`
        return SnapshotOut(quality_verdict=hisobot.verdict, duplicate=True)

    snapshot_id = snap[0]
    await session.execute(
        text("UPDATE capture_runs SET snapshot_id = :sid WHERE id = :rid"),
        {"sid": snapshot_id, "rid": run_id},
    )

    # =====================================================================
    # URUG' REJIMI — MODEL YO'Q PAYTDA BANDLIKNI ODAM O'LCHAYDI.
    #
    # ⛔ SHU TRANZAKSIYA ICHIDA VA BU ATAYIN (`jobs/capture.py` bilan
    #    bir xil qaror): kadr qatori bilan urug' hodisasi BIRGA yoziladi
    #    yoki ikkalasi ham yozilmaydi. Alohida tranzaksiyada kadr yozilib
    #    hodisa yiqilsa, o'sha kadr nazoratchi navbatiga HECH QACHON
    #    tushmasdi va qaysi kadr qolib ketgani hech qayerda yozilmasdi.
    #
    # ⚠ `cv-service` GA MUHTOJ EMAS va aynan shu sababdan bu yerda:
    #   `seed_snapshot` sof BAZA ishi, ONNX modelisiz ishlaydi. CamAgent
    #   obyektlarida model hali yo'q (`ops/models/` bo'sh), bandlik esa
    #   BUGUN o'lchanishi kerak — aks holda hisob-kitob kutib turardi.
    #
    # ⚠ Zonasi yo'q kamera uchun `zones=0` qaytadi va bu XATO EMAS:
    #   kalibrovka qilinmagan kamera shunchaki hodisa bermaydi. Zona
    #   chizilgan sayin hodisalar o'zi paydo bo'la boshlaydi.
    # =====================================================================
    if settings.occupancy_seed_mode and hisobot.verdict == VERDICT_OK:
        await seed_snapshot(session, market_id=payload.market_id, snapshot_id=snapshot_id)

    log.info(
        "camagent_snapshot_accepted",
        market_id=market_id,
        camera_id=str(camera_id),
        verdict=hisobot.verdict,
    )
    return SnapshotOut(snapshot_id=snapshot_id, quality_verdict=hisobot.verdict)


def _mahalliy(payt: datetime, mintaqa: str) -> time:
    """UTC momentni bozor mintaqasidagi SOATga o'giradi."""
    return payt.astimezone(ZoneInfo(mintaqa)).time()


def _slot(qiymat: str) -> time | None:
    """`HH:MM` -> `time`. Bo'sh qiymat -> `None` (SQL o'zi hisoblaydi)."""
    if not qiymat:
        return None
    soat, daqiqa, *qolgan = qiymat.split(":")
    return time(int(soat), int(daqiqa), int(qolgan[0]) if qolgan else 0)


async def _read_object(settings: Settings, key: str) -> bytes:
    """S3'dan kadr baytlarini o'qiydi вЂ” sbozor'ning O'Z mijozi bilan.

    вљ  Har chaqiruvda yangi mijoz: `storage.open()` kontekst menejeri
      (`services/storage.py`) va u ulanishni o'zi yopadi. Kadr qabul
      qilish kamdan-kam (soatiga 16 ta), ya'ni ulanishni ushlab turish
      foydadan ko'ra murakkablik keltirardi.
    """
    async with storage_mod.open(settings) as store:
        return await store.get(key)
