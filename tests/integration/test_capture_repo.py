"""`CaptureRepository` — reja materializatsiyasi, ijara va `SKIP LOCKED`.

=============================================================================
BU FAYL 04-03 NING SXEMA TESTLARINING O'RNINI BOSMAYDI — ULARNING USTIGA
QURILADI.

`tests/tenancy/test_snapshot_domain_meta.py` (04-03) SXEMA darajasida
isbotlaydi: `UNIQUE (market_id, camera_id, business_date, slot_time)`
bazada MAVJUD va ustunlar tartibi to'g'ri. Bu yerdagi savol boshqa —
**ILOVA o'sha konstraytdan qanday foydalanadi**: ikkinchi `ensure_plan()`
HAQIQATAN nol qator qaytaradimi, `claim_due()` parallel tranzaksiyada bir
qatorni ikki marta beradimi, ijara tugagan qator qaytadimi.

04-03 ning yakuniy sabotaj o'lchovi aynan shu qarzni nomladi: CAM-05
idempotentligi o'sha paytda FAQAT model/baza drifti orqali qo'riqlanardi.
Bu fayl uning XULQ yarmini beradi — bir slot uchun ikkinchi qator
YOZILMAYDI va bu qator SANOG'I bilan o'lchanadi, sxema o'qish bilan emas.
=============================================================================

⛔ IKKI O'LCHOV BU FAYLNING SABABI VA ULARNI ARALASHTIRIB BO'LMAYDI:

  * **`SKIP LOCKED`** faqat TRANZAKSIYA DAVOMIDA himoya qiladi. Uni
    o'lchash uchun ikkinchi sessiya birinchisi COMMIT QILISHIDAN OLDIN
    chaqirilishi shart — aks holda test qulfni emas, oddiy `status`
    predikatini o'lchagan bo'lardi (birinchi tranzaksiya qatorlarni
    allaqachon `running` qilib qo'ygan bo'lardi).

  * **Ijara (lease)** butunlay boshqa muddatni qoplaydi: «worker o'rtada
    o'ldi». `SKIP LOCKED` bu holatda HECH NIMA qilmaydi — qulf `COMMIT`
    bilan tushgan, qator esa mangu `running` bo'lib qolardi.

Ikkalasi ALOHIDA testda va bittasini o'chirish ikkinchisini yashil
qoldiradi.

=============================================================================
SANALAR «BUGUN» DAN HISOBLANADI, QOTIRILMAYDI.

`fixtures.snapshot_domain.SEED_BUSINESS_DATE` (2026-09-01) seed uchun
QADALGAN va bu to'g'ri qaror — lekin u «kelajak» ham, «o'tmish» ham
bo'lishi mumkin: bugun u kelajak, 2026-09-01 dan keyin esa o'tmish.
`ensure_plan()` ning `pending` va `skipped` shoxlari AYNAN shu farqqa
qaraydi, ya'ni qotirilgan sana bilan yozilgan test loyihaning O'Z muddati
ichida (go-live 2026-10-18) jimgina teskarisiga aylanardi.

Shu sababdan bu faylda IKKI qoida:

  1. «Bugun» `market_today` fixture'idan (DB dan, `date.today()` dan EMAS)
     olinadi va profil davri `_cover_from()` bilan kengaytiriladi.
  2. `claim_due` / `mark_missed` testlari O'ZI YOZGAN qator `id` lari
     bo'yicha da'vo qiladi (tenglik emas, A'ZOLIK). Sabab: seed'ning
     `pending` qatori 2026-09-01 07:30 da va u KELAJAKDA — bugun u
     tanlanmaydi, o'sha kunning 10 daqiqalik oynasida esa tanlanardi.
     Tenglik da'vosi shu bir kunda flaky bo'lardi.
=============================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from app.repositories.capture_repo import CaptureRepository
from app.services.capture_errors import (
    CAPTURE_BAD_CREDENTIALS,
    CAPTURE_PLAN_CREATED_LATE,
    CAPTURE_SLOT_MISSED,
    CAPTURE_SOURCE_UNREACHABLE,
    CAPTURE_STREAM_LIMIT,
    CAPTURE_WORKER_LOST,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from sbozor_core.db import make_sessionmaker
from sbozor_core.enums import CaptureMethod, CaptureRunStatus, SnapshotQuality
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import MARKET_TZ
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator
    from contextlib import AbstractContextManager
    from typing import Any

    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")


GRACE = 600
"""Sinovlardagi grace oynasi — `Settings.capture_grace_seconds` bilan bir xil.

Qiymat KO'CHIRILGAN, import qilinmagan: `Settings()` `tests` konteynerida
`DATABASE_URL`/`JWT_SECRET` siz umuman qurilmaydi (04-04 da o'lchangan).
Nusxa xavfsiz, chunki repozitoriyda bu son YO'Q — har bir metod uni
ARGUMENT sifatida oladi va sozlamani chaqiruvchi (04-07) beradi.
"""

LEASE = 120
"""Ijara muddati — `Settings.capture_lease_seconds` bilan bir xil."""

MAX_ATTEMPTS = 3
"""Urinish byudjeti — `Settings.capture_max_attempts` bilan bir xil."""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, locked_until, locked_by, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)"
)

_WIDEN_SCHEDULE = "UPDATE snapshot_schedules SET period = daterange(%s, NULL, '[)') WHERE id = %s"


@dataclass(frozen=True)
class _Fixture:
    """Bitta testga kerak bo'lgan hamma narsa — bitta obyektda.

    Har testda beshta qiymatni (`market_id`, `nvr_id`, kameralar,
    `schedule_id`, «bugun») alohida ochib olish yigirma marta
    takrorlanardi va o'sha takror birinchi navbatda XATO joyda o'zgarardi.
    """

    market_id: UUID
    nvr_id: UUID
    camera_ids: tuple[UUID, ...]
    archived_camera_id: UUID
    schedule_id: UUID
    today: date

    @property
    def planned_rows(self) -> int:
        """To'liq kunlik rejaning kutilgan hajmi — FAOL kamera x slot.

        Sonlar seed'dan HISOBLANADI, qo'lda yozilmaydi: `nvr_domain` ning
        kanallar ro'yxati yoki `DEFAULT_SNAPSHOT_SLOTS` o'zgarsa kutilma
        ular bilan birga o'zgaradi (`active_camera_ids` bilan bir xil qoida).
        """
        return len(self.camera_ids) * len(DEFAULT_SNAPSHOT_SLOTS)


def _cover_from(conn: Connection[TupleRow], schedule_id: UUID, start: date) -> None:
    """Seed profilining davrini `[start, ∞)` ga kengaytiradi.

    ⚠ YANGI PROFIL YOZILMAYDI — mavjudi kengaytiriladi. Ikkinchi profil
      `ex_snapshot_schedules_no_overlap` ni ishga tushirardi (seed'niki
      ochiq oxirli), ya'ni test o'z TAYYORGARLIGIDA yiqilardi va sabab
      o'lchanayotgan da'voga umuman aloqador bo'lmasdi.
    """
    conn.execute(_WIDEN_SCHEDULE, (start, str(schedule_id)))


def _shift(seconds: int) -> datetime:
    """`now()` dan `seconds` siljigan bozor mintaqasidagi `timestamptz`.

    Naive `datetime` bu yerda TAQIQLANGAN (`snapshot_domain` bilan bir xil
    qoida): konteyner UTC'da ishlaydi va mahalliy 00:00–04:59 oralig'idagi
    qiymat naive sanada OLDINGI kunga tushardi.
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

    `offset_seconds` — `scheduled_at` ning `now()` dan siljishi (manfiy =
    o'tmish). Sobit `datetime` yozib bo'lmaydi: `claim_due()` ning uchala
    predikati ham (`<= now()`, `> now() - grace`, `locked_until`) HOZIRGA
    nisbatan ishlaydi.

    Qator EGA ulanishi bilan (autocommit) yoziladi, ya'ni u async
    sessiyalarga DARHOL ko'rinadi — `nvr_domain` seed'i bilan bir xil sabab.
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


async def _rows_by_id(
    tenant_session: TenantSessionFactory, market_id: UUID
) -> dict[UUID, dict[str, Any]]:
    """`capture_runs` ning XOM ustun qiymatlari, `id` bo'yicha.

    ⚠ ORM obyekti EMAS, xom SQL — `test_nvr_repo.py::_camera_rows` bilan
      aynan bir xil sabab: bir sessiyada o'qilgan obyekt identity-map dan
      qaytishi mumkin va «holat o'zgardi» da'vosi bazani emas, KESHNI
      o'lchagan bo'lardi.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT id, camera_id, slot_time, scheduled_at, business_date, status, "
                "       attempts, locked_until, locked_by, started_at, finished_at, "
                "       error_code, error_detail, capture_method, is_market_open, snapshot_id "
                "  FROM capture_runs WHERE market_id = :market_id"
            ),
            {"market_id": market_id},
        )
        return {row.id: dict(row._mapping) for row in result}


async def _count_runs(tenant_session: TenantSessionFactory, market_id: UUID, day: date) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM capture_runs "
                "WHERE market_id = :market_id AND business_date = :day"
            ),
            {"market_id": market_id, "day": day},
        )
        return int(result.scalar_one())


def _build(nvr: NvrDomainSeed, snap: SnapshotDomainSeed, today: date) -> _Fixture:
    rows = nvr.market_a
    assert rows.archived_camera_id is not None, "seed arxivlangan kamerani berishi shart"
    return _Fixture(
        market_id=rows.market_id,
        nvr_id=rows.nvr_id,
        camera_ids=rows.active_camera_ids,
        archived_camera_id=rows.archived_camera_id,
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

    ATAYIN kontekst menejeri QAYTARADI, tayyor obyekt emas: `snapshot_rows`
    ning tozalash bloki `nvr_rows` NING ICHIDA turishi SHART (uning o'z
    docstringi buni talab qiladi — teskari joylashuv `cameras` ni hali
    `capture_runs` tayanib turganda o'chirardi). `yield` fixture'i ikki
    qatlamni bu tartibda ushlab tura olmasdi.
    """

    @contextmanager
    def _open() -> Iterator[_Fixture]:
        with (
            nvr_rows(sync_owner_conn, two_markets) as nvr,
            snapshot_rows(sync_owner_conn, nvr) as snap,
        ):
            yield _build(nvr, snap, market_today)

    return _open


@pytest.fixture
async def duo_sessionmaker(
    app_url: str,
    _bootstrap_roles: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """IKKI ulanishli O'Z engine'i — parallel `claim_due` testi uchun.

    ⚠ `app_engine` BU YERDA ISHLAMAYDI: u `pool_size=1, max_overflow=0`
      bilan qurilgan (`tests/conftest.py:300`) va bu ATAYIN — GUC sizishini
      ochib berish uchun. Lekin `SKIP LOCKED` o'lchovi AYNAN IKKI OCHIQ
      tranzaksiyani talab qiladi: bitta ulanish bilan ikkinchi sessiya
      poolda kutib qolardi va test qulfni emas, pool chegarasini o'lchagan
      bo'lardi.

    Engine SHU FAYLDA quriladi, `conftest.py` ga qo'shilmaydi: o'sha fayl
    parallel to'lqinning umumiy infratuzilmasi.
    """
    engine = create_async_engine(app_url, pool_size=2, max_overflow=0)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# `ensure_plan` — CAM-05 ning materializatsiyasi
# ---------------------------------------------------------------------------


async def test_ensure_plan_writes_one_row_per_active_camera_and_slot(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Reja `kamera x slot` sonicha qator yozadi; ARXIVLANGAN kamera KIRMAYDI.

    Arxivlangan kanal `04-UI-SPEC.md` §6.4 bo'yicha jurnalda ko'rinmaydi VA
    uning `capture_runs` qatorlari umuman yaratilmaydi — D-10 ning
    soft-delete'i shu yerda ham amal qiladi. Predikatsiz reja arxivlangan
    kameraga har kuni 7 ta yo'qlik yozuvi yaratardi va ular `missed` bo'lib
    HAR KUNI alert berardi.
    """
    with capture_fixture() as fx:
        day = fx.today + timedelta(days=1)
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))
        before = await _count_runs(tenant_session, fx.market_id, day)

        async with tenant_session(fx.market_id) as session:
            result = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )

        assert before + result.created == fx.planned_rows
        assert result.skipped == 0

        rows = await _rows_by_id(tenant_session, fx.market_id)
        planned = [row for row in rows.values() if row["business_date"] == day]
        assert len(planned) == fx.planned_rows
        assert all(row["status"] == CaptureRunStatus.PENDING.value for row in planned)
        assert fx.archived_camera_id not in {row["camera_id"] for row in planned}
        assert {row["camera_id"] for row in planned} == set(fx.camera_ids)
        assert {row["slot_time"] for row in planned} == set(DEFAULT_SNAPSHOT_SLOTS)


async def test_second_ensure_plan_creates_nothing(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ CAM-05 NING XULQ YARMI: ikkinchi tik dublikat qator YARATMAYDI.

    04-03 ning sabotaj o'lchovi bu da'vo o'sha paytda FAQAT model/baza
    drifti orqali qo'riqlanayotganini ko'rsatdi. Bu yerda u qator SANOG'I
    bilan o'lchanadi: `ON CONFLICT DO NOTHING` olib tashlansa ikkinchi
    chaqiruv `IntegrityError` beradi, `DO UPDATE` ga almashtirilsa esa
    `created` noldan katta chiqadi.
    """
    with capture_fixture() as fx:
        day = fx.today + timedelta(days=1)
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))

        async with tenant_session(fx.market_id) as session:
            first = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )
        after_first = await _count_runs(tenant_session, fx.market_id, day)

        async with tenant_session(fx.market_id) as session:
            second = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )

        assert first.created > 0
        assert second.created == 0
        assert second.skipped == 0
        assert await _count_runs(tenant_session, fx.market_id, day) == after_first


async def test_ensure_plan_marks_already_past_slots_as_skipped(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ T-04-38: kech ulangan bozorning o'tib ketgan slotlari `skipped`.

    Ularni `pending` qilib yozish o'sha zahoti soxta `missed` alertlar
    berardi va platforma admini birinchi kunidayoq alertga ishonishni
    to'xtatardi. `skipped` esa `capture_plan_created_late` bilan keladi va
    u reyestrdagi YAGONA `actor="none"` kodi — «harakat talab qilinmaydi».

    ⚠ Bu shox FAQAT qator YARATILAYOTGAN paytda ishlaydi. Uzoq uzilishdan
      keyin qatorlar allaqachon bor va ular `mark_missed()` bilan `missed`
      bo'ladi — bu TO'G'RI natija va ikki holatni ajratadigan narsa aynan
      shu.
    """
    with capture_fixture() as fx:
        day = fx.today - timedelta(days=1)
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))
        before = await _count_runs(tenant_session, fx.market_id, day)

        async with tenant_session(fx.market_id) as session:
            result = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )

        assert before + result.created == fx.planned_rows
        assert result.created > 0
        assert result.skipped == result.created

        rows = await _rows_by_id(tenant_session, fx.market_id)
        past = [row for row in rows.values() if row["business_date"] == day]
        assert all(row["status"] == CaptureRunStatus.SKIPPED.value for row in past)
        assert all(row["error_code"] == CAPTURE_PLAN_CREATED_LATE for row in past)


async def test_ensure_plan_freezes_the_calendar_answer_for_the_day(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """D-10: `is_market_open` `market_is_open()` DAN keladi, qayta hisoblanmaydi.

    Kalendar mantig'i TAKRORLANMAYDI — 2-fazadagi funksiya qayta
    ishlatiladi. Bayroq qator yozilgan PAYTDAGI javobni muzlatadi, ya'ni
    kalendar keyinroq tahrirlansa o'tmishdagi dalil qayta talqin
    qilinmaydi.
    """
    with capture_fixture() as fx:
        day = fx.today + timedelta(days=1)
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).ensure_plan(day, grace_seconds=GRACE)
            answer = await session.execute(
                text("SELECT market_is_open(:market_id, :day)"),
                {"market_id": fx.market_id, "day": day},
            )
            expected = bool(answer.scalar_one())

        rows = await _rows_by_id(tenant_session, fx.market_id)
        planned = [row for row in rows.values() if row["business_date"] == day]
        assert planned, "reja qatorlari yozilishi shart"
        assert all(row["is_market_open"] is expected for row in planned)


async def test_ensure_plan_without_tenant_context_writes_nothing_and_never_raises(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ ENG JIM XATO SINFI: kontekstsiz chaqiruv 0 qator yozadi VA JIM QOLADI.

    RLS ostida `INSERT ... SELECT` istisno BERMAYDI — u shunchaki hech nima
    ko'rmaydi. Ya'ni fon vazifasi tenant kontekstini o'rnatishni unutsa,
    butun kunlik reja materializatsiya qilinmagan bo'lib qolardi va yagona
    belgi «bugun kadr yo'q» bo'lardi — ERTASI KUNI.

    NAZORAT BANDI shu testning ICHIDA: AYNAN o'sha argumentlar bilan
    kontekstli chaqiruv qator YOZADI. Usiz «0 qator» javobi izolyatsiyani
    emas, so'rovning umuman ishlamasligini ham bildirishi mumkin edi.
    """
    with capture_fixture() as fx:
        day = fx.today + timedelta(days=1)
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))

        async with app_sessionmaker() as session, session.begin():
            # ⚠ `set_tenant_context()` ATAYIN CHAQIRILMAYDI.
            blind = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )

        assert blind.created == 0
        assert blind.skipped == 0
        assert await _count_runs(tenant_session, fx.market_id, day) == 0

        # NAZORAT: kontekst bilan AYNAN o'sha chaqiruv ishlaydi.
        async with tenant_session(fx.market_id) as session:
            sighted = await CaptureRepository(session, fx.market_id).ensure_plan(
                day, grace_seconds=GRACE
            )
        assert sighted.created == fx.planned_rows


async def test_a_slot_added_after_materialisation_waits_until_tomorrow(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-05: KUN O'RTASIDAGI JADVAL TAHRIRI BUGUNGI REJAGA TA'SIR QILMAYDI.

    `capture_tick` HAR DAQIQADA `ensure_plan(bugun)` ni chaqiradi
    (`04-PATTERNS.md` §3.3). Shartsiz so'rov soat 12:00 da qo'shilgan
    `23:45` vaqtini BUGUNGI rejaga yozib qo'yardi va SC#1 ning «**ertasi
    kuni** aynan o'sha slotlarda» da'vosi yolg'onga aylanardi. UI ham
    DL-1 da buni doimiy izoh bilan va'da qiladi.

    NAZORAT: AYNAN o'sha yangi vaqt ERTANGI rejada BOR — ya'ni «bugunga
    tushmadi» javobi slotning umuman ishlamasligidan kelib chiqmagan.
    """
    with capture_fixture() as fx:
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))
        tomorrow = fx.today + timedelta(days=1)

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).ensure_plan(
                fx.today, grace_seconds=GRACE
            )
        materialised = await _count_runs(tenant_session, fx.market_id, fx.today)
        assert materialised == fx.planned_rows

        # Admin kun o'rtasida yangi vaqt qo'shdi.
        new_slot = time(23, 45)
        sync_owner_conn.execute(
            "INSERT INTO snapshot_schedule_slots (id, market_id, schedule_id, slot_time) "
            "VALUES (%s, %s, %s, %s)",
            (str(uuid4()), str(fx.market_id), str(fx.schedule_id), new_slot),
        )

        async with tenant_session(fx.market_id) as session:
            repeat = await CaptureRepository(session, fx.market_id).ensure_plan(
                fx.today, grace_seconds=GRACE
            )
            future = await CaptureRepository(session, fx.market_id).ensure_plan(
                tomorrow, grace_seconds=GRACE
            )

        assert repeat.created == 0
        assert await _count_runs(tenant_session, fx.market_id, fx.today) == materialised

        rows = await _rows_by_id(tenant_session, fx.market_id)
        today_slots = {
            row["slot_time"] for row in rows.values() if row["business_date"] == fx.today
        }
        tomorrow_slots = {
            row["slot_time"] for row in rows.values() if row["business_date"] == tomorrow
        }
        assert new_slot not in today_slots
        assert new_slot in tomorrow_slots
        assert future.created == len(fx.camera_ids) * (len(DEFAULT_SNAPSHOT_SLOTS) + 1)


async def test_a_camera_discovered_after_materialisation_still_gets_todays_slots(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT BANDI: D-05 muzlatishi SLOT o'lchovida, KUN o'lchovida EMAS.

    Kun o'lchovidagi muzlatish («kunda qator bo'lsa umuman hech nima
    qo'shma») mid-day kashf etilgan kamerani BUTUN KUNGA ko'rinmas
    qilardi: uning birorta `capture_runs` qatori bo'lmasdi, ya'ni jurnalda
    ham, yo'qlik yozuvida ham iz qolmasdi.

    Usiz yuqoridagi test «hech qachon hech nima qo'shilmaydi» degan xato
    implementatsiyada ham yashil qolardi.
    """
    with capture_fixture() as fx:
        _cover_from(sync_owner_conn, fx.schedule_id, fx.today - timedelta(days=30))

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).ensure_plan(
                fx.today, grace_seconds=GRACE
            )

        newcomer = uuid4()
        sync_owner_conn.execute(
            "INSERT INTO cameras (id, market_id, nvr_id, channel_no, stream_name, name, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'online')",
            (
                str(newcomer),
                str(fx.market_id),
                str(fx.nvr_id),
                77,
                f"cam_{newcomer.hex}",
                "Kech kashf etilgan kanal",
            ),
        )

        async with tenant_session(fx.market_id) as session:
            result = await CaptureRepository(session, fx.market_id).ensure_plan(
                fx.today, grace_seconds=GRACE
            )

        assert result.created == len(DEFAULT_SNAPSHOT_SLOTS)
        rows = await _rows_by_id(tenant_session, fx.market_id)
        newcomer_slots = {
            row["slot_time"]
            for row in rows.values()
            if row["camera_id"] == newcomer and row["business_date"] == fx.today
        }
        assert newcomer_slots == set(DEFAULT_SNAPSHOT_SLOTS)


# ---------------------------------------------------------------------------
# `claim_due` — muddat oynasi va qulf
# ---------------------------------------------------------------------------


async def test_claim_due_moves_the_row_to_running_under_a_lease(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Olingan qator: `running`, `attempts` +1, `locked_until` kelajakda, `locked_by` bor."""
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 5),
            offset_seconds=-60,
        )

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=10, worker_id="worker-1"
            )

        mine = [run for run in claimed if run.id == run_id]
        assert len(mine) == 1
        assert mine[0].attempts == 1
        assert mine[0].camera_id == fx.camera_ids[0]
        assert mine[0].nvr_id == fx.nvr_id
        assert mine[0].slot_time == time(5, 5)

        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.RUNNING.value
        assert row["attempts"] == 1
        assert row["locked_by"] == "worker-1"
        assert row["locked_until"] is not None
        assert row["locked_until"] > datetime.now(tz=MARKET_TZ)
        assert row["started_at"] is not None


async def test_claim_due_ignores_a_slot_whose_time_has_not_come(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """`scheduled_at > now()` — hali navbat emas."""
    with capture_fixture() as fx:
        future_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 6),
            offset_seconds=3600,
        )

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=10, worker_id="worker-1"
            )

        assert future_id not in {run.id for run in claimed}
        row = (await _rows_by_id(tenant_session, fx.market_id))[future_id]
        assert row["status"] == CaptureRunStatus.PENDING.value
        assert row["attempts"] == 0


async def test_claim_due_ignores_a_slot_past_the_grace_window(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ GRACE OYNASIDAN CHIQQAN SLOT BAJARILMAYDI — kechikkan kadr yo'q kadrdan YOMON.

    06:00 sloti 07:05 da olingan kadr «06:00 da rasta band edimi?» savoliga
    javob bermaydi, LEKIN javob berganday ko'rinadi. Shuning uchun oyna
    IKKI TOMONLAMA: `scheduled_at <= now()` VA `scheduled_at > now() - grace`.

    NAZORAT: o'sha kameraning oyna ICHIDAGI sloti O'SHA chaqiruvda olinadi,
    ya'ni «hech nima olinmadi» javobi so'rovning umuman ishlamasligidan
    kelib chiqmagan.
    """
    with capture_fixture() as fx:
        stale_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 7),
            offset_seconds=-(GRACE + 60),
        )
        fresh_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 8),
            offset_seconds=-60,
        )

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=10, worker_id="worker-1"
            )

        claimed_ids = {run.id for run in claimed}
        assert stale_id not in claimed_ids
        assert fresh_id in claimed_ids


async def test_parallel_claim_due_never_hands_the_same_row_twice_skip_locked(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    duo_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ `FOR UPDATE SKIP LOCKED` — IKKI OCHIQ TRANZAKSIYADA o'lchanadi.

    ⚠ IKKINCHI SESSIYA BIRINCHISI COMMIT QILISHIDAN OLDIN chaqiriladi. Aks
      holda test qulfni emas, `status = 'pending'` predikatini o'lchagan
      bo'lardi (birinchi tranzaksiya qatorlarni allaqachon `running` qilib
      qo'ygan bo'lardi) va `SKIP LOCKED` olib tashlanganda ham YASHIL
      qolardi.

    ⚠ `SET LOCAL statement_timeout` MAJBURIY va u testning YURAGI:
      `SKIP LOCKED` bo'lmasa ikkinchi so'rov qulf ustida ABADIY bloklanadi.
      Timeout uni `QueryCanceled` ga aylantiradi, ya'ni sabotaj testni
      osiltirmaydi — AYNAN qizartiradi.
    """
    with capture_fixture() as fx:
        run_ids = {
            _insert_run(
                sync_owner_conn,
                fx,
                camera_id=fx.camera_ids[index % len(fx.camera_ids)],
                slot_time=time(5, 10 + index),
                offset_seconds=-60,
            )
            for index in range(4)
        }

        async with duo_sessionmaker() as first, first.begin():
            await set_tenant_context(
                first, market_id=fx.market_id, actor_id=None, request_id="pytest-a"
            )
            claimed_first = await CaptureRepository(first, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=50, worker_id="worker-a"
            )

            # ⚠ BIRINCHI TRANZAKSIYA HALI OCHIQ — qulflar TURIBDI.
            async with duo_sessionmaker() as second, second.begin():
                await set_tenant_context(
                    second, market_id=fx.market_id, actor_id=None, request_id="pytest-b"
                )
                await second.execute(text("SET LOCAL statement_timeout = '4000ms'"))
                claimed_second = await CaptureRepository(second, fx.market_id).claim_due(
                    grace_seconds=GRACE, lease_seconds=LEASE, batch=50, worker_id="worker-b"
                )

        first_ids = {run.id for run in claimed_first}
        second_ids = {run.id for run in claimed_second}
        assert run_ids <= first_ids, "birinchi worker o'z partiyasini olishi shart"
        assert first_ids & second_ids == set(), "bitta qator IKKI worker'ga berildi"
        assert second_ids == set()


# ---------------------------------------------------------------------------
# Ijara — `SKIP LOCKED` QOPLAMAYDIGAN muddat
# ---------------------------------------------------------------------------


async def test_release_expired_returns_a_lost_lease_to_pending(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ IJARA `SKIP LOCKED` NING O'RNINI BOSMAYDI VA AKSINCHA.

    Worker qatorni `running` qilib COMMIT qilgach qulf TUSHADI. Agar u
    o'shandan keyin o'lsa, `SKIP LOCKED` hech nima qilmaydi — qator mangu
    `running` bo'lib qolardi va o'sha slot uchun na kadr, na alert, na
    hisobot qatori bo'lardi (D-20 aynan shuni taqiqlaydi).
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 20),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=-30,
            locked_by="worker-dead",
        )

        async with tenant_session(fx.market_id) as session:
            released = await CaptureRepository(session, fx.market_id).release_expired(
                max_attempts=MAX_ATTEMPTS
            )

        assert released == 1
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.PENDING.value
        assert row["locked_until"] is None
        assert row["locked_by"] is None
        # Urinish HISOBLANGAN bo'lib qoladi — byudjet tiklanmaydi.
        assert row["attempts"] == 1


async def test_release_expired_closes_a_row_that_burned_its_budget(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT BANDI: byudjeti tugagan qator `pending` GA QAYTMAYDI, `failed` bo'ladi.

    Usiz «ijara qaytaradi» da'vosi cheksiz aylanishdan farqlanmasdi: har
    tikda qayta olinib, har safar yiqiladigan qator NVR ga cheksiz borardi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 21),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=MAX_ATTEMPTS,
            lease_offset_seconds=-30,
            locked_by="worker-dead",
        )

        async with tenant_session(fx.market_id) as session:
            released = await CaptureRepository(session, fx.market_id).release_expired(
                max_attempts=MAX_ATTEMPTS
            )

        assert released == 1
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.FAILED.value
        assert row["error_code"] == CAPTURE_WORKER_LOST
        assert row["finished_at"] is not None


async def test_release_expired_leaves_a_live_lease_alone(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT: ijarasi HALI TUGAMAGAN qator tegilmaydi.

    Usiz `release_expired()` `locked_until` ni umuman o'qimasa ham yashil
    qolardi — u ISHLAYOTGAN worker'ning ishini tortib olardi va bitta slot
    ikki marta bajarilardi (T-04-33).
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 22),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-alive",
        )

        async with tenant_session(fx.market_id) as session:
            released = await CaptureRepository(session, fx.market_id).release_expired(
                max_attempts=MAX_ATTEMPTS
            )

        assert released == 0
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.RUNNING.value
        assert row["locked_by"] == "worker-alive"


# ---------------------------------------------------------------------------
# `mark_missed` — YO'QLIK yozuvi va alert manbai
# ---------------------------------------------------------------------------


async def test_mark_missed_closes_the_overdue_slot_and_returns_it(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ YO'QLIK HODISA QOLDIRMAYDI — shuning uchun u QATORDAN hosil qilinadi.

    `mark_missed()` qaytargan ro'yxat alertning YAGONA manbai (D-20). Qator
    faqat o'zgartirilib, QAYTARILMASA, «bugun 12 slot umuman bajarilmadi»
    xabari hech qayerdan kelmasdi va nosozlik jimgina o'tib ketardi.
    """
    with capture_fixture() as fx:
        overdue_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 30),
            offset_seconds=-(GRACE + 120),
        )
        # NAZORAT: grace oynasi ICHIDAGI qator tegilmaydi.
        fresh_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 31),
            offset_seconds=-60,
        )

        async with tenant_session(fx.market_id) as session:
            missed = await CaptureRepository(session, fx.market_id).mark_missed(grace_seconds=GRACE)

        returned = {slot.slot_time for slot in missed}
        assert time(5, 30) in returned
        assert time(5, 31) not in returned
        assert all(slot.market_id == fx.market_id for slot in missed)
        assert fx.camera_ids[0] in {slot.camera_id for slot in missed}

        rows = await _rows_by_id(tenant_session, fx.market_id)
        assert rows[overdue_id]["status"] == CaptureRunStatus.MISSED.value
        assert rows[overdue_id]["error_code"] == CAPTURE_SLOT_MISSED
        assert rows[overdue_id]["finished_at"] is not None
        assert rows[fresh_id]["status"] == CaptureRunStatus.PENDING.value


# ---------------------------------------------------------------------------
# Yakunlash — shartli o'tish va IKKI MUSTAQIL siyosat
# ---------------------------------------------------------------------------


async def test_finish_succeeded_only_moves_a_running_row(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Ikkinchi chaqiruv `False` oladi (`nvr_repo.start_run` bilan bir xil darvoza).

    Navbat vazifani «kamida bir marta» yetkazadi, ya'ni bir xil `run_id`
    bilan ikkinchi chaqiruv MUMKIN. Shartsiz `UPDATE` yakunlangan qatorni
    qayta yozib, ikkinchi kadrni birinchisining ustiga havola qilardi va
    «qaysi biri dalil?» savoli javobsiz qolardi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 40),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )
        snapshot_id = uuid4()

        async with tenant_session(fx.market_id) as session:
            repo = CaptureRepository(session, fx.market_id)
            first = await repo.finish_succeeded(
                run_id, snapshot_id=snapshot_id, method=CaptureMethod.GO2RTC.value
            )
            second = await repo.finish_succeeded(
                run_id, snapshot_id=uuid4(), method=CaptureMethod.ISAPI.value
            )

        assert first is True
        assert second is False
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.SUCCEEDED.value
        assert row["snapshot_id"] == snapshot_id
        assert row["capture_method"] == CaptureMethod.GO2RTC.value
        assert row["locked_until"] is None
        assert row["finished_at"] is not None


async def test_an_auth_locking_code_burns_the_whole_retry_budget(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ T-04-34: `capture_bad_credentials` dan keyin qator QAYTA OLINMAYDI.

    Arifmetika shafqatsiz: tik har daqiqada ishlaydi, 25 kamera x 10 tik =
    250 muvaffaqiyatsiz autentifikatsiya va Hikvision hisobni ~5
    urinishdan keyin 30 daqiqaga QULFLAYDI — undan keyin TO'G'RI PAROL HAM
    ishlamaydi. Ya'ni tizim o'z tuzatish yo'lini o'zi yopib qo'yardi.

    NAZORAT: da'vo `status == 'failed'` bilan emas, `claim_due()` uni
    QAYTA OLMAGANI bilan yopiladi — xulq, holat emas.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 41),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )

        async with tenant_session(fx.market_id) as session:
            closed = await CaptureRepository(session, fx.market_id).finish_failed(
                run_id, CAPTURE_BAD_CREDENTIALS, {"status": 401}, max_attempts=MAX_ATTEMPTS
            )

        assert closed is True
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.FAILED.value
        assert row["attempts"] == MAX_ATTEMPTS
        assert row["error_code"] == CAPTURE_BAD_CREDENTIALS

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=50, worker_id="worker-2"
            )
        assert run_id not in {run.id for run in claimed}


async def test_a_retryable_failure_returns_the_row_to_pending(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT BANDI: qulflamaydigan kod byudjet qolgan bo'lsa QAYTA URINISHGA qo'yadi.

    Usiz «autentifikatsiya kodi byudjetni yoqadi» da'vosi «HAR QANDAY xato
    byudjetni yoqadi» dan farqlanmasdi — ya'ni bir martalik tarmoq uzilishi
    slotni butunlay yo'qotardi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 42),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).finish_failed(
                run_id,
                CAPTURE_SOURCE_UNREACHABLE,
                {"reason": "tunnel down"},
                max_attempts=MAX_ATTEMPTS,
            )

        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.PENDING.value
        assert row["locked_until"] is None
        assert row["error_code"] == CAPTURE_SOURCE_UNREACHABLE
        assert row["finished_at"] is None

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=50, worker_id="worker-2"
            )
        assert run_id in {run.id for run in claimed}


async def test_finish_failed_masks_the_secrets_in_error_detail(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ T-04-39: xom javobdagi rekvizit `error_detail` ga TUSHMAYDI.

    Filtr ICHMA-ICH obyektni ham qamraydi — faqat yuqori daraja
    tekshirilsa `{"request": {"nvr_password": ...}}` ochiq qolardi
    (`nvr_repo.finish_run` bilan aynan bir xil chegara va bir xil sabab).
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 43),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).finish_failed(
                run_id,
                CAPTURE_SOURCE_UNREACHABLE,
                {"status": 401, "request": {"nvr_password": "Sim12345", "username": "sbozor"}},
                max_attempts=MAX_ATTEMPTS,
            )

        detail = (await _rows_by_id(tenant_session, fx.market_id))[run_id]["error_detail"]
        assert detail is not None
        assert detail["request"]["nvr_password"] != "Sim12345"
        # NAZORAT: sezgir BO'LMAGAN maydonlar joyida qoladi.
        assert detail["request"]["username"] == "sbozor"
        assert detail["status"] == 401


async def test_finish_failed_rejects_an_unknown_error_code(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Reyestrda yo'q kod BAZAGA TUSHMAYDI (§S-5).

    Kod bazaga tushib ketsa API uni tanimay `errors.generic` qaytarardi va
    sabab FAQAT foydalanuvchi ekranida yo'qolardi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 44),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )

        with pytest.raises(ValueError, match="noma'lum"):
            async with tenant_session(fx.market_id) as session:
                await CaptureRepository(session, fx.market_id).finish_failed(
                    run_id, "capture_oops", None, max_attempts=MAX_ATTEMPTS
                )


async def test_defer_keeps_the_row_pending_and_delays_the_next_tick(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ T-04-35: `capture_stream_limit` KECHIKTIRADI, qulflamaydi.

    NVR shunchaki band; oqim bo'shagach kadr olish MUVAFFAQIYATLI bo'ladi.
    Uni qulflovchi kodlarga qo'shish «NVR band edi» sababini «kadr yo'q» ga
    aylantirardi.

    ⚠ `scheduled_at` O'ZGARMAYDI va bu bandning yuragi: uni surish slotning
      biznes identitetini buzardi (`business_date` u ustundan HOSILA) va
      06:00 sloti hisobotda boshqa vaqt bo'lib chiqardi.

    NAZORAT: kechikish `locked_until` ustunini o'qish bilan emas, keyingi
    `claim_due()` ning qatorni OLMAGANI bilan o'lchanadi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 50),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )
        before = (await _rows_by_id(tenant_session, fx.market_id))[run_id]

        async with tenant_session(fx.market_id) as session:
            deferred = await CaptureRepository(session, fx.market_id).defer(
                run_id, 30, code=CAPTURE_STREAM_LIMIT
            )

        assert deferred is True
        row = (await _rows_by_id(tenant_session, fx.market_id))[run_id]
        assert row["status"] == CaptureRunStatus.PENDING.value
        assert row["scheduled_at"] == before["scheduled_at"]
        assert row["locked_until"] is not None
        assert row["locked_until"] > datetime.now(tz=MARKET_TZ)

        async with tenant_session(fx.market_id) as session:
            claimed = await CaptureRepository(session, fx.market_id).claim_due(
                grace_seconds=GRACE, lease_seconds=LEASE, batch=50, worker_id="worker-2"
            )
        assert run_id not in {run.id for run in claimed}


async def test_defer_refuses_a_code_that_is_not_a_defer_code(
    sync_owner_conn: Connection[TupleRow],
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT: QULFLOVCHI kod bilan `defer()` chaqirish RAD ETILADI.

    Aks holda `capture_bad_credentials` ni kechiktirish mumkin bo'lardi va
    T-04-34 ning butun himoyasi bitta noto'g'ri chaqiruv bilan chetlab
    o'tilardi — ikki siyosat bitta metodda birlashib ketardi.
    """
    with capture_fixture() as fx:
        run_id = _insert_run(
            sync_owner_conn,
            fx,
            camera_id=fx.camera_ids[0],
            slot_time=time(5, 51),
            offset_seconds=-60,
            status=CaptureRunStatus.RUNNING.value,
            attempts=1,
            lease_offset_seconds=LEASE,
            locked_by="worker-1",
        )

        with pytest.raises(ValueError, match="kechiktir"):
            async with tenant_session(fx.market_id) as session:
                await CaptureRepository(session, fx.market_id).defer(
                    run_id, 30, code=CAPTURE_BAD_CREDENTIALS
                )


# ---------------------------------------------------------------------------
# Kun xulosasi va matritsa
# ---------------------------------------------------------------------------


async def test_day_summary_reports_every_counter_including_the_zeros(
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ NOL HISOBLAGICH — NATIJA, UNING YO'QLIGI EMAS (3-fazadan meros qoida).

    `GROUP BY` natijasidan yig'ilgan xulosa nol hisoblagichni UMUMAN
    ko'rsatmasdi va UI'da «buzuq kadr yo'q» bilan «buzuq kadr sanalmagan»
    bir xil ko'rinardi. Shuning uchun oltala hisoblagich ham aniq
    `count(*) FILTER (WHERE ...)` bilan quriladi.

    Seed rejasi (`A_RUN_PLAN`) oltala HOLATNI qamraydi, lekin `blank` va
    `corrupt` verdiktlari unda YO'Q — ya'ni ularning noli aynan shu
    testning nazorat bandi.
    """
    with capture_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            summary = await CaptureRepository(session, fx.market_id).day_summary(SEED_BUSINESS_DATE)

        assert summary.planned == 7
        assert summary.done == 2
        assert summary.ok == 1
        assert summary.dark == 1
        assert summary.blank == 0
        assert summary.corrupt == 0
        assert summary.failed == 1
        assert summary.missed == 1


async def test_day_summary_of_an_empty_day_is_all_zeros(
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Qatorsiz kun ham BITTA qator qaytaradi — `None` emas, NOLLAR.

    `None` qaytarilsa chaqiruvchi har joyda `if summary is None` yozardi va
    ulardan bittasi uni unutib, UI'ga bo'sh xulosa chizardi.
    """
    with capture_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            summary = await CaptureRepository(session, fx.market_id).day_summary(
                fx.today + timedelta(days=400)
            )

        assert summary.planned == 0
        assert summary.done == 0
        assert (summary.ok, summary.dark, summary.blank, summary.corrupt) == (0, 0, 0, 0)
        assert (summary.failed, summary.missed) == (0, 0)


async def test_list_day_returns_the_matrix_in_channel_order(
    capture_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Matritsa qatorlari `channel_no` bo'yicha — `/cameras` bilan BIR XIL tartib.

    Sifat verdikti kadrdan keladi (`LEFT JOIN`), ya'ni kadri yo'q qatorda u
    `None` bo'ladi va hujayra C5–C9 holatlaridan birini oladi.
    """
    with capture_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            rows = await CaptureRepository(session, fx.market_id).list_day(SEED_BUSINESS_DATE)

        assert len(rows) == 7
        channels = [row.channel_no for row in rows]
        assert channels == sorted(channels)
        succeeded = [row for row in rows if row.status == CaptureRunStatus.SUCCEEDED.value]
        assert {row.quality_verdict for row in succeeded} == {
            SnapshotQuality.OK.value,
            SnapshotQuality.DARK.value,
        }
        missed = [row for row in rows if row.status == CaptureRunStatus.MISSED.value]
        assert len(missed) == 1
        assert missed[0].quality_verdict is None
        assert all(row.camera_name for row in rows)


# ---------------------------------------------------------------------------
# Tenant chegarasi
# ---------------------------------------------------------------------------


async def test_repository_never_sees_the_other_market_rows(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """A bozorining repozitoriysi B ning rejasini KO'RMAYDI (T-04-32).

    Ikki bozorli seed MAJBURIY: B da qator bo'lmasa «faqat o'ziniki
    qaytdi» da'vosi izolyatsiyani emas, jadvalning bo'shligini o'lchagan
    bo'lardi. Sonlar ATAYIN farqli (A: 7, B: 2), ya'ni noto'g'ri bozorning
    qatorlari qaytganda sanoq DARHOL mos kelmaydi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as nvr, snapshot_rows(sync_owner_conn, nvr) as snap:
        market_a = snap.market_a.market_id
        market_b = snap.market_b.market_id

        async with tenant_session(market_a) as session:
            repo_a = CaptureRepository(session, market_a)
            summary_a = await repo_a.day_summary(SEED_BUSINESS_DATE)
            rows_a = await repo_a.list_day(SEED_BUSINESS_DATE)

        async with tenant_session(market_b) as session:
            summary_b = await CaptureRepository(session, market_b).day_summary(SEED_BUSINESS_DATE)

        assert summary_a.planned == len(snap.market_a.plan)
        assert summary_b.planned == len(snap.market_b.plan)
        assert summary_a.planned != summary_b.planned
        assert {row.camera_id for row in rows_a} <= set(nvr.market_a.camera_ids)
        assert {row.run_id for row in rows_a} == set(snap.market_a.run_ids)
