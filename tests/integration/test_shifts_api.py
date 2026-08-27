"""`/api/v1/shifts/*` — SMENA VA ⛔⛔ KO'R NAQD DEKLARATSIYASI (CASH-04, SC#5(d)).

=============================================================================
⛔⛔ BU FAYLNING UCH ENG QIMMAT DA'VOSI:

  1. **D-25 IKKI MUSTAQIL QATLAMDA** — `POST /shifts/{id}/close` javobi
     kalitlari to'plami AYNAN to'rtta (`assertEqual`, `not in` EMAS) VA
     `app.openapi()` dan HOSILA skan o'sha sakkiz nomni izlaydi. Ikkalasi
     ham bo'lishi shart: birinchisi javob BAYTLARINI, ikkinchisi
     KONTRAKTNI o'lchaydi va ular BOSHQA-BOSHQA yo'llardan buziladi;

  2. **SC#5(d) — IKKI TOMONLAMA VARIANCE**: `declared < system`,
     `declared > system` VA `declared == system` — uchalasi BITTA
     testda. Ikkinchisi eng muhimi: ortiqcha naqd JIM YUTILMAYDI (D-26);

  3. **§11.5 FLAG** — `shift_id IS NULL` to'lovlari ALOHIDA sanoq bilan
     qaytariladi VA birorta smenaning `system_soum` iga KIRMAYDI. Ikkala
     yarim ham o'lchanadi: faqat birinchisi «ular ko'rinadi» ni, faqat
     ikkinchisi «ular variance ga tegmaydi» ni isbotlardi.

=============================================================================
⛔ VARIANCE `GET /shifts?day=` DA O'LCHANADI, `close` JAVOBIDA EMAS.

06-RESEARCH SC#5(d) «variance SERVERDA hisoblangan va `declared > system`
holatida ham QAYTARILADI» deydi, lekin KIMGA — yozmagan. UI-SPEC §10.4
javob beradi: kassirga ⛔ YO'Q, direktorga ⛔ HA. Shuning uchun mezon
testi AYNAN direktor marshrutiga qaratilgan — `close` javobida yo'q
maydonni izlagan test YOLG'ON-QIZIL bo'lardi.

=============================================================================
⛔ KUN — `Asia/Tashkent`, `CURRENT_DATE` (UTC) EMAS.

`cashier_shifts.business_date` va `payments.business_date` `created_at`
dan `Asia/Tashkent` da hosila. Test kunni `market_today` fixture'idan
(`SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date`) oladi.
`CURRENT_DATE` Toshkent 00:00–04:59 oralig'ida BIR KUN orqada qoladi va
o'sha besh soat ichida testlar jimgina qizarardi — bu nosozlik sinfi
post-merge darvozasida ALLAQACHON bir marta o'lchangan.

=============================================================================
⚠ KALENDAR ISTISNOSI BU FAYLDA KERAK EMAS (`test_payments_api.py` dan farq).

Smena ochish va yopish `market_is_open()` ni UMUMAN o'qimaydi: yopiq
kunda ham kassir kelib kassani hisoblashi mumkin va D-25 ning oqimi
kalendarga bog'liq emas. To'lovlar esa bu faylda HTTP orqali emas,
BEVOSITA (`add_payment`) yoziladi — ya'ni `POST /payments` ning kvota
darvozasi ham qatnashmaydi va fayl haftaning kunidan MUSTAQIL.
=============================================================================
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.main import app as fastapi_app
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import PaymentKind, ShiftStatus

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    import httpx
    from fixtures import MarketScope
    from psycopg import Connection
    from psycopg.rows import TupleRow

SHIFTS_URL = "/api/v1/shifts"
OPEN_URL = f"{SHIFTS_URL}/open"

CLOSE_KEYS = frozenset({"id", "status", "declared_soum", "closed_at"})
"""UI-SPEC §10.3 ning AYNAN TO'RT kaliti.

⛔ RO'YXAT SHU YERDA QO'LDA YOZILGAN VA BU ATAYIN (06-08 da o'rnatilgan
   qoida): u KUTILGAN NATIJA, o'lchov emas. Uni
   `ShiftCloseResponse.model_fields` dan hosila qilish testni «model
   o'ziga teng» degan tavtologiyaga aylantirardi.
"""

BLIND_FIELDS = frozenset(
    {
        "system_soum",
        "system_total_soum",
        "expected_soum",
        "variance_soum",
        "variance",
        "payment_count",
        "cash_count",
        "terminal_soum",
    }
)
"""⛔ `close` javobida BO'LMASLIGI SHART bo'lgan SAKKIZ nom (§10.3).

⚠ RO'YXAT `ShiftCloseResponse` DOCSTRINGIDAGI bilan AYNAN bir xil va u
  ham QO'LDA yozilgan: ikkalasi ham «nima YO'Q» ni tasvirlaydi, ya'ni
  ularni bir-biridan hosila qilish da'voni BO'SHATARDI.
"""

REPORT_ROW_KEYS = frozenset(
    {
        "id",
        "cashier_id",
        "opened_at",
        "closed_at",
        "declared_soum",
        "system_soum",
        "variance_soum",
    }
)
"""§11.5 jadvalining AYNAN YETTI kaliti — ⛔ ISM YO'Q (C-10)."""

PERSONAL_FIELDS = frozenset({"cashier_name", "full_name", "vendor_name", "phone"})
"""C-10 darvozasining maydonlari — `test_payments_api.py:105` bilan AYNI ruh."""


class Env:
    """Billing seed + smena yozish/o'qish yordamchilari."""

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
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    @property
    def admin_id(self) -> UUID:
        return self.base.market_a.admin_user_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def seed_shift_id(self) -> UUID:
        """Seed ochib qo'ygan smena — kassirning YAGONA ochiq smenasi (D-27)."""
        return self.billing.market_a.open_shift_id

    def stall(self, name: str) -> UUID:
        stall_id: UUID | None = getattr(self.billing.market_a, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id

    def pay(self, *, shift_id: UUID | None, amount_soum: int) -> UUID:
        """Smenaga (yoki ⛔ SMENASIZ) to'lov yozadi — BEVOSITA, HTTP siz.

        ⚠ HTTP orqali yozish `POST /payments` ning kvota darvozasidan
          o'tishni talab qilardi (tarif, biriktirish, kalendar), ya'ni
          bu fayl `test_payments_api.py` ning stsenariylarini QAYTA
          quradi va o'z da'vosidan uzoqlashardi. Tizim summasi esa
          `payments` jadvalining O'ZIDAN hisoblanadi — manba bir xil.
        """
        return add_payment(
            self.conn,
            market_id=self.market_id,
            stall_id=self.stall("stall_with_two_occupied_slots"),
            vendor_id=self.vendor_id,
            cashier_id=self.cashier_id,
            shift_id=shift_id,
            amount_soum=amount_soum,
            quote_soum=amount_soum,
        )

    def reverse(self, *, shift_id: UUID, payment_id: UUID, amount_soum: int) -> UUID:
        """Storno qatori — tizim summasini MANFIY tomonga suradi (C-5)."""
        return add_payment(
            self.conn,
            market_id=self.market_id,
            stall_id=self.stall("stall_with_two_occupied_slots"),
            vendor_id=self.vendor_id,
            cashier_id=self.cashier_id,
            shift_id=shift_id,
            amount_soum=amount_soum,
            quote_soum=amount_soum,
            kind=PaymentKind.REVERSAL.value,
            reverses_payment_id=payment_id,
            reversal_reason="wrong_amount",
        )

    def open_shift_row(self, *, cashier_id: UUID | None = None) -> UUID:
        """YANGI ochiq smena — ⛔ oldingisi YOPILGANDAN keyin (D-27).

        ⚠ Ikkinchi ochiq smena `uq_cashier_shifts_market_id_cashier_open`
          bilan rad etilardi, ya'ni chaqiruv tartibi MAJBURIY.
        """
        shift_id = uuid4()
        self.conn.execute(
            "INSERT INTO cashier_shifts (id, market_id, cashier_id, status) "
            "VALUES (%s, %s, %s, %s)",
            (
                str(shift_id),
                str(self.market_id),
                str(cashier_id or self.cashier_id),
                ShiftStatus.OPEN.value,
            ),
        )
        return shift_id

    def shift(self, shift_id: UUID) -> tuple[Any, ...]:
        """`(status, declared_soum, system_soum, closed_at)` — BAZADAN."""
        row = self.conn.execute(
            "SELECT status, declared_soum, system_soum, closed_at "
            "FROM cashier_shifts WHERE market_id = %s AND id = %s",
            (str(self.market_id), str(shift_id)),
        ).fetchone()
        assert row is not None, f"nazorat: {shift_id} smenasi bazada yo'q"
        return tuple(row)


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
    migrated: None,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI (06-05 qoidasi).

    Bu faylning birorta da'vosi bandlikka ham, kunlik hisobga ham
    tayanmaydi: smena `payments` va `cashier_shifts` ustida ishlaydi.
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
        try:
            yield Env(billing, market_domain, two_markets, sync_owner_conn, market_today)
        finally:
            # ⚠ BOZOR QORALAMAGA QAYTARILADI: `payment_immutable()` va
            #   `shift_declaration_immutable()` `DELETE` ni FAQAT nofaol
            #   bozorda ruxsat etadi (`cleanup_billing_domain()` naqshi).
            #
            # ⚠ TESTLAR HTTP ORQALI SMENA YOZADI va seed ularning
            #   identifikatorlarini BILMAYDI — tozalash `market_id`
            #   bo'yicha, `id` bo'yicha EMAS.
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (str(market_id),))
            sync_owner_conn.execute(
                "DELETE FROM cashier_shifts WHERE market_id = %s AND id <> %s",
                (str(market_id), str(billing.market_a.open_shift_id)),
            )
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),)
            )


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """KASSIR sessiyasi — `shift_manage` BOR, ⛔ `report_view` YO'Q (§5.6)."""
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """BOZOR ADMINI — `shift_manage` HAM, `report_view` HAM bor (§5.6).

    ⚠ Kichik bozorda u kassirni ALMASHTIRADI, ya'ni o'z smenasini ocha
      oladi — D-27 ning «indeks `cashier_id` bo'yicha» yarmi shu sessiya
      bilan o'lchanadi.
    """
    return await session_headers(api_client, env.base.market_a.admin_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR — `report_view` BOR, ⛔ `shift_manage` YO'Q (D-26)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


async def _close(
    client: httpx.AsyncClient, headers: dict[str, str], shift_id: UUID, declared_soum: int
) -> httpx.Response:
    return await client.post(
        f"{SHIFTS_URL}/{shift_id}/close", json={"declared_soum": declared_soum}, headers=headers
    )


async def _close_ok(
    client: httpx.AsyncClient, headers: dict[str, str], shift_id: UUID, declared_soum: int
) -> dict[str, Any]:
    """Smenani yopadi va **200** ni TALAB qiladi.

    ⚠ Yordamchi ATAYIN javob TANASINI qaytaradi: chaqiruvchi testlarning
      da'vosi hisobotda, lekin yopilish MUVAFFAQIYATLI bo'lgani har
      safar tekshirilishi shart — aks holda 409 olgan test keyingi
      qadamda «hisobotda qator yo'q» deb qizarardi va sabab BOSHQA
      joyda ko'rinardi.
    """
    response = await _close(client, headers, shift_id, declared_soum)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _report(client: httpx.AsyncClient, headers: dict[str, str], day: date) -> dict[str, Any]:
    response = await client.get(SHIFTS_URL, params={"day": day.isoformat()}, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _detail(response: httpx.Response) -> str:
    """Javobning `detail` KODI — ⛔ SATR (klient `api-client.ts::detailOf()`)."""
    body = response.json()
    detail = body.get("detail")
    assert isinstance(detail, str), f"`detail` SATR bo'lishi SHART (klient shartnomasi): {body}"
    return detail


def _property_names(schema: dict[str, Any], spec: dict[str, Any]) -> set[str]:
    """Sxemadagi HAMMA maydon nomi — ⛔ `$ref` lar bo'ylab REKURSIV.

    ⛔ SAYOZ SKAN YETARLI EMAS: `ShiftReportResponse` ning `variance_soum`
       i uning O'ZIDA emas, ichma-ich joylashgan `ShiftReportRow` da
       yashaydi. Faqat yuqori qatlamga qaragan da'vo «variance
       qaytarilmayapti» degan YOLG'ON natija berardi va sabotaj uni
       ushlamasdi.
    """
    seen: set[str] = set()
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        ref = node.get("$ref")
        if isinstance(ref, str):
            key = ref.rsplit("/", 1)[-1]
            if key in seen:
                return
            seen.add(key)
            walk(spec["components"]["schemas"][key])
            return
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(properties)
        for value in node.values():
            walk(value)

    walk(schema)
    return names


def _response_schema(spec: dict[str, Any], path: str, method: str, code: str) -> dict[str, Any]:
    schema: dict[str, Any] = spec["paths"][path][method]["responses"][code]["content"][
        "application/json"
    ]["schema"]
    return schema


# ===========================================================================
# 1. SMENA OCHISH — D-27 STRUKTURAVIY
# ===========================================================================


async def test_a_second_open_shift_for_the_same_cashier_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """D-27: bir kassirda AYNAN BITTA ochiq smena -> ikkinchisi **409**.

    ⛔ MAJBURIYAT ILOVADA EMAS, QISMAN `UNIQUE` INDEKSDA. Marshrut
       «ochiq smena bormi?» deb TEKSHIRMAYDI — u `INSERT` ni bajaradi va
       `23505` ni domen istisnosiga aylantiradi. Oldindan tekshirish
       «tekshir-keyin-yoz» poygasini tug'dirardi va kassir to'lovlarni
       IKKI smenaga bo'lib yozardi (nomuvofiqlik ikkiga bo'linib
       YO'QOLARDI).
    """
    # Seed kassirga ALLAQACHON ochiq smena yozgan (`open_shift_id`).
    response = await api_client.post(SHIFTS_URL, headers=cashier_headers)

    assert response.status_code == 409, response.text
    assert _detail(response) == "shift_already_open"


async def test_a_different_cashier_can_open_a_shift_at_the_same_time(
    api_client: httpx.AsyncClient, env: Env, admin_headers: dict[str, str]
) -> None:
    """⛔ NAZORAT HOLATI: indeks `cashier_id` BO'YICHA, bozor bo'yicha EMAS.

    Usiz oldingi test «409 har doim qaytadi» degan sababdan ham yashil
    bo'lardi — ya'ni u indeksning QAMROVINI umuman o'lchamasdi. Bozor
    admini `shift_manage` ga ega (§5.6: kichik bozorda u kassirni
    almashtiradi) va uning smenasi kassirnikiga XALAQIT BERMAYDI.
    """
    response = await api_client.post(SHIFTS_URL, headers=admin_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "status", "opened_at"}, body
    assert body["status"] == "open"


async def test_opening_a_shift_is_written_to_the_audit_log_by_the_database(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
) -> None:
    """`cashier_shifts` `AUDITED_TABLES` da — jurnalni ⛔ DB-TRIGGER yozadi.

    ⛔ MARSHRUTDA `write_app_audit()` YO'Q va bu test aynan shuning
       uchun kerak: chaqiruv yo'qligini KOD-KO'RIK bilan tasdiqlash
       «audit umuman yozilmayapti» holatidan farq qilmasdi. Bu yerda
       QATORNING MAVJUDLIGI o'lchanadi, ya'ni «chaqiruv qo'shmadik»
       qarori xavfsiz.

    ⚠ JURNAL `market_scope()` ORQALI O'QILADI: `audit_read` policy'si
      tenant predikatiga bo'ysunadi va `audit_log` `owner_bootstrap`
      policy'sini ATAYIN olmagan — ega ham kontekstsiz 0 qator ko'radi
      (`test_payments_api.py` da o'lchangan).
    """
    response = await api_client.post(SHIFTS_URL, headers=admin_headers)
    assert response.status_code == 201, response.text
    shift_id = response.json()["id"]

    with market_scope(env.market_id) as conn:
        rows = conn.execute(
            "SELECT action, source FROM audit_log "
            "WHERE market_id = %s AND table_name = 'cashier_shifts' AND row_id = %s",
            (str(env.market_id), shift_id),
        ).fetchall()

    assert rows, "`cashier_shifts` uchun audit qatori YO'Q — DB triggeri ishlamagan"
    assert any(action == "insert" and source == "db_trigger" for action, source in rows), rows


async def test_the_open_shift_route_returns_null_when_there_is_none(
    api_client: httpx.AsyncClient, env: Env, admin_headers: dict[str, str]
) -> None:
    """§10.1: ochiq smena yo'q -> **200** va tanasi `null` (⛔ 404 EMAS).

    ⛔ 404 KLIENTNI «SERVER NOSOZ» SHOXIGA YUBORARDI: `useOpenShift()`
       `retry: false` bilan yozilgan (06-03), ya'ni xato holat ekranda
       QOLIB KETARDI va kassir kun boshida smenani UMUMAN ocha olmasdi.
       Ekranda IKKI holat bor, uchinchisi yo'q.
    """
    response = await api_client.get(OPEN_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    assert response.json() is None, response.text


async def test_the_open_shift_route_returns_the_cashiers_own_shift(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Ochiq smena BOR -> uch kalit; ⛔ YIG'INDI MAYDONI YO'Q (§10.1)."""
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)

    response = await api_client.get(OPEN_URL, headers=cashier_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"id", "status", "opened_at"}, (
        f"⛔ Ochiq smena kartasida yig'indi KO'RINMAYDI (§10.1): {sorted(body)}"
    )
    assert body["id"] == str(env.seed_shift_id)


# ===========================================================================
# 2. ⛔⛔ D-25 — KO'R DEKLARATSIYA, IKKI MUSTAQIL QATLAM (G-7 backend yarmi)
# ===========================================================================


async def test_the_close_response_has_exactly_four_keys(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔⛔ G-7 (backend yarmi): kalitlar to'plami AYNAN `CLOSE_KEYS`.

    =======================================================================
    ⛔ TO'PLAM TENGLIGI, `not in` EMAS (D-31). Inkor tasdiq faqat AYNAN
       sanab o'tilgan nomni ushlaydi va `systemSoum` (camelCase) yoki
       `expected` jimgina o'tib ketardi. Tenglik esa HAR QANDAY yangi
       kalitni ushlaydi — nomidan qat'i nazar.

    ⛔ VA `null` QILIB YUBORISH HAM SHU TESTDAN O'TMAYDI: `null` maydon
       javob kalitlari to'plamida BOR bo'lib qoladi.
    =======================================================================
    """
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)

    response = await _close(api_client, cashier_headers, env.seed_shift_id, 100_000)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == CLOSE_KEYS, (
        f"⛔ D-25: javob kalitlari AYNAN {sorted(CLOSE_KEYS)} bo'lishi SHART, "
        f"kelgani {sorted(body)} — ortiqcha: {sorted(set(body) - CLOSE_KEYS)}"
    )
    assert body["status"] == "closed"
    assert body["declared_soum"] == 100_000


async def test_the_openapi_schema_hides_the_totals_from_the_cashier_and_shows_them_to_the_director(
    env: Env,
) -> None:
    """⛔⛔ D-32: `app.openapi()` DAN HOSILA SKAN — ⛔ IKKI YO'NALISH.

    =======================================================================
    ⛔ IKKALA YO'NALISH HAM BO'LISHI SHART VA BU DA'VONING O'ZAGI:

      (a) `close` javobida sakkiz nomning BIRORTASI YO'Q;
      (b) `GET /shifts` javobida `system_soum` VA `variance_soum` BOR.

    Faqat (a) bo'lsa da'vo BO'SH bo'lardi: variance ni HAMMA joydan
    olib tashlash uni yashil qilardi — ya'ni test «mahsulot ishlayapti»
    ni emas, «maydon yo'q» ni o'lchagan bo'lardi. Faqat (b) esa D-25 ni
    umuman qo'riqlamasdi.
    =======================================================================

    ⚠ BU TEST HTTP GA CHIQMAYDI: u KONTRAKTNI (OpenAPI) o'lchaydi,
      yuqoridagi test esa JAVOB BAYTLARINI. Ular BOSHQA-BOSHQA yo'llardan
      buziladi — masalan `model_config` o'zgarsa birinchisi, javob
      qurilishi o'zgarsa ikkinchisi qizaradi.
    """
    spec = fastapi_app.openapi()

    close = _property_names(
        _response_schema(spec, f"{SHIFTS_URL}/{{shift_id}}/close", "post", "200"), spec
    )
    assert close == CLOSE_KEYS, f"`close` javobining maydonlari: {sorted(close)}"
    leaked = close & BLIND_FIELDS
    assert not leaked, f"⛔ D-25: `close` kontraktida sizib chiqqan maydonlar: {sorted(leaked)}"

    report = _property_names(_response_schema(spec, SHIFTS_URL, "get", "200"), spec)
    assert "system_soum" in report, (
        "⛔ SC#5(d): direktor hisobotida `system_soum` YO'Q — mezon o'lchanmay qoldi"
    )
    assert "variance_soum" in report, (
        "⛔ SC#5(d): direktor hisobotida `variance_soum` YO'Q — mezon o'lchanmay qoldi"
    )


async def test_the_close_request_does_not_accept_a_system_total(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ So'rov tanasida `system_soum` -> **422** (`extra="forbid"`).

    Maydonning MAVJUDLIGI o'zi «bu son klientda bor» degan taxminni
    kontraktga yozib qo'yardi va keyingi ijrochi uni to'ldiradigan `GET`
    marshrutini qidirardi.
    """
    response = await api_client.post(
        f"{SHIFTS_URL}/{env.seed_shift_id}/close",
        json={"declared_soum": 1_000, "system_soum": 999},
        headers=cashier_headers,
    )

    assert response.status_code == 422, response.text
    assert env.shift(env.seed_shift_id)[0] == "open", "rad etilgan so'rov smenani yopib qo'ydi"


async def test_a_zero_declaration_is_accepted(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ `declared_soum = 0` O'TADI (§10.2) — butun smena terminal bo'lgan kun.

    `> 0` sharti kassirni SOXTA naqd summa yozishga majburlardi va
    deklaratsiyaning butun ishonchliligini yo'qotardi.
    """
    response = await _close(api_client, cashier_headers, env.seed_shift_id, 0)

    assert response.status_code == 200, response.text
    assert response.json()["declared_soum"] == 0
    assert env.shift(env.seed_shift_id)[1] == 0


async def test_a_negative_declaration_is_rejected(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Manfiy naqd -> **422** (chegara `ge=0`), smena OCHIQ qoladi."""
    response = await _close(api_client, cashier_headers, env.seed_shift_id, -1)

    assert response.status_code == 422, response.text
    assert env.shift(env.seed_shift_id)[0] == "open"


async def test_closing_a_shift_twice_is_rejected_and_the_declaration_is_untouched(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ D-25: ikkinchi `close` -> **409**, qator BAYT-BAYT o'zgarmagan.

    ⛔ IKKI DA'VO BIRGA VA IKKINCHISI MUHIMROQ: faqat 409 ni tekshirish
       «javob rad etildi, lekin qator baribir o'zgardi» holatini o'tkazib
       yuborardi — o'shanda variance JIMGINA boshqa songa aylanardi va
       hisobot uni «hammasi joyida» deb ko'rsatardi.
    """
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)

    first = await _close(api_client, cashier_headers, env.seed_shift_id, 100_000)
    assert first.status_code == 200, first.text
    before = env.shift(env.seed_shift_id)

    second = await _close(api_client, cashier_headers, env.seed_shift_id, 999_999)
    assert second.status_code == 409, second.text
    assert _detail(second) == "shift_already_closed"

    assert env.shift(env.seed_shift_id) == before, (
        "⛔ D-25: rad etilgan ikkinchi `close` qatorni O'ZGARTIRDI"
    )


async def test_closing_another_cashiers_shift_is_forbidden(
    api_client: httpx.AsyncClient, env: Env, admin_headers: dict[str, str]
) -> None:
    """Begona KASSIRNING smenasi -> **403** (⛔ 404 emas, T-06-62).

    ⛔ 404 BU YERDA YOLG'ON BO'LARDI: qator so'rovchining O'Z bozorida va
       RLS undan o'tkazdi. 403 esa hech qanday yangi ma'lumot oshkor
       qilmaydi — begona BOZOR ning smenasi baribir 404 beradi (quyidagi
       matritsa da'vosi).
    """
    response = await _close(api_client, admin_headers, env.seed_shift_id, 50_000)

    assert response.status_code == 403, response.text
    assert env.shift(env.seed_shift_id)[0] == "open", "403 dan keyin smena YOPILGAN"


async def test_closing_an_unknown_shift_returns_404(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """Mavjud bo'lmagan `shift_id` -> **404** (T-01-76 bilan bir xil javob)."""
    response = await _close(api_client, cashier_headers, uuid4(), 50_000)

    assert response.status_code == 404, response.text
    assert _detail(response) == "not_found"


# ===========================================================================
# 3. ⛔⛔ SC#5(d) — VARIANCE IKKI TOMONLAMA (D-26)
# ===========================================================================


async def test_the_variance_is_returned_in_both_directions_and_zero_when_equal(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """⛔⛔ SC#5(d): `<`, `>` VA `==` — UCHALASI BITTA testda.

    =======================================================================
    ⛔ `declared > system` (ORTIQCHA) HOLATI ENG MUHIMI VA U ALOHIDA
       ASSERT BILAN: D-26 ning so'zma-so'z talabi — «ortiqcha naqd ham
       signal, uni jimgina yutish kamomadni yashirish bilan BIR XIL
       xato». Faqat kamomadni o'lchagan test `abs()` sabotajidan
       O'TARDI (musbat farq ham manfiyga aylanardi-yu, kamomad testi
       yashil qolardi).

    ⛔ UCHALA QIYMAT HAM NOLDAN FARQLI KATTALIKDA (5 000 va 7 000, teng
       emas): agar ikkala farq bir xil kattalikda bo'lsa `abs()`
       sabotaji ikkala qatorni ham bir xil songa aylantirib, farqni
       KO'RSATMASDAN qolardi (05-15 ning S-D darsi: da'vo susaytirilmaydi,
       HOLAT toraytiriladi).
    =======================================================================

    ⚠ VARIANCE `GET /shifts?day=` DAN O'QILADI, `close` JAVOBIDAN EMAS
      (UI-SPEC §10.4) — modul docstringidagi mezon bandi.
    """
    system = TARIFF_SOUM * 2

    # (a) KAMOMAD: declared < system.
    shortfall_shift = env.seed_shift_id
    env.pay(shift_id=shortfall_shift, amount_soum=system)
    await _close_ok(api_client, cashier_headers, shortfall_shift, system - 5_000)

    # (b) ORTIQCHA: declared > system.
    surplus_shift = env.open_shift_row()
    env.pay(shift_id=surplus_shift, amount_soum=system)
    await _close_ok(api_client, cashier_headers, surplus_shift, system + 7_000)

    # (c) MOS KELDI: declared == system.
    exact_shift = env.open_shift_row()
    env.pay(shift_id=exact_shift, amount_soum=system)
    await _close_ok(api_client, cashier_headers, exact_shift, system)

    report = await _report(api_client, director_headers, env.today)
    by_id = {row["id"]: row for row in report["rows"]}

    shortfall = by_id[str(shortfall_shift)]
    assert shortfall["variance_soum"] == -5_000, (
        f"⛔ KAMOMAD manfiy bo'lishi SHART (D-26): {shortfall}"
    )
    assert shortfall["system_soum"] == system

    surplus = by_id[str(surplus_shift)]
    assert surplus["variance_soum"] == 7_000, (
        f"⛔ SC#5(d): `declared > system` holati QAYTARILISHI shart va MUSBAT "
        f"bo'lishi shart — jim yutish D-26 ni buzadi: {surplus}"
    )

    assert by_id[str(exact_shift)]["variance_soum"] == 0


async def test_a_reversal_lowers_the_system_total_and_shows_up_as_a_surplus(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """Storno tizim summasini KAMAYTIRADI (C-5: belgi `kind` dan).

    ⚠ Bu SC#5(d) ning `>` shoxini IKKINCHI, MUSTAQIL yo'ldan takrorlaydi:
      u yerda ortiqcha DEKLARATSIYADAN tug'ildi, bu yerda esa TIZIM
      SUMMASINING kamayishidan. Ikkalasi ham bir xil natijani berishi
      shart — aks holda belgi qoidasi ikki joyda ajralib ketgan bo'lardi.
    """
    payment_id = env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)
    env.reverse(shift_id=env.seed_shift_id, payment_id=payment_id, amount_soum=TARIFF_SOUM)

    response = await _close(api_client, cashier_headers, env.seed_shift_id, TARIFF_SOUM)
    assert response.status_code == 200, response.text

    report = await _report(api_client, director_headers, env.today)
    row = next(item for item in report["rows"] if item["id"] == str(env.seed_shift_id))

    assert row["system_soum"] == 0, f"storno tizim summasidan AYIRILMADI: {row}"
    assert row["variance_soum"] == TARIFF_SOUM


async def test_the_report_row_has_exactly_seven_keys_and_no_cashier_name(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """C-10: javobda `cashier_id` BOR, ⛔ ISM YO'Q — TO'PLAM TENGLIGI bilan.

    ⛔ `not in` YETARLI EMAS: `cashier_label`/`who` kabi nom bilan
       aylanib o'tish jimgina o'tib ketardi (C-10 buni ochiq taqiqlaydi).
    """
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)
    await _close_ok(api_client, cashier_headers, env.seed_shift_id, TARIFF_SOUM)

    report = await _report(api_client, director_headers, env.today)

    assert set(report) == {"day", "rows", "shiftless_payment_count", "shiftless_payment_soum"}
    row = report["rows"][0]
    assert set(row) == REPORT_ROW_KEYS, f"§11.5 jadvalining kalitlari: {sorted(row)}"
    assert not set(row) & PERSONAL_FIELDS, f"⛔ C-10: shaxsiy maydon sizib chiqdi: {sorted(row)}"
    assert row["cashier_id"] == str(env.cashier_id)


async def test_an_overnight_shift_is_reported_under_the_day_it_was_opened(
    api_client: httpx.AsyncClient,
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ WR-07: hisobotning KUNI — smena OCHILGAN kun, YOPILGAN kun EMAS.

    =========================================================================
    ⛔⛔ TA'RIF ENDI PROZA EMAS, TASDIQ.

    `_SHIFT_REPORT_ROWS` `cashier_shifts.business_date` bo'yicha
    filtrlaydi va u `GENERATED ALWAYS AS (...)` — yagona kirishi
    `created_at`, ya'ni ⛔ QATOR YOZILGAN (= smena OCHILGAN) lahza.
    Docstring esa «qaysi kunda kassa hisobi olindi» deb turardi va bu
    NOTO'G'RI edi: kassa hisobi smena YOPILGANDA olinadi (`closed_at`).

    Toshkent yarim tunidan oshgan smena uchun ikkalasi AJRALADI. Bu
    test o'sha holatni AYNAN quradi va ta'rifni QULFLAYDI:

        `created_at` = KECHA   -> `business_date` = KECHA
        `closed_at`  = BUGUN

    ⛔ IKKI TOMONLAMA DA'VO: qator KECHAGI hisobotda BOR va BUGUNGISIDA
       YO'Q. Faqat birinchisi yozilsa filtr `closed_at` ga o'tkazilganda
       test YASHIL qolardi (qator ikkala kunda ham topilardi degan
       taxmin bilan) — ikkinchi yarim aynan shu shoxni yopadi.

    ⚠ QATOR XOM `INSERT` BILAN YOZILADI va bu MAJBURIY: `business_date`
      GENERATED, ya'ni unga qiymat yozib bo'lmaydi va uni faqat
      `created_at` orqali siljitish mumkin. HTTP marshruti esa har doim
      `now()` beradi — tungi holatni mahsulot yo'lidan qurish IMKONSIZ.

    ⚠ Smena YOPIQ holatda yoziladi: `closed_has_declaration` /
      `closed_has_system_total` `CHECK` lari ikkala summani TALAB qiladi,
      qisman `SHIFT_OPEN_INDEX` esa faqat OCHIQ qatorlarni qamraydi —
      ya'ni seedning ochiq smenasi bilan to'qnashuv yo'q.
    =========================================================================
    """
    yesterday = env.today - timedelta(days=1)
    overnight_id = uuid4()
    env.conn.execute(
        "INSERT INTO cashier_shifts "
        "(id, market_id, cashier_id, status, opened_at, closed_at, "
        " declared_soum, system_soum, created_at) "
        "VALUES (%s, %s, %s, %s, "
        "        (%s::date + time '23:30') AT TIME ZONE 'Asia/Tashkent', "
        "        (%s::date + time '00:30') AT TIME ZONE 'Asia/Tashkent', "
        "        %s, %s, "
        "        (%s::date + time '23:30') AT TIME ZONE 'Asia/Tashkent')",
        (
            str(overnight_id),
            str(env.market_id),
            str(env.cashier_id),
            ShiftStatus.CLOSED.value,
            yesterday,
            env.today,
            0,
            0,
            yesterday,
        ),
    )

    # ⛔ NAZORAT: holat HAQIQATAN tungi — ikki ustun ikki BOSHQA kunni ko'rsatadi.
    row = env.conn.execute(
        "SELECT business_date, (closed_at AT TIME ZONE 'Asia/Tashkent')::date "
        "FROM cashier_shifts WHERE id = %s",
        (str(overnight_id),),
    ).fetchone()
    assert row is not None
    assert (row[0], row[1]) == (yesterday, env.today), (
        f"nazorat: tungi holat qurilmadi — business_date={row[0]}, closed={row[1]}"
    )

    on_open_day = await _report(api_client, director_headers, yesterday)
    on_close_day = await _report(api_client, director_headers, env.today)

    assert str(overnight_id) in {r["id"] for r in on_open_day["rows"]}, (
        "tungi smena OCHILGAN kunning hisobotida YO'Q — kun ta'rifi o'zgargan"
    )
    assert str(overnight_id) not in {r["id"] for r in on_close_day["rows"]}, (
        "tungi smena YOPILGAN kunda ham ko'rindi — filtr `closed_at` ga o'tkazilgan"
    )


async def test_an_open_shift_is_not_in_the_report(
    api_client: httpx.AsyncClient, env: Env, director_headers: dict[str, str]
) -> None:
    """⛔ FAQAT YOPILGAN smenalar: ochiq smenaning variance i MA'NOSIZ.

    Uni «0 farq» deb ko'rsatish `NULL` ni nol deb yozish bo'lardi —
    D-14 ning aynan taqiqlaydigan narsasi.
    """
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)

    report = await _report(api_client, director_headers, env.today)

    assert report["rows"] == [], f"ochiq smena hisobotga tushdi: {report['rows']}"


async def test_the_cashier_cannot_read_the_variance_report(
    api_client: httpx.AsyncClient, env: Env, cashier_headers: dict[str, str]
) -> None:
    """⛔ UI-SPEC §10.4 ning HUQUQ darajasidagi yarmi — kassirga **403**.

    `system = declared − variance` — bitta ayirish, ya'ni bu marshrutga
    kirish D-25 ni ⛔ BITTA SO'ROV bilan bekor qilardi. Kassirda
    `report_view` YO'Q va bu STRUKTURAVIY holat, kod-ko'rik da'vosi emas.
    """
    response = await api_client.get(SHIFTS_URL, headers=cashier_headers)

    assert response.status_code == 403, response.text


async def test_a_future_day_is_rejected(
    api_client: httpx.AsyncClient, env: Env, director_headers: dict[str, str]
) -> None:
    """Kelajak kuni -> **422**: kelajakda yopilgan smena MAVJUD EMAS."""
    tomorrow = env.today + timedelta(days=1)

    response = await api_client.get(
        SHIFTS_URL, params={"day": tomorrow.isoformat()}, headers=director_headers
    )

    assert response.status_code == 422, response.text
    assert _detail(response) == "day_in_future"


# ===========================================================================
# 4. ⛔⛔ §11.5 FLAG — SMENASIZ TO'LOVLAR (OQ-6/A5)
# ===========================================================================


async def test_shiftless_payments_are_counted_separately_and_stay_out_of_the_variance(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """⛔⛔ §11.5: `shift_id IS NULL` to'lovi KO'RINADI, lekin variance ga KIRMAYDI.

    =======================================================================
    ⛔ IKKALA YARIM HAM O'LCHANADI VA BIRI IKKINCHISINI ALMASHTIRMAYDI:

      (a) `shiftless_payment_count`/`_soum` — ular JIMGINA YO'QOLMAYDI;
      (b) smenaning `system_soum` i ularni O'Z ICHIGA OLMAYDI — ular
          kassir qutisiga tushmagan.

    Faqat (a) bo'lsa, agregat to'g'ri-yu, o'sha pul smenaning tizim
    summasiga ham qo'shilib IKKI MARTA sanalishi mumkin bo'lardi va
    variance sababsiz manfiy chiqardi.
    =======================================================================
    """
    shiftless_soum = 33_000
    env.pay(shift_id=None, amount_soum=shiftless_soum)
    env.pay(shift_id=env.seed_shift_id, amount_soum=TARIFF_SOUM)

    await _close_ok(api_client, cashier_headers, env.seed_shift_id, TARIFF_SOUM)

    report = await _report(api_client, director_headers, env.today)

    assert report["shiftless_payment_count"] == 1, report
    assert report["shiftless_payment_soum"] == shiftless_soum, report

    row = next(item for item in report["rows"] if item["id"] == str(env.seed_shift_id))
    assert row["system_soum"] == TARIFF_SOUM, (
        f"⛔ smenasiz to'lov smenaning tizim summasiga QO'SHILDI: {row}"
    )
    assert row["variance_soum"] == 0


async def test_an_empty_day_still_returns_all_three_fields(
    api_client: httpx.AsyncClient, env: Env, director_headers: dict[str, str]
) -> None:
    """⛔ NOL — NATIJA: smena yo'q kunda ham uchala maydon QAYTADI.

    «Bu kunda smena yo'q» bilan «hisoblagich ishlamayapti» bir xil
    ko'rinmasligi kerak — `occupancy.py:122-124` prinsipi.
    """
    quiet_day = env.today - timedelta(days=3)

    report = await _report(api_client, director_headers, quiet_day)

    assert report["day"] == quiet_day.isoformat()
    assert report["rows"] == []
    assert report["shiftless_payment_count"] == 0
    assert report["shiftless_payment_soum"] == 0
