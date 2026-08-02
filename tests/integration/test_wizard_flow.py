"""SC#1 — "yangi bozor" ustasining UCHIDAN-UCHIGA isboti (MARKET-01).

=============================================================================
BU FAZANING ENG MUHIM TESTI: BOZOR **KOD YOZILMASDAN** QURILADI.

CLAUDE.md dagi majburiyat aniq: "yangi bozor kod yozmasdan wizard orqali
ulanadi". Uni faqat uchidan-uchiga oqim isbotlay oladi — birorta alohida
endpoint testi bunga javob bermaydi, chunki nosozlik ODATDA endpointda
emas, ULARNING ORASIDA bo'ladi:

  * 1-qadam tenant sessiyasini talab qilib qo'ysa (`market_id` hali yo'q);
  * 3-qadamda platforma adminida `STALL_MANAGE` bo'lmasa (Pitfall 6 — kod
    to'g'ri ko'rinadi, matritsa jimgina rad etadi);
  * 4-qadamda `valid_from` `operating_since` ga tushib, "o'tmish" deb rad
    etilsa (T-02-63a istisnosi 02-09 da ochilgan — bu test uni ISTE'MOL
    qiladi);
  * 9-qadamda to'liqlik tekshiruvi hech qachon qanoatlanmasa.

Har bir band alohida yashil bo'lib, zanjir baribir ishlamasligi mumkin.
=============================================================================

`operating_since` ATAYIN O'TMISHDAGI SANA (`market_today` dan hisoblanadi).
Karmana bozori yillar davomida ishlab kelgan, ya'ni bu shunchaki "qulay
qiymat" emas — u haqiqiy holat. Bugungi sana qo'yilganda 4-qadamdagi
BOSHLANG'ICH NARX tarmog'i (02-09 dagi `add_tariff` ning ikkinchi sharti)
umuman bosilmasdi va test hech nimani isbotlamasdi.

⚠ BU FAYL `tariff_repo.py` / `tariffs.py` GA TEGMAYDI. Boshlang'ich narx
nazoratining yagona egasi — 02-09. Agar u yerdagi istisno yo'qolsa,
`test_wizard_end_to_end_reaches_active_market` 5-qadamda 422 bilan
qulaydi va bu TO'G'RI SIGNAL: tuzatish shu testda emas, 02-09 da.

`POST /api/v1/markets` UCHUN QAMROV SHU YERDA QAYTA TIKLANGAN.
`/api/v1/markets` yo'li cross-tenant matritsasining `EXEMPT_ROUTES` ida va
istisno YO'L bo'yicha ishlaydi, metod bo'yicha emas — ya'ni `POST` ham
avtomatik ravishda matritsadan tashqarida qoladi. `EXEMPT_ROUTES`
docstringi bunday holatda qamrovni KO'CHIRISHNI talab qiladi:
tokensiz -> 401, bozor admini -> 403, platforma admini -> 201.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import (
    ACTIVATE_URL,
    CALENDAR_URL,
    CATEGORIES_URL,
    MARKETS_URL,
    SETUP_STATUS_URL,
    STALLS_URL,
    TARIFFS_URL,
    VENDORS_URL,
    ZONES_URL,
    audit_entries,
    session_headers,
)
from fixtures.auth_api import LOGIN_URL, SELECT_MARKET_URL, login
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import date

    import httpx
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

OPERATING_SINCE_DAYS = 180
"""`operating_since` qancha kun ORQADA — sobit sana EMAS (02-07 deviatsiya #1).

Qiymat 30 dan katta bo'lishi kifoya emas: u tarif tarixining "o'tmish"
tomonida turishi va UTC/Toshkent farqidan (bir kun) ancha uzoqda bo'lishi
kerak. Olti oy ikkala shartni ham qamraydi.
"""

WIZARD_TIMEZONE = "Asia/Tashkent"
WIZARD_ZONE_NAMES = ("Usta markaziy", "Usta sharqiy")
WIZARD_CATEGORY_NAMES = ("Usta sabzavot", "Usta go'sht")
WIZARD_STALL_CODES = ("901", "902", "903")
WIZARD_AMOUNTS = (9_000, 11_000)
WIZARD_WEEKDAYS = (1, 2, 3, 4, 5, 6)
"""Yakshanba YO'Q — seed'ning `[1..7]` jadvalidan farqli.

Farq ataylab: `PUT /calendar/weekdays` HAQIQATAN yozganini ko'rsatadi.
Bir xil qiymat yozilganda test "kalendar sozlandi" degan da'voni
`market_create()` ning standart qiymati bilan ham qanoatlantirardi.
"""

WIZARD_VENDOR_PHONE = "+998909991001"
"""Usta testining sotuvchisi — seed va matritsa diapazonlaridan TASHQARIDA.

`market_domain.A_VENDOR_PHONES` `+99890111...`, `two_markets._next_phone()`
`+99897...`, cross-tenant matritsasi esa `+998909990001` ni ishlatadi.
"""

_MARKET_DML = frozenset({"insert", "update", "delete"})
"""`markets` ustidagi O'ZGARISH amallari — sabab `_market_dml()` da."""

_DEACTIVATE = "UPDATE markets SET is_active = false WHERE id = %s"
_DELETE_DRAFT = "SELECT market_delete_draft(%s)"
_DROP_PROFILE = "DELETE FROM market_profile WHERE market_id = %s"
_DROP_ONE_STALL_CATEGORY = """
    DELETE FROM stall_category_periods
     WHERE market_id = %s
       AND stall_id = (SELECT id FROM stalls WHERE market_id = %s ORDER BY code LIMIT 1)
"""


# ---------------------------------------------------------------------------
# Fixture'lar
# ---------------------------------------------------------------------------


@pytest.fixture
def created_markets(sync_owner_conn: Connection[TupleRow]) -> Iterator[list[UUID]]:
    """Test YARATGAN bozorlarni ro'yxatga oladi va oxirida o'chiradi.

    NEGA KERAK: `two_markets` seed'i faqat O'Z bozorlarini tozalaydi, bu
    fayl esa `POST /api/v1/markets` orqali HAQIQIY qatorlar tug'diradi.
    Ular qolib ketsa `auth_list_markets()` (global funksiya) keyingi
    testlarda o'sib boradigan ro'yxat qaytarardi va "qoralama bozor
    ro'yxatda ko'rinadimi?" kabi da'volar sekin-asta ishonchsiz bo'lardi.

    Tozalash MAHSULOT funksiyasi bilan (`market_delete_draft()`), qo'lda
    yozilgan `DELETE` zanjiri bilan EMAS: o'sha funksiya o'n uchta
    jadvalning tartibini biladi va yangi jadval qo'shilganda u YAGONA
    yangilanadigan joy bo'lib qoladi.

    ⚠ AVVAL BAYROQ TUSHIRILADI: uchidan-uchiga test bozorni FAOLLASHTIRADI,
    `market_delete_draft()` esa jonli bozorga ataylab tegmaydi (`false`
    qaytaradi) — ya'ni deaktivatsiyasiz teardown jimgina hech nima
    o'chirmasdi.
    """
    market_ids: list[UUID] = []
    try:
        yield market_ids
    finally:
        for market_id in market_ids:
            sync_owner_conn.execute(_DEACTIVATE, (str(market_id),))
            sync_owner_conn.execute(_DELETE_DRAFT, (str(market_id),))


@pytest.fixture
async def platform_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """Platforma adminining BOZOR TANLANMAGAN sessiyasi (tokenda `mid` yo'q).

    Ustaning 1-qadami aynan shu holatdan boshlanadi: bozor hali mavjud
    emas, ya'ni uni tanlashning imkoni ham yo'q.
    """
    return await session_headers(api_client, two_markets.platform_admin_phone, SEED_PASSWORD)


@pytest.fixture
def new_market(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    created_markets: list[UUID],
    market_today: date,
) -> Callable[..., Any]:
    """`POST /markets` -> `select-market` -> to'ldirish — bitta chaqiruvda.

    Yordamchi ATAYIN yupqa: u faqat takrorlanadigan uchta qadamni bir
    joyga yig'adi va hech qanday da'voni yashirmaydi (`fixtures/admin_api.py`
    modul docstringidagi qoida).
    """

    async def _build(*, name: str, skip: str | None = None) -> tuple[UUID, dict[str, str], date]:
        operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
        headers = await session_headers(api_client, two_markets.platform_admin_phone, SEED_PASSWORD)
        created = await api_client.post(
            MARKETS_URL,
            json={
                "name": name,
                "timezone": WIZARD_TIMEZONE,
                "operating_since": operating_since.isoformat(),
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        market_id = UUID(created.json()["id"])
        created_markets.append(market_id)

        tenant_headers = await _select(api_client, headers, market_id)
        await _fill_wizard(api_client, tenant_headers, operating_since=operating_since, skip=skip)
        return market_id, tenant_headers, operating_since

    return _build


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


async def _select(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    market_id: UUID,
) -> dict[str, str]:
    """`POST /auth/select-market` — 1-FAZADAN, O'ZGARISHSIZ (RESEARCH Pattern 5).

    Usta uchun alohida "sessiya" mexanizmi yaratilmagan: qoralama bozor
    oddiy tenant sifatida tanlanadi va undan keyingi barcha qadamlar
    oddiy RLS ostida ketadi.
    """
    response = await client.post(
        SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _post_id(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    url: str,
    payload: dict[str, Any],
) -> UUID:
    response = await client.post(url, json=payload, headers=headers)
    assert response.status_code == 201, f"{url}: {response.status_code} — {response.text}"
    return UUID(response.json()["id"])


async def _fill_wizard(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    operating_since: date,
    skip: str | None,
) -> None:
    """Ustaning 2–7-qadamlarini API orqali bajaradi.

    `skip` — AYNAN BITTA qadamni o'tkazib yuboradi va shu bilan
    `test_activate_rejects_incomplete_market` ning har bir holati
    quriladi. Bog'liqlik tartibi (UI-SPEC §6.2) saqlanadi: zonasiz yoki
    toifasiz rasta yaratib bo'lmaydi, ya'ni ularni o'tkazib yuborish
    rastalarni ham o'chiradi — bu KUTILGAN va test `blocking` ichida
    AYNAN kutilgan kodning borligini tekshiradi, ro'yxatning uzunligini
    emas.
    """
    zone_ids: list[UUID] = []
    if skip != "zones":
        zone_ids = [
            await _post_id(client, headers, ZONES_URL, {"name": name}) for name in WIZARD_ZONE_NAMES
        ]

    category_ids: list[UUID] = []
    if skip != "categories":
        category_ids = [
            await _post_id(client, headers, CATEGORIES_URL, {"name": name})
            for name in WIZARD_CATEGORY_NAMES
        ]

    if skip != "tariffs":
        for category_id, amount in zip(category_ids, WIZARD_AMOUNTS, strict=False):
            # ⚠ `valid_from` = `operating_since`, ya'ni O'TMISHDAGI sana.
            # Bu yo'l 02-09 dagi boshlang'ich narx istisnosi bilan
            # ochilgan (T-02-63a) va bu yerda faqat ISTE'MOL qilinadi.
            response = await client.post(
                TARIFFS_URL,
                json={
                    "category_id": str(category_id),
                    "amount_soum": amount,
                    "valid_from": operating_since.isoformat(),
                },
                headers=headers,
            )
            assert response.status_code == 201, (
                "boshlang'ich narx rad etildi — 02-09 dagi istisno yo'qolgan bo'lishi "
                f"mumkin: {response.status_code} — {response.text}"
            )

    if skip != "stalls" and zone_ids and category_ids:
        for index, code in enumerate(WIZARD_STALL_CODES):
            await _post_id(
                client,
                headers,
                STALLS_URL,
                {
                    "code": code,
                    "zone_id": str(zone_ids[index % len(zone_ids)]),
                    # Rastaning BOSHLANG'ICH toifa davri shu chaqiruvning
                    # ichida, `operating_since` sanasi bilan yoziladi
                    # (`StallRepository.create()`), ya'ni 5-qadam uchun
                    # ikkinchi chaqiruv KERAK EMAS.
                    "category_id": str(category_ids[index % len(category_ids)]),
                },
            )

    if skip != "calendar":
        response = await client.put(
            f"{CALENDAR_URL}/weekdays",
            json={"open_weekdays": list(WIZARD_WEEKDAYS)},
            headers=headers,
        )
        assert response.status_code == 200, response.text


async def _status(client: httpx.AsyncClient, headers: dict[str, str], market_id: UUID) -> Any:
    response = await client.get(SETUP_STATUS_URL.format(market_id=market_id), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _activate(
    client: httpx.AsyncClient, headers: dict[str, str], market_id: UUID
) -> httpx.Response:
    return await client.post(ACTIVATE_URL.format(market_id=market_id), headers=headers)


def _market_dml(rows: list[Any]) -> list[Any]:
    """`markets` jadvalining O'ZGARISH yozuvlari — `market_selected` SIZ.

    ⚠ `table_name` bo'yicha filtr YETARLI EMAS va bu o'lchangan: D-06
    bo'yicha bozor TANLASH hodisasi ham `table_name = 'markets'` bilan
    yoziladi (`AuditAction.MARKET_SELECTED`, `security/audit.py::
    TABLE_MARKETS`). Usta oqimida `select-market` HAR DOIM chaqiriladi,
    ya'ni faqat jadval nomi bo'yicha filtrlangan "AYNAN bitta yozuv"
    da'vosi doim `2 != 1` bilan yiqilardi.

    Amal turlari bo'yicha filtr esa da'voni kuchsizlantirmaydi: u
    "yaratildi / faollashtirildi / o'chirildi" hodisalarini boshqa
    HECH NIMA bilan aralashtirmaydi.
    """
    return [row for row in rows if row.table_name == "markets" and row.action in _MARKET_DML]


# ---------------------------------------------------------------------------
# SC#1 — uchidan-uchiga
# ---------------------------------------------------------------------------


async def test_wizard_end_to_end_reaches_active_market(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Yaratish -> tanlash -> to'ldirish -> faollashtirish: BITTA oqim.

    Oqim davomida birorta chaqiruv 403 QAYTARMAYDI — Pitfall 6 aynan shu
    yerda yopiladi va `_post_id`/`_fill_wizard` ichidagi har bir assert
    uning bir bandi.
    """
    market_id, headers, _ = await new_market(name="Usta uchidan-uchiga")

    before = await _status(api_client, headers, market_id)
    assert before["can_activate"] is True, before["blocking"]
    assert before["blocking"] == []
    assert before["zones"] == len(WIZARD_ZONE_NAMES)
    assert before["categories"] == len(WIZARD_CATEGORY_NAMES)
    assert before["tariffs_covered"] == before["categories_total"]
    assert before["stalls"] == len(WIZARD_STALL_CODES)
    assert before["stalls_with_category"] == before["stalls"]
    assert before["calendar_configured"] is True

    activated = await _activate(api_client, headers, market_id)

    assert activated.status_code == 200, activated.text
    body = activated.json()
    assert body["id"] == str(market_id)
    assert body["is_active"] is True

    # Bayroq JAVOBDAN emas, KEYINGI o'qishdan ham tasdiqlanadi: yozuv
    # yo'li va o'qish yo'li jimgina ajralib ketmasin (02-09 naqshi).
    listed = await api_client.get(MARKETS_URL, headers=headers)
    assert listed.status_code == 200, listed.text
    entry = next(item for item in listed.json() if item["id"] == str(market_id))
    assert entry["is_active"] is True


async def test_draft_market_is_visible_to_its_creator(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    created_markets: list[UUID],
    platform_headers: dict[str, str],
    market_today: date,
) -> None:
    """02-03 zanjirining uchidan-uchiga isboti: qoralama login javobida BOR.

    02-03 oltita bandni (DB -> repozitoriy -> sxema -> endpoint -> zod ->
    UI) birga o'zgartirgan edi, LEKIN o'shanda `POST /markets` hali yo'q
    edi: test qoralamani xom `INSERT` bilan yasagan. Bu yerda bozor
    MAHSULOT yo'lidan tug'iladi, ya'ni zanjir haqiqiy manba bilan
    sinaladi.
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Usta ko'rinadigan qoralama",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": operating_since.isoformat(),
        },
        headers=platform_headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    created_markets.append(market_id)
    assert created.json()["is_active"] is False

    response = await login(api_client, two_markets.platform_admin_phone, SEED_PASSWORD)

    assert response.status_code == 200, response.text
    markets = {item["id"]: item for item in response.json()["markets"]}
    assert str(market_id) in markets, f"{LOGIN_URL} javobida yangi qoralama bozor yo'q"
    assert markets[str(market_id)]["is_active"] is False
    # NAZORAT: bayroq har doim `false` deb qotirilmagan.
    assert markets[str(two_markets.market_a.id)]["is_active"] is True


async def test_market_profile_is_born_with_the_market(
    api_client: httpx.AsyncClient,
    created_markets: list[UUID],
    platform_headers: dict[str, str],
    market_today: date,
    market_scope: Any,
) -> None:
    """Profil qatori BOZOR BILAN BIR AMALDA tug'iladi (PATTERNS §3.6 qarori).

    Profilsiz oyna ochilib qolsa `market_is_open()` fail-closed `false`
    beradi — bozor xato bermasdan HECH QACHON ishlamasdi va tushum
    jimgina nolga tushardi. Shuning uchun bu test "profil bormi?"
    savolini AYNAN yaratishdan keyin, boshqa hech qanday chaqiruvsiz
    beradi.
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Usta profil",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": operating_since.isoformat(),
            "tin": "123456789",
        },
        headers=platform_headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    created_markets.append(market_id)

    with market_scope(market_id) as conn:
        row = conn.execute(
            "SELECT operating_since, open_weekdays, tin FROM market_profile WHERE market_id = %s",
            (str(market_id),),
        ).fetchone()

    assert row is not None, "market_create() profil qatorini yozmadi"
    assert row[0] == operating_since
    # ⚠ ISH REJIMI TAXMIN QILINMAYDI (WR-06, 0011_weekday_choice).
    # Ilgari bu yerda jadval yettala kun bilan solishtirilardi — `market_create()`
    # `COALESCE(p_open_weekdays, ARRAY[1..7])` bilan standart yozardi. Aynan
    # o'sha standart `calendar_configured` ni HAR DOIM rost qilib,
    # `calendar_missing` to'sig'ini ustaning yagona yo'lida ishlamaydigan
    # qilib qo'ygan edi. Endi `NULL` — "hali tanlanmagan" va u to'siqni
    # ISHGA TUSHIRADI. Bo'sh massiv (`'{}'`) esa hamon TAQIQLANGAN: u
    # "hech qachon ochilmaydi" degani va boshqa nosozlik.
    assert row[1] is None
    assert row[2] == "123456789"


# ---------------------------------------------------------------------------
# Faollashtirish darvozasi
# ---------------------------------------------------------------------------


INCOMPLETE_CASES: tuple[tuple[str, str], ...] = (
    ("zones", "zones_missing"),
    ("categories", "categories_missing"),
    ("tariffs", "tariff_missing_for_category"),
    ("stalls", "stalls_missing"),
    ("stall_categories", "stalls_without_category"),
    ("calendar", "calendar_missing"),
)
"""Har bloklovchi shart uchun bitta holat — `(o'tkazib yuborilgan qadam, kod)`.

Oxirgi IKKITASI API orqali "o'tkazib yuborilmaydi" va SABABLARI HAR XIL:

  * `stalls_without_category` — `POST /stalls` boshlang'ich toifa davrini
    HAR DOIM o'zi yozadi (`StallRepository.create()`), toifa davrini
    o'chiradigan endpoint esa umuman yo'q. Ya'ni bu holat hamon
    strukturaviy jihatdan erishib bo'lmaydigan va u faqat `sbozor_owner`
    bilan quriladi;
  * `calendar_missing` — bu holatga ENDI IKKI YO'LDAN erishiladi
    (0011_weekday_choice, WR-06):
      (a) PROFIL QATORISIZ bozor — shu yerdagi `_DROP_PROFILE` yo'li,
          ya'ni migratsiya/seed/qo'lda tuzatish natijasida tug'ilgan
          qator uchun darvoza. SAQLANADI;
      (b) `open_weekdays` TANLANMAGAN bozor — `market_create()` endi
          standart yozmaydi, ya'ni `POST /markets` dan keyin `PUT
          /calendar/weekdays` chaqirilmasa ustun `NULL` qoladi. Bu
          MAHSULOT yo'li va u pastdagi alohida testlar bilan qamraladi
          (`test_market_without_weekday_choice_is_blocked` va uning
          nazorat/tiklanish juftlari).

Bu qatordagi `calendar` holati ATAYIN (a) yo'lida qoladi: ikkala yo'l
bitta testga birlashtirilsa, profil qatori yo'q bozor uchun darvoza
jimgina sinalmay qolardi.
"""


@pytest.mark.parametrize(
    ("skip", "expected_code"), INCOMPLETE_CASES, ids=[case[0] for case in INCOMPLETE_CASES]
)
async def test_activate_rejects_incomplete_market(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
    sync_owner_conn: Connection[TupleRow],
    skip: str,
    expected_code: str,
) -> None:
    """Chala bozor -> **409** va javob tanasida `blocking[]` (UI-SPEC §6.6).

    409 ning tanasi ALOHIDA tekshiriladi: usiz javob "amal bajarilmadi"
    degan ma'lumotni berardi-yu, foydalanuvchini qaysi qadamga
    qaytishini bilmay qoldirardi — bu esa aynan §6.6 taqiqlaydigan
    "qizil xato bloki" tajribasi.
    """
    api_skip = skip if skip in {"zones", "categories", "tariffs", "stalls"} else None
    market_id, headers, _ = await new_market(name=f"Usta chala {skip}", skip=api_skip)

    if skip == "stall_categories":
        sync_owner_conn.execute(_DROP_ONE_STALL_CATEGORY, (str(market_id), str(market_id)))
    if skip == "calendar":
        sync_owner_conn.execute(_DROP_PROFILE, (str(market_id),))

    status_body = await _status(api_client, headers, market_id)
    response = await _activate(api_client, headers, market_id)

    assert response.status_code == 409, f"{response.status_code} — {response.text}"
    body = response.json()
    assert body["detail"] == "market_incomplete"
    codes = [item["code"] for item in body["blocking"]]
    assert expected_code in codes, codes

    # `setup-status` va `activate` AYNAN bir xil ro'yxatni beradi —
    # ikkala yo'l ham `_blocking()` dan o'tadi va bu shartnoma yakuniy
    # panelning butun render mantiqi tayanadigan narsa.
    assert body["blocking"] == status_body["blocking"]
    assert status_body["can_activate"] is False


async def test_blocking_items_are_ordered_by_step(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """`blocking[]` `step` bo'yicha O'SISH tartibida — bu javob SHARTNOMASI.

    Frontend `blocking[0].step` ni "birinchi tugallanmagan qadam" deb
    ishlatadi (02-03 dagi `firstIncompleteStep()` va UI-SPEC §6.4), ya'ni
    tartib buzilganda uzilishdan tiklanish oqimi foydalanuvchini NOTO'G'RI
    qadamga olib borardi — va bu hech qanday xato bermasdan sodir
    bo'lardi.
    """
    market_id, headers, _ = await new_market(name="Usta bo'sh", skip="zones")

    body = await _status(api_client, headers, market_id)

    steps = [item["step"] for item in body["blocking"]]
    assert steps == sorted(steps), steps
    assert body["blocking"][0]["step"] == min(steps)
    assert {"zones_missing", "stalls_missing"} <= {item["code"] for item in body["blocking"]}


async def test_empty_draft_reports_every_missing_step(
    api_client: httpx.AsyncClient,
    created_markets: list[UUID],
    platform_headers: dict[str, str],
    two_markets: TwoMarketSeed,
    market_today: date,
) -> None:
    """Endigina yaratilgan bozor: TO'RTTA bloklovchi shart, tartibi bilan.

    Bu test `blocking[]` ning TO'LIQ VA TARTIBLI ro'yxatini qulflaydi —
    ya'ni u pastdagi `test_market_without_weekday_choice_is_blocked` dan
    BOSHQA savolga javob beradi. U yerda "`calendar_missing` bormi?"
    so'raladi; bu yerda esa "ro'yxatda AYNAN shu to'rttasi bormi, ortiqcha
    band yo'qmi va tartib `step` bo'yicha to'g'rimi?" so'raladi. Bandning
    TUSHIB QOLISHI ham, ORTIQCHASI ham faqat shu yerda ushlanadi.

    ⚠ KALENDAR BANDI ENDI RO'YXATDA — va bu tuzatish, regressiya emas
    (WR-06, 0011_weekday_choice). Ilgari `market_create()` `open_weekdays`
    ni `{1..7}` standarti bilan yozardi, ya'ni yangi bozor 7-qadamda
    HECH QACHON bloklanmasdi va "dushanba yopiq" bozor "har kuni ochiq"
    deb faollashardi. Endi ish rejimi ustaning 1-qadamida TANLANADI;
    API orqali bevosita yaratilgan bozorda (bu test aynan shunday
    yaratadi) u tanlanmagan qoladi va `calendar_missing` yonadi.

    `calendar_missing` — `step: 7`, ya'ni ro'yxatning OXIRIDA. Tartib
    `_blocking()` shartnomasi: frontend `blocking[0].step` ni "birinchi
    tugallanmagan qadam" deb ishlatadi.
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Usta yangi",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": operating_since.isoformat(),
        },
        headers=platform_headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    created_markets.append(market_id)
    headers = await _select(api_client, platform_headers, market_id)

    body = await _status(api_client, headers, market_id)

    assert body["can_activate"] is False
    assert [item["code"] for item in body["blocking"]] == [
        "zones_missing",
        "categories_missing",
        "stalls_missing",
        "calendar_missing",
    ]
    assert body["calendar_configured"] is False
    assert two_markets.market_a.id != market_id


# ---------------------------------------------------------------------------
# WR-06 — ish rejimi TANLANADI, taxmin qilinmaydi (0011_weekday_choice)
#
# TO'RTTA test va ular BIRGA bitta da'voni qoplaydi: to'siq HAQIQATDA
# ishlaydi (1), faollashtirishni HAQIQATDA to'sadi (2), HAR DOIM
# yonavermaydi (3 — nazorat) va foydalanuvchini boshi berk ko'chaga qamab
# qo'ymaydi (4 — tiklanish). Faqat (1) yozilganda to'siqning "har doim
# yonadigan" buzuq varianti ham yashil ko'rinardi; faqat (1)+(2) yozilganda
# esa 7-qadam ishlamay qolgani sezilmasdi.
# ---------------------------------------------------------------------------


async def test_market_without_weekday_choice_reports_calendar_missing(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Ish rejimi tanlanmagan bozor -> `blocking[]` da AYNAN `calendar_missing`.

    Bozor 2–6-qadamlarning HAMMASI bajarilgan holda quriladi va faqat
    haftalik jadval qoldiriladi. Shuning uchun ro'yxat AYNAN bitta
    banddan iborat bo'lishi shart: shunda test "to'siq yondi" ni emas,
    "AYNAN SHU to'siq yondi" ni o'lchaydi va boshqa qadamning tasodifiy
    chala qolishi natijani yashira olmaydi.

    ⚠ BU ASSERT 0011 GACHA YOZIB BO'LMAS EDI. `market_create()`
    `open_weekdays` ni `{1..7}` standarti bilan yozardi, ya'ni holat
    umuman yuzaga kelmasdi (WR-06). Testning yozib bo'lmasligi nosozlik
    belgisining o'zi edi.
    """
    market_id, headers, _ = await new_market(name="Usta rejimsiz", skip="calendar")

    body = await _status(api_client, headers, market_id)

    assert body["calendar_configured"] is False
    assert [item["code"] for item in body["blocking"]] == ["calendar_missing"]
    assert body["blocking"][0]["step"] == 7
    assert body["can_activate"] is False


async def test_market_without_weekday_choice_cannot_activate(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Ish rejimisiz bozor faollashtirilmaydi -> **409** va sabab ro'yxati.

    `setup-status` ni o'qish darvoza EMAS — faollashtirish yo'li o'z
    tekshiruvidan o'tadi. Ikkalasi alohida sinaladi, chunki 02-11 dagi
    shartnoma aynan "ikkala yo'l ham `_blocking()` dan o'tadi" degan
    da'voga tayanadi va u jimgina ajralib ketishi mumkin.

    Faollashtirish o'tib ketsa oqibat KO'RINMAYDIGAN bo'lardi:
    `market_is_open()` fail-closed, ya'ni jadvalsiz bozor uchun HAR KUNI
    `false` beradi — bozor "jonli" bo'lib turardi-yu, 6-fazadagi kunlik
    job birorta patta yozmasdi va tushum JIMGINA nolga tushardi.
    """
    market_id, headers, _ = await new_market(name="Usta rejimsiz faollashuv", skip="calendar")

    response = await _activate(api_client, headers, market_id)

    assert response.status_code == 409, f"{response.status_code} — {response.text}"
    body = response.json()
    assert body["detail"] == "market_incomplete"
    assert [item["code"] for item in body["blocking"]] == ["calendar_missing"]


async def test_weekday_choice_at_step_one_leaves_no_calendar_gate(
    api_client: httpx.AsyncClient,
    created_markets: list[UUID],
    platform_headers: dict[str, str],
    market_today: date,
) -> None:
    """NAZORAT: 1-qadamda ish rejimi BERILSA to'siq umuman yonmaydi.

    Usta 1-qadami aynan shunday yuboradi (`MarketRequisitesForm` ->
    `open_weekdays`), ya'ni bu test MAHSULOT yo'lining o'zini o'lchaydi.
    Usiz `calendar_missing` ning "har doim yoqilgan" buzuq varianti ham
    yuqoridagi ikki testni yashil qoldirardi.

    Jadval `WIZARD_WEEKDAYS` (yakshanbasiz) — `{1..7}` EMAS. Farq ataylab:
    qiymat HAQIQATAN uzatilganini ko'rsatadi. Barcha yetti kun berilganda
    test yo'qolgan standart qiymat bilan ham qanoatlanardi.
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Usta rejim bilan",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": operating_since.isoformat(),
            "open_weekdays": list(WIZARD_WEEKDAYS),
        },
        headers=platform_headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    created_markets.append(market_id)
    headers = await _select(api_client, platform_headers, market_id)
    # `skip="calendar"` — 7-qadam ATAYIN chaqirilmaydi: jadval 1-qadamda
    # allaqachon berilgan va aynan shu holat sinalyapti.
    await _fill_wizard(api_client, headers, operating_since=operating_since, skip="calendar")

    body = await _status(api_client, headers, market_id)
    calendar = await api_client.get(CALENDAR_URL, headers=headers)

    assert body["calendar_configured"] is True
    assert body["blocking"] == []
    assert body["can_activate"] is True
    # Yozilgan qiymat O'QISH yo'lidan ham tasdiqlanadi: yozish va o'qish
    # jimgina ajralib ketmasin (02-09 naqshi).
    assert calendar.status_code == 200, calendar.text
    assert calendar.json()["open_weekdays"] == list(WIZARD_WEEKDAYS)
    assert (await _activate(api_client, headers, market_id)).status_code == 200


async def test_weekday_choice_at_step_seven_clears_the_gate(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """TIKLANISH: 1-qadamda o'tkazib yuborilgan jadval 7-qadamda yoziladi.

    UI-SPEC §6.6 ning "409 xato emas, yo'l ko'rsatkichi" qoidasi shu
    yerda o'lchanadi: `calendar_missing` bandi `step: 7` bilan keladi,
    foydalanuvchi o'sha qadamga qaytadi, jadvalni yozadi va faollashtirish
    o'tadi. Bu test bo'lmasa 0011 foydalanuvchini boshi berk ko'chaga
    qamab qo'ygan bo'lishi mumkin edi va yuqoridagi ikki test buni
    KO'RSATMAS edi — ular to'siqning YONISHINI tekshiradi, O'CHISHINI
    emas.

    `GET /calendar` PUT'DAN OLDIN ham tekshiriladi: jadval tanlanmagan
    bozor uchun u 409 emas, `[]` beradi (`CalendarRepository.profile()`).
    Usiz 7-qadam ekrani umuman ochilmasdi — ya'ni "yo'l ko'rsatkichi"
    ko'rsatgan joyda ishlamaydigan ekran turardi.
    """
    market_id, headers, _ = await new_market(name="Usta rejim keyin", skip="calendar")
    assert (await _activate(api_client, headers, market_id)).status_code == 409

    before = await api_client.get(CALENDAR_URL, headers=headers)
    saved = await api_client.put(
        f"{CALENDAR_URL}/weekdays",
        json={"open_weekdays": list(WIZARD_WEEKDAYS)},
        headers=headers,
    )

    assert before.status_code == 200, before.text
    assert before.json()["open_weekdays"] == []
    assert saved.status_code == 200, saved.text
    assert saved.json()["open_weekdays"] == list(WIZARD_WEEKDAYS)

    body = await _status(api_client, headers, market_id)

    assert body["calendar_configured"] is True
    assert body["blocking"] == []
    assert (await _activate(api_client, headers, market_id)).status_code == 200


async def test_vendors_do_not_block_activation(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """SOTUVCHISIZ bozor faollashadi (D-11).

    D-11: sotuvchisiz band rasta — ANOMALIYA, taqiq emas. Sotuvchi
    qadami `blocking[]` ga tushsa, usta 6-qadamda o'zini bloklangan deb
    o'ylab, mavjud bo'lmagan majburiyatni bajarishga urinardi
    (UI-SPEC §6.2: "Bu **majburiy**").
    """
    market_id, headers, _ = await new_market(name="Usta sotuvchisiz")

    body = await _status(api_client, headers, market_id)

    assert body["vendors"] == 0
    assert body["can_activate"] is True
    assert body["blocking"] == []
    assert (await _activate(api_client, headers, market_id)).status_code == 200


async def test_vendor_count_is_reported_but_still_does_not_block(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """NAZORAT: sotuvchi qo'shilganda sanoq o'zgaradi, `blocking` esa yo'q.

    Usiz yuqoridagi test `vendors` sanog'i UMUMAN ishlamayotgan holatda
    ham yashil bo'lardi (`0` — "sotuvchi yo'q" ham, "sanoq buzilgan" ham
    bir xil ko'rinadi).
    """
    market_id, headers, _ = await new_market(name="Usta sotuvchili")
    await _post_id(
        api_client,
        headers,
        VENDORS_URL,
        {"full_name": "Usta Sotuvchisi", "phone": WIZARD_VENDOR_PHONE},
    )

    body = await _status(api_client, headers, market_id)

    assert body["vendors"] == 1
    assert body["can_activate"] is True
    assert body["blocking"] == []


async def test_cameras_never_block_activation(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """`cameras` maydoni javobda BOR, qiymati `0`, `blocking` da esa YO'Q (D-16).

    D-16: usta kamerasiz yakunlanadi va bozor "ishlashga tayyor" holatiga
    o'tadi. Maydonning javobda BUGUNDAN turishi 3–5 fazalar uchun
    qoldirilgan ilgak: haqiqiy sanoq qo'shilganda javob SHAKLI
    o'zgarmaydi.
    """
    market_id, headers, _ = await new_market(name="Usta kamerasiz")

    body = await _status(api_client, headers, market_id)

    assert body["cameras"] == 0
    assert not any("camera" in item["code"] for item in body["blocking"])
    assert body["can_activate"] is True


async def test_tariff_gap_reports_numbers_in_detail(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Tarifsiz toifa: `blocking` da kod VA sonli kontekst bor.

    `detail` FAQAT sonlarni tashiydi — UI matni uchta tilda frontendda
    quriladi. Serverdan chiqqan jumla i18n chegarasidan tashqarida
    qolardi.
    """
    market_id, headers, _ = await new_market(name="Usta tarifsiz", skip="tariffs")

    body = await _status(api_client, headers, market_id)

    item = next(x for x in body["blocking"] if x["code"] == "tariff_missing_for_category")
    assert item["step"] == 4
    assert item["detail"] == f"0/{len(WIZARD_CATEGORY_NAMES)}"
    assert body["tariffs_covered"] == 0
    assert body["categories_total"] == len(WIZARD_CATEGORY_NAMES)


async def test_activating_an_active_market_returns_409(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Faollashtirilgan bozorni QAYTA faollashtirib bo'lmaydi.

    Javob `market_is_active`, `market_incomplete` EMAS: bozor to'liq va
    savol umuman to'liqlikda emas. `blocking[]` bilan javob berish
    foydalanuvchini mavjud bo'lmagan ish qidirishga majburlardi.
    """
    market_id, headers, _ = await new_market(name="Usta ikki marta")
    assert (await _activate(api_client, headers, market_id)).status_code == 200

    again = await _activate(api_client, headers, market_id)

    assert again.status_code == 409, again.text
    assert again.json() == {"detail": "market_is_active"}


# ---------------------------------------------------------------------------
# Huquq darvozalari (T-02-79) va `POST /markets` qamrovi
# ---------------------------------------------------------------------------


async def test_market_admin_cannot_create_market(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_today: date,
) -> None:
    """Bozor admini yangi bozor OCHA OLMAYDI (T-02-79).

    Bu — `EXEMPT_ROUTES` dagi `/api/v1/markets` istisnosi uchun qayta
    tiklangan qamrovning bir qismi: matritsa bu marshrutni umuman
    chaqirmaydi, ya'ni darvoza faqat shu yerda sinaladi.
    """
    market_a = two_markets.market_a
    headers = await session_headers(api_client, market_a.admin_phone, market_a.admin_password)

    response = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Ruxsatsiz bozor",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": (market_today - timedelta(days=OPERATING_SINCE_DAYS)).isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 403, response.text
    assert response.json() == {"detail": "forbidden"}


async def test_market_creation_requires_a_token(
    api_client: httpx.AsyncClient,
    market_today: date,
) -> None:
    """Tokensiz `POST /markets` -> **401** (matritsa istisnosining ikkinchi bandi).

    Tana YUBORILADI va javob baribir 401 bo'lishi shart: FastAPI
    dependency'larni tanani tekshirishdan OLDIN hal qiladi. 422 kelgan
    holat "autentifikatsiyadan oldin tana o'qilyapti" degani bo'lardi.
    """
    response = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Tokensiz bozor",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": (market_today - timedelta(days=OPERATING_SINCE_DAYS)).isoformat(),
        },
    )

    assert response.status_code == 401, response.text


async def test_director_can_read_setup_status_but_cannot_activate(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
    two_markets: TwoMarketSeed,
) -> None:
    """D-07: direktor to'liqlikni KO'RADI, faollashtira OLMAYDI.

    Ikkala da'vo bitta testda ATAYIN: faqat manfiy yarmi yozilganda
    "direktor umuman kira olmaydi" holati ham yashil ko'rinardi va
    `MARKET_DATA_VIEW` / `MARKET_MANAGE` ajralishi sinalmasdi.
    """
    market_id, _, _ = await new_market(name="Usta direktor")
    director = await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)
    director = await _select(api_client, director, two_markets.market_a.id)

    # Direktor A bozorining a'zosi, ya'ni u O'Z bozorining holatini
    # o'qiydi — yangi bozor uniki emas va u yerga umuman kira olmaydi.
    readable = await api_client.get(
        SETUP_STATUS_URL.format(market_id=two_markets.market_a.id), headers=director
    )
    blocked = await api_client.post(
        ACTIVATE_URL.format(market_id=two_markets.market_a.id), headers=director
    )
    foreign = await api_client.get(SETUP_STATUS_URL.format(market_id=market_id), headers=director)

    assert readable.status_code == 200, readable.text
    assert blocked.status_code == 403, blocked.text
    assert foreign.status_code == 404, foreign.text
    assert foreign.status_code != 403


async def test_platform_admin_can_complete_every_step(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
) -> None:
    """Pitfall 6 ning bevosita testi: oltala qadam chaqiruvi 403 BERMAYDI.

    D-07 matritsasi 2-fazada `PLATFORM_ADMIN` ga `STALL_MANAGE`,
    `TARIFF_MANAGE` va `VENDOR_MANAGE` ni QO'SHDI. Ularsiz usta 3-qadamda
    to'xtardi va sabab endpoint kodida KO'RINMASDI — matritsa jimgina rad
    etardi. `test_rbac_matrix.py::test_platform_admin_can_run_the_wizard`
    buni LUG'AT darajasida, bu esa HTTP darajasida qulflaydi.
    """
    market_id, headers, operating_since = await new_market(name="Usta huquqlar")

    zone_id = await _post_id(api_client, headers, ZONES_URL, {"name": "Qo'shimcha zona"})
    category_id = await _post_id(api_client, headers, CATEGORIES_URL, {"name": "Qo'shimcha toifa"})
    calls = {
        "tariffs": await api_client.post(
            TARIFFS_URL,
            json={
                "category_id": str(category_id),
                "amount_soum": WIZARD_AMOUNTS[0],
                "valid_from": operating_since.isoformat(),
            },
            headers=headers,
        ),
        "stalls": await api_client.post(
            STALLS_URL,
            json={"code": "999", "zone_id": str(zone_id), "category_id": str(category_id)},
            headers=headers,
        ),
        "vendors": await api_client.post(
            VENDORS_URL,
            json={"full_name": "Usta Ikkinchi", "phone": "+998909991002"},
            headers=headers,
        ),
        "calendar": await api_client.put(
            f"{CALENDAR_URL}/weekdays",
            json={"open_weekdays": list(WIZARD_WEEKDAYS)},
            headers=headers,
        ),
        "setup-status": await api_client.get(
            SETUP_STATUS_URL.format(market_id=market_id), headers=headers
        ),
    }

    forbidden = {name for name, response in calls.items() if response.status_code == 403}
    assert not forbidden, f"platforma admini quyidagi qadamlarda 403 oldi: {sorted(forbidden)}"
    assert all(response.status_code in {200, 201} for response in calls.values()), {
        name: response.status_code for name, response in calls.items()
    }


# ---------------------------------------------------------------------------
# Audit (T-02-83, T-02-84)
# ---------------------------------------------------------------------------


async def test_market_creation_is_audited_at_the_platform_level(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    created_markets: list[UUID],
    tenant_session: Any,
    market_today: date,
) -> None:
    """Bozor yaratish auditi `market_id IS NULL` bilan yoziladi va REKVIZITSIZ.

    =====================================================================
    IKKI MUSTAQIL DA'VO VA IKKALASI HAM KERAK:

    1. Yozuv BOR — `markets` `AUDITED_TABLES` da yo'q, ya'ni DB-trigger
       uni umuman yozmaydi va app-qatlam qatori YAGONA iz (T-02-83).
    2. Yozuv TANLANGAN BOZORNING jurnaliga TUSHMAYDI — chaqiruv A
       bozorini tanlab turgan sessiya bilan yuboriladi va aynan shu
       holatda `principal` dan olingan `market_id` "A bozorida yangi
       bozor yaratildi" degan yolg'on dalil qoldirardi.
    =====================================================================
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    headers = await session_headers(
        api_client,
        two_markets.platform_admin_phone,
        SEED_PASSWORD,
        market_id=two_markets.market_a.id,
    )
    before = await api_client.get("/api/v1/audit/platform?limit=200", headers=headers)
    assert before.status_code == 200, before.text
    seen = {item["id"] for item in before.json()["items"]}

    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Usta auditli",
            "timezone": WIZARD_TIMEZONE,
            "operating_since": operating_since.isoformat(),
            "tin": "987654321",
            "bank_account": "20208000900000000001",
            "bank_mfo": "00014",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    created_markets.append(market_id)

    after = await api_client.get("/api/v1/audit/platform?limit=200", headers=headers)
    assert after.status_code == 200, after.text
    fresh = [
        item
        for item in after.json()["items"]
        if item["id"] not in seen and item["table_name"] == "markets"
    ]

    assert len(fresh) == 1, fresh
    entry = fresh[0]
    assert entry["action"] == "insert"
    assert entry["source"] == "app"
    assert entry["row_id"] == str(market_id)
    assert entry["new_value"] == {
        "name": "Usta auditli",
        "timezone": WIZARD_TIMEZONE,
        "operating_since": operating_since.isoformat(),
    }
    # T-02-84 — rekvizitlar jurnalga UMUMAN tushmaydi (maskalangan holda ham).
    assert "987654321" not in after.text
    assert "20208000900000000001" not in after.text

    # A bozorining jurnalida bu hodisa YO'Q: chaqiruv A tanlangan
    # sessiyada bo'lgan, lekin bozor yaratish A ga tegishli emas.
    assert not _market_dml(await audit_entries(tenant_session, two_markets.market_a.id))


async def test_activation_and_deletion_are_audited_in_the_market_journal(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
    tenant_session: Any,
) -> None:
    """Faollashtirish `update`, o'chirish `delete` — ikkalasi ham `app` manbasi.

    `old` qiymati TAXMIN QILINMAYDI: u yozuvdan oldin o'qiladi, ya'ni
    jurnalda `false -> true` o'tishi ko'rinadi. Faqat `new` yozilgan
    holatda "bozor faollashtirildi" yozuvi uning OLDIN qanday bo'lganini
    aytmasdi va nizoda hech nima isbotlamasdi.

    O'chirish yozuvi bozor qatori YO'Q bo'lgandan KEYIN ham jurnalda
    qoladi — `audit_log.market_id` da FOREIGN KEY ATAYIN yo'q.
    """
    market_id, headers, _ = await new_market(name="Usta audit izlari")
    assert (await _activate(api_client, headers, market_id)).status_code == 200

    activated = _market_dml(await audit_entries(tenant_session, market_id))
    assert len(activated) == 1, activated
    assert activated[0].action == "update"
    assert activated[0].source == "app"
    assert activated[0].old_value == {"is_active": False}
    assert activated[0].new_value == {"is_active": True}

    # O'chirish uchun bozor avval qoralamaga qaytariladi — mahsulot
    # yo'lida bunday o'tish YO'Q (`market_deactivate()` ATAYIN yaratilmagan),
    # shuning uchun bu yerda faqat AUDIT yo'li sinaladi.
    market_id, headers, _ = await new_market(name="Usta o'chirish audit")
    assert (
        await api_client.delete(f"{MARKETS_URL}/{market_id}", headers=headers)
    ).status_code == 204

    deleted = _market_dml(await audit_entries(tenant_session, market_id))
    assert len(deleted) == 1, deleted
    assert deleted[0].action == "delete"
    assert deleted[0].source == "app"
    assert deleted[0].old_value == {"name": "Usta o'chirish audit", "is_active": False}


# ---------------------------------------------------------------------------
# O'chirish (A10, Pitfall 7)
# ---------------------------------------------------------------------------


async def test_draft_market_is_deleted_with_its_domain_rows(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Qoralama o'chadi va uning domen qatorlari ham qolmaydi.

    "204 keldi" yetarli emas: `market_delete_draft()` o'n uchta jadvalni
    ANIQ ro'yxat bo'yicha tozalaydi va ro'yxatdan tushib qolgan jadval
    faqat qoldiq qator sifatida ko'rinadi (FK yiqilishi esa faqat
    `markets` ga havola qiluvchilarda bo'ladi).
    """
    market_id, headers, _ = await new_market(name="Usta o'chiriladigan")

    response = await api_client.delete(f"{MARKETS_URL}/{market_id}")
    unauth = response.status_code
    response = await api_client.delete(f"{MARKETS_URL}/{market_id}", headers=headers)

    assert unauth == 401
    assert response.status_code == 204, response.text
    remaining = sync_owner_conn.execute(
        "SELECT (SELECT count(*) FROM markets WHERE id = %s), "
        "(SELECT count(*) FROM market_profile WHERE market_id = %s), "
        "(SELECT count(*) FROM zones WHERE market_id = %s), "
        "(SELECT count(*) FROM stalls WHERE market_id = %s), "
        "(SELECT count(*) FROM tariffs WHERE market_id = %s)",
        (str(market_id),) * 5,
    ).fetchone()
    assert remaining == (0, 0, 0, 0, 0), remaining


async def test_active_market_cannot_be_deleted(
    api_client: httpx.AsyncClient,
    new_market: Callable[..., Any],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Faollashtirilgan bozor o'chmaydi -> 409 `market_is_active`.

    Qator JOYIDA qolgani ALOHIDA tekshiriladi: 409 javobi funksiya
    qatorlarni o'chirib bo'lib, keyin xato qaytargan holatda ham bir xil
    ko'rinardi (`market_delete_draft()` bayroqni ENG BOSHIDA tekshiradi,
    lekin bu test aynan o'sha tartibni qulflaydi).
    """
    market_id, headers, _ = await new_market(name="Usta jonli")
    assert (await _activate(api_client, headers, market_id)).status_code == 200

    response = await api_client.delete(f"{MARKETS_URL}/{market_id}", headers=headers)

    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "market_is_active"}
    alive = sync_owner_conn.execute(
        "SELECT count(*) FROM markets WHERE id = %s", (str(market_id),)
    ).fetchone()
    assert alive == (1,)
