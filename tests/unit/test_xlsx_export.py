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

import ast
import io
import time
import zipfile
from pathlib import Path

import openpyxl
import pytest
from app.services import xlsx_export
from app.services.xlsx_export import (
    FORMULA_PREFIXES,
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
from app.services.xlsx_reader import read_rows

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


def members(raw: bytes) -> list[tuple[str, int, int]]:
    """A'zolarning `xlsx_reader._check_zip()` KO'RADIGAN xossalari.

    Sana ATAYIN ro'yxatda yo'q — muzlatish aynan uni o'zgartiradi.
    Qolgan uchtasi esa o'zgarmasligi SHART: o'qish darvozasi a'zolar
    SONI va e'lon qilingan OCHILGAN hajmlar yig'indisi bo'yicha qaror
    qiladi.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return [(i.filename, i.compress_type, i.file_size) for i in archive.infolist()]


def test_two_builds_of_the_same_data_are_byte_identical() -> None:
    """1-O'LCHOV — AYNI ma'lumot -> AYNI baytlar.

    Bu butun modulning MAVJUD BO'LISH SABABI: imzoli solishtiruv
    eksporti (08-16) faylning xeshini da'vo qiladi, ya'ni soatga bog'liq
    bayt farqi o'sha da'voni ma'nosiz qilardi.

    ⚠ `sleep(1.1)` MAJBURIY. `zipfile` a'zo sanasini SOAT'dan oladi va
    DOS sana maydonining aniqligi 2 sekund. Ikki chaqiruv ayni sekundda
    tugasa test MUZLATISHSIZ HAM yashil bo'lardi — ya'ni u aynan
    o'lchamoqchi bo'lgan nosozlikni (T-02-172) KO'RMASDI va darvoza
    bo'sh qolardi.

    ⛔ SABOTAJ O'LCHANDI VA U REJANING DA'VOSINI RAD ETDI:
      1. `new_workbook()` dan `set_properties({"created": ...})` olindi
         -> QIZARDI, baytlar 3942-indeksda ajraldi.
      2. Qaytarildi; `finish()` dan `freeze_zip` olindi
         -> **QIZARMADI.** Butun fayl (14 test) YASHIL qoldi.

    Sabab o'lchandi (`freeze_zip` docstringi): `XlsxWriter` 3.2.9 ZIP
    a'zo sanasini O'ZI `(1980, 1, 1, 0, 0, 0)` qilib yozadi, ya'ni soat
    faylga FAQAT `docProps/core.xml` orqali kiradi. Reja «ikki mustaqil
    qatlam» deb taxmin qilgan edi; aslida determinizm qatlami BITTA.

    ⚠ Shuning uchun bu test `freeze_zip` ni O'LCHAMAYDI — uni
    `test_freeze_zip_normalises_clock_dated_members` shartnoma
    darajasida o'lchaydi. Ikkalasini bitta testga qo'shish aynan
    yuqoridagi yolg'on xotirjamlikni qaytarardi.
    """
    rows = (("Rasta 1", 150_000, "izoh"), ("Rasta 2", None, None))

    first = build(rows)
    time.sleep(1.1)
    second = build(rows)

    assert first == second


def test_frozen_zip_time_is_the_dos_epoch_start() -> None:
    """Chiqqan faylda a'zo sanasi AYNAN `FROZEN_ZIP_TIME`.

    ⚠ BU TEST YOLG'IZ O'ZI `freeze_zip` NI O'LCHAMAYDI: `XlsxWriter`
    3.2.9 a'zo sanasini o'zi ham shu qiymatga qo'yadi, ya'ni
    `freeze_zip` olib tashlansa u YASHIL QOLADI (o'lchandi). U
    faylning KUTILGAN holatini qulflaydi; funksiyaning O'Z hissasi
    quyidagi shartnoma testida o'lchanadi.
    """
    raw = build((("Rasta 1", 1, None),))

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        dates = {info.date_time for info in archive.infolist()}

    assert dates == {FROZEN_ZIP_TIME}


def test_freeze_zip_normalises_clock_dated_members() -> None:
    """`freeze_zip` ning O'Z SHARTNOMASI — soatli arxiv ustida o'lchanadi.

    Kirish ATAYIN `XlsxWriter` dan olinmaydi: u a'zo sanasini allaqachon
    muzlatib beradi va o'shanda bu test funksiyani emas, KUTUBXONANI
    sinardi (aynan shu yolg'on xotirjamlik 08-01 sabotajida fosh
    bo'lgan). Shuning uchun arxiv `zipfile` bilan, SOAT sanasi bilan
    quriladi.

    Shartnoma: sana muzlatiladi, qolgan hamma narsa — nom, siqish turi
    va OCHILGAN hajm — o'zgarmaydi.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        # Nom bilan yozish = sana SOAT'dan olinadi.
        archive.writestr("xl/worksheets/sheet1.xml", b"<x/>" * 100)
        archive.writestr("docProps/core.xml", b"<c/>" * 100)

    clock_dated = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(clock_dated)) as archive:
        before = {info.date_time for info in archive.infolist()}

    assert before != {FROZEN_ZIP_TIME}, "kirish arxivi allaqachon muzlatilgan"

    frozen = freeze_zip(clock_dated)

    with zipfile.ZipFile(io.BytesIO(frozen)) as archive:
        assert {info.date_time for info in archive.infolist()} == {FROZEN_ZIP_TIME}
    assert members(frozen) == members(clock_dated)


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

    assert members(frozen) == members(original)


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


@pytest.mark.parametrize(
    "payload",
    [
        "=cmd|' /c calc'!A1",
        "+1",
        "-1",
        "@SUM(1)",
        "\t=1+1",
        "\r=1+1",
    ],
    ids=["equals", "plus", "minus", "at", "tab", "carriage-return"],
)
def test_formula_injection_is_escaped_for_every_prefix(payload: str) -> None:
    """2-O'LCHOV — OLTALA xavfli prefiks `'` bilan zararsizlantiriladi.

    Hujum MIJOZ MASHINASIDA bajariladi — qarzdorlik reestrida
    `vendor_name` bor, ya'ni `=HYPERLINK(...)` nomli sotuvchi
    DIREKTORNING Excelida kod bajartirardi. Bu saqlangan hujum: nomni
    bir marta yozgan odam keyinchalik boshqa odamning mashinasida kod
    ishga tushiradi.

    ⚠ Qiymat FAYLDAN QAYTA O'QILADI (`openpyxl`), fayl BAYTLARIDAN
    `in` bilan izlanmaydi: `.xlsx` — siqilgan ZIP va matn u yerda
    umuman topilmasdi, ya'ni "baytda yo'q" degan da'vo HAR DOIM yashil
    bo'lardi va hech nimani o'lchamasdi.

    `\\t` va `\\r` ALOHIDA holat: ular ko'rinmaydi, lekin Excel ularni
    tashlab yuborib KEYINGI belgiga qaraydi — oddiy `startswith("=")`
    ularni O'TKAZIB YUBORARDI.
    """
    book = open_book(build(((payload, 1, None),)))
    stored = str(book[SHEET].cell(row=1, column=1).value)

    # XAVFSIZLIK DA'VOSI — faylning O'ZIDA.
    assert stored.startswith("'"), f"qochirilmagan qiymat: {stored!r}"
    assert not stored.startswith(FORMULA_PREFIXES)

    # MAZMUN DA'VOSI — faqat KO'RINADIGAN prefikslar uchun. `\t`/`\r`
    # OOXML da `_x0009_`/`_x000D_` bo'lib kodlanadi, ya'ni aynan tenglik
    # ularda kutubxona konvensiyasini sinardi, bizning kodni emas.
    if payload.isprintable():
        assert stored == "'" + payload


def test_write_money_writes_an_integer_in_the_money_format() -> None:
    """4-O'LCHOV — pul SON bo'lib yoziladi va `#,##0` formatini oladi.

    Matn bo'lib yozilgan pul Excelda YIG'ILMASDI va saralash "100" ni
    "20" dan oldin qo'yardi — qarzdorlik reestrida bu ikkalasi ham
    hisobotni foydasiz qilardi.

    ⚠ `float` HOLATI TEST EMAS, IZOH: `write_money` ning annotatsiyasi
    `int` va `float` uzatilganda `mypy` xato beradi. Ish vaqtida
    tekshirilmaydi — pul `BIGINT` so'm sifatida saqlanadi va `float`
    loyiha darajasida taqiqlangan (yaxlitlash drifti kunlik patta
    yig'indisida sotuvchi bilan nizoga aylanardi).
    """
    book = open_book(build((("Rasta 1", 150_000, None),)))
    cell = book[SHEET].cell(row=1, column=2)

    assert cell.value == 150_000
    assert cell.number_format == MONEY_NUM_FORMAT


def test_raw_worksheet_writes_live_only_inside_write_text() -> None:
    """YOZISH INTIZOMI — `ast` bilan, `grep` bilan EMAS.

    ⚠ NEGA `grep` EMAS: reja qabul mezoni
    `grep -c 'worksheet.write(' ... -> 0` deb yozgan edi, lekin AYNI
    reja modul docstringiga `worksheet.write()` NI LITERAL YOZISHNI ham
    buyuradi (2-fakt: "to'g'ridan-to'g'ri chaqirilmaydi"). O'lchandi:
    naiv `grep` **2** qaytaradi va ikkalasi ham DOKUMENTATSIYA. Ya'ni
    darvoza o'z-o'ziga qarshi turardi va uni yashil qilishning yagona
    yo'li taqiqning SABABINI o'chirish bo'lardi — 02-23 aynan shu
    to'qnashuvni `ast` foydasiga hal qilgan.

    `ast` esa HAQIQIY da'voni o'lchaydi: `worksheet.write*` chaqiruvi
    faqat `write_text`/`write_money`/`write_optional_text` ichida
    bo'lishi va `write()` ning O'ZI umuman chaqirilmasligi.
    """
    tree = ast.parse(Path(xlsx_export.__file__).read_text(encoding="utf-8"))

    calls: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and isinstance(inner.func.value, ast.Name)
                and inner.func.value.id == "worksheet"
            ):
                calls.setdefault(node.name, []).append(inner.func.attr)

    # `write()` — Excel turini O'ZI taxmin qiladigan yagona metod: u
    # `"123"` ni songa, `"=1+1"` ni esa FORMULAGA aylantirardi, ya'ni
    # qochirishdan KEYIN ham hujumni tiklardi.
    every = [attr for attrs in calls.values() for attr in attrs]
    assert "write" not in every, f"turini taxmin qiladigan write() chaqirilgan: {calls}"

    assert calls == {
        "write_text": ["write_string"],
        "write_money": ["write_number"],
        "write_optional_text": ["write_blank"],
    }, f"xom yozish yo'li ochilgan: {calls}"


def test_write_optional_text_leaves_an_empty_cell_for_none() -> None:
    """3-O'LCHOV — O'LCHANMAGAN qiymat BO'SH katak.

    ⛔ `0` ham, `""` ham, `"—"` ham EMAS va uchalasi ALOHIDA rad
    etiladi. D-10 ning sababi: o'lchanmagan nol O'LCHANGAN noldan farq
    qilmasdi va direktor hisobotdagi nolni «to'lov yig'ilmagan» deb
    o'qirdi — ya'ni mahsulotning butun da'vosi (raqam bilan fosh qilish)
    o'z ustidan kulardi.
    """
    sheet = open_book(build((("Rasta 1", None, None),)))[SHEET]

    for column in (2, 3):
        stored = sheet.cell(row=1, column=column).value
        assert stored is None, f"{column}-ustunda o'rin to'ldiruvchi: {stored!r}"
        assert stored != 0
        assert stored != ""
        assert stored != "—"


def test_frozen_bytes_still_pass_the_product_reader() -> None:
    """5-O'LCHOV — muzlatilgan fayl `xlsx_reader` darvozalaridan O'TADI.

    `freeze_zip` arxivni QAYTA O'RAYDI, ya'ni u o'qish tomonini
    buzishi MUMKIN bo'lgan yagona qadam. `_check_zip()` a'zolar SONI va
    e'lon qilingan OCHILGAN hajmlar yig'indisi bo'yicha qaror qiladi —
    ikkalasi ham qayta o'rashdan omon chiqishi SHART.

    O'lchov mahsulot o'quvchisining O'ZI bilan olinadi: `zipfile` bilan
    qo'lda tekshirish o'qish darvozalarining haqiqiy ketma-ketligini
    (hajm -> ZIP -> parse -> varaq/qator/ustun) chetlab o'tardi.
    """
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    worksheet = workbook.add_worksheet(SHEET)
    # 1-qator SARLAVHA (o'quvchi uni tashlaydi), 2-qator MA'LUMOT.
    write_text(worksheet, 0, 0, "kod")
    write_text(worksheet, 0, 1, "zona")
    write_text(worksheet, 1, 0, "12")
    write_text(worksheet, 1, 1, "Markaziy")

    rows = read_rows(finish(workbook, buffer), expected_columns=2)

    assert [row.values for row in rows] == [("12", "Markaziy")]
