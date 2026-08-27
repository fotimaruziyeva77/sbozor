"""Import qobiliyatining KARMANA MIQYOSIDAGI uchidan-uchiga isboti.

=============================================================================
NEGA BU FAYL MAVJUD — `02-VERIFICATION.md` NING 2-BO'SHLIG'I.

Tekshiruvchi import yo'lini «HOLLOW (Level 4)» deb belgiladi va sababni
aniq yozdi: *«only a self-referential template round-trip was exercised»*.
02-17 ning o'lchovi esa `inserted: 1` edi — ya'ni MIQYOS ham sinalmagan.

Bu fayl ikkala bo'shliqni birga yopadi:

  * yuk `tests/fixtures/karmana_seed.py` dan keladi va u quvurning
    shablon yo'lidan BUTUNLAY mustaqil (T-02-165, `ast` darvozasi bilan
    qulflangan);
  * miqyos — 8 zona / 600 rasta / 480 sotuvchi, ya'ni ROADMAP dagi
    `~300–1000 rasta` oralig'ining o'rtasi.

⚠ BU FAYL `test_stall_import.py` (02-12) NING O'RNINI BOSMAYDI. U yerda
har bir DARVOZA alohida sinaladi (hajm, ZIP, huquq, cross-tenant, shablon
aylanmasi). Bu yerdagi savol boshqa: **butun zanjir REAL MIQYOSDA
uzilmaydimi** — usta -> import -> reestr -> xarita -> faollashtirish.
=============================================================================

D-14 NING YAGONA YUK KO'TARUVCHI ASSERTION'I — SANOQ, JAVOB KODI EMAS.

02-12 ning 6-sabotaji buni qimmat qilib o'rgatgan: qatorlar YOZILGAN
holatda ham javob 422 bo'lib qolgan va uchala status assertion'i o'tgan
edi. Shuning uchun HAR rad etish yo'lidan keyin (iflos rasta, surilgan
ustun, iflos sotuvchi) sanoq QAYTA o'lchanadi va o'zgarmagani alohida
tasdiqlanadi.

-----------------------------------------------------------------------------
BUTUN OQIM — FAQAT HTTP (T-02-173).

Birorta xom `INSERT`, birorta `sbozor_owner` ulanishi va birorta
migratsiya qadami YO'Q; `sync_owner_conn` faqat TEARDOWN uchun olinadi
(`karmana_market` fixture'i, `test_phase2_criteria.py` naqshi).

⚠ YAGONA ISTISNO VA U O'QISH: toifa davrlarining SANOG'I. Bu jadval
API'da umuman ko'rinmaydi, D-15 ning va'dasi esa aynan unga ham
tegishli («qayta import ikkinchi toifa davrini QO'SHMAYDI» — busiz
6-fazada hisob ikki marta yozilardi). Sanoq `market_scope` bilan, ILOVA
roli (`sbozor_app`) va tenant konteksti ostida o'qiladi — ya'ni
imtiyozni chetlab o'tish emas, ilova ko'radigan haqiqatni o'qish.
-----------------------------------------------------------------------------

O'LCHOVLAR SUMMARY'GA CHIQADI. Toza importning davomiyligi,
`GET /stalls/map` ning davomiyligi va javob hajmi `perf` lug'atiga
yig'iladi va test oxirida bosiladi (`-s` bilan ko'rinadi). README §4
dagi TAXMINLAR aynan shu raqamlar bilan almashtiriladi.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import (
    ACTIVATE_URL,
    CALENDAR_URL,
    CATEGORIES_URL,
    IMPORT_STALLS_URL,
    IMPORT_VENDORS_URL,
    MARKETS_URL,
    SETUP_STATUS_URL,
    STALLS_URL,
    TARIFFS_URL,
    VENDORS_URL,
    ZONES_URL,
    session_headers,
)
from fixtures.auth_api import SELECT_MARKET_URL
from fixtures.karmana_seed import (
    KARMANA_CATEGORY_NAMES,
    KARMANA_OPERATING_SINCE,
    KARMANA_STALL_COUNT,
    KARMANA_VENDOR_COUNT,
    KARMANA_ZONE_COUNT,
    KARMANA_ZONE_NAMES,
    build_stalls_workbook,
    build_vendors_workbook,
    clean_stall_rows,
    clean_vendor_rows,
    expected_stall_issues,
    expected_vendor_issues,
)
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import MarketScope
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXTRA_STALLS = 5
"""Qisman qayta importda QO'SHILADIGAN yangi kodlar soni.

Fayl `KARMANA_STALL_COUNT + EXTRA_STALLS` qator bilan qayta quriladi, ya'ni
eski 600 kod AYNAN o'sha joyida qoladi. Bu real dunyodagi eng ehtimolli
holat: admin faylga bir necha yangi rasta qo'shib, BUTUN faylni qayta
yuklaydi (README §6).
"""

TOTAL_STALLS = KARMANA_STALL_COUNT + EXTRA_STALLS

SHUFFLED_ROWS = 40
"""Ustunlari surilgan fayl ATAYIN KICHIK.

Har qatori bir nechta xato beradi, ya'ni 600 qatorli variant 1500+
elementli 422 tanasini qurardi. O'lchanayotgan da'vo esa miqyosga
bog'liq EMAS: pozitsion parser fayl NOTO'G'RI TERILGANINI ko'radi va
JIMGINA yozmaydi.
"""

TARIFF_BASE_SOUM = 5_000
TARIFF_STEP_SOUM = 1_500
"""Toifa narxlari HAR XIL — «toifa bo'yicha amaldagi narx» da'vosi
(README §7) bir xil summalar bilan qaysi toifani o'qiganini ajrata
olmasdi."""

MARKET_NAME = "Karmana tumani bozori (miqyos testi)"
MARKET_TIMEZONE = "Asia/Tashkent"
OPEN_WEEKDAYS = (1, 2, 3, 4, 5, 6, 7)
"""Haftalik ish rejimi USTA 1-QADAMIDA yuboriladi (02-21 / WR-06).

Usiz `calendar_missing` to'sig'i faollashtirishni 409 bilan qaytarardi —
ya'ni bu ro'yxat qulaylik emas, zanjirning bir bo'g'ini.
"""


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


def _upload(payload: bytes, name: str = "karmana.xlsx") -> dict[str, tuple[str, bytes, str]]:
    return {"file": (name, payload, XLSX_MEDIA_TYPE)}


def _issue_map(errors: list[dict[str, Any]]) -> dict[int, str]:
    """422 javobining `errors[]` ini `{qator: kod}` xaritasiga aylantiradi.

    Bir qatorda ikki xato bo'lsa DARHOL yiqiladi — aks holda tenglik
    da'vosi jimgina bir tomonlama bo'lib qolardi.
    """
    mapped: dict[int, str] = {}
    for issue in errors:
        row = int(issue["row"])
        assert row not in mapped, f"{row}-qatorda ikkita xato: {mapped[row]} va {issue['code']}"
        mapped[row] = str(issue["code"])
    return mapped


async def _page_through(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Keyset sahifalarini oxirigacha varaqlaydi.

    `GET /stalls` javobida UMUMIY SANOQ maydoni ATAYIN yo'q (chegarasiz
    `count(*)` 1000 rastali bozorda har so'rovga qo'shilardi), ya'ni
    README §7 ning «umumiy rasta soni» bandi aynan shu varaqlash bilan
    olinadi — hujjatda yozilganidek.
    """
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(64):  # cheksiz sikl himoyasi (kursor qotib qolsa)
        query: dict[str, Any] = {"limit": 200, **(params or {})}
        if cursor is not None:
            query["cursor"] = cursor
        response = await client.get(url, params=query, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        items.extend(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return items
    raise AssertionError(f"{url}: kursor 64 sahifada ham tugamadi")


async def _stall_count(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    **params: Any,
) -> int:
    return len(await _page_through(client, STALLS_URL, headers, params))


def _period_count(market_scope: MarketScope, market_id: UUID) -> int:
    """Toifa davrlarining sanog'i — ILOVA roli bilan, FAQAT O'QISH.

    Sabab fayl docstringida («YAGONA ISTISNO») yozilgan: bu jadval API'da
    ko'rinmaydi, D-15 ning va'dasi esa unga ham tegishli.
    """
    with market_scope(market_id) as conn:
        row = conn.execute("SELECT count(*) FROM stall_category_periods").fetchone()
    assert row is not None
    return int(row[0])


# ---------------------------------------------------------------------------
# Fixture'lar
# ---------------------------------------------------------------------------


@pytest.fixture
def built_markets(sync_owner_conn: Connection[TupleRow]) -> Iterator[list[UUID]]:
    """Test qurgan bozorlarni oxirida o'chiradi (`test_phase2_criteria.py` naqshi).

    Tozalash MAHSULOT funksiyasi bilan (`market_delete_draft()`) — u o'n
    uchta jadvalning tartibini biladi. ⚠ Avval bayroq TUSHIRILADI: test
    bozorni faollashtiradi, funksiya esa jonli bozorga ATAYIN tegmaydi,
    ya'ni deaktivatsiyasiz teardown jimgina hech nima o'chirmasdi va
    keyingi testlar 600 rastalik qoldiqni ko'rardi.
    """
    market_ids: list[UUID] = []
    try:
        yield market_ids
    finally:
        for market_id in market_ids:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("SELECT market_delete_draft(%s)", (str(market_id),))


# ===========================================================================
# Miqyos oqimi
# ===========================================================================


async def test_karmana_scale_import_runs_end_to_end(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    built_markets: list[UUID],
    market_scope: MarketScope,
) -> None:
    """Import qobiliyati Karmana miqyosida, quvur ishlab chiqarmagan ma'lumot bilan.

    ⚠ O'N BIR BOSQICH BITTA TESTDA VA BU ATAYIN. Bosqichlar ketma-ket
    bog'langan: sotuvchi fayli rasta kodlariga, xarita reestrga,
    faollashtirish esa uchalasiga tayanadi. Ularni alohida testlarga
    bo'lish har biri uchun 600 qatorlik importni QAYTA bajarishni talab
    qilardi — ya'ni to'plam davomiyligi bir necha barobar oshardi va
    hech qanday yangi da'vo qo'shilmasdi.

    Har rad etish yo'lidan keyin SANOQ qayta o'lchanadi (02-12 sabotaj
    #6): javob kodi yolg'iz o'zi hech nimani isbotlamaydi.
    """
    perf: dict[str, float] = {}

    # ---------------------------------------------------------------- 1-bosqich
    # Qoralama bozor — usta yo'lidan, FAQAT HTTP orqali.
    headers = await session_headers(api_client, two_markets.platform_admin_phone, SEED_PASSWORD)

    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": MARKET_NAME,
            "timezone": MARKET_TIMEZONE,
            "operating_since": KARMANA_OPERATING_SINCE.isoformat(),
            "open_weekdays": list(OPEN_WEEKDAYS),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    built_markets.append(market_id)

    selected = await api_client.post(
        SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
    )
    assert selected.status_code == 200, selected.text
    admin = {"Authorization": f"Bearer {selected.json()['access_token']}"}

    for name in KARMANA_ZONE_NAMES:
        response = await api_client.post(ZONES_URL, json={"name": name}, headers=admin)
        # ⚠ 403 HAR BOSQICHDAN KEYIN tekshiriladi, faqat oxirida emas
        # (02-17 deviatsiya #4): rad etish keyingi bosqichda «texnik
        # nosozlik» bo'lib niqoblanadi va sabab ko'rinmay qoladi.
        assert response.status_code == 201, f"zona '{name}': {response.status_code} {response.text}"

    category_ids: dict[str, UUID] = {}
    for name in KARMANA_CATEGORY_NAMES:
        response = await api_client.post(CATEGORIES_URL, json={"name": name}, headers=admin)
        assert response.status_code == 201, (
            f"toifa '{name}': {response.status_code} {response.text}"
        )
        category_ids[name] = UUID(response.json()["id"])

    tariffs: dict[str, int] = {}
    for index, name in enumerate(KARMANA_CATEGORY_NAMES):
        amount = TARIFF_BASE_SOUM + index * TARIFF_STEP_SOUM
        response = await api_client.post(
            TARIFFS_URL,
            json={
                "category_id": str(category_ids[name]),
                "amount_soum": amount,
                # Qoralama bozorda boshlang'ich narx AYNAN `operating_since`
                # ga tushadi (02-09 istisnosi) — README §2 ning «tariflar
                # faollashtirishdan OLDIN» qoidasi shu yerda bajariladi.
                "valid_from": KARMANA_OPERATING_SINCE.isoformat(),
            },
            headers=admin,
        )
        assert response.status_code == 201, f"tarif '{name}': {response.text}"
        tariffs[name] = amount

    empty = await _stall_count(api_client, admin)
    assert empty == 0, "yangi qoralama bozor rastasiz boshlanishi kerak"

    # ---------------------------------------------------------------- 2-bosqich
    # IFLOS rasta fayli -> 422, `{qator: kod}` AYNAN teng, SANOQ o'zgarmaydi.
    dirty_stalls = build_stalls_workbook(dirty=True)
    rejected = await api_client.post(IMPORT_STALLS_URL, headers=admin, files=_upload(dirty_stalls))

    assert rejected.status_code == 422, rejected.text
    body = rejected.json()["detail"]
    assert body["detail"] == "import_validation_failed"
    assert _issue_map(body["errors"]) == expected_stall_issues(), (
        "quvurning xatolari generator E'LONI bilan mos kelmadi — "
        "yo tricky qator jimgina buzilgan, yo kutilma eskirgan"
    )
    assert body["error_counts"] == {
        "duplicate_code_in_file": 2,
        "zone_not_found": 1,
        "category_not_found": 1,
        "invalid_status": 1,
        "empty_code": 1,
    }
    count_before = await _stall_count(api_client, admin)
    assert count_before == empty, "IFLOS fayl rad etildi, LEKIN qatorlar yozildi (D-14 buzilgan)"

    # ---------------------------------------------------------------- 3-bosqich
    # Ustunlari SURILGAN fayl -> 422, sanoq yana o'zgarmaydi.
    shuffled = build_stalls_workbook(count=SHUFFLED_ROWS, dirty=False, column_order="shuffled")
    misordered = await api_client.post(IMPORT_STALLS_URL, headers=admin, files=_upload(shuffled))

    assert misordered.status_code == 422, misordered.text
    assert await _stall_count(api_client, admin) == count_before, (
        "ustunlari surilgan fayl JIMGINA yozildi — README §3 ning va'dasi buzilgan"
    )

    # ---------------------------------------------------------------- 4-bosqich
    # TOZA fayl -> 200, `inserted` generator e'loni bilan teng, davomiylik o'lchanadi.
    clean_stalls = build_stalls_workbook(dirty=False)
    started = time.perf_counter()
    imported = await api_client.post(IMPORT_STALLS_URL, headers=admin, files=_upload(clean_stalls))
    perf["import_600_stalls_s"] = round(time.perf_counter() - started, 3)

    assert imported.status_code == 200, imported.text
    assert imported.json() == {"inserted": KARMANA_STALL_COUNT, "skipped": 0}
    assert await _stall_count(api_client, admin) == KARMANA_STALL_COUNT
    periods_after_first = _period_count(market_scope, market_id)
    assert periods_after_first == KARMANA_STALL_COUNT, (
        "har rastaga BOSHLANG'ICH toifa davri yozilishi shart — usiz bozor "
        "hech qachon faollashmasdi (`stalls_without_category`)"
    )

    # ---------------------------------------------------------------- 5-bosqich
    # D-15: AYNI fayl ikkinchi marta -> hech nima o'zgarmaydi.
    again = await api_client.post(IMPORT_STALLS_URL, headers=admin, files=_upload(clean_stalls))

    assert again.status_code == 200, again.text
    assert again.json() == {"inserted": 0, "skipped": KARMANA_STALL_COUNT}
    assert await _stall_count(api_client, admin) == KARMANA_STALL_COUNT
    assert _period_count(market_scope, market_id) == periods_after_first, (
        "qayta import IKKINCHI toifa davrini qo'shdi — 6-fazada hisob ikki marta yozilardi"
    )

    # ---------------------------------------------------------------- 6-bosqich
    # Qisman qayta import: faqat YANGI kodlar qo'shiladi.
    extended = build_stalls_workbook(count=TOTAL_STALLS, dirty=False)
    partial = await api_client.post(IMPORT_STALLS_URL, headers=admin, files=_upload(extended))

    assert partial.status_code == 200, partial.text
    assert partial.json() == {"inserted": EXTRA_STALLS, "skipped": KARMANA_STALL_COUNT}
    assert await _stall_count(api_client, admin) == TOTAL_STALLS

    # ---------------------------------------------------------------- 7-bosqich
    # IFLOS sotuvchi fayli -> 422 va sotuvchi sanog'i o'zgarmaydi.
    stall_codes = tuple(row.code for row in clean_stall_rows())
    dirty_vendors = build_vendors_workbook(stall_codes, dirty=True)
    vendors_before = len(await _page_through(api_client, VENDORS_URL, admin))

    vendor_rejected = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin, files=_upload(dirty_vendors)
    )

    assert vendor_rejected.status_code == 422, vendor_rejected.text
    assert _issue_map(vendor_rejected.json()["detail"]["errors"]) == expected_vendor_issues()
    assert len(await _page_through(api_client, VENDORS_URL, admin)) == vendors_before

    # ---------------------------------------------------------------- 8-bosqich
    # TOZA sotuvchi fayli -> 200; telefonning uch shakli BITTA E.164 ga tushadi.
    clean_vendors = build_vendors_workbook(stall_codes, dirty=False)
    started = time.perf_counter()
    vendor_import = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin, files=_upload(clean_vendors)
    )
    perf["import_480_vendors_s"] = round(time.perf_counter() - started, 3)

    assert vendor_import.status_code == 200, vendor_import.text
    assert vendor_import.json() == {"inserted": KARMANA_VENDOR_COUNT, "skipped": 0}

    declared_vendors = clean_vendor_rows(stall_codes)
    listed_vendors = await _page_through(api_client, VENDORS_URL, admin)
    assert len(listed_vendors) == KARMANA_VENDOR_COUNT
    assert all(item["phone"].startswith("+998") for item in listed_vendors), (
        "faylda uch xil shaklda yozilgan telefon BITTA E.164 ga tushmadi (MARKET-04)"
    )
    assert {item["phone"] for item in listed_vendors} == {row.phone for row in declared_vendors}

    stall_free = [item for item in listed_vendors if item["stall_count"] == 0]
    assert len(stall_free) == sum(1 for row in declared_vendors if row.stall_code is None), (
        "rastasiz sotuvchilar reestrda yo'q — D-11 holati yo'qolgan"
    )

    # ---------------------------------------------------------------- 9-bosqich
    # README §7 — YETTALA raqam endi assertion.
    declared_stalls = clean_stall_rows(count=TOTAL_STALLS)
    registry = await _page_through(api_client, STALLS_URL, admin)

    # (1) umumiy rasta soni
    assert len(registry) == TOTAL_STALLS

    # (2) zona bo'yicha taqsimot
    zones_response = await api_client.get(ZONES_URL, headers=admin)
    assert zones_response.status_code == 200, zones_response.text
    zone_rows = zones_response.json()["items"]
    expected_by_zone: dict[str, int] = {}
    for row in declared_stalls:
        expected_by_zone[row.zone] = expected_by_zone.get(row.zone, 0) + 1
    assert {row["name"]: row["stall_count"] for row in zone_rows} == expected_by_zone
    assert sum(row["stall_count"] for row in zone_rows) == TOTAL_STALLS

    # (3) holat bo'yicha taqsimot — HAR holat uchun alohida so'rov
    expected_by_status: dict[str, int] = {}
    for row in declared_stalls:
        expected_by_status[row.status] = expected_by_status.get(row.status, 0) + 1
    for status, expected in expected_by_status.items():
        assert await _stall_count(api_client, admin, status=status) == expected, status
    assert sum(expected_by_status.values()) == TOTAL_STALLS

    # (4) toifa bo'yicha taqsimot va (7) toifa bo'yicha amaldagi narx
    categories_response = await api_client.get(CATEGORIES_URL, headers=admin)
    assert categories_response.status_code == 200, categories_response.text
    category_rows = categories_response.json()["items"]
    expected_by_category: dict[str, int] = {}
    for row in declared_stalls:
        expected_by_category[row.category] = expected_by_category.get(row.category, 0) + 1
    assert {row["name"]: row["stall_count"] for row in category_rows} == expected_by_category
    assert {row["name"]: row["current_tariff_soum"] for row in category_rows} == tariffs

    # (5) sotuvchi soni — 8-bosqichda o'lchandi
    # (6) biriktirilgan rasta soni
    assigned = [item for item in registry if item["vendor_name"] is not None]
    assert len(assigned) == sum(1 for row in declared_vendors if row.stall_code is not None)

    # --------------------------------------------------------------- 10-bosqich
    # Xarita MIQYOSDA — birorta rasta yo'qolmaydi.
    started = time.perf_counter()
    map_response = await api_client.get(f"{STALLS_URL}/map", headers=admin)
    perf["get_map_s"] = round(time.perf_counter() - started, 3)
    perf["map_bytes"] = len(map_response.content)

    assert map_response.status_code == 200, map_response.text
    map_zones = map_response.json()["zones"]
    assert len(map_zones) == KARMANA_ZONE_COUNT
    cells = [cell for zone in map_zones for cell in zone["cells"]]
    assert {cell["id"] for cell in cells} == {item["id"] for item in registry}, (
        "xarita va reestr HAR XIL rastalar to'plamini ko'rsatmoqda — miqyosda "
        "birorta rasta JIMGINA tushib qolgan"
    )
    for zone in map_zones:
        codes = [cell["code"] for cell in zone["cells"]]
        assert codes == sorted(codes, key=int), (
            f"{zone['name']}: kataklar inson-raqamli tartibda emas (`code_sort`)"
        )
        assert codes != sorted(codes), (
            f"{zone['name']}: raqamli va matn tartibi FARQ qilmadi — 600 rastali "
            "bozorda bu imkonsiz, ya'ni tartib da'vosi bo'sh bo'lardi"
        )

    # --------------------------------------------------------------- 11-bosqich
    # Faollashtirish — butun zanjir miqyosda ishlaydi.
    setup = await api_client.get(SETUP_STATUS_URL.format(market_id=market_id), headers=admin)
    assert setup.status_code == 200, setup.text
    assert setup.json()["blocking"] == [], setup.text
    assert setup.json()["can_activate"] is True
    assert setup.json()["stalls"] == TOTAL_STALLS
    assert setup.json()["stalls_with_category"] == TOTAL_STALLS

    activated = await api_client.post(ACTIVATE_URL.format(market_id=market_id), headers=admin)
    assert activated.status_code == 200, activated.text
    assert activated.json()["is_active"] is True

    markets = await api_client.get(MARKETS_URL, headers=admin)
    assert markets.status_code == 200, markets.text
    entry = next(item for item in markets.json() if item["id"] == str(market_id))
    assert entry["is_active"] is True

    # Kalendar qadami usta 1-QADAMIDA yuborilgan (WR-06) — nazorat.
    # Alohida `PUT /calendar/weekdays` chaqirilmadi, ya'ni bu assertion
    # aynan «usta ish rejimini SO'RAYDI» degan 02-21 tuzatishini o'lchaydi.
    calendar = await api_client.get(CALENDAR_URL, headers=admin)
    assert calendar.status_code == 200, calendar.text
    assert calendar.json()["open_weekdays"] == list(OPEN_WEEKDAYS)

    # O'LCHOVLAR — SUMMARY uchun (README §4 dagi taxminlarni almashtiradi).
    print(f"\nKARMANA_SCALE_PERF={json.dumps(perf)}")
