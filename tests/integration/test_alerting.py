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

import asyncio
import inspect
import json
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import pytest
import respx
from app import worker
from app.jobs.alerting import (
    ALERT_DETAIL_KEYS,
    ALERT_META,
    ALERT_SWEEP_COMPONENT,
    BACKUP_COMPONENT,
    NEVER_SUPPRESSED_ALERT_KEYS,
    NOTIFICATION_STALE_MINUTES,
    PLATFORM_SCOPED_ALERT_KEYS,
    alert_sweep,
    daily_digest,
)
from app.jobs.billing_close import BILLING_CLOSE_COMPONENT
from app.jobs.capture import CapturePolicy, capture_tick
from app.jobs.notifications import (
    DIGEST_EVENING_COMPONENT,
    DIGEST_MORNING_COMPONENT,
    OVERDUE_COMPONENT,
)
from app.jobs.outbox import OUTBOX_COMPONENT
from app.jobs.reconciliation import RECON_OPEN_COMPONENT
from app.jobs.retention import RETENTION_COMPONENT
from app.services.alerts import (
    TELEGRAM_API_BASE,
    TELEGRAM_SEND_METHOD,
    AlertSender,
    SendFailure,
)
from app.services.quality import QualityThresholds
from fixtures.nvr_domain import nvr_rows
from pydantic import SecretStr
from sbozor_core.enums import AlertSeverity, CaptureMethod, CaptureRunStatus, OutboxStatus
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import MARKET_TZ, business_date, business_today
from taskiq import Context, TaskiqMessage, TaskiqState

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date
    from uuid import UUID

    from app.settings import Settings
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

_PLATFORM_COMPONENTS = (
    BACKUP_COMPONENT,
    RETENTION_COMPONENT,
    BILLING_CLOSE_COMPONENT,
    OUTBOX_COMPONENT,
    RECON_OPEN_COMPONENT,
    DIGEST_MORNING_COMPONENT,
    DIGEST_EVENING_COMPONENT,
    OVERDUE_COMPONENT,
)
"""Platforma darajasidagi yurak urishlari — `bed` ularni YANGI qilib qo'yadi.

Sabab `bed` fixture'ining docstringida: ular yo'q bo'lganda supurgi HAR
YUGURISHDA platforma alertini ko'taradi va bozor guruhlashining o'lchovini
shovqin bilan aralashtiradi.

⚠ `BILLING_CLOSE_COMPONENT` 06-07 DA QO'SHILDI VA SABAB O'LCHANDI, uslub
  emas: u `watched` ga qo'shilgan zahoti guruhlash testlarining
  `route.call_count == 1` da'vosi 2 ga chiqardi — mahsulot TO'G'RI ishlab
  turgan holda (yurak urishi hali yozilmagan). Ro'yxatga qo'shish o'sha
  shovqinni CHIQARIB tashlaydi; `billing_close_stale` ning O'ZI esa
  pastdagi ALOHIDA testda IKKI YO'NALISHDA o'lchanadi.

⚠⚠ OXIRGI TO'RTTASI 07-14 DA QO'SHILDI VA NOSOZLIK AYNAN TAKRORLANDI —
   TAXMIN QILINMADI, O'LCHANDI: `watched` to'rt juftlik bilan o'sgach
   BESHTA guruhlash testi `assert 4 == 2` / `assert 2 == 1` bilan qizardi.
   Sabab yana MAHSULOTDA emas, TEST SHARTIDA edi (yangi joblar bu seedda
   hech qachon yugurmaydi, ya'ni ularning yurak urishi YO'Q va `None` HAM
   ESKIRISH).

⛔ RO'YXAT NOMLARNI IMPORT QILADI, literal yozmaydi: nom ayrilsa shovqin
   JIMGINA qaytardi va keyingi ishlovchi uni «flaky test» deb o'qirdi.
   To'rtala kalitning O'ZI esa pastdagi `test_missing_new_heartbeat_
   raises_an_alert` da XULQ bilan o'lchanadi.

⚠⚠ 07-21 DA RO'YXAT YETTIGA O'SDI (WR-10): bitta `notify_digest` o'rniga
   IKKI komponent (`notify_digest_morning` / `notify_digest_evening`) va
   ikkalasi ham `watched` da. `bed` ularning IKKALASINI ham yangi qilib
   qo'yishi SHART — bittasi qoldirilganda guruhlash testlari yana
   `assert 2 == 1` bilan qizarardi va sabab MAHSULOTDA emas, seedda
   bo'lardi (07-14 da AYNAN shu nosozlik o'lchangan).
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

_INSERT_OUTBOX = (
    "INSERT INTO notification_outbox "
    "(id, market_id, kind, recipient_kind, vendor_id, dedupe_key, payload, status, "
    " attempt_count, next_attempt_at, last_error_type, created_at, updated_at) "
    "VALUES (%s, %s, %s, 'market_director', NULL, %s, '{}'::jsonb, %s, %s, %s, %s, %s, %s)"
)
"""Navbat qatorini QO'LDA yozadi — ⛔ `created_at` ARGUMENT.

⚠ `created_at` odatda `server_default = now()` bilan to'ladi, ya'ni «90
  daqiqa oldin navbatga tushgan xabar» holatini soatni siljitmasdan
  qurishning yagona yo'li — ustunni OSHKORA yozish (`alert_sweep(...,
  now=...)` bilan aynan bir xil qaror: vaqt ARGUMENT bo'ladi, global
  emas).

⛔ QABUL QILUVCHI — DIREKTOR (`recipient_kind = 'market_director'`,
   `vendor_id NULL`): `RECIPIENT_MATCHES_VENDOR_CHECK` ikki tomonlama
   tenglik va `vendor` shoxi mavjud sotuvchi qatorini talab qilardi.
   Alert manbai qabul qiluvchini UMUMAN ajratmaydi, ya'ni bu tanlov
   o'lchovga ta'sir qilmaydi va seedni yengil qoldiradi.
"""


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
        days_ago: int = 0,
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
                days_ago=days_ago,
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

    def write_outbox(
        self,
        *,
        minutes_ago: float,
        status: str = OutboxStatus.PENDING.value,
        attempt_count: int = 0,
        next_attempt_in_minutes: float = 0.0,
        last_error_type: str | None = None,
    ) -> None:
        """Navbatga bitta qator qo'yadi — YOSHI va KELAJAGI alohida boshqariladi.

        ⚠ IKKI VAQT MUSTAQIL: `minutes_ago` — qator NAVBATDA TURGAN vaqti
          (`created_at`), `next_attempt_in_minutes` esa keyingi urinish
          nuqtasi (`next_attempt_at`). Ularni bitta argumentga qo'shish
          `defer_unresolved()` ning aynan shaklini (o'tmishdagi `created_at`
          + KELAJAKDAGI `next_attempt_at`) qurib bo'lmas qilardi.
        """
        moment = datetime.now(tz=MARKET_TZ)
        created_at = moment - timedelta(minutes=minutes_ago)
        self.conn.execute(
            _INSERT_OUTBOX,
            (
                str(uuid4()),
                str(self.market_id),
                "digest_evening",
                f"zond:{uuid4()}",
                status,
                attempt_count,
                moment + timedelta(minutes=next_attempt_in_minutes),
                last_error_type,
                created_at,
                created_at,
            ),
        )


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
            # ⚠ NAVBAT HAM TOZALANADI: qolgan `pending` qator KEYINGI testda
            #   `notification_stale` ni ko'tarib, guruhlash da'volarini
            #   («bitta xabar») jimgina buzardi — bu `_PLATFORM_COMPONENTS`
            #   ro'yxatining tug'ilish sababi bilan AYNAN bir xil sinf.
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = ANY(%s::uuid[])", (market_ids,)
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


def _explode(*_args: object, **_kwargs: object) -> Any:
    """Chaqirilishi DARVOZANING BUZILGANINI bildiradigan sentinel.

    ⚠ `AssertionError` ATAYIN, `RuntimeError` EMAS: `alert_sweep` ning
      birinchi qadami `SQLAlchemyError` ni YUTADI, ya'ni o'sha oiladagi
      istisno jimgina bosilib, nazorat bandi hech nimani o'lchamasdi.
    """
    raise AssertionError(
        "`sessionmaker` chaqirildi — vazifa `alerts_enabled` chegarasini chetlab o'tdi (Pitfall 9)"
    )


def _worker_context(sender: AlertSender, *, alerts_enabled: bool) -> Context:
    """`TaskiqState` ni bazasiz quradi — vazifalar faqat SHU uch nomni o'qiydi.

    ⚠ HAQIQIY `Context` VA HAQIQIY VAZIFA: `alert_sweep_task` mahsulot
      kodining O'ZI bo'lib qoladi, faqat uning resurslari sentinel bilan
      almashtiriladi. Vazifani qayta yozib «shunday ishlaydi» deb o'lchash
      chegarani mahsulotdan UZARDI.
    """
    state = TaskiqState()
    state.sessionmaker = _explode
    state.sender = sender
    state.alerts_enabled = alerts_enabled
    context = Context(
        TaskiqMessage(task_id="pytest", task_name="pytest", labels={}, args=[], kwargs={}),
        worker.broker,
    )
    context.state = state
    return context


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

    ⚠⚠ SIGNAL IKKI BIZNES-KUNGA YOZILADI — `test_an_old_alert_escalates_
      by_level_not_by_frequency` dagi bilan AYNAN bir xil sabab (`dc5f182`).
      Kech supurgi kunni `business_date(moment + 30 daq)` dan oladi
      (`alerting.py:487,668`), ya'ni Toshkent vaqti bilan 23:30 dan keyin
      u ERTANGI kun bo'ladi. Signal faqat bugunga yozilsa, kech supurgi
      BO'SH kunni ko'rib alertni bo'g'ish o'rniga YOPARDI va yopilish
      xabari IKKINCHI chaqiruv bo'lib chiqardi. O'lchandi: 23:37 da
      `resolved=1` va `assert 2 == 1`.
    """
    moment = datetime.now(tz=MARKET_TZ)
    late_moment = moment + timedelta(minutes=30)

    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    if business_date(late_moment) != bed.today:
        bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5, days_ago=-1)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        second = await _sweep(api_sessionmaker, sender, now=late_moment)

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

    ⚠⚠ BU NAZORAT TESTI KUN CHEGARASIDA YOLG'ON-YASHIL BERARDI va u
      qo'shni testdan ham YOMONROQ holat edi: 22:59 dan keyin ikkinchi
      supurgi ERTANGI bo'sh kunni ko'rib alertni YOPARDI, yopilish
      xabari esa `call_count` ni AYNAN 2 GA yetkazardi — ya'ni assert
      qanoatlanardi, lekin u o'lchayotgan narsa «debounce oynasidan
      keyin QAYTA yuborish» emas, «alert yopildi» bo'lardi. Bir xil
      langar ikkala testni ham o'sha sinfdan chiqaradi.
    """
    moment = datetime.now(tz=MARKET_TZ)
    late_moment = moment + timedelta(minutes=61)

    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    if business_date(late_moment) != bed.today:
        bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5, days_ago=-1)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        await _sweep(api_sessionmaker, sender, now=late_moment)

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

    ⚠⚠ SIGNAL IKKI BIZNES-KUNGA YOZILADI va bu bezak emas. `moment` ni
      QOTIRIB BO'LMAYDI: `first_seen_at` DB soatidan keladi (server
      default), ya'ni eskalatsiya arifmetikasi (`first_seen_at <=
      moment - 3s`) haqiqiy vaqtga langarlangan. Kech supurgi esa kunni
      `business_date(moment + 3s01d)` dan oladi (`alerting.py:487,668`) —
      Toshkent vaqti bilan 20:59 dan keyin u ERTANGI kun bo'ladi. Signal
      faqat bugunga yozilsa, kech supurgi bo'sh kunni ko'rib alertni
      eskalatsiya qilish o'rniga YOPARDI va test har kuni kechqurun
      qizarardi — mahsulotda emas, o'lchov qurilmasida bo'lgan nosozlik.
    """
    moment = datetime.now(tz=MARKET_TZ)
    late_moment = moment + timedelta(hours=3, minutes=1)

    bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5)
    if business_date(late_moment) != bed.today:
        bed.fail_slot(DEFAULT_SNAPSHOT_SLOTS[0], count=5, days_ago=-1)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        late = await _sweep(api_sessionmaker, sender, now=late_moment)

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


async def test_a_missing_billing_close_heartbeat_is_visible(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ M-C — «CRON RO'YXATGA OLINMAGAN» HOLATI ENDI ALERT BERADI (06-07).

    =========================================================================
    ⛔⛔ BU DARVOZA MEXANIK RAVISHDA USHLANMAYDIGAN BANDNING YAGONA HIMOYASI.

    `billing.close` cron jadvali `import` PAYTIDA olinadi
    (`worker.py:55-58`), ya'ni deployda `scheduler` konteyneri qayta ishga
    tushirilmasa vazifa RO'YXATGA OLINMAYDI: patta hisobi hech qachon
    yozilmaydi, xato ham chiqmaydi, jurnalda ham hech nima qolmaydi.
    Birorta test buni ushlay olmaydi — testlar reyestrni jarayonning
    O'ZIDA o'qiydi.

    `None` HAM ESKIRISH qoidasi (`_platform_signals` dagi ⚠⚠) aynan shu
    holatni alertga aylantiradi: qator UMUMAN yozilmagan bo'lsa ham
    `billing_close_stale` ochiladi.

    =========================================================================
    ⛔ DA'VO IKKI YO'NALISHLI VA BUSIZ U BO'SH BO'LARDI:

      * yurak urishi YO'Q  -> alert OCHILADI;
      * yurak urishi YANGI -> alert OCHILMAYDI.

    Faqat birinchisi yozilganda «supurgi har doim alert ochadi» degan
    nosozlik ham yashil qolardi.
    =========================================================================
    """
    bed.drop_heartbeat(BILLING_CLOSE_COMPONENT)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        missing = [row["alert_key"] for row in bed.alerts()]

        bed.set_heartbeat(BILLING_CLOSE_COMPONENT, hours_ago=1)
        bed.conn.execute("DELETE FROM alert_events WHERE market_id = %s", (str(bed.market_id),))
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=1))
        fresh = [row["alert_key"] for row in bed.alerts()]

    assert "billing_close_stale" in missing, (
        "`billing_close` yurak urishi UMUMAN yozilmagan holat alert BERMADI — "
        "«cron ro'yxatga olinmagan» nosozligi jimgina qolardi (M-C)"
    )
    assert "billing_close_stale" not in fresh, (
        "YANGI yurak urishi ham alert berdi — supurgi har yugurishda shovqin qo'shardi"
    )
    assert "billing_close_stale" in PLATFORM_SCOPED_ALERT_KEYS, (
        "platforma alerti bozor darajasiga tushib qolgan — u har bozorga alohida "
        "Telegram xabari bo'lib chiqardi"
    )


async def test_missing_new_heartbeat_raises_an_alert(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ D-17 — 7-FAZANING FON OQIMI HAM «JIMGINA O'LA OLMAYDI» (07-14).

    =========================================================================
    ⛔⛔ BU `deferred-items.md` NING 2-BANDINI YOPADIGAN YAGONA XULQIY
        O'LCHOV.

    O'sha band aynan shunday edi: yurak urishi YOZILADI, lekin uning
    YO'QLIGI hech qayerda ko'rinmasdi. `notify.outbox_tick` uchun bu
    nosozlik eng qimmat shaklda chiqardi — navbat to'xtasa KVITANSIYA ham
    ketmaydi (CASH-05) va sotuvchi to'laganini isbotlay olmaydi (D-02),
    ya'ni mahsulotning butun dalil zanjiri JIMGINA uzilardi.

    Reyestr tengligi `tests/unit/test_heartbeat_registry.py` da STRUKTURA
    sifatida o'lchanadi. Bu test esa boshqa savolga javob beradi: reyestr
    to'g'ri bo'lsa ham, `None` HAM ESKIRISH qoidasi HAQIQATAN alert
    ochadimi? Ikkalasi mustaqil buziladi.
    =========================================================================

    ⛔ DA'VO IKKI YO'NALISHLI (`test_a_missing_billing_close_heartbeat_is_
       visible` bilan aynan bir xil qoida): yurak urishi YO'Q -> alert
       OCHILADI; YANGI -> alert OCHILMAYDI. Faqat birinchisi yozilganda
       «supurgi har doim alert ochadi» degan nosozlik ham yashil qolardi.
    """
    bed.drop_heartbeat(OUTBOX_COMPONENT)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        missing = [row["alert_key"] for row in bed.alerts()]

        bed.set_heartbeat(OUTBOX_COMPONENT, hours_ago=1)
        bed.conn.execute("DELETE FROM alert_events WHERE market_id = %s", (str(bed.market_id),))
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=1))
        fresh = [row["alert_key"] for row in bed.alerts()]

    assert "outbox_stale" in missing, (
        "`outbox_tick` yurak urishi UMUMAN yozilmagan holat alert BERMADI — "
        "ro'yxatga olinmagan cron jimgina o'lardi va u bilan birga kvitansiya ham "
        "(`deferred-items.md` 2-bandi)"
    )
    assert "outbox_stale" not in fresh, (
        "YANGI yurak urishi ham alert berdi — supurgi har yugurishda shovqin qo'shardi"
    )
    assert ALERT_META["outbox_stale"].never_suppressed is True, (
        "to'xtagan navbat alerti debounce oynasida bo'g'ildi — butun savdo kunining "
        "kvitansiyalari to'planib turgan bir soatda xabar KECHIKARDI"
    )
    assert "outbox_stale" in PLATFORM_SCOPED_ALERT_KEYS, (
        "platforma alerti bozor darajasiga tushib qolgan — u har bozorga alohida "
        "Telegram xabari bo'lib chiqardi"
    )


async def test_a_dead_morning_digest_is_visible_while_the_evening_one_lives(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔⛔ WR-10 — YARIM O'LGAN DAYJEST JUFTLIGI ENDI KO'RINADI (07-21).

    =========================================================================
    ⛔ ILGARI BU HOLAT STRUKTURAVIY RAVISHDA KO'RINMAS EDI.

    Ikkala job ham BITTA `notify_digest` qatorini yangilardi, ya'ni kechki
    job har kuni 20:45 da o'sha qatorni YANGILAB turardi va ertalabki job
    butunlay o'lgan bo'lsa ham yurak urishi HAMON YANGI ko'rinardi:
    `digest_stale` HECH QACHON ko'tarilmasdi. D-20 ning «alert MUVAFFAQIYAT
    SIGNALINING YO'QLIGIGA qo'yiladi» qoidasi yarim ishlardi — signal ikki
    jobning YO'QLIGINI bitta qatorga qo'shib yuborardi.

    ⛔ DA'VO IKKI YO'NALISHLI (`test_missing_new_heartbeat_raises_an_alert`
       bilan aynan bir xil qoida): ertalabkisi o'lgan -> alert OCHILADI;
       IKKALASI ham yangi -> alert OCHILMAYDI. Faqat birinchisi
       yozilganda «supurgi har doim `digest_stale` ochadi» degan nosozlik
       ham yashil qolardi.
    =========================================================================
    """
    # Kechkisi TIRIK, ertalabkisi O'LIK — aynan yashiringan holat.
    bed.set_heartbeat(DIGEST_EVENING_COMPONENT, hours_ago=1)
    bed.drop_heartbeat(DIGEST_MORNING_COMPONENT)
    moment = datetime.now(tz=MARKET_TZ)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender, now=moment)
        half_dead = [row["alert_key"] for row in bed.alerts()]

        bed.set_heartbeat(DIGEST_MORNING_COMPONENT, hours_ago=1)
        bed.conn.execute("DELETE FROM alert_events WHERE market_id = %s", (str(bed.market_id),))
        await _sweep(api_sessionmaker, sender, now=moment + timedelta(minutes=1))
        both_fresh = [row["alert_key"] for row in bed.alerts()]

    assert "digest_stale" in half_dead, (
        "ertalabki dayjest o'lgan, kechkisi tirik — `digest_stale` KO'TARILMADI. "
        "Ikki job hamon bitta yurak urishini bo'lishyapti, ya'ni WR-10 ochiq "
        "(kechki job ertalabkisining o'limini har kuni YASHIRARDI)"
    )
    assert "digest_stale" not in both_fresh, (
        "ikkala yurak urishi ham YANGI bo'lgan holatda ham alert ochildi — "
        "supurgi har yugurishda shovqin qo'shardi"
    )


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
# 4b. ⛔ NAVBAT QOTDI — «JOB TIRIK, LEKIN NATIJA YO'Q» (Topilma №I)
#
# ⛔⛔ MAVJUD `outbox_stale` BU HOLATNI KO'RMAYDI VA BU O'LCHANGAN, TAXMIN
#     EMAS. Uning manbai `system_heartbeats['outbox_tick']`, ya'ni JOBNING
#     TIRIKLIGI. Kuzatilgan nosozlikda job tirik va HAR DAQIQADA yuguradi
#     (`OUTBOX_TICK_CRON = "* * * * *"`) — shunchaki navbat BO'SHAMAYDI.
#     Yurak urishi yangi, demak `outbox_stale` HECH QACHON ko'tarilmaydi.
#
#     D-20 ning uchta jimligidan IKKINCHISI («ish bajarildi, natija yomon»)
#     shu yerda materializatsiya qilinadi: manba — YURAK URISHI emas,
#     NAVBATNING O'ZI.
# ===========================================================================


async def test_a_frozen_queue_raises_a_market_level_alert(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ 30 daqiqadan uzoq `pending` turgan xabar ALERT beradi (Topilma №I).

    =========================================================================
    KUZATILGAN HOLAT: kvitansiya 18+ soat «Navbatda» turdi, hech qanday
    alert bo'lmadi va uni FAQAT direktor ekranga qarab topdi. Prodda bu
    «sotuvchi kvitansiya olmayapti va hech kim sezmayapti» — D-02 (nizodagi
    dalil) ning to'g'ridan-to'g'ri yo'qolishi.
    =========================================================================

    ⚠ DARAJA `warning` VA BU ONGLI: `outbox_stale` (`critical`) jobning
      O'LIMI — u o'z-o'zidan tuzalmaydi. Bu esa DAVOM ETAYOTGAN holat va
      mavjud `ESCALATION_HOURS` (3 soat) mexanizmi uni `critical` ga
      KO'TARADI, ya'ni o'tkinchi uzilish bilan haqiqatan qotgan navbat
      AJRALADI. `critical` bo'lib tug'ilsa eskalatsiya shoxi ikkalasini
      bir xil ko'rsatardi.
    """
    bed.write_outbox(minutes_ago=90)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender)

    stale = [row for row in bed.alerts() if row["alert_key"] == "notification_stale"]

    assert len(stale) == 1, (
        f"90 daqiqadan beri navbatda turgan xabar uchun {len(stale)} qator yozildi — "
        "qotgan navbat JIMGINA qoldi va uni faqat ekranga qaragan odam topardi"
    )
    assert stale[0]["severity"] == AlertSeverity.WARNING.value, (
        "alert `critical` bo'lib tug'ildi — o'shanda `ESCALATION_HOURS` mexanizmi "
        "o'tkinchi uzilishni qotgan navbatdan AJRATA olmasdi"
    )
    assert stale[0]["subject_id"] is None, (
        "signal bitta xabarga bog'landi — 500 qatorli navbat 500 ta alert berardi"
    )


async def test_a_young_queue_stays_silent(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔ SALBIY NAZORAT: yangi qator alert BERMAYDI.

    Ikkala yo'nalish ham o'lchanadi — aks holda «har doim rost» qaytaradigan
    shox (masalan `pending_count > 0` sharti) yashil turardi va supurgi har
    yugurishda shovqin qo'shardi (D-22: shovqin alert kanalini o'ldiradi).
    """
    bed.write_outbox(minutes_ago=5)

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender)

    keys = [row["alert_key"] for row in bed.alerts()]

    assert "notification_stale" not in keys, (
        f"navbatga endigina ({NOTIFICATION_STALE_MINUTES} daqiqadan kam) tushgan qator "
        "alert berdi — chegara umuman qo'llanmayapti"
    )


async def test_a_future_next_attempt_cannot_hide_a_frozen_queue(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    bed: _Bed,
) -> None:
    """⛔⛔ ENG MUHIM O'LCHOV: MANBA `created_at`, `next_attempt_at` EMAS.

    =========================================================================
    Qator AYNAN `outbox_repo.defer_unresolved()` ning shaklida yoziladi
    (`outbox_repo.py::_DEFER_UNRESOLVED`):

        status          = 'pending'              (o'zgarmaydi)
        next_attempt_at = now + 15 daqiqa        (OLDINGA suriladi)
        last_error_type = 'UnresolvedRecipient'
        attempt_count   — ⛔ UMUMAN OSHIRILMAYDI

    Shundan ikki xulosa chiqadi va ikkalasi ham shu testda qulflanadi:

      * URINISHLAR SONI BO'YICHA chegara bu nosozlikni KO'RMASDI —
        `attempt_count` mangu 0 bo'lib qoladi (bu mahsulotning TO'G'RI
        xulqi: manzilsiz shox urinish sanamaydi);
      * `next_attempt_at` MANBA SIFATIDA YAROQSIZ — u har 15 daqiqada
        oldinga suriladi, ya'ni supurgi qaragan payt `next_attempt_at <=
        now` sharti deyarli HECH QACHON rost bo'lmaydi.

    ⛔ Kimdir manbani `created_at` dan `next_attempt_at` ga almashtirsa
       AYNAN SHU test qizaradi — chegaraning o'zi emas, MANBA TANLOVI
       mexanik ravishda qulflangan.
    =========================================================================
    """
    bed.write_outbox(
        minutes_ago=90,
        attempt_count=0,
        next_attempt_in_minutes=15,
        last_error_type="UnresolvedRecipient",
    )

    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
        await _sweep(api_sessionmaker, sender)

    keys = [row["alert_key"] for row in bed.alerts()]

    assert "notification_stale" in keys, (
        "kelajakdagi `next_attempt_at` alertni YASHIRDI — manba navbat YOSHI "
        "(`created_at`) emas, keyingi urinish nuqtasi bo'lib qolgan. Kuzatilgan "
        "nosozlikda (18 soat, urinishlar = 0) alert AYNAN shu sababdan chiqmasdi"
    )


def test_the_frozen_queue_alert_is_market_scoped() -> None:
    """⛔ Alert BOZOR darajasida — `notification_outbox` TENANT jadvali.

    `platform_scoped=True` bo'lsa ikki bozorning navbati bitta Telegram
    xabariga birlashardi va ikkinchi bozor direktori O'Z qotgan navbatini
    UMUMAN ko'rmasdi — `vendor_binding_conflict` bilan aynan bir xil sabab.
    """
    assert "notification_stale" in ALERT_META, (
        "kalit reyestrga olinmagan — `_upsert()` `ALERT_META[key]` ustida `KeyError` "
        "berardi va (xato yutilsa) alert JIMGINA yo'qolardi"
    )
    assert "notification_stale" not in PLATFORM_SCOPED_ALERT_KEYS, (
        "bozor darajasidagi alert platformaga ko'tarildi — ikkinchi bozor direktori "
        "o'z navbatining qotganini ko'rmasdi"
    )
    assert ALERT_META["notification_stale"].never_suppressed is False, (
        "alert debounce'dan chiqarilgan — botga hali ulanmagan sotuvchining xabari "
        "navbatda 72 soatgacha QONUNIY turadi va bo'g'ilmagan kalit o'sha davrda "
        "har supurgida xabar berardi (D-22 ning «75 ta xabar» sinfi)"
    )


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
    """`alert_events.detail` FAQAT sakkizta kalitni qabul qiladi (§6.7, D-19).

    ⚠ ALLOWLIST YOZISH PAYTIDA qo'yiladi, render paytida emas. UI noma'lum
      kalitni ko'rsatmaydi, lekin u BAZAGA baribir yozilardi va u yerdan
      zaxiraga, zaxiradan esa tashqi bucketga chiqardi.

    ⚠ OXIRGI IKKITASI (Topilma №I) — IKKALASI HAM BUTUN SON: navbatning
      yoshi va uning hajmi. Sotuvchi ismi, telefoni, `chat_id` yoki xabar
      matni uchun kalit YO'Q va qo'shilmaydi: `notification_stale` alerti
      Telegramga ham ketadi, Telegram serverlari esa loyiha zimmasiga
      olgan O'zR data-rezidentlik chegarasidan TASHQARIDA.
    """
    assert {
        "market_name",
        "camera_count",
        "error_code",
        "slot_time",
        "stale_hours",
        "disk_pct",
        "stale_minutes",
        "pending_count",
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


# ===========================================================================
# 8. ⛔ 07-06 — YUZA O'SMADI VA OPS CHATI KVITANSIYANI O'CHIRMAYDI
# ===========================================================================


def test_sender_public_surface_did_not_grow() -> None:
    """⛔ D-19/D-23 — `AlertSender` ning ommaviy nomlari AYNAN to'rtta.

    =======================================================================
    ⛔ TO'PLAM TENGLIGI, `len()` EMAS.

    Sanoq bir nomni ikkinchisiga ALMASHTIRISHNI umuman ko'rmasdi:
    `send_message` o'chib `send_photo` qo'shilsa uzunlik hamon 3 bo'lardi
    va darvoza yashil qolardi — ya'ni u aynan o'zi to'sishi kerak bo'lgan
    o'zgarishni o'tkazib yuborardi.

    ⚠ 07-06 BU DARVOZANI KENGAYTIRMADI: `chat_id` METOD emas, ARGUMENT
      bo'lib qo'shildi (pastdagi test).

    =======================================================================
    ⛔⛔ 07-09 TO'PLAMGA AYNAN BITTA NOM QO'SHDI: `last_failure`.

    NIMA QO'SHILDI: oxirgi urinishning SIRSIZ natijasi — status kodi, xato
    TURI va Telegram bergan `retry_after`. Boshqa hech nima.

    NEGA QO'SHILDI (bloklovchi bo'shliq edi, qulaylik emas): `send_message()`
    `bool` qaytaradi (3-taqiq) va `bool` `403` ni `429` dan AJRATMAYDI.
    Outbox uchun esa bu farq butun marshrutlashning o'zi — `403` ->
    `blocked` va qayta urinish YO'Q (D-22), `429` -> `retry_after` bilan
    navbatga qaytish (DQ-3). Farqsiz job bloklangan foydalanuvchini mangu
    qayta urinardi va chegaraga urilgan xabarni butunlay yo'qotardi.

    NEGA XOSSA, NEGA METOD EMAS: metod AMALNI bildiradi va o'quvchi har
    safar «bu ikkinchi so'rov yubormaydimi?» degan savolni qaytadan
    berardi. Bu yerda hech qanday amal yo'q — chaqiruv allaqachon bo'lgan
    va o'qilayotgani uning HOLATI.

    NEGA BU 1-TAQIQNI KUCHSIZLANTIRMAYDI: yangi Bot API METODI
    QO'SHILMADI. `TELEGRAM_SEND_METHOD` hamon yagona qiymat va rasm/hujjat/
    media metodlari bu sinfda HAMON YO'Q.

    ⛔ TO'PLAM LITERAL VA MAHSULOTDAN IMPORT QILINMAYDI (05-15 darsi):
       import darvozani o'zi tekshirayotgan qiymatga bog'lardi va yangi
       metod qo'shilganda ro'yxat JIMGINA kengayardi.
    =======================================================================

    ⚠ KONTEKST MENEJERI DUNDER, ya'ni bu to'plamga TUSHMAYDI — shuning
      uchun uning mavjudligi ALOHIDA assert bilan qulflangan: `aclose`
      dunderlarsiz qolsa `AsyncExitStack` ga yozilgan resurs jimgina
      yopilmasdan qolardi.
    """
    public = {name for name in dir(AlertSender) if not name.startswith("_")}

    assert public == {"aclose", "enabled", "last_failure", "send_message"}, (
        f"`AlertSender` ning ommaviy yuzasi o'zgardi: {sorted(public)}. Har bir "
        "yangi metod yangi savol talab qiladi («bu chaqiruvda shaxsiy ma'lumot "
        "bormi?») va rasm/hujjat/media metodlari bu faylda ATAYIN YO'Q (D-19)."
    )
    assert isinstance(AlertSender.__dict__["last_failure"], property), (
        "`last_failure` METODGA aylandi — u HOLAT, amal emas va metod shakli "
        "«bu chaqiruv ikkinchi so'rov yubormaydimi?» degan savolni qaytarardi"
    )
    assert hasattr(AlertSender, "__aenter__") and hasattr(AlertSender, "__aexit__"), (
        "kontekst menejeri metodlari yo'qoldi — `AsyncExitStack` ga yozilgan "
        "jo'natuvchi jimgina yopilmasdan qolardi"
    )


def test_send_message_accepts_chat_id_without_new_method() -> None:
    """⛔ D-23 — `chat_id` KALIT-ONLY argument, standarti `None`.

    =======================================================================
    IKKALA XOSSA HAM O'LCHANADI VA IKKALASI HAM SABABLI:

      * KALIT-ONLY — pozitsion chaqiruv (`send_message(text, chat_id)`)
        matn va manzilni O'RIN bilan ajratardi va bir kun ular joyini
        almashtirganda MANZIL matn sifatida yuborilardi;
      * STANDART `None` — mavjud chaqiruvchilar (`alerting.py` ning
        supurgisi va dayjesti) TEGILMAY qoladi, ya'ni bu o'zgarish
        kengaytma, sinish emas.

    ⚠ `TELEGRAM_SEND_METHOD` ham shu yerda qulflanadi: u YAGONA Bot API
      metodi bo'lib qolishi 1-taqiqning butun mazmuni.
    =======================================================================
    """
    parameters = inspect.signature(AlertSender.send_message).parameters

    assert "chat_id" in parameters, (
        "`send_message` `chat_id` argumentini qabul qilmaydi — outbox "
        "sotuvchining shaxsiy chatiga yoza olmasdi va yagona chiqish yo'li "
        "IKKINCHI jo'natuvchi sinf bo'lardi (D-23)"
    )
    assert parameters["chat_id"].kind is inspect.Parameter.KEYWORD_ONLY, (
        "`chat_id` pozitsion bo'lib qoldi — matn bilan manzil o'rin almashganda "
        "manzil xabar matni sifatida ketardi"
    )
    assert parameters["chat_id"].default is None, (
        "`chat_id` ning standarti `None` emas — mavjud chaqiruvchilar (supurgi, "
        "dayjest) sinardi va o'zgarish kengaytma bo'lmasdi"
    )
    assert TELEGRAM_SEND_METHOD == "sendMessage", (
        "yagona Bot API metodi o'zgardi — 1-taqiqning butun mexanikasi shu satrga tayanadi"
    )


async def test_sweep_runs_without_ops_chat_and_sender_stays_open(
    test_settings: Settings,
) -> None:
    """⛔ Pitfall 9 — ops chatining YO'QLIGI kvitansiyani O'CHIRMAYDI.

    =======================================================================
    ⛔⛔ BU FAZANING CHEGARA SINOVI VA U IKKI DA'VONI BIRGA O'LCHAYDI.

    `settings.py` — `alerts_enabled = bool(token AND chat_id)`. Bugungi
    holatda `TELEGRAM_CHAT_ID` bo'sh bo'lsa `AlertSender` klientni UMUMAN
    ochmasdi, ya'ni SOTUVCHIGA ketadigan kvitansiya (CASH-05) ham
    JIMGINA ketmasdi — holbuki unga ops chati kerak emas.

    Shuning uchun:
      1. jo'natuvchi TOKEN borligida ochiladi -> `sender.enabled is True`;
      2. DAYJEST chaqiruv joyida `alerts_enabled` bilan o'raladi -> u
         FAQAT xabar yuborish uchun yashaydi va manzilsiz ma'nosiz.

    =======================================================================
    ⛔⛔ SUPURGI ENDI BU CHEGARADAN TASHQARIDA (260902, jonli tizimda
       o'lchandi) — va bu ONGLI qaytarish, tasodifiy emas.

    Ilgari supurgi ham `alerts_enabled` bilan o'ralgan edi. Ishlab
    chiqarish serverida `TELEGRAM_CHAT_ID` bo'sh bo'lgani uchun u har
    besh daqiqada ishga tushib DARHOL qaytardi va natija shunday
    ko'rindi:

      * `alert_events` jadvalida 0 qator;
      * `system_heartbeats` da `alert_sweep` komponenti umuman yo'q;
      * `backup` konteyneri 12 KUN `backup_unconfigured` deb qaytardi va
        bitta ham zaxira olmadi;
      * `backup_stale` — CRITICAL va `never_suppressed` — hech qachon
        ko'tarilmadi.

    Eski qarorning asosi «manzilsiz supurgi `notified_at` ni bo'sh
    qoldiradi va sabab hech qayerda ko'rinmaydi» edi. Bu asos NOTO'G'RI
    va buni `_notify` ning O'Z docstringi aytadi: Telegram yiqilganda
    ham `alert_events` qatori BARIBIR yoziladi, `notified_at` `NULL`
    qoladi va UI aynan shu holatni «xabar yuborilmadi» deb
    KO'RSATADI. Ya'ni yozuv ham, sabab ham ko'rinadi — yo'qolgan narsa
    faqat Telegram xabari edi.

    Farq amalda o'lchandi: tuzatishdan keyingi birinchi yugurishda 6 ta
    ogohlantirish yozildi, shundan 2 tasi CRITICAL.

    ⚠ NAZORAT BANDI MAJBURIY: bayroq `True` bo'lganda vazifa
      `sessionmaker` ga BORISHI shart. Usiz «vazifa ishlamadi» da'vosi
      vazifaning butunlay bo'sh bo'lishi bilan ham bajarilardi va
      darvoza hech nimani o'lchamasdi (05-fazaning W-2 darsi).

    ⚠ TARMOQ VA BAZA BU YERDA KERAK EMAS: `sessionmaker` o'rniga
      chaqirilganda YIQILADIGAN sentinel beriladi. `alert_sweep` ning
      birinchi qadami `active_market_ids(sessionmaker)` va u faqat
      `SQLAlchemyError` ni yutadi — `AssertionError` esa TASHQARIGA
      chiqadi, ya'ni nazorat bandi haqiqatan qizaradi.
    =======================================================================
    """
    tuned = test_settings.model_copy(
        update={"telegram_bot_token": SecretStr(TOKEN), "telegram_chat_id": ""}
    )
    assert tuned.alerts_enabled is False, (
        "test o'z farazini tasdiqlamadi: ops chati bo'sh bo'lsa `alerts_enabled` "
        "`False` bo'lishi SHART — aks holda quyidagi da'volar hech nimani o'lchamaydi"
    )

    sender = worker._alert_sender(tuned)
    try:
        assert sender.enabled is True, (
            "ops chati sozlanmagani BUTUN jo'natuvchini o'chirdi — sotuvchining "
            "kvitansiyasi (CASH-05) jimgina ketmasdi (Pitfall 9)"
        )
        assert await sender.send_message("zond") is False, (
            "manzilsiz chaqiruv `False` qaytarmadi — bo'sh `chat_id` bilan "
            "Telegram'ga so'rov ketardi"
        )

        context = _worker_context(sender, alerts_enabled=tuned.alerts_enabled)

        # SUPURGI ops chatisiz ham resursga BORADI: uning ishi — bazaga
        # yozish, xabar yuborish esa alohida va ixtiyoriy qadam.
        with pytest.raises(AssertionError, match="sessionmaker"):
            await worker.alert_sweep_task(context)

        # DAYJEST esa bormaydi: u faqat xabar yuborish uchun yashaydi.
        await worker.daily_digest_task(context)

        # NAZORAT: bayroq yoqilganda dayjest ham resursga BORADI — usiz
        # «vazifa ishlamadi» da'vosi vazifaning butunlay bo'sh bo'lishi
        # bilan ham bajarilardi (05-fazaning W-2 darsi).
        live = _worker_context(sender, alerts_enabled=True)
        with pytest.raises(AssertionError, match="sessionmaker"):
            await worker.daily_digest_task(live)
    finally:
        await sender.aclose()


# ===========================================================================
# 9. ⛔ 07-09 — `last_failure`: SIRSIZ, TOZALANADIGAN VA VAZIFAGA XOS
# ===========================================================================

BLOCKED_CHAT = "5000000001"
"""`403` beradigan manzil — «foydalanuvchi botni bloklagan» (D-22)."""

THROTTLED_CHAT = "5000000002"
"""`429` beradigan manzil — «juda tez yuboryapsiz» (DQ-3)."""

RETRY_AFTER_SECONDS = 11
"""Telegram bergan ANIQ soniya — formulaning 30 s idan ATAYIN farqli.

Farq bo'lmasa test «`retry_after` o'qildimi?» degan savolga formulaning
tasodifan mos kelgan qiymati bilan ham «ha» derdi.
"""


def _status_by_chat(request: httpx.Request) -> httpx.Response:
    """Manzilga qarab TURLI status qaytaradi — poyga o'lchovining asbobi.

    ⚠ Ikki chaqiruvchi bir vaqtda TURLI natija olishi SHART, aks holda
      «har biri o'z statusini ko'rdi» da'vosi ikkalasi bir xil status
      olganda ham yashil bo'lardi.
    """
    chat = json.loads(request.content)["chat_id"]
    if chat == BLOCKED_CHAT:
        return httpx.Response(
            403, json={"ok": False, "error_code": 403, "description": "Forbidden"}
        )
    return httpx.Response(
        429,
        json={
            "ok": False,
            "error_code": 429,
            "parameters": {"retry_after": RETRY_AFTER_SECONDS},
        },
    )


async def test_send_message_records_a_secretless_failure(sender: AlertSender) -> None:
    """⛔ D-04 — yiqilishdan keyin UCH FAKT qoladi va ularning hech biri SIR EMAS.

    =======================================================================
    ⛔ NEGA BU FAKTLAR KERAK: `send_message()` `bool` qaytaradi va `bool`
       `403` ni `429` dan ajratmaydi. Outbox uchun bu farq marshrutning
       O'ZI — biri `blocked` (qayta urinish YO'Q), ikkinchisi `retry_after`
       bilan navbatga qaytish.

    ⛔ NEGA UCHTA VA NEGA KO'PROQ EMAS: istisno OBYEKTI ham, uning MATNI
       ham saqlanmaydi. Telegram URL'i bot tokenini tashiydi, ya'ni matnni
       atributga yozish sirni JURNALDAN (bir marta ko'rinadigan satr)
       SAQLANADIGAN HOLATGA ko'chirardi.
    =======================================================================

    ⚠ `error_type` TUR NOMI shakliga tekshiriladi, LITERAL bilan
      solishtirilmaydi: `httpx` istisno sinfining nomi kutubxona
      versiyasiga bog'liq va uni qotirish testni kutubxona relizida
      qizartirardi — holbuki o'lchanadigan da'vo «bu matn emas, TUR».
    """
    async with respx.mock(assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(side_effect=_status_by_chat)
        accepted = await sender.send_message("zond", chat_id=THROTTLED_CHAT)

    failure = sender.last_failure

    assert accepted is False, "test o'z farazini tasdiqlamadi: `429` `False` bermadi"
    assert isinstance(failure, SendFailure), "yiqilishdan keyin `last_failure` yozilmadi"
    assert failure.status == 429, f"status kodi noto'g'ri: {failure.status}"
    assert failure.retry_after == RETRY_AFTER_SECONDS, (
        f"Telegram bergan `retry_after` o'qilmadi: {failure.retry_after}. Usiz "
        "backoff formulasi chegarani QATTIQROQ urardi (DQ-3)"
    )
    assert failure.error_type.isidentifier(), (
        f"`error_type` tur nomi emas: {failure.error_type!r} — matn shaklidagi "
        "qiymat Telegram URL'ini, ya'ni bot tokenini tashishi mumkin (D-04)"
    )
    assert TOKEN not in repr(failure), (
        f"⛔ TOKEN `SendFailure` NING `repr` IDA: {failure!r}. Dataklassning "
        "standart `repr` i uning MAYDONLARIDAN iborat, ya'ni istisno matnini "
        "maydonga yozish uni jurnalga qaytarardi"
    )


async def test_last_failure_is_reset_before_every_call(sender: AlertSender) -> None:
    """⛔ MUVAFFAQIYATDAN KEYIN QIYMAT `None` — eski xato OQIB O'TMAYDI.

    =======================================================================
    ⛔ USIZ NIMA BUZILARDI: outbox `send_message()` `False` qaytarganda
       `last_failure` ni o'qiydi. Qiymat tozalanmasa, KEYINGI qatorning
       «manzil yo'q» shoxi (u ham `False` beradi) OLDINGI qatorning `403`
       ini ko'rardi va SOG'LOM qator `blocked` ga o'tardi — sotuvchi bilan
       aloqa «uzilgan» deb belgilanardi, holbuki u hech qachon
       bloklamagan.

    ⚠ TOZALASH BIRORTA I/O DAN OLDIN: uni javob kelgandan keyin qilish
      tarmoq yiqilgan shoxni qamramasdi.
    =======================================================================
    """
    async with respx.mock(assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(side_effect=_status_by_chat)
        assert await sender.send_message("zond", chat_id=BLOCKED_CHAT) is False
        recorded = sender.last_failure

    assert recorded is not None and recorded.status == 403, (
        "test o'z farazini tasdiqlamadi: birinchi chaqiruv yiqilishi SHART, "
        "aks holda pastdagi `None` da'vosi hech nimani o'lchamaydi"
    )

    async with respx.mock(assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})
        )
        assert await sender.send_message("zond", chat_id=THROTTLED_CHAT) is True

    assert sender.last_failure is None, (
        f"muvaffaqiyatli chaqiruvdan keyin eski yiqilish qoldi: {sender.last_failure!r}. "
        "«Xato yo'q» holati YO'QLIK bilan ifodalanadi — ikkinchi bayroq bilan emas"
    )


async def test_last_failure_is_isolated_between_concurrent_tasks(sender: AlertSender) -> None:
    """⛔⛔ POYGA O'LCHOVI — bir jarayondagi ikki vazifa bir-birini KO'RMAYDI.

    =======================================================================
    ⛔ NEGA BU O'LCHOV MAVJUD: `AlertSender` `TaskiqState` da AYNAN BITTA
       NUSXA bo'lib saqlanadi, `alert_sweep` va `notify.outbox_tick` esa
       BIR XIL worker jarayonida asyncio vazifalari sifatida PARALLEL
       yugurishi mumkin. Instans atributi bo'lganda bir vazifaning `403` i
       ikkinchisining `429` ini JIMGINA almashtirardi va outbox qatori
       NOTO'G'RI holatga o'tardi — xatosiz, jimgina va faqat yuklama
       ostida.

    ⛔⛔ TO'SIQ (`asyncio.Barrier`) TESTNING YURAGI, BEZAK EMAS.

    Usiz ikki vazifa KETMA-KET bajarilardi: birinchisi o'z qiymatini yozib,
    O'QIB, tugardi va faqat keyin ikkinchisi boshlanardi — ya'ni INSTANS
    ATRIBUTI bilan ham har biri «o'z» qiymatini ko'rgan bo'lardi va test
    MANGU YASHIL qolardi.

    To'siq esa ikkala vazifani ham «yozdim, hali o'qimadim» nuqtasida
    UCHRASHTIRADI. Shundan keyingina ular o'qiydi — bitta umumiy atribut
    bilan IKKALASI ham OXIRGI yozuvchining statusini ko'rardi.
    =======================================================================
    """
    gate = asyncio.Barrier(2)

    async def attempt(target: str) -> tuple[bool, SendFailure | None]:
        accepted = await sender.send_message("zond", chat_id=target)
        # ⛔ IKKALA VAZIFA HAM O'Z YIQILISHINI YOZIB BO'LGACH uchrashadi.
        await gate.wait()
        return accepted, sender.last_failure

    async with respx.mock(assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(side_effect=_status_by_chat)
        async with asyncio.timeout(30):
            blocked, throttled = await asyncio.gather(
                attempt(BLOCKED_CHAT), attempt(THROTTLED_CHAT)
            )
        calls = route.call_count

    assert calls == 2, f"ikki so'rov kutilgan edi, {calls} ta ketdi — poyga umuman qurilmadi"
    assert blocked[0] is False and throttled[0] is False

    blocked_failure, throttled_failure = blocked[1], throttled[1]
    assert blocked_failure is not None and throttled_failure is not None

    assert blocked_failure.status == 403, (
        f"⛔ BLOKLANGAN chaqiruvchi BOSHQA vazifaning statusini ko'rdi: "
        f"{blocked_failure.status}. Qiymat instans atributida bo'lsa aynan "
        "shunday bo'lardi va outbox qatori noto'g'ri holatga o'tardi"
    )
    assert throttled_failure.status == 429, (
        f"⛔ CHEGARAGA URILGAN chaqiruvchi boshqa vazifaning statusini ko'rdi: "
        f"{throttled_failure.status}"
    )
    assert throttled_failure.retry_after == RETRY_AFTER_SECONDS
    assert blocked_failure.retry_after is None, (
        "`403` javobida `retry_after` paydo bo'ldi — qiymatlar vazifalar orasida aralashgan"
    )
