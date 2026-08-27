"""Ish kunlari kalendarining API xulqi — SC#4 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYLNING ENG MUHIM DA'VOSI: API VA `market_is_open()` BIR XIL HAQIQATGA
TAYANADI.

`tests/integration/test_market_calendar.py` (02-07) uchala qavatni
(istisno -> haftalik jadval -> fail-closed) DB darajasida isbotlaydi va
xom `INSERT` bilan yozadi. Bu yerdagi savol boshqa: **ilova orqali
yozilgan o'zgarish o'sha funksiyaga yetib boradimi**.

Shuning uchun kalendar testlari API orqali YOZADI va `SELECT
market_is_open(:m, :d)` orqali O'QIYDI. Ikki alohida qatlam bo'lsa —
masalan router `open_weekdays` ni boshqa ustunga yozsa yoki istisnoni
boshqa bozorga qo'ysa — faqat shu shakl uni ushlaydi: API o'z javobini
qaytarib "muvaffaqiyat" deb ko'rsatib turardi, 6-fazaning kunlik job'i
esa hech qanday o'zgarish ko'rmasdi.
=============================================================================

SANALAR `market_today` DAN HISOBLANADI (sobit yozilmaydi): "keyingi
dushanba" va "keyingi seshanba" har doim bir hafta ichida, ya'ni ular
loyihaning muddati ichida ham, undan keyin ham to'g'ri qoladi. Qaysi kun
ochiq/yopiqligi esa SEED'dan olinadi (`market_domain.market_a.
open_weekdays`) — test o'z nusxasini yozmaydi.

AUDIT DB-TRIGGERDA: `market_profile` va `market_calendar_exceptions`
ikkalasi ham `AUDITED_TABLES` da (02-05/02-06). Router `write_app_audit()`
CHAQIRMAYDI — aks holda har o'zgarish uchun jurnalda ikkita qator paydo
bo'lardi.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import CALENDAR_URL, session_headers
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from datetime import date

    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

WEEKDAYS_URL = f"{CALENDAR_URL}/weekdays"
EXCEPTIONS_URL = f"{CALENDAR_URL}/exceptions"

MONDAY = 1
TUESDAY = 2
"""ISO kun raqamlari. Seed'da A bozori DUSHANBA yopiq (`open_weekdays` = 2..7).

Ikkala qiymat ham testda QAYTA TEKSHIRILADI (`assert ... in/not in
open_weekdays`): seed jadvali o'zgarsa test o'z shartini bajarmay
qolgani DARHOL ko'rinadi, "yopiq kun yopiq" o'rniga "ochiq kun ochiq" ni
sinab yurmaydi.
"""

ALL_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7]
HOLIDAY_NOTE = "Bayram (API testi)"

IS_OPEN = "SELECT market_is_open(%s, %s::date)"
"""6-fazaning kunlik job'i ishlatadigan AYNAN o'sha shart (bitta chaqiruv)."""

PROFILE_AUDIT = (
    "SELECT action, old_value->'open_weekdays', new_value->'open_weekdays', changed_keys "
    "FROM audit_log "
    "WHERE market_id = %s AND table_name = 'market_profile' AND action = 'update' "
    "ORDER BY id"
)

INVALID_WEEKDAYS: tuple[tuple[str, list[int]], ...] = (
    ("bo'sh", []),
    ("oraliqdan-tashqari", [0, 8]),
    ("takroriy", [1, 1, 2]),
)
"""Uchala holat ham 422 berishi shart va uchalasi HAR XIL nosozlikni yopadi.

  * BO'SH massiv — "bozor hech qachon ochilmaydi", ya'ni tushum JIMGINA
    nolga tushardi;
  * `0`/`8` — `market_is_open()` dagi `EXTRACT(ISODOW ...)` bilan hech
    qachon mos kelmaydigan qiymat, ya'ni kun sababsiz yopiq bo'lib
    qolardi;
  * TAKRORIY — DB `CHECK` idan bemalol o'tadi (`<@` va `array_length`
    ikkalasi ham rozi), lekin foydalanuvchi uchta kun tanladim deb
    o'ylab, bittasini olgan bo'lardi.
"""


# ---------------------------------------------------------------------------
# Sessiyalar va yordamchilar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`STALL_MANAGE` + `MARKET_DATA_VIEW`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori direktorining sessiyasi — D-07 ning manfiy holati."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.director_phone, SEED_PASSWORD)


def _next_weekday(start: date, iso_weekday: int) -> date:
    """`start` dan KEYINGI shu hafta kuni (bugun bo'lsa — keyingi haftadagisi).

    Sana hech qachon o'tmishda bo'lmaydi, ya'ni `GET /calendar` ning
    "joriy yildan boshlab" filtri uni hech qachon kesib tashlamaydi.
    """
    ahead = (iso_weekday - start.isoweekday()) % 7
    return start + timedelta(days=ahead or 7)


def _is_open(conn: Connection[TupleRow], market_id: UUID, day: date) -> bool:
    row = conn.execute(IS_OPEN, (market_id, day)).fetchone()
    assert row is not None, "`market_is_open()` javob qaytarmadi"
    return bool(row[0])


async def _get_calendar(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.get(CALENDAR_URL, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _add_exception(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    exception_date: date,
    is_open: bool,
    note: str | None = HOLIDAY_NOTE,
) -> httpx.Response:
    return await client.post(
        EXCEPTIONS_URL,
        json={
            "exception_date": exception_date.isoformat(),
            "is_open": is_open,
            "note": note,
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Haftalik jadval (NAZORAT HOLATI birinchi turadi)
# ---------------------------------------------------------------------------


async def test_calendar_returns_the_seeded_weekly_schedule(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: `GET /calendar` seed'dagi jadvalni va BO'SH istisnolarni beradi.

    Fayldagi barcha keyingi testlar "o'zgarish yetib bordimi?" degan
    savolga javob beradi, ya'ni ularning hammasi BOSHLANG'ICH holat
    to'g'ri o'qilishiga tayanadi. Usiz endpoint doimiy bo'sh javob
    qaytarganda ham ba'zi testlar yashil bo'lardi.

    A bozorida istisno ATAYIN yo'q (`fixtures/market_domain.B_HOLIDAY`
    docstringi) — bo'sh ro'yxat shu yerda KUTILGAN natija, nuqson emas.
    """
    market_a = market_domain.market_a

    body = await _get_calendar(api_client, admin_headers)

    assert body["open_weekdays"] == list(market_a.open_weekdays)
    assert body["exceptions"] == [], "A bozorida seed istisnosi bo'lmasligi kerak"


async def test_weekdays_are_updated_and_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """`PUT /calendar/weekdays` yozadi, `GET` uni ko'radi va audit `old->new` ni saqlaydi.

    Haftalik jadvalni o'zgartirish istisno qo'yishdan ham KATTA ta'sirga
    ega: u bitta kunni emas, HAR HAFTADAGI o'sha kunni hisobdan chiqaradi.
    Undan qoladigan yagona iz — `market_profile` triggeri (T-02-65).

    ⚠ AUDIT QATORINI ROUTER YOZMAYDI. Aynan bitta `update` qatori
    kutiladi: ilova ham yozganda ular ikkita bo'lardi va jurnalni
    o'qiyotgan odam "nima ikki marta sodir bo'ldi?" degan savol bilan
    qolardi.
    """
    market_id = two_markets.market_a.id
    seeded = list(market_domain.market_a.open_weekdays)
    assert seeded != ALL_WEEKDAYS, "seed jadvali allaqachon to'liq — o'zgarish ko'rinmasdi"

    updated = await api_client.put(
        WEEKDAYS_URL, json={"open_weekdays": ALL_WEEKDAYS}, headers=admin_headers
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["open_weekdays"] == ALL_WEEKDAYS

    reread = await _get_calendar(api_client, admin_headers)
    assert reread["open_weekdays"] == ALL_WEEKDAYS

    with market_scope(market_id) as conn:
        rows = conn.execute(PROFILE_AUDIT, (str(market_id),)).fetchall()

    assert len(rows) == 1, f"aynan bitta audit qatori kutilgan edi (ikki marta yozuv?): {rows}"
    _action, old_value, new_value, changed_keys = rows[0]
    assert changed_keys is not None and "open_weekdays" in changed_keys
    assert old_value == seeded, f"auditdagi eski jadval {old_value}, seed'da {seeded}"
    assert new_value == ALL_WEEKDAYS


@pytest.mark.parametrize(
    ("label", "weekdays"), INVALID_WEEKDAYS, ids=[case[0] for case in INVALID_WEEKDAYS]
)
async def test_invalid_weekdays_are_rejected(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
    label: str,
    weekdays: list[int],
) -> None:
    """Bo'sh / oraliqdan tashqari / takroriy jadval -> 422 va DB'ga TEGILMAYDI.

    Uchala holatning sababi `INVALID_WEEKDAYS` docstringida. Javob 422
    (500 emas): DB `CHECK` konstrayti ikkinchi qatlam bo'lib qoladi, lekin
    u yerga yetib borgan so'rov foydalanuvchiga hech nima aytmaydigan
    ichki xato berardi.

    Jadval O'ZGARMAGANI ALOHIDA tekshiriladi: 422 qaytib, `UPDATE` baribir
    o'tib ketgan holat aks holda ko'rinmasdi.
    """
    market_id = two_markets.market_a.id
    seeded = list(market_domain.market_a.open_weekdays)

    response = await api_client.put(
        WEEKDAYS_URL, json={"open_weekdays": weekdays}, headers=admin_headers
    )

    assert response.status_code == 422, f"{label}: {response.text}"

    with market_scope(market_id) as conn:
        row = conn.execute(
            "SELECT open_weekdays FROM market_profile WHERE market_id = %s",
            (str(market_id),),
        ).fetchone()

    assert row is not None and row[0] == seeded, f"{label}: jadval baribir yozildi"


# ---------------------------------------------------------------------------
# Istisno kunlar — API yozadi, `market_is_open()` o'qiydi (D-18)
# ---------------------------------------------------------------------------


async def test_holiday_exception_closes_the_day(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Bayram ochiq kunni YOPADI va buni `market_is_open()` ko'radi (SC#4).

    Bu fayldagi ASOSIY da'vo: API orqali yozilgan istisno 6-fazaning
    kunlik job'i o'qiydigan AYNAN o'sha funksiyaga yetib boradi.
    Boshlang'ich holat (`true`) ham o'lchanadi — usiz test "istisno ta'sir
    qildi" ni "kun allaqachon yopiq edi" dan ajrata olmasdi.
    """
    market_id = two_markets.market_a.id
    assert TUESDAY in market_domain.market_a.open_weekdays, "seed jadvali o'zgargan"
    holiday = _next_weekday(market_today, TUESDAY)

    with market_scope(market_id) as conn:
        assert _is_open(conn, market_id, holiday) is True, "boshlang'ich holat noto'g'ri"

    created = await _add_exception(api_client, admin_headers, exception_date=holiday, is_open=False)
    assert created.status_code == 201, created.text
    assert created.json()["is_open"] is False
    assert created.json()["note"] == HOLIDAY_NOTE

    with market_scope(market_id) as conn:
        after = _is_open(conn, market_id, holiday)

    assert after is False, (
        "API orqali qo'yilgan bayram `market_is_open()` ga yetib bormadi — yopiq kunga "
        "patta hisoblanadi (SC#4 buzilgan)"
    )


async def test_exception_open_overrides_weekly_closure(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """«Bu dushanba ishlaymiz» — istisno haftalik jadvaldan USTUN (D-18).

    `test_holiday_exception_closes_the_day` ning TESKARI yo'nalishi va
    ikkalasi ham kerak: faqat "ochiqni yopish" ishlaydigan
    implementatsiya birinchi testdan o'tib, maxsus savdo kunini YOPIQ
    qoldirardi — ya'ni bozor ishlayotgan kunga patta yozilmasdi.
    """
    market_id = two_markets.market_a.id
    assert MONDAY not in market_domain.market_a.open_weekdays, "seed jadvali o'zgargan"
    special_day = _next_weekday(market_today, MONDAY)

    with market_scope(market_id) as conn:
        assert _is_open(conn, market_id, special_day) is False, "boshlang'ich holat noto'g'ri"

    created = await _add_exception(
        api_client, admin_headers, exception_date=special_day, is_open=True, note="Maxsus savdo"
    )
    assert created.status_code == 201, created.text

    with market_scope(market_id) as conn:
        after = _is_open(conn, market_id, special_day)

    assert after is True, "`is_open=true` istisnosi haftalik jadvaldan PASTDA turibdi"


async def test_exception_delete_restores_weekly_rule(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Istisno o'chirilgach kun HAFTALIK QOIDAGA qaytadi.

    Uch bosqichli zanjir (yopiq -> ochiq -> yopiq) ATAYIN: faqat "o'chirish
    204 qaytardi" ni tekshirish qator jimgina qolib ketgan holatni
    ushlamasdi — javob baribir 204 bo'lardi.
    """
    market_id = two_markets.market_a.id
    assert MONDAY not in market_domain.market_a.open_weekdays, "seed jadvali o'zgargan"
    special_day = _next_weekday(market_today, MONDAY)

    created = await _add_exception(
        api_client, admin_headers, exception_date=special_day, is_open=True, note=None
    )
    assert created.status_code == 201, created.text
    exception_id = created.json()["id"]

    with market_scope(market_id) as conn:
        assert _is_open(conn, market_id, special_day) is True

    removed = await api_client.delete(f"{EXCEPTIONS_URL}/{exception_id}", headers=admin_headers)
    assert removed.status_code == 204, removed.text

    with market_scope(market_id) as conn:
        restored = _is_open(conn, market_id, special_day)

    assert restored is False, "istisno o'chirilgandan keyin ham kun ochiq qoldi"


async def test_duplicate_exception_returns_409(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Bir sanaga IKKINCHI istisno -> 409 `calendar_exception_exists`.

    Unikalik `market_is_open()` ning ISHLASH SHARTI: ikkita qator bo'lsa
    uning skalyar subquery'si "more than one row returned by a subquery"
    bilan yiqilardi va BUTUN kunlik hisob-kitob to'xtardi (02-07 da
    o'lchangan). Javob 409, 500 EMAS — xom konstrayt xatosi
    foydalanuvchiga chiqmaydi.
    """
    holiday = _next_weekday(market_today, TUESDAY)

    first = await _add_exception(api_client, admin_headers, exception_date=holiday, is_open=False)
    assert first.status_code == 201, first.text

    second = await _add_exception(api_client, admin_headers, exception_date=holiday, is_open=True)

    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "calendar_exception_exists"


# ---------------------------------------------------------------------------
# Tenant izolyatsiyasi va huquq
# ---------------------------------------------------------------------------


async def test_cross_tenant_exception_returns_404(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """A tokeni + B bozorining istisnosi -> **404**, va aynan 403 EMAS.

    `status != 403` ALOHIDA assert qilinadi: faqat `== 404` bo'lganda
    kimdir javobni 403 ga o'zgartirsa, xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (qator MAVJUDLIGINI tasdiqlash — T-02-67) hech
    qayerda ko'rinmasdi.
    """
    foreign_exception = market_domain.market_b.calendar_exception_ids[0]

    response = await api_client.delete(
        f"{EXCEPTIONS_URL}/{foreign_exception}", headers=admin_headers
    )

    assert response.status_code != 403, "403 qator MAVJUDLIGINI tasdiqlaydi (T-02-67)"
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"


async def test_director_cannot_change_calendar(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    director_headers: dict[str, str],
) -> None:
    """Direktor kalendarni KO'RADI, lekin O'ZGARTIRA OLMAYDI (D-07, T-02-66).

    NAZORAT HOLATI (`GET` -> 200) MAJBURIY: usiz test direktorning
    sessiyasi umuman ishlamayotgan holatda ham yashil bo'lardi (har ikkala
    so'rov ham 401/403 berardi) va D-07 ning aynan mazmuni — "faqat yozish
    taqiqlangan" — sinovsiz qolardi.

    Ikkala YOZUV yo'li ham tekshiriladi: haftalik jadval va istisno
    alohida endpointlar, ya'ni biri ochiq qolishi mumkin edi.
    """
    forbidden_weekdays = await api_client.put(
        WEEKDAYS_URL, json={"open_weekdays": ALL_WEEKDAYS}, headers=director_headers
    )
    assert forbidden_weekdays.status_code == 403, forbidden_weekdays.text
    assert forbidden_weekdays.json()["detail"] == "forbidden"

    forbidden_exception = await _add_exception(
        api_client,
        director_headers,
        exception_date=_next_weekday(market_today, TUESDAY),
        is_open=False,
    )
    assert forbidden_exception.status_code == 403, forbidden_exception.text

    allowed = await _get_calendar(api_client, director_headers)
    assert allowed["open_weekdays"] == list(market_domain.market_a.open_weekdays)
