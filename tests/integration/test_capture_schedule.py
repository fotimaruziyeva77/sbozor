"""Snapshot jadvalining HTTP yuzasi (CAM-04, D-05).

=============================================================================
BU FAYLDAGI ENG MUHIM TEST — «403 JURNALDA IZ QOLDIRMAYDI».

`04-PATTERNS.md` §3.9 huquq talabini MARSHRUT DEKORATORIGA qo'yishni
buyuradi, sabab esa mexanizmda emas, DA'VODA: imzo parametriga
ko'chirilgan huquq bilan 403 olgan so'rov `audit_read` gacha yetib
borardi va jurnalda «kim nimani ko'rdi» degan YOLG'ON DALIL qolardi.

03-07 o'lchagan fakt: mexanizmni sinaydigan test (huquq qayerda e'lon
qilingan?) SABOTAJDA HECH NIMANI QIZARTIRMAGAN, chunki kafolatning
IKKI mustaqil manbai bor va ikkinchisi (`BackgroundTasks` javobga
biriktiriladi) uni YOLG'IZ ham ushlab turadi.

Shuning uchun bu yerdagi test MEXANIZMNI emas, DA'VONI o'lchaydi:
so'rov rad etiladi VA `audit_log` da o'sha bozorga tegishli o'qish
qatori PAYDO BO'LMAYDI. Da'vo har ikkala mexanizmdan ham mustaqil.
=============================================================================

⚠ SANALAR «BUGUN» DAN HISOBLANADI, QOTIRILMAYDI (`test_capture_tick.py` va
  `test_capture_repo.py` ning qoidasi va bir xil sabab). Seed profilining
  `SEED_BUSINESS_DATE` i (2026-09-01) loyihaning O'Z muddati ichida
  kelajakdan o'tmishga aylanadi va D-05 darvozasining shoxi JIMGINA
  almashardi. Shuning uchun seed davri `_cover_from()` bilan
  kengaytiriladi va har bir da'vo `market_today` dan quriladi.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.schemas import MARKET_ERROR_CODES
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.nvr_domain import nvr_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

SCHEDULES_URL = "/api/v1/snapshot-schedules"
TODAY_URL = f"{SCHEDULES_URL}/today"
TABLE_SCHEDULES = "snapshot_schedules"
TABLE_SLOTS = "snapshot_schedule_slots"

_WIDEN_SCHEDULE = "UPDATE snapshot_schedules SET period = daterange(%s, NULL, '[)') WHERE id = %s"
_SET_PERIOD = "UPDATE snapshot_schedules SET period = daterange(%s, %s, '[)') WHERE id = %s"
SLOT_TIMES = ["06:00", "06:30", "07:00"]
"""Testlar YUBORADIGAN vaqtlar — seedning YETTITASIDAN farqli SON.

Bir xil son bo'lsa «vaqtlar almashdimi?» da'vosi seedning o'z qatorlariga
qarab ham yashil bo'lardi.
"""

SLOT_TIMES_WIRE = ["06:00:00", "06:30:00", "07:00:00"]
"""AYNAN O'SHA vaqtlar — JAVOBDA qanday ko'rinsa (ISO-8601 `HH:MM:SS`).

⚠ IKKI KONSTANTA ATAYIN: kirish va chiqish shakllari BIR XIL EMAS.
  Pydantic `time` ni to'liq ISO shaklida seriyalaydi, `04-UI-SPEC.md`
  §4.6 dagi `HH:mm` esa KO'RSATISH formati va uni `next-intl` chizadi.
  Ikkalasini bitta ro'yxat bilan tekshirish testni «server nima
  qaytarishi kerak» emas, «UI nimani ko'rsatishi kerak» ustida
  o'lchagan bo'lardi.
"""


@pytest.fixture
def schedule_env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> Callable[[], AbstractContextManager[SnapshotDomainSeed]]:
    """`nvr_rows` + `snapshot_rows`, seed profili BUGUNNI qoplaydigan qilib.

    Tartib MUHIM (`test_capture_tick.py` dagi jufti bilan bir xil sabab):
    `snapshot_rows` ning tozalash bloki `nvr_rows` NING ICHIDA turishi
    shart, aks holda `cameras` hali `capture_runs` tayanib turganda
    o'chirilardi.
    """

    @contextmanager
    def _open() -> Iterator[SnapshotDomainSeed]:
        with (
            nvr_rows(sync_owner_conn, two_markets) as nvr,
            snapshot_rows(sync_owner_conn, nvr) as snap,
        ):
            for rows in snap.markets:
                sync_owner_conn.execute(
                    _WIDEN_SCHEDULE,
                    (market_today - timedelta(days=30), str(rows.schedule_id)),
                )
            yield snap

    return _open


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi — `CAMERA_VIEW` + `CAMERA_MANAGE`."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori kassirining sessiyasi — IKKALA kamera huquqi ham YO'Q."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori direktorining sessiyasi — `CAMERA_VIEW` BOR, `CAMERA_MANAGE` YO'Q."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.director_phone, SEED_PASSWORD)


async def _schedule_reads(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
) -> list[Any]:
    """`action='read'` + jadval resurslariga tegishli yozuvlar — MAHSULOT yo'li bilan.

    Superuser bilan O'QILMAYDI (`test_personal_data_audit.py` ning
    qoidasi): audit ekrani aynan shu yo'ldan ma'lumot oladi.
    """
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return [row for row in rows if row.table_name in {TABLE_SCHEDULES, TABLE_SLOTS}]


def _future(today: date, days: int = 10) -> str:
    return (today + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# D-05 — «bugun» va «ertaga» BITTA so'rovda
# ---------------------------------------------------------------------------


async def test_today_and_tomorrow_arrive_in_one_request(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """BITTA javob ikkala kunni ham beradi va ular KETMA-KET kunlar (D-05).

    Ikki marshrutga bo'lingan variant yarim tun atrofida ikkalasini BIR
    kunni ko'rsatib qo'yardi. Test aynan shuni o'lchaydi: `tomorrow.date`
    `today.date` dan AYNAN bir kun keyin.
    """
    with schedule_env():
        response = await api_client.get(TODAY_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()

    assert date.fromisoformat(body["today"]["date"]) == market_today
    assert date.fromisoformat(body["tomorrow"]["date"]) == market_today + timedelta(days=1)
    # Ikkala kun ham O'Z vaqtlari bilan keladi — «times» yolg'iz
    # qaytarilsa UI ularni qaysi kunga tegishli ekanini o'zi hisoblardi.
    assert body["today"]["times"], "bugungi reja bo'sh — seed profili qoplamadi"
    assert body["tomorrow"]["times"]
    for field in (
        "differs",
        "capture_on_closed_days",
        "uncovered_days",
        "uncovered_horizon_days",
        "profile",
    ):
        assert field in body, f"`{field}` javobda yo'q — §4.3 [TALAB] shakli buzilgan"
    assert body["profile"]["mode"] in {"past", "active", "future"}


async def test_editing_the_schedule_changes_tomorrow_and_leaves_today_alone(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """D-05 ning MAHSULOT da'vosi: tahrir ERTAGA ko'rinadi, BUGUN emas.

    Bugungi reja allaqachon materializatsiya qilingan (`capture_runs`
    qatorlari seedda bor) va `capture_repo.ensure_plan()` ning slot
    o'lchovidagi muzlatishi unga yangi vaqt qo'shmaydi. Bu marshrutning
    vazifasi — o'sha farqni KO'RSATISH.

    ⚠ DA'VO `differs` BAYROG'IDA EMAS, `times` NING O'ZIDA: bayroq
      profil bo'yicha hisoblanadi va tahrir bitta profil ichida bo'lgani
      uchun u o'zgarmaydi. Ya'ni bayroqqa qarash testni ma'nosiz qilardi.
    """
    with schedule_env() as snap:
        before = (await api_client.get(TODAY_URL, headers=admin_headers)).json()
        patched = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )
        assert patched.status_code == 200, patched.text
        after = (await api_client.get(TODAY_URL, headers=admin_headers)).json()

    # Jadval — bitta profil, ya'ni «ertaga» darhol yangi vaqtlarni ko'radi.
    assert after["tomorrow"]["times"] == SLOT_TIMES_WIRE
    assert after["today"]["times"] == SLOT_TIMES_WIRE
    # ⚠ Yuqoridagi ikkinchi assertion ATAYIN: JADVAL o'zgardi, lekin
    #   BUGUNGI REJA (`capture_runs`) o'zgarmadi — D-05 ning kafolati
    #   jadval yuzasida emas, materializatsiyada. Bu farqni
    #   `test_capture_repo.py::test_a_slot_added_after_materialisation_
    #   waits_until_tomorrow` o'lchaydi va u bu yerda TAKRORLANMAYDI.
    assert before["today"]["times"] != SLOT_TIMES_WIRE, "seed allaqachon shu vaqtlarda edi"


# ---------------------------------------------------------------------------
# HUQUQ DARVOZASI — DA'VO o'lchanadi, mexanizm emas
# ---------------------------------------------------------------------------


async def test_a_role_without_camera_view_is_refused_and_leaves_no_read_audit(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """403 VA jurnalda o'qish qatori YO'Q — fayl boshidagi asosiy da'vo.

    Ikki assertion ATAYIN bitta testda: ular bitta DA'VONING ikki yuzi
    («so'rov rad etildi» va «rad etilgan so'rov iz qoldirmadi») va
    ajratilganda ikkinchisi yolg'iz o'zi ma'nosiz bo'lardi — audit
    qatori bo'lmagan holat 403 bo'lmaganda ham rost bo'lishi mumkin.
    """
    market_id = two_markets.market_a.id
    with schedule_env():
        before = await _schedule_reads(tenant_session, market_id)
        response = await api_client.get(TODAY_URL, headers=cashier_headers)
        after = await _schedule_reads(tenant_session, market_id)

    assert response.status_code == 403
    assert len(after) == len(before), (
        "rad etilgan so'rov `audit_log` ga o'qish qatori yozdi — jurnalda "
        "YOLG'ON DALIL qoldi (huquq talabi dekoratorda emas?)"
    )


async def test_the_schedule_surface_declares_no_read_audit_at_all(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """NAZORAT: MUVAFFAQIYATLI o'qish ham audit qatori qoldirmaydi.

    Usiz yuqoridagi test «hamma `GET` ga audit kerak» degan darvozadan
    ajralmasdi — u holda 403 testi audit umuman yo'qligi uchun ham
    yashil bo'lardi va hech nimani isbotlamasdi.

    Jadval SHAXSIY MA'LUMOT EMAS (`stalls.py:348-369` bilan bir xil
    qaror va bir xil sabab): unga audit yopishtirish jurnalni har
    sahifa ochilishida shovqin bilan to'ldirardi va HAQIQIY o'qish
    hodisasini — kadr rasmini — ko'mib yuborardi.
    """
    market_id = two_markets.market_a.id
    with schedule_env():
        before = await _schedule_reads(tenant_session, market_id)
        response = await api_client.get(TODAY_URL, headers=admin_headers)
        after = await _schedule_reads(tenant_session, market_id)

    assert response.status_code == 200
    assert len(after) == len(before), (
        "jadval yuzasi o'qish auditini e'lon qilibdi — sabab `schedules.py` "
        "modul docstringida: jadval shaxsiy ma'lumot emas"
    )


async def test_the_director_reads_the_schedule_but_cannot_edit_it(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """`CAMERA_VIEW` bor, `CAMERA_MANAGE` yo'q — o'qish 200, yozuv 403.

    Nazorat holati bilan birga keladi (`test_director_cannot_manage_stalls`
    naqshi): faqat 403 ni o'lchaydigan test rolning butunlay
    bloklanganini ham «to'g'ri» deb ko'rsatardi.
    """
    with schedule_env() as snap:
        read = await api_client.get(TODAY_URL, headers=director_headers)
        write = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            json={"times": SLOT_TIMES},
            headers=director_headers,
        )

    assert read.status_code == 200
    assert write.status_code == 403


# ---------------------------------------------------------------------------
# YOZISH DARVOZALARI — HAR BIRI TANILGAN KOD BILAN
# ---------------------------------------------------------------------------


async def test_a_profile_starting_today_is_refused_with_a_recognised_code(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """`starts_on <= bugun` -> 422 va kod `MARKET_ERROR_CODES` da (D-05).

    Kod reyestrda bo'lmasa frontend uni `errors.generic` ga tushirardi va
    admin «nega rad etildi?» savoliga javob olmasdi (§S-5 sinfi).
    """
    with schedule_env():
        response = await api_client.post(
            SCHEDULES_URL,
            json={"name": "Qishki", "starts_on": market_today.isoformat(), "times": SLOT_TIMES},
            headers=admin_headers,
        )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail == "schedule_starts_too_soon"
    assert detail in MARKET_ERROR_CODES


async def test_an_overlapping_period_is_a_recognised_conflict_not_a_five_hundred(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    market_today: date,
) -> None:
    """Kesishuvchi davr -> 409, `23P01` xom holda chiqmaydi.

    ⚠ TEST ATAYIN BO'LISH (split) SEMANTIKASIGA TAYANMAYDI
      (`test_schedule_repo.py` ning 5-deviatsiyasi bilan bir xil qaror va
      bir xil sabab). Ilova qatlami kesishuvni O'ZI hal qiladi: agar
      yangi davr mavjud profilning USTIDA boshlansa, `create_seasonal()`
      uni QISQARTIRADI va hech qanday konflikt YUZAGA KELMAYDI — ya'ni
      «kesishuv 409 beradi» da'vosini shu yo'ldan o'lchab bo'lmaydi
      (birinchi urinishda AYNAN shu sabab 201 chiqdi).

      Shuning uchun yangi davr BO'SHLIQDA boshlanadi (qisqartiriladigan
      profil YO'Q) va KEYINGI profilning ustiga CHIQADI. Endi 409 ning
      manbai — DB ning `EXCLUDE` konstrayti, ilova mantig'i emas: ikki
      qatlam HAQIQATAN mustaqil o'lchanadi.
    """
    later_start = market_today + timedelta(days=20)
    with schedule_env() as snap:
        # Seed profilini bugundan +10 kunda tugatamiz -> [+10, +20) BO'SHLIQ.
        sync_owner_conn.execute(
            _SET_PERIOD,
            (
                market_today - timedelta(days=30),
                market_today + timedelta(days=10),
                str(snap.market_a.schedule_id),
            ),
        )
        later = await api_client.post(
            SCHEDULES_URL,
            json={
                "name": "Ramazon",
                "starts_on": later_start.isoformat(),
                "ends_on": (later_start + timedelta(days=20)).isoformat(),
                "times": SLOT_TIMES,
            },
            headers=admin_headers,
        )
        assert later.status_code == 201, later.text
        # BO'SHLIQDA boshlanadi (qisqartiriladigan profil yo'q), lekin
        # `later` ning ICHIGA kirib ketadi -> `EXCLUDE` buziladi.
        clash = await api_client.post(
            SCHEDULES_URL,
            json={
                "name": "Kesishuvchi",
                "starts_on": (market_today + timedelta(days=15)).isoformat(),
                "ends_on": (later_start + timedelta(days=10)).isoformat(),
                "times": SLOT_TIMES,
            },
            headers=admin_headers,
        )

    assert clash.status_code == 409, clash.text
    assert clash.json()["detail"] == "schedule_period_overlaps"


async def test_the_server_enforces_the_slot_limit(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """Chegaradan OSHIQ vaqtlar -> 422, SERVER tomonida (§4.6 `[TALAB]`).

    Klientdagi `MAX_TIMES_PER_DAY` DevTools bilan olib tashlanadi, ya'ni
    u xavfsizlik chegarasi emas. Bu yerda so'rov to'g'ridan-to'g'ri
    API'ga boradi — aynan chetlab o'tilgan holat.

    ⚠ ARIFMETIKA TEKSHIRILADI: ro'yxat chegaradan HAQIQATAN oshiqligi
      testning O'ZIDA tasdiqlanadi (04-05 da bir marta 12 == 12 bilan
      yiqilgan holat).
    """
    limit = 12
    times = [f"{hour:02d}:{minute:02d}" for hour in range(6, 13) for minute in (0, 30)]
    assert len(times) > limit, f"test o'z arifmetikasida yanglishdi: {len(times)} <= {limit}"

    with schedule_env():
        response = await api_client.post(
            SCHEDULES_URL,
            json={"name": "Ko'p", "starts_on": _future(market_today), "times": times},
            headers=admin_headers,
        )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "schedule_slots_invalid"


async def test_patching_an_active_profile_accepts_times_and_rejects_the_period(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """`times` qabul qilinadi, `starts_on` yuborilsa so'rov RAD ETILADI (§4.5).

    Jim e'tiborsizlik rad etishdan yomonroq: klient «davrni
    o'zgartirdim» deb o'ylab, hech nima o'zgarmagan bo'lardi.
    """
    with schedule_env() as snap:
        schedule_id = snap.market_a.schedule_id
        ok = await api_client.patch(
            f"{SCHEDULES_URL}/{schedule_id}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )
        rejected = await api_client.patch(
            f"{SCHEDULES_URL}/{schedule_id}",
            json={"times": SLOT_TIMES, "starts_on": _future(market_today)},
            headers=admin_headers,
        )
        after = (await api_client.get(TODAY_URL, headers=admin_headers)).json()

    assert ok.status_code == 200, ok.text
    assert ok.json()["times"] == SLOT_TIMES_WIRE
    assert rejected.status_code == 422, rejected.text
    # Davr o'zgarmagan: profil hamon BUGUNNI qoplaydi.
    assert after["profile"]["mode"] == "active"


async def test_a_past_profile_is_read_only(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    market_today: date,
) -> None:
    """O'TMISHDAGI profil tahrirlanmaydi -> 403 `schedule_not_editable`.

    403 (409 EMAS) — `tariff_past_locked` va `category_period_past_locked`
    bilan bir xil qaror: o'tmish hech kimga ochiq emas, bu HUQUQ
    masalasi. O'tmishdagi profil o'tmishdagi kadrlarni TUSHUNTIRADI va
    uni tahrirlash tarixni yolg'onga aylantirardi.
    """
    with schedule_env() as snap:
        sync_owner_conn.execute(
            _SET_PERIOD,
            (
                market_today - timedelta(days=60),
                market_today - timedelta(days=30),
                str(snap.market_a.schedule_id),
            ),
        )
        response = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "schedule_not_editable"


async def test_only_a_future_profile_can_be_deleted(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """Boshlangan profil -> 403; hali boshlanmagani -> 204 (DL-4).

    Ikkala shox ham bitta testda: faqat rad etishni o'lchaydigan variant
    o'chirish YO'LI umuman ishlamaydigan holatda ham yashil bo'lardi.
    """
    with schedule_env() as snap:
        started = await api_client.delete(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            headers=admin_headers,
        )
        created = await api_client.post(
            SCHEDULES_URL,
            json={"name": "Kelajak", "starts_on": _future(market_today, 45), "times": SLOT_TIMES},
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        assert created.json()["mode"] == "future"
        removed = await api_client.delete(
            f"{SCHEDULES_URL}/{created.json()['id']}",
            headers=admin_headers,
        )

    assert started.status_code == 403
    assert started.json()["detail"] == "schedule_not_editable"
    assert removed.status_code == 204


async def test_a_schedule_change_reaches_the_audit_log_through_the_db_trigger(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """Vaqtlarning o'zgarishi auditda — ILOVA `write_app_audit()` chaqirmasa ham.

    ⚠ DA'VO `source='db_trigger'` NI TALAB QILADI. `source='app'` bo'lsa
      marshrut auditni O'ZI yozgan bo'lardi va har `INSERT` uchun IKKITA
      qator paydo bo'lardi (`security/audit.py` ning 2-faza bo'limidagi
      qoida). Ya'ni bu test ikki narsani birdan qulflaydi: iz BOR va u
      TO'G'RI qatlamdan keladi.
    """
    market_id = two_markets.market_a.id
    with schedule_env() as snap:
        patched = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )
        assert patched.status_code == 200, patched.text
        async with tenant_session(market_id) as session:
            rows = list(
                await session.execute(
                    text(
                        "SELECT source FROM audit_log "
                        " WHERE market_id = :market_id AND table_name = :table_name"
                    ),
                    {"market_id": market_id, "table_name": TABLE_SLOTS},
                )
            )

    assert rows, "vaqtlar o'zgardi, lekin auditda iz yo'q"
    assert {row.source for row in rows} == {"db_trigger"}


async def test_a_foreign_markets_schedule_is_a_404(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """B bozorining profili A bozori admini uchun 404 (T-04-75), 403 EMAS.

    403 o'sha profil MAVJUDLIGINI tasdiqlardi — ya'ni javobning o'zi
    begona bozor haqida ma'lumot berardi.
    """
    with schedule_env() as snap:
        foreign = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_b.schedule_id}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )
        unknown = await api_client.patch(
            f"{SCHEDULES_URL}/{uuid4()}",
            json={"times": SLOT_TIMES},
            headers=admin_headers,
        )

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    # Ikkalasi ham AYNAN bir xil javob beradi — aks holda javob kodining
    # O'ZI «bunday profil bor» degan signalga aylanardi.
    assert foreign.json() == unknown.json()


async def test_the_list_shows_every_profile_with_its_times(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """DL-2 ro'yxati: har profil + vaqtlari + `mode` (o'chirish tugmasi shundan)."""
    with schedule_env() as snap:
        created = await api_client.post(
            SCHEDULES_URL,
            json={"name": "Qishki", "starts_on": _future(market_today, 60), "times": SLOT_TIMES},
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        listed = await api_client.get(SCHEDULES_URL, headers=admin_headers)
        seed_id = snap.market_a.schedule_id

    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    by_id = {UUID(item["id"]): item for item in items}
    assert seed_id in by_id, "seed profili ro'yxatda yo'q"
    assert by_id[seed_id]["mode"] == "active"
    assert by_id[UUID(created.json()["id"])] == created.json()
    for item in items:
        assert item["times"], f"{item['name']!r} profilining vaqtlari bo'sh"


async def test_the_response_never_carries_an_object_key(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    schedule_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """Ombor yuzasi jadval javobida ham YO'Q (§14.3 ning ikkinchi yuzi).

    Jadval kadrga umuman tegmaydi, ya'ni bu test «bir kun kimdir
    qulaylik uchun qo'shib qo'ymasin» darvozasi.
    """
    with schedule_env():
        today = await api_client.get(TODAY_URL, headers=admin_headers)
        listed = await api_client.get(SCHEDULES_URL, headers=admin_headers)

    for response in (today, listed):
        raw = response.text.lower()
        for marker in ("object_key", "x-amz", "presign", ":8333", "seaweed"):
            assert marker not in raw, f"javobda `{marker}` bor"
