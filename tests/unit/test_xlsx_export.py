"""`.xlsx` eksport poydevori — determinizm va yozish intizomi (RECON-04).

Bu modul `app.services.xlsx_export` ning OLTITA xulqini o'lchaydi. Har
o'lchov HOSIL BO'LGAN FAYLNI qayta o'qiydi, chaqiruvni mock bilan
tekshirmaydi: "funksiya chaqirildi" degan da'vo ikkinchi yozish yo'li
ochilganda ham yashil qolardi (`test_xlsx_template.py` modul docstringi
bilan bir xil sabab).

⚠ NEGA DETERMINIZM DARVOZA: `XlsxWriter` `in_memory` rejimida
`ZipFile.writestr(nom, ...)` ni chaqiradi, `zipfile` esa bunday
chaqiruvda a'zo sanasini SOAT'dan oladi. Ya'ni ikki qo'shni chaqiruv
baytlari sekund chegarasida farq qilardi va bunga tayangan har qanday
da'vo «gohida yiqiladigan» testga aylanardi (T-02-172). Muzlatish IKKI
QATLAMDA: `docProps/core.xml` sanasi (`FROZEN_CREATED`) va ZIP a'zo
sanasi (`freeze_zip`).
"""

from __future__ import annotations

import io
import zipfile

import openpyxl
from app.services.xlsx_export import (
    FROZEN_ZIP_TIME,
    MONEY_NUM_FORMAT,
    finish,
    freeze_zip,
    money_format,
    new_workbook,
    write_money,
    write_optional_text,
    write_text,
)

SHEET = "Varaq"


def build(rows: tuple[tuple[str, int | None, str | None], ...]) -> bytes:
    """Namunaviy kitob — YAGONA yozish yuzasi orqali.

    Uchala yordamchi ham shu yerda ishlatiladi, ya'ni har o'lchov aynan
    mahsulot iste'molchisi yuradigan yo'ldan yuradi.
    """
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    worksheet = workbook.add_worksheet(SHEET)
    money = money_format(workbook)

    for offset, (label, amount, note) in enumerate(rows):
        write_text(worksheet, offset, 0, label)
        if amount is None:
            write_optional_text(worksheet, offset, 1, None)
        else:
            write_money(worksheet, offset, 1, amount, money)
        write_optional_text(worksheet, offset, 2, note)

    return finish(workbook, buffer)


def open_book(raw: bytes) -> openpyxl.Workbook:
    return openpyxl.load_workbook(io.BytesIO(raw))


def test_two_builds_of_the_same_data_are_byte_identical() -> None:
    """AYNI ma'lumot -> AYNI baytlar.

    Bu butun modulning MAVJUD BO'LISH SABABI: imzoli sololishtiruv
    eksporti (08-16) faylning xeshini da'vo qiladi, ya'ni soatga bog'liq
    bayt farqi o'sha da'voni ma'nosiz qilardi.
    """
    rows = (("Rasta 1", 150_000, "izoh"), ("Rasta 2", None, None))

    assert build(rows) == build(rows)


def test_frozen_zip_time_is_the_dos_epoch_start() -> None:
    """A'zo sanasi SOAT'dan emas, konstantadan keladi."""
    raw = build((("Rasta 1", 1, None),))

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        dates = {info.date_time for info in archive.infolist()}

    assert dates == {FROZEN_ZIP_TIME}


def test_freeze_zip_preserves_names_compression_and_sizes() -> None:
    """Qayta o'rash MAZMUNGA tegmaydi.

    `xlsx_reader._check_zip()` a'zolar SONI va e'lon qilingan OCHILGAN
    hajmlar yig'indisi bo'yicha qaror qiladi. Muzlatish ularning
    birortasini o'zgartirsa, o'qish darvozalari boshqa faylni ko'rardi.
    """
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    worksheet = workbook.add_worksheet(SHEET)
    write_text(worksheet, 0, 0, "Rasta 1")
    workbook.close()
    original = buffer.getvalue()

    frozen = freeze_zip(original)

    with (
        zipfile.ZipFile(io.BytesIO(original)) as before,
        zipfile.ZipFile(io.BytesIO(frozen)) as after,
    ):
        assert [i.filename for i in before.infolist()] == [
            i.filename for i in after.infolist()
        ]
        assert [i.compress_type for i in before.infolist()] == [
            i.compress_type for i in after.infolist()
        ]
        assert [i.file_size for i in before.infolist()] == [
            i.file_size for i in after.infolist()
        ]


def test_core_properties_carry_the_frozen_creation_date() -> None:
    """`docProps/core.xml` sanasi SOAT'dan EMAS, `FROZEN_CREATED` dan.

    Bu ZIP muzlatishdan MUSTAQIL ikkinchi qatlam: a'zo sanasi
    muzlatilgan bo'lsa ham, hujjat xossasidagi `dcterms:created` siqilgan
    MAZMUN ichida yotadi va u har chaqiruvda o'zgarardi.
    """
    raw = build((("Rasta 1", 1, None),))

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        core = archive.read("docProps/core.xml").decode("utf-8")

    assert "2026-08-01" in core


def test_write_text_escapes_a_formula_payload() -> None:
    """`=cmd|' /c calc'!A1` faylga APOSTROF bilan tushadi.

    Hujum mijoz mashinasida bajariladi — qarzdorlik reestrida
    `vendor_name` bor, ya'ni `=HYPERLINK(...)` nomli sotuvchi
    direktorning Excelida kod bajartirardi.
    """
    payload = "=cmd|' /c calc'!A1"

    book = open_book(build(((payload, 1, None),)))
    stored = str(book[SHEET].cell(row=1, column=1).value)

    assert stored == "'" + payload


def test_write_money_writes_an_integer_in_the_money_format() -> None:
    """Pul SON bo'lib yoziladi va `#,##0` formatini oladi.

    Matn bo'lib yozilgan pul Excelda YIG'ILMASDI va saralash "100" ni
    "20" dan oldin qo'yardi.
    """
    book = open_book(build((("Rasta 1", 150_000, None),)))
    cell = book[SHEET].cell(row=1, column=2)

    assert cell.value == 150_000
    assert cell.number_format == MONEY_NUM_FORMAT


def test_write_optional_text_leaves_an_empty_cell_for_none() -> None:
    """O'LCHANMAGAN qiymat BO'SH katak — `0` ham, `""` ham, `"—"` ham EMAS.

    D-10: nol o'lchangan nol bilan bir xil ko'rinadi va direktor
    hisobotdagi nolni «to'lov yo'q» deb o'qirdi.
    """
    book = open_book(build((("Rasta 1", None, None),)))
    sheet = book[SHEET]

    assert sheet.cell(row=1, column=2).value is None
    assert sheet.cell(row=1, column=3).value is None
