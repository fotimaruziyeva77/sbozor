"""Karmana miqyosidagi generatorning SOF birlik darvozalari (konteynersiz, bazasiz).

=============================================================================
BU FAYL GENERATORNING O'ZINI SINAYDI, IMPORT QUVURINI EMAS.

Quvur `tests/integration/test_karmana_scale_import.py` da, HAQIQIY
endpointlar ustida o'lchanadi. Bu yerdagi savol undan oldin keladi va u
alohida javob talab qiladi: **generator o'zi va'da qilgan faylni
quryaptimi?**

Ikkisi bir-birini almashtira olmaydi. Generator noto'g'ri fayl qursa,
integratsiya testi «quvur ishlamadi» deb qizarardi va sabab noto'g'ri
joyda izlanardi (02-17 ning darsi: «yozildi» ≠ «ishlaydi»).
=============================================================================

ENG MUHIM DARVOZA — `test_generator_does_not_import_the_template_module`.

U `02-VERIFICATION.md` ning 2-bo'shlig'ini yopiq ushlab turadi: yuk
quvurning O'ZI ishlab chiqargan shablondan kelsa, butun miqyos o'lchovi
yana o'z-o'ziga qaytadi. Darvoza manba matnini `ast` bilan o'qiydi —
`sys.modules` izi bilan EMAS: shablon moduli boshqa test tomonidan
import qilingan bo'lsa iz darvozani YOLG'ON qizartirardi, generator
undan foydalanmasa ham.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from app.services import xlsx_export
from app.services.import_validator import (
    ImportIssue,
    StallImportRow,
    VendorImportRow,
    validate_stall_rows,
    validate_vendor_rows,
)
from app.services.xlsx_reader import MAX_ROWS, MAX_UPLOAD_BYTES, SheetRow, read_rows
from fixtures import karmana_seed
from fixtures.karmana_seed import (
    KARMANA_CATEGORY_NAMES,
    KARMANA_OPERATING_SINCE,
    KARMANA_STALL_COUNT,
    KARMANA_VENDOR_COUNT,
    KARMANA_ZONE_COUNT,
    KARMANA_ZONE_NAMES,
    STALL_COLUMN_ORDER,
    TRICKY_NUMERIC_CODE_INDEX,
    VENDOR_COLUMN_ORDER,
    blank_stall_rows,
    build_stalls_workbook,
    build_vendors_workbook,
    clean_stall_rows,
    clean_vendor_rows,
    expected_stall_issues,
    expected_vendor_issues,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

STALL_COLUMNS = len(STALL_COLUMN_ORDER)
VENDOR_COLUMNS = len(VENDOR_COLUMN_ORDER)

SMALL = 60
"""Kichik miqyos — darvoza MEXANIKASI 600 qator qurmasdan o'lchanadi.

`_stall_plan()` ning kiritish pozitsiyalari 36 gacha, ya'ni 60 qator
barcha nuqsonlarni ham, ikkala bo'sh qatorni ham (`min(300, count)`)
o'z ichiga oladi. TO'LIQ miqyos ALOHIDA, oxirgi testda bir marta
quriladi — har testda 600 qator qurish birlik to'plamini sekinlashtirardi
va u 11 soniyalik byudjetdan chiqib ketardi (02-VALIDATION «Sampling
Rate»).
"""


def _names(values: tuple[str, ...]) -> dict[str, UUID]:
    """`{nom: UUID}` lug'ati — `import_validator` kutadigan shakl."""
    return {name: uuid4() for name in values}


def _issue_map(issues: Sequence[ImportIssue]) -> dict[int, str]:
    """`ImportIssue` ro'yxatini `{qator: kod}` xaritasiga aylantiradi.

    Bir qatorda IKKI xato bo'lsa darhol yiqiladi: `{qator: kod}` shakli
    o'shanda bir qiymatli bo'lmasdi va «ikki tomonlama tenglik» da'vosi
    jimgina kuchsizlanardi.
    """
    mapped: dict[int, str] = {}
    for issue in issues:
        assert issue.row not in mapped, (
            f"{issue.row}-qatorda ikkita xato: {mapped[issue.row]} va {issue.code}"
        )
        mapped[issue.row] = issue.code
    return mapped


def _stall_sheet(
    *,
    dirty: bool,
    count: int = SMALL,
    column_order: str = "documented",
) -> list[SheetRow]:
    payload = build_stalls_workbook(
        KARMANA_ZONE_NAMES,
        KARMANA_CATEGORY_NAMES,
        count,
        dirty=dirty,
        column_order=column_order,
    )
    return read_rows(payload, expected_columns=STALL_COLUMNS)


def _validate_stalls(rows: Sequence[SheetRow]) -> tuple[list[StallImportRow], list[ImportIssue]]:
    return validate_stall_rows(
        rows,
        zones=_names(KARMANA_ZONE_NAMES),
        categories=_names(KARMANA_CATEGORY_NAMES),
        existing_codes=(),
    )


def _vendor_sheet(
    *,
    dirty: bool,
    count: int = SMALL,
) -> tuple[list[SheetRow], dict[str, UUID]]:
    codes = tuple(row.code for row in clean_stall_rows(count=KARMANA_STALL_COUNT))
    payload = build_vendors_workbook(codes, count, dirty=dirty)
    stalls_by_code = {code: uuid4() for code in codes}
    return read_rows(payload, expected_columns=VENDOR_COLUMNS), stalls_by_code


def _validate_vendors(
    rows: Sequence[SheetRow],
    stalls_by_code: dict[str, UUID],
) -> tuple[list[VendorImportRow], list[ImportIssue]]:
    return validate_vendor_rows(
        rows,
        stalls_by_code=stalls_by_code,
        existing_phones=(),
        default_from=KARMANA_OPERATING_SINCE,
    )


# ===========================================================================
# Mustaqillik darvozasi (T-02-165)
# ===========================================================================


def test_generator_does_not_import_the_template_module() -> None:
    """Generator ishlab chiqarish shabloni yo'lidan BUTUNLAY mustaqil.

    ⚠ BU TESTNI «soddalashtirish» UCHUN O'CHIRMANG. U yo'q bo'lsa keyingi
    maintainer `build_template()` ni chaqirib faylni qisqartiradi va
    o'lchov yana o'z-o'ziga qaytadi — 02-VERIFICATION.md ning tanqidi esa
    kuchida qoladi, garchi test to'plami yashil bo'lsa ham.

    Manba `ast` bilan o'qiladi: docstringda `xlsx_template` NOMI ATAYIN
    uchraydi (u yerda taqiqning SABABI yozilgan), ya'ni oddiy `grep`
    darvozani o'z-o'ziga qarshi qo'yardi.

    =======================================================================
    ⚠ DARVOZA 08-01 DA TORAYTIRILDI — «hech qanday `app.*`» O'RNIGA
      «AYNAN IKKI SIMVOL». Sabab va chegara ochiq yozilgan:

      `freeze_zip` naqshi SHU FAYLDA tug'ilgan edi, ya'ni determinizm
      faqat test fiksturasida bor, MAHSULOT eksporti esa (`build_template`,
      `build_error_report`) nodeterminik edi. 08-01 uni mahsulotga
      ko'chirdi — va o'shanda fikstur uni MAHSULOTDAN olishi kerak bo'ldi.
      Ikkinchi nusxa saqlash tanlovi bor edi va u RAD ETILDI: ikki nusxa
      sana konstantalari bir kun ajralib ketardi.

      Darvozaning MA'NOSI o'zgarmadi. U «yuk quvurning O'ZIDAN kelmasin»
      deydi — ya'ni ustun tartibi, sarlavha matni va namunaviy qator
      shablondan OLINMASIN. `freeze_zip`/`new_workbook` esa YUK EMAS:
      ular ZIP metama'lumotini va hujjat sanasini muzlatadi, faylning
      MAZMUNIGA bitta bayt ham qo'shmaydi.

      Darvoza ikki tomondan KUCHAYTIRILDI ham:
        1. Ruxsat SIMVOL darajasida (modul emas) — `build_template` ni
           `xlsx_export` orqali olib kelishning yo'li yo'q.
        2. YANGI, ilgari umuman bo'lmagan da'vo: `xlsx_export` ning O'ZI
           `xlsx_template` ni import qilmasligi. Usiz ruxsat TRANZITIV
           orqa eshik bo'lardi — fikstur shablon modulini bilvosita
           yuklab olardi va `ast` skaneri buni KO'RMASDI.
    =======================================================================
    """
    source = Path(karmana_seed.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    plain: list[str] = []
    from_imports: list[tuple[str, str]] = []
    documentation: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            plain.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            from_imports.extend((node.module, alias.name) for alias in node.names)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # Yolg'iz satr-ifoda = docstring (modul, sinf, funksiya yoki
            # e'londan keyingi atribut izohi). Ular darvozadan CHIQARILADI:
            # taqiqning SABABI aynan shu joylarda yozilgan va ularni
            # tekshirish darvozani o'z-o'ziga qarshi qo'yardi.
            documentation.add(id(node.value))

    modules = [*plain, *(module for module, _ in from_imports)]
    template_imports = [name for name in modules if "xlsx_template" in name]
    assert template_imports == [], f"shablon moduli import qilingan: {template_imports}"

    # `import app.services.xlsx_template` shaklidagi YALANG'OCH import —
    # TAQIQ. U butun paket yuzasini ochardi va simvol ro'yxati ma'nosiz
    # bo'lardi (`app.services.xlsx_template.build_template` bir nuqta
    # narigi tomonda turardi).
    plain_app = [name for name in plain if name == "app" or name.startswith("app.")]
    assert plain_app == [], f"yalang'och paket importi: {plain_app}"

    app_symbols = sorted(
        f"{module}.{name}"
        for module, name in from_imports
        if module == "app" or module.startswith("app.")
    )
    assert app_symbols == [
        "app.services.xlsx_export.freeze_zip",
        "app.services.xlsx_export.new_workbook",
    ], (
        f"generator ishlab chiqarish paketiga bog'landi: {app_symbols} — "
        "yuk quvurning O'ZIDAN kelsa miqyos o'lchovi hech nimani isbotlamaydi"
    )

    # TRANZITIV da'vo — yuqoridagi ruxsatning narxi shu tekshiruv bilan
    # to'lanadi.
    export_tree = ast.parse(Path(xlsx_export.__file__).read_text(encoding="utf-8"))
    export_modules: list[str] = []
    for node in ast.walk(export_tree):
        if isinstance(node, ast.Import):
            export_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            export_modules.append(node.module)

    leaked = [name for name in export_modules if "xlsx_template" in name]
    assert leaked == [], (
        f"`xlsx_export` shablon moduliga bog'landi: {leaked} — fikstur uni "
        "TRANZITIV yuklab olardi va yuqoridagi ro'yxat buni ko'rmasdi"
    )

    # KOD ichidagi satr literallari — ya'ni haqiqatan chaqiriladigan URL.
    endpoint_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in documentation
        and "imports/" in node.value
    ]
    assert endpoint_literals == [], (
        f"generator import endpointini chaqiryapti: {endpoint_literals} — T-02-165 buzilgan"
    )


def test_scale_constants_carry_the_karmana_range() -> None:
    """Miqyos ROADMAP ning `~300–1000 rasta` oralig'i ichida va E'LON QILINGAN."""
    assert KARMANA_ZONE_COUNT == 8
    assert KARMANA_STALL_COUNT == 600
    assert KARMANA_VENDOR_COUNT == 480
    assert 300 <= KARMANA_STALL_COUNT <= 1000
    assert len(KARMANA_ZONE_NAMES) == KARMANA_ZONE_COUNT
    assert KARMANA_VENDOR_COUNT < KARMANA_STALL_COUNT, (
        "biriktirilmagan rasta D-11 bo'yicha NORMAL holat va u datasetda bo'lishi shart"
    )


# ===========================================================================
# Rasta fayli
# ===========================================================================


def test_stall_workbook_carries_the_documented_column_count() -> None:
    """Har qator README §3 dagi BESH ustunni beradi (kod, zona, toifa, holat, izoh)."""
    rows = _stall_sheet(dirty=True)

    assert rows, "generator bo'sh fayl qurdi"
    for row in rows:
        assert len(row.values) == STALL_COLUMNS, row


def test_dirty_stall_file_contains_every_declared_issue_row() -> None:
    """E'lon qilingan har bir xato qatori faylda HAQIQATAN mavjud.

    Bu tenglik testidan OLDIN keladi va u alohida: xato qatori faylga
    umuman yozilmagan bo'lsa, quyidagi tenglik «ikkalasi ham bo'sh»
    holatida ham yashil bo'lishi mumkin edi.
    """
    present = {row.row for row in _stall_sheet(dirty=True)}

    missing = sorted(set(expected_stall_issues(SMALL)) - present)
    assert missing == [], f"e'lon qilingan xato qatorlari faylda yo'q: {missing}"


def test_clean_stall_file_passes_validation_completely() -> None:
    """Tozalangan fayl BIRORTA xatosiz o'tadi va hamma qator qabul qilinadi.

    Toza variant iflosning FILTRLANGAN ko'rinishi, ya'ni bu test aynan
    «tuzatilgan faylni qayta yuklash ishlaydi» degan mahsulot va'dasini
    o'lchaydi (README §6).
    """
    accepted, issues = _validate_stalls(_stall_sheet(dirty=False))

    assert issues == [], f"toza faylda xato chiqdi: {_issue_map(issues)}"
    assert len(accepted) == SMALL


def test_dirty_stall_issues_match_the_declaration_exactly() -> None:
    """`{qator: kod}` to'plami generator E'LONI bilan AYNAN teng (ikki tomonlama).

    Kutilmagan xato ham nomuvofiqlik: «iflos fayl 422 beradi» degan
    da'vo quvur BOSHQA sababdan rad etganda ham to'g'ri bo'lardi, va
    o'shanda tricky (xato BERMASLIGI kerak) qatorlarning birortasi
    jimgina buzilgan bo'lishi mumkin edi.
    """
    _accepted, issues = _validate_stalls(_stall_sheet(dirty=True))

    assert _issue_map(issues) == expected_stall_issues(SMALL)


def test_blank_rows_are_dropped_without_shifting_the_row_numbers() -> None:
    """Bo'sh qatorlar tashlanadi, LEKIN keyingi qatorlarning raqami SURILMAYDI.

    Admin xatoni EXCELDA tuzatadi: «88-qator» xabari uning ekranidagi
    88-qatorga to'g'ri kelishi shart (D-14). Raqam bir-ikkiga surilsa
    admin butunlay boshqa qatorni tuzatishga urinardi.
    """
    numbers = [row.row for row in _stall_sheet(dirty=True)]

    assert numbers == sorted(numbers)
    gaps = set(range(2, numbers[-1] + 1)) - set(numbers)
    assert gaps == blank_stall_rows(SMALL), (
        f"tashlangan qatorlar {sorted(gaps)}, e'lon qilingani {sorted(blank_stall_rows(SMALL))}"
    )


def test_numeric_code_cell_becomes_a_plain_integer_string() -> None:
    """SON sifatida yozilgan rasta kodi `"15"` bo'ladi, `"15.0"` EMAS.

    Excel raqamli katakni son TIPIDA saqlaydi. Normallashtirishsiz kod
    bazadagi `"15"` bilan MOS TUSHMASDI va D-15 idempotentligi buzilardi:
    har qayta import YANGI rasta yaratardi.
    """
    tricky = clean_stall_rows(count=SMALL)[TRICKY_NUMERIC_CODE_INDEX]
    matched = [row for row in _stall_sheet(dirty=True) if row.values[0] == tricky.code]

    assert len(matched) == 1, f"{tricky.code} kodli qator topilmadi yoki takrorlandi"
    assert "." not in str(matched[0].values[0])


def test_shuffled_columns_are_rejected_and_nothing_is_accepted() -> None:
    """Ustunlari surilgan fayl JIMGINA noto'g'ri yozilmaydi — u RAD ETILADI.

    README §3 ning va'dasi aynan shu: parser POZITSIYA bo'yicha o'qiydi,
    ya'ni ustunlarni almashtirgan admin buzilgan ma'lumot emas, XATO
    xabarini oladi.
    """
    accepted, issues = _validate_stalls(_stall_sheet(dirty=False, column_order="shuffled"))

    assert accepted == []
    assert issues, "surilgan ustunli fayl qabul qilindi — README §3 ning va'dasi buzilgan"


def test_unknown_column_order_is_rejected() -> None:
    """Noma'lum tartib nomi JIMGINA hujjatlashtirilgan tartibga tushmaydi."""
    with pytest.raises(ValueError, match="noma'lum ustun tartibi"):
        build_stalls_workbook(count=SMALL, dirty=False, column_order="random")


# ===========================================================================
# Sotuvchi fayli
# ===========================================================================


def test_clean_vendor_file_normalises_three_phone_shapes_to_one_e164() -> None:
    """Telefonning uch shakli AYNAN bitta E.164 ga tushadi (MARKET-04).

    ⚠ Shakllardan biri `+998 90 995 …` — `+` bilan boshlanadi. 02-24
    aynan shu chegarada defekt topgan edi (shablonning namunaviy telefoni
    formula-qochirishga tushib, O'Z importidan o'ta olmagan). Bu yerda
    qiymat qochirilmasdan yoziladi, ya'ni chegara haqiqatan bosiladi.
    """
    rows, stalls_by_code = _vendor_sheet(dirty=False)
    accepted, issues = _validate_vendors(rows, stalls_by_code)

    assert issues == [], f"toza sotuvchi faylida xato chiqdi: {_issue_map(issues)}"
    assert len(accepted) == SMALL

    declared = clean_vendor_rows(tuple(stalls_by_code), SMALL)
    assert [row.phone for row in accepted] == [row.phone for row in declared]
    assert all(row.phone.startswith("+998") for row in accepted)
    assert len({row.phone for row in accepted}) == SMALL


def test_clean_vendor_file_keeps_stall_free_rows_and_default_dates() -> None:
    """Rastasiz sotuvchi XATO EMAS (D-11); bo'sh sana `operating_since` ga tushadi."""
    rows, stalls_by_code = _vendor_sheet(dirty=False)
    accepted, _issues = _validate_vendors(rows, stalls_by_code)
    declared = clean_vendor_rows(tuple(stalls_by_code), SMALL)

    without_stall = [row for row in accepted if row.stall_id is None]
    assert without_stall, "datasetda rastasiz sotuvchi yo'q — D-11 holati sinalmasdi"
    assert len(without_stall) == sum(1 for row in declared if row.stall_code is None)

    defaulted = [
        row for row, spec in zip(accepted, declared, strict=True) if spec.from_date is None
    ]
    assert defaulted, "bo'sh sanali qator yo'q — README §3 ning standarti sinalmasdi"
    assert all(row.from_date == KARMANA_OPERATING_SINCE for row in defaulted)

    explicit = [(row, spec) for row, spec in zip(accepted, declared, strict=True) if spec.from_date]
    assert len(explicit) >= 3, "uchala sana shakli ham datasetda bo'lishi kerak"
    for row, spec in explicit:
        assert row.from_date == spec.from_date


def test_dirty_vendor_issues_match_the_declaration_exactly() -> None:
    """Sotuvchi faylining `{qator: kod}` to'plami E'LON bilan AYNAN teng."""
    rows, stalls_by_code = _vendor_sheet(dirty=True)
    _accepted, issues = _validate_vendors(rows, stalls_by_code)

    assert _issue_map(issues) == expected_vendor_issues(SMALL)


# ===========================================================================
# Determinizm va to'liq miqyos
# ===========================================================================


def test_two_builds_with_the_same_seed_are_byte_identical() -> None:
    """AYNI urug' -> AYNI baytlar (rasta ham, sotuvchi ham).

    Determinizmsiz generator «gohida yiqiladigan» testni tug'diradi va u
    eng yomon test turi: qizarish sababini qayta tiklab bo'lmaydi, ya'ni
    darvoza asta-sekin ishonchdan chiqadi (T-02-172).

    ⚠ Bu da'vo `XlsxWriter` ning ZIP sanasini SOAT'dan olishiga qarshi
    ataylab qurilgan (`_freeze_zip`). Muzlatish olib tashlansa test
    sekundlar chegarasida GOHIDA qizarardi — shuning uchun u yerda
    tuzatish emas, MUZLATISH turibdi.
    """
    codes = tuple(row.code for row in clean_stall_rows(count=SMALL))

    assert build_stalls_workbook(count=SMALL, dirty=True) == build_stalls_workbook(
        count=SMALL, dirty=True
    )
    assert build_vendors_workbook(codes, SMALL, dirty=True) == build_vendors_workbook(
        codes, SMALL, dirty=True
    )


def test_full_scale_files_stay_inside_the_reader_limits() -> None:
    """TO'LIQ miqyos (600/480) bir marta quriladi va chegaralarga urilmaydi.

    `xlsx_reader` chegaralari muhitdan sozlanadi, lekin STANDART qiymatlar
    shu yerda o'lchanadi: fayl ularning ichida ekani TAXMIN qilinmaydi
    (README §4 «chegaralardan besh barobar uzoq» degan taxminni aynan shu
    test haqiqatga aylantiradi).
    """
    stalls = build_stalls_workbook(dirty=True)
    codes = tuple(row.code for row in clean_stall_rows())
    vendors = build_vendors_workbook(codes, dirty=True)

    stall_rows = read_rows(stalls, expected_columns=STALL_COLUMNS)
    vendor_rows = read_rows(vendors, expected_columns=VENDOR_COLUMNS)

    assert len(stall_rows) == KARMANA_STALL_COUNT + len(expected_stall_issues())
    assert len(vendor_rows) == KARMANA_VENDOR_COUNT + len(expected_vendor_issues())
    assert len(stall_rows) < MAX_ROWS
    assert len(stalls) < MAX_UPLOAD_BYTES
    assert len(vendors) < MAX_UPLOAD_BYTES
