"""Rasta reestrining API xulqi — SC#2 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL 02-07 DAGI DB TESTLARINING O'RNINI BOSMAYDI — U ULARNING USTIGA
QURILADI.

`tests/integration/test_stall_code_reuse.py` (02-07) SXEMA darajasida
isbotlaydi: `trg_stall_code_claim` chetlangan kodni rad etadi, holat
o'zgarishlari `fn_audit_row()` bilan qayd etiladi, xom SQL yo'li ham
qamraladi. Bu yerdagi savol boshqa: **ilova qatlami o'sha kafolatlarni
foydalanuvchiga QANDAY ko'rsatadi** — qaysi HTTP kodi, qaysi `detail`,
qaysi tartib va qaysi sahifa.

Ikkisi bir-birini almashtira olmaydi. Sxema testi 500 bilan yiqiladigan
endpointda ham YASHIL qolardi; API testi esa trigger butunlay olib
tashlanganda "409 kelmadi" deb qizarardi, lekin SABABNI ko'rsata olmasdi.

⚠ TOIFA DAVRINING O'TMISH DARVOZASI FAQAT SHU YERDA QAMRALGAN.
02-07 `stall_category_periods` uchun `UPDATE`/`DELETE` yo'lini sinaydi
(`trg_category_period_past_immutable` aynan shu ikkalasiga ulangan), lekin
`INSERT` yo'lini HECH KIM sinamaydi va sinay olmaydi ham — trigger unda
strukturaviy ravishda ishga tushmaydi. Darvoza ilova qatlamida
(`StallRepository.set_category()`) va uning yagona isboti — quyidagi
to'rtlik (kelajak -> 201, bugun -> 403, o'tmish -> 403, boshlang'ich davr
yaratish oqimida).
=============================================================================

SANALAR `market_today` FIXTURE'IDAN HISOBLANADI, SOBIT YOZILMAYDI (02-07
deviatsiya #1): qotirilgan "kelajak" sanasi loyihaning O'Z muddati ichida
o'tmishga aylanib, nazorat holatini jimgina o'ldirardi.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import CATEGORIES_URL, STALLS_URL, ZONES_URL, session_headers
from fixtures.market_domain import (
    A_OPERATING_SINCE,
    A_STALL_CODES,
    A_STALL_CODES_BY_SORT,
    A_ZONE_NAMES,
    B_TARIFF_AMOUNT,
)
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from datetime import date

    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed

FUTURE_DAYS = 30
"""«Kelajak» oralig'i — `market_today` dan hisoblanadi (sobit sana EMAS)."""

NEW_CODE = "9001"
"""Seed'da UMUMAN uchramaydigan rasta raqami (`A_STALL_CODES` bilan solishtiring).

Seed kodlaridan biri ishlatilsa test `stall_code_taken` bilan yiqilardi va
sabab "yaratish ishlamayapti" bo'lib ko'rinardi.
"""

RENAMED_CODE = "9002"
"""Kod tahriri testlari uchun ikkinchi bo'sh raqam."""


# ---------------------------------------------------------------------------
# Sessiyalar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`STALL_MANAGE` + `MARKET_DATA_VIEW`).

    `market_domain` ATAYIN argument sifatida olinadi: domen qatlami
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi so'rov bo'sh
    reestrni ko'rardi va testlar "hech narsa yo'q" bilan "izolyatsiya
    ishladi" ni ajrata olmasdi.
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


@pytest.fixture
async def market_b_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """B bozori adminining sessiyasi (tarifsiz toifa holati B da)."""
    market_b = two_markets.market_b
    return await session_headers(api_client, market_b.admin_phone, market_b.admin_password)


def _create_payload(domain: MarketDomainSeed, code: str = NEW_CODE, **extra: Any) -> dict[str, Any]:
    """`POST /stalls` uchun yaroqli tana (A bozorining zona va toifasi bilan)."""
    market_a = domain.market_a
    return {
        "code": code,
        "zone_id": str(market_a.zone_ids[0]),
        "category_id": str(market_a.category_ids[0]),
        **extra,
    }


# ---------------------------------------------------------------------------
# SC#2 — holat o'tishi, kod konflikti, cross-tenant
# ---------------------------------------------------------------------------


async def test_stall_status_transitions_are_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """`active -> maintenance -> closed` — har o'tish 200 va auditda iz qoldiradi.

    SC#2 ning ikkinchi yarmi. Audit qatorini ILOVA yozmaydi —
    `fn_audit_row()` triggeri yozadi (02-05), ya'ni bu test ayni paytda
    "endpoint ORM orqali o'tadimi?" savoliga ham javob beradi: xom
    `session.execute(update(...))` ham trigger ostida qoladi.
    """
    stall_id = market_domain.market_a.unassigned_stall_id
    assert stall_id is not None

    for status_value in ("maintenance", "closed"):
        response = await api_client.patch(
            f"{STALLS_URL}/{stall_id}",
            json={"status": status_value},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status_value

    with market_scope(two_markets.market_a.id) as conn:
        rows = conn.execute(
            "SELECT changed_keys, old_value->>'status', new_value->>'status' "
            "FROM audit_log "
            "WHERE market_id = %s AND table_name = 'stalls' AND row_id = %s AND action = 'update' "
            "ORDER BY id",
            (str(two_markets.market_a.id), str(stall_id)),
        ).fetchall()

    assert len(rows) == 2, f"ikkita o'tish kutilgan edi, jurnalda: {rows}"
    assert [row[1] for row in rows] == ["active", "maintenance"]
    assert [row[2] for row in rows] == ["maintenance", "closed"]
    for changed_keys, _old, _new in rows:
        assert "status" in changed_keys


async def test_code_edit_returns_409_when_retired(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Bo'shab qolgan raqamni YANGI rastaga berish -> **409** `stall_code_retired`.

    D-02 ning butun mazmuni: raqam bozorda BIR MARTA ishlatiladi. Javob
    aynan 409 bo'lishi shart — 403 (huquq masalasi emas) va 500 (xom
    konstrayt xatosi foydalanuvchiga chiqishi) ikkalasi ham noto'g'ri.

    `detail` kodi ham tekshiriladi: `stall_code_taken` bilan bir xil
    SQLSTATE (`23505`) keladi va ularni faqat xato MATNI ajratadi
    (`RETIRED_CODE_MARKER`). Faqat `409` ni tekshirish D-02 mexanizmi
    umuman yo'q bo'lganda ham yashil qolardi.
    """
    stall_id = market_domain.market_a.unassigned_stall_id
    assert stall_id is not None
    freed_code = A_STALL_CODES[market_domain.market_a.stall_ids.index(stall_id)]

    renamed = await api_client.patch(
        f"{STALLS_URL}/{stall_id}",
        json={"code": RENAMED_CODE},
        headers=admin_headers,
    )
    assert renamed.status_code == 200, renamed.text

    response = await api_client.post(
        STALLS_URL,
        json=_create_payload(market_domain, code=freed_code),
        headers=admin_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "stall_code_retired"


async def test_code_edit_returns_409_when_taken(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """HOZIR band raqamga tahrirlash -> 409 `stall_code_taken`.

    `test_code_edit_returns_409_when_retired` ning JUFTI: ikkala holat ham
    `23505` beradi, lekin foydalanuvchi uchun ular butunlay boshqacha
    ("bu raqam hozir band" va "bu raqam qaytarilmaydi"). Ikkovi bir xil
    `detail` bilan qaytarilsa, chetlangan kod mexanizmi jimgina yo'qolib
    ketishi mumkin edi va hech kim sezmasdi.
    """
    market_a = market_domain.market_a
    source_id = market_a.stall_ids[0]
    taken_code = A_STALL_CODES[1]

    response = await api_client.patch(
        f"{STALLS_URL}/{source_id}",
        json={"code": taken_code},
        headers=admin_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "stall_code_taken"


async def test_cross_tenant_stall_returns_404(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """A tokeni + B bozorining `stall_id` si -> **404**, va aynan 403 EMAS.

    `status != 403` ALOHIDA assert qilinadi: faqat `== 404` bo'lganda
    kimdir javobni 403 ga o'zgartirsa, xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (obyekt MAVJUDLIGINI tasdiqlash — T-02-55) hech
    qayerda ko'rinmasdi.
    """
    foreign_stall = market_domain.market_b.stall_ids[0]

    response = await api_client.get(f"{STALLS_URL}/{foreign_stall}", headers=admin_headers)

    assert response.status_code != 403, "403 obyekt MAVJUDLIGINI tasdiqlaydi (T-02-55)"
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"


async def test_market_id_in_body_is_ignored(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """So'rov tanasidagi `market_id` E'TIBORSIZ qoldiriladi (T-02-54).

    Mass-assignment darvozasi: `StallCreateRequest` da bunday maydon
    UMUMAN e'lon qilinmagan, ya'ni Pydantic uni jimgina tashlab yuboradi
    va bozor faqat `principal.market_id` dan olinadi.

    IKKI TOMONLAMA tekshiriladi: qator A bozorida BOR va B bozorida
    YO'Q. Faqat birinchisi tekshirilsa, qator ikkala bozorda ham paydo
    bo'lgan holatda test yashil qolardi.
    """
    payload = _create_payload(market_domain, market_id=str(two_markets.market_b.id))

    response = await api_client.post(STALLS_URL, json=payload, headers=admin_headers)

    assert response.status_code == 201, response.text
    created_id = UUID(response.json()["id"])

    with market_scope(two_markets.market_a.id) as conn:
        in_a = conn.execute(
            "SELECT count(*) FROM stalls WHERE id = %s", (str(created_id),)
        ).fetchone()
    with market_scope(two_markets.market_b.id) as conn:
        in_b = conn.execute(
            "SELECT count(*) FROM stalls WHERE id = %s", (str(created_id),)
        ).fetchone()

    assert in_a is not None and in_a[0] == 1, "rasta A bozorida yaratilishi kerak edi"
    assert in_b is not None and in_b[0] == 0, "rasta B bozoriga sizib o'tdi (mass-assignment)"


# ---------------------------------------------------------------------------
# Ro'yxat — tartib, sahifalash, filtrlar
# ---------------------------------------------------------------------------


async def test_stall_list_is_in_human_numeric_order(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """`GET /stalls` -> `2, 3, 7, 10, 55, 100` (inson-raqamli, matn tartibi EMAS).

    Kutilgan ro'yxat seed modulidagi QO'LDA yozilgan konstantadan olinadi
    (`A_STALL_CODES_BY_SORT`), test ichida hisoblanmaydi: hisoblangan
    kutilma `code_sort` ifodasining o'z mantiqini takrorlardi va ikkalasi
    birga xato bo'lganda test yashil qolardi.

    Matn tartibi (`10, 100, 2, 3, 55, 7`) bilan farq qilishi seed
    kodlarining ATAYIN tanlanganidan kelib chiqadi.
    """
    response = await api_client.get(STALLS_URL, params={"limit": 200}, headers=admin_headers)

    assert response.status_code == 200, response.text
    codes = [item["code"] for item in response.json()["items"]]
    assert codes == list(A_STALL_CODES_BY_SORT)
    assert response.json()["next_cursor"] is None


async def test_stall_list_is_keyset_paginated(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """`limit=2` bilan uch sahifa aylanadi va elementlar TAKRORLANMAYDI.

    Takrorlanmaslik shartsiz emas: kursor `code_sort` o'rniga `code`
    bo'yicha qurilsa, sahifa chegarasida qatorlar ham takrorlanardi, ham
    tushib qolardi — va umumiy son baribir "yaqin" bo'lib ko'rinardi.
    Shuning uchun uchala da'vo ham tekshiriladi: takror yo'q, TARTIB
    saqlanadi, oxirgi sahifada kursor `null`.
    """
    seen: list[str] = []
    cursor: str | None = None
    pages = 0

    while True:
        params: dict[str, Any] = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = await api_client.get(STALLS_URL, params=params, headers=admin_headers)
        assert response.status_code == 200, response.text

        body = response.json()
        seen.extend(item["code"] for item in body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
        assert pages <= len(A_STALL_CODES), "kursor tugamadi — cheksiz sikl xavfi"

    assert pages == 3, f"6 rasta / 2 = 3 sahifa kutilgan edi, olingani: {pages}"
    assert len(seen) == len(set(seen)), f"sahifalar orasida takror: {seen}"
    assert seen == list(A_STALL_CODES_BY_SORT)


async def test_stall_list_respects_filters(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """`status` va `zone` filtrlari kutilgan sonni beradi.

    Har bir filtr NAZORAT bilan keladi (filtrsiz so'rov 6 ta beradi):
    filtr umuman qo'llanmaganda ham "natija bor" bo'lardi, shuning uchun
    yagona ma'noli da'vo — SONNING FARQI.
    """
    market_a = market_domain.market_a
    closed_stall = market_a.stall_ids[0]

    patched = await api_client.patch(
        f"{STALLS_URL}/{closed_stall}",
        json={"status": "closed"},
        headers=admin_headers,
    )
    assert patched.status_code == 200, patched.text

    async def _count(params: dict[str, Any]) -> int:
        response = await api_client.get(
            STALLS_URL, params={"limit": 200, **params}, headers=admin_headers
        )
        assert response.status_code == 200, response.text
        return len(response.json()["items"])

    assert await _count({}) == len(A_STALL_CODES)
    assert await _count({"status": "closed"}) == 1
    assert await _count({"status": "active"}) == len(A_STALL_CODES) - 1
    # Zonalar rastalar bo'ylab aylanma taqsimlangan: 6 rasta / 3 zona = 2.
    assert await _count({"zone": str(market_a.zone_ids[0])}) == 2


async def test_map_groups_by_zone_in_code_order(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """`GET /stalls/map` — zonalar NOM tartibida, kataklar `code_sort` tartibida.

    ZONA TARTIBI DB'DAN OLINGAN JAVOB BILAN solishtiriladi, Python'ning
    `sorted()` i bilan EMAS: matn tartibi Postgres kolatsiyasiga bog'liq
    (`G'arbiy` dagi apostrof turli kolatsiyada turlicha joylashadi) va
    kutilmani Python tomonda qayta qurish ikkinchi, ajralib ketadigan
    haqiqat manbai bo'lardi. Test "server tartibni O'ZI hal qiladi va u
    `ORDER BY name`" degan da'voni tekshiradi.

    KATAK TARTIBI esa QO'LDA yozilgan `A_STALL_CODES_BY_SORT` dan
    filtrlanadi — bu yerda kolatsiya ishtirok etmaydi va eng muhim holat
    (`3` `100` dan OLDIN) aynan shu bilan qulflanadi.
    """
    response = await api_client.get(f"{STALLS_URL}/map", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    with market_scope(two_markets.market_a.id) as conn:
        expected_zone_order = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM zones WHERE market_id = %s ORDER BY name",
                (str(two_markets.market_a.id),),
            ).fetchall()
        ]

    assert [zone["name"] for zone in body["zones"]] == expected_zone_order
    assert set(expected_zone_order) == set(A_ZONE_NAMES)

    market_a = market_domain.market_a
    codes_by_zone: dict[str, list[str]] = {}
    for index, code in enumerate(A_STALL_CODES):
        zone_id = str(market_a.zone_ids[index % len(market_a.zone_ids)])
        codes_by_zone.setdefault(zone_id, []).append(code)

    for zone in body["zones"]:
        expected = [code for code in A_STALL_CODES_BY_SORT if code in codes_by_zone[zone["id"]]]
        assert [cell["code"] for cell in zone["cells"]] == expected, zone["name"]

    every_cell = [cell for zone in body["zones"] for cell in zone["cells"]]
    assert every_cell, "xarita bo'sh — tartib da'vosi hech nimani isbotlamasdi"
    for cell in every_cell:
        # D-20: rang MANBASI qaytariladi, rangning O'ZI emas.
        assert "tone" not in cell, "`tone` API'da hisoblanmasligi kerak (D-20)"
        assert "has_vendor" in cell


async def test_director_cannot_manage_stalls(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    director_headers: dict[str, str],
) -> None:
    """Direktor reestrni KO'RADI, lekin O'ZGARTIRA OLMAYDI (D-07).

    NAZORAT HOLATI (`GET` -> 200) MAJBURIY: usiz test direktorning
    sessiyasi umuman ishlamayotgan holatda ham yashil bo'lardi (har ikkala
    so'rov ham 401/403 berardi) va D-07 ning aynan mazmuni — "faqat
    yozish taqiqlangan" — sinovsiz qolardi.
    """
    forbidden = await api_client.post(
        STALLS_URL, json=_create_payload(market_domain), headers=director_headers
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["detail"] == "forbidden"

    allowed = await api_client.get(STALLS_URL, headers=director_headers)
    assert allowed.status_code == 200, allowed.text
    assert len(allowed.json()["items"]) == len(A_STALL_CODES)


# ---------------------------------------------------------------------------
# D-04 — toifa davrining o'tmish darvozasi (TO'RTLIK, birga o'qiladi)
# ---------------------------------------------------------------------------


async def test_future_category_valid_from_returns_201(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: KELAJAKDAGI `valid_from` -> 201 va qator yoziladi.

    Bu test to'rtlikda BIRINCHI turadi va u bo'lmasa qolgan uchtasi
    yolg'on-yashil berardi: darvoza HAR QANDAY sanani rad etadigan holga
    kelib qolsa (masalan solishtiruv teskari yozilsa), 403 kutayotgan ikki
    test baribir o'tardi va yagona nosozlik "toifani umuman o'zgartirib
    bo'lmaydi" bo'lardi — buni esa hech kim sezmasdi.
    """
    market_a = market_domain.market_a
    stall_id = market_a.stall_ids[0]
    target_category = market_a.category_ids[1]
    valid_from = market_today + timedelta(days=FUTURE_DAYS)

    response = await api_client.post(
        f"{STALLS_URL}/{stall_id}/category",
        json={"category_id": str(target_category), "valid_from": valid_from.isoformat()},
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text

    with market_scope(two_markets.market_a.id) as conn:
        row = conn.execute(
            "SELECT category_id FROM stall_category_periods "
            "WHERE market_id = %s AND stall_id = %s AND valid_from = %s",
            (str(two_markets.market_a.id), str(stall_id), valid_from),
        ).fetchone()

    assert row is not None, "kelajakdagi toifa davri yozilmadi"
    assert row[0] == target_category


async def test_past_category_valid_from_returns_403(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """O'TGAN sanali `valid_from` -> **403** `category_period_past_locked`.

    JAVOB 403, 422 EMAS: so'rov shakli to'g'ri (`valid_from` haqiqiy
    sana), rad etishning sababi — o'tmish hech kimga ochiq emasligi
    (T-02-61a, 02-09 dagi `tariff_past_locked` bilan bir xil mulohaza).

    ⚠ BU DARVOZANI DB TRIGGERI BILAN ALMASHTIRIB BO'LMAYDI:
    `trg_category_period_past_immutable` — `BEFORE UPDATE OR DELETE`, bu
    yo'l esa faqat `INSERT`. Darvozasiz o'tgan sanali `valid_from`
    JIMGINA 201 bilan yozilardi va `tariffs` jadvaliga umuman tegmasdan
    tarixiy kunning tarifini almashtirib qo'yardi (SC#3 ga yon kanal).
    """
    market_a = market_domain.market_a

    response = await api_client.post(
        f"{STALLS_URL}/{market_a.stall_ids[1]}/category",
        json={
            "category_id": str(market_a.category_ids[0]),
            "valid_from": (market_today - timedelta(days=1)).isoformat(),
        },
        headers=admin_headers,
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "category_period_past_locked"


async def test_today_category_valid_from_returns_403(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """BUGUNGI sana ham rad etiladi — chegara `>`, `>=` EMAS.

    `test_past_category_valid_from_returns_403` ning jufti: o'tmish
    holati `>=` bilan yozilgan darvozadan ham o'tardi, bugungi holat esa
    faqat `>` bilan yozilganida rad etiladi.
    """
    market_a = market_domain.market_a

    response = await api_client.post(
        f"{STALLS_URL}/{market_a.stall_ids[1]}/category",
        json={
            "category_id": str(market_a.category_ids[0]),
            "valid_from": market_today.isoformat(),
        },
        headers=admin_headers,
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "category_period_past_locked"


async def test_new_stall_gets_initial_category_period_at_operating_since(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
) -> None:
    """`POST /stalls` boshlang'ich toifa davrini `operating_since` bilan yozadi.

    TO'RTLIKNING OXIRGI HALQASI va usiz darvoza YARATISH oqimiga sizib
    chiqqani sezilmay qolardi: `create()` ham `set_category()` ni
    chaqirsa, o'tgan sanali `operating_since` 403 berib butun oqimni
    bloklardi — yuqoridagi uchta test esa baribir yashil qolaverardi.

    Sana SO'ROV TANASIDAN OLINMAGANI ham shu yerda ko'rinadi:
    `StallCreateRequest` da `valid_from` maydoni UMUMAN yo'q, ya'ni
    yozilgan qiymatning yagona manbai — server.
    """
    response = await api_client.post(
        STALLS_URL, json=_create_payload(market_domain), headers=admin_headers
    )
    assert response.status_code == 201, response.text
    created_id = UUID(response.json()["id"])

    with market_scope(two_markets.market_a.id) as conn:
        rows = conn.execute(
            "SELECT valid_from, category_id FROM stall_category_periods "
            "WHERE market_id = %s AND stall_id = %s",
            (str(two_markets.market_a.id), str(created_id)),
        ).fetchall()

    assert len(rows) == 1, f"aynan bitta boshlang'ich davr kutilgan edi: {rows}"
    assert rows[0][0] == A_OPERATING_SINCE
    assert rows[0][1] == market_domain.market_a.category_ids[0]


async def test_stall_with_foreign_zone_returns_404(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """B bozorining `zone_id` si bilan rasta yaratish -> **404**, 403 EMAS.

    Composite FK (`fk_stalls_market_id_zone_id_zones`) `23503` beradi va
    ilova uni 404 ga aylantiradi: 403 o'sha zona MAVJUDLIGINI tasdiqlardi
    (T-02-56). Mavjud bo'lmagan tasodifiy UUID ham AYNAN shu javobni
    oladi — nazorat sifatida shu yerda tekshiriladi.
    """
    foreign_zone = market_domain.market_b.zone_ids[0]
    payload = _create_payload(market_domain)
    payload["zone_id"] = str(foreign_zone)

    response = await api_client.post(STALLS_URL, json=payload, headers=admin_headers)

    assert response.status_code != 403
    assert response.status_code == 404, response.text

    unknown = _create_payload(market_domain, code="9003")
    unknown["zone_id"] = str(uuid4())
    unknown_response = await api_client.post(STALLS_URL, json=unknown, headers=admin_headers)

    assert unknown_response.status_code == 404, unknown_response.text
    assert unknown_response.content == response.content


# ---------------------------------------------------------------------------
# Zona va toifa reestrlari (02-08 Task 1 ning HTTP darajasidagi isboti)
# ---------------------------------------------------------------------------


async def test_duplicate_zone_name_returns_409(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Takroriy zona nomi -> 409 `zone_name_taken` (nazorat: yangi nom -> 201)."""
    duplicate = await api_client.post(
        ZONES_URL, json={"name": A_ZONE_NAMES[0]}, headers=admin_headers
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"] == "zone_name_taken"

    fresh = await api_client.post(ZONES_URL, json={"name": "Yangi zona"}, headers=admin_headers)
    assert fresh.status_code == 201, fresh.text
    assert fresh.json()["stall_count"] == 0


async def test_zone_with_stalls_cannot_be_deleted(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Rastasi bor zona -> 409 `zone_in_use`; BO'SH zona -> 204 (nazorat).

    Nazorat holati majburiy: `DELETE` umuman ishlamayotgan bo'lsa (masalan
    har doim 409 qaytarsa) birinchi assert baribir o'tardi.
    """
    used_zone = market_domain.market_a.zone_ids[0]

    blocked = await api_client.delete(f"{ZONES_URL}/{used_zone}", headers=admin_headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == "zone_in_use"

    created = await api_client.post(ZONES_URL, json={"name": "Bo'sh zona"}, headers=admin_headers)
    assert created.status_code == 201, created.text

    removed = await api_client.delete(f"{ZONES_URL}/{created.json()['id']}", headers=admin_headers)
    assert removed.status_code == 204, removed.text


async def test_category_without_tariff_reports_null(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_b_headers: dict[str, str],
) -> None:
    """Tarifsiz toifa uchun `current_tariff_soum` `null` (D-08), `0` EMAS.

    B bozori seed'ida IKKITA toifa va BITTA tarif bor — ikkinchi toifa
    ATAYIN tarifsiz (`fixtures/market_domain.py` modul docstringi). Bu
    02-11 dagi faollashtirish darvozasining manfiy holati va u aynan shu
    ustundan o'qiladi.

    `0` qaytarilsa tarifsiz kun "bepul kun" bo'lib ko'rinardi va anomaliya
    hech qachon chiqmasdi — shuning uchun nazorat holati (tarifi BOR
    toifa) ham tekshiriladi.
    """
    response = await api_client.get(CATEGORIES_URL, headers=market_b_headers)

    assert response.status_code == 200, response.text
    amounts = {item["name"]: item["current_tariff_soum"] for item in response.json()["items"]}

    assert len(amounts) == 2, amounts
    assert B_TARIFF_AMOUNT in amounts.values(), "tarifi bor toifa nazorat holati"
    assert None in amounts.values(), "tarifsiz toifa `null` qaytarishi kerak (D-08)"
