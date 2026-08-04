"""Fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular o'z egasida qoladi:

  * `test_capture_repo.py`     (04-05) — `ensure_plan` / `claim_due` / lease;
  * `test_schedule_repo.py`    (04-05) — davr semantikasi va qoplanmagan kunlar;
  * `test_capture_tick.py`     (04-07) — tikning orkestratsiyasi va fan-out;
  * `test_snapshot_quality.py` (04-07) — sifat filtrining uchidan-uchiga oqimi;
  * `test_storage_layout.py`   (04-06) — kalit tartibi va prefiks izolyatsiyasi;
  * `test_retention.py`        (04-08) — siqish va arxivdan chiqarish mexanikasi;
  * `test_alerting.py`         (04-08) — guruhlash, debounce, eskalatsiya;
  * `test_capture_schedule.py` / `test_snapshot_api.py` (04-09) — HTTP yuzasi.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da yozilgan
jumla bugun rostmi?** Har test docstringi mezon matnini SO'ZMA-SO'Z olib
yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik ko'zga tashlanadi.

Mavjud testlar MEXANIZMNI o'lchaydi (`ensure_plan` idempotentmi, `claim_due`
lease qaytaradimi). Bu yerdagilar MAHSULOT DA'VOSINI o'lchaydi: admin
tugmani bosgandan keyin ertangi kunda AYNAN o'sha slotlar tug'iladimi.
=============================================================================

UCHTA DARVOZA VA UCHALASI HAM MUSTAQIL:

  1. **Mezon boshiga bitta test** — `test_sc1_`…`test_sc5_`, boshqasi yo'q.
  2. **Meta-test** — mezonlardan biri JIMGINA tushib qolmasin. Fayl qayta
     tashkil qilinganda yoki test vaqtincha o'chirilganda darvoza baribir
     yashil bo'lardi va «beshala mezon o'lchanadi» da'vosi ISBOTSIZ
     qolardi. Meta-testning O'Z nomida `sc<raqam>` YO'Q va bu ataylab:
     qabul mezoni `--collect-only` chiqishida `sc[1-5]` naqshini SANAYDI.
  3. **Mock'siz o'lchov** — S3 ham, kadr olish ham HAQIQIY konteynerda.

=============================================================================
⚠ UCHINCHI DARVOZANING SABABI O'LCHANGAN, FARAZGA TAYANMAYDI.

03-14 da jonli ko'rish zanjirining oxirgi bo'g'ini «qulaylik uchun»
almashtirilgan edi va to'plam yashil turardi; birinchi MOCK'SIZ o'lchov
esa media umuman oqmasligini ochdi. Ombor tomonida yashirinadigan qatlam
undan ham kattaroq: imzolash, endpoint kelishuvi va sahifalash semantikasi
almashtirilgan qatlamda UMUMAN bajarilmaydi — ya'ni birinchi «qulaylik
uchun» qo'yilgan S3 o'rnini bosuvchi butun imzolash yo'lini o'lchanmagan
qoldirardi. Taqiqlangan kutubxonalar ro'yxati docstringda EMAS,
`_MOCK_ROOTS` konstantasida yashaydi: matnda sanalgan ro'yxat o'z izohida
o'zini topib, darvozani hech qachon yashil qilmasdi.

⚠ `respx` BU QOIDANING ISTISNOSI VA U TOR: u FAQAT Telegram kontrakti
  uchun. Telegram — tashqi xizmat va unga haqiqiy so'rov yuborish testni
  HAQIQIY BOT TOKENIGA bog'lardi; o'lchanadigan narsa esa HTTP
  SHARTNOMASI (nechta so'rov, qaysi yo'lga, tanasida nima bor). Istisno
  `telegram_calls` fixture'i bilan NOMLANGAN va uni so'raydigan test
  AYNAN BITTA bo'lishi darvozada tekshiriladi.
=============================================================================
"""

from __future__ import annotations

import ast
import importlib
import inspect
import io
import json
import sys
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
import respx
from app.jobs.alerting import BACKUP_COMPONENT, alert_sweep
from app.jobs.capture import CapturePolicy, capture_batch, capture_tick
from app.jobs.retention import RETENTION_COMPONENT, RetentionPolicy, retention_daily
from app.repositories.capture_repo import CaptureRepository
from app.repositories.nvr_repo import NvrRepository
from app.security.secrets import encrypt_nvr_password
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD, AlertSender
from app.services.frame_source import FrameSourcePool
from app.services.object_key import KEY_PREFIX_FOR_DAY, object_key
from app.services.quality import QualityThresholds
from fixtures.admin_api import session_headers
from fixtures.frames import frame_bytes
from fixtures.nvr_domain import nvr_rows
from fixtures.nvr_sim import sim_patch
from fixtures.snapshot_domain import snapshot_rows
from PIL import Image
from pydantic import SecretStr
from sbozor_core.enums import (
    ActorKind,
    CaptureMethod,
    CaptureRunStatus,
    SnapshotLightMode,
    SnapshotQuality,
    SnapshotTier,
)
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import MARKET_TZ
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator
    from contextlib import AbstractContextManager

    from app.services.storage import SnapshotStorage
    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import MarketNvrRows
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

_MODULE_PATH = Path(__file__)

SCHEDULES_URL = "/api/v1/snapshot-schedules"
CAPTURE_RUNS_URL = "/api/v1/capture-runs"

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
        # `min_bytes` PASAYTIRILGAN va sabab `test_snapshot_quality.py` ning
        # modul docstringida o'lchangan: simulyator kadri 320x180 (2 927
        # bayt) va u yetkazilgan 4 096 baytlik pol ostida qoladi. Yetkazilgan
        # pol bilan bu yerdagi test SIFAT QOIDASINI emas, o'lcham polini
        # o'lchagan bo'lardi. Polning O'Z testi `tests/unit/test_quality_
        # filter.py` da va u standart qiymat bilan ishlaydi.
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

SEASONAL_TIMES = ["05:45", "10:15", "17:30"]
"""SC#1 ning «mavsumiy profil bilan, 7 ta qotib qolgan vaqt emas» qismi.

Uchta vaqt ATAYIN: standart profil YETTITA slot beradi, ya'ni sanoqning
o'zi «qotib qolgan yettilik almashdimi?» degan savolga javob beradi. Uchala
qiymat ham standart ro'yxatda YO'Q va buni test o'zi tekshiradi — aks holda
tasodifan mos tushgan vaqt da'voni jimgina bo'shatardi.
"""

SEASONAL_SLOTS: tuple[time, ...] = tuple(time.fromisoformat(value) for value in SEASONAL_TIMES)

GO2RTC_URL = "http://go2rtc:1984"
"""Kadr-manba puli uni TALAB qiladi, lekin SC#3 da usul — qurilma yo'li."""

TELEGRAM_SEND_URL_PATTERN = rf"{TELEGRAM_API_BASE}/bot.*/{TELEGRAM_SEND_METHOD}"

FRAME_SIZE = (1280, 720)
ORIGINAL_QUALITY = 92
"""SC#4 ning zond kadri ATAYIN yuqori sifat bilan yoziladi.

Siyosatning standarti 60, ya'ni 92 -> 60 qayta kodlash hajmni ANIQ
kamaytiradi. Teng sifat bilan yozilgan kadr uchun natija noaniq bo'lardi va
test «siqish ishladimi?» savoliga o'z farazi bilan javob berardi.
"""

COMPRESS_ONLY = RetentionPolicy(
    full_days=0,
    compressed_days=365,
    jpeg_quality=60,
    batch_size=200,
)
"""«90 kun to'liq» chegarasi SOZLAMA, vaqt esa ARGUMENT (`today=`).

Ikkalasi ham mahsulot yo'lidagi haqiqiy parametrlar, ya'ni 90 kunni kutmasdan
MEXANIZM isbotlanadi. ⚠ Siyosatning 90 kalendar kun davomida ishlab turishi
bu yerda ISBOTLANMAYDI — u `04-VALIDATION.md` ning Manual-Only bandi, egasi
Ops. Bu faylni «90 kunlik siyosat sinaldi» deb o'qish XATO bo'lardi.
"""

_MOCK_ROOTS = frozenset({"moto", "unittest", "mock", "aioresponses", "botocore"})
"""Bu modulda import qilinishi TAQIQLANGAN paket ildizlari.

⚠ Ro'yxat KOD ichida, docstringda emas — aks holda darvoza o'z izohida
  o'zini topib, hech qachon yashil bo'lmasdi.

⚠ `respx` bu ro'yxatda YO'Q va bu ataylab: u Telegram kontrakti uchun
  ruxsat etilgan yagona vosita. Uning TORLIGI boshqa darvoza bilan
  o'lchanadi — `telegram_calls` ni so'raydigan test AYNAN BITTA.
"""

_MOCK_NAMES = frozenset({"Stubber", "patch", "MagicMock", "AsyncMock", "mock_aws"})
"""Ildiz darajasida tutilmaydigan nomlar — ruxsat etilgan paketlar ichida yashaydi."""

TELEGRAM_FIXTURE = "telegram_calls"
"""`respx` istisnosining YAGONA nomi — darvoza uni imzolarda SANAYDI.

Qiymat shu modulda HAQIQATAN fixture ekani darvozaning o'zida tekshiriladi,
ya'ni fixture qayta nomlanganda darvoza jimgina bo'sh naqsh izlab qolmaydi.
"""

OBSERVABILITY_MODULE = "app.observability"
"""Sentry ilmoqlarining YAGONA uyi — SC#5 ning ikkinchi yarmi shu yerdan o'lchanadi.

Nomi SHU YERDA yagona joyda turadi. ⚠ Modul LAZY import qilinadi (`importlib`)
va bu ataylab: modul yo'q bo'lishi AYNAN o'lchanayotgan nosozlik: yuqorida
yozilgan `import` esa butun faylning yig'ilishini yiqitib, QAYSI da'vo
buzilganini yashirardi. `test_phase3_criteria.py` ning mock'siz o'lchov
darvozasi bilan bir xil naqsh va bir xil sabab.
"""

SENTRY_ENTRYPOINTS: tuple[tuple[str, str], ...] = (
    ("app.main", "lifespan"),
    ("app.worker", "_open_worker_resources"),
)
"""Sentry o'rnatilishi SHART bo'lgan jarayon kirish nuqtalari.

⚠ IKKITA, BITTA EMAS — VA SHU FARQ SC#5 NING IKKINCHI YARMI. Kadr olish,
saqlash siyosati va alert supurgisi WORKER jarayonida ishlaydi; API
jarayoni ularning istisnolarini UMUMAN ko'rmaydi. Faqat API'da o'rnatilgan
Sentry bilan «xato Sentry'da ko'rinadi» da'vosi aynan bu fazaning
xatolari uchun YOLG'ON bo'lardi va nosozlik faqat konteyner jurnalida
qolardi.
"""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, locked_until, locked_by, error_code, capture_method, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)"
)

_INSERT_SNAPSHOT = (
    "INSERT INTO snapshots "
    "(id, market_id, capture_run_id, camera_id, scheduled_at, captured_at, slot_time, "
    " object_key, size_bytes, quality_verdict, quality_mean, quality_stddev, "
    " quality_thresholds_version, light_mode, capture_method, storage_tier, width, height) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_SNAPSHOT_STATE = (
    "SELECT storage_tier, size_bytes, object_key, object_deleted_at FROM snapshots WHERE id = %s"
)

_WIDEN_SCHEDULE = "UPDATE snapshot_schedules SET period = daterange(%s, NULL, '[)') WHERE id = %s"

_CREATE_BILLING_CHILD = """
CREATE TABLE criteria_occupancy_probe (
    id                   uuid PRIMARY KEY DEFAULT uuidv7(),
    snapshot_id          uuid NOT NULL,
    snapshot_is_billable boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_criteria_occupancy_probe_billable CHECK (snapshot_is_billable),
    CONSTRAINT fk_criteria_occupancy_probe_snapshot
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
        REFERENCES snapshots (id, is_billable)
)
"""
_DROP_BILLING_CHILD = "DROP TABLE IF EXISTS criteria_occupancy_probe"
_INSERT_BILLING_CHILD = "INSERT INTO criteria_occupancy_probe (snapshot_id) VALUES (%s)"

_HEARTBEAT_UPSERT = (
    "INSERT INTO system_heartbeats (component, last_seen_at) VALUES (%s, %s) "
    "ON CONFLICT (component) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at"
)
_HEARTBEAT_DROP = "DELETE FROM system_heartbeats WHERE component = %s"

TELEGRAM_TOKEN = "1234567890:CRITERIA-TOKEN-NEVER-REAL"  # noqa: S105 - qalbaki
TELEGRAM_CHAT = "-1009876543210"

DEAD_WORKER = "o'lgan-worker"
"""Uzilib qolgan jarayonning ijara egasi — testda IKKI joyda solishtiriladi."""


# ===========================================================================
# UMUMIY TAYYORGARLIK
# ===========================================================================


@contextmanager
def _market_bed(
    conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    today: date,
) -> Iterator[SnapshotDomainSeed]:
    """`nvr_rows` + `snapshot_rows`, seed profili BUGUNNI qoplaydigan qilib.

    ⚠ TARTIB MUHIM: `snapshot_rows` ning tozalash bloki `nvr_rows` NING
      ICHIDA turishi shart, aks holda `cameras` hali `capture_runs` tayanib
      turganda o'chirilardi (`test_capture_tick.py` da o'rnatilgan qoida).
    """
    with (
        nvr_rows(conn, two_markets) as nvr,
        snapshot_rows(conn, nvr) as snap,
    ):
        for rows in snap.markets:
            conn.execute(_WIDEN_SCHEDULE, (today - timedelta(days=30), str(rows.schedule_id)))
        yield snap


@pytest.fixture
def criteria_env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> Callable[[], AbstractContextManager[SnapshotDomainSeed]]:
    """SC#1 va SC#2 uchun bozor + NVR + kamera + jadval."""

    def _open() -> AbstractContextManager[SnapshotDomainSeed]:
        return _market_bed(sync_owner_conn, two_markets, market_today)

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
def telegram_calls() -> Iterator[respx.Router]:
    """Telegram Bot API ning HTTP kontrakti — YAGONA ruxsat etilgan istisno.

    ⚠ `AlertSender` NING O'ZI ALMASHTIRILMAYDI. Sirsizlik, `bool`
      kontrakti va rasm taqig'i AYNAN o'sha sinfning xulqi; uni soxta
      obyekt bilan almashtirish o'lchovni mahsulot yuzasidan uzardi.
      Tutiladigan narsa faqat TARMOQ.
    """
    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=TELEGRAM_SEND_URL_PATTERN).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        yield router


async def _runs_for_day(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    day: date,
) -> list[dict[str, Any]]:
    """`capture_runs` ning XOM ustun qiymatlari — ORM keshidan MUSTAQIL."""
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT id, camera_id, slot_time, status, attempts "
                "  FROM capture_runs "
                " WHERE market_id = :market_id AND business_date = :day"
            ),
            {"market_id": market_id, "day": day},
        )
        return [dict(row._mapping) for row in result]


async def _ensure_plan(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    day: date,
) -> Any:
    async with tenant_session(market_id) as session:
        return await CaptureRepository(session, market_id).ensure_plan(day, grace_seconds=GRACE)


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_schedule_produces_slots(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    criteria_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    market_today: date,
) -> None:
    """«Bozor admini snapshot jadvalini o'z bozori uchun sozlaydi (mavsumiy profil
    bilan, 7 ta qotib qolgan vaqt emas) va ertasi kuni aynan o'sha slotlarda
    kadrlar paydo bo'ladi».

    O'LCHANADIGAN DA'VO: admin HTTP orqali jadvalni tahrirlaganidan keyin
    ERTANGI kunning materializatsiyasi AYNAN yangi vaqtlarni beradi.

    =======================================================================
    ⚠ IKKI TOMON HAM TEKSHIRILADI VA IKKINCHISI BIRINCHISIDAN MUHIMROQ.

    Faqat «ertaga yangi vaqtlar» tekshirilsa D-05 ning YARMI o'lchanmasdan
    qolardi: kun o'rtasida qo'shilgan `17:30` BUGUNGI rejaga ham tushib
    ketishi mumkin va u holda «06:00 sloti» degan dalil kun bo'yi siljib
    turardi. Aynan shu yarim support savolini tug'diradi — «nega kechagi
    hisobotda kutilmagan vaqt bor?».

    Shuning uchun tahrirdan KEYIN `ensure_plan(bugun)` QAYTA chaqiriladi:
    u hech nima qo'shmasligi kerak.
    =======================================================================
    """
    tomorrow = market_today + timedelta(days=1)

    with criteria_env() as snap:
        market_id = snap.market_a.market_id

        # --- 1. Bugungi reja tahrirdan OLDIN materializatsiya qilinadi ---
        await _ensure_plan(tenant_session, market_id, market_today)
        today_before = await _runs_for_day(tenant_session, market_id, market_today)
        assert today_before, "bugungi reja materializatsiya bo'lmadi — o'lchov ma'nosini yo'qotadi"
        default_slots = {row["slot_time"] for row in today_before}
        assert default_slots == set(DEFAULT_SNAPSHOT_SLOTS), (
            "nazorat holati buzildi: bugungi reja standart YETTILIKDAN emas, "
            f"boshqa to'plamdan qurilibdi ({sorted(default_slots)})"
        )

        # --- 2. Admin MAVSUMIY profilni saytdan sozlaydi ---
        patched = await api_client.patch(
            f"{SCHEDULES_URL}/{snap.market_a.schedule_id}",
            json={"times": SEASONAL_TIMES},
            headers=admin_headers,
        )
        assert patched.status_code == 200, patched.text

        # --- 3. Ertangi kun AYNAN yangi vaqtlarni oladi ---
        await _ensure_plan(tenant_session, market_id, tomorrow)
        tomorrow_rows = await _runs_for_day(tenant_session, market_id, tomorrow)
        tomorrow_slots = {row["slot_time"] for row in tomorrow_rows}

        # --- 4. Bugungi reja tahrirdan KEYIN ham O'ZGARMAYDI ---
        repeat = await _ensure_plan(tenant_session, market_id, market_today)
        today_after = await _runs_for_day(tenant_session, market_id, market_today)

    assert tomorrow_slots == set(SEASONAL_SLOTS), (
        f"ertangi reja yangi vaqtlarni olmadi: {sorted(tomorrow_slots)} != {sorted(SEASONAL_SLOTS)}"
    )
    assert not tomorrow_slots & set(DEFAULT_SNAPSHOT_SLOTS), (
        "ertangi rejada standart YETTILIKDAN qolgan vaqt bor — mavsumiy profil "
        "qotib qolgan ro'yxatning USTIGA qo'shilibdi, uni ALMASHTIRMABDI"
    )
    assert len(tomorrow_slots) == len(SEASONAL_TIMES) != len(DEFAULT_SNAPSHOT_SLOTS)

    assert repeat.created == 0, "tahrirdan keyingi tik BUGUNGI rejaga qator qo'shdi"
    assert {row["id"] for row in today_after} == {row["id"] for row in today_before}
    assert {row["slot_time"] for row in today_after} == default_slots, (
        "bugungi reja tahrirdan keyin siljidi — dalil-kadrning vaqti kun "
        "o'rtasida o'zgargan bo'lardi (D-05)"
    )


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_interruption_leaves_no_duplicate_and_missed_is_visible(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    criteria_env: Callable[[], AbstractContextManager[SnapshotDomainSeed]],
    tenant_session: TenantSessionFactory,
    market_today: date,
) -> None:
    """«Kadr olish uzilsa yoki takror ishga tushsa — dublikat yozuv yaratilmaydi,
    urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda ochiq ko'rinadi».

    O'LCHANADIGAN DA'VO: uchala bo'lak ham BITTA zanjirda — takroriy tik
    dublikat bermaydi, uzilib qolgan urinish qaytadi va yo'qlik JURNAL
    JAVOBIDA ko'rinadi.

    =======================================================================
    ⚠ UCHINCHI BO'LAK BAZADA EMAS, `GET /capture-runs` JAVOBIDA
      o'lchanadi. Mezon matni «jurnalda OCHIQ KO'RINADI» deydi — bu backend
      VA API da'vosi. Faqat `capture_runs` jadvalini o'qigan test javob
      shakli yo'qlikni UMUMAN ifodalay olmasa ham yashil qolardi: hujayra
      bo'sh chizilardi va bo'shliq «ko'radigan narsa yo'q» ma'nosini
      berardi.
    =======================================================================
    """
    with criteria_env() as snap:
        market_id = snap.market_a.market_id

        # --- 1. Takror tik DUBLIKAT yaratmaydi ---
        first = await capture_tick(api_sessionmaker, policy=POLICY)
        after_first = await _runs_for_day(tenant_session, market_id, market_today)
        second = await capture_tick(api_sessionmaker, policy=POLICY)
        after_second = await _runs_for_day(tenant_session, market_id, market_today)

        assert first.created > 0, "birinchi tik reja yozmadi — o'lchov ma'nosiz"
        assert second.created == 0, "ikkinchi tik yangi qator yaratdi"
        assert {row["id"] for row in after_second} == {row["id"] for row in after_first}, (
            "ikkinchi tik qatorlarni ALMASHTIRDI — identitet saqlanmadi"
        )

        camera_id = _camera_of(after_first)
        nvr_id = _nvr_of(sync_owner_conn, market_id)

        # --- 2. UZILGAN urinish qaytadi ---
        # Ijarasi tugagan `running` qator = «worker o'ldi». `SKIP LOCKED`
        # buni QOPLAMAYDI: qulf `COMMIT` bilan tushgan, qator esa mangu
        # `running` bo'lib qolardi.
        dead_at = datetime.now(tz=MARKET_TZ) - timedelta(seconds=60)
        interrupted = uuid4()
        sync_owner_conn.execute(
            _INSERT_RUN,
            (
                str(interrupted),
                str(market_id),
                str(camera_id),
                str(nvr_id),
                _probe_slot(dead_at),
                dead_at,
                CaptureRunStatus.RUNNING.value,
                1,
                datetime.now(tz=MARKET_TZ) - timedelta(seconds=LEASE),
                DEAD_WORKER,
                None,
                CaptureMethod.ISAPI.value,
            ),
        )
        await capture_tick(api_sessionmaker, policy=POLICY)
        revived = await _run_row(tenant_session, market_id, interrupted)
        assert revived["status"] in {
            CaptureRunStatus.PENDING.value,
            CaptureRunStatus.RUNNING.value,
        }, f"uzilgan urinish qaytmadi: {revived}"
        assert revived["locked_by"] != DEAD_WORKER, (
            "o'lik worker ijarasi qatorni mangu ushlab qoldi — urinish QAYTA BAJARILMASDI"
        )

        # --- 3. Grace oynasidan chiqqan slot `missed` va u JURNALDA ---
        overdue_at = datetime.now(tz=MARKET_TZ) - timedelta(seconds=GRACE + 120)
        overdue = uuid4()
        sync_owner_conn.execute(
            _INSERT_RUN,
            (
                str(overdue),
                str(market_id),
                str(camera_id),
                str(nvr_id),
                _probe_slot(overdue_at),
                overdue_at,
                CaptureRunStatus.PENDING.value,
                0,
                None,
                None,
                None,
                None,
            ),
        )
        result = await capture_tick(api_sessionmaker, policy=POLICY)
        assert overdue not in {run_id for batch in result.batches for run_id in batch.run_ids}, (
            "grace oynasidan chiqqan slot NAVBATGA tushdi — kechikkan kadr olinardi"
        )

        journal = await api_client.get(
            CAPTURE_RUNS_URL,
            params={"day": overdue_at.date().isoformat()},
            headers=admin_headers,
        )

    assert journal.status_code == 200, journal.text
    body = journal.json()
    missed = [row for row in body["rows"] if row["status"] == CaptureRunStatus.MISSED.value]
    assert missed, "yo'qlik yozuvi JURNAL JAVOBIDA umuman yo'q — SC#2 ifodalanmaydi"
    assert body["summary"]["missed"] >= 1, "kun xulosasi yo'qlikni sanamadi"
    assert all(row["attempts"] == 0 for row in missed), (
        "`missed` urinish bo'lgan holat sifatida yozilibdi — `failed` dan "
        "ajralmay qolardi va dala diagnostikasi ikkalasini bir xil ko'rardi"
    )
    assert all(row["snapshot_id"] is None for row in missed)


def _probe_slot(moment: datetime) -> time:
    """Zond qatorining slot vaqti — `moment` dan, lekin STANDART ro'yxatdan TASHQARIDA.

    ⚠ QOTIRILGAN VAQT YOZIB BO'LMAYDI: `business_date` `scheduled_at` dan
      hisoblanadi, ya'ni slot vaqti va vaqt tamg'asi bir kunga tegishli
      bo'lishi kerak — aks holda zond qatori yarim tundan keyin O'TGAN
      kunga tushib, jurnal so'rovidan tashqarida qolardi.

    ⚠ STANDART SLOT BILAN TO'QNASHUV CHETLAB O'TILADI: `uq_capture_runs_...`
      bir kamera uchun bir kunda bitta slot vaqtiga ruxsat beradi, ya'ni
      zond tasodifan `06:30` ga tushsa test O'Z TAYYORGARLIGIDA yiqilardi
      va sabab o'lchanayotgan da'voga umuman aloqador bo'lmasdi.
    """
    slot = moment.time().replace(second=0, microsecond=0)
    while slot in DEFAULT_SNAPSHOT_SLOTS:
        slot = slot.replace(minute=(slot.minute + 1) % 60)
    return slot


def _camera_of(rows: list[dict[str, Any]]) -> UUID:
    """Materializatsiya qilingan rejadagi BIRINCHI kamera — testda o'ylab topilmaydi."""
    assert rows, "reja bo'sh — kamera identifikatorini olib bo'lmaydi"
    camera_id = rows[0]["camera_id"]
    return camera_id if isinstance(camera_id, UUID) else UUID(str(camera_id))


def _nvr_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    row = conn.execute(
        "SELECT id FROM nvr_devices WHERE market_id = %s LIMIT 1", (str(market_id),)
    ).fetchone()
    assert row is not None, "bozorda NVR qurilmasi yo'q"
    return UUID(str(row[0]))


async def _run_row(
    tenant_session: TenantSessionFactory, market_id: UUID, run_id: UUID
) -> dict[str, Any]:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT status, attempts, locked_by, error_code "
                "  FROM capture_runs WHERE market_id = :market_id AND id = :run_id"
            ),
            {"market_id": market_id, "run_id": run_id},
        )
        return dict(result.one()._mapping)


# ===========================================================================
# SC#3
# ===========================================================================


class _Case:
    """Bitta uchidan-uchiga kadr o'lchovi uchun kerak bo'lgan hamma narsa."""

    __slots__ = ("camera_id", "market_id", "nvr_id", "run_id", "slot_time", "today")

    def __init__(
        self,
        *,
        market_id: UUID,
        nvr_id: UUID,
        camera_id: UUID,
        run_id: UUID,
        slot_time: time,
        today: date,
    ) -> None:
        self.market_id = market_id
        self.nvr_id = nvr_id
        self.camera_id = camera_id
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
async def sim_case(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
    sim: str,
    sim_credentials: tuple[str, str],
    s3_client: SnapshotStorage,
) -> AsyncIterator[_Case]:
    """Simga qaratilgan NVR + `running` qator + ombor prefiksining tozalanishi.

    ⚠ QURILMA QURILMA-YO'LIGA O'TKAZILADI — bu MA'LUMOT o'zgarishi, kod
      o'zgarishi emas (D-06). Sabab mexanik: javob BAYTLARINI simning
      `frame_mode` i boshqaradi, ya'ni buzuq kadrni BUYURTMA bilan olish
      mumkin. Oqim yo'li esa har doim YAROQLI kadr qaytaradi va u to'rt
      shaklni bera OLMAYDI.
    """
    host, port = _split(sim)
    username, password = sim_credentials

    with nvr_rows(sync_owner_conn, two_markets) as nvr:
        rows = nvr.market_a
        camera_id = rows.active_camera_ids[0]
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

        case = _Case(
            market_id=rows.market_id,
            nvr_id=rows.nvr_id,
            camera_id=camera_id,
            run_id=uuid4(),
            slot_time=DEFAULT_SNAPSHOT_SLOTS[0],
            today=market_today,
        )
        _claim_run(sync_owner_conn, case)
        try:
            yield case
        finally:
            sync_owner_conn.execute(
                "DELETE FROM snapshots WHERE market_id = %s", (str(case.market_id),)
            )
            sync_owner_conn.execute(
                "DELETE FROM capture_runs WHERE market_id = %s", (str(case.market_id),)
            )
            keys = await s3_client.list_prefix(f"{case.market_id}/")
            if keys:
                await s3_client.delete_many(keys)


def _claim_run(conn: Connection[TupleRow], case: _Case) -> None:
    """`running` + tirik ijara bilan qator — worker allaqachon olgan holat."""
    conn.execute(
        _INSERT_RUN,
        (
            str(case.run_id),
            str(case.market_id),
            str(case.camera_id),
            str(case.nvr_id),
            case.slot_time,
            datetime.now(tz=MARKET_TZ) - timedelta(seconds=30),
            CaptureRunStatus.RUNNING.value,
            1,
            datetime.now(tz=MARKET_TZ) + timedelta(seconds=LEASE),
            "pytest",
            None,
            None,
        ),
    )


async def _capture(
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


async def _snapshot_of(
    tenant_session: TenantSessionFactory, case: _Case, run_id: UUID
) -> dict[str, Any]:
    async with tenant_session(case.market_id) as session:
        result = await session.execute(
            text(
                "SELECT id, quality_verdict, light_mode, is_billable, object_key "
                "  FROM snapshots WHERE market_id = :market_id AND capture_run_id = :run_id"
            ),
            {"market_id": case.market_id, "run_id": run_id},
        )
        return dict(result.one()._mapping)


@contextmanager
def _billing_child(conn: Connection[TupleRow]) -> Iterator[None]:
    """HAQIQIY `snapshots` ga qaratilgan `occupancy` uslubidagi bola-jadval.

    5-fazadagi bandlik dalili AYNAN shu shaklda quriladi, ya'ni bu — uning
    oldindan olingan o'lchovi. Faqat `CHECK` yoki faqat `FK` yetarli emas:
    `FK` yolg'iz o'zi `(id, false)` juftligiga havolani ham QABUL QILARDI.
    """
    conn.execute(_DROP_BILLING_CHILD)
    conn.execute(_CREATE_BILLING_CHILD)
    try:
        yield
    finally:
        conn.execute(_DROP_BILLING_CHILD)


async def test_sc3_quality_verdict_never_reaches_billing(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    s3_client: SnapshotStorage,
    sim: str,
    sim_case: _Case,
) -> None:
    """«Qorong'i / buzuq / bo'sh kadr avtomatik belgilanadi va `light_mode` bilan
    saqlanadi — bunday kadr hech qachon hisob-kitobga ta'sir qilmaydi».

    O'LCHANADIGAN DA'VO: yaroqsiz kadr SAQLANADI (dalil yo'qolmaydi), lekin
    unga bandlik dalilini bog'lash BAZA DARAJASIDA rad etiladi.

    =======================================================================
    ⚠ «TA'SIR QILMAYDI» KONVENTSIYA EMAS, DB KAFOLATI.

    Ilova qatlamidagi `if snapshot.is_billable:` sharti bugungi kodda
    to'g'ri bo'lardi va 6-fazada yozilgan YANGI so'rov uni jimgina chetlab
    o'tardi — hech qanday test qizarmasdan. Langar (`UNIQUE (id,
    is_billable)` + kompozit FK + `CHECK`) esa yozishning O'ZINI imkonsiz
    qiladi.

    ⚠ NAZORAT HOLATI MAJBURIY: yaroqli kadrga havola O'TISHI kerak. Usiz
      butunlay buzilgan FK ham «yashil» ko'rinardi, sabab esa boshqa
      bo'lardi.
    =======================================================================
    """
    # --- 1. Buzuq kadr: belgilanadi, saqlanadi, hisobga KIRMAYDI ---
    sim_patch(sim, frame_mode="truncated")
    broken = await _capture(api_sessionmaker, s3_client, sim_case)
    assert broken.succeeded == 1, broken

    corrupt = await _snapshot_of(tenant_session, sim_case, sim_case.run_id)
    assert corrupt["quality_verdict"] == SnapshotQuality.CORRUPT.value, corrupt
    assert corrupt["is_billable"] is False, (
        "yaroqsiz kadr `is_billable` bo'lib qoldi — D-16 ning generated ustuni buzilgan"
    )
    assert corrupt["light_mode"] == SnapshotLightMode.UNKNOWN.value, (
        "buzuq kadr uchun SOXTA yorug'lik rejimi yozildi — o'lchanmagan qiymat "
        "«o'lchandi va shu chiqdi» ma'nosini berardi"
    )
    assert await s3_client.head(sim_case.key) is not None, (
        "yaroqsiz kadr OMBORDA yo'q — mezon uni SAQLASHNI talab qiladi"
    )

    # --- 2. Yaroqli kadr: NAZORAT holati ---
    sim_patch(sim, frame_mode="ok")
    good = _Case(
        market_id=sim_case.market_id,
        nvr_id=sim_case.nvr_id,
        camera_id=sim_case.camera_id,
        run_id=uuid4(),
        slot_time=DEFAULT_SNAPSHOT_SLOTS[1],
        today=sim_case.today,
    )
    _claim_run(sync_owner_conn, good)
    await _capture(api_sessionmaker, s3_client, good)
    healthy = await _snapshot_of(tenant_session, good, good.run_id)

    assert healthy["quality_verdict"] == SnapshotQuality.OK.value, healthy
    assert healthy["is_billable"] is True
    assert healthy["light_mode"] != SnapshotLightMode.UNKNOWN.value, (
        "yaroqli kadr uchun ham yorug'lik rejimi o'lchanmadi — `light_mode` "
        "ustuni mezon matnida ATAYIN nomlangan (D-12)"
    )

    # --- 3. BAZA DARAJASIDAGI RAD ETISH ---
    with _billing_child(sync_owner_conn):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            sync_owner_conn.execute(_INSERT_BILLING_CHILD, (str(corrupt["id"]),))
        sync_owner_conn.execute("ROLLBACK")
        sync_owner_conn.execute(_INSERT_BILLING_CHILD, (str(healthy["id"]),))


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_storage_layout_and_retention_policy(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    s3_client: SnapshotStorage,
    market_today: date,
) -> None:
    """«Kadrlar S3-mos omborda bozor/kamera/sana bo'yicha topiladi; 90 kun to'liq,
    keyin siqilgan saqlash siyosati amalda ishlaydi».

    O'LCHANADIGAN DA'VO: kalit BOZOR/SANA/KAMERA/SLOT tartibida topiladi va
    chegara kelganda kadr AYNAN o'sha kalit ustida siqiladi — o'lchamlari
    saqlanib, qatori qolib.

    =======================================================================
    ⚠ «90 KUN» BU YERDA KUTILMAYDI VA BU FARQ OCHIQ YOZILGAN.

    Isbotlanadigan da'vo — MEXANIZM: chegara kelganda kadr siqiladi, kaliti
    o'zgarmaydi, o'lchamlari saqlanadi va QATOR o'chirilmaydi. Vaqt
    siljitilmaydi: chegara SOZLAMA (`full_days=0`), «bugun» esa ARGUMENT
    (`today=`) — ikkalasi ham mahsulot yo'lidagi haqiqiy parametrlar.

    Isbotlanmaydigan da'vo — siyosatning 90 KALENDAR KUN davomida ishlab
    turishi. Uni faqat vaqt isbotlaydi va u `04-VALIDATION.md` da
    Manual-Only band sifatida, egasi Ops bilan turadi.

    ⚠ OMBOR MOCK QILINMAYDI: har bir bayt haqiqiy `storage` konteyneriga
      boradi va siqilgan obyekt QAYTA O'QILIB dekodlanadi. `size_bytes`
      ustunining kamayishi almashtirilgan qatlamda ham «yashil» bo'lardi.
    =======================================================================
    """
    payload = frame_bytes(mean=120, stddev=40, size=FRAME_SIZE, quality=ORIGINAL_QUALITY)
    slot = DEFAULT_SNAPSHOT_SLOTS[0]

    with nvr_rows(sync_owner_conn, two_markets) as nvr:
        market_ids = [str(market_id) for market_id in nvr.market_ids]
        try:
            mine = await _write_frame(
                sync_owner_conn,
                s3_client,
                nvr=nvr.market_a,
                day=market_today,
                slot=slot,
                payload=payload,
            )
            neighbour = await _write_frame(
                sync_owner_conn,
                s3_client,
                nvr=nvr.market_b,
                day=market_today,
                slot=slot,
                payload=payload,
            )

            # --- 1. BOZOR/SANA/KAMERA bo'yicha TOPILADI ---
            day_prefix = KEY_PREFIX_FOR_DAY(
                market_id=nvr.market_a.market_id, business_date=market_today
            )
            found = await s3_client.list_prefix(day_prefix)
            assert mine["key"] in found, (
                f"kun prefiksi ({day_prefix}) o'z kadrini topmadi — kalit tartibi buzilgan"
            )
            assert str(nvr.market_a.active_camera_ids[0]) in mine["key"], (
                "kalitda KAMERA segmenti yo'q — «kamera bo'yicha topiladi» bajarilmaydi"
            )
            assert neighbour["key"] not in found, (
                "qo'shni bozorning kadri shu bozorning prefiksida ko'rindi — "
                "bitta rekvizit BARCHA bozorlarni ochadi, ajratuvchi esa faqat PREFIKS"
            )

            # --- 2. Chegara kelganda SIQILADI ---
            before = _snapshot_state(sync_owner_conn, mine["snapshot_id"])
            result = await retention_daily(
                api_sessionmaker,
                s3_client,
                policy=COMPRESS_ONLY,
                today=market_today + timedelta(days=1),
            )
            after = _snapshot_state(sync_owner_conn, mine["snapshot_id"])

            assert result.compressed >= 1, result
            assert after["storage_tier"] == SnapshotTier.COMPRESSED.value, after
            assert after["object_key"] == before["object_key"], (
                "siqilgan kadr BOSHQA kalitga yozildi — dalil havolasi uzilardi"
            )
            assert after["object_deleted_at"] is None, "siqish obyektni o'chirdi"
            assert int(after["size_bytes"]) < int(before["size_bytes"]), (
                f"siqishdan keyin hajm kamaymadi: {after['size_bytes']} >= {before['size_bytes']}"
            )

            stored = await s3_client.get(mine["key"])
            with Image.open(io.BytesIO(stored)) as image:
                assert image.size == FRAME_SIZE, (
                    f"siqilgan kadr O'LCHAMINI yo'qotdi: {image.size} != {FRAME_SIZE}"
                )
            assert len(stored) == int(after["size_bytes"]), (
                "bazadagi hajm OMBORDAGI obyekt bilan mos emas"
            )
            assert _snapshot_count(sync_owner_conn, nvr.market_a.market_id) == 1, (
                "saqlash siyosati QATORNI o'chirdi — 6-faza dalil-kadrga havola qiladi"
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


async def _write_frame(
    conn: Connection[TupleRow],
    storage: SnapshotStorage,
    *,
    nvr: MarketNvrRows,
    day: date,
    slot: time,
    payload: bytes,
) -> dict[str, Any]:
    """Kadrni AVVAL omborga, KEYIN bazaga yozadi (§B.4 ning tartibi)."""
    camera_id = nvr.active_camera_ids[0]
    key = object_key(
        market_id=nvr.market_id, business_date=day, camera_id=camera_id, slot_time=slot
    )
    await storage.put(key, payload)

    scheduled_at = datetime.combine(day, slot, tzinfo=MARKET_TZ)
    run_id = uuid4()
    snapshot_id = uuid4()
    conn.execute(
        _INSERT_RUN,
        (
            str(run_id),
            str(nvr.market_id),
            str(camera_id),
            str(nvr.nvr_id),
            slot,
            scheduled_at,
            CaptureRunStatus.SUCCEEDED.value,
            1,
            None,
            None,
            None,
            CaptureMethod.ISAPI.value,
        ),
    )
    with Image.open(io.BytesIO(payload)) as image:
        width, height = image.size
    conn.execute(
        _INSERT_SNAPSHOT,
        (
            str(snapshot_id),
            str(nvr.market_id),
            str(run_id),
            str(camera_id),
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
            SnapshotTier.FULL.value,
            width,
            height,
        ),
    )
    return {"snapshot_id": snapshot_id, "key": key, "camera_id": camera_id}


def _snapshot_state(conn: Connection[TupleRow], snapshot_id: UUID) -> dict[str, Any]:
    row = conn.execute(_SNAPSHOT_STATE, (str(snapshot_id),)).fetchone()
    assert row is not None, "qator YO'QOLDI — bu siyosatning eng qattiq taqig'i"
    return {
        "storage_tier": row[0],
        "size_bytes": row[1],
        "object_key": row[2],
        "object_deleted_at": row[3],
    }


def _snapshot_count(conn: Connection[TupleRow], market_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM snapshots WHERE market_id = %s", (str(market_id),)
    ).fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_absence_reaches_telegram_and_sentry(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_today: date,
    telegram_calls: respx.Router,
) -> None:
    """«Kamera offline bo'lsa, slot o'tkazib yuborilsa yoki backup xato bersa —
    platforma adminiga Telegram-alert keladi va xato Sentry'da ko'rinadi».

    O'LCHANADIGAN DA'VO IKKI YARIM: (a) uchala tetik ham xabar beradi va
    ular GURUHLANADI; (b) xato Sentry'ga BORADIGAN yo'l ikkala jarayonda
    ham ulangan.

    =======================================================================
    ⚠ GURUHLASH — MEZONNING YOZILMAGAN, LEKIN MAJBURIY QISMI. Yomon kunda
      75 slot yiqiladi; har biriga bitta xabar `429` va ertasi kuni
      bildirishnomani o'chirgan admin degani — shundan keyin HAQIQIY
      nosozlik ham ko'rinmay qoladi.

    ⚠ RASM TAQIG'I (D-19) SHU YERDA HAM O'LCHANADI: kadr — bozor
      tashrifchilarining shaxsiy ma'lumoti, Telegram serverlari esa O'zR
      data-rezidentlik chegarasidan TASHQARIDA. Bir marta yuborilgan
      baytni qaytarib bo'lmaydi.

    ⚠ IKKINCHI YARIM (`Sentry`) MANBA MATNIDAN o'lchanadi va u YETTI EMAS,
      IKKI kirish nuqtasini talab qiladi — sabab `SENTRY_ENTRYPOINTS`
      docstringida.
    =======================================================================
    """
    with nvr_rows(sync_owner_conn, two_markets) as nvr:
        rows = nvr.market_a
        slot = DEFAULT_SNAPSHOT_SLOTS[0]
        scheduled_at = datetime.combine(market_today, slot, tzinfo=MARKET_TZ)
        try:
            # Retention yurak urishi YANGI: aks holda u ham platforma
            # signalini qo'shib, «backup» da'vosini shovqin ichida
            # qoldirardi (`test_alerting.py` da o'lchangan holat).
            sync_owner_conn.execute(
                _HEARTBEAT_UPSERT,
                (RETENTION_COMPONENT, datetime.now(tz=MARKET_TZ) - timedelta(hours=1)),
            )
            sync_owner_conn.execute(_HEARTBEAT_DROP, (BACKUP_COMPONENT,))

            for camera_id in rows.active_camera_ids:
                sync_owner_conn.execute(
                    _INSERT_RUN,
                    (
                        str(uuid4()),
                        str(rows.market_id),
                        str(camera_id),
                        str(rows.nvr_id),
                        slot,
                        scheduled_at,
                        CaptureRunStatus.MISSED.value,
                        0,
                        None,
                        None,
                        "capture_slot_missed",
                        None,
                    ),
                )

            sender = AlertSender(
                token=SecretStr(TELEGRAM_TOKEN), chat_id=TELEGRAM_CHAT, enabled=True
            )
            try:
                await alert_sweep(api_sessionmaker, sender)
            finally:
                await sender.aclose()

            texts = [str(json.loads(call.request.content)["text"]) for call in telegram_calls.calls]
        finally:
            market_ids = [str(market_id) for market_id in nvr.market_ids]
            sync_owner_conn.execute(
                "DELETE FROM alert_events WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM capture_runs WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(_HEARTBEAT_DROP, (RETENTION_COMPONENT,))
            sync_owner_conn.execute(_HEARTBEAT_DROP, (BACKUP_COMPONENT,))

    assert texts, "birorta xabar yuborilmadi — uchala tetik ham jim qoldi"

    market_messages = [line for line in texts if "capture_missed" in line]
    platform_messages = [line for line in texts if "backup_stale" in line]

    assert len(market_messages) == 1, (
        f"o'tkazib yuborilgan slotlar uchun {len(market_messages)} ta xabar ketdi — "
        "guruhlash ishlamadi"
    )
    assert "camera_offline" in market_messages[0], (
        "kamera javob bermayotgani AYRIM xabar bo'lib ketdi yoki umuman aytilmadi"
    )
    assert len(platform_messages) == 1, (
        f"zaxira nosozligi uchun {len(platform_messages)} ta xabar ketdi"
    )

    for call in telegram_calls.calls:
        path = call.request.url.path
        assert path.endswith(f"/{TELEGRAM_SEND_METHOD}"), (
            f"boshqa Bot API metodi chaqirildi: {path} — rasm yo'li OCHILGAN"
        )
    for line in texts:
        assert "http" not in line, f"xabarda havola bor: {line}"
        assert ".jpg" not in line, f"xabarda obyekt kaliti bor: {line}"

    _assert_sentry_is_wired()


def _assert_sentry_is_wired() -> None:
    """Sentry ilmoqlari IKKALA jarayonda ham ulangan (SC#5 ning ikkinchi yarmi).

    Manba matni o'qiladi (`test_go2rtc_client.py` da o'rnatilgan naqsh):
    ilmoqning O'ZI to'g'ri ishlashi YETARLI EMAS — ulanmagan ilmoq har
    testda yashil bo'lib, mahsulotda umuman chaqirilmasdi.
    """
    module = importlib.import_module(OBSERVABILITY_MODULE)
    initialiser = module.init_sentry
    source = inspect.getsource(initialiser)
    assert "before_send=scrub_event" in source
    assert "before_breadcrumb=scrub_breadcrumb" in source

    for module_name, function_name in SENTRY_ENTRYPOINTS:
        entry = getattr(importlib.import_module(module_name), function_name)
        assert "init_sentry(" in inspect.getsource(entry), (
            f"`{module_name}.{function_name}` Sentry'ni o'rnatmaydi — o'sha "
            "jarayondagi istisnolar FAQAT konteyner jurnalida qolardi"
        )


# ===========================================================================
# META — mezonlardan birortasi JIMGINA tushib qolmasin
# ===========================================================================


def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «beshala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: qabul
      mezoni `--collect-only` chiqishida `sc[1-5]` naqshini SANAYDI, ya'ni
      meta-testning o'zi sanoqqa kirib ketmasligi kerak.
    """
    module = sys.modules[__name__]
    names = sorted(
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )

    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 5, f"mezon testlari soni 5 emas: {criteria}"


def test_criteria_module_uses_no_storage_mock() -> None:
    """MOCK'SIZ O'LCHOV DARVOZASI — §S-13.

    =======================================================================
    NEGA BU DARVOZA KERAK.

    Birinchi «qulaylik uchun» qo'yilgan ombor o'rnini bosuvchi butun
    imzolash yo'lini, endpoint kelishuvini va sahifalash semantikasini
    o'lchanmagan qoldirardi — 03-14 nosozligining aynan takrori, faqat
    boshqa qatlamda. U yerda mock ostida «kod media serveri bilan
    gaplasha oladi» da'vosi yashil turardi va birinchi mock'siz o'lchov
    uni butunlay rad etdi.

    UCH DA'VO VA UCHALASI HAM MUSTAQIL:

      1. modul mock kutubxonalarini IMPORT QILMAYDI (`ast` daraxti
         o'qiladi — satr bo'yicha qidiruv izohni koddan ajrata olmasdi);
      2. `respx` istisnosi TOR: uni so'raydigan test AYNAN BITTA va u
         SC#5 (Telegram kontrakti);
      3. haqiqiy omborga boradigan testlar HALI HAM BOR — testlarni
         birma-bir o'chirgan o'zgarish birinchi da'voni buzmasdi va
         darvoza BO'SH faylda ham yashil bo'lardi.
    =======================================================================
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    roots: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported_names |= {alias.name for alias in node.names}

    assert len(roots) >= 10, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh "
        "daraxtda ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _MOCK_ROOTS, (
        f"mock kutubxonasi import qilingan: {sorted(roots & _MOCK_ROOTS)} — bu fayl "
        "HAQIQIY SeaweedFS va HAQIQIY simulyator ustida o'lchaydi"
    )
    assert not imported_names & _MOCK_NAMES, (
        f"mock vositasi import qilingan: {sorted(imported_names & _MOCK_NAMES)}"
    )

    module = sys.modules[__name__]
    assert hasattr(module, TELEGRAM_FIXTURE), (
        f"`{TELEGRAM_FIXTURE}` shu modulda topilmadi — istisno qayta nomlangan va bu "
        "darvoza endi MAVJUD BO'LMAGAN naqshni izlab, jimgina yashil qolardi"
    )

    tests = [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    ]
    telegram_users = [
        name for name, obj in tests if TELEGRAM_FIXTURE in inspect.signature(obj).parameters
    ]
    assert telegram_users == ["test_sc5_absence_reaches_telegram_and_sentry"], (
        f"`{TELEGRAM_FIXTURE}` ni {telegram_users} so'rayapti — istisno FAQAT "
        "Telegram kontrakti uchun va u AYNAN bitta testda qoladi"
    )

    storage_users = [
        name for name, obj in tests if "s3_client" in inspect.signature(obj).parameters
    ]
    assert len(storage_users) >= 2, (
        f"haqiqiy omborga boradigan mezon testlari {len(storage_users)} ta: {storage_users}"
    )
