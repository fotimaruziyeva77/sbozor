"""`capture_tick` — reja, ijara, yo'qlik va fan-out (D-02/D-03/D-04, CAM-05).

=============================================================================
BU FAYL WORKER KONTEYNERINI KUTMAYDI — JOBNI FUNKSIYA SIFATIDA CHAQIRADI.

`capture_tick` — sof `async def` (S-4), ya'ni uni chaqirish uchun na
broker, na planer jarayoni kerak. Bu D-06/S-4 ning BUTUN MAQSADI va
`test_nvr_discovery_job.py` da o'rnatilgan qoida: navbatning tarmoq
qismi testdan chiqadi, o'lchanadigan narsa esa ORKESTRATSIYA MANTIG'I
bo'lib qoladi.

Planerning O'ZI (bitta daqiqalik cron, `Settings` siz import) shu faylning
oxirgi bo'limida — matn va tip darvozalari bilan.
=============================================================================

=============================================================================
SANALAR «BUGUN» DAN HISOBLANADI, QOTIRILMAYDI (`test_capture_repo.py` ning
qoidasi va bir xil sabab).

`SEED_BUSINESS_DATE` (2026-09-01) seed uchun QADALGAN, lekin u «kelajak»
ham, «o'tmish» ham bo'lishi mumkin. `ensure_plan()` ning `pending` va
`skipped` shoxlari AYNAN shu farqqa qaraydi, ya'ni qotirilgan sana bilan
yozilgan test loyihaning O'Z muddati ichida jimgina teskarisiga aylanardi.

Shuning uchun profil davri `_cover_from()` bilan kengaytiriladi va
da'volar `market_today` dan hisoblanadi.
=============================================================================
"""

from __future__ import annotations

import inspect
import pathlib
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from app.jobs import capture as capture_job
from app.jobs.capture import CAPTURE_TICK_COMPONENT, BatchRequest, CapturePolicy, capture_tick
from app.services.quality import QualityThresholds
from fixtures.nvr_domain import nvr_rows
from fixtures.snapshot_domain import snapshot_rows
from sbozor_core.enums import CaptureRunStatus
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import MARKET_TZ
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager
    from datetime import date, time
    from uuid import UUID

    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKER_PATH = REPO_ROOT / "services" / "core-api" / "app" / "worker.py"

GRACE = 600
LEASE = 120
MAX_ATTEMPTS = 3

POLICY = CapturePolicy(
    grace_seconds=GRACE,
    lease_seconds=LEASE,
    max_attempts=MAX_ATTEMPTS,
    batch_size=50,
    global_concurrency=1,
    quality=QualityThresholds(
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
"""Sinovlardagi siyosat — qiymatlar `Settings` dan KO'CHIRILGAN, import EMAS.

`Settings()` `tests` konteynerida `DATABASE_URL`/`JWT_SECRET` siz umuman
qurilmaydi (04-04 da o'lchangan). Nusxa xavfsiz, chunki jobda bu sonlar
YO'Q — u hammasini `CapturePolicy` dan oladi va tarjima `worker.py` da.
"""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, locked_until, locked_by, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)"
)
_WIDEN_SCHEDULE = "UPDATE snapshot_schedules SET period = daterange(%s, NULL, '[)') WHERE id = %s"


@dataclass(frozen=True)
class _Fixture:
    """Bitta testga kerak bo'lgan hamma narsa (`test_capture_repo.py` naqshi)."""

    market_id: UUID
    nvr_id: UUID
    camera_ids: tuple[UUID, ...]
    schedule_id: UUID
    today: date

    @property
    def planned_rows(self) -> int:
        """To'liq kunlik rejaning kutilgan hajmi — FAOL kamera x slot."""
        return len(self.camera_ids) * len(DEFAULT_SNAPSHOT_SLOTS)


def _cover_from(conn: Connection[TupleRow], schedule_id: UUID, start: date) -> None:
    """Seed profilining davrini `[start, ∞)` ga kengaytiradi."""
    conn.execute(_WIDEN_SCHEDULE, (start, str(schedule_id)))


def _shift(seconds: int) -> datetime:
    """`now()` dan `seconds` siljigan bozor mintaqasidagi `timestamptz`.

    Naive `datetime` TAQIQLANGAN: konteyner UTC'da ishlaydi va mahalliy
    00:00–04:59 oralig'idagi qiymat naive sanada OLDINGI kunga tushardi.
    """
    return datetime.now(tz=MARKET_TZ) + timedelta(seconds=seconds)


def _insert_run(
    conn: Connection[TupleRow],
    fixture: _Fixture,
    *,
    camera_id: UUID,
    slot_time: time,
    offset_seconds: int,
    status: str = CaptureRunStatus.PENDING.value,
    attempts: int = 0,
    lease_offset_seconds: int | None = None,
    locked_by: str | None = None,
) -> UUID:
    """«Hozir» ga NISBATAN joylashgan bitta `capture_runs` qatorini yozadi.

    Sobit `datetime` yozib bo'lmaydi: tikning uchala predikati ham
    (`<= now()`, `> now() - grace`, `locked_until`) HOZIRGA nisbatan
    ishlaydi.
    """
    run_id = uuid4()
    conn.execute(
        _INSERT_RUN,
        (
            str(run_id),
            str(fixture.market_id),
            str(camera_id),
            str(fixture.nvr_id),
            slot_time,
            _shift(offset_seconds),
            status,
            attempts,
            None if lease_offset_seconds is None else _shift(lease_offset_seconds),
            locked_by,
        ),
    )
    return run_id


def _build(nvr: NvrDomainSeed, snap: SnapshotDomainSeed, today: date) -> _Fixture:
    rows = nvr.market_a
    return _Fixture(
        market_id=rows.market_id,
        nvr_id=rows.nvr_id,
        camera_ids=rows.active_camera_ids,
        schedule_id=snap.market_a.schedule_id,
        today=today,
    )


@pytest.fixture
def capture_fixture(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> Callable[[], AbstractContextManager[_Fixture]]:
    """`nvr_rows` + `snapshot_rows` ni bitta `with` blokiga yig'adi.

    Tartib MUHIM: `snapshot_rows` ning tozalash bloki `nvr_rows` NING
    ICHIDA turishi shart, aks holda `cameras` hali `capture_runs` tayanib
    turganda o'chirilardi.
    """

    @contextmanager
    def _open() -> Iterator[_Fixture]:
        with (
            nvr_rows(sync_owner_conn, two_markets) as nvr,
            snapshot_rows(sync_owner_conn, nvr) as snap,
        ):
            fixture = _build(nvr, snap, market_today)
            _cover_from(sync_owner_conn, fixture.schedule_id, market_today - timedelta(days=30))
            yield fixture

    return _open


async def _rows_for_day(
    tenant_session: TenantSessionFactory, market_id: UUID, day: date
) -> list[dict[str, Any]]:
    """`capture_runs` ning XOM ustun qiymatlari — ORM keshidan MUSTAQIL.

    Bir sessiyada o'qilgan ORM obyekti identity-map dan qaytishi mumkin va
    «holat o'zgardi» da'vosi bazani emas, KESHNI o'lchagan bo'lardi.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT id, camera_id, slot_time, status, attempts, locked_until, locked_by "
                "  FROM capture_runs "
                " WHERE market_id = :market_id AND business_date = :day"
            ),
            {"market_id": market_id, "day": day},
        )
        return [dict(row._mapping) for row in result]


async def _row(tenant_session: TenantSessionFactory, market_id: UUID, run_id: UUID) -> Any:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT status, attempts, locked_until, locked_by, error_code "
                "  FROM capture_runs WHERE market_id = :market_id AND id = :run_id"
            ),
            {"market_id": market_id, "run_id": run_id},
        )
        return result.one()._mapping


def _recorder() -> tuple[list[BatchRequest], Any]:
    """`enqueue` chaqiruvini YOZIB OLADIGAN, lekin navbatga tegmaydigan qobiq."""
    seen: list[BatchRequest] = []

    async def _record(batch: BatchRequest) -> None:
        seen.append(batch)

    return seen, _record


# ---------------------------------------------------------------------------
# Pitfall 9 — ENG JIM XATO SINFI
# ---------------------------------------------------------------------------


async def test_capture_tick_sets_tenant_context(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⛔ PITFALL 9 NING O'LCHOVI — `test_worker_sets_tenant_context` NING JUFTI.

    =======================================================================
    BU ENG JIM XATO SINFI VA U SHU YERDA ANIQ KO'RSATILADI.

    Tik HAMMA bozorlar ustida yuradi, `sbozor_app` esa tenant kontekstisiz
    BIRORTA bozorni ko'rmaydi. RLS ostida `INSERT ... SELECT` ning MANBASI
    bo'sh bo'ladi, ya'ni:

        * HECH QANDAY istisno ko'tarilmaydi,
        * `capture_runs` ga BIRORTA qator yozilmaydi,
        * jurnalda ham, javobda ham «xato» degan so'z YO'Q.

    Kashfiyot jobida bu «admin tugmani bosdi, hech nima bo'lmadi» bo'lib
    ko'rinardi. Tik esa hech kim bosmaydigan tugma: nosozlik faqat kun
    oxirida, hisobot bo'sh chiqqanda sezilardi.

    Kontekstni CHETLAB O'TISH usuli — `set_tenant_context` ni bo'sh
    funksiyaga almashtirish. Bu `capture_tick` ning O'Z chaqiruvini
    o'chiradi va boshqa hech nimaga tegmaydi.
    =======================================================================
    """
    with capture_fixture() as fx:
        before = await _rows_for_day(tenant_session, fx.market_id, fx.today)
        assert before == [], "seed bugungi kunga qator yozibdi — o'lchov ma'nosini yo'qotadi"

        async def _no_context(*_: Any, **__: Any) -> None:
            """Kontekst O'RNATILMAYDI — RLS fail-closed holatga tushadi."""

        monkeypatch.setattr(capture_job, "set_tenant_context", _no_context)
        blind = await capture_tick(api_sessionmaker, policy=POLICY)
        monkeypatch.undo()

        assert blind.created == 0, "kontekstsiz tik reja yozdi — RLS chetlab o'tilgan"
        assert await _rows_for_day(tenant_session, fx.market_id, fx.today) == [], (
            "kontekstsiz tik `capture_runs` ga qator qo'ydi"
        )

        # --- IKKINCHI YARIM: kontekst bilan AYNI tik rejani YOZADI ---
        seeing = await capture_tick(api_sessionmaker, policy=POLICY)
        assert seeing.created > 0, "kontekst bilan ham hech nima yozilmadi — o'lchov ma'nosiz"
        rows = await _rows_for_day(tenant_session, fx.market_id, fx.today)
        assert len(rows) == fx.planned_rows, (
            f"reja to'liq materializatsiya bo'lmadi: {len(rows)} != {fx.planned_rows}"
        )


# ---------------------------------------------------------------------------
# D-03 — taskiq'ning uchala nosozlik rejimi ZARARSIZ
# ---------------------------------------------------------------------------


async def test_duplicate_tick_is_noop(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
) -> None:
    """Ikki ketma-ket tik DUBLIKAT qator yaratmaydi (CAM-05, D-03).

    ⚠ QATOR SANOG'I BILAN o'lchanadi, `PlanResult` bilan EMAS: hisoblagich
      ilova qatlamida, dublikat esa BAZADA tug'ilardi. Ikkinchi tikning
      `created == 0` bo'lishi kerakli, LEKIN yetarli emas — u faqat
      `RETURNING` nima qaytarganini aytadi.

    Bu D-03 ning butun mazmuni: planer qayta ko'tarilib tikni takrorlasa,
    yoki ikkita planer jarayoni ishlasa — natija AYNI BIR XIL.
    """
    with capture_fixture() as fx:
        first = await capture_tick(api_sessionmaker, policy=POLICY)
        after_first = await _rows_for_day(tenant_session, fx.market_id, fx.today)

        second = await capture_tick(api_sessionmaker, policy=POLICY)
        after_second = await _rows_for_day(tenant_session, fx.market_id, fx.today)

        assert first.created == fx.planned_rows, first
        assert second.created == 0, "ikkinchi tik yangi qator yaratdi"
        assert len(after_second) == len(after_first) == fx.planned_rows
        assert {row["id"] for row in after_second} == {row["id"] for row in after_first}, (
            "ikkinchi tik qatorlarni ALMASHTIRDI — identitet saqlanmadi"
        )


async def test_expired_lease_returns_to_pending(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
) -> None:
    """Ijarasi tugagan `running` qator TIK ICHIDA qaytariladi (§B.5).

    ⚠ `SKIP LOCKED` BU HOLATNI QOPLAMAYDI: qulf `COMMIT` bilan tushgan,
      qator esa MANGU `running` bo'lib qolardi. Watchdog tikning BIRINCHI
      qadami bo'lgani uchun qator O'SHA tikda qayta olinadi — alohida job
      kutilmaydi.
    """
    with capture_fixture() as fx:
        stale = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=DEFAULT_SNAPSHOT_SLOTS[0],
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=-30,
            locked_by="o'lgan-worker",
        )

        result = await capture_tick(api_sessionmaker, policy=POLICY)

        assert result.released >= 1, "ijarasi tugagan qator umuman qaytarilmadi"
        row = await _row(tenant_session, fx.market_id, stale)
        assert row["status"] == CaptureRunStatus.RUNNING.value, row
        assert row["locked_by"] != "o'lgan-worker", (
            "qator qaytarildi, lekin QAYTA OLINMADI — tik bir daqiqa yo'qotgan bo'lardi"
        )
        assert stale in {run_id for batch in result.batches for run_id in batch.run_ids}


async def test_overdue_slot_is_missed_not_executed(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
) -> None:
    """⛔ KOMPENSATSIYA OYNASI CHEGARALANGAN — kechikkan kadr OLINMAYDI.

    06:00 sloti 07:05 da olingan kadr «06:00 da rasta band edimi?»
    savoliga JAVOB BERMAYDI. Kechikkan kadr — yo'q kadrdan YOMONROQ,
    chunki 6-faza uni dalil deb hisoblab noto'g'ri hisob chiqarardi.

    ⚠ IKKI DA'VO VA IKKALASI HAM MAJBURIY: qator `missed` bo'ldi VA u
      navbatga TUSHMADI. Faqat birinchisi tekshirilsa, bir vaqtda ham
      `missed` yozib, ham kadr oladigan kod yashil qolardi.
    """
    with capture_fixture() as fx:
        overdue = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=DEFAULT_SNAPSHOT_SLOTS[1],
            offset_seconds=-(GRACE + 120),
        )

        result = await capture_tick(api_sessionmaker, policy=POLICY)

        row = await _row(tenant_session, fx.market_id, overdue)
        assert row["status"] == CaptureRunStatus.MISSED.value, row
        assert row["error_code"] == "capture_slot_missed"
        assert overdue not in {run_id for batch in result.batches for run_id in batch.run_ids}, (
            "grace oynasidan chiqqan slot navbatga tushdi"
        )
        # D-20: yo'qlik HODISA qoldirmaydi, ya'ni uni faqat SHU ro'yxat
        # ko'rinadigan qiladi va `04-08` alertni aynan undan quradi.
        # `MissedSlot` da `run_id` YO'Q (u kamera + slot bilan nomlanadi),
        # shuning uchun da'vo o'sha juftlik bo'yicha qilinadi.
        assert (fx.camera_ids[0], DEFAULT_SNAPSHOT_SLOTS[1]) in {
            (slot.camera_id, slot.slot_time) for slot in result.missed
        }, "`missed` ro'yxatida o'tib ketgan slot yo'q — D-20 ning yagona manbai bo'sh"


# ---------------------------------------------------------------------------
# D-04 — fan-out NVR bo'yicha, tranzaksiyadan KEYIN
# ---------------------------------------------------------------------------


async def test_fan_out_groups_by_nvr_and_happens_after_the_transaction(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
) -> None:
    """Vazifa birligi — NVR + slot, kamera + slot EMAS (D-04).

    Konkurentlik chegarasi NVR ga tegishli, ya'ni semafor BITTA JARAYON
    ichida bo'lishi kerak. Kamera bo'yicha vazifa taqsimlangan qulf talab
    qilardi va u Valkey'da (davomiyliksiz kesh) yashamasdi.
    """
    with capture_fixture() as fx:
        due = [
            _insert_run(
                sync_owner_conn,
                fx,
                camera_id=camera_id,
                slot_time=DEFAULT_SNAPSHOT_SLOTS[2],
                offset_seconds=-30,
            )
            for camera_id in fx.camera_ids
        ]

        seen, record = _recorder()
        result = await capture_tick(api_sessionmaker, policy=POLICY, enqueue=record)

        mine = [batch for batch in seen if batch.market_id == fx.market_id]
        assert len(mine) == 1, f"kamera boshiga vazifa yaratildi: {len(mine)}"
        assert mine[0].nvr_id == fx.nvr_id
        assert set(due) <= set(mine[0].run_ids), "muddati kelgan qatorlar guruhga tushmadi"
        # `enqueue` chaqirilgan HAR BIR vazifa natijada ham qaytadi — ikki
        # yuza (navbat va `TickResult`) BIR XIL to'plamni ko'rsatishi shart,
        # aks holda `04-08` ning alerti navbatdan boshqa haqiqatni o'qirdi.
        assert set(seen) == set(result.batches)


async def test_the_tick_writes_its_heartbeat(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
) -> None:
    """FOUND-06 — `system_heartbeats['capture_tick']` HAR tikda yangilanadi.

    ⚠ D-20 ning eng pastki qatlami: worker VA planer ikkalasi ham o'lik
      bo'lsa hech kim hech nimani `missed` deb belgilamaydi va JIMLIK
      hukm suradi. `core-api` esa BOSHQA jarayon — u tirik qoladi va bu
      qatorning eskirganini ko'rsatadi.
    """
    with capture_fixture():
        async with api_sessionmaker() as session, session.begin():
            await session.execute(
                text("DELETE FROM system_heartbeats WHERE component = :component"),
                {"component": CAPTURE_TICK_COMPONENT},
            )

        await capture_tick(api_sessionmaker, policy=POLICY)

        async with api_sessionmaker() as session, session.begin():
            result = await session.execute(
                text(
                    "SELECT last_seen_at, detail FROM system_heartbeats "
                    " WHERE component = :component"
                ),
                {"component": CAPTURE_TICK_COMPONENT},
            )
            row = result.one()._mapping
        assert row["last_seen_at"] is not None
        assert row["detail"] is not None and "markets" in row["detail"]


async def test_a_heartbeat_failure_is_swallowed() -> None:
    """Yurak urishi — PROGRESS ko'rsatkichi, tikning NATIJASI emas.

    Uning yiqilishi butun kadr olishni to'xtatishi MUMKIN EMAS
    (`discovery.py::_publish_channels_found` bilan bir xil qaror va bir
    xil sabab): tik allaqachon rejani yozgan va kadrlarni navbatga
    qo'ygan bo'lardi, keyin esa monitoring yozuvi tufayli yiqilardi.

    ⚠ O'LCHOV MOCK'SIZ: `_write_heartbeat` YETIB BO'LMAYDIGAN bazaga
      qaratilgan sessiya fabrikasi bilan chaqiriladi va u ISTISNO
      KO'TARMASLIGI kerak. Funksiyani mock bilan almashtirish uning O'Z
      `except` blokini emas, mockning xulqini o'lchagan bo'lardi.
    """
    from sbozor_core.db import make_sessionmaker
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("postgresql+asyncpg://nobody@yurak.invalid:5432/none")
    try:
        broken = make_sessionmaker(engine)
        empty = capture_job.TickResult(
            markets=0, created=0, skipped=0, released=0, claimed=0, missed=(), batches=()
        )
        await capture_job._write_heartbeat(broken, empty)  # noqa: SLF001
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# PLANER — matn va tip darvozalari (S-5)
# ---------------------------------------------------------------------------


def test_the_scheduler_has_exactly_one_minute_cron() -> None:
    """⛔ AYNAN BITTA daqiqalik jadval (D-02).

    ⚠ REJANING MEZONI (`"cron": "* * * * *"` literalini SANASH) BAJARIB
      BO'LMAYDI, chunki o'sha rejaning O'Z `<action>` bandi cron satrini
      NOMLANGAN KONSTANTA qilishni talab qiladi (`TICK_CRON`). Ikkalasi
      bir vaqtda mumkin emas.

      Mezonning NIYATI («ikkinchi daqiqalik cron qo'shilsa darvoza
      qizarsin») KUCHLIROQ shaklda bajarildi: satr sanog'i BILAN BIRGA
      har bir jadvalning KIRISHI ham tekshiriladi — ya'ni BOSHQA literal
      bilan yozilgan ikkinchi daqiqalik jadval ham ushlanadi.

    =====================================================================
    ⚠⚠ DARVOZA `04-08` DA TORAYTIRILDI — SABAB BILAN.

    `04-07` bu yerda `len(re.findall(r"schedule=\\[", body)) == 1` deb
    yozgan edi va o'shanda u to'g'ri qiymat berardi: planerda bitta
    jadval bor edi. `04-08` esa REJA BO'YICHA yana uchtasini qo'shadi
    (`retention.daily` 03:20, `alert.sweep` har 5 daqiqa, `alert.digest`
    20:00), ya'ni eski shakl o'sha rejani BAJARIB BO'LMAYDIGAN qilardi.

    Darvozaning HAQIQIY da'vosi hech qachon «jadval bitta» bo'lmagan —
    u «DAQIQALIK cron oqimi bitta» edi (D-02/D-03: ikkinchi tik oqimi
    «bitta planer talab qilinmaydi» da'vosini shubha ostiga qo'yardi).
    Shuning uchun sanoq endi JADVAL KIRISHLARI bo'yicha yuradi va
    daqiqalik namunaga mos keladiganini AYNAN BITTA deb talab qiladi.

    Darvoza SUSAYMADI, kuchaydi: u endi `"*/1 * * * *"` va `"* * * * *"`
    ning har qanday bo'shliqli variantini ham ushlaydi, holbuki eski
    shakl faqat literalning aynan bir ko'rinishini sanardi.
    =====================================================================
    """
    body = WORKER_PATH.read_text(encoding="utf-8")
    assert len(re.findall(r'"\* \* \* \* \*"', body)) == 1, "daqiqalik cron satri bittadan ko'p"

    crons = re.findall(r'"cron"\s*:\s*([A-Za-z_][A-Za-z_0-9]*|"[^"]*")', body)
    assert crons, "planerda birorta jadval topilmadi"

    resolved = [
        _CRON_CONSTANTS[name] if name in _CRON_CONSTANTS else name.strip('"') for name in crons
    ]
    minute_crons = [value for value in resolved if _IS_MINUTE_CRON.fullmatch(value)]
    assert len(minute_crons) == 1, f"ikkinchi DAQIQALIK cron oqimi ochilgan: {resolved}"


_IS_MINUTE_CRON = re.compile(r"(\*|\*/1)(\s+\*){4}")
"""«Har daqiqada» ni bildiruvchi cron namunasi — literaldan KENGROQ."""


def _cron_constants() -> dict[str, str]:
    """`worker.py` dagi cron KONSTANTALARI — nom -> qiymat.

    Jadval dekoratorda konstantani ishlatadi (`schedule=[{"cron":
    TICK_CRON, ...}]`), ya'ni matn darvozasi qiymatni ko'rish uchun
    konstantani YECHISHI kerak. Yechish MAHSULOT modulidan olinadi, qo'lda
    takrorlanmaydi.
    """
    from app import worker

    return {
        name: value
        for name, value in vars(worker).items()
        if name.endswith("_CRON") and isinstance(value, str)
    }


_CRON_CONSTANTS = _cron_constants()


def test_the_scheduler_object_is_built_without_settings() -> None:
    """`taskiq scheduler app.worker:scheduler` IMPORT paytida muhit talab qilmaydi.

    ⚠ Agar `scheduler` (yoki `broker`) `get_settings()` dan o'qisa,
      `app.worker` ni IMPORT QILISHNING O'ZI to'liq muhitni talab qilardi —
      va `app/main.py` uni import qiladi, ya'ni butun test to'plami
      `NVR_CREDENTIAL_KEY` siz yiqilardi (`worker.py:26-41`).
    """
    from app import worker
    from taskiq import TaskiqScheduler

    assert isinstance(worker.scheduler, TaskiqScheduler)
    source = inspect.getsource(worker)
    module_level = [
        line
        for line in source.splitlines()
        if line.startswith(("scheduler", "broker")) and "get_settings" in line
    ]
    assert module_level == [], module_level


def test_the_capture_shells_carry_no_logic() -> None:
    """YUPQA QOBIQ — `str` -> `UUID` va `TaskiqState`, boshqa hech nima (S-4).

    Mantiq qobiqqa sizib kirsa, mexanizm almashtirilganda ko'chiriladigan
    qism kattalashardi — D-06 ning butun narxi aynan shu chegarada.
    """
    from app import worker

    for shell in (worker.capture_tick_task, worker.capture_batch_task):
        body = inspect.getsource(shell.original_func)
        for forbidden in ("ensure_plan", "claim_due", "storage.put", "analyze("):
            assert forbidden not in body, f"{shell.task_name}: qobiqda mantiq bor ({forbidden})"


def test_the_jobs_queue_is_a_single_queue() -> None:
    """Bitta navbat, to'rt turdagi vazifa (§3.10) va eski nom alias sifatida."""
    from app import worker

    assert worker.JOBS_QUEUE == "sbozor:jobs"
    assert worker.DISCOVERY_QUEUE == worker.JOBS_QUEUE
    assert worker.broker.queue_name == worker.JOBS_QUEUE  # type: ignore[attr-defined]
