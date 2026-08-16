"""Shablon, xato hisoboti va validator — konteynersiz unit testlar.

Ikkala modul ham DB ga tegmaydi: `xlsx_template` bayt massivi yozadi,
`import_validator` esa tayyor lug'atlar ustida sof funksiya. Ular
`tests/unit/` da aynan shuning uchun yashaydi — bu darvozalar
migratsiyasiz va konteynersiz o'lchanadi.

Hosil bo'lgan fayl `openpyxl` bilan QAYTA O'QILADI, ya'ni tekshiruv
`XlsxWriter` chaqiruvini emas, FAYLNING O'ZINI ko'radi. Chaqiruvni
mock bilan tekshirish "qochirish funksiyasi chaqirildi" degan da'voni
berardi, lekin `worksheet.write()` bilan yozilgan ikkinchi yo'l
ochilganda ham yashil qolardi.
"""

from __future__ import annotations

import io
import time
from datetime import date
from typing import TYPE_CHECKING, get_args
from uuid import UUID, uuid4

import openpyxl
import pytest
from app.services.import_validator import (
    ImportIssue,
    StallImportRow,
    validate_stall_rows,
    validate_vendor_rows,
)
from app.services.xlsx_reader import SheetRow
from app.services.xlsx_template import (
    FORMULA_PREFIXES,
    build_error_report,
    build_template,
    escape_formula,
)

if TYPE_CHECKING:
    from collections.abc import Callable

UZ = "uz-Latn"
RU = "ru"

ZONE_NAMES = ("Markaziy", "Sharqiy", "G'arbiy")
CATEGORY_NAMES = ("Sabzavot", "Go'sht", "Kiyim")


def open_book(raw: bytes) -> openpyxl.Workbook:
    """Hosil qilingan faylni O'QISH uchun ochadi (`data_only` KERAK EMAS)."""
    return openpyxl.load_workbook(io.BytesIO(raw))


def zones_map() -> dict[str, UUID]:
    return {name: uuid4() for name in ZONE_NAMES}


def categories_map() -> dict[str, UUID]:
    return {name: uuid4() for name in CATEGORY_NAMES}


def stall_row(row: int, *values: str | None) -> SheetRow:
    """Rasta qatori — `xlsx_reader` bergan shaklda (5 ustun)."""
    padded = (*values, *(None,) * (5 - len(values)))
    return SheetRow(row=row, values=padded[:5])


def vendor_row(row: int, *values: str | None) -> SheetRow:
    """Sotuvchi qatori (4 ustun)."""
    padded = (*values, *(None,) * (4 - len(values)))
    return SheetRow(row=row, values=padded[:4])


# ===========================================================================
# T-02-91 — formula injection
# ===========================================================================


@pytest.mark.parametrize(
    "payload",
    [
        "=cmd|'/c calc'!A1",
        "+1+1",
        "-2+3",
        "@SUM(A1)",
        "\t=cmd|'/c calc'!A1",
        '\r=HYPERLINK("http://x")',
    ],
    ids=["equals", "plus", "minus", "at", "tab", "carriage-return"],
)
def test_formula_injection_is_escaped(payload: str) -> None:
    """Oltita xavfli prefiksning HAR BIRI `'` bilan zararsizlantiriladi.

    Hujum MIJOZ MASHINASIDA bajariladi: server faylni yozadi, admin uni
    O'Z Excelida ochadi va formula o'sha yerda ishga tushadi. Ya'ni bu
    saqlangan hujum — zona nomini bir marta yozgan odam keyinchalik
    boshqa odamning kompyuterida kod bajartiradi.

    `\\t` va `\\r` ALOHIDA holat: ular ko'rinmaydi, lekin Excel ularni
    tashlab yuborib keyingi belgiga qaraydi — oddiy `startswith("=")`
    tekshiruvi ularni O'TKAZIB YUBORARDI.

    Tekshiruv HOSIL BO'LGAN FAYLNI qayta o'qiydi, `escape_formula()` ni
    to'g'ridan-to'g'ri chaqirmaydi: funksiya to'g'ri bo'lib, uni
    chaqirmaydigan yozish yo'li ochilgan holatda ham test qizarishi
    kerak.
    """
    zones = dict.fromkeys([payload], uuid4())

    raw = build_template("stalls", UZ, list(zones), [payload])
    book = open_book(raw)
    reference = book["Ma'lumotnoma"]

    stored = str(reference.cell(row=2, column=1).value)

    # XAVFSIZLIK DA'VOSI — faylning O'ZIDA.
    assert stored.startswith("'"), f"qochirilmagan qiymat: {stored!r}"
    assert not stored.startswith(FORMULA_PREFIXES)

    # MAZMUN DA'VOSI — faqat KO'RINADIGAN prefikslar uchun. `\t` va `\r`
    # OOXML da boshqarув belgisi sifatida `_x0009_`/`_x000D_` shaklida
    # kodlanadi (o'lchandi: `'_x000D_=HYPERLINK(...)`), ya'ni aynan
    # tenglik ularda kutubxona konvensiyasini sinardi, bizning kodni
    # emas. Himoya esa yuqoridagi ikki assertion bilan qamralgan —
    # prefiks kodlanganda Excel uni formula deb HAM o'qimaydi.
    if payload.isprintable():
        assert stored == "'" + payload


def test_escape_formula_leaves_safe_values_untouched() -> None:
    """NAZORAT: xavfsiz matn O'ZGARMAYDI.

    Usiz `escape_formula` HAR DOIM `'` qo'shadigan holatda ham yuqoridagi
    oltita test yashil bo'lardi — va o'shanda har bir zona nomi Excelda
    apostrof bilan boshlanardi.
    """
    for safe in ("Markaziy", "1", "Aliyev Vali", "+998901234567".lstrip("+"), ""):
        assert escape_formula(safe) == safe


def test_error_report_escapes_the_message() -> None:
    """Xato XABARI ham qochiriladi — u foydalanuvchi qiymatini O'ZIDA saqlaydi.

    `zone_not_found` xabari faylda yozilgan zona nomini AYNAN qaytaradi
    (`14-qator: '...' zonasi topilmadi`), ya'ni hujumchi zona ustuniga
    formula yozib, uni xato hisobotiga QAYTARIB olishi mumkin. Ikkinchi
    yo'l birinchisidan mustaqil va shuning uchun alohida test.
    """
    issues = [ImportIssue(14, "zone_not_found", "=cmd|'/c calc'!A1")]

    book = open_book(build_error_report(issues, UZ))
    sheet = book["Xatolar"]

    assert sheet.cell(row=2, column=3).value == "'=cmd|'/c calc'!A1"


def test_numeric_looking_text_stays_text() -> None:
    """`"1"` katakda MATN bo'lib qoladi, songa aylanmaydi.

    `write()` `"1"` ni songa, `"=1+1"` ni esa FORMULAGA aylantirardi —
    ya'ni qochirishdan keyin ham hujum tiklanardi. `write_string()`
    ikkala yo'lni ham yopadi. Rasta kodi uchun bu qo'shimcha ma'noga
    ega: `"007"` songa aylanganda `7` bo'lib qolardi.
    """
    book = open_book(build_template("stalls", UZ, list(ZONE_NAMES), list(CATEGORY_NAMES)))
    sheet = book["Rastalar"]

    assert sheet.cell(row=2, column=1).value == "1"
    assert isinstance(sheet.cell(row=2, column=1).value, str)


# ===========================================================================
# Open Question 5 — yashirin ma'lumotnoma varag'i
# ===========================================================================


def test_template_has_hidden_reference_sheet() -> None:
    """Ikkinchi varaq MAVJUD va u YASHIRIN."""
    book = open_book(build_template("stalls", UZ, list(ZONE_NAMES), list(CATEGORY_NAMES)))

    assert book.sheetnames == ["Rastalar", "Ma'lumotnoma"]
    assert book["Ma'lumotnoma"].sheet_state == "hidden"

    reference = book["Ma'lumotnoma"]
    stored = [reference.cell(row=index + 2, column=1).value for index in range(len(ZONE_NAMES))]
    assert stored == list(ZONE_NAMES)


def test_template_binds_data_validation_to_the_reference_sheet() -> None:
    """Zona va toifa ustunlariga ochiluvchi ro'yxat BOG'LANGAN.

    Havola varaq nomini QO'SHTIRNOQ bilan olishi shart: `Ma'lumotnoma`
    ichida APOSTROF bor va qo'shtirnoqsiz havola Excelda jimgina
    buzilardi — ro'yxat ko'rinmasdi, lekin fayl "to'g'ri" bo'lib
    ochilaverardi.
    """
    book = open_book(build_template("stalls", UZ, list(ZONE_NAMES), list(CATEGORY_NAMES)))
    sheet = book["Rastalar"]

    sources = [rule.formula1 for rule in sheet.data_validations.dataValidation]
    assert len(sources) == 2
    assert any("$A$2:$A$4" in source for source in sources)
    assert any("$B$2:$B$4" in source for source in sources)
    for source in sources:
        assert source.startswith("'Ma''lumotnoma'!"), source


def test_vendor_template_has_no_reference_sheet() -> None:
    """Sotuvchi shablonida lug'at varag'i YO'Q (rasta kodlari minglab bo'lishi mumkin)."""
    book = open_book(build_template("vendors", UZ, list(ZONE_NAMES), list(CATEGORY_NAMES)))

    assert book.sheetnames == ["Sotuvchilar"]


def test_unknown_template_kind_is_rejected() -> None:
    """Noma'lum `kind` — `ValueError` (router uni 422 ga aylantiradi)."""
    with pytest.raises(ValueError, match="noma'lum shablon turi"):
        build_template("payments", UZ, [], [])


# ===========================================================================
# O-05 — shablon TILDA, parser POZITSIYA bo'yicha
# ===========================================================================


def test_template_columns_are_positional() -> None:
    """uz-Latn va ru shablonlari BIR XIL ustun sonida va bir xil namunada.

    O-05 ning yadrosi: sarlavha MATNI tilga qarab o'zgaradi, lekin
    ustun POZITSIYALARI o'zgarmaydi va parser aynan pozitsiyani o'qiydi.
    Ya'ni ruscha shablonni yuklab olgan admin uzbekcha interfeysda
    import qilsa ham fayl ishlaydi.

    Sarlavhalarning HAQIQATAN farq qilishi ham tekshiriladi — aks holda
    tarjima umuman qo'llanmagan holatda ham test yashil bo'lardi.
    """
    uz = open_book(build_template("stalls", UZ, list(ZONE_NAMES), list(CATEGORY_NAMES)))["Rastalar"]
    ru = open_book(build_template("stalls", RU, list(ZONE_NAMES), list(CATEGORY_NAMES)))["Прилавки"]

    uz_header = [uz.cell(row=1, column=index + 1).value for index in range(5)]
    ru_header = [ru.cell(row=1, column=index + 1).value for index in range(5)]
    assert len(uz_header) == len(ru_header) == 5
    assert uz_header != ru_header, "tarjima umuman qo'llanmagan"
    assert uz_header[0] == "kod"
    assert ru_header[0] == "номер"

    uz_sample = [uz.cell(row=2, column=index + 1).value for index in range(5)]
    ru_sample = [ru.cell(row=2, column=index + 1).value for index in range(5)]
    assert uz_sample == ru_sample, "namunaviy qator tilga qarab SURILGAN"


def test_template_is_parsed_back_by_the_reader_in_every_locale() -> None:
    """UCHALA tildagi shablon O'QUVCHI qatlamdan bir xil natija beradi.

    Bu O-05 ning uchidan-uchiga isboti: shablon -> `read_rows()` ->
    namunaviy qator AYNAN bir xil pozitsiyalarda. Faqat sarlavha
    matnini solishtirish "til o'zgardi" ni ko'rsatardi, lekin
    "parser buzilmadi" ni EMAS.
    """
    from app.services.xlsx_reader import read_rows

    parsed = []
    for locale in ("uz-Latn", "uz-Cyrl", "ru"):
        raw = build_template("stalls", locale, list(ZONE_NAMES), list(CATEGORY_NAMES))
        rows = read_rows(raw, expected_columns=5)
        assert len(rows) == 1, locale
        assert rows[0].row == 2, locale
        parsed.append(rows[0].values)

    assert parsed[0] == parsed[1] == parsed[2]
    assert parsed[0][:4] == ("1", "Markaziy", "Sabzavot", "active")


def test_unknown_locale_falls_back_to_uz_latn() -> None:
    """Noma'lum til shablonni BUZMAYDI — u uz-Latn ga tushadi.

    Istisno ko'tarilsa usta oqimi butunlay to'silardi, sababi esa
    mutlaqo ahamiyatsiz bo'lardi ("shablon yuklab olinmadi, chunki til
    kodi kutilmagan").
    """
    book = open_book(build_template("stalls", "de-DE", list(ZONE_NAMES), list(CATEGORY_NAMES)))

    assert book.sheetnames[0] == "Rastalar"


# ===========================================================================
# UI-SPEC §8.5 — xato hisoboti HAMMASINI oladi
# ===========================================================================


def test_error_report_contains_every_issue() -> None:
    """300 xato berilganda faylda 300 QATOR bor (UI faqat 50 tasini ko'rsatadi).

    Ekran va fayl ATAYIN har xil qamrovda: 300 ta DOM elementi
    skrinrider uchun foydasiz, 300 qatorli Excel esa aynan tuzatish
    uchun qulay.
    """
    issues = [
        ImportIssue(index, "zone_not_found", f"{index}-qator: xato") for index in range(2, 302)
    ]

    sheet = open_book(build_error_report(issues, UZ))["Xatolar"]

    assert sheet.max_row == 301, "sarlavha + 300 xato"
    assert sheet.cell(row=301, column=3).value == "301-qator: xato"


def test_error_report_row_numbers_are_preserved() -> None:
    """Qator raqamlari SON sifatida va AYNAN o'zgarishsiz yoziladi.

    Son sifatida — Excelda saralash uchun: matn tartibida `"100"`
    `"20"` dan OLDIN turardi va 1000 qatorli hisobotni tartiblab
    bo'lmasdi.
    """
    issues = [
        ImportIssue(14, "zone_not_found", "14-qator: 'Sabzavot' zonasi topilmadi"),
        ImportIssue(88, "duplicate_code_in_file", "88-qator: 12 raqami 14-qatorda ham bor"),
        ImportIssue(100, "invalid_status", "100-qator: 'yopiq' holati noma'lum"),
    ]

    sheet = open_book(build_error_report(issues, UZ))["Xatolar"]

    assert [sheet.cell(row=index + 2, column=1).value for index in range(3)] == [14, 88, 100]
    assert sheet.cell(row=3, column=2).value == "duplicate_code_in_file"
    assert sheet.cell(row=3, column=3).value == "88-qator: 12 raqami 14-qatorda ham bor"


def test_empty_error_report_is_still_a_valid_file() -> None:
    """Bo'sh ro'yxat ham yaroqli `.xlsx` beradi (avtofiltr diapazoni buzilmaydi)."""
    sheet = open_book(build_error_report([], UZ))["Xatolar"]

    assert sheet.max_row == 1
    assert sheet.cell(row=1, column=1).value == "qator"


# ===========================================================================
# D-14 — validator: xatolar QATOR RAQAMI bilan
# ===========================================================================


def test_zone_not_found_message_names_the_row_and_the_zone() -> None:
    """`{row}-qator: '{nom}' zonasi topilmadi` — D-14 dagi AYNAN shakl."""
    zones = zones_map()
    categories = categories_map()

    accepted, issues = validate_stall_rows(
        [stall_row(14, "5", "Sabzavot", "Sabzavot", "active")],
        zones=zones,
        categories=categories,
        existing_codes=set(),
    )

    assert accepted == []
    assert len(issues) == 1
    assert issues[0].row == 14
    assert issues[0].code == "zone_not_found"
    assert issues[0].message == "14-qator: 'Sabzavot' zonasi topilmadi"


def test_duplicate_code_message_names_both_rows() -> None:
    """Takroriy kod xabarida IKKALA qator raqami ham bor.

    Faqat joriy qatorni ko'rsatish adminni "qayerda yana bor?" degan
    savol bilan qoldirardi va u 1000 qatorli faylni QO'LDA qidirardi.

    ⚠ BIRINCHI uchrash XATO EMAS va u `accepted` da qoladi — xato faqat
    IKKINCHISIDA. Bu D-14 ni buzmaydi: `issues` bo'sh bo'lmagani uchun
    router `accepted` ni UMUMAN yozmaydi (`test_all_or_nothing` shu
    zanjirni uchidan-uchiga o'lchaydi). Ikkala qatorni ham xato deb
    belgilash adminni to'g'ri qatorni "tuzatishga" majburlardi.
    """
    accepted, issues = validate_stall_rows(
        [
            stall_row(14, "12", "Markaziy", "Sabzavot"),
            stall_row(88, "12", "Sharqiy", "Go'sht"),
        ],
        zones=zones_map(),
        categories=categories_map(),
        existing_codes=set(),
    )

    assert [row.row for row in accepted] == [14]
    assert [issue.code for issue in issues] == ["duplicate_code_in_file"]
    assert issues[0].message == "88-qator: 12 raqami 14-qatorda ham bor"


def test_every_error_in_a_row_is_reported_at_once() -> None:
    """Bitta qatordagi BARCHA xatolar bir yo'la qaytariladi.

    Birinchi xatoda to'xtash adminni "tuzat -> yukla -> yangi xato"
    siklga tushirardi: 300 xatoli fayl 300 marta yuklanardi.
    """
    _, issues = validate_stall_rows(
        [stall_row(7, "", "Yo'q zona", "Yo'q toifa", "yopiq")],
        zones=zones_map(),
        categories=categories_map(),
        existing_codes=set(),
    )

    assert sorted(issue.code for issue in issues) == [
        "category_not_found",
        "empty_code",
        "invalid_status",
        "zone_not_found",
    ]
    assert {issue.row for issue in issues} == {7}


def test_missing_required_column_is_row_too_short() -> None:
    """Bo'sh zona/toifa ustuni `row_too_short` beradi, `zone_not_found` EMAS.

    Ikkalasi foydalanuvchi uchun BOSHQA harakat talab qiladi: birinchisi
    "ustunni to'ldiring", ikkinchisi "nomni tekshiring". Ularni bir kod
    ostida birlashtirish guruhlangan sanoqni (UI-SPEC §8.5) ma'nosiz
    qilardi.
    """
    _, issues = validate_stall_rows(
        [stall_row(3, "9")],
        zones=zones_map(),
        categories=categories_map(),
        existing_codes=set(),
    )

    assert sorted(issue.code for issue in issues) == ["row_too_short", "row_too_short"]
    assert issues[0].message == "3-qator: 'zona' ustuni bo'sh"


def test_status_defaults_to_active_and_unknown_status_is_rejected() -> None:
    """Bo'sh holat -> `active`; noma'lum matn -> `invalid_status`.

    JIMGINA `active` ga tushish eng xavfli yechim bo'lardi: `yopiq` deb
    yozilgan rastaga 6-fazada kunlik hisob yozilardi va sabab hech
    qayerda ko'rinmasdi.
    """
    zones = zones_map()
    categories = categories_map()

    accepted, issues = validate_stall_rows(
        [stall_row(2, "9", "Markaziy", "Sabzavot", None)],
        zones=zones,
        categories=categories,
        existing_codes=set(),
    )
    assert issues == []
    assert accepted[0].status == "active"

    _, bad = validate_stall_rows(
        [stall_row(2, "9", "Markaziy", "Sabzavot", "yopiq")],
        zones=zones,
        categories=categories,
        existing_codes=set(),
    )
    assert [issue.code for issue in bad] == ["invalid_status"]


def test_zone_lookup_is_case_insensitive() -> None:
    """`sabzavot` ham `Sabzavot` ni topadi.

    `zones.name` unikaligi REGISTRGA SEZGIR, ya'ni aniq mos kelishga
    tayanish 1000 qatorlik `zone_not_found` to'foni berardi va sabab
    ko'rinmasdi ("zona ro'yxatda turibdi-ku?").
    """
    zones = zones_map()
    categories = categories_map()

    accepted, issues = validate_stall_rows(
        [stall_row(2, "9", "MARKAZIY", "sabzavot", "ACTIVE")],
        zones=zones,
        categories=categories,
        existing_codes=set(),
    )

    assert issues == []
    assert accepted[0].zone_id == zones["Markaziy"]
    assert accepted[0].category_id == categories["Sabzavot"]


def test_ambiguous_case_folded_name_is_not_guessed() -> None:
    """Registr bilan farq qiluvchi IKKI zona bo'lsa taxmin QILINMAYDI.

    `Sabzavot` va `SABZAVOT` ikkalasi ham mavjud bo'lsa, `sabzavot`
    qaysinisiga tegishli ekani NOMA'LUM. Taxmin qilib yozish rastani
    noto'g'ri zonaga qo'yardi va buni hech kim sezmasdi — xato esa
    faqat 6-fazadagi zona bo'yicha hisobotда ko'rinardi.
    """
    zone_a, zone_b = uuid4(), uuid4()
    zones = {"Markaziy": zone_a, "MARKAZIY": zone_b}

    accepted, issues = validate_stall_rows(
        [
            stall_row(2, "9", "markaziy", "Sabzavot"),
            stall_row(3, "10", "Markaziy", "Sabzavot"),
        ],
        zones=zones,
        categories=categories_map(),
        existing_codes=set(),
    )

    assert [issue.code for issue in issues] == ["zone_not_found"]
    assert issues[0].row == 2
    # NAZORAT: AYNAN mos kelgan qator baribir o'tadi.
    assert [row.zone_id for row in accepted] == [zone_a]


# ===========================================================================
# D-15 — mavjud yozuv XATO EMAS
# ===========================================================================


def test_existing_codes_are_skipped_not_reported() -> None:
    """Mavjud kod xato ro'yxatiga TUSHMAYDI va natijadan CHIQARILADI.

    Ikkala da'vo ham majburiy va ular MUSTAQIL:

    * xato ro'yxatiga tushsa — D-14 tufayli BUTUN fayl rad etilardi va
      qayta import umuman ishlamasdi;
    * natijada qolsa — `stall_code_claim()` `BEFORE INSERT` triggeri
      `ON CONFLICT DO NOTHING` da HAM yiqilib, 409 berardi (02-05 dan
      kelgan kirish sharti).
    """
    zones = zones_map()
    categories = categories_map()

    accepted, issues = validate_stall_rows(
        [
            stall_row(2, "1", "Markaziy", "Sabzavot"),
            stall_row(3, "2", "Sharqiy", "Go'sht"),
            stall_row(4, "3", "G'arbiy", "Kiyim"),
        ],
        zones=zones,
        categories=categories,
        existing_codes={"1", "3"},
    )

    assert issues == []
    assert [row.code for row in accepted] == ["2"]


def test_existing_code_is_still_checked_for_duplicates_inside_the_file() -> None:
    """Mavjud kod fayl ICHIDA takrorlansa baribir xato bo'ladi.

    "Mavjud -> o'tkazib yubor" qoidasi takroriylik tekshiruvidan OLDIN
    qo'llansa, ikki marta yozilgan mavjud kod jimgina o'tib ketardi va
    admin o'z faylidagi haqiqiy xatoni hech qachon ko'rmasdi.
    """
    _, issues = validate_stall_rows(
        [
            stall_row(2, "1", "Markaziy", "Sabzavot"),
            stall_row(3, "1", "Sharqiy", "Go'sht"),
        ],
        zones=zones_map(),
        categories=categories_map(),
        existing_codes={"1"},
    )

    assert [issue.code for issue in issues] == ["duplicate_code_in_file"]


# ===========================================================================
# Sotuvchi validatori
# ===========================================================================


def test_vendor_phone_is_normalised_to_e164() -> None:
    """Telefon SHU YERDA E.164 ga keltiriladi (import DTO'dan o'tmaydi).

    `VendorRequest._normalize` faqat HTTP tanasi uchun ishlaydi. Usiz
    faylda `901234567` shaklida kelgan raqam bazadagi `+998901234567`
    bilan MOS TUSHMASDI va D-15 idempotentligi buzilardi — har qayta
    import "yangi" sotuvchi yaratardi (02-10 ning ogohlantirishi).
    """
    accepted, issues = validate_vendor_rows(
        [vendor_row(2, "Aliyev Vali", "90 123 45 67")],
        stalls_by_code={},
        existing_phones=set(),
        default_from=date(2026, 1, 15),
    )

    assert issues == []
    assert accepted[0].phone == "+998901234567"


def test_vendor_invalid_phone_and_duplicate_phone() -> None:
    """Yaroqsiz va takroriy telefon — ikkita alohida kod."""
    accepted, issues = validate_vendor_rows(
        [
            vendor_row(2, "Aliyev Vali", "+998901234567"),
            vendor_row(3, "Karimova Nodira", "12345"),
            vendor_row(4, "Rasulov Sardor", "901234567"),
        ],
        stalls_by_code={},
        existing_phones=set(),
        default_from=date(2026, 1, 15),
    )

    # 2-qator TO'G'RI (birinchi uchrash), 4-qator esa AYNAN o'sha
    # raqamning boshqa yozilishi — `normalize_phone()` ikkalasini ham
    # `+998901234567` ga keltirgani uchun takror ANIQLANADI. Xom matnni
    # solishtirish bu holatni O'TKAZIB YUBORARDI.
    assert [row.row for row in accepted] == [2]
    assert [(issue.row, issue.code) for issue in issues] == [
        (3, "invalid_phone"),
        (4, "duplicate_phone_in_file"),
    ]
    assert issues[1].message == "4-qator: +998901234567 raqami 2-qatorda ham bor"


def test_vendor_stall_code_must_exist_and_is_unique_in_the_file() -> None:
    """Noma'lum rasta -> `stall_not_found`; bitta rastaga ikki sotuvchi -> xato.

    Ikkinchisi bo'lmasa fayl `ex_stall_assignments_no_overlap` ga
    urilib, QATOR RAQAMISIZ 409 berardi — D-14 aynan shuni taqiqlaydi,
    va bu sotuvchi faylidagi eng ehtimolli xato.
    """
    stall_id = uuid4()

    _, issues = validate_vendor_rows(
        [
            vendor_row(2, "Aliyev Vali", "+998901110001", "1"),
            vendor_row(3, "Karimova Nodira", "+998901110002", "1"),
            vendor_row(4, "Rasulov Sardor", "+998901110003", "999"),
        ],
        stalls_by_code={"1": stall_id},
        existing_phones=set(),
        default_from=date(2026, 1, 15),
    )

    assert [(issue.row, issue.code) for issue in issues] == [
        (3, "duplicate_code_in_file"),
        (4, "stall_not_found"),
    ]
    assert issues[0].message == "3-qator: 1 raqamli rasta 2-qatorda ham biriktirilgan"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-08-01", date(2026, 8, 1)),
        ("01.08.2026", date(2026, 8, 1)),
        ("01/08/2026", date(2026, 8, 1)),
    ],
    ids=["iso", "dotted", "slashed"],
)
def test_vendor_start_date_accepts_the_common_shapes(text: str, expected: date) -> None:
    """ISO'dan tashqari `dd.mm.yyyy` ham qabul qilinadi.

    Excel SANA tipidagi katakni o'quvchi ISO ga keltiradi, lekin admin
    ustunni MATN sifatida to'ldirishi juda ehtimolli. D-14
    (all-or-nothing) tufayli bitta bunday katak BUTUN faylni qaytarib
    yuborardi.
    """
    accepted, issues = validate_vendor_rows(
        [vendor_row(2, "Aliyev Vali", "+998901110001", None, text)],
        stalls_by_code={},
        existing_phones=set(),
        default_from=date(2026, 1, 15),
    )

    assert issues == []
    assert accepted[0].from_date == expected


def test_vendor_bad_date_is_rejected_and_missing_date_defaults() -> None:
    """O'qilmagan sana -> `invalid_date`; bo'sh sana -> `operating_since`.

    Standart qiymat `business_today()` EMAS: import qilingan tarix
    bugundan boshlanardi va o'tmishga hisob qayta hisoblanganda rasta
    "sotuvchisiz" ko'rinardi (A3).
    """
    accepted, issues = validate_vendor_rows(
        [
            vendor_row(2, "Aliyev Vali", "+998901110001", None, None),
            vendor_row(3, "Karimova Nodira", "+998901110002", None, "31-fevral"),
        ],
        stalls_by_code={},
        existing_phones=set(),
        default_from=date(2026, 1, 15),
    )

    assert [(issue.row, issue.code) for issue in issues] == [(3, "invalid_date")]
    assert accepted[0].from_date == date(2026, 1, 15)


def test_existing_phones_are_skipped() -> None:
    """Mavjud telefon -> `skipped`, biriktirish HAM yozilmaydi (D-15).

    Biriktirish yozilsa har qayta import o'sha rastaga YANGI davr
    qo'shib, `EXCLUDE` konstraytiga urilardi — "hech narsa
    o'zgarmadi" o'rniga 409 kelardi.
    """
    accepted, issues = validate_vendor_rows(
        [
            vendor_row(2, "Aliyev Vali", "+998901110001", "1"),
            vendor_row(3, "Karimova Nodira", "+998901110002"),
        ],
        stalls_by_code={"1": uuid4()},
        existing_phones={"+998901110001"},
        default_from=date(2026, 1, 15),
    )

    assert issues == []
    assert [row.phone for row in accepted] == ["+998901110002"]


def test_accepted_rows_keep_their_excel_row_number() -> None:
    """Qabul qilingan qator ham O'Z Excel raqamini saqlaydi.

    Yozuv paytida chiqadigan poyga xatosi (409) uchun kerak: log'da
    qaysi qator to'qnashganini ko'rish mumkin bo'lishi shart, garchi
    javobda u ko'rsatilmasa ham.
    """
    accepted, _ = validate_stall_rows(
        [stall_row(77, "9", "Markaziy", "Sabzavot")],
        zones=zones_map(),
        categories=categories_map(),
        existing_codes=set(),
    )

    assert isinstance(accepted[0], StallImportRow)
    assert accepted[0].row == 77


# ===========================================================================
# MARKET-07 — xodimlar shabloni (uchinchi varaq turi)
# ===========================================================================

STAFF_ROLES = ("cashier", "inspector")
"""Bozor adminining darajasi (`assignable_roles(False)`) — shablonga shu tushadi."""

_STAFF_SHEETS = {"uz-Latn": "Xodimlar", "uz-Cyrl": "Ходимлар", "ru": "Сотрудники"}


def staff_template(locale: str = UZ, roles: tuple[str, ...] = STAFF_ROLES) -> bytes:
    """`staff` shabloni — zona/toifa lug'atlari bu turga UMUMAN tegmaydi."""
    return build_template("staff", locale, (), (), roles=list(roles))


def test_staff_template_headers_are_translated_in_every_locale() -> None:
    """Uchala tilda sarlavha BOSHQA, ustun soni esa AYNAN bir xil (O-05)."""
    headers = []
    for locale, sheet_name in _STAFF_SHEETS.items():
        book = open_book(staff_template(locale))
        assert book.sheetnames[0] == sheet_name, locale
        sheet = book[sheet_name]
        headers.append(tuple(sheet.cell(row=1, column=index + 1).value for index in range(3)))

    assert headers[0] == ("F.I.Sh.", "telefon", "rol")
    assert headers[2] == ("Ф.И.О.", "телефон", "роль")
    assert len(set(headers)) == 3, "tarjima umuman qo'llanmagan"


def test_staff_template_is_parsed_back_identically_in_every_locale() -> None:
    """Shablon -> `read_rows(expected_columns=3)` uchala tilda AYNAN bir xil.

    Faqat sarlavhani solishtirish "til o'zgardi" ni ko'rsatardi, lekin
    "parser buzilmadi" ni EMAS — namunaviy qator ustunlar bo'yicha
    surilgan holatda ham sarlavha testi yashil qolardi.
    """
    from app.services.xlsx_reader import read_rows

    parsed = []
    for locale in _STAFF_SHEETS:
        rows = read_rows(staff_template(locale), expected_columns=3)
        assert len(rows) == 1, locale
        assert rows[0].row == 2, locale
        parsed.append(rows[0].values)

    assert parsed[0] == parsed[1] == parsed[2]
    # ⚠ Telefon `+` SIZ: `+` — `FORMULA_PREFIXES` a'zosi va qochirish uni
    # `'+998...` ga aylantirardi, ya'ni namunaviy qator O'Z shablonining
    # importidan `invalid_phone` bilan qaytardi (02-24 deviatsiya #1).
    assert parsed[0] == ("Aliyev Vali", "998901234567", "cashier")


def test_staff_sample_row_is_accepted_by_the_validator() -> None:
    """UCHIDAN-UCHIGA: namunaviy qator O'ZGARTIRILMASDAN import qilinadi.

    Bu — A6 ustunlar tartibining va D-16 ning eng kuchli isboti:
    namunadagi `cashier` TARJIMA QILINMAYDI (u DB kontenti, aynan
    `_STALL_SAMPLE_STATUS` dagi `active` bilan bir xil sabab), ya'ni
    ruscha shablonni to'ldirgan admin ham to'g'ri qiymat yuboradi.
    """
    from app.services.import_validator import validate_staff_rows
    from app.services.xlsx_reader import read_rows

    rows = read_rows(staff_template(RU), expected_columns=3)
    accepted, issues = validate_staff_rows(
        rows,
        allowed_roles=frozenset(STAFF_ROLES),
        existing_member_phones=(),
    )

    assert issues == []
    assert [row.phone for row in accepted] == ["+998901234567"]
    assert [row.roles for row in accepted] == [("cashier",)]


def test_staff_template_has_a_hidden_role_reference_sheet() -> None:
    """Rollar YASHIRIN varaqda va C ustuniga ochiluvchi ro'yxat bilan bog'langan.

    ⚠ `data_validation` — QULAYLIK, DARVOZA EMAS: haqiqiy tekshiruv
    `validate_staff_rows` da. Ro'yxat faqat qo'lda yozishdagi imlo
    xatosini (`invalid_role` ning eng ko'p uchraydigan sababi) yo'q
    qiladi.
    """
    book = open_book(staff_template())

    assert book.sheetnames == ["Xodimlar", "Ma'lumotnoma"]
    reference = book["Ma'lumotnoma"]
    assert reference.sheet_state == "hidden"
    assert reference.cell(row=1, column=1).value == "Rollar"
    assert [reference.cell(row=index + 2, column=1).value for index in range(2)] == list(
        STAFF_ROLES
    )

    # openpyxl boshlang'ich `=` ni O'ZI tashlaydi (mavjud `stalls` testi
    # ham `startswith("'Ma''lumotnoma'!")` bilan tekshiradi).
    sources = [rule.formula1 for rule in book["Xodimlar"].data_validations.dataValidation]
    assert len(sources) == 1
    assert sources[0] == "'Ma''lumotnoma'!$A$2:$A$3"

    ranges = [str(rule.sqref) for rule in book["Xodimlar"].data_validations.dataValidation]
    assert ranges[0].startswith("C2"), f"ro'yxat C ustuniga bog'lanmagan: {ranges[0]}"


def test_staff_role_with_a_formula_prefix_is_escaped() -> None:
    """Rol ro'yxati ham `_write_text()` dan o'tadi (T-02-184).

    Rollar `assignable_roles()` dan keladi, ya'ni bugun ular xavfsiz
    enum qiymatlari. Test KELAJAK uchun: ro'yxat manbai bir kun
    sozlanadigan bo'lsa, yozish yo'li allaqachon qochirilgan bo'lishi
    kerak — aks holda himoya jimgina teshilardi.
    """
    reference = open_book(staff_template(roles=("=cmd|'/c calc'!A1",)))["Ma'lumotnoma"]

    stored = str(reference.cell(row=2, column=1).value)
    assert stored == "'=cmd|'/c calc'!A1"
    assert not stored.startswith(FORMULA_PREFIXES)


def test_staff_template_without_roles_has_no_reference_sheet() -> None:
    """Bo'sh ro'yxat varaq QURMAYDI (`stalls` dagi bilan bir xil qoida)."""
    book = open_book(staff_template(roles=()))

    assert book.sheetnames == ["Xodimlar"]


# ===========================================================================
# D-17 — daftar shabloni (TO'RTINCHI varaq turi, 08-14)
# ===========================================================================

_LEDGER_SHEETS = {"uz-Latn": "Daftar", "uz-Cyrl": "Дафтар", "ru": "Тетрадь"}

LEDGER_COLUMN_COUNT = 2
"""⛔ AYNAN IKKITA — UI-SPEC §10.3 ning literal bandi.

Uchinchi ustun (sotuvchi ismi, izoh) QO'SHILMAYDI: daftar QOG'OZ va har
qo'shimcha ustun kunlik ishni sekinlashtiradi. Son shu yerda NOMLANADI,
chunki quyidagi to'rt test uni turli tomondan o'lchaydi va bitta joyda
turgan konstanta ularni ajralib ketishdan saqlaydi.
"""


def ledger_template(locale: str = UZ) -> bytes:
    """`ledger` shabloni — zona/toifa/rol lug'atlari bu turga UMUMAN tegmaydi."""
    return build_template("ledger", locale, (), ())


def test_ledger_template_has_exactly_two_columns() -> None:
    """⛔ UCHINCHI USTUN YO'Q — VA U BO'SH KATAK BILAN O'LCHANADI.

    Faqat ikkita sarlavhani tekshirish uchinchisi qo'shilgan holatda ham
    YASHIL qolardi. Shuning uchun da'vo IKKI TOMONLAMA: birinchi ikkitasi
    TO'LDIRILGAN, uchinchisi esa `None`.
    """
    sheet = open_book(ledger_template())[_LEDGER_SHEETS[UZ]]

    header = [sheet.cell(row=1, column=index + 1).value for index in range(3)]

    assert header[:LEDGER_COLUMN_COUNT] == ["rasta kodi", "daftar summasi"]
    assert header[LEDGER_COLUMN_COUNT] is None, f"uchinchi ustun qo'shilgan: {header}"


def test_ledger_template_headers_are_translated_in_every_locale() -> None:
    """Uchala tilda sarlavha BOSHQA, ustun soni esa AYNAN bir xil (O-05)."""
    headers = []
    for locale, sheet_name in _LEDGER_SHEETS.items():
        book = open_book(ledger_template(locale))
        assert book.sheetnames[0] == sheet_name, locale
        sheet = book[sheet_name]
        headers.append(
            tuple(sheet.cell(row=1, column=index + 1).value for index in range(LEDGER_COLUMN_COUNT))
        )

    assert headers[0] == ("rasta kodi", "daftar summasi")
    assert headers[2] == ("номер прилавка", "сумма по тетради")
    assert len(set(headers)) == 3, "tarjima umuman qo'llanmagan"


def test_ledger_template_is_parsed_back_identically_in_every_locale() -> None:
    """Shablon -> `read_rows(expected_columns=2)` uchala tilda AYNAN bir xil.

    O-05 ning daftar shablonidagi shakli: sarlavha MATNI tilga qarab
    o'zgaradi, ustun POZITSIYALARI esa o'zgarmaydi. Faqat sarlavhani
    solishtirish "til o'zgardi" ni ko'rsatardi, "parser buzilmadi" ni EMAS.
    """
    from app.services.xlsx_reader import read_rows

    parsed = []
    for locale in _LEDGER_SHEETS:
        rows = read_rows(ledger_template(locale), expected_columns=LEDGER_COLUMN_COUNT)
        assert len(rows) == 1, locale
        assert rows[0].row == 2, locale
        parsed.append(rows[0].values)

    assert parsed[0] == parsed[1] == parsed[2]
    assert parsed[0] == ("1", "150000")


def test_ledger_sample_row_carries_no_formula_prefix() -> None:
    """⛔ NAMUNAVIY QATOR O'Z SHABLONIDAN QAYTIB O'QILGANDA TOZA BO'LADI.

    `_SAMPLE_PHONE` da o'lchangan tuzoqning (02-24 deviatsiya #1) daftar
    shaklidagi takrori: `+`, `=`, `-` bilan boshlangan qiymat
    `escape_formula()` dan apostrof bilan chiqadi va o'sha qiymat O'Z
    shablonining importida XATO berardi. Summa `-` bilan yozilsa
    (`-150000`) aynan shu holat yuzaga kelardi.
    """
    from app.services.xlsx_reader import read_rows

    values = read_rows(ledger_template(), expected_columns=LEDGER_COLUMN_COUNT)[0].values

    for value in values:
        assert value is not None
        assert not value.startswith(FORMULA_PREFIXES), f"qochirilgan namuna: {value!r}"


def test_ledger_template_has_no_reference_sheet() -> None:
    """Daftar shablonida lug'at varag'i YO'Q — rasta kodlari minglab bo'lishi mumkin.

    `vendors` dagi bilan AYNAN bir xil qaror va bir xil sabab: 1000
    elementli ochiluvchi ro'yxat faylni foydasiz kattalashtirardi.
    """
    assert open_book(ledger_template()).sheetnames == [_LEDGER_SHEETS[UZ]]


def test_template_kinds_are_exactly_four() -> None:
    """`TEMPLATE_KINDS` — `Literal` bilan sinxron qoladigan YAGONA ro'yxat.

    ⚠ SON TEST NOMIDA VA U ONGLI RAVISHDA UCHDAN TO'RTGA OSHIRILDI
      (08-14, R-11): daftar shabloni QO'SHILDI. Nom sonni aytadi, ya'ni
      to'plamning o'sishi diff'da KO'RINADI — nomni saqlab qiymatni
      o'zgartirish o'sha o'sishni JIMGINA qilardi.
    """
    from app.services.xlsx_template import TEMPLATE_KINDS

    assert TEMPLATE_KINDS == ("stalls", "vendors", "staff", "ledger")


def test_the_three_template_registries_stay_in_sync() -> None:
    """⛔ UCH REYESTR BIR VAQTDA YANGILANADI — VA BU MEXANIK O'LCHANADI.

    `xlsx_template.TEMPLATE_KINDS` (ish vaqtidagi darvoza),
    `imports.ImportKind` (FastAPI so'rov parametri) va
    `imports._TEMPLATE_PERMISSIONS` (huquq xaritasi) QO'LDA sinxron
    saqlanadi — uchalasi ham `TEMPLATE_KINDS` docstringida nomlangan.

    ⛔ AJRALGAN HOLAT JIMGINA BO'LARDI: `Literal` ga qo'shilgan-u
       xaritaga qo'shilmagan tur `KeyError` bilan **500** berardi (422
       emas), teskarisi esa o'lik yozuv qoldirardi.
    """
    from app.api.v1.imports import ImportKind, _TEMPLATE_PERMISSIONS
    from app.services.xlsx_template import TEMPLATE_KINDS

    assert set(get_args(ImportKind)) == set(TEMPLATE_KINDS)
    assert set(_TEMPLATE_PERMISSIONS) == set(TEMPLATE_KINDS)


def test_the_ledger_template_sits_behind_stall_manage() -> None:
    """⛔ `STALL_MANAGE` — `REPORT_VIEW` EMAS (D-20 + 08-RESEARCH OQ-5).

    Daftarni yuklaydigan odam bajaruvchi: nazoratchi yoki admin, ⛔ KASSIR
    EMAS. `REPORT_VIEW` bu yerda ISHLATILMAYDI — u O'QISH huquqi va uni
    yozuv yuzasiga qo'yish direktorga (unda `report_view` bor) daftar
    yuklash imkonini ochardi.

    ⚠ «Nazoratchi» LAVOZIM sifatida o'qiladi va u amalda `market_admin`
      hisobiga kiradi: `ROLE_PERMISSIONS[INSPECTOR]` bugun AYNAN
      `{OCCUPANCY_REVIEW}` (T-05-58) va unga yozuv huquqi berish 5-faza
      qarorini (ko'r audit) kengaytirardi.
    """
    from app.api.v1.imports import _TEMPLATE_PERMISSIONS
    from app.security.rbac import Permission

    assert _TEMPLATE_PERMISSIONS["ledger"] is Permission.STALL_MANAGE


# ===========================================================================
# Bayt determinizmi (08-01) — IKKALA MAHSULOT EKSPORT YO'LI
# ===========================================================================


@pytest.mark.parametrize(
    "build",
    [
        lambda: build_template("stalls", UZ, ZONE_NAMES, CATEGORY_NAMES),
        lambda: build_error_report(
            [ImportIssue(row=2, code="zone_not_found", message="2-qator: zona yo'q")],
            UZ,
        ),
        lambda: build_template("ledger", UZ, (), ()),
    ],
    ids=["template", "error-report", "ledger-template"],
)
def test_two_builds_are_byte_identical(build: Callable[[], bytes]) -> None:
    """AYNI kirish -> AYNI baytlar (08-01, RECON-04).

    ⛔ BU O'LCHOV 08-01 GACHA QIZIL EDI va bu ONGLI KENGAYTMA: ikkala
    quruvchi ham `xlsxwriter.Workbook(...)` ni to'g'ridan-to'g'ri
    chaqirar, `set_properties()` ni ham, ZIP muzlatishni ham
    CHAQIRMASDI. Ya'ni determinizm faqat test fiksturasida
    (`karmana_seed`) bor edi, MAHSULOT eksporti esa har chaqiruvda
    boshqa baytlar berardi.

    ⚠ `sleep(1.1)` MAJBURIY va u testni sekinlashtirish uchun emas.
    `zipfile` a'zo sanasini SOAT'dan oladi va uning aniqligi 2 sekund.
    Ikki chaqiruv ayni sekundda bo'lsa test MUZLATISHSIZ HAM yashil
    bo'lardi — ya'ni aynan o'lchamoqchi bo'lgan nosozlikni (T-02-172)
    ko'rmasdi.
    """
    first = build()
    time.sleep(1.1)
    second = build()

    assert first == second
