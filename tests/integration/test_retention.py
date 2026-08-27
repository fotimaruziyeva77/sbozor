"""Saqlash siyosati — HAQIQIY SeaweedFS ustida, 90 kunni KUTMASDAN (CAM-07, D-18).

=============================================================================
BU FAYL «MEXANIZM» NI ISBOTLAYDI, «90 KUN» NI EMAS — VA FARQ OCHIQ YOZILGAN.

Isbotlanadigan da'vo: *chegara kelganda kadr siqiladi, o'lchamlari saqlanadi,
kaliti o'zgarmaydi va ikkinchi marta siqilmaydi; muddat tugaganda obyekt
arxivdan chiqadi, QATOR esa qoladi.*

Isbotlanmaydigan da'vo: *siyosat 90 haqiqiy kun davomida ishlab turadi.*
Ikkinchisini faqat vaqt isbotlaydi va u `04-VALIDATION.md` da Manual-Only
band sifatida, egasi Ops bilan turadi. Bu faylni «90 kunlik siyosat
sinaldi» deb o'qish XATO bo'lardi.

MEXANIKA (§D.10 ning aniq tavsiyasi): vaqt SILJITILMAYDI. `freezegun` ham,
soatni almashtirish ham YO'Q — ularning o'rniga IKKI argument:

    RetentionPolicy(full_days=0, ...)   <- chegara SOZLAMA
    retention_daily(..., today=<sana>)  <- vaqt ARGUMENT

Ikkalasi ham mahsulot yo'lidagi haqiqiy parametrlar, ya'ni test mahsulotni
o'zgartirmaydi va yangi bog'liqlik ham qo'shmaydi.
=============================================================================

=============================================================================
MOCK YO'Q. Ombor — HAQIQIY `storage` konteyneri, baza — HAQIQIY Postgres.

Siqishning butun mazmuni ombordagi BAYTLARDA: «`size_bytes` ustuni
kamaydi» degan da'vo mock ostida ham yashil bo'lardi. Shuning uchun har
bir da'vo obyektni QAYTA O'QIB tekshiriladi (`get` -> `Image.open` ->
`size`), 03-14 ning metodikasi bo'yicha.
=============================================================================
"""

from __future__ import annotations

import io
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from app.jobs.retention import (
    RETENTION_COMPONENT,
    RetentionPolicy,
    RetentionResult,
    disk_usage_percent,
    retention_daily,
)
from app.services.object_key import object_key
from fixtures.frames import frame_bytes
from fixtures.nvr_domain import nvr_rows
from PIL import Image
from sbozor_core.enums import CaptureMethod, SnapshotLightMode, SnapshotQuality, SnapshotTier
from sbozor_core.timeutil import MARKET_TZ, business_today

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import date
    from uuid import UUID

    from app.services.storage import SnapshotStorage
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]


SLOT = time(6, 30)
"""Zond kadrining standart sloti — kalit shakli uchun ahamiyatsiz, lekin QADALGAN."""

ORIGINAL_QUALITY = 92
"""Zond kadri ATAYIN yuqori sifat bilan yoziladi.

Siyosatning standarti 60, ya'ni 92 -> 60 qayta kodlash hajmni ANIQ
kamaytiradi. Teng sifat bilan yozilgan kadr uchun natija noaniq bo'lardi
va test «siqish ishladimi?» degan savolga o'z farazi bilan javob berardi.
"""

FRAME_SIZE = (1280, 720)
"""HAQIQIY kadr o'lchami (04-04 ning o'lchovi: 320x180 kadr 4 KB dan kichik).

Kichik kadrda JPEG sarlavhalari tananing sezilarli ulushini egallaydi va
qayta kodlash yutug'i shovqin ichida yo'qolardi.
"""

COMPRESS_ONLY = RetentionPolicy(
    # ⚠ NOL — QONUNIY QIYMAT va u shu faylning butun mexanizmi.
    full_days=0,
    # Tozalash chegarasi UZOQ kelajakda: shunda siqish testlari faqat
    # SIQISHNI o'lchaydi. Ikkalasini bitta siyosatda birlashtirish har
    # siqish testini jimgina tozalash testiga aylantirardi.
    compressed_days=365,
    jpeg_quality=60,
    batch_size=200,
)

PURGE_TOO = RetentionPolicy(full_days=0, compressed_days=0, jpeg_quality=60, batch_size=200)
"""Ikkala chegara ham ochiq — siqish VA arxivdan chiqarish bir yugurishda."""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, capture_method, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, 'succeeded', 1, %s, true)"
)

_INSERT_SNAPSHOT = (
    "INSERT INTO snapshots "
    "(id, market_id, capture_run_id, camera_id, scheduled_at, captured_at, slot_time, "
    " object_key, size_bytes, quality_verdict, quality_mean, quality_stddev, "
    " quality_thresholds_version, light_mode, capture_method, storage_tier, width, height) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_SNAPSHOT_STATE = (
    "SELECT storage_tier, size_bytes, object_key, object_deleted_at, is_billable "
    "FROM snapshots WHERE id = %s"
)

_COUNT_SNAPSHOTS = "SELECT count(*) FROM snapshots WHERE market_id = %s"
_HEARTBEAT = "SELECT last_seen_at, detail FROM system_heartbeats WHERE component = %s"


class _Frame:
    """Bazada qatori, omborda obyekti bor bitta zond kadri."""

    __slots__ = ("business_date", "camera_id", "key", "market_id", "original_size", "snapshot_id")

    def __init__(
        self,
        *,
        market_id: UUID,
        camera_id: UUID,
        snapshot_id: UUID,
        key: str,
        business_date: date,
        original_size: int,
    ) -> None:
        self.market_id = market_id
        self.camera_id = camera_id
        self.snapshot_id = snapshot_id
        self.key = key
        self.business_date = business_date
        self.original_size = original_size


def _dimensions(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.size


class _Bed:
    """Bitta o'lchov uchun kerak bo'lgan hamma narsa."""

    __slots__ = ("camera_id", "conn", "market_id", "nvr_id", "storage", "today")

    def __init__(
        self,
        *,
        conn: Connection[TupleRow],
        storage: SnapshotStorage,
        market_id: UUID,
        nvr_id: UUID,
        camera_id: UUID,
        today: date,
    ) -> None:
        self.conn = conn
        self.storage = storage
        self.market_id = market_id
        self.nvr_id = nvr_id
        self.camera_id = camera_id
        self.today = today

    async def write_frame(
        self,
        *,
        days_ago: int = 0,
        tier: str = SnapshotTier.FULL.value,
        slot: time = SLOT,
        data: bytes | None = None,
    ) -> _Frame:
        """Kadrni AVVAL omborga, KEYIN bazaga yozadi (§B.4 ning tartibi)."""
        payload = (
            data
            if data is not None
            else frame_bytes(mean=120, stddev=40, size=FRAME_SIZE, quality=ORIGINAL_QUALITY)
        )
        day = self.today - timedelta(days=days_ago)
        key = object_key(
            market_id=self.market_id,
            business_date=day,
            camera_id=self.camera_id,
            slot_time=slot,
        )
        await self.storage.put(key, payload)

        # `business_date` — GENERATED ustun va u `scheduled_at` dan
        # hisoblanadi, ya'ni «eski kadr» AYNAN shu qiymat bilan quriladi.
        scheduled_at = datetime.combine(day, slot, tzinfo=MARKET_TZ)
        run_id = uuid4()
        snapshot_id = uuid4()
        self.conn.execute(
            _INSERT_RUN,
            (
                str(run_id),
                str(self.market_id),
                str(self.camera_id),
                str(self.nvr_id),
                slot,
                scheduled_at,
                CaptureMethod.ISAPI.value,
            ),
        )
        self.conn.execute(
            _INSERT_SNAPSHOT,
            (
                str(snapshot_id),
                str(self.market_id),
                str(run_id),
                str(self.camera_id),
                scheduled_at,
                scheduled_at.replace(second=9),
                slot,
                key,
                len(payload),
                SnapshotQuality.OK.value,
                "112.40",
                "48.75",
                1,
                SnapshotLightMode.DAY.value,
                CaptureMethod.ISAPI.value,
                tier,
                None,
                None,
            ),
        )
        return _Frame(
            market_id=self.market_id,
            camera_id=self.camera_id,
            snapshot_id=snapshot_id,
            key=key,
            business_date=day,
            original_size=len(payload),
        )

    def state(self, frame: _Frame) -> dict[str, Any]:
        row = self.conn.execute(_SNAPSHOT_STATE, (str(frame.snapshot_id),)).fetchone()
        assert row is not None, "qator YO'QOLDI — bu siyosatning eng qattiq taqig'i"
        return {
            "storage_tier": row[0],
            "size_bytes": row[1],
            "object_key": row[2],
            "object_deleted_at": row[3],
            "is_billable": row[4],
        }

    def snapshot_count(self) -> int:
        row = self.conn.execute(_COUNT_SNAPSHOTS, (str(self.market_id),)).fetchone()
        assert row is not None
        return int(row[0])


@pytest.fixture
async def bed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    s3_client: SnapshotStorage,
) -> AsyncIterator[_Bed]:
    """Faol bozor + NVR + kamera + ombor prefiksining kafolatlangan tozalanishi.

    ⚠ OMBOR PREFIKSI TESTDAN KEYIN SUPURILADI. Seed bozori `s3_markets`
      fixture'idan KELMAYDI (u o'z `uuid4()` larini beradi), ya'ni bu
      yerdagi tozalash MAJBURIY: 455 kunlik saqlash siyosati bo'lgan
      omborda qoldiq jimgina to'planadigan qarz.
    """
    with nvr_rows(sync_owner_conn, two_markets) as nvr:
        rows = nvr.market_a
        market_ids = [str(market_id) for market_id in nvr.market_ids]
        try:
            yield _Bed(
                conn=sync_owner_conn,
                storage=s3_client,
                market_id=rows.market_id,
                nvr_id=rows.nvr_id,
                camera_id=rows.active_camera_ids[0],
                today=business_today(),
            )
        finally:
            sync_owner_conn.execute(
                "DELETE FROM snapshots WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM capture_runs WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            for market_id in market_ids:
                keys = await s3_client.list_prefix(f"{market_id}/")
                if keys:
                    await s3_client.delete_many(keys)


async def _run(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    bed: _Bed,
    *,
    policy: RetentionPolicy = COMPRESS_ONLY,
) -> RetentionResult:
    """`retention_daily` ni BUGUNGI kadr ham qamraladigan qilib chaqiradi.

    ⚠ `today + 1 kun`: repozitoriyning predikati `business_date < older_than`
      va chegara O'ZI KIRMAYDI (`retention_candidates` docstringi). Ya'ni
      `full_days=0` bilan «bugungi kadr ham siqilsin» degani `today` ga
      ertangi kunni berish — bu MAHSULOT arifmetikasi, test hiylasi emas:
      ertangi haqiqiy yugurish bugungi kadrni AYNAN shu yo'l bilan ko'radi.

    Yon foyda: yetim supurgisi `today - 1` ni ko'radi, ya'ni bu chaqiruvda
    u AYNAN bugungi prefiksni tekshiradi.
    """
    return await retention_daily(
        sessionmaker,
        storage,
        policy=policy,
        today=bed.today + timedelta(days=1),
    )


# ===========================================================================
# 1. SIQISH — 90 kunni KUTMASDAN
# ===========================================================================


async def test_todays_frame_is_compressed_when_the_threshold_is_zero(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """Mexanizm 90 kunni kutmasdan isbotlanadi: chegara — SOZLAMA."""
    frame = await bed.write_frame()

    result = await _run(api_sessionmaker, s3_client, bed)

    assert result.compressed == 1, f"siqilmadi: {result}"
    assert bed.state(frame)["storage_tier"] == SnapshotTier.COMPRESSED.value


async def test_the_compressed_object_is_still_decodable(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """«Tiklash» shu fazada = QAYTA O'QISH (§D.10 ning 3-bandi, (a) qismi).

    ⚠ Bu to'liq zaxira/tiklash mashqi EMAS — u FOUND-07 va 8-faza. Bu
      yerda isbotlanadigan yagona narsa: siyosat obyektni O'QILADIGAN
      holatda qoldiradi.
    """
    frame = await bed.write_frame()

    await _run(api_sessionmaker, s3_client, bed)

    stored = await s3_client.get(frame.key)
    with Image.open(io.BytesIO(stored)) as image:
        image.load()
        assert image.format == "JPEG"


async def test_the_compressed_object_keeps_its_dimensions(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """§D.10 ning 3-bandi, (b) qismi — KICHRAYTIRISH YO'Q.

    O'lcham o'zgarsa 5-fazadagi zona poligonlari kadr piksellari bilan mos
    kelmay qolardi va arxiv ustida CV ni qayta ishga tushirish imkonsiz
    bo'lardi.
    """
    frame = await bed.write_frame()

    await _run(api_sessionmaker, s3_client, bed)

    assert _dimensions(await s3_client.get(frame.key)) == FRAME_SIZE


async def test_the_compressed_object_is_smaller(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """§D.10 ning 3-bandi, (c) qismi — hajm HAQIQATAN kamayadi.

    Ikki manba ham tekshiriladi: ombordagi obyektning O'ZI va bazadagi
    `size_bytes`. Faqat bazani tekshirish «ustun yangilandi, obyekt esa
    tegilmadi» holatini o'tkazib yuborardi.
    """
    frame = await bed.write_frame()

    await _run(api_sessionmaker, s3_client, bed)

    stored = await s3_client.get(frame.key)
    assert len(stored) < frame.original_size
    assert bed.state(frame)["size_bytes"] == len(stored)


async def test_compression_writes_over_the_same_key(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """Kalit O'ZGARMAYDI — 6-fazadagi dalil havolalari buzilmaydi.

    Prefiksda AYNAN BITTA obyekt qoladi: yangi kalit yozilsa eskisi ham
    joyida qolardi va arxiv ikki barobar o'sardi.
    """
    frame = await bed.write_frame()

    await _run(api_sessionmaker, s3_client, bed)

    assert bed.state(frame)["object_key"] == frame.key
    assert await s3_client.list_prefix(f"{bed.market_id}/") == [frame.key]


async def test_a_second_run_does_not_compress_the_frame_again(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """⛔ Pitfall 13 — IKKI MARTA SIQISH avlod yo'qotishini to'playdi.

    Predikat (`tier=COMPRESSIBLE_TIER`) buni STRUKTURAVIY to'sadi: birinchi
    yugurishdan keyin qator `compressed` bo'ladi va u nomzodlar to'plamiga
    umuman tushmaydi.

    =====================================================================
    ⚠⚠ `not_smaller == 0` — SHU TESTNING ENG MUHIM ASSERTI, VA U O'LCHOV
       NATIJASIDA QO'SHILDI.

    Rejaning sabotaji («nomzod predikatini `PURGEABLE_TIERS` ga
    kengaytirish») HECH QANDAY testni qizartirmadi — o'lchandi. Sabab:
    `mark_compressed()` ning O'ZIDA `storage_tier = 'full'` sharti bor
    (04-05), ya'ni allaqachon siqilgan QATOR ikkinchi marta YANGILANMAYDI
    va `result.compressed` baribir 0 bo'lib qoladi.

    LEKIN OBYEKT HIMOYALANMAGAN EDI: kengaytirilgan predikat bilan
    `compressed` kadr ENKODERGA QAYTA BERILADI. Bu yugurishda u omborga
    yozilmadi (natija kichraymadi), ya'ni zarar KO'RINMADI — sifat
    sozlamasi boshqa bo'lgan har qanday holatda esa obyekt ustiga IKKI
    MARTA siqilgan versiya yozilardi va baza ESKI hajmni ko'rsatib turardi.

    `not_smaller` aynan «enkoder chaqirildi va foyda bermadi» hodisasini
    sanaydi, ya'ni u SABOTAJ TOMONIDAN qizartiriladigan yagona o'lchov.
    Nazorat 04-04/04-06/04-07 ning naqshi bo'yicha qo'shildi: darvozaning
    mustaqil nazorati SO'NGGI qatlamdan O'TA OLADIGAN kirish bilan
    quriladi.
    =====================================================================
    """
    frame = await bed.write_frame()

    first = await _run(api_sessionmaker, s3_client, bed)
    after_first = bed.state(frame)["size_bytes"]
    stored_after_first = await s3_client.get(frame.key)
    second = await _run(api_sessionmaker, s3_client, bed)

    assert first.compressed == 1
    assert second.compressed == 0, "ikkinchi yugurish qatorni QAYTA siqdi"
    assert second.not_smaller == 0, "siqilgan kadr ENKODERGA qayta berildi (Pitfall 13)"
    assert bed.state(frame)["size_bytes"] == after_first
    assert await s3_client.get(frame.key) == stored_after_first


# ===========================================================================
# 2. ARXIVDAN CHIQARISH — obyekt ketadi, QATOR QOLADI
# ===========================================================================


async def test_an_expired_frame_loses_its_object_but_keeps_its_row(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """⛔ Siyosatning eng qattiq taqig'i: QATOR HECH QACHON O'CHIRILMAYDI.

    Uch da'vo bir joyda: obyekt ketdi, qator qoldi, `is_billable`
    O'ZGARMADI (o'sha paytda qilingan hisob retroaktiv bekor qilinmaydi).
    """
    frame = await bed.write_frame(tier=SnapshotTier.COMPRESSED.value)
    assert bed.state(frame)["is_billable"] is True

    result = await _run(api_sessionmaker, s3_client, bed, policy=PURGE_TOO)

    state = bed.state(frame)
    assert result.purged == 1
    assert state["storage_tier"] == SnapshotTier.PURGED.value
    assert state["object_deleted_at"] is not None
    assert state["is_billable"] is True, "hisob retroaktiv bekor qilindi"
    assert await s3_client.head(frame.key) is None


async def test_a_frame_that_could_not_be_compressed_is_still_purged(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """Siqish bosqichidan O'TA OLMAGAN kadr ham arxivdan CHIQADI.

    ⚠ Bu `PURGEABLE_TIERS` ga `full` KIRITILGANINING sababi (04-05 ning
      o'z docstringi). Faqat `compressed` ni tozalash buzuq obyekt tufayli
      `full` bo'lib qolgan kadrni MANGU saqlab qolardi — jimgina, chunki
      hech qanday xato chiqmasdi va disk faqat oylar keyin to'lardi.
    """
    broken = await bed.write_frame(data=b"\xff\xd8\xff-dekodlanmaydi")

    result = await _run(api_sessionmaker, s3_client, bed, policy=PURGE_TOO)

    assert result.compressed == 0, "buzuq obyekt siqildi deb hisoblandi"
    assert result.purged == 1
    assert bed.state(broken)["storage_tier"] == SnapshotTier.PURGED.value
    assert await s3_client.head(broken.key) is None


# ===========================================================================
# 3. YETIM OBYEKT SUPURGISI — AYNAN BITTA KUN
# ===========================================================================


async def test_an_orphan_object_is_swept_for_the_previous_day(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """Omborda bor, bazada yo'q obyekt kun prefiksi bo'yicha o'chiriladi."""
    orphan = object_key(
        market_id=bed.market_id,
        business_date=bed.today,
        camera_id=bed.camera_id,
        slot_time=time(18, 0),
    )
    await s3_client.put(orphan, b"\xff\xd8\xff-yetim")

    result = await _run(api_sessionmaker, s3_client, bed)

    assert result.orphans_deleted == 1
    assert await s3_client.head(orphan) is None


async def test_the_sweep_never_touches_a_live_object(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """NAZORAT HOLATI: bazada qatori bor obyekt yetim EMAS.

    Bu testsiz supurgi «hamma narsani o'chir» bo'lsa ham yashil qolardi —
    yuqoridagi test faqat «yetim ketdimi?» degan savolga javob beradi.

    Siyosat ATAYIN hech nimani siqmaydigan qilib qo'yilgan (chegara 10 kun
    oldinda), ya'ni yagona o'lchanadigan narsa — supurgining unga
    TEGMAGANI.
    """
    policy = RetentionPolicy(full_days=10, compressed_days=365, jpeg_quality=60, batch_size=200)
    frame = await bed.write_frame()

    result = await _run(api_sessionmaker, s3_client, bed, policy=policy)

    assert result.orphans_deleted == 0
    assert await s3_client.head(frame.key) is not None
    assert bed.state(frame)["storage_tier"] == SnapshotTier.FULL.value


# ===========================================================================
# 4. YUGURISHNING O'ZI — vaqt, yurak urishi va yiqilmaslik
# ===========================================================================


async def test_the_run_writes_its_heartbeat(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """`system_heartbeats['retention']` — `retention_stale` alertining manbai.

    ⚠ KOMPONENT NOMI MODUL KONSTANTASIDAN import qilinadi, qo'lda yozilgan
      literaldan emas: nom o'zgarsa test bilan mahsulot BIRGA o'zgaradi va
      yozuvchi bilan o'quvchi jimgina ajralib keta olmaydi.
    """
    before = datetime.now(tz=MARKET_TZ)
    await bed.write_frame()

    await _run(api_sessionmaker, s3_client, bed)

    row = bed.conn.execute(_HEARTBEAT, (RETENTION_COMPONENT,)).fetchone()
    assert row is not None, "yurak urishi YOZILMADI"
    assert row[0] >= before
    assert row[1]["compressed"] >= 1


async def test_a_broken_object_does_not_stop_the_other_frames(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """Bitta kadrning xatosi qolganlarini TO'XTATMAYDI.

    Job yiqilsa BUTUN o'rnatmaning saqlash siyosati to'xtardi va nosozlik
    faqat disk to'lganda ko'rinardi.
    """
    broken = await bed.write_frame(slot=time(6, 0), data=b"\xff\xd8\xff-dekodlanmaydi")
    healthy = await bed.write_frame(slot=time(7, 30))

    result = await _run(api_sessionmaker, s3_client, bed)

    assert result.compressed == 1, "sog'lom kadr siqilmadi"
    assert result.errors, "xato yutildi, lekin SANOQQA tushmadi"
    assert bed.state(healthy)["storage_tier"] == SnapshotTier.COMPRESSED.value
    assert bed.state(broken)["storage_tier"] == SnapshotTier.FULL.value


async def test_the_default_today_comes_from_the_business_calendar(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """`today` berilmasa `business_today()` ishlatiladi — stdlib sanasi EMAS.

    ⚠ Farq AYNAN 00:00-04:59 (Toshkent) oynasida ko'rinadi va retention
      03:20 da ishlaydi, ya'ni u o'sha oynaning ICHIDA. Kecha bilan
      adashish siyosatni bir kunga siljitardi.

    O'lchov: kechagi kadr standart `today` bilan siqiladi (u
    `business_today()` dan QAT'IY oldin), bugungisi esa TEGILMAYDI.
    """
    yesterday = await bed.write_frame(days_ago=1)
    todays = await bed.write_frame(days_ago=0, slot=time(12, 0))

    result = await retention_daily(api_sessionmaker, s3_client, policy=COMPRESS_ONLY)

    assert result.compressed == 1
    assert bed.state(yesterday)["storage_tier"] == SnapshotTier.COMPRESSED.value
    assert bed.state(todays)["storage_tier"] == SnapshotTier.FULL.value


async def test_the_job_reports_zero_instead_of_crashing_on_an_empty_market(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """NOL — NATIJA, uning yo'qligi emas.

    «Bugun hech nima siqilmadi» bilan «siqish umuman ishlamadi» bir xil
    ko'rinmasligi kerak: birinchisida `errors` bo'sh, ikkinchisida yo'q.
    """
    result = await _run(api_sessionmaker, s3_client, bed)

    assert result.markets >= 2, "faol bozorlar ro'yxati bo'sh chiqdi"
    assert (result.compressed, result.purged, result.orphans_deleted) == (0, 0, 0)
    assert result.errors == []


async def test_the_row_count_never_shrinks(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    s3_client: SnapshotStorage,
    bed: _Bed,
) -> None:
    """⛔ Butun siyosat bo'ylab `snapshots` qatorlari soni O'ZGARMAYDI.

    Yuqoridagi testlar bitta qatorni kuzatadi; bu esa AGREGAT da'vo va u
    «boshqa qator o'chib ketdi» sinfini yopadi (masalan noto'g'ri predikat
    bilan yozilgan tozalash).
    """
    await bed.write_frame(slot=time(6, 0))
    await bed.write_frame(slot=time(6, 30), tier=SnapshotTier.COMPRESSED.value)
    await bed.write_frame(slot=time(7, 0), days_ago=3)
    before = bed.snapshot_count()

    await _run(api_sessionmaker, s3_client, bed, policy=PURGE_TOO)
    await _run(api_sessionmaker, s3_client, bed, policy=PURGE_TOO)

    assert before == 3
    assert bed.snapshot_count() == 3
    assert await s3_client.list_prefix(f"{bed.market_id}/") == []


def test_disk_usage_is_measured_not_assumed() -> None:
    """`disk_pressure` alertining manbai — HAQIQIY `statvfs`, konstanta emas."""
    used = disk_usage_percent("/")

    assert 0.0 < used < 100.0, f"disk o'lchovi ishonchsiz: {used}"
