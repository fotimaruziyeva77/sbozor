"""Majburiy xizmat haqi (tarozi) + kassir ro'yxati — 0027 ning yuzalari.

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI — SUMMANING YO'QLIGI.

`GET /billing/collect-roster` kassirga BUTUN bozorning ro'yxatini beradi.
`GET /payments/recent` esa ATAYIN beshta qator bilan chegaralangan —
kassir yig'indini qo'shib chiqara olmasin (D-25/D-26, ko'r smena sanog'i).

Agar ro'yxatga summa qo'shilsa o'sha chegaralashning butun ma'nosi
yo'qolardi: kassir jamini o'zi hisoblab, smena yopishda AYNAN o'sha sonni
yozardi va direktor ko'radigan FARQ har doim nol bo'lardi.

Shuning uchun bu yerda da'vo TO'PLAM TENGLIGI bilan o'lchanadi (D-31),
inkor tasdiq bilan EMAS: `assert "amount_soum" not in row` faqat AYNAN
o'sha nomni ushlardi va `amountSoum`, `total`, `sum` jimgina o'tib
ketardi.

=============================================================================
⛔ IKKINCHI DA'VO — XIZMAT HAQI HISOBGA HAQIQATAN QO'SHILADI.

Mexanizmning yashilligi (ustun bor, CHECK bor) «summa to'g'ri» degani
EMAS. Shuning uchun bu yerda HTTP javobidagi uchta son bir-biriga
solishtiriladi: `stall_amount_soum + fee_amount_soum == amount_soum`.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    DAY_TOTAL_SOUM,
    TARIFF_SOUM,
    billing_domain_before_day_close,
)
from fixtures.market_domain import (
    A_SERVICE_FEE_LABEL,
    A_SERVICE_FEE_SOUM,
    MarketDomainSeed,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.anyio

ROSTER_URL = "/api/v1/billing/collect-roster"
PENDING_URL = "/api/v1/billing/pending"
FEES_URL = "/api/v1/service-fees"

ROSTER_ROW_KEYS = frozenset({"stall_code", "vendor_assigned", "paid_at"})
"""⛔ RO'YXAT QATORINING AYNAN UCH KALITI — QO'LDA YOZILGAN.

Reyestrni javobdan yoki mahsulot modelidan hosila qilish testni «model
o'ziga teng» degan tavtologiyaga aylantirardi: maydon qo'shgan odam
ikkala tomonni bir vaqtda o'zgartirardi va darvoza qizarmasdi (05-15 da
o'rnatilgan qoida).

⛔ `amount_soum` · `paid_soum` · `outstanding_soum` — uchalasi ham bu
   yerda YO'Q va yo'qligi TO'PLAM TENGLIGI bilan qo'riqlanadi.
"""

ROSTER_BODY_KEYS = frozenset(
    {
        "service_date",
        "state",
        "rows",
        "total",
        "page",
        "per_page",
        "page_count",
        "paid_count",
        "unpaid_count",
        "unassigned_count",
        "fetched_at",
    }
)


class Env:
    """`test_billing_api.py::Env` ning tor nusxasi — faqat kerakli maydonlar."""

    def __init__(
        self,
        billing: Any,
        domain: MarketDomainSeed,
        base: TwoMarketSeed,
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base

    @property
    def market_id(self) -> UUID:
        return self.base.market_a.id

    def stall(self, name: str) -> UUID:
        stall_id: UUID | None = getattr(self.billing.market_a, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        try:
            yield Env(billing, market_domain, two_markets)
        finally:
            # ⛔⛔ HTTP ORQALI YOZILGAN QATORLAR SHU YERDA O'CHIRILADI.
            #
            #   Testlar `POST /payments` bilan qator yozadi va seed
            #   ularning identifikatorlarini BILMAYDI — tozalash
            #   `market_id` bo'yicha ketadi.
            #
            #   `notification_outbox` MAJBURIY: `POST /payments` ning
            #   6.5-qadami (CASH-05) har to'lov uchun kvitansiya
            #   niyatini ham yozadi, `fk_notification_outbox_vendor` da
            #   esa `ondelete` YO'Q. Qoldiq qator sotuvchi/bozor
            #   `DELETE` ini FK buzilishi bilan yiqitardi va nosozlik
            #   BU faylda emas, KEYINGI faylning seed'ida ko'rinardi
            #   (`test_payments_api.py:313` da o'lchangan).
            market_id = two_markets.market_a.id
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (str(market_id),))
            sync_owner_conn.execute(
                "DELETE FROM market_service_fees WHERE market_id = %s AND valid_from > %s",
                (str(market_id), "2098-12-31"),
            )
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),)
            )


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    market_a = env.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


def _stall_code(conn: Connection[TupleRow], stall_id: UUID) -> str:
    row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(stall_id),)).fetchone()
    assert row is not None, "nazorat: rasta bazada yo'q"
    return str(row[0])


# ===========================================================================
# 1. XIZMAT HAQI KUNLIK PATTAGA QO'SHILADI
# ===========================================================================


async def test_the_pending_payload_splits_the_day_amount_into_two_components(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ UCHTA SON BIR-BIRIGA SOLISHTIRILADI — mexanizm emas, NATIJA.

    «Ustun bor va CHECK bor» degan da'vo summaning TO'G'RILIGINI
    isbotlamaydi. Bu yerda HTTP javobining o'zidan o'qilgan uch son
    tekshiriladi va ular seed konstantalari bilan langarlanadi.
    """
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    response = await api_client.get(
        PENDING_URL, params={"stall_code": code}, headers=cashier_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["stall_amount_soum"] == TARIFF_SOUM, "rasta puli tarifdan kelmadi"
    assert body["fee_amount_soum"] == A_SERVICE_FEE_SOUM, "xizmat haqi qo'shilmadi"
    assert body["amount_soum"] == DAY_TOTAL_SOUM, "yig'indi ikki komponentga teng emas"
    assert body["stall_amount_soum"] + body["fee_amount_soum"] == body["amount_soum"], (
        "komponentlar yig'indiga teng emas — klient noto'g'ri summa yuborardi"
    )

    assert body["fee_label"] == A_SERVICE_FEE_LABEL, (
        "nom SERVERDAN kelishi shart — u bozor kiritgan matn va klient uni qotirib qo'ymaydi"
    )


async def test_paying_only_the_stall_part_needs_no_reason_code(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔⛔ TAROZI BELGISINI OLIB TASHLASH — NORMAL YO'L, ISTISNO EMAS.

    =======================================================================
    Buyurtmachi qarori: «agar belgilanmasa faqat rastani pulini tulasa
    tarozi puli qoldi deb chiqadi».

    Agar `today − fee` summasi `payment_quote_set()` takliflariga
    KIRMASA, server uni «asossiz» deb ko'rib 422 `reason_required`
    berardi — ya'ni kuniga yuzlab marta takrorlanadigan harakat DL-1
    override dialogidan o'tardi.

    ⚠ SABOTAJ: `payments.py` dagi uchinchi argumentni (`money.
      fee_amount_soum or 0`) olib tashlang — bu test 422 bilan qizaradi,
      qo'shnilari esa YASHIL qoladi.
    =======================================================================
    """
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    response = await api_client.post(
        "/api/v1/payments",
        headers=cashier_headers,
        json={
            "stall_code": code,
            "amount_soum": TARIFF_SOUM,
            "method": "cash",
            "idempotency_key": "fee-off-0001",
        },
    )

    assert response.status_code == 201, (
        f"«faqat rasta puli» sabab kodisiz o'tmadi: {response.status_code} {response.text}"
    )
    body = response.json()
    assert body["amount_soum"] == TARIFF_SOUM

    # ⛔ `quote_soum` JAVOBDA YO'Q (D-20 — u ichki qaror), shuning uchun
    #   «server buni O'Z taklifi deb tanidimi?» savoli AUDITDAN
    #   o'lchanadi: override bo'lganda `payment_override` qatori
    #   yozilardi. Uning YO'QLIGI — da'voning ikkinchi yarmi.
    override_rows = sync_owner_conn.execute(
        "SELECT count(*) FROM audit_log WHERE market_id = %s AND action = 'payment_override'",
        (str(env.market_id),),
    ).fetchone()
    assert override_rows is not None and override_rows[0] == 0, (
        "«faqat rasta puli» override sifatida yozilgan — u server taklifi bo'lishi kerak edi"
    )


# ===========================================================================
# 2. KASSIR RO'YXATI — SUMMASIZ
# ===========================================================================


async def test_the_roster_row_never_carries_a_money_field(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔⛔ KO'R SMENA SANOG'I — TO'PLAM TENGLIGI BILAN (D-25/D-26, D-31)."""
    response = await api_client.get(ROSTER_URL, params={"state": "unpaid"}, headers=cashier_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body) == ROSTER_BODY_KEYS, f"javob kalitlari kutilgandan farq qiladi: {sorted(body)}"
    assert body["rows"], "nazorat: seedda to'lanmagan rasta yo'q — test bo'sh o'lchardi"

    for row in body["rows"]:
        assert set(row) == ROSTER_ROW_KEYS, (
            f"⛔ qator kalitlari to'plami buzilgan: {sorted(row)} — summa "
            "maydoni ko'r sanoqni bekor qilardi"
        )


async def test_a_payment_moves_the_stall_between_the_two_lists(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """To'lov rastani «to'lanmagan» dan «to'langan» ga KO'CHIRADI va sanoq suriladi."""
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    before = (
        await api_client.get(ROSTER_URL, params={"state": "unpaid"}, headers=cashier_headers)
    ).json()

    paid = await api_client.post(
        "/api/v1/payments",
        headers=cashier_headers,
        json={
            "stall_code": code,
            "amount_soum": DAY_TOTAL_SOUM,
            "method": "cash",
            "idempotency_key": "roster-move-0001",
        },
    )
    assert paid.status_code == 201, paid.text

    after_unpaid = (
        await api_client.get(ROSTER_URL, params={"state": "unpaid"}, headers=cashier_headers)
    ).json()
    after_paid = (
        await api_client.get(ROSTER_URL, params={"state": "paid"}, headers=cashier_headers)
    ).json()

    assert after_unpaid["unpaid_count"] == before["unpaid_count"] - 1, (
        "to'lovdan keyin to'lanmaganlar soni kamaymadi"
    )
    assert code not in {row["stall_code"] for row in after_unpaid["rows"]}
    assert code in {row["stall_code"] for row in after_paid["rows"]}

    row = next(item for item in after_paid["rows"] if item["stall_code"] == code)
    assert row["paid_at"] is not None, "to'langan qatorda vaqt tamg'asi yo'q"

    # ⛔ IKKALA SANOQ HAM HAR IKKALA JAVOBDA — klient ikkinchi so'rov
    #   yubormasdan «12 / 38» yozuvini chizadi.
    assert after_unpaid["paid_count"] == after_paid["paid_count"]
    assert after_unpaid["unpaid_count"] == after_paid["unpaid_count"]
    assert after_unpaid["unassigned_count"] == after_paid["unassigned_count"]


async def test_an_empty_page_still_reports_one_page(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ `page_count` NOL BO'LMAYDI — nol klientda sahifa raqamlarini yo'qotardi."""
    response = await api_client.get(ROSTER_URL, params={"state": "paid"}, headers=cashier_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["total"] == 0, "nazorat: seedda hali to'lov yo'q edi"
    assert body["rows"] == []
    assert body["page_count"] == 1, (
        "bo'sh to'plamda ham BITTA sahifa qaytadi — `0` «yuklanmadi» bilan «bo'sh» ni ajratmasdi"
    )


async def test_the_roster_is_closed_to_a_role_without_the_collect_permission(
    api_client: httpx.AsyncClient,
    env: Env,
    two_markets: TwoMarketSeed,
) -> None:
    """`billing_collect_view` yo'q rol — 403.

    ⚠ NISHON — PLATFORMA ADMINI: `rbac.py` ga ko'ra unda
      `billing_collect_view` YO'Q (u bozorlararo rol va unga bozor
      ichidagi pul yuzasi berilmaydi). Kassir/admin/direktorda esa BOR.

    ⚠ Bozor tanlanmagan sessiyada javob 403 bo'ladi va bu AYNI natija:
      ikkala shox ham «bu yuza bu rolga ochilmaydi» deydi.
    """
    headers = await session_headers(
        api_client,
        two_markets.platform_admin_phone,
        SEED_PASSWORD,
    )
    response = await api_client.get(ROSTER_URL, headers=headers)
    assert response.status_code == 403, response.text


async def test_the_director_sees_the_same_roster_as_the_cashier(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """`billing_collect_view` UCH ROLDA — direktor ham o'sha ro'yxatni ko'radi."""
    cashier = (await api_client.get(ROSTER_URL, headers=cashier_headers)).json()
    director = (await api_client.get(ROSTER_URL, headers=director_headers)).json()

    assert cashier["unpaid_count"] == director["unpaid_count"]
    assert [row["stall_code"] for row in cashier["rows"]] == [
        row["stall_code"] for row in director["rows"]
    ]


# ===========================================================================
# 3. XIZMAT HAQI REYESTRI (`/service-fees`)
# ===========================================================================


async def test_the_fee_registry_reports_the_current_value_and_its_history(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Seed qatori tarixda ham, «hozirgi qiymat» da ham ko'rinadi."""
    response = await api_client.get(FEES_URL, headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["current_amount_soum"] == A_SERVICE_FEE_SOUM
    assert body["current_label"] == A_SERVICE_FEE_LABEL
    assert len(body["items"]) == 1, f"seedda bitta qator kutilgan edi: {body['items']}"
    assert body["items"][0]["is_past"] is True, (
        "`valid_from` `operating_since` (o'tmish) — qator o'tgan deb belgilanishi shart"
    )


async def test_a_cashier_cannot_read_the_fee_registry(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ KASSIRDA `MARKET_DATA_VIEW` YO'Q (C-10) — u narx reyestrini ko'rmaydi.

    Xizmat haqi unga `GET /billing/pending` javobidagi `fee_amount_soum`
    orqali yetadi, ya'ni u SUMMANI biladi-yu, REYESTRNI ko'rmaydi.
    """
    response = await api_client.get(FEES_URL, headers=cashier_headers)
    assert response.status_code == 403, response.text


async def test_a_blank_label_is_rejected_before_it_reaches_the_database(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ FAQAT BO'SHLIQDAN IBORAT NOM — 422, DB'dagi `23514` EMAS.

    Pydantic `min_length=1` bo'shliqni QIRQMAYDI, ya'ni `"   "` undan
    o'tib DB cheklоviga urilardi va admin 403/500 ko'rardi. Marshrut uni
    `strip()` bilan tutadi.
    """
    response = await api_client.post(
        FEES_URL,
        headers=admin_headers,
        json={"amount_soum": 1_000, "label": "   ", "valid_from": "2099-01-01"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "service_fee_label_blank"


async def test_a_zero_fee_is_a_legitimate_value(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ `0` — «bu bozorda xizmat haqi olinmaydi», XATO EMAS.

    `amount_soum > 0` shartini majburlash har bozorni soxta «1 so'm»
    yozishga undardi.
    """
    response = await api_client.post(
        FEES_URL,
        headers=admin_headers,
        json={"amount_soum": 0, "label": "Tarozi yo'q", "valid_from": "2099-01-01"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["amount_soum"] == 0


async def test_a_director_cannot_write_a_fee(
    api_client: httpx.AsyncClient,
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ `TARIFF_MANAGE` direktorda YO'Q (D-07) — u narx yozmaydi, KO'RADI."""
    read = await api_client.get(FEES_URL, headers=director_headers)
    assert read.status_code == 200, "direktor reyestrni O'QIY oladi"

    write = await api_client.post(
        FEES_URL,
        headers=director_headers,
        json={"amount_soum": 5_000, "label": "Tarozi", "valid_from": "2099-01-01"},
    )
    assert write.status_code == 403, write.text


async def test_stalls_without_a_vendor_are_counted_apart_from_the_unpaid_ones(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔⛔ SOTUVCHISIZ RASTA «TO'LANMAGAN» HISOBIGA KIRMAYDI (O'-01 auditi).

    =======================================================================
    Ulardan patta olib BO'LMAYDI: `POST /payments` ularga 409
    `stall_not_assigned` beradi. «To'lanmagan» hisobiga qo'shilsa kassir
    har kuni BAJARIB BO'LMAYDIGAN reja bilan qolardi — auditda o'lchangan
    holat: 36 tadan 10 tasi shunday edi.

    ⛔ ULAR RO'YXATDAN OLIB TASHLANMAYDI, AJRATILADI: sotuvchisiz band
       rasta — mahsulot fosh qiladigan anomaliya («ro'yxatga olinmagan
       savdo»), uni yashirish signalni o'chirardi.

    ⚠ SABOTAJ: `billing_repo.collect_roster()` da `elif assigned:`
      shoxini olib tashlang — `unassigned_count` nolga tushadi va bu
      test qizaradi, qo'shnilari YASHIL qoladi.
    =======================================================================
    """
    unpaid = (
        await api_client.get(ROSTER_URL, params={"state": "unpaid"}, headers=cashier_headers)
    ).json()
    unassigned = (
        await api_client.get(ROSTER_URL, params={"state": "unassigned"}, headers=cashier_headers)
    ).json()

    assert unassigned["unassigned_count"] > 0, (
        "nazorat: seedda sotuvchisiz rasta yo'q — test bo'sh o'lchardi"
    )
    assert unassigned["total"] == unassigned["unassigned_count"]

    # ⛔ IKKI TO'PLAM KESISHMAYDI — bu da'voning O'ZAGI.
    unpaid_codes = {row["stall_code"] for row in unpaid["rows"]}
    unassigned_codes = {row["stall_code"] for row in unassigned["rows"]}
    assert unpaid_codes.isdisjoint(unassigned_codes), (
        f"rasta ikkala ro'yxatda ham bor: {sorted(unpaid_codes & unassigned_codes)}"
    )

    # «To'lanmagan» ro'yxatidagi HAR qatorda sotuvchi BOR.
    assert all(row["vendor_assigned"] for row in unpaid["rows"]), (
        "sotuvchisiz rasta «to'lanmagan» ro'yxatiga sizib o'tdi"
    )
    assert not any(row["vendor_assigned"] for row in unassigned["rows"])


# ===========================================================================
# 4. YARMARKA (0028) — patta ATAYIN olinmaydigan rasta
# ===========================================================================


async def test_a_fair_stall_is_named_not_billed_and_left_out_of_the_roster(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔⛔ YARMARKA UCH YUZADA BIR XIL GAPIRADI (0028).

    =======================================================================
    Bitta holat uch joyda ko'rinadi va uchalasi BIR MANBADAN kelishi
    shart (`resolve_stall_day_money()`):

      1. `GET /billing/pending`  -> `amount_soum = null`, sabab `fair_stall`
                                    («tarif yo'q» EMAS — bu QAROR, nuqson emas);
      2. kassir ro'yxati         -> rasta UCHALA bo'limda ham YO'Q
                                    (undan bugun hech nima kutilmaydi);
      3. `GET /billing/map`      -> holat `fair` (teal), `no_billing` EMAS.

    ⚠ SABOTAJ: `_money_from_row()` dagi `elif status == "fair"` shoxini
      olib tashlang — (1) `tariff_missing` ga aylanadi va bu test
      qizaradi; xarita esa yarmarkani «ma'lumot yo'q» kulrangida
      ko'rsatib qo'yadi.
    =======================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = _stall_code(sync_owner_conn, stall_id)

    sync_owner_conn.execute("UPDATE stalls SET status = 'fair' WHERE id = %s", (str(stall_id),))
    try:
        # (1) proyeksiya — nomlangan sabab
        pending = (
            await api_client.get(PENDING_URL, params={"stall_code": code}, headers=cashier_headers)
        ).json()
        assert pending["amount_soum"] is None
        assert pending["amount_unavailable_reason"] == "fair_stall", (
            f"kutilgan `fair_stall`, keldi: {pending['amount_unavailable_reason']!r}"
        )
        assert pending["stall_status"] == "fair"

        # (2) ro'yxat — rasta hech qaysi bo'limda yo'q
        for state in ("unpaid", "paid", "unassigned"):
            body = (
                await api_client.get(ROSTER_URL, params={"state": state}, headers=cashier_headers)
            ).json()
            assert code not in {row["stall_code"] for row in body["rows"]}, (
                f"yarmarka rastasi {state!r} ro'yxatiga tushib qoldi"
            )

        # (3) xarita — teal holat
        map_body = (await api_client.get("/api/v1/billing/map", headers=cashier_headers)).json()
        row = next(item for item in map_body["rows"] if item["stall_id"] == str(stall_id))
        assert row["state"] == "fair", (
            f"xarita holati {row['state']!r} — `fair` kutilgan edi (0028)"
        )
    finally:
        sync_owner_conn.execute(
            "UPDATE stalls SET status = 'active' WHERE id = %s", (str(stall_id),)
        )
