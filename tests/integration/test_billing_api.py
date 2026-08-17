"""`/api/v1/billing/*` — O'QISH YUZASINING KONTRAKTI (BILL-02…BILL-05).

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI — **MAYDONNING YO'QLIGI**, VA U
    IKKI MUSTAQIL QATLAMDA O'LCHANADI.

  1. **Payload kalitlari to'plami TENGLIGI** — javob HAQIQATAN nima
     yuborayotganini o'lchaydi (`==`, `not in` EMAS — D-31);
  2. **`app.openapi()` dan HOSILA skan** — KONTRAKT nima va'da
     qilayotganini o'lchaydi, va u `/billing/*` marshrutlarining
     HAMMASI ustidan yuguradi, qo'lda yozilgan ro'yxat ustidan emas
     (D-32).

Ikkalasi ham kerak va bu 05-14 da o'lchangan: birinchisi faqat SHU
testda yuborilgan payloadni ko'radi (boshqa shoxda maydon paydo bo'lsa
sezmaydi), ikkinchisi esa faqat E'LON QILINGAN sxemani ko'radi
(handler `dict` qaytarib sxemani chetlab o'tsa sezmaydi). Ularning
mustaqilligi SABOTAJ bilan o'lchangan — natija 06-08 SUMMARY da.

=============================================================================
⛔ BU FAYL `test_billing_repo.py` NI TAKRORLAMAYDI.

Pul arifmetikasi (tarif yechimi, FIFO taqsimlash, qoldiq tengligi)
o'sha yerda, HAQIQIY bazada, 30 darvoza bilan o'lchangan. Bu yerda
faqat HTTP CHEGARASIDAGI da'volar:

  1. javob KALITLARI (yo'qlik ham, borlik ham);
  2. HUQUQ — kassir `/pending` ni ko'radi, `/charges` ni KO'RMAYDI;
  3. NOL — NATIJA: bo'sh kunda ham hamma hisoblagich qaytadi;
  4. C-12 juftligi HTTP javobida ham buzilmaydi;
  5. standart kun KECHA va kelajak kuni 422.
=============================================================================
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from app.main import app as fastapi_app
from app.repositories.billing_repo import (
    ExistingCharge,
    write_anomaly,
    write_late_review_adjustment,
)
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_daily_charge,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import AnomalyKind
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow

PENDING_URL = "/api/v1/billing/pending"
CHARGES_URL = "/api/v1/billing/charges"
ANOMALIES_URL = "/api/v1/billing/anomalies"

PENDING_STALL_KEYS = frozenset(
    {
        "stall_code",
        "service_date",
        "market_open",
        "amount_soum",
        "amount_unavailable_reason",
        "outstanding_soum",
        "total_due_soum",
        "stall_status",
        "vendor_assigned",
    }
)
"""UI-SPEC §9.2 ning AYNAN TO'QQIZ kaliti.

⛔ RO'YXAT SHU YERDA QO'LDA YOZILGAN VA BU ATAYIN: u KUTILGAN NATIJA,
   o'lchov emas. Uni `PendingStallResponse.model_fields` dan hosila
   qilish testni «model o'ziga teng» degan tavtologiyaga aylantirardi —
   maydon qo'shgan odam ikkala tomonni bir vaqtda o'zgartirardi va
   darvoza qizarmasdi (05-14 ning S7 sabotaji aynan shu sinf).

⚠ YETTIDAN TO'QQIZGA (quick 260816-75c): `stall_status` va
  `vendor_assigned` qo'shildi. Ikkalasi ham MUSTAQIL maydon va biri
  ikkinchisidan hosila QILINMAYDI. Sabab TEST-REPORT topilmasi: kassir
  ta'mirdagi rastani ham, sotuvchisiz rastani ham oddiy karta bilan
  ko'rardi va rad javobini FAQAT [Tasdiqlash] dan keyin olardi — server
  ikkala faktni ham BILARDI, lekin lookup javobida AYTMASDI.

⛔ `vendor_id` HAMON YO'Q: yangi maydon BUL, identifikator emas (C-10).
"""

PERSONAL_FIELDS = frozenset({"vendor_name", "phone", "full_name"})
"""C-10 darvozasining maydonlari — `test_personal_data_coverage.py:59` bilan AYNI.

⚠ NUSXA ONGLI: o'sha faylni import qilish tenancy paketini integratsiya
  to'plamiga bog'lardi. Nomlar `PERSONAL_ROUTES` darvozasi tomonidan
  ALLAQACHON mustaqil qo'riqlanadi, ya'ni ikki ro'yxat ajralib ketsa
  o'sha darvoza qizaradi.
"""

FORBIDDEN_MONEY_FIELDS = frozenset({"tariff_id", "category_id", "balance", "balance_soum"})
"""⛔ BIRORTA `/billing/*` JAVOBIDA BO'LMAYDIGAN nomlar.

`tariff_id`/`category_id` — D-20 ning KUCHLI shakli (klientda pul
arifmetikasining KIRISH ma'lumoti yo'q); `balance`/`balance_soum` —
BILL-03 («saqlangan balans yo'q, NOMI ham yo'q»).
"""

CHARGE_ID_ALLOWED_PREFIX = "/api/v1/billing/charges"
"""`charge_id` FAQAT shu prefiksdagi javoblarda qonuniy.

⛔ `/api/v1/billing/pending` da u HECH QACHON bo'lmaydi (D-17): proyeksiya
   HISOB EMAS, ya'ni hisob identifikatori MAVJUD EMAS — yashirilgan emas.
"""


class Env:
    """Uch qatlamli seed — `test_billing_repo.Env` ning qisqartirilgan shakli."""

    def __init__(
        self, billing: BillingDomainSeed, domain: MarketDomainSeed, base: TwoMarketSeed
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
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
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI.

    Bu faylning birorta da'vosi BANDLIKKA tayanmaydi: o'qish marshrutlari
    `daily_charges` va `billing_anomalies` qatorlarini ko'rsatadi, ularni
    esa test O'ZI yozadi (`add_daily_charge`, `write_anomaly`). `day_close`
    ni chaqirish har testga ikki materializatsiya yugurishini qo'shardi va
    hech qanday yangi da'vo bermasdi (06-05 da o'rnatilgan qoida).
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
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Bozor adminining sessiyasi — unda `report_view` HAM, `billing_collect_view` HAM bor."""
    market_a = env.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """KASSIR sessiyasi — ⛔ unda `report_view` YO'Q (UI-SPEC §5.6).

    Aynan shu yo'qlik bu faylning huquq da'vosini ma'noli qiladi: kassir
    `/pending` ni KO'RADI (bu uning kunlik ishi), `/charges` ni esa
    KO'RMAYDI (u hisobot o'qimaydi).
    """
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — unda `report_view` VA `billing_collect_view` bor (§5.6)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


def _stall_code(conn: Connection[TupleRow], stall_id: UUID) -> str:
    """Rastaning KODI — BAZADAN, `A_STALL_CODES_BY_SORT` indeksidan EMAS.

    Indeks bo'yicha olish qo'shni faylning RO'YXAT TARTIBIGA tayanardi va
    u qayta tartiblangan kuni test boshqa rastani so'ragan bo'lardi
    (`fixtures/billing_domain._nvr_of()` da o'rnatilgan qoida).
    """
    row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(stall_id),)).fetchone()
    assert row is not None, f"nazorat: {stall_id} rastasi bazada yo'q"
    code: str = row[0]
    return code


def _set_stall_status(conn: Connection[TupleRow], stall_id: UUID, status: str) -> None:
    """Rastaning REYESTR holatini o'zgartiradi — seedni kengaytirmasdan.

    ⚠ Yangi seed rastasi QO'SHILMAYDI va bu ataylab: `billing_domain`
      ning oltala stsenariy rastasi BANDLIK holatlarini ifodalaydi,
      reyestr holati esa ular bilan ORTOGONAL. Yettinchi rasta qo'shish
      «qaysi o'lchov qaysi rastada?» savolini har testda qaytadan
      tug'dirardi.

    ⛔ Qiymat `sbozor_core.enums.StallStatus` dan bo'lishi SHART —
       `STALL_STATUS_CHECK` konstrayti aks holda yozuvni rad etadi va
       nosozlik testning O'ZIDA ko'rinadi, mahsulotda emas.
    """
    conn.execute("UPDATE stalls SET status = %s WHERE id = %s", (status, str(stall_id)))


def _evidence_pair(conn: Connection[TupleRow], market_id: UUID) -> tuple[UUID, UUID]:
    """Bozorning HAQIQIY `(occupancy_event_id, snapshot_id)` jufti.

    ⛔ ZANJIR BAZADAN OLINADI, QAYTA QURILMAYDI: `billing_anomalies`
       kompozit FK bilan ikkala jadvalga birdan tayanadi va ular BIR XIL
       bozorga tegishli bo'lishi SHART (`add_charge_evidence()` bilan
       aynan bir xil qaror).
    """
    row = conn.execute(
        "SELECT id, snapshot_id FROM occupancy_events WHERE market_id = %s ORDER BY id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, f"nazorat: {market_id} da bandlik hodisasi yo'q"
    return row[0], row[1]


def _response_field_names(spec: dict[str, Any], schema: dict[str, Any]) -> set[str]:
    """Javob sxemasidagi BARCHA maydon nomlari — `$ref` lar bo'ylab REKURSIV.

    ⛔ SKAN QO'LDA YOZILGAN RO'YXAT EMAS, OPENAPI GRAFIDAN HOSILA (D-32).
       Qo'lda yozilgan ro'yxat yangi model qo'shilganda JIMGINA eskirardi:
       maydon javobga chiqib ketardi, darvoza esa yashil turardi.

    `anyOf` ham kuzatiladi: `/billing/pending` ning javobi UCH modelning
    birlashmasi va faqat birinchisiga qarash qolgan ikkitasini skandan
    CHIQARIB yuborardi.
    """
    defs = spec.get("components", {}).get("schemas", {})
    seen: set[str] = set()

    def walk(node: Any) -> set[str]:
        if not isinstance(node, dict):
            return set()
        ref = node.get("$ref")
        if ref is not None:
            key = str(ref).rsplit("/", 1)[-1]
            if key in seen:
                return set()
            seen.add(key)
            return walk(defs.get(key, {}))
        found: set[str] = set()
        properties = node.get("properties")
        if isinstance(properties, dict):
            found |= set(properties)
            for value in properties.values():
                found |= walk(value)
        for key in ("anyOf", "oneOf", "allOf"):
            for item in node.get(key, []):
                found |= walk(item)
        if "items" in node:
            found |= walk(node["items"])
        if "additionalProperties" in node:
            found |= walk(node["additionalProperties"])
        return found

    return walk(schema)


def _billing_response_fields() -> dict[str, set[str]]:
    """`/api/v1/billing/*` marshrutlarining 200-javob maydonlari.

    Kalit — `"{METOD} {yo'l}"`, qiymat — o'sha javobdagi barcha nomlar.
    """
    spec = fastapi_app.openapi()
    result: dict[str, set[str]] = {}
    for path, operations in spec["paths"].items():
        if not path.startswith("/api/v1/billing"):
            continue
        for method, operation in operations.items():
            success = operation.get("responses", {}).get("200")
            if success is None:
                continue
            schema = success["content"]["application/json"]["schema"]
            result[f"{method.upper()} {path}"] = _response_field_names(spec, schema)
    return result


# ===========================================================================
# 1. PAYLOAD KALITLARI — TO'PLAM TENGLIGI (D-31, D-17, D-20, C-10)
# ===========================================================================


async def test_the_pending_payload_has_exactly_the_nine_keys(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ Kalitlar to'plami AYNAN to'qqizta — `not in` bilan EMAS, `==` bilan.

    =======================================================================
    D-31: inkor tasdiq (`assert "charge_id" not in body`) FAQAT o'sha
    nomni ushlaydi. `chargeId`, `charge`, `chargeRef` — uchalasi ham
    jimgina o'tib ketardi va payload D-17 ni buzgan holda YASHIL qolardi.

    To'plam tengligi esa HAR QANDAY yangi kalitni ushlaydi, hatto nomi
    hech kim o'ylamagan bo'lsa ham.
    =======================================================================
    """
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    response = await api_client.get(
        PENDING_URL, params={"stall_code": code}, headers=cashier_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == PENDING_STALL_KEYS, (
        f"payload kalitlari UI-SPEC §9.2 dan farq qiladi: "
        f"ortiqcha={sorted(set(body) - PENDING_STALL_KEYS)}, "
        f"yetishmayapti={sorted(PENDING_STALL_KEYS - set(body))}"
    )
    assert body["stall_code"] == code


async def test_the_pending_payload_pairs_the_amount_with_its_reason(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """Juftlangan invariant HTTP javobida ham buzilmaydi (§9.2).

    ⚠ DA'VO IKKI TOMONLAMA VA U KUNGA BOG'LIQ EMAS: dushanba (A bozori
      yopiq) `amount_soum = null` + sabab beradi, qolgan kunlar summa +
      `null` sabab. Testni bitta shoxga qotirish uni HAFTA KUNIGA
      bog'lardi (06-06 deviatsiya #6 ning aynan sinfi).
    """
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    body = (
        await api_client.get(PENDING_URL, params={"stall_code": code}, headers=cashier_headers)
    ).json()

    assert (body["amount_soum"] is None) == (body["amount_unavailable_reason"] is not None), (
        f"juftlangan invariant buzildi: amount_soum={body['amount_soum']!r}, "
        f"amount_unavailable_reason={body['amount_unavailable_reason']!r}"
    )


async def test_a_normal_stall_reports_active_status_and_an_assigned_vendor(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ SALBIY NAZORAT: ogohlantirish maydonlari «har doim rost» EMAS.

    Usiz quyidagi ikki test (`maintenance` va biriktirilmagan rasta)
    HAR DOIM ROST qaytaradigan maydon ustida ham yashil bo'lardi:
    `stall_status` konstanta `"maintenance"` bo'lsa ham, `vendor_assigned`
    doim `False` bo'lsa ham darvoza sezmasdi. Normal rasta ikkalasining
    ham TESKARI qiymatini talab qiladi.
    """
    code = _stall_code(sync_owner_conn, env.stall("stall_with_two_occupied_slots"))

    body = (
        await api_client.get(PENDING_URL, params={"stall_code": code}, headers=cashier_headers)
    ).json()

    assert body["stall_status"] == "active", (
        f"seed rastasi reyestrda `active` emas: {body['stall_status']!r} — "
        "salbiy nazorat o'z shartini bajarmadi"
    )
    assert body["vendor_assigned"] is True, (
        "seed rastasiga bugungi kunda sotuvchi biriktirilgan bo'lishi SHART — "
        "aks holda biriktirish da'vosi ikkala shoxda ham bir xil ko'rinardi"
    )


async def test_a_stall_in_maintenance_reports_its_status_without_erasing_the_amount(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """⛔ HOLAT XABAR BERADI, PULNI O'CHIRMAYDI.

    =======================================================================
    Reyestr holati (`stalls.status`) hisob qoidasiga KIRMAYDI: `maintenance`
    deb belgilangan rasta savdo qilsa patta to'laydi va bu qaror
    `billing_repo._market_projection()` docstringida ALLAQACHON yozilgan
    («RASTA HOLATI BO'YICHA FILTR ATAYIN YO'Q»).

    Shuning uchun da'vo IKKI TOMONLAMA: holat javobda KO'RINADI, lekin
    `amount_soum` HAMON son va `amount_unavailable_reason` HAMON `None`.
    Faqat birinchi yarmini o'lchash keyingi ijrochiga «holat summani
    o'chirsin» degan yo'lni ochiq qoldirardi.
    =======================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = _stall_code(sync_owner_conn, stall_id)
    _set_stall_status(sync_owner_conn, stall_id, "maintenance")

    # ⛔ PREKONDITSIYA: bugun A bozori uchun OCHIQ kun bo'lishi SHART.
    #   Seed'da A dushanba yopiq (`A_OPEN_WEEKDAYS = 2..7`) va bu test
    #   2026-08-17 (dushanba) kuni `market_closed` bilan yiqildi
    #   [O'LCHANDI: 09-07 gate o'lchovi] — da'vo «reyestr holati summani
    #   o'chirmaydi» va u faqat OCHIQ kunda ma'noli. Yopiq kun xulqining
    #   o'z testlari bor (`test_market_calendar.py`); bu yerda kun jadvali
    #   testning o'lchov predmeti EMAS, prekonditsiya.
    sync_owner_conn.execute(
        "UPDATE market_profile SET open_weekdays = %s WHERE market_id = %s",
        ([1, 2, 3, 4, 5, 6, 7], str(env.market_id)),
    )

    body = (
        await api_client.get(PENDING_URL, params={"stall_code": code}, headers=cashier_headers)
    ).json()

    assert body["stall_status"] == "maintenance"
    assert isinstance(body["amount_soum"], int), (
        f"⛔ reyestr holati summani O'CHIRDI: amount_soum={body['amount_soum']!r}. "
        "Ta'mirdagi rasta savdo qilsa patta to'laydi (_market_projection qarori)"
    )
    assert body["amount_unavailable_reason"] is None, (
        f"⛔ holat yo'qlik sababiga aylandi: {body['amount_unavailable_reason']!r} — "
        "`AMOUNT_UNAVAILABLE_REASONS` reyestri holat ustunini BILMAYDI (D-32)"
    )


async def test_a_stall_without_an_assignment_says_so_before_the_payment(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """Biriktirishsiz rasta -> `vendor_assigned is False` VA qarz NOL.

    ⛔ MA'LUMOT YANGI EMAS, VAQTI YANGI: server bu faktni submit'da
       ALLAQACHON aytadi (409 `stall_not_assigned`, `payments.py`). Bu
       yerda u LOOKUP javobiga chiqadi, ya'ni kassir rad javobini
       [Tasdiqlash] dan KEYIN emas, OLDIN oladi.

    ⚠ `outstanding_soum == 0` ikkinchi da'vo emas, BIR da'voning ikkinchi
      yarmi: qoldiq SOTUVCHI kesimida hisoblanadi (C-4) va sotuvchisiz
      rastada uni hisoblab bo'lmaydi. Nol bu yerda «hisoblanmadi» ning
      HALOL shakli.
    """
    stall_id = env.domain.market_a.unassigned_stall_id
    assert stall_id is not None, "nazorat: `market_domain` da biriktirishsiz rasta yo'q"
    code = _stall_code(sync_owner_conn, stall_id)

    body = (
        await api_client.get(PENDING_URL, params={"stall_code": code}, headers=cashier_headers)
    ).json()

    assert body["vendor_assigned"] is False, (
        f"{code!r} rastasiga bugun sotuvchi biriktirilmagan, lekin javob "
        "`vendor_assigned=True` dedi — kassir rad javobini submit'dan keyin olardi"
    )
    assert body["outstanding_soum"] == 0


async def test_an_ambiguous_code_returns_only_codes(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """Ko'p moslikda SUMMA UMUMAN yo'q — faqat kodlar ro'yxati (§8.3, §9.4).

    ⛔ «Taxminiy summa» KO'RSATILMAYDI: kassir ro'yxatdan boshqa rastani
       tanlab, ekranda TURGAN summani to'lardi — bu §9.4 ning oldini
       olayotgan xatosining aynan o'zi.
    """
    response = await api_client.get(
        PENDING_URL, params={"stall_code": "1"}, headers=cashier_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"matches", "stall"}, body
    assert body["stall"] is None
    assert len(body["matches"]) > 1, (
        f"seed kodlari «1» prefiksida bir nechta moslik bermadi: {body['matches']} — "
        "ko'p moslik shoxi UMUMAN sinalmadi"
    )


async def test_an_unknown_code_is_not_an_empty_list(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
) -> None:
    """Nol moslik -> **404 `stall_not_found`**, bo'sh ro'yxat EMAS.

    Bo'sh `matches` bilan 200 qaytarish kassirga «rasta bor, faqat
    ko'rsatilmadi» deb YOLG'ON aytardi va u kodni qayta-qayta terardi.

    =======================================================================
    ⛔ `detail` — **SATR**, LUG'AT EMAS (CR-04).

    Bu tasdiq ilgari `{"error_code": "stall_not_found"}` ni kutardi va
    aynan shu bilan NOSOZLIKNI QULFLAB QO'YGANDI:
    `api-client.ts::detailOf()` `detail` ni faqat satr bo'lganda o'qiydi,
    lug'at uchun `""` qaytaradi. Ya'ni kod klientga UMUMAN yetib
    bormasdi va `collect-session.tsx` ning `"not-found"` holati —
    `StallLookup` ning «Rasta topilmadi / raqamni qayta kiriting»
    shoxi — O'LIK KOD edi. Kassir esa «yuklab bo'lmadi» + [Qayta
    urinish] ko'rardi va har urinish o'sha 404 ni qaytarardi.

    ⚠ TIP HAM O'LCHANADI, faqat qiymat emas: `== "stall_not_found"`
      yolg'iz `{"error_code": ...}` ni ham rad etadi, lekin
      `isinstance` tekshiruvi nosozlik xabarini AYNAN sababga
      yo'naltiradi. Sinf darvozasi esa
      `test_route_coverage.py::test_every_billing_http_exception_sends_a_string_detail`
      da — u BUTUN oilani AST ustidan skanerlaydi.
    =======================================================================
    """
    response = await api_client.get(
        PENDING_URL, params={"stall_code": "99999"}, headers=cashier_headers
    )

    assert response.status_code == 404, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, str), (
        f"`detail` SATR bo'lishi SHART (klient shartnomasi), keldi: {detail!r}"
    )
    assert detail == "stall_not_found"


async def test_the_market_projection_returns_every_counter(
    api_client: httpx.AsyncClient,
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """Bozor kesimi — ⛔ NOL HAM NATIJA (§9.5, `occupancy.py:122-124`)."""
    response = await api_client.get(PENDING_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "service_date",
        "market_open",
        "pending_amount_soum",
        "outstanding_soum",
        "pending_stall_count",
        "fetched_at",
    }, body
    assert body["service_date"] == business_today().isoformat()


# ===========================================================================
# 2. OPENAPI HOSILA SKANI — IKKINCHI, MUSTAQIL QATLAM (D-32, G-22)
# ===========================================================================


def test_no_billing_response_declares_a_personal_field() -> None:
    """⛔ C-10: BIRORTA `/billing/*` javobi ism/telefon QAYTARMAYDI.

    Sotuvchi nomi ekranda KERAK, lekin u MAVJUD, AUDIT QILINGAN
    `GET /vendors` marshrutidan olinib KLIENTDA joinlanadi (§5.5). Bu
    javoblarga ism qo'shish `PERSONAL_ROUTES` ni o'stirardi va moliyaviy
    yuzaga shaxsiy-ma'lumot qo'riqchisini o'rnatardi — keyingi ijrochi esa
    o'sha naqshni ko'chirardi.

    ⚠ SKAN MARSHRUTLARNI O'ZI TOPADI: yangi `/billing/*` marshruti
      darvozaga QO'SHILMASDAN kiradi (D-32).
    """
    surface = _billing_response_fields()

    assert surface, "OpenAPI da birorta `/api/v1/billing/*` marshruti topilmadi"
    leaks = {route: sorted(fields & PERSONAL_FIELDS) for route, fields in surface.items()}
    assert not any(leaks.values()), f"shaxsiy maydon qaytaruvchi marshrutlar: {leaks}"


def test_no_billing_response_declares_a_money_input_field() -> None:
    """⛔ D-20 + BILL-03: tarif kirish ma'lumoti ham, `balance` NOMI ham yo'q.

    D-20 ning KUCHLI shakli: klientda summani hisoblash *taqiqlanmaydi* —
    u IMKONSIZ, chunki kirish ma'lumoti (tarif identifikatori, toifasi)
    javobda UMUMAN yo'q. `balance`/`balance_soum` esa BILL-03 ning nomi:
    saqlangan balans yo'q va uning NOMI ham hech qayerda bo'lmasligi
    kerak, aks holda nom bir kun ustunga aylanardi.
    """
    surface = _billing_response_fields()

    leaks = {route: sorted(fields & FORBIDDEN_MONEY_FIELDS) for route, fields in surface.items()}
    assert not any(leaks.values()), f"taqiqlangan pul maydonlari: {leaks}"


def test_charge_id_is_declared_only_by_the_charge_routes() -> None:
    """⛔ D-17: `charge_id` `/pending` javobida HECH QACHON e'lon qilinmaydi.

    =======================================================================
    BU DA'VO IKKI TOMONLAMA VA IKKINCHI YARIM MAJBURIY.

    Faqat «`/pending` da yo'q» deyilsa, kimdir `charge_id` ni HAMMA
    javobdan olib tashlab (ya'ni `/charges` ni ham buzib) testni yashil
    qilardi. Shuning uchun POZITIV yarim ham bor: `/charges*` javoblarida
    u BO'LISHI SHART — DL-3 ning sarlavhasi aynan shu identifikatorni
    ko'rsatadi (§11.3).
    =======================================================================
    """
    surface = _billing_response_fields()

    for route, fields in surface.items():
        path = route.split(" ", 1)[1]
        if path.startswith(CHARGE_ID_ALLOWED_PREFIX):
            assert "charge_id" in fields, (
                f"{route}: yozilgan hisob javobida `charge_id` YO'Q — DL-3 ning "
                "sarlavhasi va tuzatish zanjiri usiz ifodalab bo'lmaydi (§11.3)"
            )
        else:
            assert "charge_id" not in fields, (
                f"{route}: proyeksiya javobida `charge_id` E'LON QILINGAN. "
                "Proyeksiya HISOB EMAS (D-17) — hisob identifikatori D+1 04:10 "
                "gacha MAVJUD EMAS va uni `null` bilan e'lon qilish ekranga "
                "«hisob bor, faqat hozir bo'sh» deb YOLG'ON aytardi."
            )


# ===========================================================================
# 3. HUQUQ — KASSIR HISOBOT O'QIMAYDI (C-9, §5.6)
# ===========================================================================


@pytest.mark.parametrize("url", [CHARGES_URL, ANOMALIES_URL])
async def test_the_cashier_cannot_reach_the_director_surface(
    api_client: httpx.AsyncClient,
    env: Env,
    cashier_headers: dict[str, str],
    url: str,
) -> None:
    """Kassirda `report_view` YO'Q -> **403** (§5.6).

    ⛔ MEXANIZM: `require_permission(REPORT_VIEW)`, `require_any_permission()`
       EMAS. Ikkinchisi kassirga bu yuzani ochib berardi va C-9 ning yopiq
       to'plamiga tegishni talab qilardi.
    """
    response = await api_client.get(url, headers=cashier_headers)

    assert response.status_code == 403, response.text


async def test_the_report_viewer_also_sees_the_projection(
    api_client: httpx.AsyncClient,
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """Direktor ham `/pending` ni ko'radi — BITTA HUQUQ, UCH ROL (C-9).

    Bu «yo P yo Q» darvozasining ALTERNATIVASI va uning isboti: kassir va
    direktor AYNI marshrutdan o'tadi, chunki `billing_collect_view` ikkala
    rolga ham berilgan — `require_any_permission()` ga umuman ehtiyoj
    tug'ilmaydi.
    """
    response = await api_client.get(PENDING_URL, headers=director_headers)

    assert response.status_code == 200, response.text


# ===========================================================================
# 4. NOL — NATIJA VA STANDART KUN (C-3, §11.1)
# ===========================================================================


async def test_an_empty_day_still_returns_both_charge_counters(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Hisobsiz kunda ham `charge_count` VA `charged_soum` QAYTADI.

    ⛔ Maydonning YO'QOLISHI «bu kunda hisob yo'q» bilan «hisoblagich
       ishlamayapti» ni bir xil ko'rsatardi — 4-fazadagi «yo'qlikka
       alert» prinsipining aynan aksi.
    """
    empty_day = (business_today() - timedelta(days=90)).isoformat()

    response = await api_client.get(CHARGES_URL, params={"day": empty_day}, headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"day", "rows", "charge_count", "charged_soum"}, body
    assert body["rows"] == []
    assert body["charge_count"] == 0
    assert body["charged_soum"] == 0


async def test_an_empty_day_still_returns_all_three_anomaly_counters(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ UCHALA SANOQ HAM ALOHIDA va nol bo'lganda ham qaytadi (D-05).

    Umumiy `anomaly_count` maydoni javobda YO'Q va bo'lmasligi kerak:
    «ko'ra olmadik» ≠ «band, lekin biriktirilmagan», va ikkisini bitta
    songa qo'shish KO'R NUQTADAN TUSHUM DA'VOSI TO'QISH bo'lardi.
    """
    empty_day = (business_today() - timedelta(days=90)).isoformat()

    response = await api_client.get(ANOMALIES_URL, params={"day": empty_day}, headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "day",
        "rows",
        "unassigned_count",
        "closed_day_count",
        "no_coverage_count",
    }, body
    assert (body["unassigned_count"], body["closed_day_count"], body["no_coverage_count"]) == (
        0,
        0,
        0,
    )


@pytest.mark.parametrize("url", [CHARGES_URL, ANOMALIES_URL])
async def test_the_default_day_is_yesterday(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
    url: str,
) -> None:
    """⛔ STANDART KUN — KECHA, BUGUN EMAS (§11.1).

    C-3 bo'yicha hisob **D+1 04:10** da tug'iladi. Standarti BUGUN bo'lsa
    sahifa HAR DOIM bo'sh ochilardi va direktor to'g'ri ishlayotgan tizimni
    buzuq deb hisoblardi.
    """
    response = await api_client.get(url, headers=admin_headers)

    assert response.status_code == 200, response.text
    assert response.json()["day"] == (business_today() - timedelta(days=1)).isoformat()


@pytest.mark.parametrize("url", [CHARGES_URL, ANOMALIES_URL])
async def test_a_future_day_is_rejected(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
    url: str,
) -> None:
    """Kelajak kuni -> **422** (`CHECK (service_date <= business_date)` ning jufti).

    Usiz so'rov bazagacha borib BO'SH ro'yxat qaytarardi va «kelajakda
    hisob yo'q» degan MA'NOSIZ javob «bu kunda hisob yozilmagan» bilan bir
    xil ko'rinardi.
    """
    tomorrow = (business_today() + timedelta(days=1)).isoformat()

    response = await api_client.get(url, params={"day": tomorrow}, headers=admin_headers)

    assert response.status_code == 422, response.text


# ===========================================================================
# 5. YOZILGAN HISOB VA C-12 JUFTLIGI
# ===========================================================================


async def test_a_written_charge_appears_with_its_counters(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Yozilgan hisob jadvalda ko'rinadi va hisoblagichlar unga MOS keladi.

    ⛔ `vendor_id` QAYTADI, `vendor_name` EMAS (C-10) — bu qator to'plam
       tengligi bilan qulflanadi, ya'ni ism qo'shilsa test QIZARADI.
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    charge_id, service_date = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=stall_id,
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
    )

    response = await api_client.get(
        CHARGES_URL, params={"day": service_date.isoformat()}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["day"] == service_date.isoformat()
    assert body["charge_count"] == 1
    assert body["charged_soum"] == TARIFF_SOUM

    (row,) = body["rows"]
    assert set(row) == {
        "charge_id",
        "stall_code",
        "vendor_id",
        "service_date",
        "tariff_amount_soum",
        "amount_soum",
        "outstanding_soum",
    }, row
    assert row["charge_id"] == str(charge_id)
    assert row["stall_code"] == _stall_code(sync_owner_conn, stall_id)
    assert row["vendor_id"] == str(env.vendor_id)


async def test_the_charge_detail_never_declares_the_tariff_id(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """DL-3 payloadi — besh bo'lim, `tariff_id` YO'Q (§11.3).

    ⛔ Bo'sh `adjustments`/`evidence` YASHIRILMAYDI: dialog «Tuzatish
       yo'q» jumlasini ko'rsatadi — nol NATIJA, yo'qlik emas.
    """
    charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall("stall_with_two_occupied_slots"),
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
    )

    response = await api_client.get(f"{CHARGES_URL}/{charge_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "charge_id",
        "service_date",
        "stall_code",
        "tariff_amount_soum",
        "amount_soum",
        "adjustments",
        "evidence",
    }, body
    assert body["adjustments"] == []
    assert body["evidence"] == []


async def test_the_charge_detail_survives_a_system_written_adjustment(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ CR-01: TIZIM yozgan tuzatish (`actor_user_id IS NULL`) 200 beradi.

    =======================================================================
    BU TESTNING QIYMATI — YUQORIDAGI TESTNING KO'R NUQTASI.

    `test_the_charge_detail_never_declares_the_tariff_id` `adjustments ==
    []` ni tasdiqlaydi, ya'ni SERIALIZATOR tuzatish qatori bilan HECH
    QACHON uchrashmaydi. Sxema `actor_user_id: UUID` (non-Optional) deb
    turganda ham u YASHIL edi — 500 faqat TUZATILGAN, ya'ni nizoli
    hisoblarda chiqardi.

    ⛔ Tuzatish MAHSULOT YO'LIDAN yoziladi
      (`write_late_review_adjustment()`), xom `INSERT` bilan emas va
      AYNIQSA `admin_user_id` bilan emas: `test_billing_repo.py::_adjust`
      HAQIQIY odam biriktiradi — bu PRODUKSIYA yozadigan qatorning
      TESKARISI va aynan shu farq nuqsonni yashirgan edi.

    ⛔ `actor_user_id is None` TENGLIK bilan o'lchanadi, `in body` bilan
      emas: maydon YO'QOLIB ketsa ham (`exclude_none`) test qizarishi
      kerak — klient uni `z.uuid().nullable()` bilan KUTADI, ya'ni
      yo'qlik `strictObject` da throw berardi.
    =======================================================================
    """
    charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall("stall_with_two_occupied_slots"),
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
    )

    async with tenant_session(env.market_id) as session:
        adjustment_id = await write_late_review_adjustment(
            session,
            market_id=env.market_id,
            charge=ExistingCharge(charge_id=charge_id, amount_soum=TARIFF_SOUM),
        )
    assert adjustment_id is not None, "tuzatish yozilmadi — test o'z holatini qurmadi"

    response = await api_client.get(f"{CHARGES_URL}/{charge_id}", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    (adjustment,) = body["adjustments"]
    assert set(adjustment) == {
        "adjustment_id",
        "direction",
        "amount_soum",
        "reason_code",
        "actor_user_id",
        "created_at",
    }, adjustment
    assert adjustment["actor_user_id"] is None, "NULL = TIZIM (0022) — odam TO'QILMAYDI"
    assert adjustment["reason_code"] == "late_review"
    assert adjustment["direction"] == "decrease"
    assert adjustment["amount_soum"] == TARIFF_SOUM
    assert body["amount_soum"] == 0, "to'liq summa ayirildi — netto NOL"


async def test_an_unknown_charge_is_not_found(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Mavjud bo'lmagan hisob -> **404**, va AYNIQSA 403 EMAS (T-01-76)."""
    unknown = UUID("00000000-0000-4000-8000-000000000000")

    response = await api_client.get(f"{CHARGES_URL}/{unknown}", headers=admin_headers)

    assert response.status_code != 403, "403 obyekt MAVJUDLIGINI tasdiqlardi"
    assert response.status_code == 404, response.text


async def test_the_anomaly_rows_keep_the_c12_pairing(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ C-12: `no_coverage_stall` DALILSIZ, qolgan ikkitasi DALIL BILAN.

    =======================================================================
    UCHALA `kind` HAM BITTA JAVOBDA VA SANOQLAR ALOHIDA — ya'ni test
    «uchtasi qo'shilib ketmadimi?» savolini ham javoblaydi. Bitta `kind`
    bilan yozilgan test bu farqni UMUMAN ko'rmasdi (D-05).

    ⚠ QATORLAR MAHSULOT YO'LIDAN yoziladi (`write_anomaly()`), xom
      `INSERT` bilan emas: juftlangan shart ilova qatlamida ham
      majburlanadi va uni chetlab o'tish testni DB `CHECK` iga bog'lab
      qo'yardi.
    =======================================================================
    """
    service_date = business_today() - timedelta(days=2)
    event_id, snapshot_id = _evidence_pair(sync_owner_conn, env.market_id)

    async with tenant_session(env.market_id) as session:
        await write_anomaly(
            session,
            market_id=env.market_id,
            stall_id=env.stall("stall_occupied_without_assignment"),
            service_date=service_date,
            kind=AnomalyKind.UNASSIGNED_OCCUPIED,
            occupancy_event_id=event_id,
            snapshot_id=snapshot_id,
        )
        await write_anomaly(
            session,
            market_id=env.market_id,
            stall_id=env.stall("stall_occupied_on_a_closed_day"),
            service_date=service_date,
            kind=AnomalyKind.CLOSED_DAY_OCCUPIED,
            occupancy_event_id=event_id,
            snapshot_id=snapshot_id,
        )
        await write_anomaly(
            session,
            market_id=env.market_id,
            stall_id=env.stall("stall_with_only_no_coverage_slots"),
            service_date=service_date,
            kind=AnomalyKind.NO_COVERAGE_STALL,
        )

    response = await api_client.get(
        ANOMALIES_URL, params={"day": service_date.isoformat()}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["unassigned_count"], body["closed_day_count"], body["no_coverage_count"]) == (
        1,
        1,
        1,
    )

    by_kind = {row["kind"]: row for row in body["rows"]}
    assert set(by_kind) == {kind.value for kind in AnomalyKind}, by_kind
    for kind, row in by_kind.items():
        assert set(row) == {
            "anomaly_id",
            "kind",
            "stall_code",
            "service_date",
            "snapshot_id",
        }, row
        expected_missing = kind == AnomalyKind.NO_COVERAGE_STALL.value
        assert (row["snapshot_id"] is None) is expected_missing, (
            f"C-12 juftligi buzildi: kind={kind!r}, snapshot_id={row['snapshot_id']!r}"
        )


async def test_a_charge_from_another_market_is_not_visible(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """B bozorining hisobi A ning ro'yxatida ham, tafsilotida ham YO'Q.

    ⚠ Cross-tenant da'vosi matritsada ham bor (`test_cross_tenant.py`),
      lekin u FAQAT tafsilot marshrutini (yo'l parametri bor) qamraydi.
      RO'YXAT marshrutida yo'l parametri yo'q, ya'ni «begona qator
      ro'yxatga tushib qolmadimi?» savoli AYNAN shu yerda o'lchanadi.
    """
    other = env.billing.market_b
    charge_id, service_date = add_daily_charge(
        sync_owner_conn,
        market_id=other.market_id,
        stall_id=env.domain.market_b.stall_ids[0],
        vendor_id=other.vendor_id,
        tariff_id=other.tariff_id,
    )

    listing = await api_client.get(
        CHARGES_URL, params={"day": service_date.isoformat()}, headers=admin_headers
    )
    detail = await api_client.get(f"{CHARGES_URL}/{charge_id}", headers=admin_headers)

    assert listing.status_code == 200, listing.text
    assert listing.json()["charge_count"] == 0
    assert str(charge_id) not in listing.text
    assert detail.status_code == 404, detail.text
