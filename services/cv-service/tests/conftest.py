"""`cv-service` test to'plamining umumiy sozlamasi.

=============================================================================
BAZA FIXTURE'I SHU YERDA TUG'ILADI (05-08) — VA U `testcontainers` GA
TAYANMAYDI.

05-02 ning conftest'i buni ochiq va'da qilgan edi: *«Baza kerak bo'ladigan
integratsiya testlari 05-08 da tug'iladi va o'sha reja fixture'ni O'ZI
qo'shadi»*. Va'da bajarilmoqda, lekin MEXANIZM boshqa va sabab o'lchangan.

⚠⚠ NEGA `testcontainers` EMAS (repo ildizidagi `tests/conftest.py` esa
   AYNAN shuni ishlatadi). Uchta narx birga keladi va uchalasi ham
   `cv-service` uchun to'lanmaydi:

     1. `testcontainers[postgres]` + `psycopg` — IKKINCHI bog'liqlik
        to'plamiga ikkita yangi paket va 2.35 GB image'ning qayta
        qurilishi;
     2. SXEMA. Konteyner BO'SH ko'tariladi, ya'ni unga `alembic upgrade
        head` kerak — bu esa `alembic` VA `alembic-utils` ni ham shu
        image'ga olib kirardi (RLS siyosatlari, `SECURITY DEFINER`
        funksiyalar va o'zgarmaslik triggerlari `entities/` da yashaydi).
        `Base.metadata.create_all()` bilan qisqartirish YO'Q: u RLS ni
        ham, triggerlarni ham YARATMAYDI, ya'ni bu faylning butun
        maqsadi — tenant kontekstini VA D-21 langarini HAQIQIY sxemada
        o'lchash — yo'qolardi;
     3. `docker.sock` + `TESTCONTAINERS_HOST_OVERRIDE` — `compose.yaml`
        da `cv-tests` uchun uchta yangi band.

   Buning o'rniga to'plam MAVJUD, MIGRATSIYA QILINGAN bazaga boradi
   (`DATABASE_URL`). Bu repo ildizidagi conftest'ning O'Z qochish yo'li
   bilan bir xil mexanizm (`TEST_DATABASE_URL` — u ham konteyner
   ko'tarmaydi) va `04-06` ning ombor testlari bilan bir xil maqom:
   tashqi tayyorgarlik TALAB QILINADI va u YETISHMASA test QATTIQ
   YIQILADI, `skip` qilmaydi.

⚠ `skip` SHOXI ATAYIN YO'Q. 05-07 ning `model` markeri uchun aytilgan
  gap so'zma-so'z shu yerga tegishli: `skip` «o'lchov bajarildi» degan
  YOLG'ON signal berardi. Yiqilish xabari BAJARILADIGAN BUYRUQNI
  nomlaydi.

=============================================================================
⚠ TO'PLAMNING QOLGAN QISMI HAMON SOF.

Birlik testlari (`tests/unit/`) bazaga TEGMAYDI va quyidagi fixture'lar
ular uchun umuman qurilmaydi (pytest fixture'ni faqat SO'RALGANDA
quradi). Ya'ni `pytest tests/unit` bazasiz muhitda ham yashil.

=============================================================================
YO'LLAR `pyproject.toml` DA, BU YERDA EMAS.

`[tool.pytest.ini_options] pythonpath = [".", "tests"]` `app` va
`fixtures` paketlarini topadi; `sbozor_core` esa venv'ga editable
o'rnatilgan (`[tool.uv.sources]`). Ya'ni `sys.path` ni QO'LDA o'zgartirish
KERAK EMAS va u qilinmaydi.
=============================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from sbozor_core.db import make_engine, make_sessionmaker
from sqlalchemy import text

from app.db import system_transaction

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DATABASE_URL_ENV = "CV_TEST_DATABASE_URL"
FALLBACK_DATABASE_URL_ENV = "DATABASE_URL"
"""Ikki kalit va TARTIB muhim.

`CV_TEST_DATABASE_URL` — ATAYIN BIRINCHI: u ishlab chiqarish
o'zgaruvchisini (`DATABASE_URL`) BEKOR QILADI, ya'ni test to'plamini
boshqa bazaga yo'naltirish uchun servisning o'z sozlamasini o'zgartirish
kerak emas. Repo ildizidagi `tests/conftest.py` ning `TEST_DATABASE_URL`
qochish yo'li bilan aynan bir xil qaror.
"""

SEED_DATABASE_URL_ENV = "CV_TEST_SEED_DATABASE_URL"
"""SEED uchun EGA roli — ilova rolidan ATAYIN AJRATILGAN.

⚠ O'LCHANGAN ZARURIYAT (2026-08-09,
  `information_schema.role_table_grants`): `sbozor_app` da `markets`
  uchun FAQAT `SELECT` bor. Bozor yaratish — EGA ning ishi va bu
  MAHSULOT QARORI, test cheklovi emas.

⚠ AJRATISH TESTNI KUCHAYTIRADI: `detect` va uning natijasini o'qish
  hamon `sbozor_app` (NOSUPERUSER, NOBYPASSRLS) ostida boradi, ya'ni
  RLS da'vosi haqiqiy qoladi. Repo ildizidagi conftest ham aynan shu
  bo'linishga ega (`owner_url` ↔ `app_url`).
"""

SETUP_HINT = (
    "Bazaga yo'l yo'q. `cv-service` ning integratsiya testlari MIGRATSIYA "
    "QILINGAN Postgres talab qiladi (RLS, kompozit FK va o'zgarmaslik "
    "triggerlari sxemada yashaydi). Tayyorlash:\n"
    "    npm run up      # `db` ko'tariladi\n"
    "    npm run migrate # `alembic upgrade head`\n"
    f"So'ng `{FALLBACK_DATABASE_URL_ENV}` yoki `{DATABASE_URL_ENV}` "
    "o'rnatilgan bo'lishi kerak (`compose.yaml` dagi `cv-tests` buni "
    "avtomatik beradi)."
)

SEED_SLOT_TIME = time(6, 0)
"""06:00 — kunning BIRINCHI sloti (`04-05` ning rejasi bilan bir xil)."""

SEED_FRAME_WIDTH = 640
SEED_FRAME_HEIGHT = 480
"""Sintetik kadr o'lchami — kichik, chunki uning MAZMUNI hech qayerda o'qilmaydi.

⚠ ZONA POLIGONI NORMALANGAN (0..1) saqlanadi, ya'ni bu sonlar zona
  geometriyasiga TA'SIR QILMAYDI — ular faqat piksellashtirish shkalasini
  belgilaydi. Kattaroq kadr testni sekinlashtirardi va HECH NIMA
  qo'shmasdi.
"""


@dataclass(frozen=True, slots=True)
class FrameSeed:
    """Bitta bozor, bitta kamera, ikki rasta va bitta kadr.

    ⚠ NOMLAR FIZIK FAKT BO'YICHA (§S-9): `zone_ids` — «shu kamerada
      chizilgan faol konturlar», `snapshot_id` — «shu kadr». Birorta nom
      verdikt aytmaydi (`zone_that_makes_it_occupied` ❌), aks holda
      fixture tekshirilayotgan qoidaning AKS-SADOSI bo'lib qolardi.
    """

    market_id: UUID
    camera_id: UUID
    stall_ids: tuple[UUID, ...]
    zone_ids: tuple[UUID, ...]
    snapshot_id: UUID
    object_key: str


def _database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV) or os.environ.get(FALLBACK_DATABASE_URL_ENV)
    if not url:
        pytest.fail(SETUP_HINT)
    return url


def _seed_database_url() -> str:
    url = os.environ.get(SEED_DATABASE_URL_ENV)
    if not url:
        pytest.fail(f"`{SEED_DATABASE_URL_ENV}` o'rnatilmagan.\n\n{SETUP_HINT}")
    return url


@pytest.fixture
async def seed_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """EGA roli ostidagi sessiya fabrikasi — FAQAT seed va tozalash uchun.

    ⚠ BU FABRIKA `detect()` GA HECH QACHON BERILMAYDI. Ega
      `owner_bootstrap` siyosati (`USING true`) ostida ishlaydi, ya'ni
      unga berilgan job RLS ni umuman his qilmasdi va tenant
      da'vosining butun mazmuni yo'qolardi.
    """
    engine = make_engine(_seed_database_url())
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def db_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessiya fabrikasi — HAR TEST uchun YANGI engine.

    ⚠ ENGINE FUNKSIYA DARAJASIDA VA BU MAJBURIY: `asyncpg` ning puli
      HODISA ILMOG'IGA bog'langan, `pytest-asyncio` esa har testga yangi
      ilmoq beradi. Sessiya darajasidagi engine ikkinchi testda
      «attached to a different loop» bilan yiqilardi.
    """
    engine = make_engine(_database_url())
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM occupancy_events WHERE false"))
    except Exception as exc:  # noqa: BLE001 - sabab foydalanuvchiga ko'rsatiladi
        await engine.dispose()
        pytest.fail(f"{SETUP_HINT}\n\nAsl xato: {type(exc).__name__}: {exc}")
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


async def _seed(
    session: AsyncSession, seed: FrameSeed, *, quality_verdict: str, days_ago: int
) -> None:
    """Bitta kadrga yetadigan eng QISQA zanjir — SQL matni `tests/fixtures/` dan.

    Ustun ro'yxatlari repo ildizidagi seed modullaridan (`nvr_domain.py`,
    `market_domain.py`, `snapshot_domain.py`) NUSXA OLINGAN, IMPORT
    QILINMAGAN: o'sha modullar `psycopg` ga tayanadi va u bu image'da
    yo'q (`core-api` ning test to'plami). Nusxaning narxi ochiq yozilsin —
    ustun ro'yxati o'zgarsa bu fayl ham o'zgarishi kerak, va uni
    migratsiya EMAS, birinchi yugurish aytadi (`INSERT` `NOT NULL` da
    yiqiladi).

    Args:
        days_ago: `scheduled_at` ni shuncha kun ORQAGA suradi.
            ⚠⚠ BU PARAMETR SABOTAJ BILAN TUG'ILDI (2026-08-09) VA U
               «QULAYLIK» EMAS. `business_date` — `snapshots` da
               `GENERATED ... (scheduled_at AT TIME ZONE 'Asia/Tashkent')`,
               ya'ni BUGUNGI kadr uchun u `date.today()` GA TENG. O'lchandi:
               `detect` da `snapshot.business_date` -> `date.today()`
               almashtirilganda 17 testning HAMMASI yashil qoldi — Pitfall
               3 ning butun mazmuni (yarim tunda bir kun farq) bugungi
               kadrda KO'RINMAYDI. `days_ago > 0` bo'lgan seed farqni
               HAR QANDAY soatda ko'rinadigan qiladi.
    """
    scheduled_at = datetime.now(tz=UTC) - timedelta(days=days_ago)
    nvr_id = uuid4()
    zone_row_id = uuid4()

    await session.execute(
        text("INSERT INTO markets (id, name) VALUES (:id, :name)"),
        {"id": seed.market_id, "name": f"CV test bozori {seed.market_id.hex[:8]}"},
    )
    await session.execute(
        text("INSERT INTO zones (id, market_id, name) VALUES (:id, :market_id, :name)"),
        {"id": zone_row_id, "market_id": seed.market_id, "name": "Sabzavot qatori"},
    )
    for index, stall_id in enumerate(seed.stall_ids, start=1):
        await session.execute(
            text(
                "INSERT INTO stalls (id, market_id, zone_id, code) "
                "VALUES (:id, :market_id, :zone_id, :code)"
            ),
            {
                "id": stall_id,
                "market_id": seed.market_id,
                "zone_id": zone_row_id,
                "code": f"A-{index:03d}",
            },
        )
    await session.execute(
        text(
            "INSERT INTO nvr_devices (id, market_id, host, port, username, model, "
            " device_type, serial_number, rtsp_port, rtsp_port_assumed) "
            "VALUES (:id, :market_id, :host, 80, 'admin', 'DS-7616NI-K2', 'NVR', "
            " :serial, 554, false)"
        ),
        {
            "id": nvr_id,
            "market_id": seed.market_id,
            "host": "10.77.0.10",
            "serial": f"CVTEST{nvr_id.hex[:10].upper()}",
        },
    )
    await session.execute(
        text(
            "INSERT INTO cameras (id, market_id, nvr_id, channel_no, stream_name, name, "
            " status, has_substream) "
            "VALUES (:id, :market_id, :nvr_id, 1, :stream, 'Kanal 1', 'online', true)"
        ),
        {
            "id": seed.camera_id,
            "market_id": seed.market_id,
            "nvr_id": nvr_id,
            # GLOBAL UNIQUE (`uq_cameras_stream_name`) — nom har chaqiruvda
            # YANGI bo'lishi shart, aks holda ikkinchi test `23505` berardi.
            "stream": f"cam_{seed.camera_id.hex}",
        },
    )
    for stall_id, camera_zone_id in zip(seed.stall_ids, seed.zone_ids, strict=True):
        await session.execute(
            text(
                "INSERT INTO camera_zones (id, market_id, camera_id, stall_id, version, "
                " polygon, source_width, source_height, is_active) "
                "VALUES (:id, :market_id, :camera_id, :stall_id, 1, "
                " CAST(:polygon AS jsonb), :w, :h, true)"
            ),
            {
                "id": camera_zone_id,
                "market_id": seed.market_id,
                "camera_id": seed.camera_id,
                "stall_id": stall_id,
                # Kadrning CHAP yarmi — geometrik fakt, verdikt emas.
                "polygon": "[[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]",
                "w": SEED_FRAME_WIDTH,
                "h": SEED_FRAME_HEIGHT,
            },
        )

    capture_run_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO capture_runs (id, market_id, camera_id, nvr_id, slot_time, "
            " scheduled_at, status, attempts, capture_method, is_market_open) "
            "VALUES (:id, :market_id, :camera_id, :nvr_id, :slot_time, :scheduled_at, "
            " 'succeeded', 1, 'go2rtc', true)"
        ),
        {
            "id": capture_run_id,
            "market_id": seed.market_id,
            "camera_id": seed.camera_id,
            "nvr_id": nvr_id,
            "slot_time": SEED_SLOT_TIME,
            "scheduled_at": scheduled_at,
        },
    )
    await session.execute(
        text(
            "INSERT INTO snapshots (id, market_id, capture_run_id, camera_id, scheduled_at, "
            " captured_at, slot_time, object_key, size_bytes, quality_verdict, "
            " quality_thresholds_version, light_mode, capture_method, width, height) "
            "VALUES (:id, :market_id, :run_id, :camera_id, :scheduled_at, :scheduled_at, "
            " :slot_time, :object_key, 4096, :verdict, 1, 'day', 'go2rtc', :w, :h)"
        ),
        {
            "id": seed.snapshot_id,
            "market_id": seed.market_id,
            "run_id": capture_run_id,
            "camera_id": seed.camera_id,
            "scheduled_at": scheduled_at,
            "slot_time": SEED_SLOT_TIME,
            "object_key": seed.object_key,
            "verdict": quality_verdict,
            "w": SEED_FRAME_WIDTH,
            "h": SEED_FRAME_HEIGHT,
        },
    )


async def _cleanup(sessionmaker: async_sessionmaker[AsyncSession], market_id: UUID) -> None:
    """Bozorni QORALAMAGA tushiradi va MAHSULOTNING O'Z kaskadi bilan o'chiradi.

    ⚠ KASKAD QO'LDA YOZILMAYDI. `market_delete_draft()` (`0019` da
      bandlik domeni bilan kengaytirilgan) tartibni O'ZI biladi va u
      MAHSULOT KODI — ya'ni tozalash yo'li kelajakda yangi jadval
      qo'shilganda AVTOMATIK to'g'ri qoladi. Qo'lda yozilgan `DELETE`
      ro'yxati esa jimgina eskirardi va qoldiq qatorlar keyingi
      yugurishda `23505` berardi.

    ⚠ `is_active = false` MAJBURIY VA U ZAIFLASHTIRISH EMAS: `0013`
      faol bozorni o'chirishni taqiqlaydi va `occupancy_events` ning
      o'zgarmaslik qo'riqchisi `DELETE` ga faqat QORALAMA bozorda ruxsat
      beradi (05-05, deviatsiya #2). Bu mahsulot qoidasining O'ZI —
      `tests/fixtures/market_domain.py` da ham aynan shu qadam bor.
    """
    async with system_transaction(
        sessionmaker, market_id=market_id, request_id=f"cv-test-cleanup-{market_id}"
    ) as session:
        await session.execute(
            text("UPDATE markets SET is_active = false WHERE id = :id"), {"id": market_id}
        )
        await session.execute(text("SELECT market_delete_draft(:id)"), {"id": market_id})


@pytest.fixture
async def frame_seed(
    seed_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[FrameSeed]:
    """`quality_verdict = 'ok'` kadr + shu kameraning ikki faol zonasi."""
    async for seed in _seeded(seed_sessionmaker, quality_verdict="ok", days_ago=0):
        yield seed


@pytest.fixture
async def dark_frame_seed(
    seed_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[FrameSeed]:
    """`quality_verdict = 'dark'` kadr — `is_billable` HOSILA ustuni `false` beradi."""
    async for seed in _seeded(seed_sessionmaker, quality_verdict="dark", days_ago=0):
        yield seed


@pytest.fixture
async def past_frame_seed(
    seed_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[FrameSeed]:
    """UCH KUN OLDINGI kadr — `business_date` BUGUNGI SANAGA TENG EMAS.

    ⚠ FIXTURE SABOTAJ BILAN TUG'ILDI: `_seed()` ning `days_ago`
      docstringiga qarang. Bugungi kadrda «qatordan nusxalandi» va
      «bugundan hisoblandi» IKKI XIL KOD bir xil natija beradi.
    """
    async for seed in _seeded(seed_sessionmaker, quality_verdict="ok", days_ago=3):
        yield seed


async def _seeded(
    sessionmaker: async_sessionmaker[AsyncSession], *, quality_verdict: str, days_ago: int
) -> AsyncIterator[FrameSeed]:
    market_id = uuid4()
    seed = FrameSeed(
        market_id=market_id,
        camera_id=uuid4(),
        stall_ids=(uuid4(), uuid4()),
        zone_ids=(uuid4(), uuid4()),
        snapshot_id=uuid4(),
        object_key=f"{market_id}/2026-08-09/cam/0600.jpg",
    )
    async with system_transaction(
        sessionmaker, market_id=market_id, request_id=f"cv-test-seed-{market_id}"
    ) as session:
        await _seed(session, seed, quality_verdict=quality_verdict, days_ago=days_ago)
    try:
        yield seed
    finally:
        await _cleanup(sessionmaker, market_id)


async def read_events(
    sessionmaker: async_sessionmaker[AsyncSession], market_id: UUID
) -> list[dict[str, Any]]:
    """Shu bozorning `occupancy_events` qatorlari — TENANT KONTEKSTI ostida.

    ⚠ Test yozuvchi bilan BIR XIL yo'ldan o'qiydi (RLS ostida), ya'ni
      «yozildi» da'vosi kontekstsiz `SELECT` bilan tekshirilmaydi.
      Kontekstsiz o'qish 0 qator berardi va test IKKALA holatda ham —
      yozuv bo'lmaganda ham, RLS ni chetlab o'tganda ham — bir xil
      javob ko'rardi.
    """
    async with system_transaction(
        sessionmaker, market_id=market_id, request_id=f"cv-test-read-{market_id}"
    ) as session:
        rows = (
            await session.execute(
                text(
                    "SELECT camera_zone_id, business_date, slot_time, verdict, confidence, "
                    "       model_version, thresholds_version, zone_version, "
                    "       snapshot_is_billable "
                    "  FROM occupancy_events WHERE market_id = :market_id "
                    " ORDER BY camera_zone_id"
                ),
                {"market_id": market_id},
            )
        ).mappings()
        return [dict(row) for row in rows]
