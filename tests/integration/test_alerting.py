"""Alert supurgisi — guruhlash, debounce, eskalatsiya va rasm taqig'i (FOUND-06).

=============================================================================
TELEGRAM `respx` BILAN TUTILADI, BAZA ESA HAQIQIY.

Ikki tanlov, ikki xil sabab:

  * **Telegram — `respx`.** Haqiqiy Bot API ga borish testni tashqi
    xizmatga, tarmoqqa va HAQIQIY BOT TOKENIGA bog'lardi. Bu yerda
    o'lchanadigan narsa esa HTTP KONTRAKTI: nechta so'rov ketdi, qaysi
    yo'lga va tanasida nima bor.
  * **Baza — HAQIQIY Postgres.** Debounce ning butun kafolati QISMAN
    UNIQUE INDEKSDA (`uq_alert_events_market_id_alert_key_open`) va u
    faqat Postgres'da mavjud. Uni mock ostida o'lchash «guruhlash
    ishlayapti» degan yolg'on ishonch berardi.
=============================================================================

=============================================================================
VAQT SILJITILMAYDI — U ARGUMENT (`alert_sweep(..., now=...)`).

Debounce (60 daqiqa) va eskalatsiya (3 soat) arifmetikasi AYNAN `now`
argumentiga qaraydi, ya'ni «bir soatdan keyin nima bo'ladi?» savoli
soatni almashtirmasdan, `freezegun`siz va yangi bog'liqliksiz o'lchanadi.
`retention_daily(..., today=...)` bilan aynan bir xil qaror.
=============================================================================

⚠ RASM TAQIG'INING TESTI (D-19) SHU FAYLNING ENG MUHIM DARVOZASI:
  `respx` tutgan BARCHA so'rovlarning yo'li `/sendMessage` bilan tugaydi
  va birortasining tanasida rasmga tegishli maydon YO'Q. Frontend
  tomonidagi jufti — `04-UI-SPEC.md` ning G-3 darvozasi.
"""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import pytest
import respx
from app.jobs.alerting import (
    ALERT_DETAIL_KEYS,
    ALERT_META,
    ALERT_SWEEP_COMPONENT,
    BACKUP_COMPONENT,
    NEVER_SUPPRESSED_ALERT_KEYS,
    PLATFORM_SCOPED_ALERT_KEYS,
    alert_sweep,
    daily_digest,
)
from app.jobs.capture import CapturePolicy, capture_tick
from app.jobs.retention import RETENTION_COMPONENT
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD, AlertSender
from app.services.quality import QualityThresholds
from fixtures.nvr_domain import nvr_rows
from pydantic import SecretStr
from sbozor_core.enums import AlertSeverity, CaptureMethod, CaptureRunStatus
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import MARKET_TZ, business_today

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date
    from uuid import UUID

    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

TOKEN = "1234567890:TEST-TOKEN-NEVER-REAL"  # noqa: S105 - qalbaki, `respx` tutadi
CHAT_ID = "-1001234567890"
SEND_URL = f"{TELEGRAM_API_BASE}/bot{TOKEN}/{TELEGRAM_SEND_METHOD}"

CAMERA_COUNT = 22
"""§E.13 ning aniq stsenariysi: 25 kameradan 22 tasi bitta slotda yiqildi."""

_PLATFORM_COMPONENTS = (BACKUP_COMPONENT, RETENTION_COMPONENT)
"""Platforma darajasidagi yurak urishlari — `bed` ularni YANGI qilib qo'yadi.

Sabab `bed` fixture'ining docstringida: ular yo'q bo'lganda supurgi HAR
YUGURISHDA ikkita platforma alertini ko'taradi va bozor guruhlashining
o'lchovini shovqin bilan aralashtiradi.
"""

_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, error_code, capture_method, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)"
)
_INSERT_CAMERA = (
    "INSERT INTO cameras "
    "(id, market_id, nvr_id, channel_no, stream_name, name, status, is_archived) "
    "VALUES (%s, %s, %s, %s, %s, %s, 'online', false)"
)
_ALERTS = (
    "SELECT alert_key, severity, subject_id, occurrences, notified_at, resolved_at "
    "FROM alert_events WHERE market_id = %s ORDER BY alert_key, occurrences"
)
_HEARTBEAT_UPSERT = (
    "INSERT INTO system_heartbeats (component, last_seen_at) VALUES (%s, %s) "
    "ON CONFLICT (component) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at"
)
_HEARTBEAT_DROP = "DELETE FROM system_heartbeats WHERE component = %s"
_HEARTBEAT_READ = "SELECT last_seen_at FROM system_heartbeats WHERE component = %s"


class _Bed:
    """Bitta o'lchov uchun bozor, kameralar va bugungi kun."""

    __slots__ = ("camera_ids", "conn", "market_id", "nvr_id", "other_market_id", "today")

    def __init__(
        self,
        *,
        conn: Connection[TupleRow],
        market_id: UUID,
        other_market_id: UUID,
        nvr_id: UUID,
        camera_ids: tuple[UUID, ...],
        today: date,
    ) -> None:
        self.conn = conn
        self.market_id = market_id
        self.other_market_id = other_market_id
        self.nvr_id = nvr_id
        self.camera_ids = camera_ids
        self.today = today

    def write_run(
        self,
        *,
        camera_id: UUID,
        slot: time,
        status: str,
        error_code: str | None = None,
        days_ago: int = 0,
    ) -> None:
        scheduled_at = datetime.combine(self.today - timedelta(days=days_ago), slot, MARKET_TZ)
        attempted = status in {CaptureRunStatus.FAILED.value, CaptureRunStatus.SUCCEEDED.value}
        self.conn.execute(
            _INSERT_RUN,
            (
                str(uuid4()),
                str(self.market_id),
                str(camera_id),
                str(self.nvr_id),
                slot,
                scheduled_at,
                status,
                1 if attempted else 0,
                error_code,
                CaptureMethod.ISAPI.value if attempted else None,
            ),
        )

    def fail_slot(
        self,
        slot: time,
        *,
        count: int = CAMERA_COUNT,
        status: str = CaptureRunStatus.MISSED.value,
        error_code: str | None = None,
    ) -> None:
        """Bitta slotda `count` ta kamerani yiqitadi, qolganini muvaffaqiyatli qiladi.

        ⚠ STANDART HOLAT — `missed`, `failed` EMAS. D-20 ning yuragi aynan
          shu: «slot umuman bajarilmadi» holatida HECH QANDAY hodisa yo'q
          va uni faqat materializatsiya qilingan QATOR ko'rinadigan qiladi.
        """
        for index, camera_id in enumerate(self.camera_ids):
            broken = index < count
            self.write_run(
                camera_id=camera_id,
                slot=slot,
                status=status if broken else CaptureRunStatus.SUCCEEDED.value,
                error_code=error_code if broken else None,
            )

    def alerts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(_ALERTS, (str(self.market_id),)).fetchall()
        return [
            {
                "alert_key": row[0],
                "severity": row[1],
                "subject_id": row[2],
                "occurrences": row[3],
                "notified_at": row[4],
                "resolved_at": row[5],
            }
            for row in rows
        ]

    def set_heartbeat(self, component: str, *, hours_ago: float) -> None:
        moment = datetime.now(tz=MARKET_TZ) - timedelta(hours=hours_ago)
        self.conn.execute(_HEARTBEAT_UPSERT, (component, moment))

    def drop_heartbeat(self, component: str) -> None:
        self.conn.execute(_HEARTBEAT_DROP, (component,))


@pytest.fixture
def bed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[_Bed]:
    """Bozor + 25 kamera + YANGI yurak urishlari + kafolatlangan tozalash.

    ⚠ 25 KAMERA — KARMANANING HAQIQIY KATTALIGI (§E.13). Uch kamerali
      seed bilan «≥30 %» chegarasi ma'nosiz bo'lardi: uchtadan bittasi
      allaqachon 33 %.

    =====================================================================
    ⚠⚠ YURAK URISHLARI ATAYIN YANGI QILIB QO'YILADI — VA BU O'LCHOV
       NATIJASIDA QO'SHILDI.

    Birinchi yugurishda guruhlash testlari `4 == 1` bilan qizardi. Sabab
    MAHSULOTDA emas, TEST SHARTIDA edi: `system_heartbeats` da `backup`
    ham, `retention` ham YO'Q (zaxira 8-fazada quriladi, retention esa
    hali yugurmagan), ya'ni supurgi HAR YUGURISHDA ikkita PLATFORMA
    alertini ham ko'tarardi va ular BOSHQA (platforma) xabarini
    tug'dirardi.

    Bu MAHSULOTNING TO'G'RI XULQI (`test_stale_heartbeat_alerts` uni
    alohida o'lchaydi). Lekin guruhlash testi «BOZOR bo'yicha bitta
    xabar» da'vosini o'lchaydi, ya'ni platforma shovqini undan
    CHIQARILISHI kerak — aks holda test ikki mustaqil qarorni bir sonda
    aralashtirardi.
    =====================================================================
    """
    with nvr_rows(sync_owner_conn, two_markets) as nvr:
        rows = nvr.market_a
        camera_ids = list(rows.active_camera_ids)
        channel = 100
        while len(camera_ids) < 25:
            camera_id = uuid4()
            sync_owner_conn.execute(
                _INSERT_CAMERA,
                (
                    str(camera_id),
                    str(rows.market_id),
                    str(rows.nvr_id),
                    channel,
                    f"cam_zond_{channel}",
                    f"Zond {channel}",
                ),
            )
            camera_ids.append(camera_id)
            channel += 1

        market_ids = [str(market_id) for market_id in nvr.market_ids]
        bed = _Bed(
            conn=sync_owner_conn,
            market_id=rows.market_id,
            other_market_id=nvr.market_b.market_id,
            nvr_id=rows.nvr_id,
            camera_ids=tuple(camera_ids),
            today=business_today(),
        )
        for component in _PLATFORM_COMPONENTS:
            bed.set_heartbeat(component, hours_ago=1)
        try:
            yield bed
        finally:
            sync_owner_conn.execute(
                "DELETE FROM alert_events WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM capture_runs WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            for component in (ALERT_SWEEP_COMPONENT, *_PLATFORM_COMPONENTS):
                sync_owner_conn.execute(_HEARTBEAT_DROP, (component,))


@pytest.fixture
def sender() -> Iterator[AlertSender]:
    """Haqiqiy `AlertSender` — `respx` faqat TARMOQNI tutadi.

    ⚠ MAHSULOT OBYEKTI ALMASHTIRILMAYDI. Sirsizlik, `bool` kontrakti va
      rasm taqig'i AYNAN shu sinfning xulqi, ya'ni uni soxta obyekt bilan
      almashtirish o'lchovni mahsulot yuzasidan uzardi (03-14 ning
      metodikasi).
    """
    yield AlertSender(token=SecretStr(TOKEN), chat_id=CHAT_ID, enabled=True)


def _bodies(router: respx.Router) -> list[dict[str, Any]]:
    """Tutingan so'rovlarning tanalari."""
    return [json.loads(call.request.content) for call in router.calls]


async def _sweep(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    now: datetime | None = None,
) -> Any:
    return await alert_sweep(sessionmaker, sender, now=now)


# ===========================================================================
# 1. GURUHLASH — 75 yiqilish 75 xabar BERMAYDI
# ===========================================================================


async def test_missed_slots_are_grouped(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ D-22 — 22 ta o'tkazib yuborilgan slot BITTA xabar beradi, 22 ta emas.

    Guruhlashsiz bu 22 (yomon kunda 75) ta Telegram xabari bo'lardi, `429`
    va ertasi kuni bildirishnomani o'chirgan admin — shundan keyin
    HAQIQIY nosozlik ham ko'rinmay qoladi.

    ⚠ MANBA — `missed` QATORI (D-20). «Slot umuman bajarilmadi» holatida
      hech qanday istisno yo'q; uni faqat oldindan materializatsiya
      qilingan qator ko'rinadigan qiladi.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0])

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        result = await _sweep(api_sessionmaker, sender)
        bodies = _bodies(router)

    rows = bed.alerts()
    missed = [row for row in rows if row["alert_key"] == "capture_missed"]
    offline = [row for row in rows if row["alert_key"] == "camera_offline"]

    assert len(missed) == 1, f"22 o'tkazib yuborilgan slot uchun {len(missed)} qator yozildi"
    assert missed[0]["subject_id"] is None, "butun bozorga tegishli alert kameraga bog'landi"
    assert len(offline) == 1, f"22 kamera uchun {len(offline)} `camera_offline` qatori"
    assert route.call_count == 1, f"{route.call_count} ta Telegram xabari ketdi"
    assert result.notified == 1
    # ⚠ IKKI ALERT — BITTA XABAR: guruhlash qatorlarni emas, XABARLARNI
    #   birlashtiradi. Qatorlar UI uchun alohida qoladi (§6.7).
    assert "capture_missed" in bodies[0]["text"]
    assert "camera_offline" in bodies[0]["text"]


async def test_a_repeat_inside_the_debounce_window_sends_nothing(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """Bir xil `(bozor, kalit)` uchun 60 daqiqada IKKINCHI xabar YO'Q.

    ⚠ TAKROR YO'QOLMAYDI: `occurrences` oshadi va UI uni «So'nggi soatda
      yana N marta» qatori bilan KO'RSATADI (§6.7). Bo'g'ish ma'lumot
      yashirish emas.

    ⚠⚠ 5 KAMERA, 22 EMAS — VA BU O'LCHOV NATIJASIDA TANLANDI. 22 bilan
       test `4 == 1` berdi va sabab MAHSULOTDA emas edi: 22/25 = 88 %
       `camera_offline` ni ham ko'taradi, u esa
       `NEVER_SUPPRESSED_ALERT_KEYS` da — ya'ni u BO'G'ILMASLIGI KERAK va
       bo'g'ilmadi ham. 5/25 = 20 % chegaradan past, ya'ni bu stsenariyda
       YAGONA alert `capture_missed` bo'lib qoladi va debounce AYNAN
       o'lchanadi.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        second = await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=30))

    rows = bed.alerts()
    assert [row["alert_key"] for row in rows] == ["capture_missed"], rows
    assert route.call_count == 1, "debounce oynasi ichida ikkinchi xabar ketdi"
    assert rows[0]["occurrences"] == 2, "bo'g'ilgan takror SANALMADI"
    assert second.suppressed == 1


async def test_a_repeat_after_the_debounce_window_sends_again(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """NAZORAT HOLATI: 60 daqiqadan keyin xabar QAYTA ketadi.

    Bu testsiz «bo'g'ish» va «umuman yubormaslik» bir xil ko'rinardi —
    yuqoridagi test ikkalasida ham yashil bo'lardi.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=61))

    assert route.call_count == 2, "debounce oynasidan keyin xabar qayta ketmadi"


# ===========================================================================
# 2. ESKALATSIYA — DARAJA, chastota emas
# ===========================================================================


async def test_an_old_alert_escalates_by_level_not_by_frequency(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """3 soatdan oshgan ochiq alert `warning` -> `critical` va YANGI xabar.

    ⚠ CHASTOTA OSHMAYDI: uch soat davomida jami ikki xabar ketadi
      (birinchisi va eskalatsiya), 180 ta emas.

    ⚠ 5 KAMERA — chegaradan past (20 % < 30 %), ya'ni stsenariyda YAGONA
      alert `capture_missed` bo'lib qoladi va eskalatsiya sanog'i AYNAN
      bittaga tegishli bo'ladi.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        late = await _sweep(api_sessionmaker, sender, now=moment + timedelta(hours=3, minutes=1))

    rows = bed.alerts()
    assert late.escalated == 1, f"eskalatsiya bo'lmadi: {rows}"
    assert rows[0]["severity"] == AlertSeverity.CRITICAL.value
    assert route.call_count == 2, f"eskalatsiya {route.call_count} xabar berdi"


# ===========================================================================
# 3. TIKLANISH
# ===========================================================================


async def test_recovery_closes_the_alert_and_sends_a_message(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """Manba yo'qolganda `resolved_at` qo'yiladi va TIKLANISH xabari ketadi.

    ⛔ QO'LDA YOPISH YO'Q (§6.7): ochiq alertni yopadigan yagona narsa —
       manbaning yo'qolishi. Yopish tugmasi adminga muammoni ko'rmasdan
       yashirish imkonini berardi.
    """
    slot = DEFAULT_SNAPSHOT_SLOTS[0]
    bed.fail_slot(slot)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)

        # Manba yo'qoladi: hamma qator MUVAFFAQIYATLI bo'ladi.
        bed.conn.execute(
            "UPDATE capture_runs SET status = 'succeeded', error_code = NULL WHERE market_id = %s",
            (str(bed.market_id),),
        )
        recovered = await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=5))
        bodies = _bodies(router)

    offline = [row for row in bed.alerts() if row["alert_key"] == "camera_offline"]
    assert recovered.resolved >= 1
    assert offline[0]["resolved_at"] is not None
    assert route.call_count == 2, "tiklanish xabari yuborilmadi"
    assert "capture_recovered" in bodies[-1]["text"]


# ===========================================================================
# 4. BOSTIRILMAYDIGANLAR va YURAK URISHI
# ===========================================================================


async def test_stale_heartbeat_alerts(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """26 soatdan eskirgan yurak urishi alert beradi (D-20).

    Uch holat bir joyda o'lchanadi:
      * yozuv UMUMAN yo'q (zaxira hali qurilmagan — 8-faza) -> ALERT;
      * yozuv bor va ESKIRGAN -> ALERT;
      * yozuv bor va YANGI -> alert YO'Q (nazorat holati).
    """
    bed.drop_heartbeat(BACKUP_COMPONENT)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        missing = [row["alert_key"] for row in bed.alerts()]

        bed.set_heartbeat(BACKUP_COMPONENT, hours_ago=48)
        bed.conn.execute("DELETE FROM alert_events WHERE market_id = %s", (str(bed.market_id),))
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=1))
        stale = [row["alert_key"] for row in bed.alerts()]

        bed.set_heartbeat(BACKUP_COMPONENT, hours_ago=1)
        bed.conn.execute("DELETE FROM alert_events WHERE market_id = %s", (str(bed.market_id),))
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=2))
        fresh = [row["alert_key"] for row in bed.alerts()]

    assert "backup_stale" in missing, "YOZILMAGAN yurak urishi alert bermadi"
    assert "backup_stale" in stale, "ESKIRGAN yurak urishi alert bermadi"
    assert "backup_stale" not in fresh, "YANGI yurak urishi ham alert berdi"


async def test_a_never_suppressed_alert_ignores_the_debounce_window(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ D-22 — bostirilmaydigan hodisa debounce oynasi ICHIDA ham ketadi.

    Bo'g'ilmasligi kerak bo'lgan hodisani bo'g'ish debounce YO'Q
    bo'lishidan YOMONROQ: admin tizim ishlayapti deb o'ylab turadi,
    holbuki zaxira uch kundan beri yozilmayapti.
    """
    bed.drop_heartbeat(BACKUP_COMPONENT)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=5))

    assert "backup_stale" in NEVER_SUPPRESSED_ALERT_KEYS
    assert route.call_count == 2, "bostirilmaydigan alert BO'G'ILDI"


def test_the_never_suppressed_list_is_derived_from_the_registry() -> None:
    """Ro'yxat METADAN HOSILA, qo'lda takrorlangan literal EMAS.

    ⚠ Qo'lda yozilgan nusxa BUGUN to'g'ri qiymat berardi va ertaga
      reyestrga qo'shilgan yangi kalit bilan jimgina ajralib ketardi
      (04-04 ning 6-sabotaji aynan shuni o'lchagan).
    """
    expected = {key for key, meta in ALERT_META.items() if meta.never_suppressed}
    platform = {key for key, meta in ALERT_META.items() if meta.platform_scoped}

    assert expected == NEVER_SUPPRESSED_ALERT_KEYS
    assert platform == PLATFORM_SCOPED_ALERT_KEYS
    assert "backup_stale" in platform, "platforma alerti bozor darajasiga tushib qolgan"


async def test_the_sweep_writes_its_own_heartbeat(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """Detektorning O'ZI ham kuzatiladi (D-20 ning uchinchi qatori)."""
    before = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender)

    row = bed.conn.execute(_HEARTBEAT_READ, (ALERT_SWEEP_COMPONENT,)).fetchone()
    assert row is not None, "supurgi O'Z yurak urishini yozmadi"
    assert row[0] >= before


# ===========================================================================
# 5. TELEGRAM YIQILGANDA
# ===========================================================================


async def test_a_telegram_failure_still_writes_the_row(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """Telegram `500` bersa qator YOZILADI va `notified_at` `NULL` QOLADI.

    ⚠ `NULL` YASHIRILMAYDI: UI aynan shu holatni «Telegram xabari
      YUBORILMADI» deb ko'rsatadi (§6.7). «Alert bor deb o'ylash»
      yolg'oni aynan shu qatorni yashirganda tug'ilardi.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0])

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(500, text="oops"))
        result = await _sweep(api_sessionmaker, sender)

    offline = [row for row in bed.alerts() if row["alert_key"] == "camera_offline"]
    assert len(offline) == 1, "Telegram yiqilganda qator ham yozilmadi"
    assert offline[0]["notified_at"] is None
    assert result.notified == 0


async def test_telegram_failure_does_not_block_capture(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ Telegram `500` qaytarganda `capture_tick` MUVAFFAQIYATLI tugaydi.

    =====================================================================
    KUZATUV VOSITASI KUZATILAYOTGAN TIZIMNI YIQITA OLMASLIGI KERAK.

    Bu testning butun mazmuni ALOQANING YO'QLIGINI o'lchash: alert
    supurgisi kadr olish tranzaksiyasidan TASHQARIDA va alohida
    vazifada. Ular bog'langan holatda bir soatlik Telegram nosozligi bir
    kunlik patta hisobini yo'q qilardi.
    =====================================================================
    """
    policy = CapturePolicy(
        grace_seconds=600,
        lease_seconds=120,
        max_attempts=3,
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
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0])

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(500, text="oops"))
        sweep = await _sweep(api_sessionmaker, sender)
        tick = await capture_tick(api_sessionmaker, policy=policy)

    assert sweep.notified == 0, "Telegram yiqilmadi — test o'z farazini tasdiqlayapti"
    assert tick.markets >= 1, "Telegram nosozligi kadr olish tikini to'xtatdi"


# ===========================================================================
# 6. ⛔ D-19 — RASM TAQIG'INING MEXANIK SHAKLI
# ===========================================================================


async def test_no_request_ever_carries_an_image(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ D-19 — BARCHA so'rovlar `/sendMessage` va tanasida rasm YO'Q.

    =====================================================================
    BU DARVOZA IKKI DA'VONI BIR VAQTDA O'LCHAYDI:

      1. YO'L: har bir chaqiruv `sendMessage` bilan tugaydi. Boshqa Bot
         API metodi (rasm, hujjat, media guruh) UMUMAN chaqirilmaydi.
      2. TANA: birorta so'rovda rasmga tegishli maydon ham, ombor kaliti
         ham, `http` havolasi ham yo'q.

    Kadr — bozor tashrifchilarining SHAXSIY MA'LUMOTI, Telegram
    serverlari esa O'zR data-rezidentlik chegarasidan TASHQARIDA. Bir
    marta yuborilgan baytni QAYTARIB BO'LMAYDI.

    ⚠ Bu darvoza `AlertSender` da rasm biriktiruvchi metod
      YO'QLIGINING jufti: birinchisi STRUKTURANI, bu esa XULQNI
      o'lchaydi. Ikkalasi ham kerak — metod bir kun qo'shilsa, bu test
      uni ISHLATILGAN paytda ushlaydi.
    =====================================================================
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0])
    bed.drop_heartbeat(BACKUP_COMPONENT)

    async with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=r"https://api\.telegram\.org/.*").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await _sweep(api_sessionmaker, sender)
        await daily_digest(api_sessionmaker, sender, business_date=bed.today)
        calls = list(router.calls)

    assert calls, "birorta so'rov tutilmadi — test o'z farazini tasdiqlayapti"
    for call in calls:
        assert call.request.url.path.endswith(f"/{TELEGRAM_SEND_METHOD}"), call.request.url.path
        body = json.loads(call.request.content)
        assert set(body) <= {"chat_id", "text", "parse_mode", "disable_web_page_preview"}, body
        assert "http" not in body["text"], f"xabarda havola bor: {body['text']}"
        assert ".jpg" not in body["text"], f"xabarda obyekt kaliti bor: {body['text']}"


def test_the_detail_allowlist_matches_the_ui_contract() -> None:
    """`alert_events.detail` FAQAT oltita kalitni qabul qiladi (§6.7, D-19).

    ⚠ ALLOWLIST YOZISH PAYTIDA qo'yiladi, render paytida emas. UI noma'lum
      kalitni ko'rsatmaydi, lekin u BAZAGA baribir yozilardi va u yerdan
      zaxiraga, zaxiradan esa tashqi bucketga chiqardi.
    """
    assert {
        "market_name",
        "camera_count",
        "error_code",
        "slot_time",
        "stale_hours",
        "disk_pct",
    } == ALERT_DETAIL_KEYS


# ===========================================================================
# 7. KUNLIK DAYJEST
# ===========================================================================


async def test_the_daily_digest_is_one_message_per_market(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """Har bozor uchun BITTA xabar va u `day_summary` dan chiziladi."""
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=3)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        result = await daily_digest(api_sessionmaker, sender, business_date=bed.today)
        bodies = _bodies(router)

    assert route.call_count == result.markets, "bozor soni bilan xabar soni mos emas"
    assert result.sent == result.markets
    digest = next(body["text"] for body in bodies if str(bed.market_id) in body["text"])
    assert "kadrlar: 22/25" in digest, digest
    # ⚠ `missed`, `failed` EMAS: manba `mark_missed()` yozadigan qator —
    #   D-20 ning yagona manbai (`fail_slot` ning standarti).
    assert "missed=3" in digest, digest


async def test_alerts_disabled_never_raises_and_never_calls(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    bed: _Bed,
) -> None:
    """Bo'sh token bilan supurgi ISHLAYDI, lekin tarmoqqa CHIQMAYDI.

    ⚠ Qator BARIBIR yoziladi: alertlar o'chiq bo'lgani muammoning
      yo'qligini bildirmaydi va UI uni ko'rsatishi SHART.
    """
    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0])
    silent = AlertSender(token=SecretStr(""), chat_id="", enabled=False)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(url__regex=r"https://api\.telegram\.org/.*")
        result = await _sweep(api_sessionmaker, silent)

    await silent.aclose()
    assert route.call_count == 0, "o'chirilgan jo'natuvchi tarmoqqa chiqdi"
    assert result.notified == 0
    assert [row["alert_key"] for row in bed.alerts()], "alert qatori yozilmadi"
