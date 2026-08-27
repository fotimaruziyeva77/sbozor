"""Excel import — D-13/D-14/D-15 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL `tests/unit/test_xlsx_*.py` NING O'RNINI BOSMAYDI.

Unit testlar UCHTA SERVIS MODULINI alohida-alohida sinaydi (hujum
namunalari, qochirish, qator raqamlari). Bu yerdagi savol boshqa:
**butun zanjir haqiqiy bazada ishlaydimi** — validatsiya -> tranzaksiya
-> konstraytlar -> javob.

Ikkisi bir-birini almashtira olmaydi. Validator to'g'ri bo'lib, router
uni CHAQIRMASA unit testlar YASHIL qolardi; DB darvozasi (`stall_code_
claim()`) esa unit testda umuman ko'rinmaydi.
=============================================================================

D-14 (ALL-OR-NOTHING) SANOQ BILAN O'LCHANADI, JAVOB BILAN EMAS.

"422 keldi" degan da'vo yetarli emas: endpoint qatorlarni yozib bo'lib,
so'ng 422 qaytargan holatda ham u to'g'ri bo'lardi. Shuning uchun
`test_all_or_nothing` importdan OLDIN va KEYIN `stalls` sanog'ini
solishtiradi va ular AYNAN teng bo'lishi shart.

SANALAR `market_today` FIXTURE'IDAN, sobit yozilmaydi (02-07 deviatsiya
#1). `A_OPERATING_SINCE` esa sobit qolaveradi — u hech qachon kelajakka
aylanmaydi.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import pytest
import xlsxwriter
from fixtures.admin_api import (
    IMPORT_STALLS_URL,
    IMPORT_VENDORS_URL,
    IMPORTS_ERRORS_URL,
    IMPORTS_TEMPLATE_URL,
    STALLS_URL,
    VENDORS_URL,
    session_headers,
)
from fixtures.market_domain import (
    A_CATEGORY_NAMES,
    A_OPERATING_SINCE,
    A_STALL_CODES,
    A_ZONE_NAMES,
)
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STALL_HEADER = ["kod", "zona", "toifa", "holat", "izoh"]
VENDOR_HEADER = ["F.I.Sh.", "telefon", "rasta kodi", "boshlanish sanasi"]

NEW_CODES = ("9101", "9102", "9103")
"""Seed'da UMUMAN uchramaydigan raqamlar (`A_STALL_CODES` bilan solishtiring).

Seed kodi ishlatilsa javob D-15 bo'yicha `skipped` bo'lardi — ya'ni 200,
lekin `inserted = 0`, va test "import ishlamadi" deb qizarardi.
"""

IMPORT_PHONES = ("+998909910001", "+998909910002", "+998909910003")
"""Import testlari yaratadigan sotuvchi telefonlari.

Seed'lar `+99890111...` (`A_VENDOR_PHONES`) va `+99897...` ni,
matritsa esa `+99890999...` ni ishlatadi — bu to'rtinchi diapazon
ularning birortasiga ham tegmaydi.
"""


# ---------------------------------------------------------------------------
# Fayl quruvchilar
# ---------------------------------------------------------------------------


def build_xlsx(header: list[str], rows: list[list[Any]], *, sheet: str = "Rastalar") -> bytes:
    """`XlsxWriter` bilan haqiqiy `.xlsx` quradi (repoda binar fayl YO'Q)."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet(sheet)
    worksheet.write_row(0, 0, header)
    for index, row in enumerate(rows, start=1):
        worksheet.write_row(index, 0, row)
    workbook.close()
    return buffer.getvalue()


def stall_file(rows: list[list[Any]]) -> bytes:
    return build_xlsx(STALL_HEADER, rows)


def vendor_file(rows: list[list[Any]]) -> bytes:
    return build_xlsx(VENDOR_HEADER, rows, sheet="Sotuvchilar")


def upload(payload: bytes, name: str = "import.xlsx") -> dict[str, tuple[str, bytes, str]]:
    """`multipart/form-data` yuklamasi."""
    return {"file": (name, payload, XLSX_MEDIA_TYPE)}


def good_rows(codes: tuple[str, ...] = NEW_CODES) -> list[list[Any]]:
    """HAQIQIY zona va toifa nomlari bilan to'g'ri qatorlar.

    Nomlar seed konstantalaridan olinadi (`A_ZONE_NAMES` /
    `A_CATEGORY_NAMES`) — to'qib chiqarilgan nom `zone_not_found`
    berardi va test importni emas, validatorning RAD ETISH yo'lini
    sinardi (02-06 da o'rnatilgan qoida: kutilma seed'dan olinadi).
    """
    return [[code, A_ZONE_NAMES[0], A_CATEGORY_NAMES[0], "active", ""] for code in codes]


# ---------------------------------------------------------------------------
# Sessiyalar va DB sanoqlari
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`STALL_MANAGE` + `VENDOR_MANAGE`).

    `market_domain` ATAYIN argument sifatida: zona va toifa lug'ati
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi import
    `zone_not_found` bilan tugardi.
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


def count_stalls(market_scope: MarketScope, market_domain: MarketDomainSeed) -> int:
    """`stalls` sanog'i — ILOVA roli va tenant konteksti bilan.

    Superuser bilan O'QILMAYDI: D-14 da'vosi aynan ilova ko'radigan
    haqiqat ustida bo'lishi kerak.
    """
    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT count(*) FROM stalls").fetchone()
    assert row is not None
    return int(row[0])


def count_periods(market_scope: MarketScope, market_domain: MarketDomainSeed) -> int:
    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT count(*) FROM stall_category_periods").fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# D-14 — ALL-OR-NOTHING
# ===========================================================================


async def test_all_or_nothing(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Uchta xatoli fayl -> 422, va bazada NOL yangi qator (D-14).

    Fayl ATAYIN ARALASH: uchta qator to'g'ri, uchtasi xatoli. Faqat
    xatoli qatorlardan iborat fayl bilan test "hech narsa yozilmadi"
    ni isbotlay olmasdi — yoziladigan narsaning O'ZI yo'q edi.

    Sanoq oldin va keyin solishtiriladi: "422 keldi" degan da'vo
    endpoint qatorlarni yozib bo'lib, so'ng 422 qaytargan holatda ham
    to'g'ri bo'lardi.
    """
    before = count_stalls(market_scope, market_domain)
    periods_before = count_periods(market_scope, market_domain)

    payload = stall_file(
        [
            *good_rows(),
            ["9201", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""],
            ["9202", A_ZONE_NAMES[0], "Yo'q toifa", "active", ""],
            ["9203", A_ZONE_NAMES[0], A_CATEGORY_NAMES[0], "yopiq", ""],
        ]
    )

    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert body["detail"] == "import_validation_failed"
    assert {issue["row"] for issue in body["errors"]} == {5, 6, 7}
    assert sorted(issue["code"] for issue in body["errors"]) == [
        "category_not_found",
        "invalid_status",
        "zone_not_found",
    ]

    assert count_stalls(market_scope, market_domain) == before
    assert count_periods(market_scope, market_domain) == periods_before


async def test_error_counts_are_grouped(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """`error_counts` — kod bo'yicha guruhlangan sanoq (UI-SPEC §8.5).

    300 ta qator o'qib bo'lmaydi, 3 ta jumla o'qiladi va harakatga
    aylanadi. `errors` massivi esa TO'LIQ keladi — kesish KLIENTDA
    (birinchi 50 ta), serverda emas.
    """
    payload = stall_file(
        [
            ["9301", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""],
            ["9302", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""],
            ["9303", A_ZONE_NAMES[0], "Yo'q toifa", "active", ""],
        ]
    )

    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert body["error_counts"] == {"zone_not_found": 2, "category_not_found": 1}
    assert len(body["errors"]) == 3
    assert body["errors"][0]["message"] == f"2-qator: '{"Yo'q zona"}' zonasi topilmadi"


async def test_error_messages_carry_the_excel_row_number(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Xabardagi raqam admin EXCELDA ko'radigan raqam (D-14).

    Sarlavha 1-qator, ya'ni ikkinchi ma'lumot qatorining raqami — 3.
    Nol yoki birdan qayta sanash butunlay boshqa qatorni ko'rsatardi.
    """
    payload = stall_file(
        [
            good_rows()[0],
            ["9302", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""],
        ]
    )

    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(payload)
    )

    body = response.json()["detail"]
    assert body["errors"][0]["row"] == 3
    assert body["errors"][0]["message"].startswith("3-qator: ")


# ===========================================================================
# Muvaffaqiyatli import
# ===========================================================================


async def test_successful_import_creates_stalls_and_category_periods(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Har rasta uchun toifa davri ham yoziladi, `valid_from = operating_since`.

    ⚠ BU 02-11 NING FAOLLASHTIRISH DARVOZASI UCHUN MAJBURIY. `setup-
    status` har rastada `valid_from <= operating_since` bo'lgan davrni
    TALAB qiladi; import `business_today()` yozsa, import qilingan
    rastalar `stalls_without_category` bo'lib sanalardi va bozor HECH
    QACHON faollashmasdi — sabab esa hech qayerda ko'rinmasdi.
    """
    before = count_stalls(market_scope, market_domain)

    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(good_rows()))
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"inserted": 3, "skipped": 0}
    assert count_stalls(market_scope, market_domain) == before + 3

    with market_scope(market_domain.market_a.market_id) as conn:
        rows = conn.execute(
            "SELECT s.code, p.valid_from FROM stalls s "
            "JOIN stall_category_periods p ON p.stall_id = s.id "
            "WHERE s.code = ANY(%s) ORDER BY s.code",
            (list(NEW_CODES),),
        ).fetchall()

    assert [row[0] for row in rows] == list(NEW_CODES)
    assert {row[1] for row in rows} == {A_OPERATING_SINCE}


async def test_imported_stalls_are_visible_through_the_registry(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT: import qilingan rasta `GET /stalls` da ko'rinadi.

    DB sanog'i yetarli emas — u qator YOZILGANINI ko'rsatadi, lekin
    uning MAHSULOT yuzasida ko'rinishini emas. Zona va toifa havolalari
    noto'g'ri bog'langan bo'lsa `_STALL_ROWS` ning `LATERAL` lari
    `null` berardi va sanoq baribir o'sardi.
    """
    await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(good_rows()))
    )

    listed = await api_client.get(
        STALLS_URL, params={"q": NEW_CODES[0], "limit": 10}, headers=admin_headers
    )

    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert [item["code"] for item in items] == [NEW_CODES[0]]
    assert items[0]["zone_name"] == A_ZONE_NAMES[0]
    assert items[0]["category_name"] == A_CATEGORY_NAMES[0]


# ===========================================================================
# D-15 — qayta import IDEMPOTENT
# ===========================================================================


async def test_reimport_is_idempotent(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Bir xil faylni IKKI marta yuklash: ikkinchisida `inserted=0`.

    Uchta mustaqil da'vo va uchalasi ham majburiy:

    * javob `{inserted: 0, skipped: 3}` — admin "38 tasi qayerga
      ketdi?" savolisiz qoladi (UI-SPEC §8.5);
    * `stalls` sanog'i O'ZGARMAGAN;
    * toifa davrlari sanog'i ham O'ZGARMAGAN — ya'ni "mavjud kod
      o'tkazib yuborildi" qoidasi IKKALA jadvalga ham qo'llanadi.
      Faqat `stalls` ga qo'llansa har qayta import o'sha rastaga
      IKKINCHI toifa davrini qo'shardi va 6-fazadagi hisob ikki
      marta yozilardi.
    """
    payload = upload(stall_file(good_rows()))
    first = await api_client.post(IMPORT_STALLS_URL, headers=admin_headers, files=payload)
    assert first.status_code == 200, first.text

    stalls_after_first = count_stalls(market_scope, market_domain)
    periods_after_first = count_periods(market_scope, market_domain)

    second = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(good_rows()))
    )

    assert second.status_code == 200, second.text
    assert second.json() == {"inserted": 0, "skipped": 3}
    assert count_stalls(market_scope, market_domain) == stalls_after_first
    assert count_periods(market_scope, market_domain) == periods_after_first


async def test_partial_reimport_adds_only_new_rows(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Faylga ikkita yangi qator qo'shilib qayta yuklanadi -> `inserted=2`."""
    await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(good_rows()))
    )
    before = count_stalls(market_scope, market_domain)

    extended = good_rows((*NEW_CODES, "9104", "9105"))
    second = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(extended))
    )

    assert second.status_code == 200, second.text
    assert second.json() == {"inserted": 2, "skipped": 3}
    assert count_stalls(market_scope, market_domain) == before + 2


async def test_reimport_does_not_touch_the_vendor_history(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Qayta import mavjud sotuvchi TARIXINI ham tegmaydi (D-15).

    Sotuvchi faylida rasta kodi bor, ya'ni birinchi import biriktirish
    davrini ham yozadi. Qayta importda telefon MAVJUD bo'lgani uchun
    qator butunlay o'tkazib yuboriladi — biriktirish HAM yozilmaydi.
    Aks holda o'sha rastaga ikkinchi OCHIQ davr qo'shilib, `EXCLUDE`
    konstraytiga urilardi va admin "hech narsa o'zgarmadi" o'rniga
    409 olardi.
    """
    free_stall = market_domain.market_a.unassigned_stall_id
    assert free_stall is not None, "seed `unassigned_stall_id` ni to'ldirmagan"

    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(free_stall),)).fetchone()
    assert row is not None
    free_code = row[0]

    rows = [["Import Sotuvchi", IMPORT_PHONES[0], free_code, ""]]
    first = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin_headers, files=upload(vendor_file(rows))
    )
    assert first.status_code == 200, first.text
    assert first.json() == {"inserted": 1, "skipped": 0}

    with market_scope(market_domain.market_a.market_id) as conn:
        count_row = conn.execute(
            "SELECT count(*) FROM stall_assignments WHERE stall_id = %s", (str(free_stall),)
        ).fetchone()
    assert count_row is not None
    assignments_after_first = int(count_row[0])

    second = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin_headers, files=upload(vendor_file(rows))
    )

    assert second.status_code == 200, second.text
    assert second.json() == {"inserted": 0, "skipped": 1}

    with market_scope(market_domain.market_a.market_id) as conn:
        count_row = conn.execute(
            "SELECT count(*) FROM stall_assignments WHERE stall_id = %s", (str(free_stall),)
        ).fetchone()
    assert count_row is not None
    assert int(count_row[0]) == assignments_after_first


async def test_retired_code_is_reported_not_silently_skipped(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """CHETLANGAN kod 409 beradi, `skipped` bo'lib JIMGINA yo'qolmaydi (D-02).

    `existing_stall_codes()` FAQAT tirik rastalarni beradi, ya'ni
    chetlangan kod validatordan o'tadi va `INSERT` ga boradi. U yerda
    `stall_code_claim()` triggeri uni `23505` bilan to'xtatadi va
    javob 409 `import_conflict` bo'ladi.

    ⚠ ALTERNATIVA XAVFLIROQ EDI: chetlangan kodlarni ham "mavjud" deb
    o'tkazib yuborish faylda qolgan eski raqamni foydalanuvchiga
    KO'RSATMASDAN yo'q qilardi — admin uni import qilinди deb o'ylab
    yurardi. 409 esa "bu raqam qaytarilmaydi" degan haqiqatni ko'rsatadi.

    Tranzaksiya butunlay orqaga qaytadi, ya'ni D-14 buzilmaydi.
    """
    retired_code = "9401"
    market_a = market_domain.market_a.market_id
    with market_scope(market_a) as conn:
        conn.execute(
            "INSERT INTO stall_code_registry (market_id, code, stall_id) VALUES (%s, %s, %s)",
            (str(market_a), retired_code, str(market_domain.market_a.stall_ids[0])),
        )
    before = count_stalls(market_scope, market_domain)

    payload = stall_file([*good_rows(("9402",)), *good_rows((retired_code,))])
    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "import_conflict"}
    assert "duplicate key" not in response.text
    assert count_stalls(market_scope, market_domain) == before


# ===========================================================================
# Fayl darvozalari
# ===========================================================================


async def test_oversized_file_returns_422(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Chegaradan katta yuklama -> 422 `file_too_large`.

    Yuklama ATAYIN `.xlsx` deb nomlangan, lekin mazmuni ahamiyatsiz:
    hajm darvozasi parse'dan OLDIN turadi va u fayl NOMIGA emas,
    BAYTLARGA qaraydi.
    """
    response = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(b"\0" * (5 * 1024 * 1024 + 1)),
    )

    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "file_too_large"}


async def test_non_xlsx_returns_422(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """CSV yuklama -> 422 `unsupported_file_type`."""
    response = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files={"file": ("rastalar.csv", b"kod,zona\n1,Markaziy\n", "text/csv")},
    )

    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "unsupported_file_type"}


async def test_xlsx_named_file_that_is_not_a_zip_returns_422(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """`.xlsx` deb NOMLANGAN, lekin ZIP bo'lmagan fayl ham rad etiladi.

    Kengaytma tekshiruvi faqat QULAYLIK. Haqiqiy darvoza — ZIP va XML
    qatlami, u fayl nomiga umuman qaramaydi. Bu test aynan shu
    ajratishni qulflaydi: kengaytma darvozasi YAGONA himoya bo'lib
    qolsa, `.xlsx` deb nomlangan PDF parserga yetib borardi.
    """
    response = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "hisobot.xlsx"),
    )

    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "unsupported_file_type"}


# ===========================================================================
# Tenant va huquq darvozalari
# ===========================================================================


async def test_cross_tenant_zone_name_is_not_found(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """B bozorining zona nomi A ga import qilinganda `zone_not_found` (T-02-94).

    Lug'at `TenantSessionDep` ostida RLS bilan o'qiladi, ya'ni B ning
    zonasi A ning lug'atiga UMUMAN tushmaydi. Javob o'sha nomning
    boshqa bozorda MAVJUDLIGINI oshkor qilmaydi — u noma'lum nom bilan
    AYNAN bir xil (`Yo'q zona`).

    ⚠ Ikkinchi assertion mustaqil va u yuk ko'taruvchi: begona nom
    bilan noma'lum nom uchun xabar BAYT-BAYT bir xil bo'lishi shart.
    """
    foreign_zone = "Yagona"  # `B_ZONE_NAMES[0]` — B bozorining YAGONA zonasi

    foreign = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(stall_file([["9501", foreign_zone, A_CATEGORY_NAMES[0], "active", ""]])),
    )
    unknown = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(stall_file([["9501", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""]])),
    )

    assert foreign.status_code == 422, foreign.text
    body = foreign.json()["detail"]
    assert [issue["code"] for issue in body["errors"]] == ["zone_not_found"]
    assert unknown.status_code == foreign.status_code
    assert unknown.json()["detail"]["error_counts"] == body["error_counts"]


async def test_market_id_in_the_file_cannot_move_rows(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
    two_markets: TwoMarketSeed,
) -> None:
    """Faylga qo'shimcha ustun qo'yish qatorni BOSHQA bozorga ko'chira olmaydi.

    `market_id` FAQAT `principal` dan olinadi (T-02-54) va shablonda
    bunday ustun umuman yo'q. Ortiqcha ustun `xlsx_reader` da
    KESILADI, ya'ni u validatorga ham yetib bormaydi.

    Da'vo IKKI TOMONLAMA: qator A da BOR va B da YO'Q. Faqat
    birinchisini tekshirish qator IKKALA bozorda ham paydo bo'lgan
    holatda ham yashil qolardi (02-08 dagi qoida).
    """
    payload = build_xlsx(
        [*STALL_HEADER, "market_id"],
        [
            [
                NEW_CODES[0],
                A_ZONE_NAMES[0],
                A_CATEGORY_NAMES[0],
                "active",
                "",
                str(two_markets.market_b.id),
            ]
        ],
    )

    response = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 200, response.text
    with market_scope(market_domain.market_a.market_id) as conn:
        in_a = conn.execute(
            "SELECT count(*) FROM stalls WHERE code = %s", (NEW_CODES[0],)
        ).fetchone()
    with market_scope(two_markets.market_b.id) as conn:
        in_b = conn.execute(
            "SELECT count(*) FROM stalls WHERE code = %s", (NEW_CODES[0],)
        ).fetchone()

    assert in_a is not None and int(in_a[0]) == 1
    assert in_b is not None and int(in_b[0]) == 0


async def test_director_cannot_import(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """Direktor import qila olmaydi (D-07); admin — NAZORAT holati.

    Nazoratsiz test endpoint HAR KIMGA 403 beradigan holatda ham
    yashil bo'lardi.
    """
    payload = upload(stall_file(good_rows()))

    denied_stalls = await api_client.post(
        IMPORT_STALLS_URL, headers=director_headers, files=payload
    )
    denied_vendors = await api_client.post(
        IMPORT_VENDORS_URL,
        headers=director_headers,
        files=upload(vendor_file([["Direktor Sotuvchi", IMPORT_PHONES[1], "", ""]])),
    )
    denied_template = await api_client.get(IMPORTS_TEMPLATE_URL, headers=director_headers)

    assert denied_stalls.status_code == 403, denied_stalls.text
    assert denied_vendors.status_code == 403, denied_vendors.text
    assert denied_template.status_code == 403, denied_template.text

    allowed = await api_client.post(
        IMPORT_STALLS_URL, headers=admin_headers, files=upload(stall_file(good_rows()))
    )
    assert allowed.status_code == 200, allowed.text


async def test_import_requires_a_token(api_client: httpx.AsyncClient) -> None:
    """Tokensiz so'rov 401 — FAYL yuborilgan holatda ham.

    FastAPI dependency'larni tanani (va faylni) tekshirishdan OLDIN
    hal qiladi. Javob 422 bo'lsa, marshrut autentifikatsiyadan OLDIN
    yuklamani o'qiyapti degani va bu alohida ko'rinishi kerak.
    """
    response = await api_client.post(IMPORT_STALLS_URL, files=upload(stall_file(good_rows())))

    assert response.status_code == 401, response.text


# ===========================================================================
# Shablon va xato hisoboti
# ===========================================================================


async def test_template_download_returns_xlsx(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Shablon `.xlsx` bo'lib keladi — sehrli baytlar VA `Content-Type`.

    Faqat `Content-Type` ni tekshirish yetarli emas: sarlavhani server
    o'zi qo'yadi, ya'ni bo'sh yoki buzuq tana bilan ham u to'g'ri
    bo'lardi. `PK` — ZIP ning sehrli baytlari va `.xlsx` — bu ZIP.
    """
    response = await api_client.get(IMPORTS_TEMPLATE_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == XLSX_MEDIA_TYPE
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.content[:2] == b"PK"


async def test_downloaded_template_is_accepted_by_the_import(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """UCHIDAN-UCHIGA: yuklab olingan shablon O'ZI import qilinadi.

    Bu — O-05 ning va A6 ustunlar tartibining eng kuchli isboti.
    Shablonning namunaviy qatori HAQIQIY zona va toifa nomlari bilan
    to'ldiriladi (`_sample_row`), ya'ni uni o'zgartirmasdan yuborish
    HAQIQIY rasta yaratadi. Ustunlar tartibi shablon bilan parser
    orasida bir kun ajralib ketsa, AYNAN shu test qizaradi.

    Namunaviy kod `"1"` seed'da YO'Q (`A_STALL_CODES` — `2, 10, 100, 7,
    55, 3`), ya'ni qator HAQIQATAN yoziladi va oqim oxirigacha boradi:
    zona nomi topildi, toifa nomi topildi, holat tanildi, qator
    `stalls` ga tushdi. Dastlabki yozuv `skipped = 1` kutgan va AYNAN
    shu farq bilan yiqilgan — kutilma seed'dan tekshirilmagan edi
    (02-06 qoidasi).

    Ikkinchi assertion o'sha kutilmani QULFLAYDI: kod seed'ga
    qo'shilsa test darhol qizaradi va sabab ko'rinadi.
    """
    assert "1" not in A_STALL_CODES, (
        "shablon namunasi seed kodiga aylandi — quyidagi kutilma endi `skipped`"
    )

    template = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "stalls"}, headers=admin_headers
    )
    assert template.status_code == 200, template.text

    imported = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(template.content, "shablon.xlsx"),
    )

    assert imported.status_code == 200, imported.text
    assert imported.json() == {"inserted": 1, "skipped": 0}


async def test_vendor_template_download(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """`?kind=vendors` — sotuvchi shabloni (`VENDOR_MANAGE`)."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "vendors"}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    assert response.content[:2] == b"PK"


async def test_unknown_template_kind_returns_422(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Noma'lum `kind` -> 422 (`Literal` tipi)."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "payments"}, headers=admin_headers
    )

    assert response.status_code == 422, response.text


async def test_error_report_round_trip(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """422 javobining `errors` massivi AYNAN qaytarilib `.xlsx` olinadi.

    Bu — UI-SPEC §8.5 dagi "xatolar ro'yxatini yuklab olish" oqimining
    uchidan-uchiga isboti: server javobining shakli klient qaytaradigan
    tananing shakli bilan MOS bo'lishi shart. Ular ajralib ketsa
    (masalan `message` maydoni nomi o'zgarsa) yuklab olish 422 berardi.
    """
    failed = await api_client.post(
        IMPORT_STALLS_URL,
        headers=admin_headers,
        files=upload(stall_file([["9601", "Yo'q zona", A_CATEGORY_NAMES[0], "active", ""]])),
    )
    assert failed.status_code == 422, failed.text
    errors = failed.json()["detail"]["errors"]

    report = await api_client.post(
        IMPORTS_ERRORS_URL, headers=admin_headers, json={"errors": errors}
    )

    assert report.status_code == 200, report.text
    assert report.headers["content-type"] == XLSX_MEDIA_TYPE
    assert report.content[:2] == b"PK"


async def test_error_report_rejects_an_oversized_list(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Chegaradan uzun massiv -> 422 (T-02-97).

    Kirish MAHSULOT yo'lidan kelmaydi — u 422 javobining NUSXASI, ya'ni
    uni hech kim tekshirmagan. Chegarasiz endpoint o'z-o'ziga DoS
    bo'lardi.
    """
    payload = {
        "errors": [
            {"row": index, "code": "zone_not_found", "message": "x"} for index in range(5_001)
        ]
    }

    response = await api_client.post(IMPORTS_ERRORS_URL, headers=admin_headers, json=payload)

    assert response.status_code == 422, response.text


# ===========================================================================
# Sotuvchi importi
# ===========================================================================


async def test_vendor_import_creates_vendors_and_assignments(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Sotuvchi + OCHIQ biriktirish davri; telefon E.164 ga keltiriladi.

    Faylda raqam MILLIY shaklda (`90 991 00 03`) yozilgan — admin uni
    aynan shunday yozadi. `normalize_phone()` chegarada emas, IMPORT
    yo'lida chaqiriladi (`VendorRequest` DTO'si bu yerda ishlamaydi),
    ya'ni usiz bazada ikki xil shakl yashardi va D-15 idempotentligi
    buzilardi.
    """
    free_stall = market_domain.market_a.unassigned_stall_id
    assert free_stall is not None
    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(free_stall),)).fetchone()
    assert row is not None
    free_code = row[0]

    payload = vendor_file([["Import Sotuvchi", "90 991 00 03", free_code, ""]])
    response = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"inserted": 1, "skipped": 0}

    listed = await api_client.get(
        VENDORS_URL, params={"q": "Import Sotuvchi"}, headers=admin_headers
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["phone"] == IMPORT_PHONES[2]
    assert items[0]["stall_codes"] == [free_code]

    with market_scope(market_domain.market_a.market_id) as conn:
        period = conn.execute(
            "SELECT lower(period), upper(period) FROM stall_assignments WHERE stall_id = %s",
            (str(free_stall),),
        ).fetchone()
    assert period is not None
    assert period[0] == A_OPERATING_SINCE
    assert period[1] is None, "import qilingan biriktirish OCHIQ davr bo'lishi kerak"


async def test_vendor_import_reports_row_numbered_errors(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """Yaroqsiz telefon va noma'lum rasta — qator raqami bilan, hech narsa yozilmaydi."""
    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT count(*) FROM vendors").fetchone()
    assert row is not None
    before = int(row[0])

    payload = vendor_file(
        [
            ["To'g'ri Sotuvchi", IMPORT_PHONES[0], "", ""],
            ["Yomon Telefon", "12345", "", ""],
            ["Yo'q Rasta", IMPORT_PHONES[1], "99999", ""],
        ]
    )

    response = await api_client.post(
        IMPORT_VENDORS_URL, headers=admin_headers, files=upload(payload)
    )

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert [(issue["row"], issue["code"]) for issue in body["errors"]] == [
        (3, "invalid_phone"),
        (4, "stall_not_found"),
    ]

    with market_scope(market_domain.market_a.market_id) as conn:
        row = conn.execute("SELECT count(*) FROM vendors").fetchone()
    assert row is not None
    assert int(row[0]) == before
