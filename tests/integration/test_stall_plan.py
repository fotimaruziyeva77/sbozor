"""`PUT /api/v1/stalls/plan` — PLAN-XARITANI QO'LDA CHIZISH (260820).

=============================================================================
⛔⛔ BU YO'L NIMA UCHUN BOR.

Sxematik xarita (`GET /stalls/map`) rastalarni ZONA bo'yicha guruhlab,
kod tartibida bir tekis panjaraga teradi. U har doim ishlaydi va hech
qanday sozlash talab qilmaydi — lekin u bozorning HAQIQIY shaklini
ko'rsatmaydi: qaysi qator qayerda, qaysi rasta kirish yo'liga yaqin,
qaysi burchak bo'sh.

Bozor admini bu shaklni O'ZI chizadi — rastani panjaraga qo'yib. Chizma
`stalls.plan_x` / `plan_y` da yashaydi va U IXTIYORIY: koordinata
qo'yilmagan bozor sxematik ko'rinishda ishlashda davom etadi (0026
migratsiyasi ustunlarni `NULL` qilib qo'shgani shuning uchun).

=============================================================================
⛔ NEGA BITTA `PUT`, «har rastaga bitta `PATCH`» EMAS.

Chizish paytida odam o'nlab rastani suradi. Har surish uchun alohida
so'rov yuborilsa: (a) yarmi ketib yarmi ketmasligi mumkin — chizma
YARIM saqlanardi; (b) 1000 rastali bozorda «Saqlash» 1000 so'rov
bo'lardi. Shuning uchun butun chizma BITTA tanada, bitta tranzaksiyada
yoziladi.

=============================================================================
⛔⛔ SANOQ SERVERDAN QAYTADI — VA BU TESTNING ASOSIY MAVZUSI.

`placed_count` klient yuborgan ro'yxatning UZUNLIGI emas, HAQIQATAN
o'zgargan qatorlar soni. Farq begona bozorning rastasi yuborilganda
ko'rinadi: RLS uni yangilamaydi, ya'ni sanoq kichik chiqadi. Agar
javob ro'yxat uzunligini qaytarsa, cross-tenant urinish «muvaffaqiyatli
saqlandi» ko'rinishida jimgina yutilardi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fixtures.admin_api import STALLS_URL, session_headers
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed

PLAN_URL = f"{STALLS_URL}/plan"
MAP_URL = f"{STALLS_URL}/map"

PLAN_BODY_KEYS = frozenset({"placed_count", "cleared_count"})
"""Javob kalitlarining AYNAN to'plami.

⛔ `stalls` YO'Q: chizmani muharrir ALLAQACHON biladi (u yuborgan), va
   javobda butun xaritani qaytarish 1000 rastali bozorda har «Saqlash»
   ni og'ir qilardi. Muharrir kerak bo'lsa `GET /stalls/map` ni qayta
   so'raydi.
"""


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori admini — `STALL_MANAGE` bor, ya'ni chiza oladi."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori direktori — xaritani KO'RADI, lekin ko'chira OLMAYDI (D-07)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def market_b_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """B bozori admini — cross-tenant urinishning MANBASI."""
    market_b = two_markets.market_b
    return await session_headers(api_client, market_b.admin_phone, market_b.admin_password)


def _cells(body: dict) -> dict[str, tuple[int | None, int | None]]:
    """Xarita javobini `{stall_id: (x, y)}` ga yig'adi."""
    return {
        cell["id"]: (cell["plan_x"], cell["plan_y"])
        for zone in body["zones"]
        for cell in zone["cells"]
    }


# ---------------------------------------------------------------------------
# Saqlash va o'qish
# ---------------------------------------------------------------------------


async def test_placed_coordinates_come_back_on_the_map(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Qo'yilgan koordinata AYNAN o'sha qiymat bilan xaritada qaytadi.

    ⛔ O'qish YO'LI BOSHQA: yozish `PUT /stalls/plan`, o'qish esa
       `GET /stalls/map`. Ikkalasi bitta testda o'lchanadi, chunki
       muharrir uchun ular BITTA zanjir — biri ikkinchisisiz foydasiz.
    """
    stall_ids = market_domain.market_a.stall_ids
    payload = {
        "placed": [
            {"stall_id": str(stall_ids[0]), "plan_x": 0, "plan_y": 0},
            {"stall_id": str(stall_ids[1]), "plan_x": 7, "plan_y": 3},
            {"stall_id": str(stall_ids[2]), "plan_x": 999, "plan_y": 999},
        ]
    }

    response = await api_client.put(PLAN_URL, headers=admin_headers, json=payload)
    assert response.status_code == 200, response.text
    assert set(response.json()) == PLAN_BODY_KEYS
    assert response.json() == {"placed_count": 3, "cleared_count": 0}

    map_body = (await api_client.get(MAP_URL, headers=admin_headers)).json()
    cells = _cells(map_body)
    assert cells[str(stall_ids[0])] == (0, 0)
    assert cells[str(stall_ids[1])] == (7, 3)
    assert cells[str(stall_ids[2])] == (999, 999)


async def test_unplaced_stalls_report_null_not_zero(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Chizilmagan rasta `null` beradi — `0` EMAS.

    ⛔⛔ `0` chizmaning CHAP-YUQORI burchagi, ya'ni haqiqiy joy. Agar
       chizilmagan rasta `0` bilan kelsa, muharrir hamma chizilmagan
       rastani bitta katakka bosib qo'yardi va odam «nega hammasi
       burchakda?» degan savol bilan qolardi.
    """
    map_body = (await api_client.get(MAP_URL, headers=admin_headers)).json()
    cells = _cells(map_body)

    assert cells, "xarita bo'sh — da'vo hech nimani isbotlamasdi"
    assert set(cells.values()) == {(None, None)}


async def test_placing_the_same_stall_again_moves_it(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Qayta qo'yish — KO'CHIRADI, ikkinchi nusxa yaratmaydi."""
    stall_id = str(market_domain.market_a.stall_ids[0])

    await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={"placed": [{"stall_id": stall_id, "plan_x": 2, "plan_y": 2}]},
    )
    response = await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={"placed": [{"stall_id": stall_id, "plan_x": 9, "plan_y": 4}]},
    )

    assert response.json() == {"placed_count": 1, "cleared_count": 0}
    cells = _cells((await api_client.get(MAP_URL, headers=admin_headers)).json())
    assert cells[stall_id] == (9, 4)


async def test_cleared_stall_returns_to_null(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """O'chirilgan rasta chizmadan CHIQADI va yana `null` bo'ladi.

    ⛔ Chizmani BUZISH ham chizishning bir qismi: noto'g'ri qo'yilgan
       rastani qaytarib ololmaslik odamni butun chizmani boshidan
       chizishga majburlardi.
    """
    stall_id = str(market_domain.market_a.stall_ids[0])
    await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={"placed": [{"stall_id": stall_id, "plan_x": 5, "plan_y": 5}]},
    )

    response = await api_client.put(
        PLAN_URL, headers=admin_headers, json={"cleared": [stall_id]}
    )

    assert response.json() == {"placed_count": 0, "cleared_count": 1}
    cells = _cells((await api_client.get(MAP_URL, headers=admin_headers)).json())
    assert cells[stall_id] == (None, None)


async def test_place_and_clear_in_one_request(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Bitta «Saqlash» — bir nechta qo'yish VA o'chirish, bitta tanada."""
    stall_ids = market_domain.market_a.stall_ids
    await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={
            "placed": [
                {"stall_id": str(stall_ids[0]), "plan_x": 1, "plan_y": 1},
                {"stall_id": str(stall_ids[1]), "plan_x": 2, "plan_y": 1},
            ]
        },
    )

    response = await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={
            "placed": [{"stall_id": str(stall_ids[2]), "plan_x": 3, "plan_y": 1}],
            "cleared": [str(stall_ids[0])],
        },
    )

    assert response.json() == {"placed_count": 1, "cleared_count": 1}
    cells = _cells((await api_client.get(MAP_URL, headers=admin_headers)).json())
    assert cells[str(stall_ids[0])] == (None, None)
    assert cells[str(stall_ids[1])] == (2, 1)
    assert cells[str(stall_ids[2])] == (3, 1)


async def test_empty_body_is_a_quiet_zero_not_an_error(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Hech nima o'zgarmagan «Saqlash» — 200 va 0/0.

    ⛔ Bu xato EMAS: odam muharrirni ochib, hech narsani surmasdan
       «Saqlash» bosishi mumkin. Unga qizil xato ko'rsatish «men nimani
       buzdim?» degan savol tug'dirardi — javobi esa «hech nimani».
    """
    response = await api_client.put(PLAN_URL, headers=admin_headers, json={})

    assert response.status_code == 200, response.text
    assert response.json() == {"placed_count": 0, "cleared_count": 0}


# ---------------------------------------------------------------------------
# Chegaralar — 0026 migratsiyasining CHECK konstraytlari
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("x", "y"),
    [(1000, 0), (0, 1000), (-1, 0), (0, -1)],
    ids=["x-katta", "y-katta", "x-manfiy", "y-manfiy"],
)
async def test_coordinates_outside_the_grid_are_rejected(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
    x: int,
    y: int,
) -> None:
    """Panjaradan tashqaridagi koordinata 422 — DB xatosi EMAS.

    ⛔⛔ Chegara IKKI JOYDA: sxemada (`ck_stalls_plan_x_range`) va
       Pydantic'da. Ikkinchisi birinchisining TAKRORI emas — u xatoni
       500 (`IntegrityError`) o'rniga 422 qilib beradi, ya'ni muharrir
       «qayerda xato» degan javobni oladi. Sxemadagisi esa xom SQL
       yo'lini ham yopadi.
    """
    payload = {
        "placed": [
            {"stall_id": str(market_domain.market_a.stall_ids[0]), "plan_x": x, "plan_y": y}
        ]
    }

    response = await api_client.put(PLAN_URL, headers=admin_headers, json=payload)

    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Huquq va ijara chegarasi
# ---------------------------------------------------------------------------


async def test_director_cannot_draw_the_plan(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    director_headers: dict[str, str],
) -> None:
    """Direktor xaritani KO'RADI, lekin chiza OLMAYDI (D-07).

    ⛔ Plan — bozor QURILISHI, kundalik kuzatuv emas. Direktorda
       `STALL_MANAGE` yo'q va bu ataylab: chizmani tasodifan surib
       yuborish hisobotdagi joyni o'zgartirardi.
    """
    payload = {
        "placed": [
            {"stall_id": str(market_domain.market_a.stall_ids[0]), "plan_x": 1, "plan_y": 1}
        ]
    }

    response = await api_client.put(PLAN_URL, headers=director_headers, json=payload)

    assert response.status_code == 403, response.text


async def test_foreign_stall_is_not_placed_and_the_count_says_so(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
    market_b_headers: dict[str, str],
) -> None:
    """⭐ B bozorining rastasi A ning chizmasiga TUSHMAYDI — va sanoq buni AYTADI.

    =======================================================================
    ⛔⛔ IKKI DA'VO, IKKALASI HAM ZARUR:

    1. B ning rastasi yangilanmaydi — RLS `UPDATE ... FROM unnest(...)`
       yo'lida ham ishlaydi (`market_id = :market_id` sharti + siyosat).

    2. `placed_count` = 1, YUBORILGAN 2 EMAS. Agar javob ro'yxat
       uzunligini qaytarsa, birinchi da'vo bajarilgan bo'lsa ham
       muharrir «ikkalasi ham saqlandi» deb ko'rsatardi — ya'ni
       izolyatsiya ISHLAYDI, lekin EKRAN yolg'on gapirardi.
    =======================================================================
    """
    own_stall = str(market_domain.market_a.stall_ids[0])
    foreign_stall = str(market_domain.market_b.stall_ids[0])

    response = await api_client.put(
        PLAN_URL,
        headers=admin_headers,
        json={
            "placed": [
                {"stall_id": own_stall, "plan_x": 4, "plan_y": 4},
                {"stall_id": foreign_stall, "plan_x": 5, "plan_y": 5},
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"placed_count": 1, "cleared_count": 0}

    with market_scope(two_markets.market_b.id) as conn:
        row = conn.execute(
            "SELECT plan_x, plan_y FROM stalls WHERE id = %s", (foreign_stall,)
        ).fetchone()
    assert row == (None, None), "B bozorining rastasi A tomonidan ko'chirilgan"

    b_cells = _cells((await api_client.get(MAP_URL, headers=market_b_headers)).json())
    assert b_cells[foreign_stall] == (None, None)


async def test_foreign_stall_cannot_be_cleared_either(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
    market_b_headers: dict[str, str],
) -> None:
    """O'CHIRISH yo'li ham chegarani hurmat qiladi.

    ⛔ Qo'yish tekshirildi degani o'chirish ham tekshirildi degani EMAS:
       ular ikki xil SQL (`_PLAN_PLACE` va `_PLAN_CLEAR`) va biri
       ikkinchisining qo'riqchisini meros olmaydi. Buzg'unchi uchun
       begona bozorning chizmasini O'CHIRISH uni ko'chirishdan ko'ra
       ARZONROQ hujum — u hech qanday koordinata bilishni talab qilmaydi.
    """
    foreign_stall = str(market_domain.market_b.stall_ids[0])
    await api_client.put(
        PLAN_URL,
        headers=market_b_headers,
        json={"placed": [{"stall_id": foreign_stall, "plan_x": 6, "plan_y": 6}]},
    )

    response = await api_client.put(
        PLAN_URL, headers=admin_headers, json={"cleared": [foreign_stall]}
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"placed_count": 0, "cleared_count": 0}

    with market_scope(two_markets.market_b.id) as conn:
        row = conn.execute(
            "SELECT plan_x, plan_y FROM stalls WHERE id = %s", (foreign_stall,)
        ).fetchone()
    assert row == (6, 6), "B bozorining chizmasi A tomonidan o'chirilgan"
