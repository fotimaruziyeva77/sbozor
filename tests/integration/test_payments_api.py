"""`/api/v1/payments/*` — KASSIRNING YOZUV YUZASI (CASH-01…CASH-03, SC#5).

=============================================================================
⛔⛔ BU FAYLNING UCH ENG QIMMAT DA'VOSI:

  1. **D-21 XULQ BILAN** — takror so'rov (ketma-ket VA parallel) BITTA
     qator yozadi, ikkinchi javob **200** va **O'SHA** `payment_id`;
  2. **422 NING SHARTI — BO'SH KVOTA TO'PLAMI**, «bugungi summa yo'q»
     EMAS: yopiq kunda va tarifsiz toifada eski QARZ undiriladi
     (UI-SPEC §9.4). Bu uch ALOHIDA nomlangan test bilan o'lchanadi va
     eski shartni qaytarish SABOTAJ sifatida sinalgan;
  3. **D-23 — TAHRIRLASH YO'LI UMUMAN YO'Q**: `UPDATE payments` xom SQL
     da ham rad etiladi, `openapi()` da esa `PATCH`/`PUT`/`DELETE`
     METODI YO'Q (to'plam tengligi, `not in` EMAS).

=============================================================================
⛔ BU FAYL `test_billing_repo.py` NI TAKRORLAMAYDI.

Pul arifmetikasi (tarif yechimi, FIFO taqsimlash, qoldiq tengligi) o'sha
yerda; kvota to'plamining O'ZI esa `tests/unit/test_payment_credit_rules.py`
da (jadval testi). Bu yerda faqat HTTP CHEGARASIDAGI da'volar.

=============================================================================
⛔ KUN — `Asia/Tashkent`, `CURRENT_DATE` (UTC) EMAS.

`POST /payments` `business_today()` bilan ishlaydi. Test kunni
`market_today` fixture'idan (`SELECT (now() AT TIME ZONE 'Asia/Tashkent')
::date`) oladi. `CURRENT_DATE` Toshkent 00:00–04:59 oralig'ida BIR KUN
orqada qoladi va o'sha besh soat ichida testlar jimgina qizarardi — bu
nosozlik sinfi post-merge darvozasida ALLAQACHON bir marta o'lchangan.

=============================================================================
⛔ BUGUNGI KUN KALENDAR ISTISNOSI BILAN QULFLANADI (`is_open = true`).

A bozori DUSHANBA yopiq (`A_OPEN_WEEKDAYS` = ISO 2..7). Istisnosiz bu
faylning yarmi HAFTADA BIR KUN qizarardi va sabab test matnida
ko'rinmasdi. `market_is_open()` ning `COALESCE` tartibida istisno HAR
DOIM ustun (D-18), ya'ni bitta qator butun faylni haftaning kunidan
MUSTAQIL qiladi. Yopiq kun testlari o'sha qatorni `is_open = false` ga
o'giradi — ya'ni ikkala shox ham AYNI mexanizm bilan boshqariladi.
=============================================================================
"""

from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.main import app as fastapi_app
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import ShiftStatus

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    import httpx
    from fixtures import MarketScope
    from psycopg import Connection
    from psycopg.rows import TupleRow

PAYMENTS_URL = "/api/v1/payments"
RECENT_URL = "/api/v1/payments/recent"

PAYMENT_KEYS = frozenset(
    {
        "payment_id",
        "stall_code",
        "service_date",
        "amount_soum",
        "kind",
        "method",
        "created_at",
        "reversed",
    }
)
"""UI-SPEC §8.8 ning AYNAN SAKKIZ kaliti.

⛔ RO'YXAT SHU YERDA QO'LDA YOZILGAN VA BU ATAYIN (06-08 da o'rnatilgan
   qoida): u KUTILGAN NATIJA, o'lchov emas. Uni
   `PaymentResponse.model_fields` dan hosila qilish testni «model o'ziga
   teng» degan tavtologiyaga aylantirardi.

⚠ Ikkinchi, MUSTAQIL qatlam pastda: `test_the_payload_matches_the_client_
  schema` bu to'plamni `frontend/src/lib/payment-queries.ts` dagi
  `paymentResponseSchema` bilan solishtiradi, ya'ni til chegarasi ham
  MEXANIK qulflangan.
"""

PERSONAL_FIELDS = frozenset({"vendor_name", "phone", "full_name"})
"""C-10 darvozasining maydonlari — `test_billing_api.py:96` bilan AYNI."""

CLIENT_SCHEMA_PATH = Path("frontend/src/lib/payment-queries.ts")
"""Klient kontraktining manbai — 06-03 da yozilgan va ALLAQACHON merge qilingan."""

_CLIENT_SCHEMA_RE = re.compile(
    r"paymentResponseSchema\s*=\s*z\.strictObject\(\{(?P<body>.*?)\}\)", re.DOTALL
)
_CLIENT_KEY_RE = re.compile(r"^\s*(?P<key>[a-z_][a-z0-9_]*)\s*:", re.MULTILINE)

MATRIX_METHODS = frozenset({"POST", "GET"})
"""`/api/v1/payments*` prefiksida MUMKIN bo'lgan metodlar — D-23.

⛔ `PATCH`/`PUT`/`DELETE` ⛔ **YO'Q** va bu to'plam TENGLIGI bilan
   o'lchanadi (`not in` EMAS): inkor tasdiq faqat sanab o'tilgan nomni
   ushlaydi va to'rtinchi metod jimgina qo'shilardi.
"""


class Env:
    """Billing seed + domen + baza qatlami — `test_billing_api.Env` ning kengaytmasi."""

    def __init__(
        self,
        billing: BillingDomainSeed,
        domain: MarketDomainSeed,
        base: TwoMarketSeed,
        conn: Connection[TupleRow],
        today: date,
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base
        self.conn = conn
        self.today = today

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id: UUID | None = getattr(self.billing.market_a, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id

    def code(self, stall_id: UUID) -> str:
        """Rastaning KODI — BAZADAN, qo'shni faylning ro'yxat tartibidan EMAS."""
        row = self.conn.execute(
            "SELECT code FROM stalls WHERE id = %s", (str(stall_id),)
        ).fetchone()
        assert row is not None, f"nazorat: {stall_id} rastasi bazada yo'q"
        code: str = row[0]
        return code

    def set_market_open(self, *, is_open: bool) -> None:
        """BUGUNGI kunni ochiq/yopiq qiladi — ⛔ AYNI istisno qatori orqali.

        Ikkala shox ham bitta mexanizmdan (`market_calendar_exceptions`)
        yuradi, ya'ni «yopiq kun» testi haftaning kuniga UMUMAN
        bog'lanmaydi (modul docstringi).
        """
        self.conn.execute(
            "UPDATE market_calendar_exceptions SET is_open = %s "
            "WHERE market_id = %s AND exception_date = %s",
            (is_open, str(self.market_id), self.today),
        )

    def add_debt(self, *, stall_id: UUID, vendor_id: UUID, amount_soum: int) -> UUID:
        """ESKI qarz — `service_date` KECHA, ya'ni `vendor_outstanding()` uni SANAYDI.

        ⚠ `vendor_outstanding(as_of=bugun)` hisoblarni `service_date <
          :as_of` bilan cheklaydi (BILL-03): bugungi patta proyeksiyada
          ALOHIDA maydon va uni qoldiqqa ham qo'shish `total_due_soum` ni
          IKKI MARTA sanardi.
        """
        charge_id, _ = add_daily_charge(
            self.conn,
            market_id=self.market_id,
            stall_id=stall_id,
            vendor_id=vendor_id,
            tariff_id=self.billing.market_a.tariff_id,
            amount_soum=amount_soum,
        )
        return charge_id

    def outstanding(self, vendor_id: UUID) -> int:
        """Sotuvchining HISOBLANADIGAN qoldig'i — `_VENDOR_OUTSTANDING` bilan bir xil qoida.

        ⚠ Bu YOZUV EMAS, O'LCHOV: manfiy natija (avans) ATAYIN
          kattalikka aylantirilmaydi (OQ-4/A4).
        """
        row = self.conn.execute(
            "SELECT COALESCE(("
            "  SELECT sum(c.amount_soum) FROM daily_charges c"
            "   WHERE c.market_id = %s AND c.vendor_id = %s AND c.service_date < %s"
            "), 0) - COALESCE(("
            "  SELECT sum(CASE WHEN p.kind = 'reversal' THEN -p.amount_soum "
            "              ELSE p.amount_soum END)"
            "    FROM payments p WHERE p.market_id = %s AND p.vendor_id = %s"
            "), 0)",
            (str(self.market_id), str(vendor_id), self.today, str(self.market_id), str(vendor_id)),
        ).fetchone()
        assert row is not None
        return int(row[0])

    def payments(self) -> list[tuple[Any, ...]]:
        """Bozorning BARCHA to'lov qatorlari — `(id, kind, amount, shift_id, reason)`."""
        return list(
            self.conn.execute(
                "SELECT id, kind, amount_soum, shift_id, reversal_reason, override_reason, "
                "quote_soum, reverses_payment_id "
                "FROM payments WHERE market_id = %s ORDER BY created_at, id",
                (str(self.market_id),),
            ).fetchall()
        )

    def close_the_open_shift(self) -> None:
        """Ochiq smenani O'CHIRADI — `shift_id = NULL` shoxini ochish uchun (OQ-6/A5).

        ⛔ `status = 'closed'` GA O'GIRISH YARAMAYDI: `closed_is_paired` /
           `closed_has_declaration` / `closed_has_system_total` `CHECK`
           lari yopilgan smenadan deklaratsiya VA tizim summasini talab
           qiladi, ya'ni test smenani «yopish» uchun ko'r deklaratsiyani
           O'ZI to'qishga majbur bo'lardi — va o'sha son 06-10 ning
           o'lchovi, bu faylniki emas.

        ⚠ O'CHIRISH UCHUN BOZOR QORALAMAGA QAYTARILADI:
          `shift_declaration_immutable()` `DELETE` ni faqat qoralama
          bozorda ruxsat etadi (`cleanup_billing_domain()` naqshi).
        """
        self.conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(self.market_id),)
        )
        self.conn.execute(
            "DELETE FROM cashier_shifts WHERE market_id = %s AND cashier_id = %s",
            (str(self.market_id), str(self.cashier_id)),
        )
        self.conn.execute(
            "UPDATE markets SET is_active = true WHERE id = %s", (str(self.market_id),)
        )

    def open_a_shift(self) -> UUID:
        """Yangi OCHIQ smena — `close_the_open_shift()` dan KEYIN chaqiriladi.

        ⚠ Ikkinchi ochiq smena `uq_cashier_shifts_..._open` bilan rad
          etilardi (D-27), ya'ni tartib majburiy.
        """
        shift_id = uuid4()
        self.conn.execute(
            "INSERT INTO cashier_shifts (id, market_id, cashier_id, status) "
            "VALUES (%s, %s, %s, %s)",
            (str(shift_id), str(self.market_id), str(self.cashier_id), ShiftStatus.OPEN.value),
        )
        return shift_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
    migrated: None,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed + BUGUNGI kun uchun `is_open = true` istisnosi.

    `day_close` CHAQIRILMAYDI (06-05 da o'rnatilgan qoida): bu faylning
    birorta da'vosi bandlikka tayanmaydi — `POST /payments` `daily_charges`
    ni ham, `stall_slot_occupancy` ni ham O'QIMAYDI, u tarif + biriktirish +
    kalendar + qoldiq ustida ishlaydi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        exception_id = uuid4()
        market_id = billing.market_a.market_id
        sync_owner_conn.execute(
            "INSERT INTO market_calendar_exceptions "
            "(id, market_id, exception_date, is_open, note) VALUES (%s, %s, %s, %s, %s)",
            (str(exception_id), str(market_id), market_today, True, "06-09 test — bugun ochiq"),
        )
        try:
            yield Env(billing, market_domain, two_markets, sync_owner_conn, market_today)
        finally:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            # ⚠ TO'LOVLAR SHU YERDA O'CHIRILADI, `cleanup_billing_domain()`
            #   dan OLDIN: testlar HTTP orqali qator yozadi va seed ularning
            #   identifikatorlarini BILMAYDI. Tozalash `market_id` bo'yicha.
            #
            # ⛔ `notification_outbox` 07-12 DA QO'SHILDI VA U MAJBURIY:
            #    `POST /payments` ning 6.5-QADAMI (CASH-05) har yangi to'lov
            #    uchun kvitansiya niyatini ham yozadi.
            #    `fk_notification_outbox_vendor` da `ondelete` YO'Q
            #    (NO ACTION), ya'ni qoldiq qator `cleanup_market_domain()`
            #    ning sotuvchi/bozor `DELETE` ini FK buzilishi bilan
            #    yiqitardi — va nosozlik BU faylda emas, KEYINGI faylning
            #    seed'ida ko'rinardi.
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (str(market_id),)
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
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """KASSIR sessiyasi — ⛔ `payment_create` D-07 matritsasida FAQAT unda (§5.6)."""
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — `billing_collect_view` BOR, `payment_create` YO'Q."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


def _body(
    *,
    stall_code: str,
    amount_soum: int,
    key: str | None = None,
    reason_code: str | None = None,
    method: str = "cash",
) -> dict[str, Any]:
    """`POST /payments` tanasi — ⛔ `quote_soum` MAYDONI YO'Q (D-20)."""
    payload: dict[str, Any] = {
        "idempotency_key": key or f"test-{uuid.uuid4()}",
        "stall_code": stall_code,
        "method": method,
        "amount_soum": amount_soum,
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    return payload


async def _post(
    client: httpx.AsyncClient, headers: dict[str, str], payload: dict[str, Any]
) -> httpx.Response:
    return await client.post(PAYMENTS_URL, json=payload, headers=headers)


def _outbox_count(env: Env) -> int:
    """Bozordagi kvitansiya niyatlari soni — 07-12 ning regressiya bandi.

    ⚠ BU FAYL CASH-05 NI O'LCHAMAYDI: to'rt xulqiy o'lchov (bir
      tranzaksiya / takror / Telegram yiqilishi / quiet hours)
      `tests/integration/test_receipt_outbox.py` da. Bu yordamchi faqat
      «yangi qadam MAVJUD kafolatni buzmadi» degan bitta da'vo uchun.
    """
    row = env.conn.execute(
        "SELECT count(*) FROM notification_outbox WHERE market_id = %s", (str(env.market_id),)
    ).fetchone()
    assert row is not None
    return int(row[0])


def _detail(response: httpx.Response) -> str:
    """Javobning `detail` KODI — ⛔ SATR (klient `api-client.ts::detailOf()` bilan).

    Lug'at shaklidagi `detail` klientda bo'sh satrga aylanadi va kod
    `errors.generic` ga tushardi, ya'ni bu tekshiruv KLIENT KONTRAKTINI
    ham o'lchaydi.
    """
    body = response.json()
    detail = body.get("detail")
    assert isinstance(detail, str), f"`detail` SATR bo'lishi SHART (klient shartnomasi): {body}"
    return detail


# ===========================================================================
# 1. SC#5(a) — D-21: TAKROR SO'ROV KASSIR UCHUN KO'RINMAS
# ===========================================================================


async def test_the_same_key_twice_writes_one_row_and_returns_the_same_payment(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """SC#5(a): bir xil kalit -> **1 qator**, ikkinchi javob **200** va O'SHA `payment_id`.

    ⛔ IKKINCHI JAVOB **409 EMAS** va bu D-21 ning butun mazmuni: tarmoq
       uzilishida qayta yuborish kassir uchun KO'RINMAS bo'lishi kerak.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    payload = _body(stall_code=code, amount_soum=TARIFF_SOUM, key="sc5a-bir-xil-kalit")

    first = await _post(api_client, cashier_headers, payload)
    assert first.status_code == 201, first.text

    second = await _post(api_client, cashier_headers, payload)
    assert second.status_code == 200, second.text
    assert second.json()["payment_id"] == first.json()["payment_id"]

    assert len(env.payments()) == 1, "takror so'rov IKKINCHI qator yozdi — D-21 buzilgan"
    # ⛔ 07-12 REGRESSIYA BANDI: 6.5-QADAM (CASH-05) MAVJUD kafolatni
    #    buzmagan. Kvitansiya niyati ham AYNAN BITTA — takror so'rov
    #    sotuvchiga ikkinchi tasdiq YUBORMAYDI. To'liq xulqiy o'lchov
    #    `tests/integration/test_receipt_outbox.py` da; bu yerda faqat
    #    o'sha qadam BU testning da'vosini buzmaganini qulflaydi.
    assert _outbox_count(env) == 1, "takror so'rov IKKINCHI kvitansiya niyatini yozdi"


@pytest.mark.parametrize(
    ("label", "pays_the_debt_too"),
    [("qarzni_ham_olish", True), ("faqat_qarz", False)],
)
async def test_a_debt_moving_payment_is_still_idempotent_on_retry(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    label: str,
    pays_the_debt_too: bool,
) -> None:
    """⛔ CR-02: QARZNI SURGAN to'lovni qayta yuborish ham **200** beradi.

    =======================================================================
    ⛔⛔ YUQORIDAGI TEST BU NOSOZLIKNI KO'RA OLMASDI VA SABABI HOLATDA.

    U QARZSIZ holatni qayta yuboradi: o'shanda kvota to'plami `(tarif,)`
    va u BIRINCHI so'rovdan KEYIN HAM o'sha bo'lib qoladi. Ya'ni test
    «narxlash darvozasi retryni rad etadimi?» degan savolni umuman
    bermaydi.

    Qarz bo'lganda esa `vendor_outstanding()` — u `as_of` bilan
    filtrlanmaydi va HAMMA to'lovni ayiradi — retryda BOSHQA son
    qaytaradi:

        so'rov 1  qoldiq  45 000   kvotalar (15000, 45000, 60000)
        retry     qoldiq −15 000   kvotalar (15000,)

    Ya'ni asl summa endi kvota EMAS, `reason_code` esa yo'q ->
    422 `reason_required`. Pul YOZILGAN, kassir esa qattiq xato
    ko'radi va `[Qayta yuborish]` o'sha 422 ni qaytaradi.

    ⛔ IKKALA SHOX HAM O'LCHANADI (§9.6 ning uchinchi va ikkinchi
       kvotasi): ular BOSHQA `quote_soum` bilan yoziladi, ya'ni bitta
       shox yashil qolib ikkinchisi qizarishi MUMKIN.

    ⛔ DA'VO «200» BILAN CHEKLANMAYDI: `payment_id` AYNI bo'lishi va
       jadvalda BITTA qator qolishi ham tekshiriladi — 200 ni ikkinchi
       qator yozib ham qaytarish mumkin bo'lardi.
    =======================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    debt = 45_000
    env.add_debt(stall_id=stall_id, vendor_id=env.vendor_id, amount_soum=debt)

    amount = TARIFF_SOUM + debt if pays_the_debt_too else debt
    payload = _body(stall_code=code, amount_soum=amount, key=f"cr02-{label}")

    first = await _post(api_client, cashier_headers, payload)
    assert first.status_code == 201, first.text

    retry = await _post(api_client, cashier_headers, payload)

    assert retry.status_code == 200, (
        "qarzni surgan to'lovning retryi 200 BERMADI — D-21 buzilgan: "
        f"{retry.status_code} {retry.text}"
    )
    assert retry.json()["payment_id"] == first.json()["payment_id"]
    assert len(env.payments()) == 1, "retry IKKINCHI qator yozdi"


async def test_a_replayed_key_sent_to_another_stall_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """CR-02 tuzatishining ⛔ NAZORATI: kalit O'SHA, **rasta** BOSHQA -> **409**.

    ⛔ BU TEST TUZATISHNING ARZON SHAKLINI RAD ETADI. Barmoq izini
       qatorning O'Z `stall_id` si bilan hisoblash (ya'ni «hamma
       maydonni qatordan olish») retryni har doim mos qilardi va server
       kassirga BIRINCHI rastaning to'lovini «tasdiqlangan» deb
       ko'rsatardi — noto'g'ri rasta pul yo'lida JIMGINA to'langan
       bo'lib qolardi.

    ⚠ Faqat `quote_soum` qatordan olinadi (u serverning O'Z hosilasi va
      birinchi so'rov uni o'zgartirgan); qolgan maydonlar SO'ROVDAN.

    ⛔ OXIRIDA NAZORAT: O'SHA ikkinchi rasta YANGI kalit bilan **201**
       oladi. Usiz 409 «bu rastaga umuman to'lov yozib bo'lmaydi»
       degandan ham kelib chiqishi mumkin edi va test o'z da'vosini
       («kalit qayta ishlatilgan») isbotlamasdi (D-30).
    """
    first_stall = env.stall("stall_with_two_occupied_slots")
    other_stall = env.stall("stall_with_one_human_confirmed_occupied_slot")
    assert first_stall != other_stall, "nazorat: seedda ikkinchi rasta yo'q"
    other_code = env.code(other_stall)
    key = "cr02-boshqa-rasta"

    first = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=env.code(first_stall), amount_soum=TARIFF_SOUM, key=key),
    )
    assert first.status_code == 201, first.text

    second = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=other_code, amount_soum=TARIFF_SOUM, key=key),
    )

    assert second.status_code == 409, second.text
    assert _detail(second) == "idempotency_key_reused"
    assert len(env.payments()) == 1

    control = await _post(
        api_client, cashier_headers, _body(stall_code=other_code, amount_soum=TARIFF_SOUM)
    )
    assert control.status_code == 201, f"nazorat yiqildi — 409 rastadan edi: {control.text}"
    assert len(env.payments()) == 2


async def test_two_concurrent_requests_write_one_row_and_neither_returns_5xx(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """A1 zondining HTTP QATLAMIDAGI JUFTI — parallel ikki `POST`.

    =======================================================================
    ⛔ ZOND SQL DARAJASIDA O'LCHAGAN, BU ESA BUTUN YO'LNI: marshrut ->
       repozitoriy -> `ON CONFLICT` -> ikkinchi `SELECT` -> javob.

    Uchala da'vo BIRGA: jadvalda **1 qator**, ikkala javobda ham **bir
    xil** `payment_id`, birortasi **5xx bermaydi**. Uchinchisi eng
    muhimi — `RuntimeError` (Pitfall 3) 500 bo'lib chiqardi va u
    «to'lov yozilmadi» degan noto'g'ri xulosaga olib kelardi.
    =======================================================================
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    payload = _body(stall_code=code, amount_soum=TARIFF_SOUM, key="parallel-kalit-0001")

    first, second = await asyncio.gather(
        _post(api_client, cashier_headers, payload),
        _post(api_client, cashier_headers, payload),
    )

    for response in (first, second):
        assert response.status_code < 500, f"5xx: {response.status_code} — {response.text}"
        assert response.status_code in {200, 201}, response.text

    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert len(env.payments()) == 1, "parallel so'rovlar IKKI qator yozdi"


async def test_the_same_key_with_a_different_amount_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Pitfall 4: kalit O'SHA, ⛔ **FAQAT SUMMA** BOSHQA -> **409 `idempotency_key_reused`**.

    =======================================================================
    ⛔⛔ IKKI SO'ROV `amount_soum` DAN BOSHQA HAMMA NARSADA BIR XIL — VA BU
        HOLAT SABOTAJ BILAN O'LCHANGAN (05-15 ning S-D darsi).

    Birinchi yozilishida bu test ikkinchi so'rovga `reason_code` ni HAM
    qo'shgan edi (birinchisida u yo'q edi). O'shanda
    `request_fingerprint()` dan `amount_soum` ni OLIB TASHLASH sabotaji
    ⛔ **YASHIL QOLDI**: xesh `override_reason` maydonidan farq chiqarib,
    409 ni BOSHQA sababdan bergan — ya'ni test o'z nomidagi da'voni
    («summa boshqa») UMUMAN o'lchamayotgan edi.

    Tuzatish testda emas, ⛔ **HOLATNING O'ZIDA**: ikkala so'rov ham
    kvota to'plamidan TASHQARIDAGI summa yuboradi, ya'ni:

        `quote_soum`      -> ikkalasida ham `quotes[0]` (BIR XIL)
        `override_reason` -> ikkalasida ham `partial_day` (BIR XIL)
        `method`/`stall`/`service_date` -> BIR XIL

    Farq qiladigan YAGONA maydon — `amount_soum`. Endi sabotaj ⛔ **AYNAN
    shu maydonni** o'lchaydi.
    =======================================================================

    ⛔ 200 QAYTARISH TAQIQLANADI: server eski to'lovni qaytarardi va
       YANGI summa JIMGINA yo'qolardi — nizoda esa kassir «men 2 000
       yozdim» deb turardi, jurnalda 1 000 bo'lardi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    key = "pitfall4-bir-xil-kalit"

    first = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, key=key, reason_code="partial_day"),
    )
    assert first.status_code == 201, first.text

    second = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=2_000, key=key, reason_code="partial_day"),
    )

    assert second.status_code == 409, second.text
    assert _detail(second) == "idempotency_key_reused"
    assert len(env.payments()) == 1


async def test_the_same_key_with_a_different_reason_is_also_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Pitfall 4 ning IKKINCHI shoxi: kalit O'SHA, ⛔ **faqat SABAB** boshqa.

    ⚠ ALOHIDA TEST VA BU YUQORIDAGI SABOTAJNING NATIJASI: bitta testda
      ikki maydonni birdan o'zgartirish «qaysi maydon xeshni himoya
      qilyapti?» savolini javobsiz qoldiradi. Endi har maydonning O'Z
      testi bor va sabotaj ikkalasini AJRATIB ko'rsatadi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    key = "pitfall4-sabab-kaliti"

    first = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, key=key, reason_code="partial_day"),
    )
    assert first.status_code == 201, first.text

    second = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, key=key, reason_code="director_waiver"),
    )

    assert second.status_code == 409, second.text
    assert _detail(second) == "idempotency_key_reused"
    assert len(env.payments()) == 1


# ===========================================================================
# 2. SC#5(c) — D-23: APPEND-ONLY, TUZATISH FAQAT STORNO
# ===========================================================================


async def test_a_written_payment_cannot_be_updated_even_with_raw_sql(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """SC#5(c) ning BIRINCHI yarmi: `UPDATE payments` ⛔ **EGA ROLIDA HAM** rad etiladi.

    ⚠ Hujum `sbozor_owner` bilan qilinadi, `sbozor_app` bilan EMAS: ilova
      roli baribir RLS ostida, ya'ni u yerdagi rad etish «himoya
      ishlayapti» degan YOLG'ON ishonch berardi. Qo'riqchi
      (`payment_immutable()`) SHARTSIZ, ya'ni u egani ham to'xtatadi.
    """
    from psycopg.errors import RaiseException

    code = env.code(env.stall("stall_with_two_occupied_slots"))
    created = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert created.status_code == 201, created.text
    payment_id = created.json()["payment_id"]

    with pytest.raises(RaiseException):
        sync_owner_conn.execute("UPDATE payments SET amount_soum = 1 WHERE id = %s", (payment_id,))
    sync_owner_conn.rollback()


async def test_a_reversal_is_a_new_row_and_the_original_is_untouched(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """SC#5(c) ning IKKINCHI yarmi: storno **YANGI QATOR**, asl qator O'ZGARMAGAN.

    ⛔ `reversal_reason` MAJBURIY va u yangi qatorda; `amount_soum`
       MUSBAT KATTALIK (C-5) — belgi faqat ko'rinishda tug'iladi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    created = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert created.status_code == 201, created.text
    original = created.json()

    reversed_response = await api_client.post(
        f"{PAYMENTS_URL}/{original['payment_id']}/reverse",
        json={"reason_code": "wrong_amount"},
        headers=cashier_headers,
    )
    assert reversed_response.status_code == 201, reversed_response.text
    assert reversed_response.json()["kind"] == "reversal"

    rows = env.payments()
    assert len(rows) == 2, f"storno YANGI qator bo'lishi kerak: {rows}"
    payment_row = next(row for row in rows if row[1] == "payment")
    reversal_row = next(row for row in rows if row[1] == "reversal")

    assert payment_row[2] == TARIFF_SOUM, "ASL qator o'zgargan — D-23 buzilgan"
    assert reversal_row[2] == TARIFF_SOUM, "storno summasi MUSBAT KATTALIK bo'lishi kerak (C-5)"
    assert reversal_row[4] == "wrong_amount", "`reversal_reason` yozilmagan"
    assert reversal_row[7] == UUID(original["payment_id"])


async def test_reversing_twice_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Ikkinchi storno -> **409 `payment_already_reversed`**; qator SONI O'SMAYDI.

    ⛔ Ikkinchi manfiy qator qoldiqni IKKI MARTA kamaytirardi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    created = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    payment_id = created.json()["payment_id"]

    first = await api_client.post(
        f"{PAYMENTS_URL}/{payment_id}/reverse",
        json={"reason_code": "wrong_amount"},
        headers=cashier_headers,
    )
    assert first.status_code == 201, first.text

    second = await api_client.post(
        f"{PAYMENTS_URL}/{payment_id}/reverse",
        json={"reason_code": "duplicate_entry"},
        headers=cashier_headers,
    )
    assert second.status_code == 409, second.text
    assert _detail(second) == "payment_already_reversed"

    reversals = [row for row in env.payments() if row[1] == "reversal"]
    assert len(reversals) == 1, f"IKKINCHI storno qatori yozilgan: {reversals}"


async def test_a_reversal_without_a_reason_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """`reason_code` siz storno -> **422** (Pydantic darajasida, D-19)."""
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    created = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    payment_id = created.json()["payment_id"]

    response = await api_client.post(
        f"{PAYMENTS_URL}/{payment_id}/reverse", json={}, headers=cashier_headers
    )
    assert response.status_code == 422, response.text


def test_the_payments_prefix_exposes_no_edit_or_delete_method() -> None:
    """`openapi()` da `/api/v1/payments*` metodlari ⛔ **AYNAN** `{POST, GET}` (D-23).

    ⛔ TO'PLAM TENGLIGI, `not in` EMAS: inkor tasdiq faqat SANAB O'TILGAN
       nomni ushlaydi va to'rtinchi metod jimgina qo'shilardi (D-31).
    """
    spec = fastapi_app.openapi()
    methods = {
        method.upper()
        for path, operations in spec["paths"].items()
        if path.startswith(PAYMENTS_URL)
        for method in operations
    }
    assert methods == MATRIX_METHODS, f"kutilmagan metodlar: {sorted(methods - MATRIX_METHODS)}"


# ===========================================================================
# 3. CASH-02 / D-19 — SUMMA O'ZGARISHI IKKI TOMONLAMA DARVOZA
# ===========================================================================


async def test_a_changed_amount_without_a_reason_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Chetlangan summa + sababsiz -> **422 `reason_required`**; qator YOZILMAYDI."""
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM - 5_000)
    )

    assert response.status_code == 422, response.text
    assert _detail(response) == "reason_required"
    assert env.payments() == []


async def test_a_changed_amount_with_a_reason_is_written_and_audited(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    market_scope: MarketScope,
) -> None:
    """CASH-02: sabab bilan -> **201** va `audit_log` da `payment_override`.

    =======================================================================
    ⛔ AUDITDA AKTOR, ESKI VA YANGI SUMMA — UCHALASI BIRGA.

    `payments` `AUDITED_TABLES` da YO'Q (append-only, hajm katta), ya'ni
    DB-trigger u yerda hech nima yozmaydi va `write_app_audit()` YAGONA
    audit yo'li. Faqat `amount_soum` yozish nizoda «serverning taklifi
    qanday edi?» savolini javobsiz qoldirardi.

    ⛔ `quotes` TO'PLAMI HAM YOZILADI: `quote_soum` YOLG'IZ tanlangan
       variantni ko'rsatadi, TAKLIF MAYDONINI emas (D-02).
    =======================================================================

    ⚠ JURNAL `market_scope()` ORQALI O'QILADI, `sync_owner_conn` BILAN
      EMAS — VA BU O'LCHANGAN: `audit_read` policy'si oddiy tenant
      predikatiga bo'ysunadi va `audit_log` `owner_bootstrap` policy'sini
      ATAYIN OLMAGAN (`policies.py`), ya'ni tenant konteksti
      o'rnatilmagan EGA ham 0 qator ko'radi. Ega bilan o'qish testni
      «audit yozilmagan» degan YOLG'ON natijaga olib kelardi (shakl
      `test_assignments_api.py:500-506` dan olingan).
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    partial = TARIFF_SOUM - 5_000

    response = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=partial, reason_code="partial_day"),
    )
    assert response.status_code == 201, response.text

    with market_scope(env.market_id) as conn:
        audit = conn.execute(
            "SELECT actor_user_id, new_value->>'quote_soum', new_value->>'amount_soum', "
            "       new_value->>'reason_code', new_value->'quotes' "
            "FROM audit_log WHERE market_id = %s AND action = 'payment_override' ORDER BY id",
            (str(env.market_id),),
        ).fetchall()

    assert len(audit) == 1, f"aynan bitta `payment_override` qatori kutilgan: {audit}"
    actor, quote_soum, amount_soum, reason_code, quotes = audit[0]
    assert actor == env.cashier_id, "aktor yozilmagan"
    assert int(quote_soum) == TARIFF_SOUM, "ESKI (server bergan) summa yozilmagan"
    assert int(amount_soum) == partial, "YANGI summa yozilmagan"
    assert reason_code == "partial_day"
    assert TARIFF_SOUM in quotes, f"server taklif to'plami yozilmagan: {quotes}"


async def test_an_unchanged_amount_with_a_reason_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Server taklifiga TENG summa + sabab -> **422 `override_not_applicable`**.

    =======================================================================
    ⛔ BU `reason_required` NING TESKARISI VA ULAR BIR JUFT BO'LIB
       O'LCHANADI — aks holda darvoza bir tomonni UMUMAN ko'rmasdi.

    Sababni JIMGINA tashlab yuborish auditga ma'nosiz yozuv qoldirardi
    («direktor kechirdi» — hech narsa kechirilmagan holda) va 06-04 ning
    juftlangan `CHECK` i bunday qatorni IFODALAB BO'LMAYDIGAN qiladi.
    =======================================================================
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    response = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=TARIFF_SOUM, reason_code="director_waiver"),
    )

    assert response.status_code == 422, response.text
    assert _detail(response) == "override_not_applicable"
    assert env.payments() == []


async def test_a_partial_and_an_overpayment_are_both_allowed(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """OQ-4/A4: qisman **va** ortiqcha to'lov RUXSAT; ortiqchadan keyin qoldiq MANFIY.

    ⛔ Ortiqcha to'lovni bloklash kassirni pulni UMUMAN YOZMASLIKKA
       majburlardi — ya'ni himoya o'zi himoya qilayotgan yozuvni yo'q
       qilardi (avans `vendor_outstanding()` da manfiy bo'lib qoladi).
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    vendor_id = env.vendor_id

    partial = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, reason_code="partial_day"),
    )
    assert partial.status_code == 201, partial.text

    over = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=TARIFF_SOUM * 3, reason_code="director_waiver"),
    )
    assert over.status_code == 201, over.text

    assert env.outstanding(vendor_id) < 0, "ortiqcha to'lovdan keyin qoldiq AVANS bo'lishi kerak"


# ===========================================================================
# 4. BLOCKER 4 — YOPIQ KUNDA ESKI QARZ UNDIRILADI (UI-SPEC §9.4)
# ===========================================================================


async def test_on_a_closed_day_an_outstanding_debt_can_still_be_collected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ BLOCKER 4(a): `market_closed` + qarz > 0 -> **201** (rad etish EMAS).

    =======================================================================
    ⛔ ESKI SHART (`amount_soum is None` -> 422) BU TESTNI QIZARTIRADI.

    §9.4 ning to'lanadigan ustuni `market_closed` uchun «Faqat
    `outstanding_soum`» deb yozilgan va u tarmoq xatosi qatoridagi
    «Hech nima» dan ATAYIN farqlangan. `POST /payments` esa CASH-01 ning
    YAGONA kirish nuqtasi, ya'ni eski shart qarzni UNDIRILMAYDIGAN
    qilardi — har dushanba, har bayram.
    =======================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    debt = 45_000
    env.add_debt(stall_id=stall_id, vendor_id=env.vendor_id, amount_soum=debt)
    env.set_market_open(is_open=False)

    response = await _post(api_client, cashier_headers, _body(stall_code=code, amount_soum=debt))

    assert response.status_code == 201, response.text
    assert response.json()["service_date"] == env.today.isoformat()
    assert len(env.payments()) == 1


async def test_on_a_closed_day_without_a_debt_the_named_reason_is_visible(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ BLOCKER 4(b): `market_closed` + qarz yo'q -> **422** va `detail` da `market_closed`.

    ⛔ SABAB KO'RINADI: `amount_unavailable` ning matni «Server summani
       bermadi / Sahifani yangilang» — u NOSOZLIK deb o'qiladi va kassir
       sahifani qayta-qayta yangilardi, holbuki bu NORMAL kalendar holati.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    env.set_market_open(is_open=False)

    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )

    assert response.status_code == 422, response.text
    assert _detail(response) == "market_closed"
    assert env.payments() == []


async def test_without_a_tariff_an_outstanding_debt_can_still_be_collected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ BLOCKER 4(c): `tariff_missing` + qarz > 0 -> **201**.

    ⚠ TARIFSIZ TOIFA TEST TOMONIDAN YOZILADI: `market_domain` A bozorining
      UCHALA toifasiga ham tarif beradi (tarifsiz toifa faqat B da), ya'ni
      bu shox seedda MAVJUD EMAS. Toifa davri BUGUNDAN boshlanadi, ya'ni
      u eski qatordan USTUN turadi (`valid_from <= as_of ORDER BY DESC`).
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    debt = 30_000
    env.add_debt(stall_id=stall_id, vendor_id=env.vendor_id, amount_soum=debt)

    tariffless_category = uuid4()
    env.conn.execute(
        "INSERT INTO stall_categories (id, market_id, name) VALUES (%s, %s, %s)",
        (str(tariffless_category), str(env.market_id), "06-09 test — tarifsiz toifa"),
    )
    env.conn.execute(
        "INSERT INTO stall_category_periods (id, market_id, stall_id, category_id, valid_from) "
        "VALUES (%s, %s, %s, %s, %s)",
        (str(uuid4()), str(env.market_id), str(stall_id), str(tariffless_category), env.today),
    )

    response = await _post(api_client, cashier_headers, _body(stall_code=code, amount_soum=debt))

    assert response.status_code == 201, response.text
    assert len(env.payments()) == 1


# ===========================================================================
# 5. §9.6 — `[Qarzni ham olish]` SABABSIZ O'TADI
# ===========================================================================


async def test_paying_the_total_due_needs_no_reason_code(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ `[Qarzni ham olish]`: `amount = bugungi tarif + qarz`, sababsiz -> **201**.

    ⛔ §9.6: bu BIR QO'SHIMCHA BOSISH, sabab dialogi EMAS. Kvota
       to'plamining UCHINCHI elementi (`total_due_soum()`), ya'ni sabab
       talab qilish normal holatni ISTISNO yo'lidan o'tkazardi.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    debt = 45_000
    env.add_debt(stall_id=stall_id, vendor_id=env.vendor_id, amount_soum=debt)

    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM + debt)
    )

    assert response.status_code == 201, response.text
    assert env.outstanding(env.vendor_id) == -TARIFF_SOUM, (
        "jami to'langach eski qarz to'liq yopilishi kerak edi"
    )


async def test_paying_only_the_outstanding_needs_no_reason_code(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ Kvota to'plamining IKKINCHI elementi ham sababsiz o'tadi (§9.4).

    «Faqat eski qarz» — §9.4 ning to'lanadigan ustunidagi variant va u
    bugungi tarif MAVJUD bo'lganda ham qonuniy.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    debt = 45_000
    env.add_debt(stall_id=stall_id, vendor_id=env.vendor_id, amount_soum=debt)

    response = await _post(api_client, cashier_headers, _body(stall_code=code, amount_soum=debt))

    assert response.status_code == 201, response.text
    assert env.outstanding(env.vendor_id) == 0


# ===========================================================================
# 6. BLOCKER 3 — BIRIKTIRILMAGAN RASTA: BITTA ANIQ JAVOB (D-28)
# ===========================================================================


async def test_an_unassigned_stall_is_rejected_with_a_named_conflict(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ BLOCKER 3: biriktirilmagan rasta -> **409 `stall_not_assigned`**, 404 EMAS.

    =======================================================================
    ⛔ 404 `stall_not_found` KASSIRGA YOLG'ON AYTARDI.

    Rasta REESTRDA BOR — `stall_assignments` da o'sha kunga tegishli qator
    yo'q (`periods.py:29-33` bo'shliqni ATAYIN ruxsat etadi). 404 kassirni
    to'g'ri kodni QAYTA-QAYTA terishga majburlardi va u oxirida raqamni
    noto'g'ri deb hisoblardi (D-28 ning nizo modeli).

    ⚠ RASTA `market_domain.unassigned_stall_id` — unga BIRORTA
      biriktirish YOZILMAGAN (D-11 ning ikkinchi shakli), ya'ni bu holat
      SANAGA BOG'LIQ EMAS. `gap_stall` sanaga bog'liq bo'lardi
      (`GAP_REOPENED_AT` o'tgach u biriktirilgan bo'lib qolardi).
    =======================================================================
    """
    stall_id = env.domain.market_a.unassigned_stall_id
    assert stall_id is not None, "nazorat: seedda biriktirilmagan rasta yo'q"
    code = env.code(stall_id)

    response = await _post(api_client, cashier_headers, _body(stall_code=code, amount_soum=5_000))

    assert response.status_code == 409, response.text
    assert _detail(response) == "stall_not_assigned"
    assert env.payments() == [], "biriktirilmagan rastaga qator YOZILGAN"


async def test_the_same_stall_accepts_a_payment_once_an_assignment_exists(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ BLOCKER 3 ning NAZORATI: biriktirish qo'shilgach O'SHA so'rov -> **201**.

    ⛔ USIZ 409 «kod xatosi» ham bo'lishi mumkin edi: nazorat holati
       javobning HOLATDAN kelayotganini isbotlaydi.
    """
    stall_id = env.domain.market_a.unassigned_stall_id
    assert stall_id is not None
    code = env.code(stall_id)

    env.conn.execute(
        "INSERT INTO stall_assignments (id, market_id, stall_id, vendor_id, period) "
        "VALUES (%s, %s, %s, %s, daterange(%s, NULL, '[)'))",
        (str(uuid4()), str(env.market_id), str(stall_id), str(env.vendor_id), env.today),
    )

    response = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, reason_code="partial_day"),
    )

    assert response.status_code == 201, response.text
    assert len(env.payments()) == 1


async def test_an_unknown_stall_code_is_a_not_found(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Mavjud BO'LMAGAN kod -> **404 `stall_not_found`** — `stall_not_assigned` DAN farqli.

    Ikkala kod ham 06-02 reyestrida va ular ATAYIN ajratilgan: bu TERISH
    xatosi (yechimi — raqamni qayta kiritish), u esa HOLAT (yechimi —
    biriktirishlar sahifasi).
    """
    response = await _post(
        api_client, cashier_headers, _body(stall_code="9999-yoq", amount_soum=5_000)
    )

    assert response.status_code == 404, response.text
    assert _detail(response) == "stall_not_found"


# ===========================================================================
# 7. WR-01 — OCHIQ SMENA SHART; `shift_id = NULL` QATORI OYNADA KO'RINMAYDI
# ===========================================================================


async def test_a_payment_without_an_open_shift_is_refused(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ WR-01: ochiq smenasiz to'lov -> **409 `no_open_shift`**, 201 EMAS.

    =======================================================================
    ⛔⛔ REYESTR BU QOIDANI E'LON QILGAN, MARSHRUT ESA QO'LLAMAGAN EDI.

    `billing_errors.NO_OPEN_SHIFT` docstringi: «To'lov yozish uchun ochiq
    smena yo'q (409) … ochiq smenasiz yozilgan to'lov keyin hech qaysi
    ko'r deklaratsiyaga tushmasdi va variance o'z maxrajini yo'qotardi».
    Hech qaysi marshrut uni ko'tarmasdi — bu test ILGARI **201** ni va
    `shift_id IS NULL` ni TASDIQLARDI, ya'ni u nuqsonni QULFLAB
    QO'YGANDI.

    ⛔ IKKINCHI, HUJJATLASHTIRILMAGAN OQIBAT — ABADIY BEKOR QILINMASLIK:
       `reverse_payment` `owner.shift_id` so'rovchining OCHIQ smenasiga
       teng bo'lishini talab qiladi (`None != <uuid>` har doim rost ->
       403), `payments` esa append-only. Ya'ni noto'g'ri rastaga
       yozilgan smenasiz to'lovni HECH QACHON tuzatib bo'lmasdi.

    ⛔ OQ-6/A5 («direktor smenasiz kiritishi mumkin») BU YO'LNI
       OQLAMAYDI: `PAYMENT_CREATE` D-07 matritsasida ⛔ YOLG'IZ KASSIRDA
       va direktor qatorida u ATAYIN yo'q — o'sha asos API orqali
       yetib bo'lmaydigan holatga tegishli edi.

    ⚠ USTUN NULLABLE QOLADI (migratsiya TEGILMADI): qaror MARSHRUT
      darajasida va kelajakdagi direktor yuzasi uni o'z shartlari bilan
      qayta ochishi mumkin. Pastdagi test aynan shu sababdan hamon
      `shift_id IS NULL` qatorini SEED bilan yozadi.
    =======================================================================
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    env.close_the_open_shift()

    response = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, reason_code="partial_day"),
    )

    assert response.status_code == 409, response.text
    assert _detail(response) == "no_open_shift"
    assert env.payments() == [], "smenasiz to'lov YOZILDI — WR-01 darvozasi ishlamadi"

    # ⛔ NAZORAT: 409 SMENADAN keldi, boshqa shartdan emas (D-30).
    env.open_a_shift()
    allowed = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=1_000, reason_code="partial_day"),
    )
    assert allowed.status_code == 201, f"nazorat yiqildi — 409 smenadan EMAS edi: {allowed.text}"


async def test_a_shiftless_row_stays_out_of_the_cashier_window(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """`shift_id IS NULL` qatori `GET /payments/recent` da KO'RINMAYDI.

    =======================================================================
    ⛔ BU DA'VO WR-01 DAN KEYIN HAM YASHAYDI VA U BOSHQA NARSANI
       O'LCHAYDI: oyna `shift_id` BO'YICHA filtrlanadimi.

    Ustun hamon nullable (migratsiya tegilmadi) va bazada bunday qator
    bo'lishi mumkin — masalan WR-01 dan OLDIN yozilgan tarixiy yozuv.
    Agar filtr `cashier_id` bo'yicha bo'lsa, u kassirning yangi
    smenasidagi ro'yxatga SIZIB KIRARDI va §8.8 ning oynasi begona
    yozuvni ko'rsatardi.

    ⛔ QATOR SEED BILAN YOZILADI, MARSHRUT ORQALI EMAS: marshrut endi
       uni ATAYIN yozmaydi (WR-01) va uni «yozdirish» uchun darvozani
       chetlab o'tish testni o'z himoyasiga qarshi qo'yardi.
    =======================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)

    # ⚠ `amount_soum == quote_soum` VA `override_reason IS NULL` —
    #   `ck_payments_override_is_paired` juftlangan `CHECK` i shuni
    #   talab qiladi (chetlanish bu testning da'vosi EMAS).
    shiftless_id = add_payment(
        env.conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=None,
        amount_soum=1_000,
        quote_soum=1_000,
    )

    in_shift = await _post(
        api_client,
        cashier_headers,
        _body(stall_code=code, amount_soum=2_000, reason_code="partial_day"),
    )
    assert in_shift.status_code == 201, in_shift.text

    window = await api_client.get(RECENT_URL, headers=cashier_headers)
    assert window.status_code == 200, window.text
    ids = {item["payment_id"] for item in window.json()["items"]}
    assert ids == {in_shift.json()["payment_id"]}, (
        f"smenasiz qator ({shiftless_id}) oynada KO'RINDI — filtr `shift_id` bo'yicha emas"
    )


# ===========================================================================
# 8. §8.8 — OYNA SERVERDA QAT'IY 5 VA PARAMETRSIZ
# ===========================================================================


async def test_the_window_returns_at_most_five_rows(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Yetti to'lov -> oynada **5** qator (§8.8, §10.3).

    ⛔ Kassir smenasining HAMMA to'lovini ko'rsa, ularni QO'SHIB tizim
       summasini chiqarib olardi va ko'r deklaratsiya ARIFMETIKA BILAN
       buzilardi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    for index in range(7):
        response = await _post(
            api_client,
            cashier_headers,
            _body(stall_code=code, amount_soum=1_000 + index, reason_code="partial_day"),
        )
        assert response.status_code == 201, response.text

    window = await api_client.get(RECENT_URL, headers=cashier_headers)
    assert window.status_code == 200, window.text
    assert len(window.json()["items"]) == 5


def test_the_window_route_declares_no_paging_parameter() -> None:
    """`openapi()` da `GET /payments/recent` ning parametrlari ⛔ **BO'SH TO'PLAM**.

    ⛔ Yig'indi yo'lini MAYDON YASHIRISH emas, MARSHRUTNING IMKONIYATI
       to'sadi: `limit`/`offset`/`cursor`/`page` — birortasi e'lon
       qilinmagan.
    """
    spec = fastapi_app.openapi()
    operation = spec["paths"][RECENT_URL]["get"]
    names = {param["name"] for param in operation.get("parameters", [])}

    assert names == set(), f"oyna marshrutida parametr e'lon qilingan: {sorted(names)}"


async def test_the_window_is_empty_without_an_open_shift(
    api_client: httpx.AsyncClient, env: Env, director_headers: dict[str, str]
) -> None:
    """Ochiq smenasi bo'lmagan foydalanuvchi -> **200** va BO'SH ro'yxat (404 EMAS).

    ⚠ Direktorda `billing_collect_view` BOR (u oynani ko'rishi mumkin,
      §5.6), smena esa YO'Q — ya'ni bu holat REAL va bo'sh ro'yxat
      «natija», nosozlik emas.
    """
    response = await api_client.get(RECENT_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"items": []}


# ===========================================================================
# 9. C-10 VA KLIENT KONTRAKTI — TO'PLAM TENGLIGI
# ===========================================================================


async def test_the_payment_payload_has_exactly_the_eight_keys(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Javob kalitlari AYNAN sakkizta — `vendor_name`/`phone` YO'Q (C-10, D-24).

    ⛔ TO'PLAM TENGLIGI, `not in` EMAS (D-31): inkor tasdiq faqat AYNAN
       o'sha nomni ushlaydi va `vendorName` jimgina o'tib ketardi.
    """
    code = env.code(env.stall("stall_with_two_occupied_slots"))
    response = await _post(
        api_client, cashier_headers, _body(stall_code=code, amount_soum=TARIFF_SOUM)
    )
    assert response.status_code == 201, response.text

    keys = set(response.json())
    assert keys == PAYMENT_KEYS, f"kutilmagan kalitlar: {sorted(keys ^ PAYMENT_KEYS)}"
    assert keys & PERSONAL_FIELDS == set()
    assert "charge_id" not in keys, "D-24: to'lov hisobga bog'lanmaydi"
    assert "quote_soum" not in keys, "D-20: server taklifi javobda YO'Q"


def test_the_payload_matches_the_client_schema() -> None:
    """⛔ SERVER JAVOBI VA KLIENT SXEMASI — TIL CHEGARASI BO'YLAB TO'PLAM TENGLIGI.

    =======================================================================
    ⛔ NEGA BU DARVOZA KERAK: `paymentResponseSchema` `z.strictObject`
       (06-03, allaqachon merge qilingan), ya'ni serverda QO'SHILGAN har
       qanday maydon klientda PARSE PAYTIDA yiqilardi — va nosozlik
       kassir panelida, dala sinovida ko'rinardi.

    ⚠ RO'YXAT KLIENT FAYLIDAN HOSILA, qo'lda yozilgan EMAS: nusxa bir
      kun ajralib ketardi va bu darvoza aynan o'sha ajralishni ushlash
      uchun bor.
    =======================================================================
    """
    source = CLIENT_SCHEMA_PATH.read_text(encoding="utf-8")
    match = _CLIENT_SCHEMA_RE.search(source)
    assert match is not None, (
        f"{CLIENT_SCHEMA_PATH} da `paymentResponseSchema` topilmadi — "
        "klient kontrakti ko'chirilgan bo'lsa bu darvoza YANGILANISHI shart"
    )
    client_keys = set(_CLIENT_KEY_RE.findall(match.group("body")))

    assert client_keys == PAYMENT_KEYS, (
        f"server va klient kalitlari ajralib ketdi: {sorted(client_keys ^ PAYMENT_KEYS)}"
    )
