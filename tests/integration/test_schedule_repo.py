"""`ScheduleRepository` — mavsumiy profil, davr bo'lish va qoplanmagan kunlar.

=============================================================================
UCH DA'VO SHU FAYLDA O'LCHANADI VA ULARNING HAR BIRI BOSHQA QATLAMGA TEGISHLI:

  1. **ILOVA SEMANTIKASI** — «mavsumiy profil qo'shish = mavjud davrni
     BO'LISH». Bu 2-fazadagi tarif naqshining aynan takrori va u faqat
     natijadagi davrlar ro'yxatidan ko'rinadi.

  2. **DB INVARIANTI** — `ex_snapshot_schedules_no_overlap`. Ilova uni
     TAKRORLAMAYDI: «avval kesishuvni tekshir, keyin yoz» ikki parallel
     so'rovda ikkalasini ham o'tkazib yuborardi. Repozitoriy `23P01` ni
     TANILGAN xatoga aylantiradi, ya'ni chaqiruvchi 409 beradi, 500 emas.

  3. **D-05** — «bugungi rejaga ta'sir qilmaydi». Bu da'vo `snapshot_
     schedules` jadvalida UMUMAN ko'rinmaydi: profil tahrirlangach jadval
     yangi vaqtlarni ko'rsatadi, bugungi REJA esa (`capture_runs`)
     o'zgarmaydi. Shuning uchun D-05 testi IKKI repozitoriyni birga
     ishlatadi — faqat `schedule_repo` bilan uni o'lchab bo'lmaydi.

Ikkinchi va birinchi da'vo ALOHIDA o'lchanadi: bo'lish qadamini olib
tashlash birinchisini qizartiradi, ikkinchisi esa (u bo'lishga umuman
tayanmaydigan yo'ldan boradi) YASHIL qoladi.
=============================================================================

SANALAR «BUGUN» DAN HISOBLANADI — `test_capture_repo.py` bilan bir xil
qoida va bir xil sabab. Bu yerda u YANADA qattiq: `create_seasonal()` ning
D-05 darvozasi AYNAN `starts_on > bugun` shartini o'lchaydi, ya'ni
qotirilgan sana bilan yozilgan test o'sha kundan keyin teskarisiga
aylanardi.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from app.repositories.capture_repo import CaptureRepository
from app.repositories.schedule_repo import (
    ScheduleNotEditableError,
    ScheduleOverlapError,
    ScheduleRepository,
    ScheduleSlotsInvalidError,
    ScheduleStartsTooSoonError,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.snapshot_domain import SCHEDULE_NAME, snapshot_rows
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager
    from typing import Any

    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")


HORIZON = 90
"""Qoplanish ufqi — `04-UI-SPEC.md` §4.3 dagi «keyingi 90 kun» bilan bir xil."""

MAX_TIMES = 12
"""Server chegarasi — `Settings.snapshot_max_times_per_day` bilan bir xil.

Qiymat KO'CHIRILGAN, import qilinmagan (`test_capture_repo.py::GRACE` bilan
bir xil sabab): `Settings()` `tests` konteynerida qurilmaydi. Nusxa
xavfsiz, chunki repozitoriyda bu son YO'Q — u ARGUMENT sifatida kiradi.
"""

WINTER_TIMES = (time(7, 0), time(7, 30), time(8, 0), time(15, 0), time(17, 0))
"""Qishki profilning beshta vaqti — `04-RESEARCH.md` §A.1 misolidan.

Standart yettitadan FARQLI SON: «bugun 7 slot · ertaga 5 slot» da'vosi
sonlar teng bo'lsa hech nimani o'lchamasdi.
"""

_WIDEN_SCHEDULE = "UPDATE snapshot_schedules SET period = daterange(%s, NULL, '[)') WHERE id = %s"
_SET_PERIOD = "UPDATE snapshot_schedules SET period = daterange(%s, %s, '[)') WHERE id = %s"


@dataclass(frozen=True)
class _Fixture:
    """Bir testga kerak bo'lgan seed qiymatlari."""

    market_id: UUID
    schedule_id: UUID
    camera_ids: tuple[UUID, ...]
    today: date


def _build(nvr: NvrDomainSeed, snap: SnapshotDomainSeed, today: date) -> _Fixture:
    return _Fixture(
        market_id=nvr.market_a.market_id,
        schedule_id=snap.market_a.schedule_id,
        camera_ids=nvr.market_a.active_camera_ids,
        today=today,
    )


@pytest.fixture
def schedule_fixture(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> Callable[[], AbstractContextManager[_Fixture]]:
    """`nvr_rows` + `snapshot_rows`, seed profili «bugun-30» dan ochiq oxirli.

    Davr DARHOL kengaytiriladi, chunki bu faylning HAR BIR testi «bugun»
    ga nisbatan qaror qiladi: seed'ning qadalgan `2026-09-01` boshlanishi
    bugun kelajakda, keyinroq esa o'tmishda bo'lardi va `active`/`future`
    rejimlari o'z-o'zidan almashardi.
    """

    @contextmanager
    def _open() -> Iterator[_Fixture]:
        with (
            nvr_rows(sync_owner_conn, two_markets) as nvr,
            snapshot_rows(sync_owner_conn, nvr) as snap,
        ):
            fixture = _build(nvr, snap, market_today)
            sync_owner_conn.execute(
                _WIDEN_SCHEDULE,
                (market_today - timedelta(days=30), str(fixture.schedule_id)),
            )
            yield fixture

    return _open


async def _periods(
    tenant_session: TenantSessionFactory, market_id: UUID
) -> list[tuple[str, date, date | None]]:
    """Bozorning BARCHA profillari — `(nom, boshlanish, tugash)`, tartibda.

    ⚠ XOM SQL, repozitoriyning O'Z o'qish metodi EMAS: bo'lish natijasini
      o'sha bo'lishni bajargan sinfning o'qish yo'li bilan tekshirish ikki
      xatoni bir-birini yopadigan qilib qo'yardi (`test_nvr_repo.py::
      _camera_rows` bilan bir xil qoida).
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT name, lower(period) AS starts_on, upper(period) AS ends_on "
                "  FROM snapshot_schedules WHERE market_id = :market_id "
                " ORDER BY lower(period)"
            ),
            {"market_id": market_id},
        )
        return [(row.name, row.starts_on, row.ends_on) for row in result]


async def _times_of(
    tenant_session: TenantSessionFactory, market_id: UUID, schedule_id: UUID
) -> list[time]:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT slot_time FROM snapshot_schedule_slots "
                " WHERE market_id = :market_id AND schedule_id = :schedule_id "
                " ORDER BY slot_time"
            ),
            {"market_id": market_id, "schedule_id": schedule_id},
        )
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# `today_and_tomorrow` — BITTA so'rov, BITTA lahza
# ---------------------------------------------------------------------------


async def test_today_and_tomorrow_come_from_a_single_query(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ BITTA `SELECT` — MEXANIK O'LCHOV, kelishuv emas.

    Ikki so'rovga bo'lingan variant «bugun» va «ertaga» ni TURLI lahzada
    olib kelardi va yarim tun atrofida ikkalasi bir kunni ko'rsatib
    qolardi — ya'ni D-05 ning butun ko'rsatkichi («bugun 7 slot · ertaga 5
    slot») aynan eng muhim daqiqada yolg'on bo'lardi.

    Sana o'zgarishini testda simulyatsiya qilib bo'lmaydi, shuning uchun
    o'lchov BOSHQA: bajarilgan SQL operatorlari SANALADI. Kontekst
    o'rnatilgandan KEYIN tinglovchi ulanadi, ya'ni oynada faqat
    repozitoriyning o'z so'rovlari qoladi.
    """
    with schedule_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            captured: list[str] = []

            def _record(
                conn: Any,
                cursor: Any,
                statement: str,
                parameters: Any,
                context: Any,
                executemany: bool,  # noqa: FBT001
            ) -> None:
                captured.append(statement)

            event.listen(Engine, "before_cursor_execute", _record)
            try:
                view = await ScheduleRepository(session, fx.market_id).today_and_tomorrow(
                    horizon_days=HORIZON
                )
            finally:
                event.remove(Engine, "before_cursor_execute", _record)

        assert len(captured) == 1, f"kutilgan 1 ta SQL, bajarilgani {len(captured)}: {captured}"
        assert view.today.date == fx.today
        assert view.tomorrow.date == fx.today + timedelta(days=1)
        assert tuple(view.today.times) == DEFAULT_SNAPSHOT_SLOTS
        assert view.uncovered_horizon_days == HORIZON


async def test_one_profile_covering_both_days_reports_no_difference(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Bugun va ertaga bir profilga tushsa `differs is False`.

    ⚠ «Ertaga» qatori UI'da DOIM render qilinadi, bir xil bo'lsa ham
      (`04-UI-SPEC.md` §4.3): D-05 ning butun mazmuni ikki qatorning
      MAVJUDLIGIDA. Shuning uchun `tomorrow` bu yerda ham to'ldirilgan
      bo'lishi shart, bo'sh emas.
    """
    with schedule_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            view = await ScheduleRepository(session, fx.market_id).today_and_tomorrow(
                horizon_days=HORIZON
            )

        assert view.differs is False
        assert tuple(view.today.times) == tuple(view.tomorrow.times)
        assert view.profile is not None
        assert view.profile.name == SCHEDULE_NAME
        assert view.profile.mode == "active"
        assert view.capture_on_closed_days is True


async def test_a_seasonal_profile_starting_tomorrow_makes_the_two_days_differ(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Ertangi kun boshqa profilga tushsa `differs is True` va vaqtlar farq qiladi.

    Bu UI'ning «Yangi jadval ertadan boshlab ishlaydi» ogohlantirishining
    YAGONA manbai — bayroqsiz u hech qachon chizilmasdi.
    """
    with schedule_fixture() as fx:
        tomorrow = fx.today + timedelta(days=1)

        async with tenant_session(fx.market_id) as session:
            await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=tomorrow,
                ends_on=None,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )

        async with tenant_session(fx.market_id) as session:
            view = await ScheduleRepository(session, fx.market_id).today_and_tomorrow(
                horizon_days=HORIZON
            )

        assert view.differs is True
        assert tuple(view.today.times) == DEFAULT_SNAPSHOT_SLOTS
        assert tuple(view.tomorrow.times) == WINTER_TIMES
        assert len(view.today.times) != len(view.tomorrow.times)


# ---------------------------------------------------------------------------
# Davr bo'lish (split) — CAM-04
# ---------------------------------------------------------------------------


async def test_a_seasonal_profile_splits_the_open_ended_one(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ «Qishki profil qo'shish» — MAVJUD davrni BO'LISH (`04-RESEARCH.md` §A.1).

    `EXCLUDE` kesishishni taqiqlagani uchun bu amal 2-fazadagi tarif
    qo'shish bilan BIR XIL sinfda. Bo'lish qadami bo'lmasa `INSERT` ning
    o'zi `23P01` bilan yiqilardi va admin «nega qo'sha olmayapman?» degan
    savolga javob topolmasdi.
    """
    with schedule_fixture() as fx:
        starts = fx.today + timedelta(days=10)

        async with tenant_session(fx.market_id) as session:
            new_id = await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=starts,
                ends_on=None,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )

        periods = await _periods(tenant_session, fx.market_id)
        assert periods == [
            (SCHEDULE_NAME, fx.today - timedelta(days=30), starts),
            ("Qishki", starts, None),
        ]
        assert await _times_of(tenant_session, fx.market_id, new_id) == list(WINTER_TIMES)


async def test_a_closed_seasonal_profile_restores_the_previous_one_as_a_copy(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ `ends_on` BERILGANDA oldingi profil NUSXA sifatida TIKLANADI.

    UI «Keyin «Standart» jadvali qaytadi» jumlasini AYNAN shundan chizadi
    (`04-UI-SPEC.md` §4.7). Tiklanmasa mavsum tugagan kuni bozor
    QOPLANMAGAN kunga tushardi — ya'ni kadr olish jimgina to'xtardi va
    admin buni faqat hisobot bo'shligidan bilardi.

    NUSXANING NOMI ASL NOM BILAN BIR XIL: farqli nom («Standart (nusxa)»)
    UI jumlasini yolg'on qilardi va admin uchun ikkinchi, tushunarsiz
    profil paydo bo'lardi.

    NUSXANING VAQTLARI HAM KO'CHADI — usiz tiklangan profil BO'SH bo'lardi
    va u qoplanmagan kundan farq qilmasdi.
    """
    with schedule_fixture() as fx:
        starts = fx.today + timedelta(days=10)
        ends = fx.today + timedelta(days=40)

        async with tenant_session(fx.market_id) as session:
            await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=starts,
                ends_on=ends,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )

        periods = await _periods(tenant_session, fx.market_id)
        assert periods == [
            (SCHEDULE_NAME, fx.today - timedelta(days=30), starts),
            ("Qishki", starts, ends),
            (SCHEDULE_NAME, ends, None),
        ]

        async with tenant_session(fx.market_id) as session:
            resumed = await ScheduleRepository(session, fx.market_id).slots_for(
                ends + timedelta(days=1)
            )
        assert tuple(resumed) == DEFAULT_SNAPSHOT_SLOTS


async def test_an_overlapping_period_is_a_recognised_error_not_a_five_hundred(
    sync_owner_conn: Connection[TupleRow],
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ DB INVARIANTI ALOHIDA O'LCHANADI — bo'lish qadamiga TAYANMAYDI.

    Seed profili «bugun+30» dan boshlanadigan qilib ko'chiriladi, ya'ni
    «bugun+10» kuni HECH QAYSI profilga tegishli emas. Shunda
    `create_seasonal()` ning bo'lish qadami umuman ishlamaydi (bo'linadigan
    profil yo'q), lekin yozilayotgan davr keyingi profilning ustiga
    CHIQADI va `ex_snapshot_schedules_no_overlap` uni rad etadi.

    Ilova bu tekshiruvni TAKRORLAMAYDI: «avval kesishuvni tekshir, keyin
    yoz» ikki parallel so'rovda ikkalasini ham o'tkazib yuborardi. Yagona
    qo'riqchi — konstraytning O'ZI; repozitoriyning ishi uni TANILGAN
    xatoga aylantirish, ya'ni chaqiruvchi 409 beradi, 500 emas.
    """
    with schedule_fixture() as fx:
        sync_owner_conn.execute(
            _WIDEN_SCHEDULE, (fx.today + timedelta(days=30), str(fx.schedule_id))
        )

        with pytest.raises(ScheduleOverlapError):
            async with tenant_session(fx.market_id) as session:
                await ScheduleRepository(session, fx.market_id).create_seasonal(
                    name="Qishki",
                    starts_on=fx.today + timedelta(days=10),
                    ends_on=fx.today + timedelta(days=40),
                    times=WINTER_TIMES,
                    today=fx.today,
                    max_times_per_day=MAX_TIMES,
                )


# ---------------------------------------------------------------------------
# D-05 — bugungi REJA (jadval emas) o'zgarmaydi
# ---------------------------------------------------------------------------


async def test_editing_the_active_profile_never_reaches_todays_plan(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-05 NING HAQIQIY O'LCHOVI — U `snapshot_schedules` DA KO'RINMAYDI.

    Faol profil tahrirlangach JADVAL yangi vaqtlarni ko'rsatadi (u bitta
    qator), lekin BUGUNGI REJA — `capture_runs` — o'zgarmasligi shart.
    Faqat `schedule_repo` bilan bu da'voni o'lchab BO'LMAYDI: u jadvalni
    ko'radi, rejani emas. Shuning uchun test IKKI repozitoriyni birga
    ishlatadi va bu ATAYIN.

    NAZORAT: AYNAN o'sha yangi vaqt ERTANGI rejaga TUSHADI — ya'ni
    «bugunga tushmadi» javobi tahrirning umuman ishlamasligidan kelib
    chiqmagan.
    """
    with schedule_fixture() as fx:
        tomorrow = fx.today + timedelta(days=1)
        extended = (*DEFAULT_SNAPSHOT_SLOTS, time(19, 30))

        async with tenant_session(fx.market_id) as session:
            await CaptureRepository(session, fx.market_id).ensure_plan(fx.today, grace_seconds=600)

        async with tenant_session(fx.market_id) as session:
            updated = await ScheduleRepository(session, fx.market_id).update_slots(
                fx.schedule_id,
                extended,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )
        assert updated is True

        async with tenant_session(fx.market_id) as session:
            repo = CaptureRepository(session, fx.market_id)
            repeat = await repo.ensure_plan(fx.today, grace_seconds=600)
            future = await repo.ensure_plan(tomorrow, grace_seconds=600)

        assert repeat.created == 0
        assert future.created == len(fx.camera_ids) * len(extended)

        async with tenant_session(fx.market_id) as session:
            rows_today = await CaptureRepository(session, fx.market_id).list_day(fx.today)
            rows_tomorrow = await CaptureRepository(session, fx.market_id).list_day(tomorrow)

        assert time(19, 30) not in {row.slot_time for row in rows_today}
        assert time(19, 30) in {row.slot_time for row in rows_tomorrow}


# ---------------------------------------------------------------------------
# Tahrirlash darvozalari — uch rejim (`04-UI-SPEC.md` §4.5)
# ---------------------------------------------------------------------------


async def test_a_seasonal_profile_starting_today_is_rejected(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """D-05: eng erta boshlanish — ERTAGA.

    Bugundan boshlanadigan profil bugungi rejani IKKI xil holatda
    qoldirardi: ertalabki slotlar eski jadvaldan materializatsiya
    qilingan, kechkilari esa yangisidan — ya'ni «shu kunda qaysi jadval
    amal qildi?» savoli javobsiz qolardi.
    """
    with schedule_fixture() as fx, pytest.raises(ScheduleStartsTooSoonError):
        async with tenant_session(fx.market_id) as session:
            await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=fx.today,
                ends_on=None,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )


async def test_update_slots_refuses_a_past_profile(
    sync_owner_conn: Connection[TupleRow],
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """O'tmishdagi profil O'QISH UCHUN (`04-UI-SPEC.md` §4.5).

    U o'tmishdagi kadrlarni TUSHUNTIRADI: «2026-01-15 da nega faqat 5
    kadr bor?» savolining javobi aynan o'sha profil. Tahrirlash tarixni
    yolg'onga aylantirardi va uni hech kim sezmasdi — kadrlar joyida
    qolardi, izoh esa boshqa bo'lardi.
    """
    with schedule_fixture() as fx:
        sync_owner_conn.execute(
            _SET_PERIOD,
            (
                fx.today - timedelta(days=60),
                fx.today - timedelta(days=30),
                str(fx.schedule_id),
            ),
        )

        with pytest.raises(ScheduleNotEditableError):
            async with tenant_session(fx.market_id) as session:
                await ScheduleRepository(session, fx.market_id).update_slots(
                    fx.schedule_id,
                    WINTER_TIMES,
                    today=fx.today,
                    max_times_per_day=MAX_TIMES,
                )

        assert await _times_of(tenant_session, fx.market_id, fx.schedule_id) == list(
            DEFAULT_SNAPSHOT_SLOTS
        )


async def test_delete_future_removes_a_profile_that_has_not_started(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ KELAJAKDAGI PROFILNI O'CHIRISH RUXSAT ETILADI — VA U ISTISNO.

    Bu fazadagi boshqa ikkala repozitoriy ham hech nimani o'chirmaydi
    (dalil zanjiri). Bu yerda esa o'chirish XAVFSIZ va zarur: hali
    boshlanmagan profil birorta `capture_runs` qatorini tug'dirmagan,
    ya'ni o'chiriladigan DALIL yo'q. Xato bilan kiritilgan mavsumni
    tuzatishning boshqa yo'li ham yo'q.

    ⚠ Amalning O'ZI baribir izsiz emas: `snapshot_schedules` va
      `snapshot_schedule_slots` `AUDITED_TABLES` da, ya'ni o'chirish audit
      jurnaliga tushadi.

    Profil o'chgach o'sha kunlar QOPLANMAGAN bo'lib qoladi va buni
    `uncovered_days` ko'rsatadi — jim ma'lumot yo'qotish emas.
    """
    with schedule_fixture() as fx:
        starts = fx.today + timedelta(days=10)
        ends = fx.today + timedelta(days=40)

        async with tenant_session(fx.market_id) as session:
            future_id = await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=starts,
                ends_on=ends,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )

        async with tenant_session(fx.market_id) as session:
            removed = await ScheduleRepository(session, fx.market_id).delete_future(
                future_id, today=fx.today
            )

        assert removed is True
        names = [name for name, _, _ in await _periods(tenant_session, fx.market_id)]
        assert names == [SCHEDULE_NAME, SCHEDULE_NAME]
        # Slotlari ham ketdi (`ON DELETE CASCADE`).
        assert await _times_of(tenant_session, fx.market_id, future_id) == []

        async with tenant_session(fx.market_id) as session:
            gap = await ScheduleRepository(session, fx.market_id).uncovered_days(
                horizon_days=HORIZON
            )
        assert gap == (ends - starts).days


async def test_delete_future_refuses_a_profile_that_already_started(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT BANDI: boshlangan profil o'chirilmaydi.

    Usiz «kelajakdagini o'chirish mumkin» da'vosi «hamma narsani o'chirish
    mumkin» dan farqlanmasdi — va o'chirilgan faol profil o'tmishdagi
    kadrlarning yagona izohini yo'q qilardi.
    """
    with schedule_fixture() as fx:
        with pytest.raises(ScheduleNotEditableError):
            async with tenant_session(fx.market_id) as session:
                await ScheduleRepository(session, fx.market_id).delete_future(
                    fx.schedule_id, today=fx.today
                )

        names = [name for name, _, _ in await _periods(tenant_session, fx.market_id)]
        assert names == [SCHEDULE_NAME]


async def test_the_server_enforces_the_slot_limit(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ KLIENTDAGI CHEGARA — QULAYLIK, XAVFSIZLIK CHEGARASI EMAS.

    12 x 25 kamera = 300 kadr/kun/bozor ≈ 6,5 GB/yil. Chegarasiz
    «06:00–20:00 har 5 daqiqada» = 169 vaqt = 4 225 kadr/kun va Contabo
    diski bir necha oyda to'lardi. DevTools bilan olib tashlanadigan
    klient tekshiruvi bunga qarshi hech nima emas.

    Uch shakl ham shu yerda: chegaradan oshiq, BO'SH ro'yxat (kadr
    olinmaydigan bozorni jadval orqali yasab bo'lmaydi) va DUBLIKAT.
    """
    with schedule_fixture() as fx:
        too_many = tuple(time(hour, minute) for hour in (6, 7, 8, 9) for minute in (0, 15, 30, 45))
        assert len(too_many) > MAX_TIMES, "nazorat: ro'yxat chegaradan OSHIQ bo'lishi shart"

        async with tenant_session(fx.market_id) as session:
            repo = ScheduleRepository(session, fx.market_id)
            with pytest.raises(ScheduleSlotsInvalidError):
                await repo.update_slots(
                    fx.schedule_id, too_many, today=fx.today, max_times_per_day=MAX_TIMES
                )

        async with tenant_session(fx.market_id) as session:
            repo = ScheduleRepository(session, fx.market_id)
            with pytest.raises(ScheduleSlotsInvalidError):
                await repo.update_slots(
                    fx.schedule_id, (), today=fx.today, max_times_per_day=MAX_TIMES
                )

        async with tenant_session(fx.market_id) as session:
            repo = ScheduleRepository(session, fx.market_id)
            with pytest.raises(ScheduleSlotsInvalidError):
                await repo.update_slots(
                    fx.schedule_id,
                    (time(6, 0), time(6, 0)),
                    today=fx.today,
                    max_times_per_day=MAX_TIMES,
                )

        assert await _times_of(tenant_session, fx.market_id, fx.schedule_id) == list(
            DEFAULT_SNAPSHOT_SLOTS
        )


async def test_update_slots_normalises_the_order(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Tartib DOMEN MA'NOSI TASHIMAYDI — repozitoriy uni normallashtiradi.

    Klient tartibini saqlash «06:00, 18:00, 07:00» ko'rinishidagi ro'yxat
    berardi va UI har safar uni qayta saralashi kerak bo'lardi — ya'ni
    saralash mantig'i ikki joyda yashardi.
    """
    with schedule_fixture() as fx:
        shuffled = (time(18, 0), time(6, 0), time(12, 30))

        async with tenant_session(fx.market_id) as session:
            await ScheduleRepository(session, fx.market_id).update_slots(
                fx.schedule_id, shuffled, today=fx.today, max_times_per_day=MAX_TIMES
            )

        assert await _times_of(tenant_session, fx.market_id, fx.schedule_id) == sorted(shuffled)


# ---------------------------------------------------------------------------
# Qoplanmagan kunlar — BIRINCHI DARAJALI metod, qo'shimcha emas
# ---------------------------------------------------------------------------


async def test_uncovered_days_counts_the_gap_between_two_profiles(
    sync_owner_conn: Connection[TupleRow],
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ BO'SHLIQ ATAYIN MUMKIN VA U XATO EMAS — LEKIN U KO'RINISHI SHART.

    Qoplanmagan kunda umuman slot yo'q, ya'ni kadr olinmaydi. Mavsumiy
    yopiladigan bozor uchun bu to'g'ri xulq; ko'rinmasa esa bu JIM
    MA'LUMOT YO'QOTISH bo'lardi — admin bir oydan keyin hisobotdagi
    bo'shliqni ko'rib «tizim buzilibdi» deb o'ylardi.

    Sanoq SQL'da (`generate_series`), Python'da EMAS: 90 kunni tarmoqdan
    olib kelib sanash bir xil javobni ancha qimmatga berardi.
    """
    with schedule_fixture() as fx:
        gap_start = fx.today + timedelta(days=10)
        gap_end = fx.today + timedelta(days=25)
        sync_owner_conn.execute(
            _SET_PERIOD, (fx.today - timedelta(days=30), gap_start, str(fx.schedule_id))
        )

        async with tenant_session(fx.market_id) as session:
            await ScheduleRepository(session, fx.market_id).create_seasonal(
                name="Qishki",
                starts_on=gap_end,
                ends_on=None,
                times=WINTER_TIMES,
                today=fx.today,
                max_times_per_day=MAX_TIMES,
            )

        async with tenant_session(fx.market_id) as session:
            repo = ScheduleRepository(session, fx.market_id)
            uncovered = await repo.uncovered_days(horizon_days=HORIZON)
            view = await repo.today_and_tomorrow(horizon_days=HORIZON)

        assert uncovered == (gap_end - gap_start).days
        assert view.uncovered_days == uncovered
        assert view.uncovered_horizon_days == HORIZON


async def test_uncovered_days_is_zero_when_the_horizon_is_fully_covered(
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT: ochiq oxirli profil butun ufqni qoplaydi -> 0.

    Usiz «bo'shliq sanaladi» da'vosi «har doim nol bo'lmagan son
    qaytariladi» dan farqlanmasdi va UI doimiy soxta ogohlantirish
    ko'rsatardi — operator esa unga ishonishni to'xtatardi.
    """
    with schedule_fixture() as fx:
        async with tenant_session(fx.market_id) as session:
            uncovered = await ScheduleRepository(session, fx.market_id).uncovered_days(
                horizon_days=HORIZON
            )
        assert uncovered == 0


async def test_slots_for_an_uncovered_day_is_empty_not_an_error(
    sync_owner_conn: Connection[TupleRow],
    schedule_fixture: Callable[[], AbstractContextManager[_Fixture]],
    tenant_session: TenantSessionFactory,
) -> None:
    """Qoplanmagan kun uchun `slots_for()` BO'SH ro'yxat beradi, istisno emas.

    Istisno bo'lsa `ensure_plan()` ni chaqiradigan tik butun bozor uchun
    yiqilardi — holbuki bo'shliq XATO EMAS. Bo'sh ro'yxat esa tabiiy
    natijaga olib keladi: o'sha kunga reja yozilmaydi.
    """
    with schedule_fixture() as fx:
        sync_owner_conn.execute(
            _SET_PERIOD,
            (
                fx.today - timedelta(days=30),
                fx.today + timedelta(days=5),
                str(fx.schedule_id),
            ),
        )

        async with tenant_session(fx.market_id) as session:
            repo = ScheduleRepository(session, fx.market_id)
            covered = await repo.slots_for(fx.today)
            uncovered = await repo.slots_for(fx.today + timedelta(days=10))
            profile = await repo.active_profile(fx.today + timedelta(days=10))

        assert tuple(covered) == DEFAULT_SNAPSHOT_SLOTS
        assert uncovered == []
        assert profile is None


# ---------------------------------------------------------------------------
# Tenant chegarasi
# ---------------------------------------------------------------------------


async def test_repository_never_sees_the_other_market_profiles(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    market_today: date,
) -> None:
    """A bozorining bo'lishi B ning profiliga TEGMAYDI (T-04-32).

    Ikki bozorli seed MAJBURIY: B da profil bo'lmasa «faqat o'ziniki
    o'zgardi» da'vosi izolyatsiyani emas, jadvalning bo'shligini o'lchagan
    bo'lardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snap,
    ):
        market_a = snap.market_a.market_id
        market_b = snap.market_b.market_id
        for rows in (snap.market_a, snap.market_b):
            sync_owner_conn.execute(
                _WIDEN_SCHEDULE, (market_today - timedelta(days=30), str(rows.schedule_id))
            )
        before_b = await _periods(tenant_session, market_b)

        async with tenant_session(market_a) as session:
            await ScheduleRepository(session, market_a).create_seasonal(
                name="Qishki",
                starts_on=market_today + timedelta(days=10),
                ends_on=None,
                times=WINTER_TIMES,
                today=market_today,
                max_times_per_day=MAX_TIMES,
            )

        assert len(await _periods(tenant_session, market_a)) == 2
        assert await _periods(tenant_session, market_b) == before_b

        # B ning profilini A ning konteksti bilan tahrirlab bo'lmaydi.
        async with tenant_session(market_a) as session:
            edited = await ScheduleRepository(session, market_a).update_slots(
                snap.market_b.schedule_id,
                WINTER_TIMES,
                today=market_today,
                max_times_per_day=MAX_TIMES,
            )
        assert edited is False
        assert await _times_of(tenant_session, market_b, snap.market_b.schedule_id) == list(
            DEFAULT_SNAPSHOT_SLOTS
        )
