"""Uchidan-uchiga kadr oqimi — SIM ustida, MOCK'SIZ (CAM-06/CAM-07, D-16).

=============================================================================
BU FAYL BUTUN ZANJIRNI BITTA CHAQIRUVDA O'LCHAYDI.

    bazadagi qator  ->  ISAPI `/picture`  ->  magic-bayt darvozasi
    ->  `quality.analyze()`  ->  S3 `PUT`  ->  `snapshots` + `capture_runs`

Oradagi HECH NIMA taqlid qilinmaydi: NVR — haqiqiy `nvr-sim` konteyneri
(Digest auth bilan), ombor — haqiqiy SeaweedFS, baza — haqiqiy Postgres.
03-14 ning metodikasi: mock'langan qatlam «kod gaplasha oladi» da'vosini
UMUMAN sinamaydi va u yashil bo'lib turaveradi.

⚠ USUL — `isapi`, `go2rtc` EMAS. Sabab D-07 va u shu testning MEXANIKASI:
  ISAPI `/picture` javob BAYTLARINI `SimState.frame_mode` dan oladi
  (04-02), ya'ni buzuq/kesilgan/HTML javoblarni BUYURTMA bilan berish
  mumkin. MediaMTX orqali keladigan go2rtc oqimi bu to'rt shaklni BERA
  OLMAYDI — u har doim yaroqli kadr qaytaradi.
=============================================================================

=============================================================================
SIFAT CHEGARASI TESTDA PASAYTIRILGAN — VA SABAB O'LCHANGAN.

Yetkazilgan `QUALITY_MIN_BYTES` = 4 096 va u REAL kadr uchun to'g'ri:
1280x720 dagi eng qorong'i kadr ham 29 607 bayt (04-04 ning o'lchovi).
Simulyatorning kadri esa 320x180 — 2 927 bayt, ya'ni u yetkazilgan pol
ostida qoladi va `analyze()` uni HAJM bo'yicha `corrupt` deb yopardi.

Shuning uchun bu faylda `min_bytes = 1024`: shunda test SIFAT
QOIDASINI o'lchaydi, o'lcham polini emas. Pol o'zining ALOHIDA testiga ega
(`tests/unit/test_quality_filter.py`) va u yetkazilgan standart bilan
ishlaydi.
=============================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import psycopg
import pytest
from app.jobs.capture import CapturePolicy, capture_batch
from app.repositories.nvr_repo import NvrRepository
from app.security.secrets import encrypt_nvr_password
from app.services.frame_source import FrameSourcePool
from app.services.object_key import object_key
from app.services.quality import QualityThresholds
from fixtures.nvr_domain import nvr_rows
from fixtures.nvr_sim import sim_patch
from fixtures.snapshot_domain import snapshot_rows
from sbozor_core.enums import ActorKind, CaptureMethod, CaptureRunStatus, SnapshotQuality
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import MARKET_TZ
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from datetime import date, time
    from uuid import UUID

    from app.services.storage import SnapshotStorage
    from fixtures import TenantSessionFactory
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

GRACE = 600
LEASE = 120

POLICY = CapturePolicy(
    grace_seconds=GRACE,
    lease_seconds=LEASE,
    max_attempts=3,
    batch_size=50,
    global_concurrency=1,
    quality=QualityThresholds(
        # Modul docstringidagi «chegara pasaytirilgan» bandiga qarang.
        min_bytes=1024,
        max_bytes=8 * 1024 * 1024,
        blank_stddev=3.0,
        dark_mean=25.0,
        dark_stddev=12.0,
        ir_saturation=0.05,
        night_mean=110.0,
        version=1,
    ),
)

GO2RTC_URL = "http://go2rtc:1984"
"""Pul uni TALAB qiladi, lekin bu faylda U CHAQIRILMAYDI (usul — `isapi`)."""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, locked_until, locked_by, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, 'running', 1, %s, 'pytest', true)"
)

_CREATE_CHILD = """
CREATE TABLE probe_occupancy_real (
    id                   uuid PRIMARY KEY DEFAULT uuidv7(),
    snapshot_id          uuid NOT NULL,
    snapshot_is_billable boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_probe_occupancy_real_billable CHECK (snapshot_is_billable),
    CONSTRAINT fk_probe_occupancy_real_snapshot
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
        REFERENCES snapshots (id, is_billable)
)
"""
_DROP_CHILD = "DROP TABLE IF EXISTS probe_occupancy_real"
_INSERT_CHILD = "INSERT INTO probe_occupancy_real (snapshot_id) VALUES (%s)"


class _Case:
    """Bitta e2e o'lchov uchun kerak bo'lgan hamma narsa."""

    __slots__ = ("camera_id", "channel_no", "market_id", "nvr_id", "run_id", "slot_time", "today")

    def __init__(
        self,
        *,
        market_id: UUID,
        nvr_id: UUID,
        camera_id: UUID,
        channel_no: int,
        run_id: UUID,
        slot_time: time,
        today: date,
    ) -> None:
        self.market_id = market_id
        self.nvr_id = nvr_id
        self.camera_id = camera_id
        self.channel_no = channel_no
        self.run_id = run_id
        self.slot_time = slot_time
        self.today = today

    @property
    def key(self) -> str:
        return object_key(
            market_id=self.market_id,
            business_date=self.today,
            camera_id=self.camera_id,
            slot_time=self.slot_time,
        )


def _split(url: str) -> tuple[str, int]:
    remainder = url.split("://", 1)[-1]
    host, _, port = remainder.partition(":")
    return host, int(port or 80)


@pytest.fixture
async def e2e(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
    sim: str,
    sim_credentials: tuple[str, str],
    s3_client: SnapshotStorage,
) -> AsyncIterator[_Case]:
    """Sim'ga qaratilgan NVR + `running` qator + ombor tozalash.

    ⚠ QURILMA `capture_method = 'isapi'` GA O'TKAZILADI. Bu MA'LUMOT
      o'zgarishi, kod o'zgarishi emas (D-06) — va aynan shu SC#7 ning
      («real qurilmaga o'tish — sozlama o'zgarishi») bevosita o'lchovi.

    ⚠ SEED'NING PAROLI FERNET EMAS (`NVR_PASSWORD_PLACEHOLDER`) — u faqat
      ustunning mavjudligini sinaydi. Bu yerda HAQIQIY shifrlangan parol
      yoziladi, chunki job uni haqiqatan deshifrlaydi.
    """
    host, port = _split(sim)
    username, password = sim_credentials

    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as _snap,
    ):
        rows = nvr.market_a
        camera_id = rows.active_camera_ids[0]
        channel_no = sync_owner_conn.execute(
            "SELECT channel_no FROM cameras WHERE id = %s", (str(camera_id),)
        ).fetchone()
        assert channel_no is not None
        sync_owner_conn.execute(
            "UPDATE nvr_devices SET capture_method = %s WHERE id = %s",
            (CaptureMethod.ISAPI.value, str(rows.nvr_id)),
        )

        async with api_sessionmaker() as session, session.begin():
            await set_tenant_context(
                session,
                market_id=rows.market_id,
                actor_id=None,
                request_id="pytest",
                actor_kind=ActorKind.SYSTEM,
            )
            repo = NvrRepository(session, rows.market_id)
            await repo.update_device(rows.nvr_id, host=host, port=port, username=username)
            await repo.put_credential(rows.nvr_id, encrypt_nvr_password(password), 1)

        slot_time = DEFAULT_SNAPSHOT_SLOTS[0]
        run_id = uuid4()
        sync_owner_conn.execute(
            _INSERT_RUN,
            (
                str(run_id),
                str(rows.market_id),
                str(camera_id),
                str(rows.nvr_id),
                slot_time,
                datetime.now(tz=MARKET_TZ) - timedelta(seconds=30),
                datetime.now(tz=MARKET_TZ) + timedelta(seconds=LEASE),
            ),
        )

        case = _Case(
            market_id=rows.market_id,
            nvr_id=rows.nvr_id,
            camera_id=camera_id,
            channel_no=int(channel_no[0]),
            run_id=run_id,
            slot_time=slot_time,
            today=market_today,
        )
        try:
            yield case
        finally:
            # Ombor tozalash: seed bozori `s3_markets` fixture'idan
            # KELMAYDI, ya'ni prefiksni bu yerda supurish SHART — 455
            # kunlik saqlash siyosati bo'lgan omborda qoldiq jimgina
            # to'planadigan qarz.
            keys = await s3_client.list_prefix(f"{case.market_id}/")
            if keys:
                await s3_client.delete_many(keys)


@contextmanager
def _billable_child(conn: Connection[TupleRow]) -> Iterator[None]:
    """HAQIQIY `snapshots` ga qaratilgan `occupancy` uslubidagi bola-jadval.

    ⚠ ZOND JADVALI EMAS — 04-01 ning `billable_probe.py` si `probe_snapshots`
      ni O'ZI yaratardi va SXEMA imkoniyatini (D-23) o'lchardi. Bu yerda
      savol boshqa: MAHSULOTDAGI `snapshots` jadvali D-16 ning langarini
      HAQIQATAN ko'tarmoqdami. Ikkinchi savolga faqat haqiqiy jadval
      javob beradi.
    """
    conn.execute(_DROP_CHILD)
    conn.execute(_CREATE_CHILD)
    try:
        yield
    finally:
        conn.execute(_DROP_CHILD)


async def _run_batch(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: SnapshotStorage,
    case: _Case,
) -> Any:
    pool = FrameSourcePool(go2rtc_url=GO2RTC_URL)
    try:
        return await capture_batch(
            sessionmaker,
            storage,
            pool,
            policy=POLICY,
            market_id=case.market_id,
            nvr_id=case.nvr_id,
            run_ids=[case.run_id],
        )
    finally:
        await pool.aclose()


async def _run_row(tenant_session: TenantSessionFactory, case: _Case) -> Any:
    async with tenant_session(case.market_id) as session:
        result = await session.execute(
            text(
                "SELECT status, error_code, capture_method, snapshot_id "
                "  FROM capture_runs WHERE market_id = :market_id AND id = :run_id"
            ),
            {"market_id": case.market_id, "run_id": case.run_id},
        )
        return result.one()._mapping


async def _snapshot_rows(tenant_session: TenantSessionFactory, case: _Case) -> list[Any]:
    async with tenant_session(case.market_id) as session:
        result = await session.execute(
            text(
                "SELECT id, quality_verdict, is_billable, quality_mean, quality_stddev, "
                "       size_bytes, object_key, capture_method "
                "  FROM snapshots WHERE market_id = :market_id AND capture_run_id = :run_id"
            ),
            {"market_id": case.market_id, "run_id": case.run_id},
        )
        return [row._mapping for row in result]


# ---------------------------------------------------------------------------
# 1. `frame_mode="ok"` — to'liq oqim
# ---------------------------------------------------------------------------


async def test_a_good_frame_walks_the_whole_chain(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    s3_client: SnapshotStorage,
    e2e: _Case,
) -> None:
    """CAM-07 ning uchidan-uchiga isboti: qator + OMBORDAGI OBYEKT.

    ⚠ UCHTA MUSTAQIL DA'VO VA UCHALASI HAM KERAK:
      1. `capture_runs.status = 'succeeded'` — orkestratsiya yakunlandi;
      2. `snapshots` qatori bor va u `is_billable` — sifat filtri o'tdi;
      3. OBYEKT OMBORDA MAVJUD (`head()` `None` emas) — §B.4 ning
         tartibi HAQIQATAN bajarildi.

    Uchinchisi ikkinchisidan MUSTAQIL: baza qatori obyekt borligini
    TASDIQLAYDI degan da'vo faqat omborga borib tekshirilganda isbotlanadi.
    """
    result = await _run_batch(api_sessionmaker, s3_client, e2e)
    assert result.succeeded == 1, result

    run = await _run_row(tenant_session, e2e)
    assert run["status"] == CaptureRunStatus.SUCCEEDED.value, run
    assert run["error_code"] is None
    assert run["capture_method"] == CaptureMethod.ISAPI.value, (
        "DALIL sozlamadan olinmadi — `capture_method` qaysi yo'l HAQIQATAN "
        "ishlaganini yozishi kerak"
    )

    snapshots = await _snapshot_rows(tenant_session, e2e)
    assert len(snapshots) == 1, snapshots
    snapshot = snapshots[0]
    assert snapshot["quality_verdict"] == SnapshotQuality.OK.value, snapshot
    assert snapshot["is_billable"] is True
    assert snapshot["object_key"] == e2e.key
    assert run["snapshot_id"] == snapshot["id"]

    stored = await s3_client.head(e2e.key)
    assert stored is not None, (
        "baza qatori bor, OBYEKT esa omborda YO'Q — §B.4 ning tartibi buzilgan "
        "va 6-faza mavjud bo'lmagan dalilga havola qilardi"
    )
    assert stored.size_bytes == snapshot["size_bytes"]


# ---------------------------------------------------------------------------
# 2. `frame_mode="truncated"` — CAM-06 ning yuragi
# ---------------------------------------------------------------------------


async def test_a_truncated_frame_is_stored_but_never_billable(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    s3_client: SnapshotStorage,
    sim: str,
    e2e: _Case,
) -> None:
    """CAM-06: sifat tekshiruvidan o'tmagan kadr SAQLANADI, lekin `is_billable=false`.

    =======================================================================
    BU YERDA 04-05 OCHIQ QOLDIRGAN ZIDDIYAT YOPILADI (qarorning egasi shu
    reja, migratsiya `0016`).

    Kesilgan JPEG magic-baytdan O'TADI (u haqiqiy JPEG ning boshi), ya'ni
    `frame_source` uni rad etmaydi — va bu TO'G'RI: javob KADR, faqat
    yaroqsiz. `quality.analyze()` esa uni `corrupt` deb belgilaydi va
    o'lchovlarni `None` qaytaradi.

    Ya'ni bu qator `succeeded` + `corrupt` — `04-UI-SPEC.md` §6.4 ning C4
    hujayrasi. Uni yozib bo'lmasligi `04-05` ni to'xtatgan edi; `0016`
    o'lchov ustunlarini NULLABLE qildi va hujayra endi CHIZILADI.
    =======================================================================
    """
    sim_patch(sim, frame_mode="truncated")

    result = await _run_batch(api_sessionmaker, s3_client, e2e)
    assert result.succeeded == 1, result

    run = await _run_row(tenant_session, e2e)
    assert run["status"] == CaptureRunStatus.SUCCEEDED.value, run

    snapshots = await _snapshot_rows(tenant_session, e2e)
    assert len(snapshots) == 1, "buzuq kadr yozilmadi — C4 hujayrasi hech qachon chizilmasdi"
    snapshot = snapshots[0]
    assert snapshot["quality_verdict"] == SnapshotQuality.CORRUPT.value, snapshot
    assert snapshot["is_billable"] is False, (
        "yaroqsiz kadr `is_billable` bo'lib qoldi — D-16 ning generated ustuni buzilgan"
    )
    assert snapshot["quality_mean"] is None and snapshot["quality_stddev"] is None, (
        "buzuq kadr uchun SOXTA NOL yozildi — u bazada «o'lchandi va nol chiqdi» "
        "ma'nosini beradi va D-15 ning `percentile_cont` yo'lini buzadi"
    )
    assert await s3_client.head(e2e.key) is not None, "yaroqsiz kadr ham SAQLANADI (CAM-06)"


# ---------------------------------------------------------------------------
# 3. `frame_mode="html"` — javob UMUMAN kadr emas
# ---------------------------------------------------------------------------


async def test_an_html_response_never_becomes_a_snapshot_row(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    s3_client: SnapshotStorage,
    sim: str,
    e2e: _Case,
) -> None:
    """`capture_invalid_response` — va `snapshots` qatori UMUMAN yozilmaydi.

    ⚠ IKKINCHI QATLAM BILAN FARQ: kesilgan kadr (yuqoridagi test) `corrupt`
      QATOR beradi, HTML sahifa esa qator UMUMAN bermaydi. Ikkalasi ham
      yaroqsiz, lekin ular BOSHQA nosozliklar: birinchisida NVR kadr
      yubordi (tarmoq uzildi), ikkinchisida esa NVR umuman kadr
      YUBORMADI (oqim sozlamasi yoki firmware).

      Aynan shu farq `capture_invalid_response` kodini MA'NOLI qiladi:
      admin birinchi holatda tunnelni, ikkinchisida esa NVR sozlamasini
      tekshiradi.
    """
    sim_patch(sim, frame_mode="html")

    result = await _run_batch(api_sessionmaker, s3_client, e2e)
    assert result.succeeded == 0, result

    run = await _run_row(tenant_session, e2e)
    assert run["error_code"] == "capture_invalid_response", run
    assert await _snapshot_rows(tenant_session, e2e) == [], (
        "javobda tasvir yo'q edi, lekin `snapshots` qatori yozildi"
    )
    assert await s3_client.head(e2e.key) is None, (
        "kadr bo'lmagan javob omborga yuklandi — magic-bayt darvozasi S3 dan OLDIN turishi kerak"
    )


# ---------------------------------------------------------------------------
# 4. D-16 — DB KAFOLATI, konventsiya emas
# ---------------------------------------------------------------------------


async def test_non_billable_cannot_be_referenced(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    s3_client: SnapshotStorage,
    sim: str,
    e2e: _Case,
) -> None:
    """⛔ YAROQSIZ KADR BANDLIK DALILINI UMUMAN YARATA OLMAYDI (D-16, CAM-06).

    =======================================================================
    BU KONVENTSIYA EMAS, DB KAFOLATI — VA U MAHSULOTDAGI `snapshots`
    JADVALIDA O'LCHANADI.

    `04-01` ning zondi (`billable_probe.py`) SXEMA imkoniyatini o'lchagan
    edi: `GENERATED STORED` ustun kompozit FK ning nishoni bo'la oladimi.
    Bu yerdagi savol boshqa va u KUCHLIROQ: `snapshots` jadvalining O'ZI
    o'sha langarni (`uq_snapshots_billable_anchor`) ko'tarmoqdami.

    5-fazadagi `occupancy_events` aynan shu shaklda quriladi, ya'ni bu
    test uning oldindan olingan o'lchovi. Faqat CHECK yoki faqat FK
    yetarli emas: FK yolg'iz o'zi `(id, false)` juftligiga havolani ham
    QABUL QILARDI (u ham mavjud juftlik), CHECK esa `false` ni butunlay
    taqiqlaydi.
    =======================================================================
    """
    sim_patch(sim, frame_mode="truncated")
    await _run_batch(api_sessionmaker, s3_client, e2e)

    snapshots = await _snapshot_rows(tenant_session, e2e)
    assert len(snapshots) == 1
    corrupt_id = snapshots[0]["id"]
    assert snapshots[0]["is_billable"] is False

    with _billable_child(sync_owner_conn):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            sync_owner_conn.execute(_INSERT_CHILD, (str(corrupt_id),))
        # ⚠ NAZORAT HOLATI MAJBURIY: FK butunlay buzilgan bo'lsa (masalan
        #   noto'g'ri jadvalga qaratilgan bo'lsa) yuqoridagi assert HAM
        #   qizarardi, lekin sabab boshqa bo'lardi. Yaroqli kadrga havola
        #   O'TISHI kerak.
        sync_owner_conn.execute("ROLLBACK")
        sim_patch(sim, frame_mode="ok")
        second = _Case(
            market_id=e2e.market_id,
            nvr_id=e2e.nvr_id,
            camera_id=e2e.camera_id,
            channel_no=e2e.channel_no,
            run_id=uuid4(),
            slot_time=DEFAULT_SNAPSHOT_SLOTS[1],
            today=e2e.today,
        )
        sync_owner_conn.execute(
            _INSERT_RUN,
            (
                str(second.run_id),
                str(second.market_id),
                str(second.camera_id),
                str(second.nvr_id),
                second.slot_time,
                datetime.now(tz=MARKET_TZ) - timedelta(seconds=30),
                datetime.now(tz=MARKET_TZ) + timedelta(seconds=LEASE),
            ),
        )
        await _run_batch(api_sessionmaker, s3_client, second)
        billable = await _snapshot_rows(tenant_session, second)
        assert len(billable) == 1 and billable[0]["is_billable"] is True, billable
        sync_owner_conn.execute(_INSERT_CHILD, (str(billable[0]["id"]),))
