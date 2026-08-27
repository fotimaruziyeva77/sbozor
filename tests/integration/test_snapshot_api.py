"""Kun jurnali, kadr detali va RASM PROXYSI (CAM-06, `04-UI-SPEC.md` §6, §14.3).

=============================================================================
BU FAYLNING YURAGI — IKKI ALOHIDA DA'VO, IKKI ALOHIDA TEST.

  1. «Rasm KELADI»    — `image/jpeg` va baytlar ombordagi obyekt bilan bir xil;
  2. «Rasm IZ QOLDIRADI» — `audit_log` da `read`/`snapshots` qatori paydo bo'ladi.

Ular ATAYIN ajratilgan va bu qaror 03-07 da o'lchangan faktdan kelib
chiqadi: bitta testda birlashtirilgan kafolat sabotajda «nimadir
buzildi» deb qizaradi, lekin QAYSI BIRI buzilganini AYTMAYDI. Ajratilgan
holatda esa `audit_read` ni olib tashlash AYNAN ikkinchisini qizartiradi
va birinchisi YASHIL qoladi — ya'ni shaxsiy ma'lumot izining ALOHIDA
o'lchanayotgani shu bilan isbotlanadi.
=============================================================================

⚠⚠ OMBOR MOCK QILINMAYDI. Rasm testlari HAQIQIY SeaweedFS konteyneriga
   yozadi va o'qiydi (`test_storage_layout.py` da o'rnatilgan qoida va
   bir xil sabab): mock ostida S3 imzosi, endpoint kelishuvi va bayt
   yo'lining O'ZI umuman bajarilmaydi — ya'ni «proxy ishlaydi» da'vosi
   isbotsiz qolardi.

⚠ OBYEKT KALITI TESTDA QURILMAYDI — u BAZADAN o'qiladi. Seed uni
  `snapshots.object_key` ustuniga yozgan, ya'ni bazadagi qiymat proxy
  ishlatadigan AYNAN o'sha qiymat. Testda qayta qurish ikkinchi manba
  bo'lardi va kalit tartibi o'zgarganda test emas, MAHSULOT sinishi
  kerak (`test_storage_layout.py` ning qoidasi).
"""

from __future__ import annotations

import pathlib
import re
from contextlib import contextmanager
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.frames import frame_bytes
from fixtures.nvr_domain import nvr_rows
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction, SnapshotTier

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    import httpx
    from app.services.storage import SnapshotStorage
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

CAPTURE_RUNS_URL = "/api/v1/capture-runs"
SNAPSHOTS_URL = "/api/v1/snapshots"
ALERTS_URL = "/api/v1/alerts"

TABLE_SNAPSHOTS = "snapshots"
SNAPSHOT_IMAGE_VIEW = "snapshot_image_view"

_OBJECT_KEY = "SELECT object_key FROM snapshots WHERE id = %s"
_MARK_PURGED = "UPDATE snapshots SET storage_tier = %s, object_deleted_at = now() WHERE id = %s"
_SHIFT_RUNS = "UPDATE capture_runs SET scheduled_at = scheduled_at + %s WHERE market_id = %s"
_SHIFT_SNAPSHOTS = (
    "UPDATE snapshots SET scheduled_at = scheduled_at + %s, captured_at = captured_at + %s "
    " WHERE market_id = %s"
)
_ARCHIVE_CAMERA = "UPDATE cameras SET is_archived = true WHERE id = %s"

STORAGE_SURFACE_MARKERS = ("x-amz", "presign", "seaweed", ":8333", "object_key")
"""Javobda (tana va SARLAVHALARDA) hech qachon uchramasligi kerak bo'lgan satrlar.

`04-UI-SPEC.md` §14.3 va G-4 darvozasining backend tomondagi jufti:
frontend `frontend/src` ni skanerlaydi, bu esa HAQIQIY javobni.
"""


@pytest.fixture
def snapshot_env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> Callable[[], AbstractContextManager[SnapshotDomainSeed]]:
    """`nvr_rows` + `snapshot_rows`, kunlik reja BUGUNGA ko'chirilgan holda.

    =======================================================================
    ⚠ SEED SANASI (2026-09-01) «BUGUN» EMAS — VA UNI KO'CHIRISH MAJBURIY.

    `GET /capture-runs` standart holatda BUGUNGI kunni beradi va
    kelajakdagi kunni RAD ETADI (422). Seedning qadalgan sanasi
    loyihaning O'Z muddati ichida kelajakdan o'tmishga aylanadi, ya'ni
    `?day=2026-09-01` bilan yozilgan test bir kuni 422, boshqa kuni 200
    olardi va shox JIMGINA almashardi.

    Shuning uchun seed qatorlari `scheduled_at` bo'yicha BUGUNGA
    siljitiladi. `business_date` — hisoblanadigan ustun (`GENERATED …
    STORED`), ya'ni u siljish bilan O'ZI ergashadi.
    =======================================================================

    Tartib MUHIM: `snapshot_rows` ning tozalash bloki `nvr_rows` NING
    ICHIDA turishi shart (`test_capture_tick.py` dagi jufti bilan bir xil
    sabab).
    """
    shift = market_today - SEED_BUSINESS_DATE

    @contextmanager
    def _open() -> Iterator[SnapshotDomainSeed]:
        with (
            nvr_rows(sync_owner_conn, two_markets) as nvr,
            snapshot_rows(sync_owner_conn, nvr) as snap,
        ):
            for rows in snap.markets:
                sync_owner_conn.execute(_SHIFT_RUNS, (shift, str(rows.market_id)))
                sync_owner_conn.execute(_SHIFT_SNAPSHOTS, (shift, shift, str(rows.market_id)))
            yield snap

    return _open


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi — `CAMERA_VIEW` bor."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori kassirining sessiyasi — `CAMERA_VIEW` YO'Q."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def inspector_headers(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
) -> dict[str, str]:
    """A bozori NAZORATCHISINING sessiyasi — huquqi AYNAN `OCCUPANCY_REVIEW`.

    ⚠ `two_markets.market_a.cashier_phone` NAQSHI ISHLAMAYDI: nazoratchi
      `two_markets` qatlamida YO'Q, u `auth_seed` da tug'iladi
      (`fixtures/auth_users.py`). Aynan shu fixture RBAC rad etish
      testlari uchun yaratilgan va uning `must_change_password` i `false` —
      ya'ni 403 kelsa sababi HUQUQ, parol darvozasi emas.
    """
    return await session_headers(api_client, auth_seed.inspector.phone, auth_seed.password)


def _object_key(conn: Connection[TupleRow], snapshot_id: UUID) -> str:
    """Kadrning HAQIQIY obyekt kaliti — bazadan (modul docstringining oxirgi ⚠)."""
    row = conn.execute(_OBJECT_KEY, (str(snapshot_id),)).fetchone()
    assert row is not None, f"{snapshot_id} kadri bazada topilmadi"
    return str(row[0])


async def _snapshot_reads(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
) -> list[Any]:
    """`action='read'` + `table_name='snapshots'` yozuvlari — MAHSULOT yo'li bilan."""
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return [row for row in rows if row.table_name == TABLE_SNAPSHOTS]


def _assert_no_storage_surface(response: httpx.Response, label: str) -> None:
    """Javobning TANASIDA ham, SARLAVHALARIDA ham ombor izi yo'q (§14.3).

    ⚠ SARLAVHALAR ALOHIDA TEKSHIRILADI: presigned URL ga o'tishning eng
      tabiiy shakli — `302` + `Location`, ya'ni u javob TANASIDA umuman
      ko'rinmasdi va faqat tanaga qaraydigan darvoza uni o'tkazib
      yuborardi.
    """
    haystacks = [response.text.lower()]
    haystacks += [f"{name.lower()}: {value.lower()}" for name, value in response.headers.items()]
    for marker in STORAGE_SURFACE_MARKERS:
        for haystack in haystacks:
            assert marker not in haystack, f"{label}: javobda `{marker}` bor"


# ---------------------------------------------------------------------------
# Y-1/Y-2 — KUN JURNALI
# ---------------------------------------------------------------------------


async def test_the_day_log_returns_all_six_counters_even_when_zero(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """Oltala hisoblagich HAR DOIM javobda — nol bo'lsa ham (§6.3).

    ⛔ NOL — NATIJA, UNING YO'QLIGI EMAS. Seedda `blank` va `corrupt`
       kadr YO'Q, ya'ni ikkalasi ham `0` bo'lishi kerak — va aynan shu
       ikkitasi `GROUP BY` bilan yig'ilgan variantda javobdan UMUMAN
       tushib qolardi. UI o'shanda «buzuq kadr yo'q» bilan «buzuq kadr
       sanalmagan» ni ajrata olmasdi.
    """
    with snapshot_env():
        response = await api_client.get(CAPTURE_RUNS_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    summary = response.json()["summary"]
    assert set(summary) == {
        "planned",
        "done",
        "ok",
        "dark",
        "blank",
        "corrupt",
        "failed",
        "missed",
    }
    # Seed rejasi (`A_RUN_PLAN`): 2 `succeeded` (`ok` + `dark`), 1 `failed`,
    # 1 `missed`, hamda `pending`/`running`/`skipped`.
    assert summary["ok"] == 1
    assert summary["dark"] == 1
    assert summary["failed"] == 1
    assert summary["missed"] == 1
    assert summary["blank"] == 0
    assert summary["corrupt"] == 0
    assert summary["planned"] == 7


async def test_the_day_log_can_express_absence(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """`missed` — QATOR BOR, urinish YO'Q (§6.4 C6, SC#2).

    =======================================================================
    ⛔ BU FAYLDAGI ENG MAHSULOTGA YAQIN DA'VO.

    Jurnal NIMA SODIR BO'LGANINI emas, NIMA SODIR BO'LMAGANINI ham
    ifodalashi kerak. Faqat natijalarni qaytaradigan javob shakli
    o'tkazib yuborilgan slotni UMUMAN ko'rsata olmasdi — hujayra bo'sh
    chizilardi va bo'shliq «ko'radigan narsa yo'q» degan ma'no berardi.

    `missed` va `failed` FARQI ham shu yerda o'lchanadi: birinchisi
    «bizning tizimimiz ishlamadi» (`attempts == 0`), ikkinchisi «NVR
    javob bermadi» (`attempts > 0`). Ular operatsion jihatdan butunlay
    boshqa va bir xil ko'rinishi dala diagnostikasini o'ldirardi.
    =======================================================================
    """
    with snapshot_env():
        response = await api_client.get(CAPTURE_RUNS_URL, headers=admin_headers)

    rows = response.json()["rows"]
    missed = [row for row in rows if row["status"] == "missed"]
    failed = [row for row in rows if row["status"] == "failed"]

    assert missed, "yo'qlik yozuvi javobda umuman yo'q — SC#2 ifodalanmaydi"
    assert missed[0]["attempts"] == 0, "`missed` urinish bo'lmagan holat"
    assert missed[0]["snapshot_id"] is None
    assert failed, "nazorat holati yo'q — `missed` ni nimadan ajratamiz?"
    assert failed[0]["attempts"] > 0, "`failed` urinish BO'LGAN holat"
    # To'qqizala hujayra holatini chizish uchun UI'ga yetadigan ma'lumot.
    assert {row["status"] for row in rows} >= {
        "succeeded",
        "failed",
        "missed",
        "pending",
        "running",
        "skipped",
    }


async def test_the_day_log_is_ordered_by_channel_number(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """Qatorlar `channel_no` bo'yicha O'SISH tartibida — `/cameras` bilan bir xil.

    Frontend qayta saralamaydi (§6.4): ikki ekranda ikki xil tartib
    admin uchun «bu o'sha kameramiykin?» savolini tug'dirardi.
    """
    with snapshot_env():
        response = await api_client.get(CAPTURE_RUNS_URL, headers=admin_headers)

    channels = [row["channel_no"] for row in response.json()["rows"]]
    assert channels == sorted(channels), f"tartib buzilgan: {channels}"


async def test_an_archived_camera_is_hidden_but_its_existence_is_announced(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Arxivlangan kamera `rows` da YO'Q, lekin `archived_present` BOR (§6.4).

    ⚠ IKKI ASSERTION BIR TESTDA: «yashirildi» yolg'iz o'zi bayroq
      umuman yo'q bo'lganda ham rost bo'lardi va admin «kecha 25 kamera
      bor edi, bugun 24» farqini NOSOZLIK deb o'ylardi.
    """
    with snapshot_env() as snap:
        before = await api_client.get(CAPTURE_RUNS_URL, headers=admin_headers)
        assert before.json()["archived_present"] is False, (
            "nazorat holati buzildi — seedda arxivlangan kameraning qatori bor"
        )
        archived_camera = UUID(before.json()["rows"][0]["camera_id"])
        sync_owner_conn.execute(_ARCHIVE_CAMERA, (str(archived_camera),))
        after = await api_client.get(CAPTURE_RUNS_URL, headers=admin_headers)
        _ = snap

    body = after.json()
    assert body["archived_present"] is True
    assert all(UUID(row["camera_id"]) != archived_camera for row in body["rows"])


async def test_a_future_day_is_refused(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """Kelajakdagi kun -> 422, bo'sh jurnal EMAS (§6.3).

    Ertangi reja hali materializatsiya qilinmagan, ya'ni bo'sh javob
    «bugun hech narsa olinmadi» degan YOLG'ON SIGNAL bilan bir xil
    ko'rinardi — va u aynan mahsulot izlayotgan anomaliya bilan
    chalkashardi.
    """
    tomorrow = (market_today + timedelta(days=1)).isoformat()
    with snapshot_env():
        response = await api_client.get(
            CAPTURE_RUNS_URL, params={"day": tomorrow}, headers=admin_headers
        )

    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Y-3 — KADR DETALI
# ---------------------------------------------------------------------------


async def test_the_snapshot_detail_carries_measurements_but_no_object_key(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """O'lchovlar BOR, ombor kaliti YO'Q (§14.3 va D-15).

    Ikki tomon bitta testda ATAYIN: faqat `object_key` yo'qligini
    tekshiradigan variant javob BUTUNLAY bo'sh bo'lganda ham yashil
    bo'lardi.
    """
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        response = await api_client.get(f"{SNAPSHOTS_URL}/{snapshot_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "object_key" not in body
    for field in ("quality_mean", "quality_stddev", "quality_thresholds_version"):
        assert field in body, f"`{field}` javobda yo'q — D-15 ning o'lchovlari yo'qoldi"
    assert body["quality_verdict"] == "ok"
    assert body["is_billable"] is True
    _assert_no_storage_surface(response, "kadr detali")


async def test_a_foreign_markets_snapshot_is_a_404(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """B bozorining kadri va MAVJUD BO'LMAGAN kadr — bayt-bayt bir xil 404.

    Farqli javob (masalan 403) o'sha kadr MAVJUDLIGINI tasdiqlardi va
    javobning O'ZI enumeration signali bo'lardi (T-04-75).
    """
    with snapshot_env() as snap:
        foreign_id = snap.market_b.snapshot_ids[0]
        foreign = await api_client.get(f"{SNAPSHOTS_URL}/{foreign_id}", headers=admin_headers)
        unknown = await api_client.get(f"{SNAPSHOTS_URL}/{uuid4()}", headers=admin_headers)
        foreign_image = await api_client.get(
            f"{SNAPSHOTS_URL}/{foreign_id}/image", headers=admin_headers
        )

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert foreign.json() == unknown.json()
    assert foreign_image.status_code == 404


# ---------------------------------------------------------------------------
# §14.3 — RASM PROXYSI. HAQIQIY OMBOR, MOCK YO'Q.
# ---------------------------------------------------------------------------


async def test_the_image_arrives_as_jpeg_through_the_proxy(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    s3_client: SnapshotStorage,
) -> None:
    """Baytlar ombordan core-api ORQALI keladi — va ular AYNAN o'sha baytlar.

    ⚠ DA'VO STATUS KODIDA EMAS, BAYTLARDA (03-14 metodikasi): 200 +
      bo'sh tana ham «ishladi» ko'rinardi. Yozilgan JPEG bilan
      qaytarilgan tananing TENGLIGI proxy zanjirining har bo'g'inini
      (ombor -> klient -> `StreamingResponse`) qamraydi.
    """
    payload = frame_bytes(mean=120, stddev=45)
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        key = _object_key(sync_owner_conn, snapshot_id)
        await s3_client.put(key, payload)
        try:
            response = await api_client.get(
                f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=admin_headers
            )
        finally:
            await s3_client.delete_many([key])

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == payload
    # Kesh sessiyadan tashqariga chiqmaydi — kadr shaxsiy ma'lumot.
    assert response.headers["cache-control"] == "private, no-store"
    _assert_no_storage_surface(response, "rasm proxysi")


async def test_reading_the_image_leaves_an_audit_row(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    s3_client: SnapshotStorage,
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """Dalil-kadrning O'QILISHI `audit_log` ga tushadi (§6.6 `[TALAB]`, D-09).

    =======================================================================
    ⛔ BU TEST PRESIGNED URL NING RAD ETILISH SABABINI O'LCHAYDI.

    Imzolangan havola berilganda bu qator PAYDO BO'LMASDI: havola
    muddati tugagunicha ombordan to'g'ridan-to'g'ri o'qilardi va
    core-api uni umuman ko'rmasdi. Nizo paytida «kim bu kadrni ko'rdi?»
    savoli javobsiz qolardi.

    Yuqoridagi «baytlar keladi» testidan ALOHIDA: sabotajda `audit_read`
    ni olib tashlash AYNAN shu testni qizartiradi va u YASHIL qoladi.
    =======================================================================
    """
    market_id = two_markets.market_a.id
    payload = frame_bytes(mean=120, stddev=45)
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        key = _object_key(sync_owner_conn, snapshot_id)
        await s3_client.put(key, payload)
        try:
            before = await _snapshot_reads(tenant_session, market_id)
            response = await api_client.get(
                f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=admin_headers
            )
            after = await _snapshot_reads(tenant_session, market_id)
        finally:
            await s3_client.delete_many([key])

    assert response.status_code == 200, response.text
    assert len(after) == len(before) + 1, "kadr o'qildi, lekin jurnalda iz qolmadi"
    row = after[-1]
    assert row.new_value["reason"] == SNAPSHOT_IMAGE_VIEW
    assert row.new_value["filters"]["snapshot_id"] == str(snapshot_id)


async def test_a_role_without_camera_view_is_refused_and_leaves_no_audit_row(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """403 VA jurnalda YOLG'ON DALIL yo'q — huquq darvozasi audit'dan OLDIN.

    =======================================================================
    ⛔ DA'VO O'LCHANADI, MEXANIZM EMAS.

    «Huquq dekoratorda e'lon qilinganmi?» degan test 03-07 da sabotajda
    HECH NIMANI qizartirmagan: kafolatning ikki mustaqil manbai bor
    (dekorator tartibi VA fon vazifasining faqat muvaffaqiyatli javobga
    biriktirilishi) va ikkinchisi uni yolg'iz ham ushlab turadi.

    Bu test esa NATIJANI o'lchaydi: ko'rmagan odam jurnalda ko'rgan
    bo'lib turmaydi. Da'vo har ikkala mexanizmdan ham mustaqil.
    =======================================================================
    """
    market_id = two_markets.market_a.id
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        before = await _snapshot_reads(tenant_session, market_id)
        response = await api_client.get(
            f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=cashier_headers
        )
        after = await _snapshot_reads(tenant_session, market_id)

    assert response.status_code == 403
    assert len(after) == len(before), (
        "rad etilgan so'rov `audit_log` ga o'qish qatori yozdi — jurnalda "
        "YOLG'ON DALIL qoldi (ko'rmagan odam ko'rgan bo'lib turibdi)"
    )


# ---------------------------------------------------------------------------
# 05-15 — DALIL-KADR DARVOZASINING KENGAYISHI VA UNING CHEGARASI
# ---------------------------------------------------------------------------


async def test_a_pure_inspector_can_open_the_evidence_frame(
    api_client: httpx.AsyncClient,
    inspector_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    s3_client: SnapshotStorage,
) -> None:
    """SOF `inspector` (huquqi AYNAN `OCCUPANCY_REVIEW`) kadrni OLADI.

    =======================================================================
    ⛔ 5-FAZANING YOPILISH SHARTI — VA U UCH REJADA OCHIQ TURGAN.

    05-10 bo'shliqni topdi, 05-11 uni yozdi, 05-13 QAYTA O'LCHADI: navbat
    bandini nazoratchi oladi, DALILNI esa 403 bilan ololmasdi. Fazaning
    mezonlari («nazoratchi ko'r audit navbatida AI javobini KO'RMASDAN
    zonalarni BAHOLAYDI») rasmni ko'rishga tayanadi, ya'ni ekranning
    asosiy boshqaruvi o'z foydalanuvchisida ishlamas holda faza yopilib
    bo'lmasdi.

    ⚠ DA'VO STATUS KODIDA EMAS, BAYTLARDA (yuqoridagi proxy testining
      metodikasi): 200 + bo'sh tana ham «ishladi» ko'rinardi, va aynan
      shu holat nazoratchining ekranida oq to'rtburchak bo'lib chiqardi.

    ⚠ FOYDALANUVCHI TANLOVI YUK KO'TARADI: `auth_seed.inspector` ning
      roli AYNAN BITTA (`inspector`) va `must_change_password = false`.
      Ikkinchisi shart — `must_change` egasi 403 `password_change_required`
      olardi va test «huquq berildi» ni emas, parol darvozasini
      o'lchardi (`fixtures/auth_users.py` dagi `must_change` docstringi).
    =======================================================================
    """
    payload = frame_bytes(mean=118, stddev=41)
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        key = _object_key(sync_owner_conn, snapshot_id)
        await s3_client.put(key, payload)
        try:
            response = await api_client.get(
                f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=inspector_headers
            )
        finally:
            await s3_client.delete_many([key])

    assert response.status_code == 200, (
        f"sof `inspector` dalil kadrini ololmadi ({response.status_code}) — "
        "noaniq navbat va ko'r audit ekranlari o'z foydalanuvchisida ISHLAMAYDI"
    )
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == payload, (
        "javob 200 berdi, lekin baytlar mos emas — darvoza ochildi-yu, proxy "
        "zanjiri nazoratchi uchun boshqacha ishlayapti"
    )


async def test_the_inspector_gate_stops_at_the_frame(
    api_client: httpx.AsyncClient,
    inspector_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    market_today: date,
) -> None:
    """NAZORAT — o'sha nazoratchi kadr METAMA'LUMOTINI va kun jurnalini OLMAYDI.

    =======================================================================
    ⛔ BU TEST YUQORIDAGISIZ MA'NOSIZ, YUQORIDAGISI ESA BUSIZ XAVFLI.

    «Nazoratchi rasmni ko'rsin» so'rovining eng oson bajarilishi —
    `ROLE_PERMISSIONS[INSPECTOR]` ga `CAMERA_VIEW` qo'shish yoki
    `SnapshotViewerDep` ni bo'shatish edi. Ikkalasi ham yuqoridagi testni
    YASHIL qilardi va ikkalasi ham nazoratchiga butun kadr arxivini,
    kun jurnalini va alert oqimini ochardi.

    Bu yerdagi savol shuning uchun boshqa: «kengayish QAYERDA TO'XTADI?»
    Struktura darvozasi (`tests/tenancy/test_personal_data_coverage.py::
    test_the_evidence_frame_widening_stops_at_the_image_route`) buni
    marshrut grafida o'lchaydi; bu yerda XULQ o'lchanadi va ikkalasi
    mustaqil.
    =======================================================================
    """
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        detail = await api_client.get(f"{SNAPSHOTS_URL}/{snapshot_id}", headers=inspector_headers)
        day_log = await api_client.get(
            CAPTURE_RUNS_URL, params={"day": market_today.isoformat()}, headers=inspector_headers
        )

    assert detail.status_code == 403, (
        f"nazoratchi kadr METAMA'LUMOTINI oldi ({detail.status_code}) — kengayish "
        "dalil-kadr marshrutidan tashqariga oqib ketgan"
    )
    assert day_log.status_code == 403, (
        f"nazoratchi KUN JURNALINI oldi ({day_log.status_code}) — u kuzatuv "
        "yuzasining hisobot qismi va nazoratchining ishiga kirmaydi"
    )


async def test_a_request_that_fails_after_the_audit_dependency_leaves_no_row(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    two_markets: TwoMarketSeed,
) -> None:
    """IKKINCHI MEXANIZM — fon vazifasi FAQAT muvaffaqiyatli javobga biriktiriladi.

    =======================================================================
    ⛔ BU TEST YUQORIDAGI 403 TESTINING TAKRORI EMAS — U BOSHQA MEXANIZMNI
       O'LCHAYDI, VA U SABOTAJ BILAN O'LCHANGANDAN KEYIN QO'SHILDI.

    O'lchov (04-09): huquqni dekoratordan olib, imzoda `intent` DAN
    KEYINGA surish HECH NIMANI qizartirmadi. Sabab — `audit_read`
    kafolatining IKKI mustaqil manbai bor va ikkinchisi uni YOLG'IZ ham
    ushlab turadi: yozuv `BackgroundTasks` orqali ketadi, u esa faqat
    MUVAFFAQIYATLI qaytgan javobga biriktiriladi. 403 da FastAPI yangi
    javob quradi va unda fon vazifasi umuman yo'q.

    Ya'ni 403 testi o'sha ikkinchi mexanizm tufayli yashil qolaveradi va
    u YOLG'IZ o'zi birinchi mexanizmni (dekorator tartibi) o'lchay
    olmaydi. Bu test esa IKKINCHISINI to'g'ridan-to'g'ri o'lchaydi:
    so'rov `audit_read` dan O'TIB, keyin 410 bilan yiqiladi — va jurnal
    baribir bo'sh qoladi.

    Buzilishi uchun BITTA o'zgarish yetadi: agar kimdir `audit_read` ni
    `BackgroundTasks` dan olib, endpoint ichida `await` bilan yozsa, bu
    test qizaradi va 403 testi YASHIL qoladi. Ikkalasi birga butun
    kafolatni qamraydi.
    =======================================================================

    MAHSULOT DA'VOSI: `purged` kadrni so'ragan odam HECH NIMANI
    KO'RMAGAN — obyekt allaqachon o'chirilgan. Uni jurnalda «kadrni
    ko'rdi» deb yozish nizo paytida YOLG'ON DALIL bo'lardi.
    """
    market_id = two_markets.market_a.id
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        sync_owner_conn.execute(_MARK_PURGED, (SnapshotTier.PURGED.value, str(snapshot_id)))
        before = await _snapshot_reads(tenant_session, market_id)
        response = await api_client.get(
            f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=admin_headers
        )
        after = await _snapshot_reads(tenant_session, market_id)

    assert response.status_code == 410, response.text
    assert len(after) == len(before), (
        "410 bilan tugagan so'rov jurnalga «kadr ko'rildi» qatorini yozdi — "
        "fon vazifasi muvaffaqiyatsiz javobga ham biriktirilyapti"
    )


async def test_a_purged_object_is_gone_not_missing(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """`storage_tier='purged'` -> 410, 500 ham 404 ham EMAS (D-18).

    410 «bor edi, 455 kun o'tdi» deydi; 404 esa «bunday kadr bo'lmagan»
    deb operatorni yo'qolgan dalilni qidirishga yuborardi. Ombor
    chaqiruvi UMUMAN qilinmaydi — qator holatining o'zi javob beradi.

    ⚠ Kadr DETALI esa hamon 200 qaytaradi: metama'lumot joyida va UI
      rasm o'rniga sababni chizadi.
    """
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        sync_owner_conn.execute(_MARK_PURGED, (SnapshotTier.PURGED.value, str(snapshot_id)))
        image = await api_client.get(f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=admin_headers)
        detail = await api_client.get(f"{SNAPSHOTS_URL}/{snapshot_id}", headers=admin_headers)

    assert image.status_code == 410, image.text
    assert image.json()["detail"] == "snapshot_object_purged"
    assert detail.status_code == 200
    assert detail.json()["storage_tier"] == "purged"


async def test_an_unreachable_object_is_a_503_not_a_500(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """Ombor obyektni topa olmasa -> 503 tanilgan kod bilan, xom istisno EMAS.

    Kadr qatori BOR, obyekt esa yo'q (ombor tozalandi, migratsiya
    tugallanmadi yoki tarmoq uzildi). Bu holat 500 bo'lsa admin «tizim
    buzildi» degan xulosaga kelardi — holbuki bitta kadr yetib
    kelmayapti va qolgan hamma narsa ishlayapti.

    ⚠ Obyekt ATAYIN yozilmaydi: seed faqat BAZAGA yozadi, omborga emas.
      Ya'ni bu stsenariy sun'iy emas — u seedning tabiiy holati.
    """
    with snapshot_env() as snap:
        snapshot_id = snap.market_a.snapshot_ids[0]
        response = await api_client.get(
            f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=admin_headers
        )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "snapshot_storage_unavailable"
    _assert_no_storage_surface(response, "ombor javob bermadi")


# ---------------------------------------------------------------------------
# Y-4 — OGOHLANTIRISHLAR
# ---------------------------------------------------------------------------


async def test_open_and_closed_alerts_are_separate_lists(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
) -> None:
    """`?closed=0` ochiqlarni, `?closed=1` yopilganlarni beradi (§6.7).

    Bitta ro'yxatda kelsa admin o'nlab yopilgan qator orasidan
    ochiqlarini qidirishga majbur bo'lardi va D-22 ning alert
    charchashi UI tomonda qaytardi.
    """
    with snapshot_env() as snap:
        open_list = await api_client.get(ALERTS_URL, headers=admin_headers)
        closed_list = await api_client.get(
            ALERTS_URL, params={"closed": "1"}, headers=admin_headers
        )
        rows = snap.market_a

    open_ids = {UUID(item["id"]) for item in open_list.json()["items"]}
    closed_ids = {UUID(item["id"]) for item in closed_list.json()["items"]}

    assert rows.open_alert_id in open_ids
    assert rows.open_alert_id not in closed_ids
    assert rows.resolved_alert_id in closed_ids
    assert rows.resolved_alert_id not in open_ids
    # `notified_at` `null` bo'lsa ham MAYDON JAVOBDA — «yuborilmadi»
    # qatori aynan shundan chiziladi va u yashirilmaydi.
    assert all("notified_at" in item for item in open_list.json()["items"])


async def test_an_unknown_detail_key_never_reaches_the_response(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    snapshot_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """`detail` ALLOWLIST bilan filtrlanadi — noma'lum kalit TASHLANADI (T-04-74).

    ⚠ NAZORAT BANDI MAJBURIY: faqat «noma'lum kalit yo'q» ni
      tekshiradigan test `detail` BUTUNLAY bo'sh qaytganda ham yashil
      bo'lardi va allowlist emas, blokirovka o'lchangan bo'lardi.
    """
    with snapshot_env() as snap:
        sync_owner_conn.execute(
            "UPDATE alert_events SET detail = %s::jsonb WHERE id = %s",
            (
                '{"camera_count": 22, "rtsp_password": "SIR", "object_key": "a/b.jpg"}',
                str(snap.market_a.open_alert_id),
            ),
        )
        response = await api_client.get(ALERTS_URL, headers=admin_headers)
        alert_id = snap.market_a.open_alert_id

    item = next(row for row in response.json()["items"] if UUID(row["id"]) == alert_id)
    assert item["detail"] == {"camera_count": 22}, (
        "allowlist ishlamadi yoki u haddan tashqari tor (nazorat kaliti ham yo'qoldi)"
    )
    _assert_no_storage_surface(response, "ogohlantirishlar")


# ---------------------------------------------------------------------------
# MEXANIK DARVOZALAR — MANBA MATNI USTIDA
# ---------------------------------------------------------------------------


def test_the_router_never_calls_the_presigned_url_api() -> None:
    """`boto3` ning imzolangan-havola API'si bu faylda CHAQIRILMAGAN (§14.3).

    ⚠ DARVOZA IZOHLARNI FILTRLAMAYDI va u shunday BO'LISHI KERAK:
      `generate_presigned` va `presigned_url` — API NOMLARI, taqiq
      MATNI esa «presigned URL berilmaydi» deb yozilgan, ya'ni ular
      bir-biriga tegmaydi. Modul docstringi taqiqni to'liq tushuntira
      oladi va darvoza baribir ishlaydi.
    """
    source = pathlib.Path("services/core-api/app/api/v1/snapshots.py").read_text(encoding="utf-8")

    assert "generate_presigned" not in source
    assert "presigned_url" not in source
    assert "audit_read" in source, "rasm marshrutining audit izi e'lon qilinmagan"


def test_no_manual_alert_close_route_exists() -> None:
    """`PATCH`/`POST`/`DELETE /alerts` marshruti UMUMAN yo'q (T-04-73).

    Ogohlantirishni faqat TIKLANISH yopadi. Qo'lda yopish tugmasi
    adminga muammoni KO'RMASDAN yashirish imkonini berardi.

    ⚠ IZOH QATORLARI FILTRLANADI: taqiqning O'ZI docstringda
      `PATCH`/`POST`/`DELETE /alerts` shaklida yozilgan va filtrsiz
      darvoza o'z hujjatini buzilish deb belgilagan bo'lardi.
    """
    source = pathlib.Path("services/core-api/app/api/v1/snapshots.py").read_text(encoding="utf-8")
    body = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))

    assert not re.search(r"(patch|post|delete)\(\s*[\"']/alerts", body, re.IGNORECASE)
    assert not re.search(r"alerts_router\.(patch|post|delete)", body, re.IGNORECASE)
