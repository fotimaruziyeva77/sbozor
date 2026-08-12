"""7-fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular O'Z EGASIDA qoladi:

  * `test_reconciliation_api.py` (07-10) — hisobot, case yuzasi, hit-rate;
  * `test_reconciliation_repo.py`(07-07) — case domeni va hosila nisbat;
  * `test_notifications.py`      (07-13) — D-15/D-16 ning manba farqi;
  * `test_outbox.py`             (07-09) — `403`/`429`/backoff/G7-5;
  * `test_receipt_outbox.py`     (07-12) — CASH-05 ning tranzaksiyasi;
  * `test_bot_internal_api.py`   (07-08) — D-26 ning uch shoxi;
  * `test_headline.py`           (07-03) — rol -> bitta son;
  * `test_delivery_surface.py`   (07-16) — yetkazilganlik yuzasi;
  * `test_binding.py`            (07-11, ⛔ BOSHQA KONTEYNERDA) — `contact`.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da
yozilgan jumla bugun rostmi?** Har test docstringi mezon matnini
SO'ZMA-SO'Z olib yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik
ko'zga tashlanadi.

=============================================================================
⛔⛔ SOXTALASHTIRISH TAQIQLANADI — VA BU FAZADA TAQIQNING SHAKLI BOSHQA.

5-fazada taqiq ANIQLIK METRIKASI nomlariga, 6-fazada SUZUVCHI
ARIFMETIKAGA qo'yilgan edi. Bu fazaning yolg'oni ikkalasidan ham
boshqa: SC#3 va SC#5 «Telegramda oladi» deydi, CI'da esa haqiqiy
Telegram YO'Q. Ya'ni eng arzon yolg'on — jo'natuvchini almashtirish
yoki `notification_outbox` qatorini QO'LDA yetkazilgan deb belgilash
va «xabar bordi» deb yozish.

Shuning uchun bu modulda TAQIQLANADI:

  1. standart kutubxonaning soxta obyekt vositalari va ularning
     uchinchi tomon qarindoshlari (reyestr: `_FAKE_ROOTS`);
  2. pytest ning tuzatuvchi fixture'i va loyihaning spy fixture'lari
     (reyestr: `_FAKE_FIXTURES`);
  3. ⛔ `AlertSender` NING VORISI — ya'ni jo'natuvchini almashtirish
     (`test_outbox.py::_ExplodingSender` bu modulda TAKRORLANMAYDI);
  4. ⛔ navbat qatorini QO'LDA yakuniy holatga o'tkazadigan xom SQL.

⛔ VA BULARNING O'RNIGA NIMA ISHLATILADI: `respx`. U mahsulot
   yo'lini ALMASHTIRMAYDI — u faqat TARMOQ CHEGARASINI tutadi.
   `outbox_tick` -> `AlertSender.send_message()` -> `httpx` zanjiri
   OXIRIGACHA mahsulotniki bo'lib qoladi va o'lchanadigan narsa
   AYNAN CHIQQAN HTTP SO'ROVI. Bu farq mexanik: `assert_all_mocked=True`
   tutilmagan so'rovni QIZIL qiladi, ya'ni haqiqiy Telegram'ga chiqish
   IMKONSIZ, mahsulot jo'natuvchisini chetlab o'tish esa SO'ROVNI
   YO'Q QILARDI va da'vo darhol qulardi.

=============================================================================
⛔⛔ SC#4 NING CHEGARASI — OCHIQ YOZILADI, YASHIRILMAYDI.

Bot handlerlari `bot-service` konteynerida, bu modul esa `core-api`
image'ida yuguradi va ⛔ ULAR BIR JARAYONDA UCHRASHA OLMAYDI: ikkala
kod bazasi ham `app` nomli paketga ega va ikkinchisining importi
birinchisini soya qilardi (`tests/unit/test_sentry_processes.py::
CORE_API_ROOT` docstringi aynan shu sinfni yozgan). Ustiga
`bot-service` ning `pyproject.toml` i ALOHIDA (aiogram `pydantic<2.14`
va `redis<8` ni talab qiladi, core-api esa `redis==8.0.1` ni).

Shuning uchun SC#4 ⛔ IKKI QISMDA o'lchanadi va IKKALASI HAM nomlanadi
(`test_sc4_...` docstringiga qarang). Chegarani yashirish yolg'on
yashil berardi — «sotuvchi contact ulashish orqali ulanadi» jumlasining
`contact` yarmi bu modulda UMUMAN o'lchanmaydi.

=============================================================================
⛔ KUN — SEEDNING KUNI EMAS, `business_today() - 1` (07-10 ning darsi).

`daily_charges.ck_..._service_date_not_in_future` `service_date <=
business_date` ni talab qiladi, `SEED_BUSINESS_DATE` (2026-09-01) esa
QADALGAN va bugundan KEYIN bo'lishi mumkin. Marshrutlar ham kunni
`sbozor_core.timeutil.business_today()` (Asia/Tashkent) bilan
hisoblaydi, konteynerlar esa UTC da yuguradi — ya'ni `date.today()`
Toshkent yarim tunidan keyingi besh soatda BOSHQA kunni berardi va
nosozlik KODDA emas, SOATDA bo'lardi.

⛔ TOZALASH `market_id` BO'YICHA (06-14 qoidasi): mezon qoldirgan
   qatorlar keyingi fayllarning seed'ini FK buzilishi bilan yiqitardi
   (`fk_notification_outbox_vendor` da `ondelete` YO'Q).
=============================================================================
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from app.jobs.notifications import digest_evening, digest_morning, overdue_reminder
from app.jobs.outbox import outbox_tick
from app.jobs.reconciliation import DEFAULT_OVERDUE_DAYS, reconciliation_open
from app.main import app as fastapi_app
from app.repositories import billing_repo, binding_repo
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD, AlertSender
from fixtures.admin_api import session_headers
from fixtures.auth_users import AuthSeed
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_charge_evidence,
    add_daily_charge,
    billing_domain,
)
from fixtures.notification_domain import (
    cleanup_case_targets,
    cleanup_notification_domain,
    seed_binding,
    seed_notification_settings,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from pydantic import SecretStr
from sbozor_core.enums import AnomalyKind, OutboxKind, OutboxStatus, ReconciliationCaseStatus
from sbozor_core.timeutil import MARKET_TZ, business_today

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.market_domain import MarketDomainSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_MODULE_PATH = Path(__file__)


# ===========================================================================
# ⛔ MEZONLAR — ROADMAP § Phase 7 DAN LITERAL KO'CHIRILGAN
#
# ⚠ QISQARTIRILMAYDI VA QAYTA YOZILMAYDI: matn shu yerda o'zgarsa,
#   darvoza ROADMAP bilan JIMGINA ajralib ketardi va «beshala mezon
#   o'lchanadi» da'vosi boshqa beshta jumlaga tegishli bo'lib qolardi.
# ===========================================================================

CRITERIA: Final[tuple[str, ...]] = (
    'Kunlik nomuvofiqlik hisoboti "band, lekin to\'lovsiz" rastalar va '
    '"ro\'yxatga olinmagan savdo" anomaliyalarini rasm-dalil havolalari bilan '
    "ko'rsatadi",
    "Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat "
    "(yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi "
    "hisoblanadi",
    "Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10 qarzdor) va "
    "kechqurun nomuvofiqlik xabarini Telegramda oladi; har rol bosh ekranida "
    "o'ziga mos bitta asosiy raqamni ko'radi",
    "Sotuvchi contact ulashish orqali botga ulanadi (telefon raqami admin "
    "reestriga mos bo'lsa) va o'z qoldig'i/qarzi hamda to'lov tarixini ko'radi",
    "To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya boradi (summa, "
    "rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik eslatma keladi — "
    "barcha xabarlar outbox orqali, throttling va quiet hours hurmat qilinib, "
    "yetkazilganlik holati bilan",
)


REPORT_URL = "/api/v1/reconciliation/report"
CASES_URL = "/api/v1/reconciliation/cases"
HIT_RATE_URL = "/api/v1/reconciliation/hit-rate"
DELIVERY_URL = "/api/v1/reconciliation/delivery"
HEADLINE_URL = "/api/v1/me/headline"
PAYMENTS_URL = "/api/v1/payments"

BOT_RESOLVE_URL = "/internal/bot/resolve"
BOT_SUMMARY_URL = "/internal/bot/vendor/summary"
BOT_PAYMENTS_URL = "/internal/bot/vendor/payments"
DIRECTOR_RESOLVE_URL = "/internal/bot/director/resolve"
"""⛔ `director_chat_id` NING YAGONA YOZUV YO'LI (07-18, RECON-03).

Mezon #3 ning «Telegramda oladi» yarmi shu marshrutsiz produksiyada
BAJARILMAS edi: ustunga yozadigan boshqa hech qanday yo'l yo'q.
"""

PERSONAL_FIELDS: Final[frozenset[str]] = frozenset({"vendor_name", "phone", "full_name"})
"""G7-6 ning maydonlari — `test_reconciliation_api.py:74` bilan AYNI ro'yxat.

⚠ NUSXA ONGLI: `PERSONAL_ROUTES` darvozasi (`tests/tenancy/`) ularni
  MUSTAQIL qo'riqlaydi, ya'ni ikki ro'yxat ajralib ketsa o'sha darvoza
  qizaradi. Import esa tenancy paketini integratsiya to'plamiga
  bog'lardi.
"""

FORBIDDEN_EVIDENCE_MARKERS: Final[tuple[str, ...]] = ("presigned", "http", "image")
"""D-03 ning XULQ darajasidagi o'lchovi — javob tanasida BO'LMAYDIGAN satrlar."""

HEADLINE_KEYS: Final[frozenset[str]] = frozenset({"metric", "value"})

SERVICE_TOKEN = "phase7-criteria-bot-token-not-a-real-secret"  # noqa: S105 - test uskunasi
TELEGRAM_TOKEN = "1234567890:PHASE7-CRITERIA-NEVER-REAL"  # noqa: S105 - qalbaki, `respx` tutadi
SEND_URL = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/{TELEGRAM_SEND_METHOD}"

DIRECTOR_CHAT = 7_700_000_301
VENDOR_CHAT = 7_700_000_302
"""Telegram identifikatorlari — ⛔ `2**31` DAN KATTA (ustun `BIGINT`)."""

MESSAGE_ID = 555_000_111

RECEIPT_SOUM = TARIFF_SOUM
"""⛔ TO'LOV SUMMASI TARIFDAN — LITERAL EMAS VA BU MAJBURIY.

`POST /payments` server hisoblagan summadan HAR QANDAY chetlanish uchun
NOMLANGAN sabab talab qiladi (`reason_required`, D-19 sxemaga
ko'chirilgan). Qadalgan «chiroyli» son bu mezonni sabab-kod yo'liga
burib yuborardi — holbuki o'lchanayotgan narsa NORMAL kassa oqimi.
"""

_COUNT_CASE_EVENTS = (
    "SELECT count(*) FROM reconciliation_case_events WHERE market_id = %s AND case_id = %s"
)
_OUTBOX_ROWS = (
    "SELECT id, kind, status, dedupe_key, attempt_count, last_status_code, vendor_id "
    "FROM notification_outbox WHERE market_id = %s ORDER BY created_at, id"
)
_INSERT_EVIDENCED_ANOMALY = (
    "INSERT INTO billing_anomalies "
    "(id, market_id, kind, stall_id, service_date, occupancy_event_id, snapshot_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
_EVIDENCE_PAIR = (
    "SELECT e.id, e.snapshot_id FROM occupancy_events e "
    "WHERE e.market_id = %s AND e.snapshot_id IS NOT NULL ORDER BY e.id LIMIT 1"
)
_HEARTBEAT_DROP = "DELETE FROM system_heartbeats WHERE component LIKE %s"


# ===========================================================================
# ⛔⛔ SOXTALASHTIRISH REYESTRLARI — NOMLAR BO'LAKLAB QURILADI
#
# ⛔ NEGA LITERAL YOZILMAYDI VA BU HIYLA EMAS, ZARURAT (05-13 / 06-14
#    darsining takrori): bu modulning O'Z qabul mezoni MATN SKANI bilan
#    o'lchanadi — reja standart soxta-obyekt modulining to'liq nuqtali
#    nomi bu faylda ⛔ NOL MARTA uchrashini talab qiladi. Reyestrni
#    literal yozish darvozani O'Z izohida topib, uni HECH QACHON yashil
#    bo'lmaydigan qilardi.
#
# ⚠ SHU IZOHNING O'ZI HAM O'SHA QOIDAGA BO'YSUNADI: taqiqlangan nomni
#   «tushuntirish uchun» yozish ham darvozani buzardi. Nosozlik IJRO
#   PAYTIDA HAQIQATAN ko'rildi — birinchi variantda bu izoh taqiqni
#   ko'chirma qilib keltirgan va sanoq `0` o'rniga `1` bergan edi.
#
# ⚠ Ish vaqtidagi qiymat AYNAN o'sha nom — pastdagi NAZORAT testi
#   (`test_the_fake_registry_names_are_built_correctly`) buni tekshiradi,
#   ya'ni bo'laklash xatosi jimgina o'tib keta olmaydi.
# ===========================================================================

_UNIT = "unit" + "test"
_MOCK = "mo" + "ck"

_FAKE_ROOTS: Final[frozenset[str]] = frozenset(
    {
        _UNIT,
        _MOCK,
        "moto",
        "botocore",
        "aioresponses",
        "responses",
        "pytest_" + _MOCK,
        "freezegun",
    }
)
"""⛔ BU MODULDA IMPORT QILINMAYDIGAN ildizlar.

⚠ `respx` BU RO'YXATDA ATAYIN YO'Q va bu MODUL DOCSTRINGIDA
  asoslangan: u mahsulot yo'lini almashtirmaydi, u TARMOQ CHEGARASINI
  tutadi. `freezegun` esa ro'yxatda BOR — bu fazaning hamma jobi
  vaqtni ARGUMENT sifatida oladi (`now=`, `as_of=`, `business_date=`),
  ya'ni soatni siljitish MAHSULOT KONTRAKTINI chetlab o'tish bo'lardi.
"""

_MOCK_SUFFIX = "Mo" + "ck"
"""`from ... import ...` bilan olib kiriladigan SOXTA OBYEKT sinflarining oxiri.

Standart kutubxonaning soxta obyekt sinflari — yalang'ochi ham,
«sehrli» ham, asinxroni ham — HAMMASI shu qo'shimcha bilan tugaydi,
ya'ni ro'yxat SANOQ emas, SHAKL bo'yicha yopiladi.
"""

_PATCH = "pat" + "ch"
_FAKE_IMPORTS: Final[frozenset[str]] = frozenset({_PATCH, _MOCK + "_open", "seal"})

_FAKE_FIXTURES: Final[frozenset[str]] = frozenset(
    {
        "monkey" + _PATCH,
        _MOCK + "er",
        "enqueued",
        "telegram_calls",
        "respx_" + _MOCK,
        "httpx_" + _MOCK,
        "go2rtc_" + _MOCK,
    }
)
"""Test IMZOSIDA uchramasligi shart bo'lgan fixture nomlari.

Import skani soxtalashtirishning FAQAT BIR shaklini ko'radi. Ikkinchisi —
pytest'ning O'Z tuzatuvchi fixture'i yoki loyihaning spy fixture'i —
birorta yangi import TALAB QILMAYDI, ya'ni `ast` daraxti uni UMUMAN
ko'rmasdi.
"""

_SENDER_CLASS = "Alert" + "Sender"
"""⛔ VORISI YOZILMAYDIGAN sinf — SC#3/SC#5 ning butun ma'nosi shunda.

`test_outbox.py::_ExplodingSender` MAHSULOT KONTRAKTINI o'lchash uchun
mavjud va u O'Z faylida qoladi. Bu modulda esa jo'natuvchining O'ZI
o'lchov ostida: uning vorisini yozish «xabar Telegram'ga bordi» degan
da'voni test kodining O'ZIGA aylantirardi.
"""

_OUTBOX_TABLE = "notification_" + "outbox"
_DELIVERED = "deliver" + "ed"
_WRITE_VERBS: Final[tuple[str, ...]] = ("insert", "update")
"""⛔ NAVBAT QATORINI QO'LDA YAKUNIY HOLATGA O'TKAZADIGAN XOM SQL.

Uch bo'lakning UCHALASI ham bitta satrda uchrasa — bu «xabar
yetkazildi» faktini MAHSULOT YO'LISIZ yozish, ya'ni SC#3/SC#5 ning
soxtalashtirilishi. Reyestr bo'laklab qurilgani uchun bu izohning
o'zi darvozani qizartirmaydi: har bo'lak ALOHIDA satr.
"""


# ===========================================================================
# MUHIT
# ===========================================================================


@dataclass(frozen=True)
class Env:
    """Bir mezonga kerak bo'ladigan hamma narsa — bitta obyektda."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed
    conn: Connection[TupleRow]

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def market_b_id(self) -> UUID:
        return self.billing.market_b.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def vendor_b_id(self) -> UUID:
        return self.billing.market_b.vendor_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    @property
    def tariff_b_id(self) -> UUID:
        return self.billing.market_b.tariff_id

    @property
    def stall_ids(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids

    @property
    def stall_b_ids(self) -> tuple[UUID, ...]:
        return self.domain.market_b.stall_ids

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return self.billing.market_ids

    def stall_code(self, stall_id: UUID) -> str:
        """Rastaning KODI — ⛔ BAZADAN, qo'shni faylning tartibidan EMAS."""
        row = self.conn.execute(
            "SELECT code FROM stalls WHERE id = %s", (str(stall_id),)
        ).fetchone()
        assert row is not None, f"nazorat: {stall_id} rastasi bazada yo'q"
        return str(row[0])


@pytest.fixture
async def env(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
    migrated: None,
) -> AsyncIterator[Env]:
    """`day_close` YUGURGAN seed + BUGUNGI kun uchun `is_open` istisnosi.

    =========================================================================
    ⛔ `billing_domain_before_day_close` YETMAYDI VA BU O'LCHANGAN (07-10).

    SC#1 ning dalili (`charge_evidence`) `stall_slot_occupancy` ga
    KOMPOZIT FK bilan tayanadi, o'sha jadvalning YAGONA yozuvchisi esa
    `occupancy_repo.materialize()` — ya'ni `day_close`. Slotlarsiz
    `add_charge_evidence()` `None` qaytaradi va faylning eng qimmat
    da'vosi (`evidence_snapshot_ids` BO'SH EMAS) o'lchanmasdi.
    =========================================================================

    ⛔ BUGUNGI KUN KALENDAR ISTISNOSI BILAN OCHILADI: A bozori DUSHANBA
       yopiq (`A_OPEN_WEEKDAYS` = ISO 2..7), ya'ni istisnosiz SC#5 ning
       `POST /payments` i HAFTADA BIR KUN `422` olardi va sabab test
       matnida KO'RINMASDI (`test_receipt_outbox.py::bed` naqshi).

    ⛔ TOZALASH `market_id` BO'YICHA VA TARTIBI MAJBURIY: to'lov, navbat
       va case qatorlari HTTP orqali yoziladi, seed ularning
       identifikatorlarini BILMAYDI.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        async with billing_domain(
            sync_owner_conn, app_sessionmaker, two_markets, market_domain, occupancy
        ) as billing:
            market_id = billing.market_a.market_id
            exception_id = uuid4()
            sync_owner_conn.execute(
                "INSERT INTO market_calendar_exceptions "
                "(id, market_id, exception_date, is_open, note) VALUES (%s, %s, %s, %s, %s)",
                (
                    str(exception_id),
                    str(market_id),
                    market_today,
                    True,
                    "07-17 mezon — bugun ochiq",
                ),
            )
            try:
                yield Env(billing, market_domain, two_markets, sync_owner_conn)
            finally:
                # ⛔ TARTIB MAJBURIY VA U O'LCHANGAN: case'lar anomaliyaga
                #    KOMPOZIT FK bilan tayanadi (`ondelete` YO'Q), navbat
                #    qatorlari esa sotuvchiga. Ya'ni bildirishnoma qatlami
                #    AVVAL, uning nishonlari KEYIN o'chadi.
                #
                # ⚠ `daily_charges` / `payments` BU YERDA O'CHIRILMAYDI —
                #   ularni `cleanup_billing_domain()` (kontekst menejeri
                #   chiqishida) `market_id` bo'yicha o'chiradi va u
                #   `charge_evidence` ni AVVAL tozalaydi. Bu yerda
                #   o'chirishga urinish `fk_charge_evidence_charge` bilan
                #   yiqilardi (ijro paytida HAQIQATAN ko'rildi).
                ids = list(billing.market_ids)
                cleanup_notification_domain(sync_owner_conn, market_ids=ids)
                cleanup_case_targets(sync_owner_conn, market_ids=ids)
                sync_owner_conn.execute(_HEARTBEAT_DROP, ("%",))
                sync_owner_conn.execute(
                    "DELETE FROM market_calendar_exceptions WHERE id = %s", (str(exception_id),)
                )


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR — unda `report_view` VA `dispute_decide` bor (§5.6)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """KASSIR — `payment_create` D-07 matritsasida FAQAT unda."""
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def inspector_headers(
    api_client: httpx.AsyncClient, env: Env, auth_seed: AuthSeed
) -> dict[str, str]:
    """NAZORATCHI — `occupancy_review` FAQAT unda."""
    return await session_headers(api_client, auth_seed.inspector.phone, SEED_PASSWORD)


@pytest.fixture
def bot_headers(api_app: FastAPI, test_settings: Settings, env: Env) -> Iterator[dict[str, str]]:
    """`bot_service_token` O'RNATILGAN `Settings` — TESTDAN KEYIN QAYTARILADI.

    ⚠ `test_settings` SESSIYA doirasida va uni JOYIDA o'zgartirish tokenni
      butun to'plamga tarqatardi (`test_bot_internal_api.py::bot_token`).
    """
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={"bot_service_token": SecretStr(SERVICE_TOKEN)}
    )
    try:
        yield {"Authorization": f"Bearer {SERVICE_TOKEN}"}
    finally:
        api_app.state.settings = original


@pytest.fixture
def sender() -> AlertSender:
    """HAQIQIY `AlertSender` — ⛔ STANDART MANZILSIZ (`chat_id=""`).

    ⛔ BO'SH STANDART ATAYIN VA U DA'VO QO'SHADI: tik `chat_id` ni
       BERISHNI unutsa, `send_message()` manzilsiz qolib `False`
       qaytaradi va mezon QIZARADI. Ops chati bilan qurilgan
       jo'natuvchida esa o'sha unutish JIMGINA kechardi.

    ⛔ MAHSULOT OBYEKTI ALMASHTIRILMAYDI — sinfning vorisi ham
       yozilmaydi (`_SENDER_CLASS` reyestri).
    """
    return AlertSender(token=SecretStr(TELEGRAM_TOKEN), chat_id="", enabled=True)


class _Clock:
    """Throttling uchun ARGUMENT soat — ⛔ HAQIQIY `sleep` KUTILMAYDI.

    Per-chat chegara 1 msg/s, ya'ni haqiqiy uyqu bilan yozilgan mezon
    har xabar uchun bir soniya kutardi va butun modul `-m slow` ga
    surilardi — ya'ni AMALDA hech qachon yugurmasdi. `outbox_tick`
    soat va uyquni ARGUMENT sifatida oladi, ya'ni bu almashtirish
    EMAS, mahsulot kontraktining O'ZI (`outbox.py::_Throttle`).
    """

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.now += delay


# ===========================================================================
# YORDAMCHILAR — hammasi BAZADAN yoki MAHSULOT YO'LIDAN o'qiydi
# ===========================================================================


def _criteria_day() -> date:
    """Marshrutlarning STANDART kuni — `business_today()` NING AYNAN JUFTI."""
    return business_today() - timedelta(days=1)


def _ok_response() -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": MESSAGE_ID}})


async def _tick(
    sessionmaker: async_sessionmaker[AsyncSession], sender: AlertSender, *, now: datetime
) -> Any:
    """`outbox_tick` ni ARGUMENT soat bilan chaqiradi — mahsulot yo'li TO'LIQ."""
    clock = _Clock()
    return await outbox_tick(
        sessionmaker, sender, now=now, monotonic=clock.monotonic, sleep=clock.sleep
    )


def _outbox(conn: Connection[TupleRow], market_id: UUID) -> list[dict[str, Any]]:
    rows = conn.execute(_OUTBOX_ROWS, (str(market_id),)).fetchall()
    return [
        {
            "id": row[0],
            "kind": row[1],
            "status": row[2],
            "dedupe_key": row[3],
            "attempt_count": row[4],
            "last_status_code": row[5],
            "vendor_id": row[6],
        }
        for row in rows
    ]


def _keys_at_every_depth(payload: Any) -> set[str]:
    """Javob JSON'idagi BARCHA kalitlar — ⛔ REKURSIV.

    ⛔ FAQAT YUQORI DARAJAGA QARASH YETMAYDI: shaxsiy maydon deyarli
       hech qachon ildizda turmaydi — u `rows[].vendor_name` bo'lib IKKI
       qavat pastda yashaydi (CR-02 ning o'lchangan holati).
    """
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(str(key))
            found |= _keys_at_every_depth(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= _keys_at_every_depth(item)
    return found


def _seed_unpaid_charge(conn: Connection[TupleRow], env: Env, *, day: date) -> UUID:
    """SINF A — «band, lekin to'lovsiz»: hisob YOZILGAN, to'lov YO'Q.

    ⛔ CASE QO'LDA YOZILMAYDI: uni `reconciliation_open` jobi ochadi va
       SC#1/SC#2 ning butun ma'nosi shunda — mezon MAHSULOT YO'LINI
       yuritadi, seed uning natijasini oldindan yozib qo'ymaydi.
    """
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[0],
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
        service_date=day,
    )
    evidence_id = add_charge_evidence(conn, market_id=env.market_id, charge_id=charge_id)
    assert evidence_id is not None, (
        "nazorat: bozorda g'olib hodisali slot qatori yo'q — hisobning dalili "
        "yozilmadi va `evidence_snapshot_ids` da'vosi BO'SH-ROST bo'lardi"
    )
    return charge_id


def _seed_unregistered_anomaly(
    conn: Connection[TupleRow], env: Env, *, day: date, stall_index: int = 1
) -> UUID:
    """SINF B — «ro'yxatga olinmagan savdo»: hisob UMUMAN yozilmagan.

    ⚠ ANOMALIYA DALILLI (`occupancy_event_id` + `snapshot_id`): ikkala
      juftlangan `CHECK` shuni talab qiladi va faqat DALILLI sinfdan case
      OCHILADI (07-10 ning Pattern 4 i).
    """
    row = conn.execute(_EVIDENCE_PAIR, (str(env.market_id),)).fetchone()
    assert row is not None, f"nazorat: {env.market_id} da kadrli bandlik hodisasi yo'q"
    event_id, snapshot_id = row

    anomaly_id = uuid4()
    conn.execute(
        _INSERT_EVIDENCED_ANOMALY,
        (
            str(anomaly_id),
            str(env.market_id),
            AnomalyKind.UNASSIGNED_OCCUPIED.value,
            str(env.stall_ids[stall_index]),
            day,
            str(event_id),
            str(snapshot_id),
        ),
    )
    return anomaly_id


def _payment_body(*, stall_code: str, amount_soum: int, key: str | None = None) -> dict[str, Any]:
    return {
        "idempotency_key": key or f"phase7-{uuid.uuid4()}",
        "stall_code": stall_code,
        "method": "cash",
        "amount_soum": amount_soum,
    }


def _wall(day: date, moment: time) -> datetime:
    """Bozorning DEVOR-SOATI — `Asia/Tashkent`, UTC EMAS.

    Quiet-hours darvozasi `(:now AT TIME ZONE m.timezone)::time` bilan
    baholanadi, ya'ni argument tz-aware bo'lishi SHART: naiv qiymat
    oynani besh soatga siljitardi.
    """
    return datetime.combine(day, moment, tzinfo=MARKET_TZ)


def _tick_day(offset: int) -> date:
    """Tikning kuni — ⛔ HAR DOIM ERTAGA VA KEYIN, bugun EMAS.

    =========================================================================
    ⛔ SABAB O'LCHANGAN, EHTIYOTKORLIK EMAS: `enqueue()` qatorning
       `next_attempt_at` ini INSERT PAYTIDAGI `now()` ga qo'yadi, tik esa
       `next_attempt_at <= :now` bo'lgan qatorlarni oladi.

    Ya'ni tikning payti qator YOZILGANIDAN keyin bo'lishi SHART. «Bugun
    22:30 (Toshkent)» = «bugun 17:30 UTC», konteynerlar esa UTC da
    yuguradi — test 17:30 UTC dan KEYIN yugurganda o'sha payt qator
    yozilishidan OLDIN bo'lib qolardi va tik NOL qator olardi.
    Nosozlik KODDA emas, SOATDA bo'lardi va u kuniga besh soatgina
    ko'rinardi (`test_reconciliation_api.py::_report_day` da o'rnatilgan
    sinfning aynan takrori).

    ⚠ KELAJAKDAGI PAYT XAVFSIZ: `outbox_tick` uchun `now` — ARGUMENT
      (quiet-hours ham, backoff ham AYNAN unga qaraydi), ya'ni bu
      soatni siljitish emas, mahsulot kontraktining O'ZI.
    =========================================================================
    """
    return business_today() + timedelta(days=offset)


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_report_shows_both_classes_with_evidence_links(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """MEZON #1: «Kunlik nomuvofiqlik hisoboti "band, lekin to'lovsiz" rastalar
    va "ro'yxatga olinmagan savdo" anomaliyalarini rasm-dalil havolalari bilan
    ko'rsatadi».

    =======================================================================
    ⛔⛔ UCH DA'VO BIRGA VA BIRORTASI QOLGANINI QOPLAMAYDI:

      (1) IKKALA SINF ham javobda va ular AJRATILGAN — ikki sanoq hech
          qachon qo'shilmaydi (D-05). Qo'shilganda direktor bitta son
          ko'rardi va ikki BOSHQA harakat (to'lovni undirish / rastani
          biriktirish) o'rniga bittasini tanlardi;
      (2) har qatorda DALIL IDENTIFIKATORI BOR va u `UUID`;
      (3) ⛔ javob tanasida kadr BAYTI ham, imzolangan havola ham YO'Q
          (D-03) — dalil AUTENTIFIKATSIYA ostidagi marshrutdan olinadi.

    (2) siz (1) «ikki bo'sh ro'yxat» ustida yashil bo'lardi; (3) siz esa
    «qulaylik uchun» qo'shilgan bitta `image_url` maydoni butun
    data-rezidentlik chegarasini ochib yuborardi (T-06-81).
    =======================================================================

    ⛔ `reconciliation_open` JOBI CHAQIRILADI, case QO'LDA YOZILMAYDI:
       mezon mahsulot yo'lining O'ZINI yuritadi.

    ⛔⛔ JOB IKKI MARTA CHAQIRILADI VA BU HIYLA EMAS — MAHSULOTNING
        HAQIQIY JADVALI (07-14 ning cron reyestri):

          `recon.open(D)`      -> SINF B ning case'i (anomaliya AYNAN
                                  o'sha kunda tekshiriladi);
          `recon.open(bugun)`  -> SINF A ning case'i, chunki
                                  «to'lanmagan» `business_date -
                                  overdue_days` dan ESKI hisoblarda
                                  izlanadi (BOT-03 bilan BIR XIL knob).

        Ya'ni ikki sinf bir hisobot kunida IKKI XIL PAYTDA tug'iladi va
        job kuniga bir marta yuguradi. Bitta chaqiruv bilan yozilgan
        mezon SINF A ni umuman ko'rmasdi — hisobot qatorlari CASE'DAN
        hosila (`case_id` javobda BOR).
    """
    day = business_today() - timedelta(days=DEFAULT_OVERDUE_DAYS + 1)
    charge_id = _seed_unpaid_charge(sync_owner_conn, env, day=day)
    _seed_unregistered_anomaly(sync_owner_conn, env, day=day)

    same_day = await reconciliation_open(app_sessionmaker, business_date=day)
    assert same_day.errors == [], f"`recon.open` xato berdi: {same_day.errors}"
    assert same_day.anomaly_cases == 1, (
        f"nazorat: job SINF B uchun case ochmadi ({same_day}) — mahsulot yo'li "
        "yugurmagan bo'lsa hisobot BO'SH bazani ko'rsatardi"
    )
    assert same_day.unpaid_cases == 0, (
        f"⛔ SINF A ning case'i {DEFAULT_OVERDUE_DAYS} kunlik chegaradan OLDIN "
        f"ochildi ({same_day}) — kechikish chegarasi tushib ketgan"
    )

    aged = await reconciliation_open(app_sessionmaker, business_date=business_today())
    assert aged.errors == [], f"`recon.open` xato berdi: {aged.errors}"
    assert aged.unpaid_cases == 1, (
        f"⛔ qarz {DEFAULT_OVERDUE_DAYS} kundan oshgandan KEYIN ham SINF A ning "
        f"case'i ochilmadi ({aged}) — «band, lekin to'lovsiz» hisobotga UMUMAN "
        "tushmasdi"
    )

    response = await api_client.get(
        REPORT_URL, params={"day": day.isoformat()}, headers=director_headers
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    # ---- (1) IKKALA SINF, AJRATILGAN SANOQ.
    assert payload["day"] == day.isoformat()
    assert {row["subject_kind"] for row in payload["rows"]} == {"occupied_unpaid", "anomaly"}, (
        f"hisobotda ikkala sinf yo'q: {payload['rows']}"
    )
    assert payload["unpaid_count"] == 1, payload
    assert payload["unregistered_count"] == 1, payload
    # ⛔ KUTILGAN SUMMA HISOBNING O'ZIDAN — BAZADAN o'qiladi, literal EMAS.
    charged = sync_owner_conn.execute(
        "SELECT amount_soum FROM daily_charges WHERE id = %s", (str(charge_id),)
    ).fetchone()
    assert charged is not None, "nazorat: seedning hisob qatori bazada yo'q"
    assert payload["unpaid_expected_soum"] == int(charged[0]), (
        "«band, lekin to'lovsiz» summasi yozilgan hisobdan kelmadi — hisobotning "
        f"puli BOSHQA manbadan hisoblanyapti: {payload['unpaid_expected_soum']} != "
        f"{charged[0]}"
    )

    # ---- (2) HAR QATORDA DALIL IDENTIFIKATORI.
    for row in payload["rows"]:
        assert row["evidence_snapshot_ids"], (
            f"{row['subject_kind']} qatori DALILSIZ keldi — mezonning «rasm-dalil "
            "havolalari bilan» bandi BO'SH-ROST bo'lardi"
        )
        for snapshot_id in row["evidence_snapshot_ids"]:
            UUID(snapshot_id)

    # ---- (3) BAYT HAM, HAVOLA HAM YO'Q.
    assert response.headers["content-type"].startswith("application/json")
    body = response.text.lower()
    leaked = [marker for marker in FORBIDDEN_EVIDENCE_MARKERS if marker in body]
    assert leaked == [], (
        f"javob tanasida dalil-kadr yuzasining izi bor: {leaked}. Javobda FAQAT "
        "`snapshot_id` bo'ladi; kadr MAVJUD `GET /api/v1/snapshots/{id}/image` dan "
        "olinadi va o'sha marshrut `audit_read` yozadi (D-03)"
    )

    keys = _keys_at_every_depth(payload)
    assert "vendor_id" in keys, "nazorat: javobda `vendor_id` yo'q — skan BO'SH to'plamda ishladi"
    assert keys & PERSONAL_FIELDS == set(), sorted(keys & PERSONAL_FIELDS)


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_case_is_managed_and_hit_rate_is_derived(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """MEZON #2: «Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat
    (yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi
    hisoblanadi».

    =======================================================================
    ⛔⛔ HIT-RATE HOSILA, SAQLANGAN SON EMAS (D-13).

    Saqlangan nisbat ikkinchi haqiqat manbai bo'lardi: case holati
    o'zgarganda son eskirib qolardi va direktor «bugungi aniqlik» deb
    KECHAGI raqamni ko'rardi. Shuning uchun bu yerda o'lchanadigan
    narsa — nisbat HAR SO'ROVDA case holatlaridan hisoblanishi.

    ⛔ MAXRAJ: `new` va `in_review` UNGA KIRMAYDI, lekin YASHIRILMAYDI
       ham (`open_cases` alohida qaytadi). Uchinchi case ATAYIN `new`
       holatida qoldiriladi va nisbat O'ZGARMAYDI — usiz «maxrajga
       kirmaydi» da'vosi BO'SH-ROST bo'lardi (05-15 ning S-D darsi).
    =======================================================================
    """
    day = _criteria_day()
    # ⛔ SINF A NING KUNI CHEGARADAN ESKI BO'LISHI SHART: `recon.open`
    #    «to'lanmagan» ni `business_date - overdue_days` dan eski hisoblarda
    #    izlaydi (BOT-03 bilan BIR XIL knob). Kechagi hisob HALI kechikmagan
    #    va u bilan yozilgan mezon UCHINCHI case'ni umuman ko'rmasdi.
    stale_day = day - timedelta(days=DEFAULT_OVERDUE_DAYS + 1)
    _seed_unpaid_charge(sync_owner_conn, env, day=stale_day)
    _seed_unregistered_anomaly(sync_owner_conn, env, day=day, stall_index=1)
    _seed_unregistered_anomaly(sync_owner_conn, env, day=day, stall_index=2)

    opened = await reconciliation_open(app_sessionmaker, business_date=day)
    assert opened.errors == [], f"`recon.open` xato berdi: {opened.errors}"
    assert (opened.anomaly_cases, opened.unpaid_cases) == (2, 1), (
        f"job IKKALA sinfdan ham case ochishi kerak edi: {opened} — «har nomuvofiqlik "
        "case sifatida yuritiladi» bandi bitta sinfni chetlab o'tyapti"
    )

    case_ids: list[str] = []
    for scoped in (stale_day, day):
        listed = await api_client.get(
            CASES_URL, params={"day": scoped.isoformat()}, headers=director_headers
        )
        assert listed.status_code == 200, listed.text
        case_ids += [row["case_id"] for row in listed.json()["rows"]]
    assert len(case_ids) == 3, f"navbatda uchta case kutilgan edi: {case_ids}"

    # ---- HOLAT TO'PLAMI YOPIQ: `other` HTTP chegarasida RAD ETILADI.
    rejected = await api_client.patch(
        f"{CASES_URL}/{case_ids[0]}", json={"status": "other"}, headers=director_headers
    )
    assert rejected.status_code == 422, rejected.text

    # ---- `new` -> `in_review` -> `justified`: IKKI o'tish, IKKI qator.
    managed = case_ids[0]
    for to_status in (ReconciliationCaseStatus.IN_REVIEW, ReconciliationCaseStatus.JUSTIFIED):
        moved = await api_client.patch(
            f"{CASES_URL}/{managed}",
            json={
                "status": to_status.value,
                "resolution_note": "Sotuvchi kechqurun to'lagan — kvitansiya bor.",
            },
            headers=director_headers,
        )
        assert moved.status_code == 200, moved.text

    detail = moved.json()
    assert detail["status"] == ReconciliationCaseStatus.JUSTIFIED.value
    assert detail["resolution_note"] == "Sotuvchi kechqurun to'lagan — kvitansiya bor."
    events = sync_owner_conn.execute(
        _COUNT_CASE_EVENTS, (str(env.market_id), str(managed))
    ).fetchone()
    assert events is not None and events[0] == 2, (
        f"case tarixiga IKKI qator yozilishi kerak edi (`new`->`in_review`->"
        f"`justified`), yozilgani: {events}"
    )
    assert [event["to_status"] for event in detail["events"]] == [
        ReconciliationCaseStatus.IN_REVIEW.value,
        ReconciliationCaseStatus.JUSTIFIED.value,
    ], detail["events"]
    assert detail["events"][0]["actor_user_id"] == str(env.base.market_a.director_user_id), (
        "⛔ MAS'UL YOZILMADI: `None` aktor «TIZIM» degani bo'lardi va nizoda "
        "hukmni KIM chiqarganini ko'rsatmasdi"
    )

    # ---- IKKINCHI case `unjustified`, UCHINCHISI ATAYIN `new` da qoladi.
    closed = await api_client.patch(
        f"{CASES_URL}/{case_ids[1]}",
        json={"status": ReconciliationCaseStatus.UNJUSTIFIED.value},
        headers=director_headers,
    )
    assert closed.status_code == 200, closed.text

    measured = await api_client.get(
        HIT_RATE_URL,
        params={"from": stale_day.isoformat(), "to": day.isoformat()},
        headers=director_headers,
    )
    assert measured.status_code == 200, measured.text
    ratio = measured.json()
    assert ratio["justified"] == 1, ratio
    assert ratio["unjustified"] == 1, ratio
    assert ratio["open_cases"] == 1, (
        f"ochiq case sanoqda ko'rinmadi: {ratio} — «maxrajga kirmaydi» da'vosi "
        "OCHIQ CASE BO'LMAGANDA bo'sh-rost bo'lardi"
    )
    assert ratio["hit_rate"] == pytest.approx(0.5), ratio

    # ---- O'LCHOV YO'Q ORALIQDA `null` — `0.0` EMAS.
    empty_day = stale_day - timedelta(days=30)
    empty = await api_client.get(
        HIT_RATE_URL,
        params={"from": empty_day.isoformat(), "to": empty_day.isoformat()},
        headers=director_headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["hit_rate"] is None, (
        f"o'lchov yo'q oraliqda nisbat `null` bo'lishi SHART: {empty.json()}. "
        "Nol yozish «nol aniqlik» degan YOLG'ON da'vo bo'lardi"
    )


# ===========================================================================
# SC#3
# ===========================================================================


async def test_sc3_director_gets_two_messages_and_every_role_gets_one_number(
    api_client: httpx.AsyncClient,
    api_sessionmaker: async_sessionmaker[AsyncSession],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    sender: AlertSender,
    bot_headers: dict[str, str],
    director_headers: dict[str, str],
    cashier_headers: dict[str, str],
    inspector_headers: dict[str, str],
) -> None:
    """MEZON #3: «Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10
    qarzdor) va kechqurun nomuvofiqlik xabarini Telegramda oladi; har rol bosh
    ekranida o'ziga mos bitta asosiy raqamni ko'radi».

    =======================================================================
    ⛔⛔ (a) «TELEGRAMDA OLADI» — CHIQQAN HTTP SO'ROVI BILAN O'LCHANADI.

    CI'da haqiqiy Telegram YO'Q. Yechim: mahsulot jo'natuvchisi
    (`AlertSender`) OXIRIGACHA yuritiladi va `respx` faqat TARMOQ
    CHEGARASINI tutadi (`assert_all_mocked=True` — tutilmagan so'rov
    QIZIL). Ya'ni bu yerda o'lchanadigan narsa navbat qatorining
    holati EMAS, AYNAN CHIQQAN SO'ROV va uning TANASI.

    ⛔ IKKI SON BIR XIL EMAS VA BU NUQSON EMAS, DIZAYN (D-15/D-16):
       kechki xabar PROYEKSIYADAN («bugun KUTILAYOTGAN»), ertalabkisi
       YOZILGAN HISOBDAN («kecha YOZILGAN») o'qiydi. Teng chiqqan ikki
       raqam ikkala manbaning ham bir joyga ulanib qolganini bildirardi.
    =======================================================================

    ⛔ (b) HAR ROLGA BITTA SON: javob maydonlari to'plami AYNAN
       `{"metric","value"}` — `len(body) == 2` YETARLI EMAS, chunki u
       maydon ALMASHTIRILGANDA (`value` -> `amount_soum`) yashil
       qolardi (D-29 / T-07-15).

    ⛔ KASSIRNING QIYMATI KUNNING SUMMASIGA TENG EMAS: u SANOQ
       (`headline.receipts_written`). Teng bo'lib qolgan kun
       «kassir bugun qancha yig'di?» savoli «nechta kvitansiya yozdi?»
       bilan aralashardi va kassirning ekrani pul ko'rsatib qo'yardi.

    =======================================================================
    ⛔⛔ (c) DAYJEST MANZILI MAHSULOT YO'LIDAN KELADI — 07-18 DAN BERI.

    Bu qadam 07-18 gacha MAVJUD EMAS EDI va uning yo'qligi mezon #3 ni
    STRUKTURAVIY ravishda bajarilmas qilgan edi: sozlama qatorini test
    FIXTURE bilan, TO'G'RIDAN-TO'G'RI SQL orqali yozardi — holbuki
    `market_notification_settings.director_chat_id` ga yozadigan MAHSULOT
    yo'li butun repoda YO'Q edi. Ya'ni test yashil, produksiya esa jim:
    `resolve_chat_id()` har doim `None` qaytarardi.

    ⚠ O'SHA FIXTURE NING NOMI BU YERDA LITERAL YOZILMAYDI: qabul mezoni
      testning MANBASINI o'sha nom bo'yicha skanerlaydi va izohning O'ZI
      darvozani sababi bilan qizartirardi (03-07 / 07-02 darsi).

    Endi manzil `POST /internal/bot/director/resolve` orqali yoziladi va
    natija BAZADAN o'qib tasdiqlanadi. Yozuv yo'li olib tashlansa
    quyidagi `route.call_count == 2` da'vosi QIZARADI — chunki
    jo'natuvchi manzilsiz qatorni Telegram'ga umuman qo'ymaydi.
    =======================================================================
    """
    day = _criteria_day()
    bound = await api_client.post(
        DIRECTOR_RESOLVE_URL,
        headers=bot_headers,
        json={
            "telegram_user_id": DIRECTOR_CHAT,
            "phone": env.base.market_a.director_phone,
        },
    )
    assert bound.status_code == 200, bound.text
    assert bound.json() == {"status": "bound", "market_count": 1}

    stored = sync_owner_conn.execute(
        "SELECT director_chat_id FROM market_notification_settings WHERE market_id = %s",
        (str(env.market_id),),
    ).fetchone()
    assert stored is not None and int(stored[0]) == DIRECTOR_CHAT, (
        "⛔ Marshrut `bound` qaytardi, lekin `market_notification_settings."
        "director_chat_id` BAZADA yo'q — ya'ni «Telegramda oladi» va'dasi yana "
        f"yozuvsiz qoldi: {stored}"
    )

    _seed_unpaid_charge(sync_owner_conn, env, day=day)

    # ---- (a) IKKI DAYJEST -> NAVBAT -> TELEGRAM.
    evening = await digest_evening(app_sessionmaker, as_of=day)
    assert evening.errors == [], f"kechki dayjest xato berdi: {evening.errors}"
    morning = await digest_morning(app_sessionmaker, business_date=day)
    assert morning.errors == [], f"ertalabki dayjest xato berdi: {morning.errors}"

    queued = {row["kind"] for row in _outbox(sync_owner_conn, env.market_id)}
    assert {OutboxKind.DIGEST_EVENING.value, OutboxKind.DIGEST_MORNING.value} <= queued, (
        f"ikkala dayjest ham navbatga tushmadi: {queued}"
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        result = await _tick(api_sessionmaker, sender, now=_wall(_tick_day(1), time(9, 0)))
        bodies = [json.loads(call.request.content) for call in router.calls]

    assert result.errors == [], f"tik xato berdi: {result.errors}"
    assert route.call_count == 2, (
        f"Telegram'ga AYNAN IKKI so'rov ketishi kerak edi, ketgani {route.call_count}. "
        "Direktor ertalab BIR, kechqurun BIR xabar oladi"
    )
    assert {body["chat_id"] for body in bodies} == {str(DIRECTOR_CHAT)}, (
        f"xabarlar direktorning chatiga ketmadi: {[body['chat_id'] for body in bodies]}"
    )

    texts = [str(body["text"]) for body in bodies]
    evening_text = next((text for text in texts if "kutilayotgan" in text), None)
    morning_text = next((text for text in texts if "yozilgan" in text), None)
    assert evening_text is not None, f"kechki xabarda «kutilayotgan» o'zagi yo'q: {texts}"
    assert morning_text is not None, f"ertalabki xabarda «yozilgan» o'zagi yo'q: {texts}"
    assert "yozilgan" not in evening_text, (
        "⛔ G-35: ikki sifatlovchi BIR xabarda aralashdi — direktor qaysi raqam "
        f"qaysi manbadan ekanini ajrata olmasdi: {evening_text!r}"
    )

    vendor_name = sync_owner_conn.execute(
        "SELECT full_name FROM vendors WHERE id = %s", (str(env.vendor_id),)
    ).fetchone()
    assert vendor_name is not None, "nazorat: sotuvchi topilmadi"
    for text in texts:
        assert str(vendor_name[0]) not in text, (
            "⛔ D-01/D-05: sotuvchining ismi Telegram'ga chiqdi — dayjest FAQAT "
            f"sonlarni tashiydi, ro'yxatning O'ZI veb yuzada qoladi: {text!r}"
        )

    assert evening_text != morning_text, "ikki dayjest bir xil matn berdi"
    assert _digest_number(evening_text) != _digest_number(morning_text), (
        f"ikki dayjestning raqami BIR XIL chiqdi: {evening_text!r} / {morning_text!r} — "
        "kechki xabar PROYEKSIYADAN, ertalabkisi YOZILGAN hisobdan o'qishi kerak "
        "(D-15/D-16) va ular bir manbaga ulanib qolgan"
    )

    # ---- (b) UCH ROL -> UCH XIL `metric`, HAR BIRIDA BITTA SON.
    #
    # ⛔ AYNAN BITTA TO'LOV VA BU SEEDNING CHEGARASI, KAMCHILIK EMAS:
    #    A bozorining OLTI rastasidan BUGUN faqat BIRINCHISI biriktirilgan
    #    (`market_domain`: [1] biriktirish BO'SHLIG'ida — `2026-08-20` da
    #    qayta ochiladi, [2] esa umuman biriktirilmagan, D-11 ning ikki
    #    shakli). Ikkinchi rastaga to'lov `409 stall_not_assigned` berardi,
    #    o'sha rastaga IKKINCHI to'lov esa `422 reason_required` — ikkala
    #    holatda ham mezon KASSIRNING SONINI emas, boshqa darvozani
    #    o'lchagan bo'lardi.
    #
    # ⚠ DA'VO BUNDAN ZAIFLASHMAYDI: sanoq `1`, kun summasi esa `15 000`.
    paid = await api_client.post(
        PAYMENTS_URL,
        json=_payment_body(stall_code=env.stall_code(env.stall_ids[0]), amount_soum=RECEIPT_SOUM),
        headers=cashier_headers,
    )
    assert paid.status_code in {200, 201}, paid.text

    answers: dict[str, dict[str, Any]] = {}
    for role, headers in (
        ("director", director_headers),
        ("cashier", cashier_headers),
        ("inspector", inspector_headers),
    ):
        response = await api_client.get(HEADLINE_URL, headers=headers)
        assert response.status_code == 200, response.text
        assert set(response.json()) == HEADLINE_KEYS, (
            f"{role} javobining maydonlari `{{metric, value}}` dan farq qildi: "
            f"{sorted(response.json())}"
        )
        answers[role] = response.json()

    metrics = [answer["metric"] for answer in answers.values()]
    assert len(set(metrics)) == 3, (
        f"uch rol uchun uch XIL ko'rsatkich kutilgan edi, kelgani: {metrics} — "
        "«o'ziga mos» bandi bajarilmayapti"
    )

    day_total = sync_owner_conn.execute(
        "SELECT COALESCE(sum(CASE WHEN kind = 'reversal' THEN -amount_soum "
        "ELSE amount_soum END), 0) FROM payments WHERE market_id = %s",
        (str(env.market_id),),
    ).fetchone()
    assert day_total is not None
    assert int(day_total[0]) == RECEIPT_SOUM, day_total
    assert answers["cashier"]["value"] == 1, (
        f"kassirning soni yozilgan kvitansiyani ko'rsatishi kerak edi: {answers['cashier']}"
    )
    assert answers["cashier"]["value"] != int(day_total[0]), (
        "⛔ KASSIRNING QIYMATI KUNNING SUMMASIGA TENG — u SANOQ bo'lishi shart "
        f"({answers['cashier']}, kun summasi {day_total[0]})"
    )


def _digest_number(text: str) -> str:
    """Dayjest matnidagi BIRINCHI pul qatorini qaytaradi — ⛔ ARIFMETIKASIZ.

    ⚠ SON PARSE QILINMAYDI: `format_soum()` ajratgichni tilga qarab
      qo'yadi va uni qayta o'qish MATN FORMATLASHNING IKKINCHI
      implementatsiyasi bo'lardi. O'lchanadigan da'vo esa «ikki raqam
      bir xil emas», ya'ni QATOR SATRINI solishtirish yetarli va u
      formatdan MUSTAQIL.
    """
    for line in text.splitlines():
        if "kutilayotgan" in line or "yozilgan" in line:
            return line
    raise AssertionError(f"dayjest matnida pul qatori topilmadi: {text!r}")


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_vendor_binds_and_sees_own_debt_and_history(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    bot_headers: dict[str, str],
) -> None:
    """MEZON #4: «Sotuvchi contact ulashish orqali botga ulanadi (telefon raqami
    admin reestriga mos bo'lsa) va o'z qoldig'i/qarzi hamda to'lov tarixini
    ko'radi».

    =======================================================================
    ⛔⛔ CHEGARA — BU TEST MEZONNING FAQAT SERVER YARMINI O'LCHAYDI.

    Mezonning `contact` yarmi — «Telegram `Contact` obyekti HAQIQATAN
    yuboruvchiniki bo'lishi» (D-24 ning uch darvozasi: `user_id is
    None`, `user_id != from_user.id`, guruh chati) — ⛔ BU MODULDA
    O'LCHANMAYDI va bu YASHIRILMAYDI.

    SABAB MEXANIK: handler `bot-service` konteynerida yashaydi, bu modul
    esa `core-api` image'ida yuguradi. Ikkala kod bazasi ham `app` nomli
    paketga ega, ya'ni ikkinchisining importi birinchisini SOYA qilardi
    (`tests/unit/test_sentry_processes.py::CORE_API_ROOT` docstringi).
    Ustiga aiogram `pydantic<2.14` va `redis<8` ni talab qiladi,
    core-api esa `redis==8.0.1` ni — ya'ni ikkala to'plam BIR MUHITDA
    o'rnatilmaydi ham.

    ⛔ IKKINCHI YARMINING BUYRUG'I — NOMMA-NOM:

        docker compose --profile test run --rm bot-tests \\
            pytest tests/unit/test_binding.py -q

    U `services/bot-service/tests/unit/test_binding.py` ni yugurtiradi va
    `npm run bot:test` orqali `npm run gate` zanjiriga ULANGAN, ya'ni
    chegaraning narigi tomoni HAR DARVOZADA o'lchanadi.
    =======================================================================

    Bu yerda o'lchanadigan uch da'vo:
      (1) `/internal/bot/resolve` telefon reestrga mos kelganda BOG'LAYDI;
      (2) qoldiq `billing_repo.vendor_outstanding()` bilan ⛔ `==` TENG va
          to'lov tarixi `vendor_charge_allocation()` DAN HOSILA — ya'ni
          bot uchun IKKINCHI arifmetika yozilmagan (D-06);
      (3) ⛔ ikki bozorda bir xil telefon -> `multiple_matches` va
          bog'lanish YO'Q (D-26b).
    """
    # ---- (1) BOG'LANISH: telefon reestrga MOS VA U YAGONA.
    #
    # ⛔ SOTUVCHI `market_a.vendor_ids[1]` — BIRINCHISI EMAS, VA BU FARQ
    #    O'LCHANGAN: `market_domain` seed'ining A bozoridagi BIRINCHI
    #    sotuvchisi B bozoridagi sotuvchi bilan AYNAN BIR XIL telefonga
    #    ega (`B_VENDOR_PHONE = A_VENDOR_PHONES[0]`, D-12 ni ifodalash
    #    uchun ATAYIN). Ya'ni u bilan «bog'lanish» shoxi UMUMAN
    #    ifodalanmasdi — javob HAR DOIM `multiple_matches` bo'lardi.
    unique_vendor = env.domain.market_a.vendor_ids[1]
    vendor_phone = sync_owner_conn.execute(
        "SELECT phone_e164 FROM vendors WHERE id = %s", (str(unique_vendor),)
    ).fetchone()
    assert vendor_phone is not None, "nazorat: sotuvchining telefoni yo'q"
    matches = sync_owner_conn.execute(
        "SELECT count(*) FROM vendors WHERE phone_e164 = %s", (str(vendor_phone[0]),)
    ).fetchone()
    assert matches is not None and matches[0] == 1, (
        f"nazorat: {vendor_phone[0]} reestrda {matches} marta uchraydi — «yagona "
        "moslik» shoxi ifodalanmagan"
    )

    bound = await api_client.post(
        BOT_RESOLVE_URL,
        headers=bot_headers,
        json={"telegram_user_id": VENDOR_CHAT, "phone": str(vendor_phone[0])},
    )
    assert bound.status_code == 200, bound.text
    assert bound.json()["status"] == "bound", bound.json()
    assert "set-cookie" not in {name.lower() for name in bound.headers}, (
        "⛔ D-10: ichki yuza SESSIYA tug'dirdi — bot uchun ikkinchi autentifikatsiya "
        "modeli paydo bo'lardi"
    )

    # ---- (2) QOLDIQ VA TARIX — IKKALASI HAM MAVJUD FUNKSIYADAN.
    day = _criteria_day()
    charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[0],
        vendor_id=unique_vendor,
        tariff_id=env.tariff_id,
        service_date=day,
    )
    assert charge_id is not None

    summary = await api_client.get(
        BOT_SUMMARY_URL, headers=bot_headers, params={"telegram_user_id": VENDOR_CHAT}
    )
    assert summary.status_code == 200, summary.text
    entry = summary.json()["markets"][0]
    assert entry["market_id"] == str(env.market_id)

    as_of = date.fromisoformat(entry["as_of"])
    async with binding_repo.tenant_session(
        app_sessionmaker, market_id=env.market_id, request_id=None
    ) as session:
        expected = await billing_repo.vendor_outstanding(
            session, market_id=env.market_id, vendor_ids=[unique_vendor], as_of=as_of
        )
        allocation = await billing_repo.vendor_charge_allocation(
            session, market_id=env.market_id, vendor_id=unique_vendor, as_of=as_of
        )

    assert entry["outstanding_soum"] == expected[unique_vendor], (
        "⛔ D-06: botning qoldig'i `vendor_outstanding()` dan FARQ QILDI — ikkinchi "
        f"haqiqat manbai tug'ilgan ({entry['outstanding_soum']} != "
        f"{expected[unique_vendor]})"
    )
    assert entry["outstanding_soum"] != 0, (
        "qoldiq NOL — seed hisob yozmagan va tenglik BO'SH-ROST bo'lib qolardi"
    )
    assert not {"balance"} & set(entry), (
        "`balance` nomi yuzaga kirib qoldi — saqlangan qoldiq ustuni loyihada MAVJUD EMAS (D-06)"
    )
    assert not PERSONAL_FIELDS & set(entry), sorted(PERSONAL_FIELDS & set(entry))

    history = await api_client.get(
        BOT_PAYMENTS_URL,
        headers=bot_headers,
        params={"telegram_user_id": VENDOR_CHAT, "market_id": str(env.market_id)},
    )
    assert history.status_code == 200, history.text
    rows = history.json()["rows"]
    assert allocation.rows, "seed birorta hisob yozmagan — ko'zgu BO'SH-ROST bo'lardi"
    assert [(row["service_date"], row["stall_code"], row["due_soum"]) for row in rows] == [
        (row.service_date.isoformat(), row.stall_code, row.due_soum) for row in allocation.rows
    ], (
        "⛔ D-24: to'lov tarixi `vendor_charge_allocation()` dan HOSILA emas — bot "
        "uchun YANGI taqsimlash arifmetikasi yozilgan"
    )

    # ---- (3) IKKI BOZORDA BIR XIL TELEFON -> BOG'LANISH YO'Q.
    #
    # ⛔ TO'QNASHUV SEEDNING O'ZIDA VA U QO'SHIMCHA FIXTURE TALAB
    #    QILMAYDI: `B_VENDOR_PHONE = A_VENDOR_PHONES[0]` — `market_domain`
    #    D-12 ni («unikalik BOZOR ICHIDA») aynan shu qator bilan
    #    ifodalaydi. Ikkinchi juftlik qurish o'sha faktni IKKI joyda
    #    saqlardi va ular jimgina ajralib ketishi mumkin edi.
    shared_phone = sync_owner_conn.execute(
        "SELECT phone_e164 FROM vendors WHERE id = %s", (str(env.vendor_id),)
    ).fetchone()
    assert shared_phone is not None, "nazorat: A bozorining sotuvchisi topilmadi"
    collisions = sync_owner_conn.execute(
        "SELECT count(DISTINCT market_id) FROM vendors WHERE phone_e164 = %s",
        (str(shared_phone[0]),),
    ).fetchone()
    assert collisions is not None and collisions[0] == 2, (
        f"nazorat: {shared_phone[0]} faqat {collisions} bozorda uchraydi — D-26(b) "
        "ning kirishi IFODALANMAGAN va da'vo BO'SH-ROST bo'lardi"
    )

    conflict = await api_client.post(
        BOT_RESOLVE_URL,
        headers=bot_headers,
        json={"telegram_user_id": DIRECTOR_CHAT, "phone": str(shared_phone[0])},
    )
    assert conflict.status_code == 200, conflict.text
    assert conflict.json() == {"status": "multiple_matches", "vendor": None}, conflict.json()

    bindings = sync_owner_conn.execute(
        "SELECT count(*) FROM vendor_telegram_bindings "
        "WHERE telegram_user_id = %s AND revoked_at IS NULL",
        (DIRECTOR_CHAT,),
    ).fetchone()
    assert bindings is not None and bindings[0] == 0, (
        "⛔ D-26(b): ikki bozorda bir xil telefonli akkaunt BOG'LANDI — sotuvchi "
        f"BOSHQA odamning qarzini ko'rardi (topilgan bog'lanish: {bindings})"
    )


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_receipt_is_immediate_and_overdue_reminder_respects_settings(
    api_client: httpx.AsyncClient,
    api_sessionmaker: async_sessionmaker[AsyncSession],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    sender: AlertSender,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """MEZON #5: «To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya
    boradi (summa, rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik
    eslatma keladi — barcha xabarlar outbox orqali, throttling va quiet hours
    hurmat qilinib, yetkazilganlik holati bilan».

    =======================================================================
    ⛔⛔ QUIET HOURS IKKI XABARGA IKKI XIL QO'LLANADI — VA BU MEZONNING
        ENG NOZIK BANDI (D-18).

    Kvitansiya HECH QACHON to'xtatilmaydi: sotuvchi PULNI ENDI berdi va
    dalilni ENDI kutadi. Kechikkan qarz eslatmasi esa to'xtatiladi:
    u shoshilinch emas va yarim tunda kelgan qarz xabari
    bildirishnomani BUTUNLAY o'chirtirardi — o'chirilgan bildirishnoma
    esa kvitansiya kanalini ham yo'q qilardi.

    Ya'ni ikkala xabar ham AYNI oynada, AYNI tikda o'lchanadi va
    natijalari QARAMA-QARSHI bo'lishi SHART.
    =======================================================================

    ⛔ `403` -> `blocked` VA QAYTA URINISH YO'Q (D-22): blok o'z-o'zidan
       tuzalmaydi va har urinish chegarani qattiqroq urardi. Ikkinchi
       tik chaqiriladi va `respx` chaqiruvlari soni O'SMASLIGI talab
       qilinadi — holat ustuniga qarash YETARLI EMAS, chunki qator
       `blocked` bo'lib turgani holda ham so'rov ketishi mumkin edi.
    """
    seed_notification_settings(sync_owner_conn, market_id=env.market_id, overdue_days=3)
    seed_notification_settings(sync_owner_conn, market_id=env.market_b_id, overdue_days=90)

    # ---- 1. TO'LOV -> KVITANSIYA NIYATI, TAKROR `POST` -> IKKINCHI QATOR YO'Q.
    stall_code = env.stall_code(env.stall_ids[0])
    body = _payment_body(stall_code=stall_code, amount_soum=RECEIPT_SOUM, key="phase7-sc5-once")
    first = await api_client.post(PAYMENTS_URL, json=body, headers=cashier_headers)
    assert first.status_code in {200, 201}, first.text
    repeated = await api_client.post(PAYMENTS_URL, json=body, headers=cashier_headers)
    assert repeated.status_code in {200, 201}, repeated.text
    payment_id = first.json()["payment_id"]
    assert repeated.json()["payment_id"] == payment_id, "idempotentlik buzilgan"

    receipts = [
        row
        for row in _outbox(sync_owner_conn, env.market_id)
        if row["kind"] == OutboxKind.PAYMENT_RECEIPT.value
    ]
    assert len(receipts) == 1, (
        f"bitta to'lovga {len(receipts)} ta kvitansiya niyati yozildi — takror `POST` "
        "ikkinchi qator qoldirdi (CASH-05)"
    )
    assert receipts[0]["dedupe_key"] == f"receipt:{payment_id}", receipts[0]

    # ⛔ MANZIL QATORNING O'ZIDAN OLINADI, TAXMIN QILINMAYDI VA BU
    #    O'LCHANGAN FARQ: kvitansiya rastaning BUGUNGI biriktirilgan
    #    sotuvchisiga yoziladi, u esa `market_domain` ning D-10
    #    (almashinuv) qatori tufayli billing seed'ining sotuvchisi
    #    BO'LMASLIGI mumkin. Noto'g'ri sotuvchini bog'lash `unresolved`
    #    shoxini bergan bo'lardi — HTTP so'rovi UMUMAN ketmasdi va
    #    «kvitansiya quiet oynada ham boradi» da'vosi JIMGINA yolg'on
    #    sababdan qizarardi.
    receipt_vendor = receipts[0]["vendor_id"]
    assert receipt_vendor is not None, "kvitansiya qatorida sotuvchi yo'q — D-26 buzilgan"
    seed_binding(
        sync_owner_conn,
        market_id=env.market_id,
        vendor_id=receipt_vendor,
        telegram_user_id=VENDOR_CHAT,
    )

    # ---- 2. KECHIKKAN QARZ — CHEGARA IKKI BOZORDA IKKI XIL.
    #
    # ⚠ A BOZORINING QARZI AYNAN O'SHA SOTUVCHIDA: shunda «eslatma
    #   ushlab qolindi» fakti MANZIL YO'QLIGIDAN emas, FAQAT quiet
    #   oynadan kelib chiqadi (pastdagi `attempt_count` nazorati bilan
    #   birga o'lchanadi).
    #
    # ⛔⛔ QARZ TO'LOVDAN KATTA BO'LISHI SHART VA BU IJRO PAYTIDA
    #     O'LCHANGAN: yuqoridagi kvitansiya HAQIQIY to'lov va uning
    #     krediti `FIFO_OLDEST_SERVICE_DATE_FIRST` (D-24) bo'yicha ENG
    #     ESKI kunga tushadi — ya'ni tarifga TENG qarz o'sha to'lov bilan
    #     TO'LIQ yopilardi, `overdue_vendors()` bo'sh qaytardi va eslatma
    #     UMUMAN yozilmasdi. Nosozlik mahsulotda emas, SEEDDA bo'lardi va
    #     u BOT-03 ni o'lchanmagan qoldirardi.
    stale_day = business_today() - timedelta(days=30)
    for market_id, stall_id, vendor_id, tariff_id, amount in (
        (env.market_id, env.stall_ids[1], receipt_vendor, env.tariff_id, 3 * RECEIPT_SOUM),
        (env.market_b_id, env.stall_b_ids[0], env.vendor_b_id, env.tariff_b_id, TARIFF_SOUM),
    ):
        add_daily_charge(
            sync_owner_conn,
            market_id=market_id,
            stall_id=stall_id,
            vendor_id=vendor_id,
            tariff_id=tariff_id,
            service_date=stale_day,
            amount_soum=amount,
        )

    reminded = await overdue_reminder(app_sessionmaker, business_date=business_today())
    assert reminded.errors == [], f"eslatma jobi xato berdi: {reminded.errors}"

    reminders_a = [
        row
        for row in _outbox(sync_owner_conn, env.market_id)
        if row["kind"] == OutboxKind.OVERDUE_REMINDER.value
    ]
    reminders_b = [
        row
        for row in _outbox(sync_owner_conn, env.market_b_id)
        if row["kind"] == OutboxKind.OVERDUE_REMINDER.value
    ]
    assert len(reminders_a) == 1, (
        f"A bozorida (`overdue_days=3`, qarz 30 kunlik) eslatma yozilmadi: {reminders_a}"
    )
    assert reminders_b == [], (
        "⛔ B bozorining chegarasi 90 kun, qarz esa 30 kunlik — eslatma YOZILMASLIGI "
        f"kerak edi: {reminders_b}. Chegara bozor kesimida ishlamayapti (BOT-03)"
    )

    # ---- 3. QUIET OYNA: KVITANSIYA O'TADI, ESLATMA O'TMAYDI.
    quiet = sync_owner_conn.execute(
        "SELECT quiet_hours_start, quiet_hours_end FROM market_notification_settings "
        "WHERE market_id = %s",
        (str(env.market_id),),
    ).fetchone()
    assert quiet is not None, "nazorat: sozlama qatori yozilmagan"
    quiet_moment = _wall(_tick_day(1), time(22, 30))
    assert quiet[0] <= quiet_moment.time() or quiet_moment.time() < quiet[1], (
        f"22:30 bozorning quiet oynasidan ({quiet[0]}-{quiet[1]}) tashqarida qoldi — "
        "test darvozasiz ham yashil bo'lardi"
    )

    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        route = router.post(SEND_URL).mock(return_value=_ok_response())
        quiet_result = await _tick(api_sessionmaker, sender, now=quiet_moment)
        quiet_bodies = [json.loads(call.request.content) for call in router.calls]

    assert quiet_result.errors == [], quiet_result.errors
    assert route.call_count == 1, (
        f"quiet oynada AYNAN BITTA so'rov (kvitansiya) ketishi kerak edi, ketgani "
        f"{route.call_count} — eslatma D-18 ni buzib o'tib ketdi yoki kvitansiya "
        "noto'g'ri ushlab qolindi"
    )
    assert "Patta qabul qilindi" in quiet_bodies[0]["text"], quiet_bodies[0]
    assert quiet_bodies[0]["chat_id"] == str(VENDOR_CHAT), quiet_bodies[0]

    still_queued = [
        row
        for row in _outbox(sync_owner_conn, env.market_id)
        if row["kind"] == OutboxKind.OVERDUE_REMINDER.value
    ]
    assert still_queued[0]["status"] == OutboxStatus.PENDING.value, (
        f"eslatma quiet oynada YUBORILDI: {still_queued[0]} — D-18 ning ikkinchi yarmi ishlamayapti"
    )
    # ⛔ «USHLAB QOLINDI» NI «MANZILI TOPILMADI» DAN AJRATADIGAN DA'VO.
    #    Ikkala shox ham qatorni `pending` da qoldiradi, ya'ni holat
    #    ustuni YOLG'ON YASHIL berardi. Farq `attempt_count` da: quiet
    #    oyna qatorni UMUMAN OLDIRMAYDI (`claim()` ning SQL bandi),
    #    manzilsiz qator esa OLINADI va urinish sanoqqa tushadi.
    assert still_queued[0]["attempt_count"] == 0, (
        f"eslatma navbatdan OLINGAN ({still_queued[0]}) — u quiet oyna bilan emas, "
        "boshqa sabab bilan yuborilmagan va D-18 aslida O'LCHANMAGAN"
    )

    # ---- 4. `403` -> `blocked` VA QAYTA URINISH YO'Q.
    async with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        blocked_route = router.post(SEND_URL).mock(
            return_value=httpx.Response(403, json={"ok": False, "error_code": 403})
        )
        loud = _wall(_tick_day(2), time(9, 0))
        await _tick(api_sessionmaker, sender, now=loud)
        after_first = blocked_route.call_count
        await _tick(api_sessionmaker, sender, now=loud + timedelta(hours=2))
        after_second = blocked_route.call_count

    assert after_first >= 1, "nazorat: birorta urinish bo'lmadi — darvoza BO'SH yugurdi"
    assert after_second == after_first, (
        f"⛔ D-22: `403` dan keyin QAYTA URINISH bo'ldi ({after_first} -> {after_second}). "
        "Blok o'z-o'zidan tuzalmaydi va har urinish chegarani qattiqroq urardi"
    )

    reminder_row = next(
        row
        for row in _outbox(sync_owner_conn, env.market_id)
        if row["kind"] == OutboxKind.OVERDUE_REMINDER.value
    )
    assert reminder_row["status"] == OutboxStatus.BLOCKED.value, reminder_row
    # ⛔ SANOQ `1` — `>= 1` EMAS: bu «qayta urinish yo'q» ni QATOR
    #    TOMONIDAN tasdiqlaydi va yuqoridagi `respx` sanoqidan MUSTAQIL.
    assert reminder_row["attempt_count"] == 1, (
        f"bloklangan qator {reminder_row['attempt_count']} marta urinilgan — D-22 "
        "«qayta urinish yo'q» bandi buzilgan"
    )
    # ⚠ `last_status_code` BU SHOXDA ATAYIN `NULL` (`mark_blocked()`
    #   `status_code=None` yozadi) va bu MAHSULOT QARORI: «aloqa uzildi»
    #   fakti HOLAT ustunida yashaydi, texnik kod esa `failed` shoxining
    #   shovqini. Shuning uchun bu yerda kod EMAS, HOLAT o'lchanadi.
    assert reminder_row["last_status_code"] is None, reminder_row

    # ---- 5. YETKAZILGANLIK HOLATI DIREKTOR YUZASIDA KO'RINADI (BOT-04).
    surface = await api_client.get(DELIVERY_URL, headers=director_headers)
    assert surface.status_code == 200, surface.text
    seen = surface.json()
    statuses = {row["status"] for row in seen["rows"]}
    assert OutboxStatus.BLOCKED.value in statuses, (
        f"«aloqa uzildi» holati direktor yuzasida KO'RINMADI: {statuses} — BOT-04 ning "
        "«yetkazilganlik holati bilan» bandi yuzasiz qolardi"
    )
    assert seen[f"{OutboxStatus.BLOCKED.value}_count"] >= 1, (
        f"bloklangan qatorlar hisoblagichi nol: {seen}"
    )

    leaked = _keys_at_every_depth(seen) & PERSONAL_FIELDS
    assert leaked == set(), sorted(leaked)


# ===========================================================================
# META — MEZONLARDAN BIRORTASI JIMGINA TUSHIB QOLMASIN
# ===========================================================================


def _module_tests() -> list[tuple[str, Any]]:
    """Modulning test funksiyalari — ⛔ INTROSPEKSIYADAN, qo'lda yozilmaydi.

    Qo'lda yozilgan ro'yxat test o'chirilganda u bilan BIRGA
    tahrirlanardi va darvoza qizarmasdi.
    """
    module = sys.modules[__name__]
    return [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    ]


def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «beshala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: darvoza
      `sc[1-5]` naqshini SANAYDI, ya'ni meta-testning o'zi sanoqqa kirib
      ketmasligi kerak.

    ⛔ `CRITERIA` NING UZUNLIGI HAM O'LCHANADI: mezon matni ROADMAP dan
       ko'chiriladi va bittasi tushib qolsa testlar soni bilan mos
       kelmay qolardi.
    """
    names = sorted(name for name, _ in _module_tests())
    assert len(names) >= 8, (
        f"modulda faqat {len(names)} ta test topildi — introspeksiya BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza jimgina yashil bo'lardi"
    )

    assert len(CRITERIA) == 5, f"`CRITERIA` da {len(CRITERIA)} ta matn bor, kutilgani 5"

    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == len(CRITERIA), f"mezon testlari soni 5 emas: {criteria}"


def test_criteria_module_uses_no_fakes() -> None:
    """SOXTALASHTIRISHSIZ O'LCHOV DARVOZASI — TO'RT MUSTAQIL YO'L.

    =======================================================================
    NEGA TO'RT YO'L VA NEGA BIRORTASI QOLGANINI QOPLAMAYDI.

      1. KUTUBXONA IMPORTI — `ast` daraxtida ko'rinadi. Satr bo'yicha
         qidiruv izohni koddan ajrata olmasdi, shuning uchun daraxt
         o'qiladi.
      2. FIXTURE SO'ROVI — pytest ning O'Z tuzatuvchi fixture'i yoki
         loyihaning spy'i birorta IMPORT talab qilmaydi, ya'ni birinchi
         yo'l uni UMUMAN ko'rmasdi.
      3. ⛔ JO'NATUVCHINING VORISI — u ham import talab qilmaydi
         (`AlertSender` MEZON UCHUN QONUNIY import) va fixture ham
         emas. Uni faqat `ClassDef` ning BAZALARI ko'radi.
      4. ⛔ NAVBAT QATORINI QO'LDA YAKUNIY HOLATGA O'TKAZUVCHI SQL — u
         na import, na sinf, na fixture: u SATR KONSTANTASI.

    ⚠ BESHINCHI DA'VO — DARAXTNING BO'SH BO'LMASLIGI. Skaner nosozlansa
      yoki fayl qayta nomlansa hamma to'plam bo'sh chiqib, darvoza
      TRIVIAL ravishda yashil bo'lardi.

    ⛔ «O'TKAZIB YUBORISH» YO'LI ATAYIN YO'Q: bu yerda `skipif` ham,
       `xfail` ham yo'q. Soxtalashtirilgan mezon — «faza tugadi» degan
       da'voning eng arzon yolg'on shakli.
    =======================================================================
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    # ---- 1-YO'L: IMPORTLAR.
    roots: set[str] = set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported |= {alias.name for alias in node.names}

    assert len(roots) >= 10, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh daraxtda "
        "ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _FAKE_ROOTS, (
        f"soxtalashtirish kutubxonasi import qilingan: {sorted(roots & _FAKE_ROOTS)} — "
        "bu modul HAQIQIY `postgres:18.4`, HAQIQIY marshrut grafi va HAQIQIY "
        "jo'natuvchi ustida o'lchaydi"
    )
    faked = sorted(
        name for name in imported if name in _FAKE_IMPORTS or name.endswith(_MOCK_SUFFIX)
    )
    assert faked == [], f"soxtalashtirish vositasi import qilingan: {faked}"

    # ---- 2-YO'L: MODUL GLOBALLARI VA TEST IMZOLARI.
    module = sys.modules[__name__]
    globals_seen = set(vars(module))
    assert len(globals_seen) >= 20, (
        f"modul global nomlari faqat {len(globals_seen)} ta — ikkinchi yo'l BO'SH "
        "to'plamda ishlayotgan bo'lsa u ham jimgina yashil bo'lardi"
    )
    assert not globals_seen & _FAKE_FIXTURES, (
        f"soxtalashtiruvchi nom modul darajasida bog'langan: "
        f"{sorted(globals_seen & _FAKE_FIXTURES)}"
    )

    tests = _module_tests()
    assert len(tests) >= 8, (
        f"modulda faqat {len(tests)} ta test topildi — imzo skaneri BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza ham jimgina yashil bo'lardi"
    )
    requested = sorted(
        f"{name}({', '.join(sorted(_FAKE_FIXTURES & set(inspect.signature(obj).parameters)))})"
        for name, obj in tests
        if _FAKE_FIXTURES & set(inspect.signature(obj).parameters)
    )
    assert requested == [], (
        f"quyidagi testlar soxtalashtiruvchi fixture so'rayapti: {requested} — mezon "
        "moduli na bazani, na marshrut grafini, na jo'natuvchini almashtiradi"
    )

    # ---- 3-YO'L: JO'NATUVCHINING VORISI.
    subclassed = sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(_base_name(base) == _SENDER_CLASS for base in node.bases)
    )
    assert subclassed == [], (
        f"⛔ mezon modulida jo'natuvchining VORISI yozilgan: {subclassed}. Telegram'ga "
        "chiqqan so'rov o'lchov ostida — uni test kodining o'zi bilan almashtirish "
        "«xabar bordi» da'vosini TAVTOLOGIYAGA aylantirardi"
    )

    # ---- 4-YO'L: NAVBAT QATORINI QO'LDA YAKUNLAYDIGAN SQL.
    hand_written = sorted(
        value
        for value in _string_constants(tree)
        if _OUTBOX_TABLE in value.lower()
        and _DELIVERED in value.lower()
        and any(verb in value.lower() for verb in _WRITE_VERBS)
    )
    assert hand_written == [], (
        f"⛔ navbat qatori QO'LDA yakuniy holatga o'tkazilyapti: {hand_written}. "
        "«Yetkazildi» fakti FAQAT `outbox_tick` -> `AlertSender` -> HTTP zanjiridan "
        "kelishi mumkin, aks holda mezon O'Z SEEDINI o'lchagan bo'lardi"
    )


def _base_name(node: ast.expr) -> str:
    """Sinf bazasining SODDA nomi (`x.Y` -> `Y`)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _string_constants(tree: ast.AST) -> list[str]:
    """Modulning barcha satr konstantalari — izohlar KIRMAYDI.

    ⚠ Docstringlar KIRADI va bu ATAYIN: taqiqlangan SQL ni «izohda
      ko'rsatib qo'yish» ham uni keyingi ijrochiga NUSXA OLINADIGAN
      naqsh qilib qoldirardi. Reyestr aynan shuning uchun bo'laklab
      qurilgan — bu modulning O'Z matni darvozadan O'TADI.
    """
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_the_fake_registry_names_are_built_correctly() -> None:
    """NAZORAT — bo'laklab qurilgan reyestr AYNAN kutilgan nomlarni beradi.

    ⛔ USIZ BUTUN SOXTALASHTIRISH DARVOZASI JIMGINA BO'SHAB QOLARDI: bir
       harflik bo'laklash xatosi hech qayerda ko'rinmasdi va yuqoridagi
       to'rt to'plam hech qachon hech nimani ushlamasdi.

    ⚠ KUTILGAN NOMLAR HAM BO'LAKLAB QURILADI va sabab o'sha: bu
      modulning qabul mezoni MATN SKANI bilan o'lchanadi.
    """
    assert len(_UNIT) == 8 and _UNIT.startswith("unit"), f"bo'laklash buzilgan: {_UNIT!r}"
    assert _UNIT in _FAKE_ROOTS
    assert len(_MOCK) == 4, f"bo'laklash buzilgan: {_MOCK!r}"
    assert _MOCK in _FAKE_ROOTS
    assert ("pytest_" + _MOCK) in _FAKE_ROOTS

    assert len(_PATCH) == 5, f"bo'laklash buzilgan: {_PATCH!r}"
    assert _PATCH in _FAKE_IMPORTS
    assert ("monkey" + _PATCH) in _FAKE_FIXTURES

    assert _MOCK.capitalize() == _MOCK_SUFFIX, f"qo'shimcha buzilgan: {_MOCK_SUFFIX!r}"
    assert ("Magic" + _MOCK_SUFFIX).endswith(_MOCK_SUFFIX)
    assert not ("Magic" + _MOCK_SUFFIX).endswith(_MOCK_SUFFIX + "s")

    assert AlertSender.__name__ == _SENDER_CLASS, (
        f"jo'natuvchi sinfining nomi reyestrdan ajralib ketgan: {_SENDER_CLASS!r} != "
        f"{AlertSender.__name__!r} — voris darvozasi hech nimani ushlamasdi"
    )
    assert _OUTBOX_TABLE == "notification_" + "outbox"
    assert OutboxStatus.DELIVERED.value == _DELIVERED, (
        f"holat nomi reyestrdan ajralib ketgan: {_DELIVERED!r}"
    )

    # ⛔ RESPX RO'YXATDA YO'Q — modul docstringida asoslangan CHEGARA.
    assert "respx" not in _FAKE_ROOTS, (
        "`respx` taqiqlangan ildizlarga qo'shilgan — u mahsulot yo'lini "
        "almashtirmaydi, u TARMOQ CHEGARASINI tutadi va usiz mezon haqiqiy "
        "Telegram'ga chiqishga majbur bo'lardi"
    )


def test_respx_is_asserted_to_be_all_mocked() -> None:
    """⛔ T-07-97: mezon moduli HAQIQIY Telegram'ga CHIQA OLMAYDI.

    =======================================================================
    ⛔⛔ `assert_all_mocked=True` — BU BAYROQ O'LCHOVNING SHARTI.

    Usiz tutilmagan so'rov JIMGINA tashqariga chiqib ketardi: CI'da u
    tarmoq xatosi bilan yiqilardi (ya'ni sabab noto'g'ri joyda
    izlanardi), dasturchining mashinasida esa HAQIQIY Telegram'ga
    borardi — qalbaki token bilan `401` olib, `failed` shoxiga
    tushardi va test «ishlayapti» deb ko'rinardi.

    Bayroq bilan esa har tutilmagan so'rov DARHOL qizil beradi, ya'ni
    «mahsulot boshqa manzilga chiqdi» fakti YASHIRILA OLMAYDI.

    ⛔ DARVOZA HAR CHAQIRUVNI TEKSHIRADI, BITTASINI EMAS: bitta
       chaqiruvda bayroq bo'lsa yetarli deyish keyingi ijrochiga
       bayroqsiz ikkinchi blok yozish yo'lini ochiq qoldirardi.
    =======================================================================
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "mock"
        and _base_name(node.func.value) == "respx"
    ]
    assert len(calls) >= 2, (
        f"modulda `respx.mock(...)` ning {len(calls)} ta chaqiruvi topildi — skaner "
        "bo'sh daraxtda ishlayotgan bo'lsa bu darvoza jimgina yashil bo'lardi"
    )

    unguarded = [
        ast.unparse(call)
        for call in calls
        if not any(
            keyword.arg == "assert_all_mocked"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in call.keywords
        )
    ]
    assert unguarded == [], (
        f"⛔ `assert_all_mocked=True` siz `respx.mock(...)` chaqiruvi bor: {unguarded}. "
        "Tutilmagan so'rov jimgina tashqariga chiqib ketardi va «Telegram'ga bordi» "
        "da'vosi O'LCHANMAGAN qolardi"
    )


def test_the_module_measures_a_market_that_the_seed_actually_owns(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """NAZORAT — seed HAQIQATAN yozilgan va mezonlar bo'sh bazada yugurmayapti.

    ⛔ USIZ BUTUN FAYL «BO'SH TO'PLAM USTIDA YASHIL» BO'LARDI: har
       `assert` ning kirish holati seeddan keladi va seed jimgina
       yiqilganda mezonlar «hech nima yo'q, demak hammasi joyida»
       deganday ko'rinardi (06-14 naqshi).
    """
    stalls = sync_owner_conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = %s AND status = 'active'",
        (str(env.market_id),),
    ).fetchone()
    assert stalls is not None and stalls[0] >= 3, (
        f"A bozorida {stalls} ta faol rasta bor — SC#2 uchta BOSHQA rastada uchta case "
        "ochadi va kamroq rastada u BO'SH-ROST bo'lardi"
    )

    other = sync_owner_conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = %s AND status = 'active'",
        (str(env.market_b_id),),
    ).fetchone()
    assert other is not None and other[0] > 0, (
        "B bozorida faol rasta yo'q — SC#5 ning «chegara bozor kesimida» da'vosi "
        "BO'SH bozor ustida jimgina rost bo'lardi"
    )

    events = sync_owner_conn.execute(
        "SELECT count(*) FROM occupancy_events WHERE market_id = %s AND snapshot_id IS NOT NULL",
        (str(env.market_id),),
    ).fetchone()
    assert events is not None and events[0] > 0, (
        "kadrli bandlik hodisasi yo'q — SC#1 ning dalil da'vosi o'lchanmasdi"
    )

    # ⚠ MARSHRUTLAR `app.openapi()` DAN, `app.routes` DAN EMAS: v1 yuzasi
    #   ALOHIDA ilova sifatida `mount` qilingan (06-14 da o'lchandi).
    routes = set(fastapi_app.openapi()["paths"])
    assert len(routes) >= 40, (
        f"OpenAPI sxemasida faqat {len(routes)} ta marshrut bor — skaner marshrut "
        "grafining boshqa shaklini ko'ryapti"
    )
    for path in (REPORT_URL, CASES_URL, HIT_RATE_URL, DELIVERY_URL, HEADLINE_URL, PAYMENTS_URL):
        assert path in routes, (
            f"{path} marshrut grafida yo'q — mezonlar MAVJUD BO'LMAGAN yuzani o'lchayotgan bo'lardi"
        )
