"""`outbox_tick` — BOT-04 ning xulqiy o'lchovlari va ⛔ G7-5 (token sizmaydi).

=============================================================================
TELEGRAM `respx` BILAN TUTILADI, BAZA ESA HAQIQIY.

Ikki tanlov, ikki xil sabab (`test_alerting.py` bilan aynan bir xil):

  * **Telegram — `respx`, `assert_all_mocked=True`.** Haqiqiy Bot API ga
    borish testni tashqi xizmatga, tarmoqqa va HAQIQIY BOT TOKENIGA
    bog'lardi. Bayroq esa TUTILMAGAN so'rovni QIZIL qiladi: usiz kod
    boshqa manzilga chiqib ketsa test buni umuman sezmasdi.
  * **Baza — HAQIQIY Postgres.** Ijara (`SKIP LOCKED` + `lease_until`),
    quiet-hours darvozasi (`AT TIME ZONE` + `LEFT JOIN`) va append-only
    holat mashinasi FAQAT Postgres'da mavjud.
=============================================================================

=============================================================================
⛔⛔ `delivered` NING MA'NOSI — BU FAYLNING BIRINCHI DA'VOSI.

Bot API `sendMessage` faqat `Message` obyektini qaytaradi: YETKAZILGANLIK
yoki O'QILGANLIK kvitansiyasi YO'Q (Pitfall 2). Shuning uchun `delivered`
= «Telegram 200 qaytardi va `message_id` berdi», ya'ni xabar CHATGA
JOYLANDI — «sotuvchi O'QIDI» EMAS.

Bu farq nizoda (D-02) hal qiluvchi: tizim isbotlab bo'lmaydigan da'vo
qilmasligi kerak. Semantika UCH joyda bir xil yozilgan — `enums.py` ning
docstringi, `outbox.py` ning modul docstringi va shu yerdagi test
docstringlari.
=============================================================================

⛔⛔ VAQT SILJITILMAYDI — U ARGUMENT (`outbox_tick(..., now=...)`), va
   THROTTLING SOATI HAM (`monotonic=`, `sleep=`). Ya'ni «bir soatdan keyin
   nima bo'ladi?» va «ikkinchi xabar qancha kutadi?» savollari
   `freezegun`siz, HAQIQIY UYQUSIZ o'lchanadi — butun fayl bir necha
   soniyada yuguradi.

⚠ `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` — 07-06
  ochiq qoldirgan VAQTINCHALIK nusxa va u `NOTIFICATION_META` dan
  AJRALGAN (`cashier_name` unda YO'Q). Fayl bu rejaning o'zgartirish
  ro'yxatida emas, shuning uchun u TEGILMAYDI: `html.escape()` testi
  fixture o'rniga MAHSULOTNING `enqueue()` idan yuradi va shu bilan
  reyestrning haqiqiy allowlisti ustidan o'lchaydi.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import pytest
import respx
from app.jobs.notification_meta import outbox_payload
from app.jobs.outbox import (
    OUTBOX_COMPONENT,
    PER_CHAT_INTERVAL_SECONDS,
    UNRESOLVED_RETRY_SECONDS,
    outbox_tick,
)
from app.repositories import outbox_repo
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD, AlertSender
from fixtures.notification_domain import (
    cleanup_notification_domain,
    seed_binding,
    seed_outbox_row,
)
from pydantic import SecretStr
from sbozor_core.enums import OutboxKind, OutboxRecipientKind, OutboxStatus
from sbozor_core.timeutil import MARKET_TZ
from structlog.testing import capture_logs

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from fixtures import TenantSessionFactory
    from fixtures.market_domain import MarketDomainSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

TOKEN = "1234567890:TEST-TOKEN-NEVER-REAL"  # noqa: S105 - qalbaki, `respx` tutadi
SEND_URL = f"{TELEGRAM_API_BASE}/bot{TOKEN}/{TELEGRAM_SEND_METHOD}"

LEAKY_TOKEN = "123456:AAH-TESTTOKEN-DO-NOT-LEAK"  # noqa: S105 - G7-5 ning IGNASI
"""⛔ G7-5 NING O'LCHOV IGNASI — qalbaki, ammo O'ZIGA XOS satr.

Qiymat `TOKEN` dan ATAYIN farq qiladi: u faqat bitta testda ishlatiladi,
ya'ni «jurnalda topilmadi» natijasi boshqa testning shovqiniga taqalib
qolmaydi. `DO-NOT-LEAK` bo'lagi esa xato xabarini o'qiyotgan odam uchun
niyatni darhol ochadi.
"""
LEAKY_SEND_URL = f"{TELEGRAM_API_BASE}/bot{LEAKY_TOKEN}/{TELEGRAM_SEND_METHOD}"

_THIS_FILE_SOURCE = Path(__file__).read_text(encoding="utf-8")
"""Shu test faylining O'Z matni — G7-5 ning NAZORAT bandi uchun.

⚠ IMPORT PAYTIDA O'QILADI, test ichida emas: sinxron fayl o'qish `async`
  testda `ASYNC240` beradi va — muhimrog'i — nazorat bandining o'zi
  o'lchovga vaqt qo'shmasligi kerak.
"""

RECEIPT = OutboxKind.PAYMENT_RECEIPT.value
VENDOR = OutboxRecipientKind.VENDOR.value

LOUD_MOMENT = datetime(2026, 8, 12, 9, 0, tzinfo=MARKET_TZ)
"""Quiet oynadan (21:00-08:00) TASHQARIDAGI payt.

Sana QOTIRILGAN va bu xavfsiz: tikning butun arifmetikasi `now`
argumentiga qaraydi, ya'ni test kalendarga umuman bog'liq emas.
"""

CHAT_A = 7_600_000_101
CHAT_B = 7_600_000_202
"""Telegram identifikatorlari — ⛔ `2**31` DAN KATTA.

`vendor_telegram_bindings.telegram_user_id` `BIGINT` deb e'lon qilingan va
haqiqiy identifikatorlar 32-bit diapazondan allaqachon oshib ketgan
(`fixtures/notification_domain.py::DEFAULT_TELEGRAM_USER_ID` ning sababi).
"""

MESSAGE_ID = 987_654_321
"""Telegram qaytaradigan `message_id` — `provider_message_id` ga yoziladi."""

RETRY_AFTER_SECONDS = 7
"""Telegram bergan ANIQ soniya — formulaning 30 s idan ATAYIN farqli.

Farqsiz «`retry_after` o'qildimi?» savoliga formulaning tasodifan mos
kelgan qiymati bilan ham «ha» deb javob berilardi.
"""

_ROW = (
    "SELECT status, attempt_count, provider_message_id, last_error_type, "
    "last_status_code, next_attempt_at, lease_until "
    "FROM notification_outbox WHERE id = %s"
)
_HEARTBEAT_DROP = "DELETE FROM system_heartbeats WHERE component = %s"


class _Clock:
    """Throttling uchun SOXTA soat — ⛔ HAQIQIY `sleep` KUTILMAYDI.

    =========================================================================
    Chegara sekundlar bilan o'lchanadi (per-chat 1 msg/s), ya'ni haqiqiy
    uyqu bilan yozilgan test har bir xabar uchun bir soniya kutardi va
    birinchi kunidanoq `-m slow` ga surilardi — ya'ni AMALDA hech qachon
    yugurmasdi.

    Soat `sleep()` ning O'ZI bilan siljiydi: shunda pacer'ning ikkinchi
    hisobi birinchisining natijasini KO'RADI va o'lchov haqiqiy vaqt
    o'tishini to'liq taqlid qiladi.
    =========================================================================
    """

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.slept.append(delay)
        self.now += delay


class _ExplodingSender(AlertSender):
    """⛔ ATAYIN DUSHMAN jo'natuvchi: `send_message()` ISTISNO KO'TARADI.

    =========================================================================
    ⚠ BU MAHSULOT KONTRAKTINI QAYTA YOZMAYDI, U TIKNING HIMOYASINI
      O'LCHAYDI.

    `AlertSender.send_message()` istisno ko'tarmaydi (3-taqiq) va bu
    `test_alerting.py` da alohida o'lchangan. Lekin `outbox_tick` o'sha
    kafolatga TAYANMASLIGI kerak: jo'natuvchi bir kun o'zgarsa yoki
    kutilmagan istisno (`RuntimeError`, `asyncio.CancelledError` emas)
    chiqsa, tik BUTUN NAVBATNI to'xtatmasligi shart (D-23).

    Shuning uchun bu sinf mahsulot obyektining O'RNINI BOSMAYDI — u
    faqat BITTA nosozlikni majburlaydi va qolgan hamma narsa (repo,
    baza, holat mashinasi) mahsulotning O'ZI bo'lib qoladi.
    =========================================================================
    """

    async def send_message(self, text: str, *, chat_id: str | None = None) -> bool:
        raise RuntimeError("telegram jo'natuvchisi kutilmaganda yiqildi")


@pytest.fixture
def bed(
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> Iterator[MarketDomainSeed]:
    """Domen qatlami + KAFOLATLANGAN tozalash (yurak urishi ham).

    ⚠ `market_domain` ARGUMENT sifatida olinadi, faqat «oldin ishlasin»
      uchun emas: pytest fixture'larni TESKARI tartibda yopadi, ya'ni
      bildirishnoma qatorlari sotuvchilar va bozorlar o'chirilishidan
      OLDIN tozalanadi.
    """
    try:
        yield market_domain
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(market_domain.market_ids))
        sync_owner_conn.execute(_HEARTBEAT_DROP, (OUTBOX_COMPONENT,))


@pytest.fixture
def sender() -> Iterator[AlertSender]:
    """HAQIQIY `AlertSender` — ⛔ STANDART MANZILSIZ (`chat_id=""`).

    =========================================================================
    ⛔ BO'SH STANDART ATAYIN VA U DA'VO QO'SHADI: tik `chat_id` ni
       BERISHNI unutsa, `send_message()` manzilsiz qolib `False` qaytaradi
       va test QIZARADI. Ops chati bilan qurilgan jo'natuvchida esa o'sha
       unutish JIMGINA kechardi — sotuvchining kvitansiyasi platforma
       adminining chatiga ketardi va test buni umuman sezmasdi.

    ⚠ MAHSULOT OBYEKTI ALMASHTIRILMAYDI (03-14 metodikasi): sirsizlik,
      `bool` kontrakti va rasm taqig'i AYNAN shu sinfning xulqi.
    =========================================================================
    """
    yield AlertSender(token=SecretStr(TOKEN), chat_id="", enabled=True)


def _row(conn: Connection[TupleRow], outbox_id: UUID) -> dict[str, Any]:
    row = conn.execute(_ROW, (str(outbox_id),)).fetchone()
    assert row is not None, f"qator YO'QOLDI: {outbox_id} — D-20 append-only buzilgan"
    return {
        "status": row[0],
        "attempt_count": row[1],
        "provider_message_id": row[2],
        "last_error_type": row[3],
        "last_status_code": row[4],
        "next_attempt_at": row[5],
        "lease_until": row[6],
    }


def _seed_receipt(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    vendor_id: UUID,
    stall_code: str,
    bind_chat: int | None = CHAT_A,
) -> UUID:
    """Bitta kvitansiya niyati + (ixtiyoriy) faol Telegram bog'lanishi.

    ⚠ TUR ATAYIN `payment_receipt`: u D-18 bo'yicha HECH QACHON
      to'xtatilmaydi, ya'ni quiet-hours darvozasi bu fayldagi o'lchovlarga
      SHOVQIN qo'shmaydi. Quiet oynaning O'ZI `test_outbox_repo.py` da
      alohida va to'liq o'lchangan — uni bu yerda takrorlash ikki
      darvozani bir sonda aralashtirardi.
    """
    if bind_chat is not None:
        seed_binding(conn, market_id=market_id, vendor_id=vendor_id, telegram_user_id=bind_chat)
    return seed_outbox_row(
        conn,
        market_id=market_id,
        kind=RECEIPT,
        vendor_id=vendor_id,
        payload={"amount_soum": 15_000, "stall_code": stall_code},
        next_attempt_at=LOUD_MOMENT - timedelta(hours=1),
    )


def _ok_response() -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": MESSAGE_ID}})


async def _tick(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    now: datetime,
    clock: _Clock | None = None,
) -> Any:
    """Tikni SOXTA soat bilan chaqiradi — haqiqiy uyqu HECH QACHON kutilmaydi."""
    pacer = clock or _Clock()
    return await outbox_tick(
        sessionmaker, sender, now=now, monotonic=pacer.monotonic, sleep=pacer.sleep
    )


# ---------------------------------------------------------------------------
# 1. `delivered` — MA'NOSI BILAN BIRGA
# ---------------------------------------------------------------------------


async def test_delivered_records_the_provider_message_id(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """`200` -> `delivered` + `provider_message_id`.

    =======================================================================
    ⛔⛔ `delivered` = «TELEGRAM QABUL QILDI», «O'QILDI» EMAS.

    Bot API `sendMessage` faqat `Message` obyektini qaytaradi:
    yetkazilganlik yoki o'qilganlik kvitansiyasi YO'Q (Pitfall 2). Ya'ni
    bu holat AYNAN shuni bildiradi — xabar chatga JOYLANDI.

    Kengroq o'qish (masalan UI da «sotuvchi ko'rdi») nizoda (D-02) tizimni
    ISBOTLAB BO'LMAYDIGAN da'voga majburlardi va aynan o'sha da'vo
    tortishuvda birinchi bo'lib qulardi.
    =======================================================================
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        result = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)
        bodies = [json.loads(call.request.content) for call in router.calls]

    row = _row(sync_owner_conn, outbox_id)

    assert route.call_count == 1, f"aynan bitta so'rov kutilgan edi, {route.call_count} ketdi"
    assert row["status"] == OutboxStatus.DELIVERED.value, row
    assert row["provider_message_id"] == MESSAGE_ID, (
        f"`provider_message_id` yozilmadi: {row['provider_message_id']}. Usiz "
        "«Telegram qabul qildi» fakti nizoda hech qanday tayanchsiz qolardi"
    )
    assert row["lease_until"] is None, "yakuniy holatda ijara bo'shatilmadi"
    assert result.delivered == 1 and result.claimed == 1

    # ⛔ MANZIL SOTUVCHINIKI: bo'sh standart bilan qurilgan jo'natuvchi
    #   `chat_id` unutilganda `False` qaytarardi, ya'ni bu da'vo yuqoridagi
    #   `delivered` bilan BIRGA o'lchanadi.
    assert bodies[0]["chat_id"] == str(CHAT_A), bodies[0]


async def test_the_message_text_is_built_and_html_escaped(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ T-07-51 — ism ichidagi `<` xabarni BUZMAYDI va matn QATORDAN o'qilmaydi.

    =======================================================================
    ⛔ BU FUNKSIONAL VA XAVFSIZLIK BANDI BIR VAQTDA.

    `alerts.py` `parse_mode="HTML"` ni tanlagan (Markdown bozor nomidagi
    `_` va `*` da butun xabarni rad etardi). Ya'ni kassir ismida `<`
    bo'lsa Telegram butun xabarni PARSE XATOSI bilan rad etardi — va u
    aynan o'sha ismli kassirning HAR BIR kvitansiyasida takrorlanardi.

    ⛔ IKKINCHI DA'VO: `payload` da TAYYOR MATN yo'q. Xabar `kind` +
       `payload` dan JO'NATISH paytida quriladi (Pitfall 6) — tayyor matn
       ustunga yozilsa u `pg_dump` -> restic -> TASHQI BUCKET zanjiriga
       chiqardi.

    ⚠ NIYAT MAHSULOTNING `enqueue()` I ORQALI YOZILADI, fixture orqali
      EMAS: `cashier_name` reyestrning allowlistida bor, fixture'ning
      VAQTINCHALIK nusxasida esa YO'Q (07-06 ning ochiq bandi). Mahsulot
      yo'lidan yurish testni haqiqiy chegara ustidan o'lchaydi.
    """
    market = bed.market_a
    seed_binding(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        telegram_user_id=CHAT_A,
    )
    async with tenant_session(market.market_id) as session:
        outbox_id = await outbox_repo.enqueue(
            session,
            market_id=market.market_id,
            kind=RECEIPT,
            recipient_kind=VENDOR,
            vendor_id=market.vendor_ids[0],
            dedupe_key=f"receipt:{uuid4()}",
            payload=outbox_payload(
                RECEIPT,
                amount_soum=15_000,
                stall_code=market.stall_codes[0],
                cashier_name="A <b> B",
            ),
        )
    assert outbox_id is not None, "test o'z farazini tasdiqlamadi: niyat yozilmadi"

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(return_value=_ok_response())
        # `enqueue()` `next_attempt_at` ni SERVER soatidan oladi, ya'ni tik
        # HOZIRGI paytda chaqiriladi (`LOUD_MOMENT` emas).
        await _tick(api_sessionmaker, sender, now=datetime.now(tz=MARKET_TZ))
        bodies = [json.loads(call.request.content) for call in router.calls]

    assert bodies, "birorta so'rov tutilmadi — test o'z farazini tasdiqlamadi"
    text = bodies[0]["text"]
    assert "&lt;b&gt;" in text, f"ism `html.escape()` dan o'tmadi: {text!r}"
    assert "A <b> B" not in text, (
        f"xom `<b>` matnga tushdi: {text!r} — Telegram butun xabarni parse xatosi bilan RAD ETARDI"
    )
    assert "15" in text and "000" in text, f"summa `format_soum()` bilan chizilmadi: {text!r}"


# ---------------------------------------------------------------------------
# 2. ⛔ TAKSONOMIYA — `403` / `429` / `5xx` (D-22, DQ-3)
# ---------------------------------------------------------------------------


async def test_403_marks_blocked_and_never_retries(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ D-22 — `403` `blocked` beradi va u QAYTA URINILMAYDI.

    =======================================================================
    ⛔ `blocked` — MA'LUMOT, XATO EMAS. Foydalanuvchi botni bloklagan;
       bu o'z-o'zidan tuzalmaydi va har urinish chegarani QATTIQROQ
       urardi. Holat `failed` DAN ATAYIN ajratilgan: uni texnik nosozlik
       shovqiniga qo'shish direktordan «bu sotuvchi bilan ALOQA UZILDI»
       faktini YASHIRARDI.

    ⛔ NAZORAT IKKINCHI TIKDA: birinchi tikning natijasi yolg'iz o'zi
       «qayta urinilmaydi» ni ISBOTLAMAYDI — qator `blocked` bo'lib,
       keyingi tik uni baribir olishi mumkin edi. Shuning uchun ikkinchi
       tik chaqiriladi va `respx` chaqiruvlari soni O'SMASLIGI talab
       qilinadi.
    =======================================================================
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(
            return_value=httpx.Response(
                403, json={"ok": False, "error_code": 403, "description": "Forbidden"}
            )
        )
        first = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)
        after_first = _row(sync_owner_conn, outbox_id)
        calls_after_first = route.call_count

        second = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT + timedelta(hours=2))
        after_second = _row(sync_owner_conn, outbox_id)

    assert first.blocked == 1 and second.blocked == 0
    assert after_first["status"] == OutboxStatus.BLOCKED.value, after_first
    assert after_first["attempt_count"] == 1
    assert calls_after_first == 1

    assert route.call_count == 1, (
        f"ikkinchi tik bloklangan qatorga QAYTA urindi ({route.call_count} so'rov). "
        "Blok o'z-o'zidan tuzalmaydi va har urinish chegarani qattiqroq urardi (D-22)"
    )
    assert after_second["attempt_count"] == 1, (
        f"bloklangan qatorning urinishi oshdi: {after_second['attempt_count']}"
    )
    assert after_second["status"] == OutboxStatus.BLOCKED.value


async def test_429_uses_retry_after_over_the_formula(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ DQ-3 — Telegram bergan `retry_after` FORMULADAN USTUN.

    Formula birinchi urinish uchun 30 s berardi; Telegram esa 7 s dedi.
    Formulaga tayanish chegarani QATTIQROQ urardi va bu `alerts.py` ning
    «`429` ga retry qilish holatni yomonlashtiradi» qoidasining aynan
    takrori bo'lardi.

    ⚠ FARQ ATAYIN KATTA (7 s va 30 s): yaqin qiymatlarda test o'lchov
      xatosi bilan ham yashil bo'lardi.
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(
            return_value=httpx.Response(
                429,
                json={
                    "ok": False,
                    "error_code": 429,
                    "parameters": {"retry_after": RETRY_AFTER_SECONDS},
                },
            )
        )
        result = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)

    row = _row(sync_owner_conn, outbox_id)
    waited = (row["next_attempt_at"] - LOUD_MOMENT).total_seconds()

    assert result.rescheduled == 1
    assert row["status"] == OutboxStatus.PENDING.value, row
    assert row["last_status_code"] == 429
    assert waited == pytest.approx(RETRY_AFTER_SECONDS, abs=1), (
        f"keyingi urinish {waited} s dan keyinga qo'yildi, kutilgani "
        f"{RETRY_AFTER_SECONDS} s. 30 s — formulaning qiymati, ya'ni Telegram "
        "bergan `retry_after` UMUMAN o'qilmagan (DQ-3)"
    )


async def test_five_attempts_then_failed(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ DQ-3 — `5xx` da AYNAN 5 urinish, keyin `failed`. OLTINCHISI YO'Q.

    =======================================================================
    ⛔ IKKI TOMONLAMA DA'VO VA IKKALASI HAM KERAK:

      * 5 urinish HAQIQATAN bo'ladi (`respx` chaqiruvlari soni = 5) —
        ya'ni byudjet erta tugamaydi va bir necha daqiqalik Telegram
        uzilishi kvitansiyani yo'qotmaydi;
      * OLTINCHISI YO'Q — cheksiz urinish navbatni to'ldirardi va tikning
        har yugurishi mangu yiqilgan qatorlarga sarflanardi.

    ⚠ HAR TIK SOATNI IKKI SOATGA SURADI: backoff ning tepa chegarasi bir
      soat, ya'ni ikki soat HAR DOIM yetarli. Aniq intervalni qaytarish
      testni formulaning NUSXASIGA aylantirardi — u alohida, birlik
      darajasida o'lchanadi.
    =======================================================================
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(500, text="oops"))
        for index in range(6):
            await _tick(api_sessionmaker, sender, now=LOUD_MOMENT + timedelta(hours=2 * index))

    row = _row(sync_owner_conn, outbox_id)

    assert route.call_count == 5, (
        f"{route.call_count} urinish bo'ldi, kutilgani AYNAN 5. Ko'proq bo'lsa "
        "byudjet umuman ishlamayapti; kamroq bo'lsa xabar erta yo'qotilgan"
    )
    assert row["status"] == OutboxStatus.FAILED.value, row
    assert row["attempt_count"] == 5
    assert row["last_status_code"] == 500
    assert row["last_error_type"] and row["last_error_type"].isidentifier(), (
        f"`last_error_type` tur nomi emas: {row['last_error_type']!r}"
    )


# ---------------------------------------------------------------------------
# 3. ⛔ G7-5 — TOKEN JURNALGA HAM, USTUNGA HAM TUSHMAYDI
# ---------------------------------------------------------------------------


async def test_failure_log_carries_no_token(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """⛔⛔ G7-5 — XULQIY o'lchov: yiqilgan jo'natuvchi tokenni CHIQARMAYDI.

    =======================================================================
    ⛔ NEGA AST DARVOZASI (G7-4) YETARLI EMAS.

    `tests/unit/test_outbox_secrets.py` STRUKTURANI o'lchaydi: `str(exc)`,
    `repr(exc)` va f-string interpolyatsiyasi yo'q. Lekin kod sirni
    BOSHQA yo'ldan ham chiqarishi mumkin — masalan `httpx` ning o'z
    jurnalidan, `exc.request.url` atributidan yoki uchinchi tomon
    kutubxonasining `logging` chaqiruvidan. Struktura ularning HECH
    BIRINI ko'rmaydi.

    ⛔ VA XULQ HAM YOLG'IZ O'ZI YETARLI EMAS: test o'sha shoxni
       bajarmasligi mumkin. Shuning uchun IKKALASI HAM majburiy va
       ikkalasi ham shu fazaning darvozasi.
    =======================================================================

    =======================================================================
    ⛔⛔ UCH TOMONLAMA DA'VO + IKKI NAZORAT BANDI.

    `caplog` yolg'iz o'zi bu yerda YOLG'ON YASHIL berardi: `structlog`
    `PrintLoggerFactory` bilan sozlangan (`sbozor_core/logging.py`), ya'ni
    u stdlib `logging` dan UMUMAN o'tmaydi va `caplog.text` BO'SH bo'lardi
    — «token topilmadi» da'vosi esa bo'sh matnda ham yashil.

    Shuning uchun asosiy asbob — `structlog.testing.capture_logs()`:

      * u hodisa lug'atlarini XOM holda tutadi, ya'ni `censor_secrets`
        protsessori ISHLAMAYDI. Bu o'lchovni KUCHAYTIRADI: kod tokenni
        senzura QOPLAMAGAN kalit ostida yozsa ham ushlanadi;
      * NAZORAT: tutilgan hodisalar ro'yxati BO'SH BO'LMASLIGI shart —
        aks holda asbob ishlamayapti va butun test hech nimani
        o'lchamaydi.
    =======================================================================
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )
    leaky = AlertSender(token=SecretStr(LEAKY_TOKEN), chat_id="", enabled=True)

    try:
        with capture_logs() as captured, caplog.at_level("DEBUG"):
            async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
                router.post(LEAKY_SEND_URL).mock(
                    return_value=httpx.Response(500, text="internal error")
                )
                result = await _tick(api_sessionmaker, leaky, now=LOUD_MOMENT)
    finally:
        await leaky.aclose()

    rendered = json.dumps(captured, default=str, ensure_ascii=False)
    row = _row(sync_owner_conn, outbox_id)

    # NAZORAT 1 — asbob ishlayapti (aks holda «topilmadi» bo'sh matndan kelardi).
    assert captured, (
        "birorta strukturaviy jurnal hodisasi tutilmadi — `capture_logs()` "
        "ishlamayapti va quyidagi «token yo'q» da'vosi BO'SH matnni o'lchagan "
        "bo'lardi"
    )
    assert result.rescheduled == 1, "test o'z farazini tasdiqlamadi: jo'natuvchi yiqilmadi"

    # NAZORAT 2 — izlanayotgan satr HAQIQATAN mavjud (bu fayldagi literal).
    assert LEAKY_TOKEN in _THIS_FILE_SOURCE, (
        "test o'zi izlayotgan satrni topa olmadi — `LEAKY_TOKEN` o'zgargan yoki "
        "yo'l buzilgan bo'lsa «topilmadi» natijasi hech nimani isbotlamasdi"
    )

    # (a) STRUKTURAVIY JURNALDA yo'q.
    assert LEAKY_TOKEN not in rendered, (
        f"⛔ BOT TOKENI JURNALGA TUSHDI:\n{rendered}\n\nTelegram Bot API ning "
        "URL'i tokenni tashiydi va `httpx` istisnosining matni to'liq URL'ni "
        "o'z ichiga oladi — jurnaldan u Sentry'ga chiqardi (D-04)"
    )
    # (b) STDLIB jurnalida ham yo'q (`httpx` va boshqa kutubxonalar yo'li).
    assert LEAKY_TOKEN not in caplog.text, f"⛔ BOT TOKENI STDLIB JURNALIGA TUSHDI:\n{caplog.text}"
    # (c) BAZADAGI USTUNDA yo'q va u TUR NOMI.
    assert row["last_error_type"] is not None
    assert LEAKY_TOKEN not in row["last_error_type"], (
        f"⛔ BOT TOKENI `last_error_type` USTUNIGA YOZILDI: {row['last_error_type']!r}. "
        "U yerdan `pg_dump` -> restic -> TASHQI BUCKET zanjiri ochilardi"
    )
    assert row["last_error_type"].isidentifier(), (
        f"`last_error_type` tur nomi emas: {row['last_error_type']!r} — matn "
        "shaklidagi qiymat URL parchasini tashishi mumkin (D-04)"
    )


# ---------------------------------------------------------------------------
# 4. ⛔ D-23 — JO'NATUVCHI BLOKLAMAYDI
# ---------------------------------------------------------------------------


async def test_telegram_failure_does_not_block_payment(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ D-23 — Telegram butunlay yiqilsa ham tik ISTISNO KO'TARMAYDI.

    =======================================================================
    KUZATUV VA XABAR VOSITASI KUZATILAYOTGAN TIZIMNI YIQITA OLMASLIGI KERAK.

    Telegram uzilganda pul yozuvi va case yuritish DAVOM ETISHI shart —
    aks holda bir soatlik Telegram nosozligi bir kunlik patta hisobini
    yo'q qilardi, ya'ni xabar mexanizmi o'zi ogohlantirishi kerak bo'lgan
    zarardan KATTAROQ zarar keltirardi.
    =======================================================================

    =======================================================================
    ⚠⚠ BU TESTNING CHEGARASI OCHIQ YOZILADI — U IKKI BOSQICHLI.

    BUGUN (07-09): to'lov marshruti hali navbatga YOZMAYDI (`POST
    /payments` ni 07-12 ulaydi), ya'ni «to'lov o'tdimi?» degan savolni bu
    yerda o'lchash MUMKIN EMAS — o'lchansa u aloqasi yo'q ikki narsani
    bir testda bog'lab, keyin 07-12 ni yolg'on-yashil holatda qabul
    qilardi.

    Shuning uchun bu yerda ALOQANING YO'QLIGI o'lchanadi:
      1. tik istisno KO'TARMAYDI (Telegram butunlay yiqilgan);
      2. bitta qatorning nosozligi QOLGANLARINI to'xtatmaydi;
      3. jo'natuvchi KUTILMAGAN istisno bergan holatda ham (1) va (2)
         kuchda qoladi va xato SANOQQA aylanadi, MATNGA emas.

    07-12 uni `POST /payments` ning `201` i bilan KENGAYTIRADI.
    =======================================================================
    """
    market = bed.market_a
    first_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )
    second_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[1],
        stall_code=market.stall_codes[1],
        bind_chat=CHAT_B,
    )

    # 1-BOSQICH: Telegram BUTUNLAY yiqilgan (tarmoq darajasida).
    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(side_effect=httpx.ConnectTimeout("telegram yo'q"))
        dead = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)

    assert dead.claimed == 2, f"ikkala qator ham olinishi kerak edi: {dead}"
    assert dead.rescheduled == 2, (
        f"birinchi qatorning nosozligi ikkinchisini to'xtatdi: {dead}. Tik "
        "qatorlar bo'ylab DAVOM ETISHI shart (D-23)"
    )
    for outbox_id in (first_id, second_id):
        row = _row(sync_owner_conn, outbox_id)
        assert row["status"] == OutboxStatus.PENDING.value, row
        assert row["last_status_code"] is None, "tarmoq yiqilishida status kodi bo'lmaydi"

    # 2-BOSQICH: jo'natuvchining O'ZI kutilmaganda yiqiladi.
    exploding = _ExplodingSender(token=SecretStr(TOKEN), chat_id="", enabled=True)
    try:
        crashed = await _tick(api_sessionmaker, exploding, now=LOUD_MOMENT + timedelta(hours=2))
    finally:
        await exploding.aclose()

    assert crashed.claimed == 2, f"kutilmagan istisno tikni to'xtatdi: {crashed}"
    assert len(crashed.errors) == 2, (
        f"xatolar SANOQQA aylanmadi: {crashed.errors}. Har qator uchun bittadan yozuv kutilgan edi"
    )
    assert all(entry.endswith(":RuntimeError") for entry in crashed.errors), (
        f"xato yozuvida TUR emas, boshqa narsa bor: {crashed.errors} — istisno "
        "MATNI Telegram URL'ini, ya'ni bot tokenini tashishi mumkin (D-04)"
    )
    assert crashed.rescheduled == 2, "kutilmagan istisnodan keyin qatorlar navbatga qaytmadi"


# ---------------------------------------------------------------------------
# 5. MANZILSIZ QATOR, TAKRORLANMASLIK VA THROTTLING
# ---------------------------------------------------------------------------


async def test_unresolved_chat_stays_pending_without_consuming_an_attempt(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ Bog'lanmagan sotuvchi — `pending` da qoladi, `blocked` EMAS.

    =======================================================================
    ⛔ «HALI ULANMAGAN» VA «BIZNI BLOKLAGAN» — IKKI BOSHQA FAKT.

    Ularni aralashtirish direktorning «aloqa uzildi» ro'yxatini hali
    botga ulanmagan sotuvchilar bilan to'ldirardi va HAQIQIY bloklar
    o'sha shovqinda ko'rinmay qolardi (D-22 ning teskarisi).

    ⛔ URINISH UMUMAN QILINMAYDI VA BU O'LCHANADI: `respx` chaqiruvlari
       soni NOL. Ya'ni «urinish sarflanmadi» da'vosi holat nomidan emas,
       HTTP sanog'idan kelib chiqadi.

    ⚠ CHEGARA OCHIQ YOZILADI: `claim()` `attempt_count` ni O'ZI oshiradi
      (u urinishlarni SANAYDIGAN yagona joy, `outbox_repo` ning qarori)
      va bu modul uni ORQAGA QAYTARA OLMAYDI. Shuning uchun byudjet ikki
      mustaqil mexanizm bilan himoyalanadi va ikkalasi ham shu yerda
      o'lchanadi:

        1. `MAX_ATTEMPTS` tekshiruvi manzilsiz shoxga QO'LLANMAYDI —
           ya'ni bog'lanmagan sotuvchining kvitansiyasi HECH QACHON
           `failed` bo'lmaydi;
        2. qator 15 daqiqaga KECHIKTIRILADI — ya'ni keyingi tiklar uni
           qayta OLMAYDI va sanoq tik-be-tik o'smaydi.
    =======================================================================
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
        bind_chat=None,
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        result = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)
        after_first = _row(sync_owner_conn, outbox_id)

        # AYNAN O'SHA paytda ikkinchi tik: kechiktirish ishlayotgan bo'lsa
        # qator umuman OLINMAYDI.
        await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)
        after_second = _row(sync_owner_conn, outbox_id)

    assert route.call_count == 0, (
        f"manzilsiz qator uchun {route.call_count} so'rov ketdi — urinish QILINMASLIGI kerak edi"
    )
    assert result.unresolved == 1 and result.blocked == 0, result
    assert after_first["status"] == OutboxStatus.PENDING.value, after_first
    assert after_first["status"] != OutboxStatus.BLOCKED.value

    deferred = (after_first["next_attempt_at"] - LOUD_MOMENT).total_seconds()
    assert deferred == pytest.approx(UNRESOLVED_RETRY_SECONDS, abs=1), (
        f"qator {deferred} s ga kechiktirildi, kutilgani {UNRESOLVED_RETRY_SECONDS} s"
    )
    assert after_second["attempt_count"] == after_first["attempt_count"], (
        f"ikkinchi tik urinishni yana sarfladi: {after_first['attempt_count']} -> "
        f"{after_second['attempt_count']}. Sotuvchi hali ULANMAGAN, ya'ni Telegram "
        "bilan hech qanday muammo yo'q va byudjet yeyilmasligi kerak"
    )


async def test_two_ticks_do_not_send_twice(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ D-21/T-07-53 — bir niyat IKKI MARTA yuborilmaydi.

    Sotuvchi bir to'lov uchun ikkita tasdiq olsa nizo modelining (D-02)
    butun asosi qulardi: «qancha to'ladim?» savoliga tizimning O'ZI ikki
    xil javob berardi.

    ⚠ HIMOYA ILOVA SHARTIDA EMAS: `claim()` qatorni `sent` ga o'tkazadi
      va ijara oladi, yakuniy holat esa uni `pending` dan butunlay
      chiqaradi — ya'ni ikkinchi tik uni UMUMAN KO'RMAYDI.
    """
    market = bed.market_a
    outbox_id = _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)
        await _tick(api_sessionmaker, sender, now=LOUD_MOMENT + timedelta(hours=3))

    row = _row(sync_owner_conn, outbox_id)

    assert route.call_count == 1, (
        f"bitta niyat {route.call_count} marta yuborildi — sotuvchi bir to'lov "
        "uchun bir nechta tasdiq olardi (D-21)"
    )
    assert row["status"] == OutboxStatus.DELIVERED.value
    assert row["attempt_count"] == 1


async def test_throttle_respects_per_chat_interval(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """⛔ T-07-49 — bitta chatga ketma-ket xabarlar orasida kamida 1 soniya.

    =======================================================================
    ⛔ CHEGARANI BUZISH TEZLIKNI OSHIRMAYDI, KAMAYTIRADI: Telegram `429`
       qaytaradi, `429` esa navbatga qaytish + backoff narxini keltiradi.
       Ya'ni throttling «xushmuomalalik» emas, O'TKAZUVCHANLIK qarori.

    ⛔ SOAT SOXTA VA HAQIQIY UYQU KUTILMAYDI: chegara sekundlar bilan
       o'lchanadi, ya'ni haqiqiy `sleep` bilan yozilgan test har xabar
       uchun bir soniya yo'qotardi va birinchi kunidanoq `-m slow` ga
       surilardi — AMALDA hech qachon yugurmasdi.
    =======================================================================

    ⚠ IKKALA QATOR HAM BIR SOTUVCHINIKI, ya'ni bir CHATGA ketadi — aks
      holda per-chat chegarasi umuman qo'llanmasdi va test global
      tezlikni o'lchagan bo'lardi.
    """
    market = bed.market_a
    seed_binding(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        telegram_user_id=CHAT_A,
    )
    for _ in range(2):
        seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=RECEIPT,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 15_000, "stall_code": market.stall_codes[0]},
            next_attempt_at=LOUD_MOMENT - timedelta(hours=1),
        )

    clock = _Clock()
    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        result = await _tick(api_sessionmaker, sender, now=LOUD_MOMENT, clock=clock)

    assert route.call_count == 2 and result.delivered == 2, result
    assert clock.slept, (
        "throttle UMUMAN kutmadi — bir chatga ikki xabar ketma-ket, kechikishsiz "
        "yuborildi va Telegram uni `429` bilan qaytarardi"
    )
    assert max(clock.slept) >= PER_CHAT_INTERVAL_SECONDS, (
        f"eng uzun kutish {max(clock.slept)} s, kutilgani kamida "
        f"{PER_CHAT_INTERVAL_SECONDS} s (per-chat chegarasi)"
    )
    assert clock.now >= PER_CHAT_INTERVAL_SECONDS, "soxta soat umuman siljimadi"


async def test_the_tick_writes_its_own_heartbeat(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    sender: AlertSender,
    bed: MarketDomainSeed,
) -> None:
    """Tikning O'ZI ham kuzatiladi va detalda ⛔ FAQAT SANOQLAR bo'ladi.

    ⚠ IKKINCHI DA'VO XAVFSIZLIK BANDI: `system_heartbeats.detail` `jsonb`
      va u `pg_dump` -> restic -> TASHQI BUCKET zanjirida yashaydi. Unga
      `chat_id`, sotuvchi ismi yoki xabar matni tushsa shaxsiy ma'lumot
      zaxiraga chiqardi (T-07-54 / D-01).
    """
    market = bed.market_a
    _seed_receipt(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=market.vendor_ids[0],
        stall_code=market.stall_codes[0],
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        router.post(SEND_URL).mock(return_value=_ok_response())
        await _tick(api_sessionmaker, sender, now=LOUD_MOMENT)

    row = sync_owner_conn.execute(
        "SELECT detail FROM system_heartbeats WHERE component = %s", (OUTBOX_COMPONENT,)
    ).fetchone()

    assert row is not None, f"tik O'Z yurak urishini yozmadi ({OUTBOX_COMPONENT})"
    detail = row[0]
    assert detail["delivered"] == 1 and detail["claimed"] >= 1, detail
    assert all(isinstance(value, int) for value in detail.values()), (
        f"yurak urishi detalida SON bo'lmagan qiymat bor: {detail}. Bu maydon "
        "zaxiraga chiqadi — unga faqat sanoqlar tushishi kerak (D-01)"
    )
    assert str(CHAT_A) not in json.dumps(detail), (
        f"`chat_id` yurak urishi detaliga tushdi: {detail}"
    )
