"""Tarif API'sining xulqi — MARKET-03 va SC#3 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL 02-07 DAGI `test_tariff_history.py` NING O'RNINI BOSMAYDI.

U SXEMA darajasida isbotlaydi: `trg_tariff_past_immutable` o'tgan sanali
qatorni `sbozor_owner` ning xom `UPDATE`/`DELETE` yo'lida ham `23514`
bilan rad etadi, `valid_to` ustuni umuman mavjud emas va tarifsiz kun 0
qator beradi. Bu yerdagi savol boshqa: **ilova qatlami o'sha kafolatlarni
foydalanuvchiga QANDAY ko'rsatadi** — qaysi HTTP kodi, qaysi `detail`,
javobda qaysi maydonlar.

Ikkisi bir-birini almashtira olmaydi. Sxema testi 500 bilan yiqiladigan
endpointda ham YASHIL qolardi; API testi esa trigger butunlay olib
tashlanganda "403 kelmadi" deb qizarardi, lekin SABABNI ko'rsata olmasdi.
=============================================================================

⚠ BOSHLANG'ICH NARX ISTISNOSI (T-02-63a) UCHTA TEST BILAN QAMRALGAN VA
ULAR BIRGA O'QILADI:

  * `test_initial_tariff_at_operating_since_is_accepted_on_draft_market`
    — istisno ROSTDAN ochiq (usiz qolgan ikkitasi "hammasi rad etiladi"
    degan yolg'on-yashil berardi);
  * `test_other_past_date_is_rejected_on_draft_market`
    — istisno AYNAN tenglik bo'yicha tor (`<=` yozilsa qoralama bozorda
    ixtiyoriy o'tmishga narx yozib bo'lardi);
  * `test_operating_since_is_rejected_after_activation`
    — istisno faollashtirishdan keyin BUTUNLAY yopiladi (usiz u faol
    bozorga sizib chiqqanini hech kim sezmasdi).

Birortasini olib tashlash qolgan ikkitasini ma'nosiz qiladi.

SANALAR `market_today` FIXTURE'IDAN HISOBLANADI, SOBIT YOZILMAYDI (02-07
deviatsiya #1): qotirilgan "kelajak" sanasi loyihaning O'Z muddati ichida
o'tmishga aylanib, nazorat holatini jimgina o'ldirardi. `operating_since`
esa sobit qolaveradi — u hech qachon kelajakka aylanmaydi.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import CATEGORIES_URL, TARIFFS_URL, session_headers
from fixtures.market_domain import A_OPERATING_SINCE, A_TARIFF_AMOUNTS
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from datetime import date

    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

FUTURE_DAYS = 30
"""«Kelajak» oralig'i — `market_today` dan hisoblanadi (sobit sana EMAS)."""

NEW_AMOUNT = 15_000
"""Seed'da UMUMAN uchramaydigan summa (`A_TARIFF_AMOUNTS` = 5000/12000/8000,
B = 7000).

Seed summalaridan biri ishlatilsa, so'rov NOTO'G'RI qatorni topganda ham
test yashil qolardi — 02-07 deviatsiya #2 da aynan shu xato tuzatilgan.
"""

SECOND_AMOUNT = 17_000
"""Uch qatorli tarix uchun ikkinchi yangi summa (`NEW_AMOUNT` dan farqli)."""

SET_MARKET_ACTIVE = "UPDATE markets SET is_active = %s WHERE id = %s"
"""Bozorni qoralama <-> faol holatiga o'tkazadi (`sbozor_owner` bilan).

⚠ `POST /markets/{id}/activate` ENDPOINTI HALI YO'Q — u 02-11 da
quriladi. Ya'ni bu test faollashtirishning YAKUNIY HOLATINI (bayroq
`true`) taqlid qiladi, oqimini emas. Darvoza aynan bayroqqa qaraydi
(`markets.is_active`), shuning uchun qamrov o'zgarmaydi: 02-11 endpointi
paydo bo'lganda u ham xuddi shu bayroqni ko'taradi.

`sbozor_owner` KERAK: `markets` policy'si `id = app.market_id` va
`sbozor_app` uchun u faqat O'QISH. Seed'ning `cleanup_market_domain()` i
ham aynan shu yo'ldan bayroqni tushiradi.
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
    """A bozori adminining sessiyasi (`TARIFF_MANAGE` + `MARKET_DATA_VIEW`).

    `market_domain` ATAYIN argument sifatida olinadi: domen qatlami
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi so'rov bo'sh
    tarif tarixini ko'rardi.
    """
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


def _set_active(conn: Connection[TupleRow], market_id: UUID, *, active: bool) -> None:
    """Bozorni faol/qoralama holatiga o'tkazadi (sabab konstanta docstringida)."""
    conn.execute(SET_MARKET_ACTIVE, (active, str(market_id)))


async def _new_category(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str,
) -> UUID:
    """API orqali TARIFSIZ toifa yaratadi.

    Seed'ning uchala A toifasida ham `operating_since` sanasida tarif BOR,
    ya'ni "boshlang'ich narx" testlari o'sha sanaga ikkinchi qator yozib
    409 olardi va 422/201 farqi umuman sinalmasdi. Toza toifa bu
    to'siqni olib tashlaydi va ayni paytda usta 4-qadamining haqiqiy
    boshlang'ich holatini takrorlaydi (D-13).
    """
    response = await client.post(CATEGORIES_URL, json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def _post_tariff(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    category_id: UUID,
    valid_from: date,
    amount_soum: int = NEW_AMOUNT,
) -> httpx.Response:
    return await client.post(
        TARIFFS_URL,
        json={
            "category_id": str(category_id),
            "amount_soum": amount_soum,
            "valid_from": valid_from.isoformat(),
        },
        headers=headers,
    )


async def _items(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    category_id: UUID | None = None,
) -> dict[str, Any]:
    params = {} if category_id is None else {"category": str(category_id)}
    response = await client.get(TARIFFS_URL, params=params, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


# ---------------------------------------------------------------------------
# D-06 — kelajakdagi narx (NAZORAT HOLATI birinchi turadi)
# ---------------------------------------------------------------------------


async def test_future_tariff_is_created(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: kelajakdagi `valid_from` -> 201, `is_past=false`, `valid_to=null`.

    Bu test fayldagi barcha rad etish testlaridan OLDIN turadi va usiz
    ular yolg'on-yashil berardi: darvoza HAR QANDAY sanani rad etadigan
    holga kelib qolsa (masalan solishtiruv teskari yozilsa), 422 kutayotgan
    testlar baribir o'tardi va yagona nosozlik "narx umuman kiritib
    bo'lmaydi" bo'lardi.

    `valid_to` `null`: bu toifada undan KEYINGI qator yo'q, ya'ni narx
    muddatsiz. Qiymat DB ustunidan emas, `LEAD()` dan keladi (Pitfall 9).
    """
    category_id = market_domain.market_a.category_ids[0]
    valid_from = market_today + timedelta(days=FUTURE_DAYS)

    response = await _post_tariff(
        api_client, admin_headers, category_id=category_id, valid_from=valid_from
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount_soum"] == NEW_AMOUNT
    assert body["valid_from"] == valid_from.isoformat()
    assert body["valid_to"] is None, "oxirgi qatorning amal qilish oxiri `null` bo'lishi kerak"
    assert body["is_past"] is False
    assert body["category_id"] == str(category_id)


@pytest.mark.parametrize("days_back", [0, 1], ids=["bugun", "kecha"])
async def test_past_valid_from_is_rejected_on_active_market(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
    days_back: int,
) -> None:
    """FAOL bozorda bugungi va o'tgan sana -> **422** `valid_from_must_be_future`.

    `bugun` holati alohida: chegara `>` bo'lishi shart, `>=` EMAS.
    6-fazaning kunlik job'i bugungi hisobni allaqachon yozgan bo'lishi
    mumkin, ya'ni "bugun" ham o'tmish (T-02-63).

    Javob 422, 403 EMAS: bu yerda mavjud qatorga umuman tegilmayapti — rad
    etilayotgani YANGI qatorning sanasi.
    """
    category_id = market_domain.market_a.category_ids[0]

    response = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=market_today - timedelta(days=days_back),
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "valid_from_must_be_future"


# ---------------------------------------------------------------------------
# T-02-63a — BOSHLANG'ICH NARX ISTISNOSI (uchtalik, birga o'qiladi)
# ---------------------------------------------------------------------------


async def test_initial_tariff_at_operating_since_is_accepted_on_draft_market(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
) -> None:
    """QORALAMA bozorda `valid_from == operating_since` -> **201** (A3 + D-13).

    UCHTALIKNING BIRINCHISI. Karmana bozori yillar davomida ishlab kelgan,
    ya'ni uning `operating_since` sanasi O'TMISHDA (seed'da 2026-01-15).
    02-11 dagi faollashtirish darvozasi esa har toifada `valid_from <=
    operating_since` bo'lgan tarifni TALAB qiladi — istisnosiz usta
    4-qadamda boshi berk ko'chaga tushardi.

    `is_past` javobda `true` va bu TO'G'RI: sana rostdan o'tmishda.
    Bayroq "tahrirlab bo'lmaydi" degani emas — qoralama bozorda D-07
    qulfi ham ochiq (trigger `is_active = false` ni istisno qiladi).
    """
    market_id = two_markets.market_a.id
    _set_active(sync_owner_conn, market_id, active=False)
    category_id = await _new_category(api_client, admin_headers, "Qoralama toifa")

    response = await _post_tariff(
        api_client, admin_headers, category_id=category_id, valid_from=A_OPERATING_SINCE
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["valid_from"] == A_OPERATING_SINCE.isoformat()
    assert body["is_past"] is True, "o'tgan sanadagi qator `is_past=true` bo'lishi kerak"

    with market_scope(market_id) as conn:
        row = conn.execute(
            "SELECT amount_soum, valid_from FROM tariffs WHERE market_id = %s AND category_id = %s",
            (str(market_id), str(category_id)),
        ).fetchone()

    assert row is not None, "boshlang'ich narx qatori yozilmadi"
    assert row[0] == NEW_AMOUNT
    assert row[1] == A_OPERATING_SINCE


@pytest.mark.parametrize("days_offset", [-1, 1], ids=["operating_since-1", "operating_since+1"])
async def test_other_past_date_is_rejected_on_draft_market(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
    days_offset: int,
) -> None:
    """QORALAMA bozorda BOSHQA o'tgan sana -> **422** — istisno TOR.

    UCHTALIKNING IKKINCHISI. Shart `valid_from == operating_since`, ya'ni
    AYNAN tenglik, va u IKKALA yo'nalishda ham qulflanishi kerak:

      * `operating_since - 1` — `<=` yozilgan implementatsiyadan bemalol
        o'tardi va istisno "har qanday o'tmish" ga aylanardi;
      * `operating_since + 1` — `>=` yozilgan implementatsiyadan o'tardi
        (o'sha sana ham o'tmishda, seed sanasi 2026-01-15).

    Faqat bittasi sinalganda solishtiruvning teskari tomoni ochiq qolardi
    va sabab hech qayerda ko'rinmasdi. Ikkala sana ham `operating_since`
    ga eng yaqin holat, ya'ni chegaraning HARFINI o'lchaydi.
    """
    market_id = two_markets.market_a.id
    _set_active(sync_owner_conn, market_id, active=False)
    category_id = await _new_category(api_client, admin_headers, f"Chegara {days_offset}")

    response = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=A_OPERATING_SINCE + timedelta(days=days_offset),
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "valid_from_must_be_future"


async def test_operating_since_is_rejected_after_activation(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
) -> None:
    """Faollashtirishdan KEYIN o'sha sana -> **422** — istisno YOPILDI.

    UCHTALIKNING UCHINCHISI va u regressiya darvozasi: `markets.is_active`
    sharti tushib qolsa (masalan "soddalashtirish" uchun), birinchi ikki
    test baribir yashil qolardi — istisno esa FAOL bozorga sizib chiqqan
    bo'lardi va o'sha bozorda `daily_charges` allaqachon yozilgan
    bo'lishi mumkin (T-02-63a).

    Qoralama holatidagi 201 shu yerda ham tekshiriladi: usiz test
    "faollashtirish yopdi" ni "istisno hech qachon ochilmagan" dan ajrata
    olmasdi.
    """
    market_id = two_markets.market_a.id

    _set_active(sync_owner_conn, market_id, active=False)
    draft_category = await _new_category(api_client, admin_headers, "Qoralama oynasi")
    opened = await _post_tariff(
        api_client, admin_headers, category_id=draft_category, valid_from=A_OPERATING_SINCE
    )
    assert opened.status_code == 201, f"qoralama tarmoq ochiq bo'lishi kerak edi: {opened.text}"

    _set_active(sync_owner_conn, market_id, active=True)
    active_category = await _new_category(api_client, admin_headers, "Faol oyna")
    closed = await _post_tariff(
        api_client, admin_headers, category_id=active_category, valid_from=A_OPERATING_SINCE
    )

    assert closed.status_code == 422, closed.text
    assert closed.json()["detail"] == "valid_from_must_be_future"


async def test_min_valid_from_matches_market_state(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
) -> None:
    """`min_valid_from` bozor HOLATIDAN kelib chiqadi va BO'SH ro'yxatda ham keladi.

    Qoralama bozorda u `operating_since`, faol bozorda `bugun + 1`. Klient
    uni sana maydonining `min` atributiga qo'yadi (02-15) — shu bilan
    "server ruxsat bergan sanani UI taqiqlab qo'yishi" strukturaviy
    imkonsiz bo'ladi.

    BO'SH RO'YXAT HOLATI ALOHIDA TEKSHIRILADI: usta 4-qadami aynan bo'sh
    ro'yxatdan boshlanadi va o'sha ekranda sana chegarasi allaqachon
    kerak. Maydon `| None` bo'lganda uni "unutish" mumkin bo'lardi va
    unutilgan joyda sana maydoni chegarasiz ochilib qolardi.
    """
    market_id = two_markets.market_a.id
    empty_category = await _new_category(api_client, admin_headers, "Bo'sh toifa")

    _set_active(sync_owner_conn, market_id, active=False)
    draft = await _items(api_client, admin_headers, category_id=empty_category)
    assert draft["items"] == [], "toza toifada tarif bo'lmasligi kerak"
    assert draft["min_valid_from"] == A_OPERATING_SINCE.isoformat()

    _set_active(sync_owner_conn, market_id, active=True)
    active = await _items(api_client, admin_headers, category_id=empty_category)
    assert active["items"] == []
    assert active["min_valid_from"] == (market_today + timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# D-06 — takroriy sana va hisoblanadigan `valid_to`
# ---------------------------------------------------------------------------


async def test_duplicate_valid_from_returns_409(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Bir toifaga bir sanada IKKINCHI narx -> 409 `tariff_already_set_for_date`.

    `uq_tariffs_market_id_category_id_valid_from` (D-06). Javob 409, 500
    EMAS: xom konstrayt xatosi foydalanuvchiga chiqmasligi kerak
    (T-02-58).
    """
    category_id = market_domain.market_a.category_ids[0]
    valid_from = market_today + timedelta(days=FUTURE_DAYS)

    first = await _post_tariff(
        api_client, admin_headers, category_id=category_id, valid_from=valid_from
    )
    assert first.status_code == 201, first.text

    second = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=valid_from,
        amount_soum=SECOND_AMOUNT,
    )

    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "tariff_already_set_for_date"


async def test_valid_to_is_computed_from_next_row(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Uch qatorli tarixda o'rtadagi qatorning `valid_to` = keyingisining `valid_from`.

    `valid_to` DB'da USTUN EMAS (Pitfall 9) — u `LEAD(valid_from) OVER
    (PARTITION BY market_id, category_id ORDER BY valid_from)` bilan
    hisoblanadi. Ustun sifatida saqlansa ikkinchi haqiqat manbai bo'lardi
    va ikkalasi bir kun ajralib ketardi.

    Uchinchi qator MAJBURIY: ikki qatorda "oxirgisi `null`, oldingisi
    keyingisiga teng" da'vosi tasodifan ham to'g'ri chiqishi mumkin edi.

    ⚠ QATORLAR ATAYIN TESKARI TARTIBDA YOZILADI (avval KEYINGISI, so'ng
    oldingisi) va ikkinchi `POST` NING JAVOBI ham tekshiriladi. Sabab
    strukturaviy: yozuvdan keyingi javob BITTA qatorni o'qiydi, oyna
    funksiyasi esa butun toifa tarixi ustida hisoblanishi kerak. Filtr
    oyna ICHIGA tushib qolsa (eng tabiiy "soddalashtirish") `valid_to`
    o'sha javobda HAR DOIM `null` bo'lardi, ro'yxatda esa to'g'ri
    chiqardi — ikki javob bir-biriga zid bo'lib, sabab kodga qarab
    umuman ko'rinmasdi.
    """
    category_id = market_domain.market_a.category_ids[0]
    first_future = market_today + timedelta(days=FUTURE_DAYS)
    second_future = market_today + timedelta(days=FUTURE_DAYS * 2)

    later = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=second_future,
        amount_soum=SECOND_AMOUNT,
    )
    assert later.status_code == 201, later.text
    assert later.json()["valid_to"] is None

    earlier = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=first_future,
        amount_soum=NEW_AMOUNT,
    )
    assert earlier.status_code == 201, earlier.text
    assert earlier.json()["valid_to"] == second_future.isoformat(), (
        "yozuvdan keyingi javobda `valid_to` hisoblanmadi — oyna funksiyasi "
        "faqat bitta qatorni ko'ryapti"
    )

    body = await _items(api_client, admin_headers, category_id=category_id)
    rows = body["items"]

    # Tartib: `valid_from` KAMAYISH bo'yicha, ya'ni eng yangisi birinchi.
    assert [row["valid_from"] for row in rows] == [
        second_future.isoformat(),
        first_future.isoformat(),
        A_OPERATING_SINCE.isoformat(),
    ]
    assert rows[0]["valid_to"] is None, "eng yangi qator muddatsiz bo'lishi kerak"
    assert rows[1]["valid_to"] == second_future.isoformat()
    assert rows[2]["valid_to"] == first_future.isoformat()

    assert [row["is_past"] for row in rows] == [False, False, True]
    # Seed narxi o'zgarmagan — yangi qatorlar eski qatorga TEGMAYDI (D-06).
    assert rows[2]["amount_soum"] == A_TARIFF_AMOUNTS[0]


# ---------------------------------------------------------------------------
# D-07 — o'tmish qulfi (NAZORAT HOLATI rad etishdan OLDIN)
# ---------------------------------------------------------------------------


async def test_future_tariff_patch_and_delete_succeed(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: KELAJAKDAGI qator tahrirlanadi (200) va o'chiriladi (204).

    Usiz quyidagi ikkita 403 testi hech nimani isbotlamasdi: `PATCH`/`DELETE`
    umuman ishlamayotgan (masalan har doim 403 qaytaradigan) endpointda ham
    ular yashil bo'lardi va D-07 ning aynan mazmuni — "faqat O'TMISH
    qulflangan" — sinovsiz qolardi.
    """
    category_id = market_domain.market_a.category_ids[0]
    valid_from = market_today + timedelta(days=FUTURE_DAYS)

    created = await _post_tariff(
        api_client, admin_headers, category_id=category_id, valid_from=valid_from
    )
    assert created.status_code == 201, created.text
    tariff_id = created.json()["id"]

    patched = await api_client.patch(
        f"{TARIFFS_URL}/{tariff_id}",
        json={"amount_soum": SECOND_AMOUNT},
        headers=admin_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["amount_soum"] == SECOND_AMOUNT

    removed = await api_client.delete(f"{TARIFFS_URL}/{tariff_id}", headers=admin_headers)
    assert removed.status_code == 204, removed.text


async def test_past_tariff_patch_returns_403(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """O'TGAN sanali qatorni tahrirlash -> **403** `tariff_past_locked`.

    Kafolat DB triggerida (`trg_tariff_past_immutable`, `23514`), bu test
    esa uning ILOVA tomonidagi tarjimasini qulflaydi. Javob AYNAN 403:
    o'tmish hech kimga ochiq emas, ya'ni bu HUQUQ masalasi — 409 (konflikt)
    va 422 (shakl) ikkalasi ham noto'g'ri ma'no berardi.

    `detail` ham tekshiriladi: faqat `403` ni tekshirish huquq
    tekshiruvining o'zi yiqilganda (masalan `TARIFF_MANAGE` olib
    tashlanganda, `forbidden`) ham yashil qolardi.
    """
    tariff_id = market_domain.market_a.tariff_ids[0]

    response = await api_client.patch(
        f"{TARIFFS_URL}/{tariff_id}",
        json={"amount_soum": SECOND_AMOUNT},
        headers=admin_headers,
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "tariff_past_locked"


async def test_past_tariff_delete_returns_403(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """O'TGAN sanali qatorni o'chirish -> **403** va qator JOYIDA qoladi.

    `PATCH` jufti bilan birga o'qiladi: trigger `BEFORE UPDATE OR DELETE`,
    ya'ni ikkala amal ham qamralishi shart. Faqat bittasi sinalsa, ikkinchi
    yo'l orqali o'tmishdagi narxni butunlay yo'q qilish mumkin bo'lardi.

    Qator MAVJUDLIGI ALOHIDA tekshiriladi: istisno ko'tarilib, amal
    qisman o'tib ketgan holat aks holda ko'rinmasdi (02-07 dagi bilan bir
    xil qoida).
    """
    market_id = two_markets.market_a.id
    tariff_id = market_domain.market_a.tariff_ids[0]

    response = await api_client.delete(f"{TARIFFS_URL}/{tariff_id}", headers=admin_headers)

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "tariff_past_locked"

    with market_scope(market_id) as conn:
        row = conn.execute(
            "SELECT amount_soum FROM tariffs WHERE market_id = %s AND id = %s",
            (str(market_id), str(tariff_id)),
        ).fetchone()

    assert row is not None, "403 qaytdi, lekin qator baribir o'chib ketdi"
    assert row[0] == A_TARIFF_AMOUNTS[0]


async def test_patch_cannot_move_a_tariff_into_the_past(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """KELAJAKDAGI qatorni O'TMISHGA surish -> **422** (T-02-63 ning yon kanali).

    ⚠ BU DARVOZANI DB TRIGGERI QAMRAMAYDI: `trg_tariff_past_immutable`
    faqat `OLD.valid_from` ni tekshiradi, ya'ni kelajakdagi qatorni
    o'tmishga ko'chirish uning uchun butunlay qonuniy `UPDATE`.

    Darvozasiz `POST` tekshiruvi (T-02-63) IKKI QADAMDA chetlab
    o'tilardi: avval kelajakka narx yoziladi (ruxsat etilgan), so'ng
    uning sanasi kechagi kunga suriladi — va o'tmishdagi hisob jimgina
    qayta baholanadi.

    Qatorning sanasi O'ZGARMAGANI ALOHIDA tekshiriladi: 422 qaytib,
    `UPDATE` baribir o'tib ketgan holat aks holda ko'rinmasdi.
    """
    market_id = two_markets.market_a.id
    category_id = market_domain.market_a.category_ids[0]
    valid_from = market_today + timedelta(days=FUTURE_DAYS)

    created = await _post_tariff(
        api_client, admin_headers, category_id=category_id, valid_from=valid_from
    )
    assert created.status_code == 201, created.text
    tariff_id = created.json()["id"]

    response = await api_client.patch(
        f"{TARIFFS_URL}/{tariff_id}",
        json={"valid_from": (market_today - timedelta(days=1)).isoformat()},
        headers=admin_headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "valid_from_must_be_future"

    with market_scope(market_id) as conn:
        row = conn.execute(
            "SELECT valid_from FROM tariffs WHERE market_id = %s AND id = %s",
            (str(market_id), tariff_id),
        ).fetchone()

    assert row is not None and row[0] == valid_from, "422 qaytdi, lekin sana baribir surildi"


# ---------------------------------------------------------------------------
# Tenant izolyatsiyasi, huquq va audit
# ---------------------------------------------------------------------------


async def test_cross_tenant_tariff_returns_404(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """A tokeni + B bozorining `tariff_id` si -> **404**, va aynan 403 EMAS.

    `status != 403` ALOHIDA assert qilinadi: faqat `== 404` bo'lganda
    kimdir javobni 403 ga o'zgartirsa, xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (qator MAVJUDLIGINI tasdiqlash — T-02-67) hech
    qayerda ko'rinmasdi.
    """
    foreign_tariff = market_domain.market_b.tariff_ids[0]

    response = await api_client.delete(f"{TARIFFS_URL}/{foreign_tariff}", headers=admin_headers)

    assert response.status_code != 403, "403 qator MAVJUDLIGINI tasdiqlaydi (T-02-67)"
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"


async def test_director_cannot_manage_tariffs(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    director_headers: dict[str, str],
) -> None:
    """Direktor narx tarixini KO'RADI, lekin O'ZGARTIRA OLMAYDI (D-07, T-02-66).

    NAZORAT HOLATI (`GET` -> 200) MAJBURIY: usiz test direktorning
    sessiyasi umuman ishlamayotgan holatda ham yashil bo'lardi (har ikkala
    so'rov ham 401/403 berardi) va D-07 ning aynan mazmuni — "faqat yozish
    taqiqlangan" — sinovsiz qolardi.
    """
    category_id = market_domain.market_a.category_ids[0]

    forbidden = await _post_tariff(
        api_client,
        director_headers,
        category_id=category_id,
        valid_from=market_today + timedelta(days=FUTURE_DAYS),
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["detail"] == "forbidden"

    allowed = await api_client.get(TARIFFS_URL, headers=director_headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["items"], "direktor uchun tarif tarixi bo'sh qaytdi"


async def test_tariff_creation_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Yangi narx `audit_log` da ko'rinadi — YOZUVNI DB TRIGGERI qiladi.

    `tariffs` `AUDITED_TABLES` da va `fn_audit_row()` triggeri ostida
    (02-05), ya'ni router `write_app_audit()` chaqirmaydi. Bu test ayni
    paytda o'sha qarorni ham tekshiradi: agar ilova ham yozsa, jurnalda
    AYNAN o'sha `row_id` uchun IKKITA `insert` qatori paydo bo'lardi.
    """
    market_id = two_markets.market_a.id
    category_id = market_domain.market_a.category_ids[0]

    created = await _post_tariff(
        api_client,
        admin_headers,
        category_id=category_id,
        valid_from=market_today + timedelta(days=FUTURE_DAYS),
    )
    assert created.status_code == 201, created.text
    tariff_id = created.json()["id"]

    with market_scope(market_id) as conn:
        rows = conn.execute(
            "SELECT action, source, new_value->>'amount_soum' FROM audit_log "
            "WHERE market_id = %s AND table_name = 'tariffs' AND row_id = %s ORDER BY id",
            (str(market_id), tariff_id),
        ).fetchall()

    assert len(rows) == 1, f"aynan bitta audit qatori kutilgan edi (ikki marta yozuv?): {rows}"
    assert rows[0][0] == "insert"
    assert rows[0][1] == "db_trigger", "yozuvni ilova emas, DB triggeri qilishi kerak"
    assert rows[0][2] == str(NEW_AMOUNT)
