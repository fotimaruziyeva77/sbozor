"""`GET /reconciliation/delivery` — «XABAR BORDIMI?» SAVOLINING YUZASI (BOT-04).

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI — ⛔ **XABARNING O'ZI JAVOBDA YO'Q**.

Navbat qatorida `payload` bor va unda ⛔ **summa va rasta kodi** yotibdi;
`dedupe_key` esa ⛔ **to'lov identifikatorini** tashiydi. Ikkalasi ham
ekranga chiqishi «qulaylik» bo'lib boshlanardi va ⛔ **ikkinchi pul
yuzasi** bo'lib tugardi (07-UI-SPEC §11.3) — ya'ni direktor
yetkazilganlik jadvalidan summa qo'shib chiqara olardi va bu son
hisobotdagi son bilan ajralib ketardi.

Shuning uchun da'vo ⛔ **REKURSIV KALIT SKANI** bilan yoziladi, «javobda
`payload` bormi?» degan bitta tekshiruv bilan EMAS: birinchisi javob
shakli ichma-ich o'sganda ham (`rows[].meta.payload`) qizaradi.
=============================================================================

=============================================================================
⛔⛔ IKKINCHI DA'VO — ⛔ **YOZISH YUZASI UMUMAN YO'Q** (D-20, §17.2).

`POST /reconciliation/delivery/{id}/retry` va uning qardoshlari
⛔ **yozilmagan**, va bu fayl uni ⛔ **OpenAPI ustidan** o'lchaydi:
handler qo'shilgan zahoti spetsifikatsiyada metod paydo bo'ladi, ya'ni
taqiq INTIZOMGA emas, ⛔ **mexanizmga** tayanadi.

Uch mustaqil sabab (marshrutning docstringida ham yozilgan):
  1. outbox O'ZI qayta uradi (DQ-3 backoff);
  2. qo'lda yuborish `uq_notification_outbox_market_id_dedupe_key` bilan
     TO'QNASHARDI yoki uni aylanib o'tib IKKINCHI kvitansiya yuborardi;
  3. qo'lda `delivered` qo'yish nizoda (D-02) ⛔ **SOXTA DALIL** bo'lardi.
=============================================================================

⛔ BU FAYL `tests/integration/test_outbox.py` NI TAKRORLAMAYDI: u yerda
   jo'natuvchining xulqi (tik, backoff, quiet hours, terminal holatlar)
   o'lchanadi. Bu yerda faqat ⛔ **O'QISH CHEGARASI**: javob shakli,
   huquq, tenant chegarasi, keyset va OpenAPI.

⚠ SEED ZANJIRI ATAYIN QISQA (`two_markets` + `auth_seed` +
  `market_domain`): bu marshrut `daily_charges` ga ham,
  `stall_slot_occupancy` ga ham TEGMAYDI. Og'ir zanjirni ko'chirish
  testni sekinlashtirardi va nosozlik sababini yuzadan uzoqlashtirardi.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from app.main import app as fastapi_app
from fixtures.admin_api import session_headers
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import cleanup_notification_domain, seed_outbox_row
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import OutboxKind, OutboxStatus
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

DELIVERY_URL = "/api/v1/reconciliation/delivery"
"""Marshrutning yo'li — ⛔ HTTP so'rovi UCHUN HAM, OpenAPI SKANI uchun ham.

⚠ BITTA KONSTANTA: ikkinchi nusxa yozilganda ular ajralib ketardi va
  «yozish metodi yo'q» da'vosi MAVJUD BO'LMAGAN yo'l ustidan yugurib
  JIMGINA yashil qolardi.
"""

FORBIDDEN_KEYS = frozenset(
    {
        "payload",
        "chat_id",
        "telegram_user_id",
        "telegram_username",
        "text",
        "message",
        "body",
        "provider_message_id",
        "dedupe_key",
        "lease_until",
    }
)
"""⛔ JAVOBNING HECH BIR CHUQURLIGIDA UCHRAMASLIGI KERAK BO'LGAN KALITLAR.

Har biri O'Z sababi bilan (marshrut docstringi va `outbox_repo` ning
5-majburiyati):

  `payload` / `text` / `message` / `body` — xabarning MAZMUNI. Unda summa
      va rasta kodi bor; ekranda takrorlash IKKINCHI PUL YUZASI bo'lardi.
      Tayyor matn esa umuman SAQLANMAYDI (Pitfall 6) — ya'ni uning
      javobda paydo bo'lishi «kimdir matnni qatorga yozib qo'ydi» degan
      BIRINCHI belgi bo'lardi.
  `chat_id` / `telegram_user_id` / `telegram_username` — odamni TASHQI
      tizimda aniqlaydi (D-01) va `PERSONAL_FIELDS` darvozasi ularni
      USHLAMAYDI (07-UI-SPEC §5.5).
  `provider_message_id` — Telegram ning ICHKI identifikatori; direktorga
      hech nima aytmaydi.
  `dedupe_key` — `<kind>:<manba-id>` shaklida TO'LOV identifikatorini
      tashiydi.
  `lease_until` — ijara, ya'ni ichki qulf mexanizmi.

⚠ `text` / `message` / `body` seed'da MAVJUD EMAS va bu ATAYIN: da'vo
  «bugungi ustunlar» ni emas, ⛔ KELAJAKDAGI QO'SHIMCHANI qo'riqlaydi.
"""

ERROR_TYPE_FORBIDDEN = (" ", "http", "api.telegram.org", "/")
"""⛔ `last_error_type` QIYMATIDA uchramasligi kerak bo'lgan parchalar (D-04).

⚠ `"http"` BU YERDA TAQIQLANADI, `outbox_repo._ERROR_TYPE_FORBIDDEN` da
  esa YO'Q — va farq ATAYIN, ikki ro'yxat IKKI BOSHQA savolga javob
  beradi:

    repo ro'yxati — «bu qiymatni YOZISH mumkinmi?». U `HTTPStatusError`
        kabi QONUNIY sinf nomlarini o'tkazishi SHART (07-09 aynan shu
        nuqsonni tuzatgan: `"http"` fragmenti status xatolarini terminal
        holatga o'tishdan to'sib qo'ygan edi);

    bu ro'yxat — «bu qiymat EKRANGA chiqdimi va u xato MATNIGA
        o'xshaydimi?». Bu yerda seed ATAYIN `ConnectTimeout` yozadi,
        ya'ni da'vo o'z seedining ustidan yuguradi va `str(exc)`
        shaklidagi har qanday qiymatda qizaradi.

⛔ IKKI RO'YXATNI BIRLASHTIRISH TAQIQLANADI: birlashtirilgan ro'yxat yo
   07-09 ning tuzatishini QAYTARARDI (`HTTPStatusError` yana rad
   etilardi), yo bu yerdagi da'voni BO'SHASHTIRARDI.
"""

_SET_ERROR = (
    "UPDATE notification_outbox SET last_error_type = %s, last_status_code = %s WHERE id = %s"
)
"""Terminal qatorning xato TURI — ⛔ XOM SQL SHU MODULDA.

`seed_outbox_row()` bu ikki ustunni bilmaydi (u NIYAT qatorini yozadi,
ya'ni jo'natishdan OLDINGI holatni). Ularni fixture'ga qo'shish umumiy
seed'ni jo'natuvchining ichki holatiga bog'lardi — 07-10 aynan shu
qarorni `_INSERT_EVIDENCED_ANOMALY` uchun bergan.
"""


# ===========================================================================
# Fixture'lar
# ===========================================================================


@pytest.fixture
def bed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[Bed]:
    """Ikki bozor + sotuvchilar + nazoratchi; navbat qatorlari TESTDAN KEYIN o'chadi.

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi (`test_headline.py::
      env` da o'rnatilgan qoida): pytest fixture'larni TESKARI tartibda
      yopadi, ya'ni nazoratchi foydalanuvchisi domen qatorlaridan KEYIN
      o'chiriladi.
    """
    try:
        yield Bed(two_markets, auth_seed, market_domain, sync_owner_conn)
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(market_domain.market_ids))


class Bed:
    """Bir testning butun kirishi — bozorlar, sotuvchilar va navbat yozuvi."""

    def __init__(
        self,
        base: TwoMarketSeed,
        auth: AuthSeed,
        domain: MarketDomainSeed,
        conn: Connection[TupleRow],
    ) -> None:
        self.base = base
        self.auth = auth
        self.domain = domain
        self.conn = conn

    @property
    def market_id(self) -> UUID:
        return self.domain.market_a.market_id

    @property
    def other_market_id(self) -> UUID:
        return self.domain.market_b.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.domain.market_a.vendor_ids[0]

    @property
    def second_vendor_id(self) -> UUID:
        return self.domain.market_a.vendor_ids[1]

    def seed_status(
        self,
        status: OutboxStatus,
        *,
        market_id: UUID | None = None,
        vendor_id: UUID | None = None,
        kind: OutboxKind = OutboxKind.PAYMENT_RECEIPT,
        attempt_count: int = 0,
    ) -> UUID:
        """Bitta navbat qatori — ⛔ `created_at` SERVER soatidan (`now()`)."""
        return seed_outbox_row(
            self.conn,
            market_id=self.market_id if market_id is None else market_id,
            kind=kind.value,
            vendor_id=vendor_id,
            status=status.value,
            attempt_count=attempt_count,
        )

    def seed_every_status(self) -> dict[str, UUID]:
        """⛔ BESHALA HOLAT — «nol bo'lganda ham qaytadi» ning NAZORAT jufti.

        Nol da'vosi yolg'iz o'zi «hisoblagich umuman ishlaydimi?» degan
        savolga javob bermasdi: hamma sanoq nol bo'lgan javob ham uni
        qondirardi.
        """
        return {
            member.value: self.seed_status(member, vendor_id=self.vendor_id)
            for member in OutboxStatus
        }

    def set_error(self, outbox_id: UUID, *, error_type: str, status_code: int | None) -> None:
        self.conn.execute(_SET_ERROR, (error_type, status_code, str(outbox_id)))


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, bed: Bed) -> dict[str, str]:
    """DIREKTOR — unda `report_view` BOR (§5.6)."""
    return await session_headers(api_client, bed.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, bed: Bed) -> dict[str, str]:
    """KASSIR — ⛔ unda `report_view` YO'Q."""
    return await session_headers(api_client, bed.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, bed: Bed) -> dict[str, str]:
    """NAZORATCHI — ⛔ unda ham `report_view` YO'Q (T-05-58 ning davomi)."""
    return await session_headers(api_client, bed.auth.inspector.phone, SEED_PASSWORD)


@pytest.fixture
async def other_market_headers(api_client: httpx.AsyncClient, bed: Bed) -> dict[str, str]:
    """B BOZORINING direktori — RLS chegarasining ikkinchi tomoni."""
    return await session_headers(api_client, bed.base.market_b.director_phone, SEED_PASSWORD)


# ===========================================================================
# Yordamchilar
# ===========================================================================


def keys_at_every_depth(node: Any) -> set[str]:
    """JSON daraxtining ⛔ BARCHA chuqurligidagi kalitlar.

    ⛔ YUZAKI TEKSHIRUV YETMAYDI: `rows[].meta.payload` shaklidagi
       ichma-ich qo'shimcha «javobda `payload` bormi?» degan bitta
       da'voni JIMGINA o'tkazib yuborardi.
    """
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            found |= keys_at_every_depth(value)
    elif isinstance(node, list):
        for item in node:
            found |= keys_at_every_depth(item)
    return found


def methods_under(path_prefix: str) -> set[str]:
    """OpenAPI da berilgan prefiks ostidagi ⛔ BARCHA HTTP metodlari.

    ⚠ PREFIKS BO'YICHA, aniq yo'l bo'yicha EMAS: `POST /delivery/{id}/
      retry` qo'shilsa u BOSHQA yo'lda tug'ilardi va aniq moslikdagi
      da'vo uni KO'RMASDI.
    """
    spec = fastapi_app.openapi()
    found: set[str] = set()
    for path, operations in spec["paths"].items():
        if path.startswith(path_prefix):
            found |= {method.upper() for method in operations}
    return found


# ===========================================================================
# 1. JAVOB SHAKLI — BESHALA HISOBLAGICH
# ===========================================================================


async def test_every_status_gets_its_own_counter(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """Besh holatli seed -> beshala hisoblagich AYNAN BIRDAN."""
    bed.seed_every_status()

    response = await api_client.get(DELIVERY_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["day"] == business_today().isoformat()
    assert len(body["rows"]) == len(OutboxStatus)
    assert {
        "pending": body["pending_count"],
        "sent": body["sent_count"],
        "delivered": body["delivered_count"],
        "failed": body["failed_count"],
        "blocked": body["blocked_count"],
    } == {member.value: 1 for member in OutboxStatus}


async def test_all_five_counters_come_back_even_when_zero(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ NOL HAM NATIJA — to'rt sanoq NOL bo'lib QAYTADI, tushib qolmaydi.

    ⛔ «Bu kunda bloklangan sotuvchi yo'q» bilan «hisoblagich
       ishlamayapti» bir xil ko'rinsa, direktor D-02 nizosida noto'g'ri
       xulosaga kelardi — va aynan o'sha nizo uchun bu yuza qurilgan.
    """
    bed.seed_status(OutboxStatus.PENDING, vendor_id=bed.vendor_id)

    response = await api_client.get(DELIVERY_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    body = response.json()

    counters = {key: value for key, value in body.items() if key.endswith("_count")}
    assert set(counters) == {
        "pending_count",
        "sent_count",
        "delivered_count",
        "failed_count",
        "blocked_count",
    }
    assert counters["pending_count"] == 1
    assert [counters[key] for key in counters if key != "pending_count"] == [0, 0, 0, 0]


async def test_the_empty_day_still_answers_with_five_counters(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ BIRORTA QATOR YO'Q kun ham BESH sanoq bilan javob beradi.

    ⚠ NAZORAT: `rows` bo'sh bo'lgani holda ham javob to'liq shaklda
      keladi, ya'ni klientning `z.strictObject` sxemasi PARSE
      chegarasida yiqilmaydi.
    """
    response = await api_client.get(DELIVERY_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["rows"] == []
    assert body["next_cursor"] is None
    assert (
        body["pending_count"]
        == body["sent_count"]
        == body["delivered_count"]
        == body["failed_count"]
        == body["blocked_count"]
        == 0
    )


# ===========================================================================
# 2. XABARNING O'ZI JAVOBDA YO'Q — REKURSIV KALIT SKANI
# ===========================================================================


async def test_the_message_itself_never_reaches_the_response(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ JAVOBNING HECH BIR CHUQURLIGIDA taqiqlangan kalit YO'Q.

    ⛔ DA'VO TO'PLAM KESISHMASI BILAN: «`payload` yo'qmi?» shaklidagi
       bitta tekshiruv YONIDAGI yangi kalitni (masalan `chat_id`)
       KO'RMASDI.
    """
    bed.seed_every_status()

    response = await api_client.get(DELIVERY_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    leaked = sorted(keys_at_every_depth(response.json()) & FORBIDDEN_KEYS)

    assert leaked == [], (
        f"⛔ yetkazilganlik javobiga taqiqlangan kalit(lar) kirdi: {leaked}. "
        "Xabarning MAZMUNI ekranga chiqmaydi (ikkinchi pul yuzasi), Telegram "
        "identifikatori esa odamni TASHQI tizimda aniqlaydi (D-01, §5.5)."
    )


def test_the_scan_would_catch_a_leak() -> None:
    """NAZORAT — skaner ICHMA-ICH qo'yilgan kalitni USHLAYDI.

    ⛔ Usiz yuqoridagi bo'sh natija «toza javob» emas, «ishlamayotgan
       skaner» degani bo'lishi mumkin edi (`reconciliation-copy.test.mjs`
       ning nazorat naqshi).
    """
    probe = {"rows": [{"outbox_id": "x", "meta": {"payload": {"amount_soum": 1}}}]}

    assert keys_at_every_depth(probe) & FORBIDDEN_KEYS == {"payload"}


async def test_the_error_type_is_a_type_name_not_a_message(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ `last_error_type` — TUR NOMI; URL parchasi va probel YO'Q (D-04).

    Telegram Bot API ning URL'i BOT TOKENINI tashiydi va `httpx`
    istisnosining MATNI to'liq URL'ni o'z ichiga oladi — bitta
    `str(exc)` sirni bazaga, u yerdan `pg_dump` -> restic -> TASHQI
    BUCKET ga olib chiqardi.
    """
    failed_id = bed.seed_status(OutboxStatus.FAILED, vendor_id=bed.vendor_id, attempt_count=5)
    bed.set_error(failed_id, error_type="ConnectTimeout", status_code=502)

    response = await api_client.get(DELIVERY_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert len(rows) == 1

    error_type = rows[0]["last_error_type"]
    assert error_type == "ConnectTimeout"
    assert rows[0]["last_status_code"] == 502
    assert rows[0]["attempt_count"] == 5

    found = sorted(token for token in ERROR_TYPE_FORBIDDEN if token in error_type.lower())
    assert found == [], f"xato TURI matnga o'xshayapti — topilgan parcha(lar): {found}"


# ===========================================================================
# 3. HUQUQ — KASSIR VA NAZORATCHI 403
# ===========================================================================


async def test_the_cashier_cannot_read_the_delivery_log(
    api_client: httpx.AsyncClient, bed: Bed, cashier_headers: dict[str, str]
) -> None:
    """⛔ KASSIRDA `report_view` YO'Q — **403** (T-07-58 ning davomi)."""
    bed.seed_every_status()

    response = await api_client.get(DELIVERY_URL, headers=cashier_headers)

    assert response.status_code == 403, response.text


async def test_the_inspector_cannot_read_the_delivery_log(
    api_client: httpx.AsyncClient, bed: Bed, inspector_headers: dict[str, str]
) -> None:
    """⛔ NAZORATCHIDA HAM `report_view` YO'Q — **403**.

    ⚠ U BANDLIK verdiktini beradi; xabar yetkazilishi esa direktorning
      NIZO yuzasi va u nazoratchining ishiga umuman aloqador emas.
    """
    bed.seed_every_status()

    response = await api_client.get(DELIVERY_URL, headers=inspector_headers)

    assert response.status_code == 403, response.text


# ===========================================================================
# 4. TENANT CHEGARASI — RLS
# ===========================================================================


async def test_a_foreign_market_never_sees_the_rows(
    api_client: httpx.AsyncClient,
    bed: Bed,
    other_market_headers: dict[str, str],
    director_headers: dict[str, str],
) -> None:
    """⛔ B bozorining direktori A ning qatorlarini KO'RMAYDI (RLS `FORCE`).

    ⛔ DA'VO IKKI TOMONLAMA VA IKKINCHISI MAJBURIY: faqat «B bo'sh
       ko'radi» tekshiruvi A ham bo'sh bo'lgan holatda YASHIL qolardi
       — ya'ni seed umuman yozilmagan bo'lsa ham o'tardi.
    """
    seeded = bed.seed_every_status()

    own = await api_client.get(DELIVERY_URL, headers=director_headers)
    assert own.status_code == 200, own.text
    assert len(own.json()["rows"]) == len(seeded)

    foreign = await api_client.get(DELIVERY_URL, headers=other_market_headers)
    assert foreign.status_code == 200, foreign.text

    body = foreign.text
    assert foreign.json()["rows"] == []
    for outbox_id in seeded.values():
        assert str(outbox_id) not in body, "begona bozorning javobida A ning izi bor"


# ===========================================================================
# 5. KEYSET — TAKRORLANMAYDI
# ===========================================================================


async def test_the_keyset_never_repeats_a_row(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ IKKI SAHIFA — KESISHMA BO'SH va birlashma TO'LIQ (DQ-4).

    ⛔ `OFFSET` ISHLATILMAYDI: bugungi navbat KUN DAVOMIDA o'sadi
       (har to'lov yangi qator qo'yadi), ya'ni offset bilan
       sahifalangan ro'yxat bir qatorni IKKI marta ko'rsatib,
       ikkinchisini UMUMAN ko'rsatmasdi.
    """
    seeded = bed.seed_every_status()

    first = await api_client.get(DELIVERY_URL, params={"limit": 2}, headers=director_headers)
    assert first.status_code == 200, first.text
    page_one = first.json()
    assert len(page_one["rows"]) == 2
    assert page_one["next_cursor"] is not None

    second = await api_client.get(
        DELIVERY_URL,
        params={"limit": 2, "cursor": page_one["next_cursor"]},
        headers=director_headers,
    )
    assert second.status_code == 200, second.text
    page_two = second.json()

    ids_one = [row["outbox_id"] for row in page_one["rows"]]
    ids_two = [row["outbox_id"] for row in page_two["rows"]]

    assert set(ids_one) & set(ids_two) == set(), "keyset bir qatorni IKKI marta berdi"
    assert set(ids_one) | set(ids_two) <= {str(value) for value in seeded.values()}

    # ⛔ HISOBLAGICHLAR SAHIFADAN MUSTAQIL: ikkinchi sahifada ham AYNAN
    #   o'sha beshta son. Aks holda direktor «raqam o'zgarib ketdi»
    #   degan xulosaga kelardi.
    assert [page_two[f"{member.value}_count"] for member in OutboxStatus] == [1, 1, 1, 1, 1]


async def test_a_broken_cursor_is_rejected_not_ignored(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ Buzilgan kursor **422**, jim e'tiborsizlik EMAS.

    Jim tashlab yuborilgan kursor BIRINCHI sahifani qayta ko'rsatardi va
    ro'yxat cheksiz aylanardi — direktor buni SEZMASDI ham.
    """
    response = await api_client.get(
        DELIVERY_URL, params={"cursor": "not-a-cursor"}, headers=director_headers
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "cursor_invalid"


# ===========================================================================
# 6. FILTR VA KUN
# ===========================================================================


async def test_the_vendor_filter_scopes_the_rows_and_the_counters(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ Sotuvchi filtri QAMROVNI toraytiradi — hisoblagichlarga HAM.

    ⚠ Bu `status` filtridan FARQ QILADI (`_CASE_COUNTS` qarori): holat
      filtri sanoqni buzardi, sotuvchi filtri esa savolning O'ZINI
      o'zgartiradi — «SHU sotuvchiga bugun nechta xabar yetdi?».
    """
    bed.seed_status(OutboxStatus.DELIVERED, vendor_id=bed.vendor_id)
    bed.seed_status(OutboxStatus.BLOCKED, vendor_id=bed.second_vendor_id)

    response = await api_client.get(
        DELIVERY_URL, params={"vendor_id": str(bed.vendor_id)}, headers=director_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert [row["vendor_id"] for row in body["rows"]] == [str(bed.vendor_id)]
    assert body["delivered_count"] == 1
    assert body["blocked_count"] == 0, (
        "filtr hisoblagichlarga qo'llanmagan — boshqa sotuvchining bloki "
        "shu sotuvchining sanog'iga qo'shilib ketdi"
    )


async def test_the_default_day_is_today_and_the_future_is_rejected(
    api_client: httpx.AsyncClient, bed: Bed, director_headers: dict[str, str]
) -> None:
    """⛔ STANDART KUN — **BUGUN** (§4.4), va u `report` ning TESKARISI.

    Kvitansiya ⛔ HOZIR ketadi (D-18) va «xabar kelmadi» nizosi ⛔ O'SHA
    KUNI chiqadi; kechaga qulflangan yuza BOT-04 ning amaliy qiymatini
    NOLGA tushirardi.
    """
    bed.seed_status(OutboxStatus.SENT, vendor_id=bed.vendor_id)
    today = business_today()

    default_day = await api_client.get(DELIVERY_URL, headers=director_headers)
    assert default_day.status_code == 200, default_day.text
    assert default_day.json()["day"] == today.isoformat()
    assert len(default_day.json()["rows"]) == 1

    # ⛔ KECHA -> BO'SH: bugungi qatorlar KECHAGI kunga TUSHMAYDI, ya'ni
    #   kun chegarasi HAQIQATAN qo'llanadi (nazorat).
    yesterday = today - timedelta(days=1)
    past = await api_client.get(
        DELIVERY_URL, params={"day": yesterday.isoformat()}, headers=director_headers
    )
    assert past.status_code == 200, past.text
    assert past.json()["day"] == yesterday.isoformat()
    assert past.json()["rows"] == []

    tomorrow = today + timedelta(days=1)
    future = await api_client.get(
        DELIVERY_URL, params={"day": tomorrow.isoformat()}, headers=director_headers
    )
    assert future.status_code == 422, future.text
    assert future.json()["detail"] == "day_in_future"


# ===========================================================================
# 7. YOZISH YUZASI UMUMAN YO'Q — OpenAPI USTIDAN
# ===========================================================================


def test_the_delivery_surface_is_read_only_in_the_contract() -> None:
    """⛔ `/reconciliation/delivery` OSTIDA `POST`/`PATCH`/`DELETE` — **0** ta.

    =======================================================================
    ⛔⛔ DA'VO OpenAPI USTIDAN VA U INTIZOMDAN KUCHLIROQ: handler
        qo'shilgan zahoti spetsifikatsiyada metod PAYDO BO'LADI, ya'ni
        taqiq mexanizmga tayanadi.

    Uch mustaqil sabab (§17.2):
      1. outbox O'ZI qayta uradi (DQ-3 backoff);
      2. qo'lda yuborish `uq_notification_outbox_market_id_dedupe_key`
         (D-21) bilan TO'QNASHARDI yoki uni aylanib o'tib sotuvchiga
         IKKINCHI kvitansiya yuborardi;
      3. qo'lda `delivered` qo'yish nizoda ⛔ SOXTA DALIL bo'lardi.
    =======================================================================
    """
    methods = methods_under(DELIVERY_URL)

    assert methods == {"GET"}, (
        f"⛔ yetkazilganlik yuzasida yozish metodi paydo bo'ldi: {sorted(methods)}. "
        "Navbat APPEND-ONLY (D-20) va uning yagona yozuvchisi JO'NATUVCHI."
    )


def test_no_second_router_module_was_opened() -> None:
    """⛔ Marshrut MAVJUD routerda — `app/api/v1/notifications.py` YO'Q.

    ⚠ Ikkinchi modul G-36 skanining qamrovini IKKIGA bo'lardi: frontend
      darvozasi AYNAN `lib/reconciliation-queries.ts` ni o'qiydi va
      ikkinchi so'rov moduli undan CHIQIB ketardi.
    """
    from pathlib import Path

    api_dir = Path(__file__).resolve().parents[2] / "services" / "core-api" / "app" / "api" / "v1"

    assert api_dir.is_dir(), f"nazorat: {api_dir} topilmadi — yo'l o'zgargan"
    assert not (api_dir / "notifications.py").exists(), (
        "yetkazilganlik marshruti IKKINCHI modulda ochilgan — u 07-10 ning "
        "mavjud routerida qolishi SHART"
    )
