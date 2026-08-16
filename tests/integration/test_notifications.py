"""Ikki dayjest va BOT-03 eslatmasi — HAQIQIY BAZADA (RECON-03/BOT-03).

=============================================================================
BESHTA QOIDA BU FAYLNING SHAKLINI BELGILAYDI.

  1. ⛔ FAZANING ENG MUHIM O'LCHOVI — IKKI MANBANING TENGSIZLIGI.
     Kechki xabar PROYEKSIYADAN, ertalabki YOZILGAN hisobdan o'qiydi va
     ularning sonlari BIR XIL EMAS. Bu nuqson emas, DIZAYN (D-15/D-16) —
     shuning uchun test farqni «xato» deb emas, KUTILGAN NATIJA deb
     o'lchaydi.

  2. ⛔ KUN SEED TOMONIDAN TANLANADI VA U SESHANBA (`_recent_open_day`).
     Sabab MEXANIK va u sabotajni KO'RINADIGAN qiladi: A bozori
     DUSHANBA yopiq (`A_OPEN_WEEKDAYS` — ISO 1 yo'q). Ya'ni `D` ochiq,
     `D - 1` esa YOPIQ kun va ularning proyeksiyasi STRUKTURAVIY ravishda
     boshqacha. Ixtiyoriy «kecha» tanlansa `D` va `D - 1` ikkalasi ham
     ochiq bo'lardi, ikkala proyeksiya AYNAN teng chiqardi va
     `as_of = D - 1` sabotaji HECH NIMANI qizartirmasdi (05-15 ning S-D
     darsi: sabotaj sistemaga yetib borib ham hech nima qizarmasa,
     tuzatish TESTDA emas, HOLATDA).

  3. ⛔ SESSIYA TENANT KONTEKSTI BILAN — lekin joblar uni O'ZLARI
     o'rnatadi. Test `set_tenant_context()` ni oldindan qo'ymaydi:
     `market_is_open()` INVOKER va fail-closed, ya'ni kontekstsiz HAMMA
     KUN yopiq bo'lardi va proyeksiya JIMGINA nol chiqardi (Pitfall 9).

  4. ⛔ SANALAR BAZADAN OLINADI. `daily_charges` / `payments` da
     `service_date <= business_date` `CHECK` i bor va `business_date`
     `created_at` DAN HOSILA. `date.today()` test JARAYONINING
     mintaqasida hisoblanadi va yarim tunda bir kun farq qilardi —
     test FLAKY bo'lardi va sabab kodda emas, soatda bo'lardi.

  5. ⛔ TESTLAR TELEGRAM'GA CHIQMAYDI va bu TAXMIN emas, O'LCHOV:
     `_no_outbound_http` autouse fixture'i BIROR marshrutsiz `respx`
     routerini o'rnatadi, ya'ni har qanday chiquvchi HTTP so'rov
     `AllMockedAssertionError` bilan yiqiladi. Joblar niyat yozadi,
     jo'natish esa `notify.outbox_tick` ning ishi (D-08/D-23).
=============================================================================
⚠ MATN KONTRAKTI (`07-UI-SPEC.md` §12.2/G-35) BU FAYLDA O'LCHANMAYDI VA
  BU ONGLI: matn `app/jobs/outbox.py::_build_text` da quriladi, u esa
  07-09 ning fayli va bu rejaning `files_modified` ida YO'Q. Bu fayl
  G-35 ning SHAKLINI (yopiq lug'at ustidagi TO'PLAM TENGLIGI) o'zi
  egallik qiladigan qatlamda — `payload` kontraktida — bajaradi.
=============================================================================
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import dataclass, fields
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
import respx
from app.jobs import notification_meta, notifications, reconciliation
from app.jobs.notifications import (
    DIGEST_EVENING_COMPONENT,
    DIGEST_MORNING_COMPONENT,
    OVERDUE_COMPONENT,
    digest_evening,
    digest_morning,
    overdue_reminder,
)
from app.jobs.reconciliation import overdue_cutoff
from app.repositories import digest_repo, outbox_repo
from app.repositories.billing_repo import pending_projection
from app.repositories.headline_repo import revenue_today_soum
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import (
    cleanup_case_targets,
    cleanup_notification_domain,
    seed_case,
    seed_notification_settings,
    seed_outbox_row,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    OutboxKind,
    OutboxRecipientKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import date

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_TASHKENT = ZoneInfo("Asia/Tashkent")

_MORNING = OutboxKind.DIGEST_MORNING.value
_EVENING = OutboxKind.DIGEST_EVENING.value
_REMINDER = OutboxKind.OVERDUE_REMINDER.value
_RECEIPT = OutboxKind.PAYMENT_RECEIPT.value

_QUALIFIER_KEYS = frozenset({"expected_soum", "charged_soum"})
"""⛔ YOPIQ LUG'AT — `07-UI-SPEC.md` §12.2 ning `payload` qatlamidagi aksi.

Kechki xabar «kutilayotgan» sonni, ertalabkisi «yozilgan» sonni tashiydi
va TO'PLAM TENGLIGI ikkinchisining YO'QLIGINI ham o'lchaydi (§16.6 G-35
ning shakli). Oddiy «`expected_soum` bormi?» tekshiruvi kechki payloadga
`charged_soum` HAM qo'shilganda YASHIL qolardi — va aynan o'sha
aralashuv direktorni chalkashtiradi.
"""

_HEARTBEAT = "SELECT last_seen_at, detail FROM system_heartbeats WHERE component = %s"
_OUTBOX_ROWS = (
    "SELECT kind, recipient_kind, vendor_id, dedupe_key, payload "
    "FROM notification_outbox WHERE market_id = %s ORDER BY created_at, id"
)
_CHARGE_SUM = (
    "SELECT COALESCE(sum(amount_soum), 0)::bigint FROM daily_charges "
    "WHERE market_id = %s AND service_date = %s"
)
_CHARGE_COUNT = "SELECT count(*) FROM daily_charges WHERE market_id = %s AND service_date = %s"
_VENDOR_NAME = "SELECT full_name FROM vendors WHERE id = %s"
_UNPAID_CASES = (
    "SELECT count(*) FROM reconciliation_cases rc "
    "JOIN daily_charges c ON c.id = rc.charge_id "
    "WHERE rc.market_id = %s AND c.vendor_id = %s"
)
_INSERT_ADJUSTMENT = (
    "INSERT INTO charge_adjustments "
    "(id, market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""Hisob tuzatishi — job darajasidagi NOSOZLIK holatining YAGONA qurilishi.

Hisobning O'ZIDAN katta `decrease` o'sha kunning qoldig'ini MANFIY qiladi
va `allocate_charge_credit()` uni `ValueError` bilan rad etadi. Holat
o'sha funksiyaning O'Z docstringida nomlab qo'yilgan, ya'ni u erishib
bo'ladigan ma'lumot holati — soxta nosozlik EMAS (07-07 da o'lchangan).
"""

_SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""`charge_adjustments` AUDIT ostida — kontekstsiz `INSERT` egasiz qatordan.

⚠ Blok tugagach kontekst BO'SHATILADI: `sync_owner_conn` autocommit
  rejimida ishlaydi va qoldirilgan qiymat keyingi testga sizib o'tardi.
"""


# ===========================================================================
# Fixture'lar — `test_reconciliation_repo.py::env` naqshi
# ===========================================================================


@dataclass(frozen=True)
class Env:
    """Bir testning butun kirishi — ikki bozor, rastalar, sotuvchilar."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed

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
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    @property
    def shift_id(self) -> UUID:
        return self.billing.market_a.open_shift_id

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return self.billing.market_ids


@pytest.fixture(autouse=True)
def _no_outbound_http() -> Iterator[None]:
    """⛔ HAR QANDAY CHIQUVCHI HTTP SO'ROV YIQILADI — marshrut RO'YXATGA OLINMAGAN.

    Bu «joblar Telegram bilan gaplashmaydi» da'vosining O'LCHOVI
    (D-08/D-23). Grep darvozasi modulda `AlertSender` ning YO'QLIGINI
    ko'radi, bu fixture esa XULQNI: agar biror qatlam baribir tashqariga
    chiqsa, `respx` uni `AllMockedAssertionError` bilan to'xtatadi.

    ⚠ `assert_all_called=False`: bu router HECH QACHON chaqirilmasligi
      KERAK va uning chaqirilmagani XATO EMAS, kutilgan natija.
    """
    with respx.mock(assert_all_called=False):
        yield


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI.

    Dayjestlarning kirishi `daily_charges`, `payments` va tarif zanjiri;
    bandlik foizi esa `stall_slot_occupancy` bo'sh bo'lganda ATAYIN
    `None` qaytaradi va bu ham O'LCHANADIGAN holat
    (`test_occupancy_percent_is_none_when_no_stall_was_measured`).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets)


@pytest.fixture
def notify(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[Env]:
    """`env` USTIGA bildirishnoma jadvallarining tozalanishi.

    ⚠ `env` ARGUMENT sifatida olinadi, faqat «oldin ishlasin» uchun emas:
      pytest fixture'larni TESKARI tartibda yopadi, ya'ni case'lar va
      outbox qatorlari billing qatorlaridan OLDIN o'chadi. Teskari holatda
      `cleanup_billing_domain()` hali havola qilib turgan case tufayli FK
      buzilishi bilan yiqilardi.
    """
    try:
        yield env
    finally:
        ids = list(env.market_ids)
        cleanup_notification_domain(sync_owner_conn, market_ids=ids)
        cleanup_case_targets(sync_owner_conn, market_ids=ids)


# ===========================================================================
# Yordamchilar — hammasi BAZADAN o'qiydi
# ===========================================================================


def _today(conn: Connection[TupleRow]) -> date:
    """`CURRENT_DATE` — ⛔ BAZADAN, `date.today()` DAN EMAS (4-qoida)."""
    row = conn.execute("SELECT CURRENT_DATE").fetchone()
    assert row is not None, "baza sanani qaytarmadi"
    value: date = row[0]
    return value


def _days_ago(conn: Connection[TupleRow], days: int) -> date:
    row = conn.execute("SELECT (CURRENT_DATE - %s::int)::date", (days,)).fetchone()
    assert row is not None, "baza sanani qaytarmadi"
    value: date = row[0]
    return value


def _recent_open_day(conn: Connection[TupleRow]) -> date:
    """O'TMISHDAGI ENG YAQIN SESHANBA — ⛔ `D` ochiq, `D - 1` esa YOPIQ.

    =========================================================================
    ⛔⛔ SANA TASODIFIY EMAS VA U MODUL DOCSTRINGINING 2-QOIDASI.

    A bozori DUSHANBA yopiq (`A_OPEN_WEEKDAYS = (2..7)`), ya'ni seshanba
    tanlanganda `D` ochiq, `D - 1` (dushanba) esa yopiq bo'ladi va ikki
    kunning PROYEKSIYASI strukturaviy ravishda boshqacha chiqadi
    (`market_is_open()` -> summa hisoblanmaydi -> `pending_amount_soum = 0`).

    «Kecha» ni tanlash arzonroq bo'lardi va aynan o'sha arzonlik
    `as_of = D - 1` sabotajini KO'RINMAS qilardi: ikkala kun ham ochiq
    bo'lganda proyeksiyalar teng chiqadi va sabotaj YASHIL qolardi.
    =========================================================================

    ⚠ Natija HAR DOIM o'tmishda (`CURRENT_DATE - 1` dan katta emas):
      `daily_charges` ning `service_date <= business_date` `CHECK` i
      kelajakdagi kunni rad etardi.
    """
    row = conn.execute(
        "SELECT ((CURRENT_DATE - 1) "
        "- ((EXTRACT(ISODOW FROM (CURRENT_DATE - 1))::int - 2 + 7) % 7))::date"
    ).fetchone()
    assert row is not None, "baza sanani qaytarmadi"
    value: date = row[0]
    assert value.isoweekday() == 2, f"{value} seshanba emas — seed kunni noto'g'ri tanladi"
    return value


def _outbox(conn: Connection[TupleRow], market_id: UUID) -> list[dict[str, Any]]:
    """Bozorning navbat qatorlari — `kind` bo'yicha filtrsiz, TO'LIQ ro'yxat."""
    rows = conn.execute(_OUTBOX_ROWS, (str(market_id),)).fetchall()
    return [
        {
            "kind": row[0],
            "recipient_kind": row[1],
            "vendor_id": row[2],
            "dedupe_key": row[3],
            "payload": row[4],
        }
        for row in rows
    ]


def _one(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """AYNAN BITTA qator — ikkitasi idempotentlikning buzilishi bo'lardi."""
    found = [row for row in rows if row["kind"] == kind]
    assert len(found) == 1, f"`{kind}` uchun {len(found)} qator topildi, kutilgani 1"
    return found[0]


def _charge_sum(conn: Connection[TupleRow], market_id: UUID, day: date) -> int:
    row = conn.execute(_CHARGE_SUM, (str(market_id), day)).fetchone()
    assert row is not None
    return int(row[0])


def _charge_count(conn: Connection[TupleRow], market_id: UUID, day: date) -> int:
    row = conn.execute(_CHARGE_COUNT, (str(market_id), day)).fetchone()
    assert row is not None
    return int(row[0])


def _vendor_name(conn: Connection[TupleRow], vendor_id: UUID) -> str:
    row = conn.execute(_VENDOR_NAME, (str(vendor_id),)).fetchone()
    assert row is not None, "sotuvchi topilmadi — nazorat bandi bajarilmadi"
    return str(row[0])


def _unpaid_case_count(conn: Connection[TupleRow], market_id: UUID, vendor_id: UUID) -> int:
    row = conn.execute(_UNPAID_CASES, (str(market_id), str(vendor_id))).fetchone()
    assert row is not None
    return int(row[0])


_SET_DUE = "UPDATE notification_outbox SET next_attempt_at = %s WHERE market_id = %s AND kind = %s"


def _set_due(conn: Connection[TupleRow], *, market_id: UUID, kind: str, moment: datetime) -> None:
    """Navbat qatorining MUDDATINI aniq paytga qadaydi — devor soatidan ajratadi.

    =========================================================================
    ⛔ NEGA KERAK: `enqueue()` `next_attempt_at` ni `server_default` dan
       (`now()`) oladi, ya'ni JOB YOZGAN qatorning muddati HAQIQIY server
       soatiga bog'lanadi. Quiet-hours o'lchovi esa `claim(now=22:30)` ni
       chaqiradi — mahalliy vaqt 22:30 dan keyin yugurgan test uchun
       `o.next_attempt_at <= :now` YOLG'ON bo'lardi va «eslatma olinmadi»
       da'vosi quiet oynani emas, MUDDATNI o'lchagan bo'lardi (bo'sh-rost).

    ⚠ BU MAHSULOT YO'LINI CHETLAB O'TMAYDI: qatorni baribir JOB yozgan
      (uning `dedupe_key` i, `payload` i va `kind` i mahsulotniki).
      Faqat muddat — bu testning PREDMETI BO'LMAGAN o'lchov —
      determinlashtiriladi.
    =========================================================================
    """
    conn.execute(_SET_DUE, (moment, str(market_id), kind))


def _wall(day: date, moment: time) -> datetime:
    """Bozorning DEVOR-SOATI — `Asia/Tashkent`, UTC EMAS.

    Quiet-hours darvozasi `(:now AT TIME ZONE m.timezone)::time` bilan
    baholanadi, ya'ni argument tz-aware bo'lishi SHART: naiv qiymat
    oynani besh soatga siljitardi va 22:30 testi 17:30 ni o'lchagan
    bo'lardi.
    """
    return datetime.combine(day, moment, tzinfo=_TASHKENT)


def _break_market(
    conn: Connection[TupleRow], *, market_id: UUID, charge_id: UUID, amount_soum: int
) -> None:
    """Bir bozorning ma'lumotini BUZADI — hisobdan SAL katta `decrease`.

    Natijada o'sha kunning qoldig'i manfiy bo'ladi va
    `allocate_charge_credit()` uni `ValueError` bilan rad etadi, ya'ni
    `overdue_vendors()` shu bozorda yiqiladi.

    ⛔ TUZATISH `amount_soum + 5 000`, `amount_soum * 3` EMAS VA BU FARQ
       O'LCHANGAN: uch baravar tuzatish sotuvchining UMUMIY qoldig'ini
       ham manfiy qilardi, o'shanda u qarzdorlar ro'yxatiga UMUMAN
       kirmasdi va NOSOZLIK TUG'ILMASDI — job «xatosiz» yakunlanardi va
       test mangu qizil bo'lardi (07-07 ning aynan darsi).
    """
    conn.execute(_SET_MARKET_GUC, (str(market_id),))
    try:
        conn.execute(
            _INSERT_ADJUSTMENT,
            (
                str(uuid4()),
                str(market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.DIRECTOR_WAIVER.value,
                amount_soum + 5_000,
                None,
            ),
        )
    finally:
        conn.execute(_SET_MARKET_GUC, ("",))


# ===========================================================================
# 1. ⛔ FAZANING ENG MUHIM O'LCHOVI — IKKI MANBANING TENGSIZLIGI
# ===========================================================================


async def test_evening_reads_projection_and_morning_reads_ledger(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ Kechki xabar PROYEKSIYADAN, ertalabkisi YOZILGAN hisobdan (D-15/D-16).

    =======================================================================
    ⛔⛔ IKKI SON BIR XIL EMAS VA BU NUQSON EMAS, KUTILGAN FARQ.

    Mexanik sabab: kunlik hisob D+1 ning 04:10 da tug'iladi, ya'ni
    kechqurun `daily_charges` da D kuni HALI YO'Q. Test aynan shu
    holatni quradi: 1-fazada jadval BO'SH (nazorat bandi), 2-fazada
    hisob yoziladi va ikkinchi dayjest UNI o'qiydi.
    =======================================================================

    ⚠ 2-FAZADA `billing_close(D)` O'RNIGA HISOB TO'G'RIDAN-TO'G'RI
      SEED QILINADI VA BU ONGLI CHETLANISH. `billing_close(D)`
      o'tmishdagi kun uchun `stall_slot_occupancy` qatorlarini talab
      qiladi va ularni qurish `test_billing_close.py::PastDay` ning
      butun mashinasini bu faylga KO'CHIRARDI — o'sha job esa AYNAN
      o'sha faylda 20+ test bilan o'lchangan. Bu yerda o'lchanayotgan
      da'vo boshqa: `digest_morning` QAYSI MANBADAN o'qiydi. Hisobni
      KIM yozgani (job yoki seed) bu da'voga umuman ta'sir qilmaydi va
      1-fazadagi nazorat asserti «yozilgan hisob» holatini testning
      O'ZI yaratganini KO'RSATIB turadi.
    """
    day = _recent_open_day(sync_owner_conn)

    # --- 1-FAZA: hisob HALI YO'Q (nazorat bandi) --------------------------
    assert _charge_count(sync_owner_conn, notify.market_id, day) == 0, (
        "seed `daily_charges` ga qator yozib qo'ygan — «billing_close hali "
        "yugurmagan» holati ifodalanmagan va D-15 ni o'lchab bo'lmasdi"
    )

    async with tenant_session(notify.market_id) as session:
        projected = await pending_projection(session, market_id=notify.market_id, as_of=day)
    assert projected.market is not None, "bozor kesimi qaytmadi — proyeksiya kontrakti buzilgan"
    expected_soum = projected.market.pending_amount_soum
    assert expected_soum > 0, (
        f"{day} kuni uchun kutilayotgan patta 0 — seed tarifsiz yoki bozor yopiq. "
        "Bu holatda ikki manbaning tengsizligi HECH QACHON ko'rinmasdi."
    )

    evening = await digest_evening(app_sessionmaker, as_of=day)
    assert evening.errors == [], f"kechki dayjest xato berdi: {evening.errors}"
    evening_row = _one(_outbox(sync_owner_conn, notify.market_id), _EVENING)

    # (a) ⛔ TENGLIK, «yaqin» emas.
    assert evening_row["payload"]["expected_soum"] == expected_soum, (
        "kechki xabarning soni `pending_projection()` natijasidan FARQ QILDI — "
        "ya'ni jobda ikkinchi proyeksiya implementatsiyasi paydo bo'lgan"
    )
    assert evening.charges == 0, (
        "kechki dayjest `daily_charges` da qator ko'rdi — D-15 ning butun "
        "mexanikasi buzilgan (hisob D+1 da tug'ilishi kerak)"
    )

    # --- 2-FAZA: hisob YOZILDI --------------------------------------------
    # ⛔ Summa `TARIFF_SOUM` dan FARQLI: teng bo'lsa (c) bandi tasodifan
    #   yashil bo'lardi va u ikki manbani emas, ikki songa tayinlangan
    #   qiymatni o'lchagan bo'lardi.
    charged_amount = TARIFF_SOUM + 7_000
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        amount_soum=charged_amount,
        service_date=day,
    )
    ledger_sum = _charge_sum(sync_owner_conn, notify.market_id, day)
    assert ledger_sum == charged_amount, "seed hisobni yozmadi"

    morning = await digest_morning(app_sessionmaker, business_date=day)
    assert morning.errors == [], f"ertalabki dayjest xato berdi: {morning.errors}"
    morning_row = _one(_outbox(sync_owner_conn, notify.market_id), _MORNING)

    # (b) ⛔ TENGLIK — yozilgan hisobning yig'indisi bilan.
    assert morning_row["payload"]["charged_soum"] == ledger_sum, (
        "ertalabki dayjestning soni `daily_charges` yig'indisidan FARQ QILDI"
    )

    # (c) ⛔ IKKI SON BIR XIL EMAS — VA BU KUTILGAN FARQ.
    assert morning_row["payload"]["charged_soum"] != evening_row["payload"]["expected_soum"], (
        "ikki dayjestning soni TENG chiqdi. Bu darvoza nuqsonni emas, "
        "SEEDNI o'lchaydi: ikki manba ajratilmagan bo'lsa D-15 ning butun "
        "mazmuni (va §12.2 sifatlovchi kontrakti) o'lchanmay qolardi"
    )


async def test_the_two_digests_name_their_difference_in_the_payload(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ TO'PLAM TENGLIGI — G-35 ning `payload` qatlamidagi yarmi.

    =======================================================================
    ⛔ IKKINCHISINING YO'QLIGI HAM O'LCHANADI.

    `07-UI-SPEC.md` §16.6 G-35: har xabar uchun topilgan sifatlovchilar
    to'plami AYNAN BITTAGA teng bo'lishi shart. Oddiy «bormi?» tekshiruvi
    kechki payloadga `charged_soum` HAM qo'shilganda yashil qolardi — va
    aynan o'sha aralashuv direktorni chalkashtiradi (§1.2 ssenariysi).

    ⚠ MATN yarmi (uchala locale, `recon.qualifier.*`) 07-09 ning
      `_build_text` i ustida o'lchanadi — modul docstringining oxirgi
      bandiga qarang.
    =======================================================================
    """
    day = _recent_open_day(sync_owner_conn)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )

    await digest_evening(app_sessionmaker, as_of=day)
    await digest_morning(app_sessionmaker, business_date=day)
    rows = _outbox(sync_owner_conn, notify.market_id)

    evening_keys = _QUALIFIER_KEYS & set(_one(rows, _EVENING)["payload"])
    morning_keys = _QUALIFIER_KEYS & set(_one(rows, _MORNING)["payload"])

    assert evening_keys == {"expected_soum"}, (
        f"kechki payloadda topilgan sifatlovchilar {sorted(evening_keys)}, "
        "kutilgani AYNAN {'expected_soum'}"
    )
    assert morning_keys == {"charged_soum"}, (
        f"ertalabki payloadda topilgan sifatlovchilar {sorted(morning_keys)}, "
        "kutilgani AYNAN {'charged_soum'}"
    )
    assert _one(rows, _EVENING)["dedupe_key"] != _one(rows, _MORNING)["dedupe_key"]


async def test_evening_case_count_comes_from_the_previous_day(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔⛔ WR-02 — STRUKTURAVIY NOL O'RNIGA O'LCHANGAN SON.

    =======================================================================
    ⛔ NUQSONNING MEXANIKASI: `list_cases(day=...)` `service_date = :day`
       bo'yicha filtrlaydi, BUGUNGI `service_date` li case esa faqat
       ERTAGA 04:25 da (`RECON_OPEN_CRON`) tug'iladi. Ya'ni 20:45 dagi
       so'rov har kuni, ISTISNOSIZ `0` qaytarardi va direktor
       «nomuvofiqlik yo'q» degan YOLG'ON xulosani ko'rardi.

    ⛔ SEED IKKI SONNI ATAYIN FARQLI QILADI (kecha 2, bugun 1) VA BU
       NAZORAT BANDINING O'ZI. «Bugun 0» bilan qurilgan seed ham eski
       kodni qizartirardi, lekin u YANA BIR nosozlikni o'tkazib
       yuborardi: sanoq umuman ishlamay qolib HAR DOIM `0` qaytarsa,
       o'sha seedda ham `0 != 2` bo'lib test qizarardi va sabab
       noaniq qolardi. Ikki FARQLI musbat son esa «qaysi kun o'qilyapti?»
       degan savolga BIR QIYMATLI javob beradi: `2` -> kecha, `1` ->
       bugun, `0` -> umuman o'qilmadi.
    =======================================================================
    """
    day = _recent_open_day(sync_owner_conn)
    yesterday = day - timedelta(days=1)

    # ⚠ HAR CASE O'Z RASTASIDA: `daily_charges` bitta rasta uchun bir kunda
    #   BITTA qator saqlaydi, ya'ni ikkala kechagi case'ni bir rastaga
    #   yozish seedning O'ZINI yiqitardi.
    for stall_id in (notify.stall_ids[0], notify.stall_ids[1]):
        charge_id, _ = add_daily_charge(
            sync_owner_conn,
            market_id=notify.market_id,
            stall_id=stall_id,
            vendor_id=notify.vendor_id,
            tariff_id=notify.tariff_id,
            service_date=yesterday,
        )
        seed_case(
            sync_owner_conn,
            market_id=notify.market_id,
            service_date=yesterday,
            charge_id=charge_id,
        )

    today_charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )
    seed_case(
        sync_owner_conn,
        market_id=notify.market_id,
        service_date=day,
        charge_id=today_charge_id,
    )

    result = await digest_evening(app_sessionmaker, as_of=day)
    assert result.errors == [], f"kechki dayjest xato berdi: {result.errors}"
    payload = _one(_outbox(sync_owner_conn, notify.market_id), _EVENING)["payload"]

    assert payload["prev_day_case_count"] == 2, (
        f"kechki xabar {payload.get('prev_day_case_count')} ta nomuvofiqlik "
        "ko'rsatdi, kutilgani 2 (KECHAGI kun). `1` chiqsa job hamon BUGUNGI "
        "kunni o'qiyapti, `0` chiqsa sanoq umuman ishlamayapti"
    )
    assert "anomaly_count" not in payload, (
        "eski `anomaly_count` kaliti payloadda qoldi — u strukturaviy ravishda "
        "HAR DOIM `0` edi va uning yashab qolishi ikki nomni bir vaqtda "
        "qonuniy qilardi"
    )


async def test_the_evening_payload_rejects_the_old_anomaly_key() -> None:
    """⛔ ALLOWLIST ESKI NOMNI RAD ETADI — WR-02 ning ikkinchi yarmi.

    ⚠ Bu `test_evening_case_count_comes_from_the_previous_day` ning
      TAKRORI EMAS, BOSHQA QATLAM: yuqoridagi test JOB nima yozishini
      o'lchaydi, bu esa REYESTRNING chegarasini. Eski nom allowlistda
      qolganda job to'g'ri ishlab tursa ham, «bugungi kunni sanaydigan»
      yangi chaqiruvchi darvozadan JIMGINA o'tib ketardi.
    """
    with pytest.raises(ValueError, match="anomaly_count"):
        notification_meta.outbox_payload(
            _EVENING,
            business_date="2026-08-13",
            expected_soum=1,
            collected_soum=0,
            unpaid_stall_count=0,
            anomaly_count=0,
        )

    allowed = notification_meta.NOTIFICATION_META[_EVENING].payload_keys
    assert "prev_day_case_count" in allowed and "anomaly_count" not in allowed, (
        f"kechki payload allowlisti kutilmagan holatda: {sorted(allowed)}"
    )


async def test_morning_digest_carries_no_vendor_name(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ TOP-10 QARZDORNING ISMI CHEGARADAN CHIQMAYDI (D-01/D-05).

    ⚠ NAZORAT BANDI: ism BAZADA mavjudligi OLDIN isbotlanadi. Usiz
      «topilmadi» da'vosi BO'SH ROST bo'lardi — sotuvchi umuman
      yozilmagan bo'lsa ham test yashil qolardi (Pitfall 10).
    """
    day = _recent_open_day(sync_owner_conn)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )
    name = _vendor_name(sync_owner_conn, notify.vendor_id)
    assert name.strip(), "sotuvchining ismi bo'sh — nazorat bandi bajarilmadi"

    await digest_morning(app_sessionmaker, business_date=day)
    row = _one(_outbox(sync_owner_conn, notify.market_id), _MORNING)

    serialized = json.dumps(row["payload"], ensure_ascii=False)
    assert name not in serialized, (
        f"sotuvchining ismi `payload` ga tushdi: {serialized}. Chegara YOZISH "
        "paytida qo'yiladi — qator `pg_dump` -> restic -> TASHQI BUCKET "
        "zanjiriga kiradi va matn Telegram serverlariga chiqadi (D-01)"
    )
    assert str(notify.vendor_id) not in serialized, (
        "sotuvchining identifikatori direktorning payloadiga tushdi (D-05)"
    )
    assert row["payload"]["top_debtor_count"] >= 1, (
        "qarzdor sanog'i 0 — seedda to'lanmagan hisob bor, ya'ni bu son "
        "«ism yo'q» da'vosini BO'SH ROST qilib qo'yardi"
    )


# ===========================================================================
# 2. BOT-03 — BOZOR KESIMIDAGI KNOB VA QUIET HOURS
# ===========================================================================


def _seed_overdue_vendor(
    conn: Connection[TupleRow], notify: Env, *, days: int
) -> tuple[UUID, UUID]:
    """Ikkala bozorda ham `bugun - days` kunlik TO'LANMAGAN hisob.

    Returns:
        `(A bozoridagi charge_id, B bozoridagi charge_id)`.
    """
    day = _days_ago(conn, days)
    charge_a, _ = add_daily_charge(
        conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )
    charge_b, _ = add_daily_charge(
        conn,
        market_id=notify.market_b_id,
        stall_id=notify.stall_b_ids[0],
        vendor_id=notify.vendor_b_id,
        tariff_id=notify.tariff_b_id,
        service_date=day,
    )
    return charge_a, charge_b


async def test_overdue_reminder_respects_market_settings(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ D-19 — chegara BOZOR KESIMIDA va u yagona haqiqiy isbot.

    Bir bozorda `overdue_days = 3`, ikkinchisida `10`; ikkalasida ham
    `bugun - 5` kunlik to'lanmagan hisob. Bitta bozorli test bu farqni
    HECH QACHON ko'rmasdi.
    """
    _seed_overdue_vendor(sync_owner_conn, notify, days=5)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_id, overdue_days=3)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_b_id, overdue_days=10)

    result = await overdue_reminder(app_sessionmaker, business_date=_today(sync_owner_conn))
    assert result.errors == [], f"eslatma jobi xato berdi: {result.errors}"
    assert result.markets >= 2, "job ikkala bozorga ham yetmadi"

    strict = [row for row in _outbox(sync_owner_conn, notify.market_id) if row["kind"] == _REMINDER]
    lax = [row for row in _outbox(sync_owner_conn, notify.market_b_id) if row["kind"] == _REMINDER]

    assert len(strict) == 1, (
        f"`overdue_days = 3` bo'lgan bozorda {len(strict)} eslatma, kutilgani 1"
    )
    assert lax == [], (
        f"`overdue_days = 10` bo'lgan bozorda {len(lax)} eslatma yozildi — chegara "
        "bozor kesimida ISHLAMAYAPTI va sozlama e'tiborga olinmagan"
    )
    assert strict[0]["payload"]["overdue_days"] == 3
    assert strict[0]["vendor_id"] == notify.vendor_id


def _shell_context(sessionmaker: async_sessionmaker[AsyncSession]) -> Any:
    """`taskiq` `Context` ning ENG KICHIK o'rnini bosuvchisi.

    Ikkala qobiq ham `context.state.sessionmaker` dan boshqa hech nimaga
    tegmaydi (`worker.py` ning «yupqa qobiq» majburiyati), ya'ni bu
    obyekt qobiqning BUTUN kirish yuzasini qamraydi. Haqiqiy
    `TaskiqState` qurish `WORKER_STARTUP` ilmog'ini, u esa to'liq
    `Settings` ni (ombor rekviziti bilan) talab qilardi.
    """
    return SimpleNamespace(state=SimpleNamespace(sessionmaker=sessionmaker))


async def test_overdue_reminder_shares_the_knob_with_case_opening(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⛔ PATTERN 5 — eslatma VA case AYNAN BIR chegaradan o'tadi (D-19).

    Ikki alohida sozlama ajralib ketardi va o'shanda direktor navbatida
    case turgan, sotuvchi esa eslatma OLMAGAN holat tug'ilardi — ya'ni
    sotuvchi OGOHLANTIRILMAGAN qarz uchun nazoratchi navbatiga tushardi.

    =======================================================================
    ⛔⛔ TEST MAHSULOT QOBIQLARIDAN YURITADI — VA AYNAN SHU BAND WR-06 NI
        TUG'DIRGAN EDI.

    Eski shakl ikkala jobga ham QO'LDA bir xil `business_date` uzatardi.
    Mahsulotda esa qobiqlar boshqacha berardi (`recon.open` -> kecha,
    `notify.overdue` -> bugun), ya'ni ikki chegara HAR DOIM bir kunga
    farq qilardi va «AYNI knob, AYNI javob» da'vosi FAQAT testda rost
    bo'lardi. Endi kunni qobiqning O'ZI hisoblaydi va test unga umuman
    tegmaydi.

    ⛔ QO'LDA `business_date` UZATISH BU TESTDA TAQIQLANADI: uzatilgan
       kun ikkala mexanizmni sun'iy ravishda tenglashtiradi va o'lchov
       o'zi tekshirayotgan nosozlikni KO'RMAY qoladi.
    =======================================================================

    ⚠ CHEGARA SPIONI IKKI MODULDA ALOHIDA: `overdue_cutoff` ikkala jobga
      ham NOM bilan import qilingan, ya'ni bitta e'lonni yamash yetmaydi
      — har modulning O'Z bog'lami almashtiriladi va shu bilan «ikkalasi
      ham SHU funksiyani chaqiradimi?» savoli ham o'lchanadi.

    ⚠ TESKARI NAZORAT: `overdue_days = 10` bo'lgan bozorda IKKALASI HAM
      yo'q. Usiz test «ikkalasi ham bor» ni o'lchardi, «ikkalasi ham BIR
      XIL chegaradan o'tadi» ni emas.
    """
    from app import worker

    _seed_overdue_vendor(sync_owner_conn, notify, days=5)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_id, overdue_days=3)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_b_id, overdue_days=10)

    seen: dict[str, list[date]] = {"reminder": [], "case": []}

    def _spy(bucket: str) -> Callable[[date, int], date]:
        def recorder(business_date: date, overdue_days: int) -> date:
            value = overdue_cutoff(business_date, overdue_days)
            seen[bucket].append(value)
            return value

        return recorder

    monkeypatch.setattr(notifications, "overdue_cutoff", _spy("reminder"))
    monkeypatch.setattr(reconciliation, "overdue_cutoff", _spy("case"))

    context = _shell_context(app_sessionmaker)
    await worker.overdue_reminder_task.original_func(context)
    await worker.reconciliation_open_task.original_func(context)

    assert seen["reminder"], (
        "`notify.overdue` qobig'i chegarani UMUMAN hisoblamadi — eslatma "
        "yo'li `overdue_cutoff()` dan o'tmayapti"
    )
    assert seen["case"], (
        "`recon.open` qobig'i chegarani UMUMAN hisoblamadi — case yo'li "
        "`overdue_cutoff()` dan o'tmayapti"
    )
    assert sorted(seen["reminder"]) == sorted(seen["case"]), (
        f"MAHSULOT yo'lida ikki chegara AJRALDI: eslatma={sorted(seen['reminder'])}, "
        f"case={sorted(seen['case'])}. D-19 ning «bir knob» da'vosi qobiqlar "
        "bir xil `business_date` bermaguncha rost bo'la olmaydi (WR-06)."
    )

    reminders_a = [
        row for row in _outbox(sync_owner_conn, notify.market_id) if row["kind"] == _REMINDER
    ]
    reminders_b = [
        row for row in _outbox(sync_owner_conn, notify.market_b_id) if row["kind"] == _REMINDER
    ]
    cases_a = _unpaid_case_count(sync_owner_conn, notify.market_id, notify.vendor_id)
    cases_b = _unpaid_case_count(sync_owner_conn, notify.market_b_id, notify.vendor_b_id)

    assert len(reminders_a) == 1 and cases_a == 1, (
        f"chegarasi 3 bo'lgan bozorda eslatma={len(reminders_a)}, case={cases_a} — "
        "ikkala mexanizm ham AYNI knobdan yurishi kerak edi"
    )
    assert reminders_b == [] and cases_b == 0, (
        f"chegarasi 10 bo'lgan bozorda eslatma={len(reminders_b)}, case={cases_b} — "
        "teskari nazorat buzildi, ya'ni knob umuman o'qilmayapti"
    )


async def test_overdue_reminder_is_held_by_quiet_hours(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ D-18 NING TESKARISI — eslatma USHLANADI, kvitansiya YO'Q.

    ⚠ NAZORAT AYNI OYNADA: o'sha 22:30 da kvitansiya qatori OLINADI.
      Usiz test «22:30 da hech nima olinmaydi» ni o'lchardi va quiet
      oynaning butunlay buzuq bo'lgan holati ham YASHIL bo'lardi — farq
      `kind` da, OYNADA emas.

    =======================================================================
    ⛔⛔ NAZORAT QATORI `enqueue()` BILAN EMAS, ANIQ `next_attempt_at`
       BILAN SEED QILINADI — VA BU DEVOR SOATIGA BOG'LIQLIKNI YOPADI
       (`deferred-items.md` 3-bandi, 07-19 da o'lchangan, 07-21 da
       tuzatilgan).

    `notification_outbox.next_attempt_at` ning `server_default` i —
    `now()`, ya'ni `enqueue()` bilan yozilgan qator HAQIQIY SERVER
    soatidan muddat olardi. Keyingi `claim(now=_wall(today, 22:30))`
    chaqiruvida `_CLAIM_DUE` ning `o.next_attempt_at <= :now` sharti
    mahalliy vaqt 22:30 dan KEYIN yugurgan har qanday yugurishda YOLG'ON
    bo'lardi — qator olinmasdi va nazorat bandi `assert 'payment_receipt'
    in set()` bo'lib qulardi. Ya'ni test kuniga ~1.5 soat (22:30 -> 00:00)
    QIZIL edi va sabab mahsulotda emas, SOATDA edi.

    ⛔ `enqueue()` NING IDEMPOTENTLIGI BU TESTNING PREDMETI EMAS (u
       `test_digests_are_idempotent` va `test_overdue_reminder_is_
       idempotent_per_vendor_and_day` da o'lchanadi), ya'ni mahsulot
       yo'lidan yurishning bu yerda hech qanday qiymati yo'q. Naqsh
       `test_outbox.py` va `test_outbox_repo.py` dagi BARCHA o'lchovlar
       bilan bir xil.
    =======================================================================
    """
    _seed_overdue_vendor(sync_owner_conn, notify, days=5)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_id, overdue_days=3)
    today = _today(sync_owner_conn)
    await overdue_reminder(app_sessionmaker, business_date=today)

    quiet_moment = _wall(today, time(22, 30))
    # ⛔ ESLATMANING MUDDATI HAM QADALADI — usiz «22:30 da eslatma
    #   olinmaydi» da'vosi mahalliy vaqt 22:30 dan keyin BO'SH-ROST
    #   bo'lardi (qator quiet oyna tufayli emas, MUDDATI kelmagani uchun
    #   qolib ketardi) va quiet-hours darvozasi butunlay buzuq holatda
    #   ham test yashil bo'lardi.
    _set_due(sync_owner_conn, market_id=notify.market_id, kind=_REMINDER, moment=quiet_moment)
    seed_outbox_row(
        sync_owner_conn,
        market_id=notify.market_id,
        kind=_RECEIPT,
        recipient_kind=OutboxRecipientKind.VENDOR.value,
        vendor_id=notify.vendor_id,
        payload={"amount_soum": 15_000},
        # ⛔ MUDDAT O'LCHOV PAYTIDAN OLDIN — nazorat qatori 22:30 da DUE
        #   bo'lishi SHART, aks holda «kvitansiya olinadi» da'vosi quiet
        #   oynani emas, muddat arifmetikasini o'lchagan bo'lardi.
        next_attempt_at=quiet_moment - timedelta(hours=1),
    )

    async with tenant_session(notify.market_id) as session:
        quiet = await outbox_repo.claim(
            session,
            market_id=notify.market_id,
            batch_size=10,
            lease_seconds=60,
            now=quiet_moment,
        )
    quiet_kinds = {row.kind for row in quiet}
    assert _RECEIPT in quiet_kinds, (
        "22:30 da kvitansiya OLINMADI — D-18 buzilgan yoki oyna umuman "
        "ishlamayapti; nazorat bandi aynan shu ikki holatni ajratadi"
    )
    assert _REMINDER not in quiet_kinds, (
        "22:30 da qarz eslatmasi olindi — u quiet hours ga BO'YSUNISHI shart "
        "(D-18 ning teskarisi) va bayroq reyestrda `False` bo'lishi kerak"
    )

    async with tenant_session(notify.market_id) as session:
        awake = await outbox_repo.claim(
            session,
            market_id=notify.market_id,
            batch_size=10,
            lease_seconds=60,
            now=_wall(today + timedelta(days=1), time(9, 0)),
        )
    assert _REMINDER in {row.kind for row in awake}, (
        "oynadan TASHQARIDA ham eslatma olinmadi — ya'ni u quiet hours "
        "tufayli emas, boshqa sabab bilan ushlanib qolgan"
    )
    assert notification_meta.NOTIFICATION_META[_REMINDER].never_suppressed is False


# ===========================================================================
# 3. IDEMPOTENTLIK, YURAK URISHI VA NOSOZLIKKA CHIDAMLILIK
# ===========================================================================


async def test_digests_are_idempotent(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ `dedupe_key` DA KUN BOR — qayta yugurish ikkinchi xabar yozmaydi (D-21)."""
    day = _recent_open_day(sync_owner_conn)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )

    first_morning = await digest_morning(app_sessionmaker, business_date=day)
    second_morning = await digest_morning(app_sessionmaker, business_date=day)
    await digest_evening(app_sessionmaker, as_of=day)
    await digest_evening(app_sessionmaker, as_of=day)

    rows = _outbox(sync_owner_conn, notify.market_id)
    assert len([row for row in rows if row["kind"] == _MORNING]) == 1
    assert len([row for row in rows if row["kind"] == _EVENING]) == 1
    assert first_morning.enqueued >= 1, "birinchi yugurish hech nima yozmadi"
    assert second_morning.enqueued == 0 and second_morning.skipped_existing >= 1, (
        "ikkinchi yugurish `enqueued` ni oshirdi — `None` javobi «xabar allaqachon "
        "navbatda» deb O'QILMAYAPTI"
    )


async def test_overdue_reminder_is_idempotent_per_vendor_and_day(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ SOTUVCHI KUNIGA ENG KO'PI BILAN BITTA ESLATMA OLADI (D-22)."""
    _seed_overdue_vendor(sync_owner_conn, notify, days=5)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_id, overdue_days=3)
    today = _today(sync_owner_conn)

    await overdue_reminder(app_sessionmaker, business_date=today)
    second = await overdue_reminder(app_sessionmaker, business_date=today)

    rows = [row for row in _outbox(sync_owner_conn, notify.market_id) if row["kind"] == _REMINDER]
    assert len(rows) == 1, f"bir sotuvchi bir kunda {len(rows)} eslatma oldi, kutilgani 1"
    assert second.skipped_existing >= 1, "takroriylik `skipped_existing` da ko'rinmadi"


async def test_jobs_write_their_heartbeats(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ RO'YXATGA OLINMAGAN CRON JIMGINA O'LADI (D-17) — ⛔ UCH komponent.

    ⚠ 07-21: dayjestlar endi IKKI ALOHIDA qator yozadi (WR-10). Ilgari
      bu tsikl ikkitasini aylanardi va u BITTA `notify_digest` qatorini
      ikki marta ko'rardi.
    """
    day = _recent_open_day(sync_owner_conn)
    await digest_morning(app_sessionmaker, business_date=day)
    await digest_evening(app_sessionmaker, as_of=day)
    await overdue_reminder(app_sessionmaker, business_date=_today(sync_owner_conn))

    for component in (DIGEST_MORNING_COMPONENT, DIGEST_EVENING_COMPONENT, OVERDUE_COMPONENT):
        row = sync_owner_conn.execute(_HEARTBEAT, (component,)).fetchone()
        assert row is not None, (
            f"`{component}` uchun yurak urishi YOZILMAGAN — 07-14 ning "
            "`EXPECTED_COMPONENTS` i uni MANGU `never_seen` da ko'rsatardi"
        )
        assert row[0] is not None, f"`{component}`: `last_seen_at` bo'sh"
        detail = row[1]
        assert all(isinstance(value, int) for value in detail.values()), (
            f"`{component}` ning `detail` ida butun sondan boshqa qiymat bor: {detail}. "
            "`system_heartbeats` GLOBAL jadval — bozor yoki sotuvchi identifikatori "
            "u yerda hamma uchun ko'rinadigan joyda qolardi"
        )


async def test_each_digest_writes_only_its_own_heartbeat(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔⛔ WR-10 — YARIM O'LGAN JUFTLIK BITTA SIGNAL ORTIGA YASHIRINA OLMAYDI.

    =======================================================================
    ⛔ DA'VO IKKI YO'NALISHLI VA IKKINCHI YO'NALISH MAJBURIY.

    Faqat «ertalabkisi o'z qatorini yozdi» tekshirilganda eski xulq
    (ikkala job BITTA `notify_digest` qatorini yangilaydi) HAM yashil
    bo'lardi: nom o'zgargani bilan qator baribir bitta bo'lib qolardi.
    Nuqson aynan IKKINCHISINING YO'QLIGIDA — shuning uchun test
    ertalabki job yugurgandan keyin KECHKI qator YO'Qligini, keyin esa
    teskarisini o'lchaydi.

    Oqibati o'lchangan: bitta qatorda kechkisi ishlab ertalabkisi
    o'lganda yurak urishi HAMON YANGI ko'rinardi va `digest_stale`
    HECH QACHON ko'tarilmasdi (D-20 ning yarim ishlashi).
    =======================================================================
    """
    day = _recent_open_day(sync_owner_conn)
    sync_owner_conn.execute(
        "DELETE FROM system_heartbeats WHERE component = ANY(%s)",
        ([DIGEST_MORNING_COMPONENT, DIGEST_EVENING_COMPONENT],),
    )

    await digest_morning(app_sessionmaker, business_date=day)

    assert sync_owner_conn.execute(_HEARTBEAT, (DIGEST_MORNING_COMPONENT,)).fetchone() is not None
    assert sync_owner_conn.execute(_HEARTBEAT, (DIGEST_EVENING_COMPONENT,)).fetchone() is None, (
        "ertalabki dayjest KECHKI komponentning qatorini ham yangiladi — ikki job "
        "hamon BITTA yurak urishini bo'lishyapti va yarim o'lgan juftlik "
        "kuzatuvda TIRIK ko'rinardi (WR-10)"
    )

    await digest_evening(app_sessionmaker, as_of=day)

    evening_row = sync_owner_conn.execute(_HEARTBEAT, (DIGEST_EVENING_COMPONENT,)).fetchone()
    assert evening_row is not None, "kechki dayjest O'Z komponentini yozmadi"


async def test_one_broken_market_does_not_stop_the_others(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    notify: Env,
) -> None:
    """⛔ Bir bozorning nuqsoni butun navbatni BO'SH qoldirmaydi.

    ⚠ NOSOZLIK HAQIQIY MA'LUMOT HOLATIDAN quriladi (07-07 da o'lchangan):
      hisobning O'ZIDAN katta `decrease` o'sha kunning qoldig'ini manfiy
      qiladi va `allocate_charge_credit()` uni rad etadi. Ikkinchi hisob
      sotuvchining UMUMIY qoldig'ini musbat saqlaydi — usiz u qarzdorlar
      ro'yxatiga umuman kirmasdi va NOSOZLIK TUG'ILMASDI.
    """
    charge_a, _ = _seed_overdue_vendor(sync_owner_conn, notify, days=5)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[1],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=_days_ago(sync_owner_conn, 6),
    )
    _break_market(
        sync_owner_conn, market_id=notify.market_id, charge_id=charge_a, amount_soum=TARIFF_SOUM
    )
    seed_notification_settings(sync_owner_conn, market_id=notify.market_id, overdue_days=3)
    seed_notification_settings(sync_owner_conn, market_id=notify.market_b_id, overdue_days=3)

    result = await overdue_reminder(app_sessionmaker, business_date=_today(sync_owner_conn))

    assert len(result.errors) == 1, f"kutilgani AYNAN bitta xato, olingani {result.errors}"
    assert result.markets >= 2, "job ikkinchi bozorga umuman yetmadi"
    healthy = [
        row for row in _outbox(sync_owner_conn, notify.market_b_id) if row["kind"] == _REMINDER
    ]
    assert len(healthy) == 1, (
        "sog'lom bozor eslatmasiz qoldi — bitta bozorning nuqsoni butun navbatni to'xtatgan"
    )
    assert all(":" in item for item in result.errors), (
        f"xato yozuvi `<hodisa>:<tur>` shaklida emas: {result.errors}"
    )


# ===========================================================================
# 4. `digest_repo` — CHEGARA VA O'LCHOV BIRLIKLARI
# ===========================================================================


async def test_digest_repo_exposes_exactly_four_functions() -> None:
    """⛔ Modulning ommaviy FUNKSIYALARI — aynan to'rtta (`headline_repo` naqshi)."""
    public = {
        name
        for name in dir(digest_repo)
        if not name.startswith("_") and inspect.isfunction(getattr(digest_repo, name))
    }
    assert public == {"ledger_day", "occupancy_percent", "overdue_vendors", "top_debtors"}, (
        f"modulning ommaviy funksiyalari o'zgardi: {sorted(public)}. Har bir yangi nom "
        "dayjest sonlariga (va u orqali Telegram matniga) yangi yo'l ochadi"
    )


async def test_top_debtors_and_overdue_vendors_carry_no_identity() -> None:
    """⛔ ISM VA TELEFON MAYDONLARI DATAKLASSDA UMUMAN YO'Q (D-01/D-05).

    ⚠ Darvoza `dataclasses.fields()` ustida, grep ustida EMAS: grep yangi
      nom o'ylab topilganda (`debtor_label`) jimgina yashil qolardi.
    """
    top = {item.name for item in fields(digest_repo.TopDebtors)}
    overdue = {item.name for item in fields(digest_repo.OverdueVendor)}

    assert top == {"count", "outstanding_soum"}, f"`TopDebtors` maydonlari o'zgardi: {sorted(top)}"
    assert overdue == {"vendor_id", "outstanding_soum", "oldest_service_date"}, (
        f"`OverdueVendor` maydonlari o'zgardi: {sorted(overdue)}"
    )
    assert not {"vendor_name", "phone", "phone_e164", "full_name"} & (top | overdue)


async def test_occupancy_percent_is_none_when_no_stall_was_measured(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    notify: Env,
) -> None:
    """⛔ MAXRAJ NOL -> `None`, `0` EMAS (05-14 ning darsi).

    «Rasta yo'q» bilan «hech biri band emas» bir xil ko'rinsa, direktor
    kadr olinmagan kunni «hammasi bo'sh» deb o'qirdi.
    """
    day = _recent_open_day(sync_owner_conn)
    async with tenant_session(notify.market_id) as session:
        measured = await digest_repo.occupancy_percent(
            session, market_id=notify.market_id, business_date=day
        )
    assert measured is None, (
        f"materializatsiya qilinmagan kun uchun {measured} qaytdi — o'lchanmagan "
        "holat O'LCHANGAN nol bo'lib ko'rinardi"
    )


async def test_ledger_day_collected_equals_the_signed_payment_sum(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    notify: Env,
) -> None:
    """⛔ `collected_soum` `headline_repo` NING BELGILI YIG'INDISI BILAN `==`.

    Ikki ifoda yozilganda direktorning ertalabki xabari bilan bosh
    ekrandagi «bugungi tushum» bir kun ajralardi va IKKALASI HAM xatosiz
    ko'rinardi.
    """
    day = _recent_open_day(sync_owner_conn)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=day,
    )
    add_payment(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        cashier_id=notify.cashier_id,
        shift_id=notify.shift_id,
        service_date=day,
        # ⚠ `amount_soum == quote_soum`: `ck_payments_override_is_paired`
        #   farqli juftlikda `override_reason` ni TALAB qiladi. Qisman
        #   qoplanish bu yerda KOTIROVKANING kichikligidan keladi, ya'ni
        #   o'lchanayotgan da'vo («hisob to'liq qoplanmagan») o'zgarmaydi.
        amount_soum=TARIFF_SOUM // 3,
        quote_soum=TARIFF_SOUM // 3,
    )

    async with tenant_session(notify.market_id) as session:
        ledger = await digest_repo.ledger_day(
            session, market_id=notify.market_id, business_date=day
        )
        headline = await revenue_today_soum(session, market_id=notify.market_id, business_date=day)

    assert ledger.collected_soum == headline, (
        "dayjestning to'lov yig'indisi bosh ekranникidan farq qildi — ikkinchi "
        "belgili ifoda paydo bo'lgan"
    )
    assert ledger.charge_count == 1
    assert ledger.unpaid_stall_count == 1, (
        "qisman to'langan rasta «to'lanmagan» deb sanalmadi — taqqoslash "
        "QAT'IY KICHIK bo'lishi shart"
    )
    assert ledger.paid_stall_count == 1


async def test_overdue_vendors_uses_the_same_cutoff_as_case_opening(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    notify: Env,
) -> None:
    """⛔ CHEGARADAGI KUN — `<=`, `<` EMAS (Pattern 5 ning mexanikasi).

    `_OVERDUE_CHARGES` `service_date <= cutoff` bilan ishlaydi. Bu yerda
    `<` yozilsa AYNAN chegaradagi kun bir mexanizmda case ochib,
    ikkinchisida eslatma bermasdi — va farq faqat SHU kunda ko'rinardi.
    """
    today = _today(sync_owner_conn)
    boundary = _days_ago(sync_owner_conn, 3)
    add_daily_charge(
        sync_owner_conn,
        market_id=notify.market_id,
        stall_id=notify.stall_ids[0],
        vendor_id=notify.vendor_id,
        tariff_id=notify.tariff_id,
        service_date=boundary,
    )

    async with tenant_session(notify.market_id) as session:
        at_boundary = await digest_repo.overdue_vendors(
            session, market_id=notify.market_id, cutoff=overdue_cutoff(today, 3)
        )
        inside = await digest_repo.overdue_vendors(
            session, market_id=notify.market_id, cutoff=overdue_cutoff(today, 4)
        )

    assert [item.vendor_id for item in at_boundary] == [notify.vendor_id], (
        "chegaradagi kun (`bugun - 3`, `overdue_days = 3`) qamralmadi — taqqoslash "
        "`<` bo'lib qolgan va u `recon.open` niki bilan AJRALGAN"
    )
    assert at_boundary[0].oldest_service_date == boundary
    assert inside == [], "`overdue_days = 4` da ham eslatma chiqdi — chegara umuman qo'llanmayapti"


# ===========================================================================
# 5. D-32 — `DEFAULT_OVERDUE_DAYS` NING YAGONA MANBAI
# ===========================================================================


async def test_default_overdue_days_has_exactly_one_source() -> None:
    """⛔ IKKALA E'LON HAM SXEMADAN HOSILA — nusxa YO'Q (D-32).

    07-06 bu qiymatni literal bilan yozgan, 07-07 esa sxemadan hosila
    qilgan. Merge'dan keyin bazada IKKI MUSTAQIL e'lon qoldi:
    `market_notification_settings.overdue_days` ning `server_default` i
    o'zgargan kuni literal JIMGINA eskirardi va eslatma noto'g'ri kunda
    yonardi, holbuki case to'g'ri kunda ochilardi — ya'ni D-19 ning bir
    knobi IKKIGA bo'linardi.
    """
    from sbozor_core.models.notification import MarketNotificationSettings

    server_default = MarketNotificationSettings.__table__.c.overdue_days.server_default
    text = getattr(getattr(server_default, "arg", None), "text", None)
    assert text is not None, (
        "`overdue_days` ustunida o'qib bo'ladigan `server_default` yo'q — "
        "ikkala modul ham SHU e'londan oziqlanadi (D-32)"
    )
    literal = int(text)

    assert literal == notification_meta.DEFAULT_OVERDUE_DAYS
    assert literal == reconciliation.DEFAULT_OVERDUE_DAYS
    assert notification_meta.DEFAULT_OVERDUE_DAYS == reconciliation.DEFAULT_OVERDUE_DAYS


async def test_default_overdue_days_is_never_a_bare_literal_again() -> None:
    """⛔ QIYMAT HISOBLANADI, YOZILMAYDI — AST bilan o'lchanadi.

    =======================================================================
    ⛔ QIYMAT TENGLIGI YETMAYDI VA SABAB O'LCHANADIGAN: sxemaning
       standarti BUGUN `3`, ya'ni kimdir literalni QAYTA yozib qo'ysa
       oldingi test HAMON YASHIL qolardi. Bu darvoza esa e'lonning
       SHAKLINI o'qiydi: o'ng tomon CHAQIRUV bo'lishi shart, konstanta
       EMAS.

    ⚠ AST, grep EMAS: grep izohni koddan ajratmaydi va bu fayl
      docstringlarida `= 3` shakli bemalol uchrashi mumkin (03-07 ning
      o'lchangan darsi).
    =======================================================================
    """
    for module in (notification_meta, reconciliation):
        tree = ast.parse(inspect.getsource(module))
        found = [
            node
            for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DEFAULT_OVERDUE_DAYS"
        ]
        assert len(found) == 1, (
            f"{module.__name__}: `DEFAULT_OVERDUE_DAYS` uchun {len(found)} e'lon topildi"
        )
        assert isinstance(found[0].value, ast.Call), (
            f"{module.__name__}: `DEFAULT_OVERDUE_DAYS` LITERAL bilan yozilgan. "
            "Qiymat `market_notification_settings.overdue_days` ning "
            "`server_default` idan HOSILA bo'lishi shart — aks holda ikki "
            "standart jimgina ajralardi (D-32)"
        )


async def test_the_two_digests_do_not_talk_to_telegram() -> None:
    """⛔ JOB MODULIDA JO'NATUVCHI SINF UMUMAN YO'Q (D-08/D-23).

    ⚠ Bu darvoza `_no_outbound_http` fixture'ining JUFTI: fixture XULQNI
      o'lchaydi (chiquvchi so'rov yiqiladi), bu esa STRUKTURANI — modul
      jo'natuvchini import ham qilmaydi, ya'ni keyingi ijrochi uni
      «bir joyda ishlatib qo'yish» yo'liga umuman yeta olmaydi.
    """
    source = inspect.getsource(notifications)
    for forbidden in ("AlertSender", "httpx", "aiohttp"):
        assert forbidden not in source, (
            f"job modulida `{forbidden}` paydo bo'ldi — jo'natish "
            "`notify.outbox_tick` ning ishi va bu modul niyat YOZADI, XOLOS"
        )
