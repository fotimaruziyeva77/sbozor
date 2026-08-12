"""CASH-05 — kvitansiya niyati to'lov bilan ⛔ **AYNAN BIR TRANZAKSIYADA**.

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI — «BIR TRANZAKSIYA» VA U ⛔ **IKKI
    TOMONLAMA** O'LCHANADI.

Bir tomonlama o'lchov («to'lov yozildi -> kvitansiya ham bor») ⛔ **hech
nimani isbotlamaydi**: u `enqueue()` ALOHIDA tranzaksiyada, hatto alohida
sessiyada bajarilgan holatda ham yashil bo'lardi. Da'voni faqat
**TESKARI** yo'nalish qulflaydi — oqim 6.5-QADAMDAN KEYIN yiqitilganda
⛔ **IKKALA** jadval ham bo'sh qolishi shart. Bittasining bo'shligi
yetarli emas: aynan «biri bor, ikkinchisi yo'q» holati bu rejaning butun
mavjudlik sababi.
=============================================================================

=============================================================================
⛔ BU FAYL `tests/integration/test_outbox.py` NI ⛔ **TAHRIR QILMAYDI**.

U 07-09 niki (tik + backoff) va ikkala reja ⛔ **bir to'lqinda** ishlaydi.
D-23 ning ikki yarmi bor: «tik Telegram bilan qanday gaplashadi» — o'sha
faylda; «to'lov marshruti Telegram'ga ⛔ **umuman bormaydi**» — bu yerda.
Ikkinchisi to'lov yo'liga bog'langan, ya'ni uni o'sha faylga qo'shish ikki
rejani bitta faylda to'qnashtirardi.
=============================================================================

=============================================================================
⛔ NAVBAT QATORI ⛔ **MAHSULOT YO'LIDAN** TUG'ILADI, seed'dan EMAS.

Kvitansiya qatorini `seed_outbox_row()` bilan yozib, keyin uni o'lchash
`POST /payments` ning 6.5-QADAMI ⛔ **umuman mavjudmi** degan savolni
bermasdi — testlar mahsulot yo'q holatda ham yashil bo'lardi. Shuning
uchun HAR BIR kvitansiya qatori bu faylda AYNAN `POST /payments` dan
keladi.

⚠ Seed FAQAT **NAZORAT** qatori uchun ishlatiladi (`overdue_reminder`,
  D-18 o'lchovida) — va u ATAYIN boshqa `kind`: nazoratning butun vazifasi
  «quiet oyna HAQIQATAN kuchda» ekanini ko'rsatish.
=============================================================================

⚠ `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` bu
  faylning `payload` da'volari uchun ⛔ **manba EMAS**: u 07-04 ning
  vaqtinchalik nusxasi va reyestrdan (`NOTIFICATION_META`) ALLAQACHON
  ajralib ketgan — unda `paid_at` ham, `cashier_name` ham yo'q. Bu fayl
  kutilgan kalitlarni ⛔ **reyestrdan** oladi (`NOTIFICATION_META
  [payment_receipt].payload_keys`), ya'ni mahsulotning O'Z chegarasidan.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from app.jobs.notification_meta import NOTIFICATION_META
from app.repositories import outbox_repo
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import seed_notification_settings, seed_outbox_row
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import OutboxKind, OutboxRecipientKind, OutboxStatus
from sbozor_core.timeutil import MARKET_TZ

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date, datetime

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

PAYMENTS_URL = "/api/v1/payments"

RECEIPT = OutboxKind.PAYMENT_RECEIPT.value
OVERDUE = OutboxKind.OVERDUE_REMINDER.value

RECEIPT_PAYLOAD_KEYS = NOTIFICATION_META[RECEIPT].payload_keys
"""⛔ KUTILGAN KALITLAR ⛔ **REYESTRDAN**, fixture nusxasidan EMAS.

`tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` — 07-04 ning
VAQTINCHALIK ro'yxati va u reyestrdan allaqachon ajralgan (`paid_at` va
`cashier_name` unda YO'Q). O'sha ro'yxatga tayanish bu faylni **eskirgan
nusxaga** bog'lardi.

⚠ BU TAVTOLOGIYA EMAS: reyestr — `payload` ni QURADIGAN kod emas, unga
  RUXSAT BERADIGAN chegara. Marshrut to'rttadan kamini yozsa (masalan
  `cashier_name` ni umuman bermasa) allowlist ⛔ **jim** qolardi —
  `outbox_payload()` faqat ORTIQCHA kalitni rad etadi, YETISHMAGANINI
  emas. Ya'ni bu tenglik marshrutning haqiqiy chiqishini o'lchaydi.
"""

LEASE = 120
"""Ijara muddati (soniya) — `test_outbox_repo.py` bilan bir xil qiymat."""

QUIET_HOUR = time(22, 30)
"""D-18 ning o'lchov nuqtasi — standart oyna (21:00-08:00) ⛔ **ICHIDA**.

⚠ FAQAT SOAT QOTIRILGAN, SANA EMAS: `next_attempt_at` ni marshrut yozadi
  (`server_default`, ya'ni `now()`) va uni test boshqara olmaydi. Sana
  o'sha qatordan OLINADI — aks holda test kechasi soat 23:00 da yugurganda
  «22:30» O'TMISHDA qolardi va `next_attempt_at <= :now` sharti kvitansiyani
  darvozadan oldin, ⛔ **butunlay boshqa sababdan** chiqarib tashlardi.
"""

TELEGRAM_HOST = "api.telegram.org"
"""D-23 tuzog'ining domeni — `AlertSender` ning YAGONA manzili."""


class Bed:
    """To'lov marshrutini yuritadigan minimal muhit + navbat o'lchovlari.

    ⚠ `test_payments_api.py::Env` NING NUSXASI EMAS, uning ⛔ **kesimi**:
      bu yerda kvota to'plami, storno va smena shoxlari umuman
      o'lchanmaydi. Ikkala fayl ham AYNI seed zanjiridan yuradi
      (`nvr -> snapshot -> occupancy -> billing_domain_before_day_close`),
      ya'ni ular bir xil holatni ko'radi.
    """

    def __init__(
        self,
        billing: BillingDomainSeed,
        base: TwoMarketSeed,
        conn: Connection[TupleRow],
        today: date,
    ) -> None:
        self.billing = billing
        self.base = base
        self.conn = conn
        self.today = today

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    def stall_code(self) -> str:
        """Stsenariy rastasining KODI — ⛔ **BAZADAN**, seed ro'yxatidan emas."""
        stall_id = self.billing.market_a.stall_with_two_occupied_slots
        assert stall_id is not None, "nazorat: seedda `stall_with_two_occupied_slots` yo'q"
        row = self.conn.execute(
            "SELECT code FROM stalls WHERE id = %s", (str(stall_id),)
        ).fetchone()
        assert row is not None, f"nazorat: {stall_id} rastasi bazada yo'q"
        code: str = row[0]
        return code

    def payment_count(self) -> int:
        row = self.conn.execute(
            "SELECT count(*) FROM payments WHERE market_id = %s", (str(self.market_id),)
        ).fetchone()
        assert row is not None
        return int(row[0])

    def outbox(self) -> list[dict[str, Any]]:
        """Bozorning BARCHA navbat qatorlari — yozilish tartibida."""
        rows = self.conn.execute(
            "SELECT id, kind, recipient_kind, vendor_id, dedupe_key, payload, status, "
            "next_attempt_at FROM notification_outbox WHERE market_id = %s "
            "ORDER BY created_at, id",
            (str(self.market_id),),
        ).fetchall()
        return [
            {
                "id": row[0],
                "kind": row[1],
                "recipient_kind": row[2],
                "vendor_id": row[3],
                "dedupe_key": row[4],
                "payload": row[5],
                "status": row[6],
                "next_attempt_at": row[7],
            }
            for row in rows
        ]

    def receipts(self) -> list[dict[str, Any]]:
        return [row for row in self.outbox() if row["kind"] == RECEIPT]

    def quiet_window(self) -> tuple[time, time]:
        """Bozorning HAQIQIY quiet oynasi — ⛔ **BAZADAN O'QILADI**.

        ⛔ TESTNING SHARTI TAXMIN QILINMAYDI: «oyna 21:00-08:00» da'vosi
           `server_default` dan keladi va u o'zgarsa bu faylning D-18
           o'lchovi ⛔ **boshqa savolni** o'lchay boshlardi (22:30 oynadan
           tashqarida qolib, test darvozasiz ham yashil bo'lardi).
        """
        row = self.conn.execute(
            "SELECT quiet_hours_start, quiet_hours_end FROM market_notification_settings "
            "WHERE market_id = %s",
            (str(self.market_id),),
        ).fetchone()
        assert row is not None, "nazorat: sozlama qatori yozilmagan"
        return (row[0], row[1])


@pytest.fixture
def bed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
) -> Iterator[Bed]:
    """Seed + BUGUNGI kun uchun `is_open = true` istisnosi + KAFOLATLANGAN tozalash.

    ⛔ BUGUNGI KUN KALENDAR ISTISNOSI BILAN QULFLANADI: A bozori DUSHANBA
       yopiq (`A_OPEN_WEEKDAYS` = ISO 2..7) va istisnosiz bu faylning
       hamma testi ⛔ **haftada bir kun** 422 olardi — sabab esa test
       matnida ko'rinmasdi (`test_payments_api.py::env` naqshi).

    ⛔ `notification_outbox` TOZALASH ⛔ **MAJBURIY VA U YANGI**: 6.5-QADAM
       tufayli HTTP orqali yozilgan har bir to'lov endi navbat qatori ham
       qoldiradi. `fk_notification_outbox_vendor` da `ondelete` YO'Q
       (NO ACTION), ya'ni qoldiq qator sotuvchilar va bozorlar
       o'chirilishini ⛔ **FK buzilishi** bilan yiqitardi — nosozlik bu
       testda emas, KEYINGI faylning seed'ida ko'rinardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        market_id = billing.market_a.market_id
        exception_id = uuid4()
        sync_owner_conn.execute(
            "INSERT INTO market_calendar_exceptions "
            "(id, market_id, exception_date, is_open, note) VALUES (%s, %s, %s, %s, %s)",
            (str(exception_id), str(market_id), market_today, True, "07-12 test — bugun ochiq"),
        )
        try:
            yield Bed(billing, two_markets, sync_owner_conn, market_today)
        finally:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (str(market_id),)
            )
            sync_owner_conn.execute(
                "DELETE FROM market_notification_settings WHERE market_id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (str(market_id),))
            sync_owner_conn.execute(
                "DELETE FROM daily_charges WHERE market_id = %s", (str(market_id),)
            )
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute(
                "DELETE FROM market_calendar_exceptions WHERE id = %s", (str(exception_id),)
            )


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, bed: Bed) -> dict[str, str]:
    """KASSIR sessiyasi — `payment_create` D-07 matritsasida FAQAT unda (§5.6)."""
    return await session_headers(api_client, bed.base.market_a.cashier_phone, SEED_PASSWORD)


def _body(
    *,
    stall_code: str,
    amount_soum: int,
    key: str | None = None,
    reason_code: str | None = None,
) -> dict[str, Any]:
    """`POST /payments` tanasi — `test_payments_api.py::_body` bilan bir shakl."""
    payload: dict[str, Any] = {
        "idempotency_key": key or f"receipt-{uuid.uuid4()}",
        "stall_code": stall_code,
        "method": "cash",
        "amount_soum": amount_soum,
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    return payload


async def _post(
    client: httpx.AsyncClient, headers: dict[str, str], payload: dict[str, Any]
) -> httpx.Response:
    return await client.post(PAYMENTS_URL, json=payload, headers=headers)


class _TransactionSabotage(RuntimeError):
    """6.5-QADAMDAN KEYIN oqimni yiqitadigan SUN'IY nosozlik.

    ⚠ O'Z SINFI ATAYIN: yalang'och `RuntimeError` ni `pytest.raises` bilan
      ushlash `payment_repo` ning Pitfall 3 `RuntimeError` ini ham
      tutardi — test o'shanda «tranzaksiya bir» degan da'voni emas,
      butunlay boshqa nosozlikni o'lchagan bo'lardi va ⛔ **yashil**
      qolardi.
    """


# ===========================================================================
# 1. CASH-05 NING ASOSIY O'LCHOVI — BIR TO'LOV, BIR KVITANSIYA
# ===========================================================================


async def test_receipt_is_enqueued_once_per_payment(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """Bir xil kalit bilan IKKI `POST` -> `payments` **1**, navbat ham ⛔ **1**.

    =======================================================================
    ⛔⛔ IKKINCHI SO'ROV `enqueue()` NI UMUMAN CHAQIRMAYDI (`if created`),
        LEKIN DA'VO BUNGA ⛔ **TAYANMAYDI**.

    `dedupe_key` takror so'rovda ham AYNAN o'sha (`receipt:{payment_id}` —
    D-21 tufayli `payment_id` o'zgarmaydi), ya'ni ilova sharti olib
    tashlansa ham `uq_notification_outbox_market_id_dedupe_key` ikkinchi
    qatorni ⛔ **cheklov darajasida** rad etadi. Bu 6-fazaning T-06-49
    bilan aynan bir sinf.

    ⚠ SABOTAJ AYNAN SHU YERDA O'LCHANDI (SUMMARY): `dedupe_key` dagi
      `payment_id` `uuid4()` bilan almashtirilganda bu test ⛔ QIZARADI —
      ya'ni u kalitning SHAKLINI o'lchaydi, «qator bormi» ni emas.
    =======================================================================
    """
    code = bed.stall_code()
    payload = _body(stall_code=code, amount_soum=TARIFF_SOUM, key="cash05-bir-xil-kalit")

    first = await _post(api_client, cashier_headers, payload)
    assert first.status_code == 201, first.text

    second = await _post(api_client, cashier_headers, payload)
    assert second.status_code == 200, second.text

    payment_id = first.json()["payment_id"]
    assert second.json()["payment_id"] == payment_id, "takror so'rov BOSHQA to'lovni qaytardi"
    assert bed.payment_count() == 1, "takror so'rov IKKINCHI to'lov qatori yozdi (D-21 buzilgan)"

    receipts = bed.receipts()
    assert len(receipts) == 1, (
        f"bir to'lov uchun {len(receipts)} ta kvitansiya niyati yozildi — sotuvchi bir "
        "to'lovga ikki tasdiq olardi va D-02 ning nizo modeli TESKARI tomonga buzilardi"
    )

    row = receipts[0]
    assert row["dedupe_key"] == f"receipt:{payment_id}", (
        "kalit `payment_id` dan qurilmagan — takror so'rov BOSHQA kalit bergan bo'lardi va "
        "`UNIQUE` cheklov ikkinchi qatorni RAD ETMASDI"
    )
    assert row["recipient_kind"] == OutboxRecipientKind.VENDOR.value
    assert row["vendor_id"] == bed.vendor_id, "kvitansiya BOSHQA sotuvchiga manzillandi"
    assert row["status"] == OutboxStatus.PENDING.value


async def test_the_receipt_payload_carries_exactly_the_registry_keys(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """`payload` kalitlari ⛔ **AYNAN** reyestrdagi to'rttasi — kam ham, ko'p ham emas.

    ⛔ TO'PLAM TENGLIGI, `in` EMAS (03-07 ning o'lchangan darsi): `issubset`
       shakli `cashier_name` UMUMAN yozilmagan holatda ham yashil bo'lardi —
       va aynan o'sha maydon CASH-05 ning «kimga to'ladim?» savoliga javob
       beradi (A8).

    ⚠ `cashier_name` — `PERSONAL_FIELDS` a'zosi (`full_name`) va u
      chegaradan CHIQADI. Bu D-05 ni BUZMAYDI: pastdagi test uning javob
      modeliga QAYTMASLIGINI alohida o'lchaydi.
    """
    code = bed.stall_code()
    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert response.status_code == 201, response.text

    payload = bed.receipts()[0]["payload"]
    assert set(payload) == set(RECEIPT_PAYLOAD_KEYS), (
        f"navbat qatorining kalitlari {sorted(payload)} — reyestr esa "
        f"{sorted(RECEIPT_PAYLOAD_KEYS)} kutadi"
    )
    assert payload["amount_soum"] == TARIFF_SOUM
    assert payload["stall_code"] == code
    assert payload["cashier_name"] == f"{bed.base.market_a.name} kassiri", (
        "kassir ismi seed'dagi qiymat emas — `principal` dan olingan `user_id` boshqa "
        "profilga tushgan bo'lishi mumkin"
    )
    assert isinstance(payload["paid_at"], str) and payload["paid_at"], "`paid_at` bo'sh"


async def test_the_cashier_name_never_reaches_the_http_response(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """⛔ D-05: ism navbat `payload` ida BOR, ⛔ **javobda YO'Q** (T-07-74).

    ⚠ O'LCHOV JAVOB TANASINING ⛔ **XOM MATNI** USTIDA, maydon nomlari
      ustida emas: ism boshqa nom bilan (`collected_by`, `operator`)
      qaytarilsa ham u SHAXSIY ma'lumot bo'lib qolardi va nom ro'yxatiga
      tayangan tekshiruv uni KO'RMASDI.
    """
    code = bed.stall_code()
    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert response.status_code == 201, response.text

    cashier_name = bed.receipts()[0]["payload"]["cashier_name"]
    assert cashier_name, "nazorat: seed kassirga ism yozmagan — quyidagi da'vo bo'sh bo'lardi"
    assert cashier_name not in response.text, (
        f"kassir ismi HTTP javobiga chiqdi ({response.text}) — `PERSONAL_ROUTES` o'sardi "
        "va D-05 ning darvozasi (G7-6) qizarardi"
    )


async def test_two_concurrent_requests_enqueue_one_receipt(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """⛔ **PARALLEL** takror — `asyncio.gather` bilan ikki bir vaqtdagi `POST`.

    =======================================================================
    ⛔⛔ KETMA-KET TEST BU OYNANI ⛔ **UMUMAN OCHMAYDI**.

    Yuqoridagi test ikkinchi so'rovni birinchisi TUGAGANDAN keyin yuboradi,
    ya'ni `if created:` sharti ikkinchi chaqiruvni allaqachon to'sadi va
    `UNIQUE` cheklov ⛔ **hech qachon ishlamaydi**. Faqat parallel juftlik
    `SELECT` bilan `INSERT` orasidagi oynani ochadi — o'shanda ikkala so'rov
    ham `created=True` ko'rishi mumkin va navbatni cheklovdan boshqa hech
    nima ushlab qololmaydi.

    Naqsh `test_payments_api.py::test_two_concurrent_requests_write_one_row_
    and_neither_returns_5xx` (A1 zondi) dan olingan — bu uning navbat yarmi.
    =======================================================================
    """
    code = bed.stall_code()
    payload = _body(stall_code=code, amount_soum=TARIFF_SOUM, key="cash05-parallel-0001")

    first, second = await asyncio.gather(
        _post(api_client, cashier_headers, payload),
        _post(api_client, cashier_headers, payload),
    )

    for response in (first, second):
        assert response.status_code < 500, f"5xx: {response.status_code} — {response.text}"
        assert response.status_code in {200, 201}, response.text

    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert bed.payment_count() == 1, "parallel so'rovlar IKKI to'lov qatori yozdi"

    receipts = bed.receipts()
    assert len(receipts) == 1, (
        f"parallel so'rovlar {len(receipts)} ta kvitansiya yozdi — `UNIQUE (market_id, "
        "dedupe_key)` ishlamadi yoki kalit `payment_id` dan qurilmagan"
    )


# ===========================================================================
# 2. «BIR TRANZAKSIYA» — IKKI TOMONLAMA ISBOT (T-07-72)
# ===========================================================================


async def test_receipt_and_payment_share_one_transaction(
    api_client: httpx.AsyncClient,
    bed: Bed,
    cashier_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oqim 6.5-QADAMDAN ⛔ **KEYIN** yiqitiladi -> ⛔ **IKKALA** jadval ham BO'SH.

    =======================================================================
    ⛔⛔ NAZORAT BANDI TESTNING YURAGI VA USIZ U HECH NIMANI O'LCHAMASDI.

    «Ikkala jadval ham bo'sh» da'vosi so'rov ⛔ **umuman 6.5-QADAMGA
    yetmagan** holatda ham rost bo'lardi: 422 (bo'sh kvota to'plami), 409
    (smena yo'q), 404 (rasta topilmadi) — uchalasida ham ikkala jadval
    bo'sh. Ya'ni sabotaj sinovdan o'tmagan bo'lardi.

    Shuning uchun test IKKI QADAM: (1) sabotaj bilan — ikkalasi ham **0**;
    (2) `monkeypatch.undo()` dan keyin ⛔ **AYNAN O'SHA tana** bilan —
    ikkalasi ham **1**. Ikkinchi qadam so'rovning 6.5-QADAMGA va undan ham
    keyingi 7-QADAMGA HAQIQATAN yetishini isbotlaydi.
    =======================================================================

    ⛔ NISHON — 7-QADAM (`write_app_audit`): u 6.5-QADAMDAN KEYIN turadi,
       ya'ni sabotaj paytida kvitansiya niyati ALLAQACHON yozilgan bo'ladi.
       Undan OLDINGI nuqtani yiqitish «niyat yozilgan edimi?» degan
       savolni umuman bermasdi.

    ⚠ TANA CHETLANISHLI (`reason_code` + kvotadan tashqari summa) VA BU
      MAJBURIY: `write_app_audit()` faqat `created and override_reason is
      not None` shoxida chaqiriladi. Oddiy to'lovda u umuman
      bajarilmasdi va sabotaj ⛔ **jimgina** o'tib ketardi.
    """

    async def _explode(*_args: object, **_kwargs: object) -> None:
        raise _TransactionSabotage("6.5-QADAMDAN KEYINGI sun'iy nosozlik")

    code = bed.stall_code()
    # ⛔ Kvotadan TASHQARIDAGI summa + sabab -> 5-QADAM `quotes[0]` ni tanlaydi
    #    va 7-QADAM auditi ISHLAYDI.
    payload = _body(
        stall_code=code, amount_soum=1_000, key="cash05-sabotaj", reason_code="partial_day"
    )

    monkeypatch.setattr("app.api.v1.payments.write_app_audit", _explode)
    with pytest.raises(_TransactionSabotage):
        await _post(api_client, cashier_headers, payload)

    assert bed.payment_count() == 0, (
        "to'lov qatori QOLDI — tranzaksiya orqaga qaytmadi va bu butun da'voni buzadi"
    )
    assert bed.outbox() == [], (
        "⛔ KVITANSIYA NIYATI QOLDI, TO'LOV ESA YO'Q — `enqueue()` ALOHIDA tranzaksiyada "
        "bajarilgan. Sotuvchi HECH QACHON YOZILMAGAN to'lov uchun kvitansiya olardi va "
        "bu D-02 ning nizo modelini TESKARI tomonga buzardi"
    )

    # ---- NAZORAT: AYNAN O'SHA tana, sabotajsiz -> IKKALASI HAM YOZILADI.
    monkeypatch.undo()
    control = await _post(api_client, cashier_headers, payload)
    assert control.status_code == 201, (
        f"nazorat yiqildi — yuqoridagi so'rov 6.5-QADAMGA UMUMAN yetmagan bo'lishi mumkin: "
        f"{control.text}"
    )
    assert bed.payment_count() == 1
    assert len(bed.receipts()) == 1, "nazorat: sabotajsiz oqimda kvitansiya niyati yozilmadi"


# ===========================================================================
# 3. D-23 — TO'LOV YO'LI TELEGRAM'GA UMUMAN BORMAYDI (T-07-73)
# ===========================================================================


async def test_payment_succeeds_while_telegram_is_down(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """Telegram BUTUNLAY yiqilgan -> `POST /payments` ⛔ **201**, chaqiruvlar ⛔ **0**.

    =======================================================================
    ⛔⛔ DA'VO «YIQILISHGA CHIDADI» EMAS, ⛔ **«UMUMAN TEGMADI»**.

    «Chidadi» shakli (jo'natishga urinib, xatoni yutish) 201 berardi —
    lekin so'rov Telegram ning timeout muddatini KUTARDI va o'sha muddat
    davomida to'lov tranzaksiyasi OCHIQ turardi. Kassirning har bosishi
    internetning holatiga bog'lanardi. Shuning uchun o'lchov
    `route.call_count == 0` — bu ⛔ **kuchliroq** da'vo.
    =======================================================================

    ⛔ NAZORAT BANDI: tuzoq ⛔ **QUROLLANGANLIGI** o'sha `respx` bloki
       ichida isbotlanadi. Usiz `call_count == 0` «respx bu yo'ldagi
       chaqiruvni umuman KO'RA olmaydi» holatida ham yashil bo'lardi —
       ya'ni test o'z uskunasining ko'rligini mahsulotning fazilati deb
       o'qirdi.
    """
    code = bed.stall_code()
    telegram_url = f"{TELEGRAM_API_BASE}/bot1234567890:FAKE/{TELEGRAM_SEND_METHOD}"

    async with respx.mock(assert_all_called=False) as router:
        route = router.route(host=TELEGRAM_HOST).mock(
            side_effect=httpx.ConnectTimeout("telegram BUTUNLAY yiqilgan")
        )

        response = await _post(
            api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
        )

        assert response.status_code == 201, (
            f"⛔ D-23 BUZILDI: Telegram yiqilganda PUL YOZUVI rad etildi ({response.text}). "
            "Bildirishnoma nosozligi kassirni ishdan to'xtatardi"
        )
        assert route.call_count == 0, (
            f"to'lov marshruti Telegram'ga {route.call_count} marta bordi — tarmoq "
            "chaqiruvi to'lov tranzaksiyasini internet muddatiga bog'laydi (D-23)"
        )

        # ---- NAZORAT: tuzoq HAQIQATAN telegram trafigini ushlaydi.
        async with httpx.AsyncClient() as probe:
            with pytest.raises(httpx.ConnectTimeout):
                await probe.post(telegram_url, json={"text": "zond"})
        assert route.call_count == 1, "nazorat: `respx` telegram chaqiruvini UMUMAN ko'rmadi"

    assert bed.payment_count() == 1, "Telegram yiqilganda to'lov qatori yozilmadi"
    assert len(bed.receipts()) == 1, "niyat yozilmadi — jo'natish keyin ham amalga oshmasdi"


# ===========================================================================
# 4. D-18 — QUIET HOURS KVITANSIYANI USHLAB QOLMAYDI (T-07-75)
# ===========================================================================


async def test_quiet_hours_do_not_hold_the_receipt(
    api_client: httpx.AsyncClient,
    bed: Bed,
    cashier_headers: dict[str, str],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
) -> None:
    """22:30 da yozilgan kvitansiya ⛔ **DARHOL OLINADI**; qarz eslatmasi — YO'Q.

    =======================================================================
    ⛔⛔ NAZORAT QATORI (`overdue_reminder`) TESTNING YARMI.

    Kvitansiya olinganini yolg'iz o'lchash quiet-hours darvozasi ⛔
    **UMUMAN YO'Q** bo'lgan holatda ham yashil bo'lardi. Ikkinchi qator
    aynan o'sha bozorda, aynan o'sha vaqtda, aynan o'sha `next_attempt_at`
    bilan turadi va farq FAQAT `kind` da — ya'ni uning OLINMAGANI oynaning
    HAQIQATAN kuchda ekanini isbotlaydi va birinchi da'voni `never_
    suppressed` istisnosiga bog'laydi.

    ⛔ Pitfall 7 aynan shu bandning unutilishini tasvirlaydi: filtr
       yoziladi, `kind` istisnosi esa UNUTILADI — va 21:00 dan keyin
       to'lagan sotuvchi kvitansiyani ERTASI KUNI olardi. Xatosiz,
       jimgina, «to'g'ri ishlagan» so'rov bilan.
    =======================================================================

    ⚠ VAQT SILJITILMAYDI — U ARGUMENT (`claim(..., now=...)`), ya'ni
      `freezegun` va yangi bog'liqlik KERAK EMAS (`test_outbox_repo.py`
      bilan bir xil qaror).
    """
    seed_notification_settings(sync_owner_conn, market_id=bed.market_id)
    start, end = bed.quiet_window()
    assert (start, end) == (time(21, 0), time(8, 0)), (
        f"nazorat: bozorning quiet oynasi {start}-{end} — test 22:30 ni OYNA ICHIDA deb "
        "hisoblaydi va boshqa oyna bilan u butunlay boshqa savolni o'lchagan bo'lardi"
    )

    code = bed.stall_code()
    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert response.status_code == 201, response.text

    receipt = bed.receipts()[0]
    due_at: datetime = receipt["next_attempt_at"]
    quiet_moment = _quiet_moment_after(due_at)

    # ⛔ NAZORAT QATORI — AYNAN o'sha muddat, AYNAN o'sha sotuvchi, FARQ FAQAT `kind`.
    overdue_id = seed_outbox_row(
        sync_owner_conn,
        market_id=bed.market_id,
        kind=OVERDUE,
        vendor_id=bed.vendor_id,
        payload={"overdue_days": 3},
        next_attempt_at=due_at,
    )

    async with tenant_session(bed.market_id) as session:
        claimed = await outbox_repo.claim(
            session,
            market_id=bed.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=quiet_moment,
        )

    claimed_ids = {row.id for row in claimed}
    assert receipt["id"] in claimed_ids, (
        f"⛔ D-18 BUZILDI: {quiet_moment.astimezone(MARKET_TZ):%H:%M} da yozilgan kvitansiya "
        "quiet oyna ichida USHLAB QOLINDI. Sotuvchi hozirgina to'lagan pulining tasdig'ini "
        "ERTAGA olardi va nizo modelining (D-02) butun asosi yo'qolardi"
    )
    assert overdue_id not in claimed_ids, (
        "qarz eslatmasi quiet oyna ichida OLINDI — nazorat bandi qulab tushdi, ya'ni "
        "yuqoridagi da'vo «darvoza umuman yo'q» holatida ham yashil bo'lardi"
    )


def _quiet_moment_after(due_at: datetime) -> datetime:
    """`due_at` dan KEYINGI eng yaqin 22:30 (Toshkent devor-soati).

    ⛔ SANA QOTIRILMAYDI: `next_attempt_at` ni marshrut yozadi (`now()`) va
       test uni boshqara olmaydi. Qotirilgan sana yarim tundan keyin
       yugurgan to'plamni `next_attempt_at <= :now` sharti bilan — ya'ni
       quiet-hours darvozasiga UMUMAN yetmasdan — qizartirardi.
    """
    local = due_at.astimezone(MARKET_TZ)
    moment = local.replace(hour=QUIET_HOUR.hour, minute=QUIET_HOUR.minute, second=0, microsecond=0)
    if moment < local:
        moment += timedelta(days=1)
    return moment


# ===========================================================================
# 5. STORNO KVITANSIYA YOZMAYDI — ONGLI RAD ETISH
# ===========================================================================


async def test_a_reversal_writes_no_receipt(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """`POST /payments/{id}/reverse` -> navbatda YANGI qator ⛔ **YO'Q**.

    ⛔ BU «HALI QURILMAGAN» EMAS, ⛔ **ONGLI RAD ETISH**: CASH-05 «to'lov
       kiritilishi bilan» deydi, storno esa TUZATISH va uning xabari
       o'z `OutboxKind` a'zosini, o'z matnini va o'z allowlistini talab
       qiladigan YANGI qobiliyat (07-CONTEXT Deferred Ideas).

    ⚠ O'LCHOV `count(*)` NING ⛔ **O'ZGARMASLIGI** ustida, «0» ustida emas:
      storno o'zidan oldingi to'lovni talab qiladi, ya'ni navbatda BITTA
      (kvitansiya) qator ALLAQACHON bor. «0» kutish testni ifodalab
      bo'lmaydigan qilardi.
    """
    code = bed.stall_code()
    created = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert created.status_code == 201, created.text
    before = len(bed.outbox())
    assert before == 1, "nazorat: to'lovning O'ZI kvitansiya yozmadi — quyidagi da'vo bo'sh"

    payment_id = created.json()["payment_id"]
    reversed_response = await api_client.post(
        f"{PAYMENTS_URL}/{payment_id}/reverse",
        json={"reason_code": "wrong_stall"},
        headers=cashier_headers,
    )
    assert reversed_response.status_code == 201, reversed_response.text

    after = bed.outbox()
    assert len(after) == before, (
        f"storno {len(after) - before} ta yangi navbat qatori yozdi — CASH-05 faqat TO'LOV "
        "kvitansiyasi, storno xabari esa reyestrda MAVJUD BO'LMAGAN `kind` talab qilardi"
    )
    assert bed.payment_count() == 2, "nazorat: storno qatori yozilmagan — test bo'sh yugurdi"
