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
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

import openpyxl
import pytest
from app.schemas import (
    AnomalyArchiveRowResponse,
    ReceivablesReportRow,
    RevenueReportRow,
)
from app.services import xlsx_export
from app.services.accuracy_report import AccuracyReport, ConfusionMatrix, ProportionInterval
from app.services.xlsx_export import (
    FORMULA_PREFIXES,
    FROZEN_ZIP_TIME,
    MONEY_NUM_FORMAT,
    PERCENT_NUM_FORMAT,
    ReportPeriod,
    build_accuracy_workbook,
    build_discrepancies_workbook,
    build_receivables_workbook,
    build_revenue_workbook,
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

    ⚠⚠ 08-12 DA RO'YXAT IKKI YOZUV BILAN O'SDI — VA U BO'SHASHMADI.

    To'rt hisobot quruvchisi (`build_*_workbook`) varaqqa xom
    `worksheet.*` bilan UMUMAN tegmaydi: ular faqat yordamchilardan
    o'tadi. Yangi ikki yordamchi shu ro'yxatga QO'SHILADI, ya'ni
    darvozaning shakli o'zgarmaydi — «kim varaqqa tegishi mumkin»
    savoli hamon YOPIQ to'plam bilan javob oladi. Agar quruvchining
    O'ZI ro'yxatda paydo bo'lsa, bu test qizaradi.

    ⚠⚠ 08-16 DA DARVOZA AYNAN SHUNI USHLADI — O'LCHANGAN, TAXMIN EMAS.

    Solishtiruv quruvchisi `ai_expected_soum is None` uchun varaqqa
    XOM `worksheet.write_blank(...)` bilan tegdi va test QIZARDI:

        AssertionError: xom yozish yo'li ochilgan:
        {..., 'build_three_way_workbook': ['write_blank']}

    ⛔ TO'G'RI JAVOB — RO'YXATGA QURUVCHINI QO'SHISH EMAS (bu darvozani
       bo'shatardi va keyingi ijrochiga «bu yerda xom yozsa ham
       bo'larkan» degan pretsedent berardi), balki YANGI NOMLANGAN
       yordamchi qo'shish: `write_optional_money`. U PUL uchun va u
       `write_optional_number` DAN AYRIM — o'shanining annotatsiyasi
       `float` va u O'Z docstringida «pul uchun emas» deb yozilgan.

    ⚠ QIYMATLAR `sorted(set(...))` BILAN SOLISHTIRILADI: `ast.walk`
      tugunlarni kenglik bo'yicha yuradi va bitta funksiya ichidagi
      IKKI xil chaqiruvning tartibi shart (`if`) shakliga bog'liq —
      ya'ni ro'yxat tartibiga bog'langan da'vo kodning MA'NOSINI emas,
      uning YOZILISH SHAKLINI qulflab qo'yardi.
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

    assert {name: sorted(set(attrs)) for name, attrs in calls.items()} == {
        "write_text": ["write_string"],
        "write_money": ["write_number"],
        "write_optional_text": ["write_blank"],
        "write_optional_money": ["write_blank"],
        "write_optional_number": ["write_blank", "write_number"],
        "layout_sheet": ["autofilter", "freeze_panes", "set_column"],
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


# ===========================================================================
# 08-12 — TO'RT HISOBOT QURUVCHISI
#
# ⛔ HAR O'LCHOV FAYLNI QAYTA O'QIYDI (`openpyxl`), chaqiruvni mock bilan
#    tekshirmaydi. «Quruvchi `write_text` ni chaqirdi» degan da'vo ikkinchi
#    yozish yo'li ochilganda ham yashil qolardi — yuqoridagi modul
#    docstringining aynan qoidasi.
# ===========================================================================

PERIOD = ReportPeriod(from_date=date(2026, 8, 1), to_date=date(2026, 8, 7))
PERIOD_LABEL = "2026-08-01 — 2026-08-07"
"""Davrning FAYL ICHIDAGI shakli — ⛔ EM TIRE (U+2014) BILAN.

`frontend/messages/*.json::reports.periodShown` AYNAN shu belgini
ishlatadi (`'{from} — {to}'`). Ekran bilan fayl bir xil davrni ikki xil
shaklda ko'rsatsa, «bu qaysi hisobot?» savoli chop etilgan varaqda
javobsiz qolardi (UI-SPEC §1.2 qoida 2).
"""

EVIL_NAME = '=HYPERLINK("http://evil","x")'
"""Sotuvchi ismi sifatida yozilgan formula — T-08-48 ning kirish holati."""

SNAPSHOT_ID = UUID("00000000-0000-4000-8000-0000000000ab")


def revenue_rows() -> tuple[RevenueReportRow, ...]:
    return (
        RevenueReportRow(
            business_date=date(2026, 8, 1),
            collected_soum=150_000,
            charged_soum=180_000,
            diff_soum=-30_000,
        ),
        RevenueReportRow(
            business_date=date(2026, 8, 2),
            collected_soum=210_000,
            charged_soum=180_000,
            diff_soum=30_000,
        ),
    )


def receivable_rows(*, vendor_name: str | None = EVIL_NAME) -> tuple[ReceivablesReportRow, ...]:
    return (
        ReceivablesReportRow(
            vendor_id=None,
            vendor_name=vendor_name,
            stall_codes=["A-1", "A-2"],
            outstanding_soum=540_000,
            oldest_debt_date=date(2026, 7, 19),
        ),
        ReceivablesReportRow(
            vendor_id=None,
            # ⛔ ISM TOPILMAGAN QATOR — BO'SH KATAK bo'lib chiqishi SHART
            #    (`schemas.ReceivablesReportRow` docstringi: na «—», na
            #    «Noma'lum», na «Sotuvchi #123»).
            vendor_name=None,
            stall_codes=[],
            outstanding_soum=120_000,
            oldest_debt_date=None,
        ),
    )


def archive_rows() -> tuple[AnomalyArchiveRowResponse, ...]:
    return (
        AnomalyArchiveRowResponse(
            business_date=date(2026, 8, 3),
            kind="occupied_unpaid",
            stall_code="A-1",
            snapshot_id=SNAPSHOT_ID,
            case_status="justified",
        ),
        AnomalyArchiveRowResponse(
            business_date=date(2026, 8, 4),
            kind="unassigned_occupied",
            stall_code="B-7",
            snapshot_id=None,
            case_status=None,
        ),
    )


def accuracy(*, measured: bool) -> AccuracyReport:
    """Aniqlik hisobotining ikki holati — ⛔ BIRORTA SANOQ NOL EMAS.

    Nol sanoq ATAYIN chetlab o'tiladi: `measured=False` o'lchovi «faylda
    `0` yozilmagan» degan BUTUN FAYL bo'yicha da'voni qo'yadi (reja Task
    1, (c)), va o'lchangan nol sanoq o'sha da'voni yolg'on-qizil
    qilardi. O'lchanayotgan narsa esa boshqa: O'LCHANMAGAN foizning
    o'rniga nol yozilmasligi (D-10).
    """
    if not measured:
        return AccuracyReport(
            drawn=7,
            answered=6,
            unanswered=1,
            dont_know=1,
            matrix=ConfusionMatrix(tp=2, fp=1, fn=1, tn=1),
            n=5,
            measured=False,
            base_rate=None,
            correct=ProportionInterval(None, None, None),
            false_occupied=ProportionInterval(None, None, None),
            false_empty=ProportionInterval(None, None, None),
        )
    return AccuracyReport(
        drawn=620,
        answered=612,
        unanswered=8,
        dont_know=4,
        matrix=ConfusionMatrix(tp=401, fp=23, fn=38, tn=150),
        n=612,
        measured=True,
        base_rate=0.7173202614379085,
        correct=ProportionInterval(0.9003267973856209, 0.8749, 0.9214),
        false_occupied=ProportionInterval(0.05424528301886792, 0.0364, 0.0798),
        false_empty=ProportionInterval(0.08656036446469248, 0.0637, 0.1165),
    )


def build_every(locale: str = "uz-Latn") -> dict[str, bytes]:
    """To'rtala hujjat — bitta chaqiruvda, AYNI kirish bilan."""
    return {
        "revenue": build_revenue_workbook(revenue_rows(), locale, PERIOD),
        "receivables": build_receivables_workbook(receivable_rows(), locale, PERIOD),
        "discrepancies": build_discrepancies_workbook(archive_rows(), locale, PERIOD),
        "accuracy": build_accuracy_workbook(accuracy(measured=True), locale, PERIOD),
    }


def first_sheet(raw: bytes) -> Any:
    return open_book(raw).worksheets[0]


def labelled_rows(raw: bytes) -> dict[str, tuple[Any, ...]]:
    """1-ustundagi MATN -> butun qator. Aniqlik varag'i shu bilan o'qiladi.

    ⚠ Qator INDEKSI bilan emas, YORLIQ bilan izlanadi: indeksga
    bog'langan test yangi ko'rsatkich qo'shilganda ma'nosiz joyda
    qizarardi va keyingi ijrochi uni «raqamni siljitib» tuzatardi.
    """
    found: dict[str, tuple[Any, ...]] = {}
    for row in first_sheet(raw).iter_rows(values_only=True):
        if row and isinstance(row[0], str):
            found[row[0]] = row
    return found


def test_every_report_workbook_is_byte_deterministic() -> None:
    """(a) To'rtala hujjat ham AYNI ma'lumotda AYNI baytlarni beradi.

    ⚠ `sleep(1.1)` YUQORIDAGI DETERMINIZM TESTIDAGI BILAN AYNI SABABDAN
      (DOS sana maydonining aniqligi 2 sekund). Bir marta uxlanadi va
      to'rtala hujjat ham shu oraliqning IKKI TOMONIDA quriladi — to'rt
      alohida uyqu testni sababsiz to'rt barobar sekinlashtirardi.

    08-16 imzoli solishtiruv eksporti faylning XESHINI da'vo qiladi,
    ya'ni bu yerdagi har bir bayt farqi o'sha da'voni ma'nosiz qilardi.
    """
    first = build_every()
    time.sleep(1.1)
    second = build_every()

    assert first == second


@pytest.mark.parametrize(
    "kind",
    ["revenue", "receivables", "discrepancies", "accuracy"],
)
def test_every_report_file_carries_the_period_in_its_first_row(kind: str) -> None:
    """Davr FAYL ICHIDA — chop etilgan varaq kontekstsiz tarqaydi.

    UI-SPEC §1.2 qoida 2: davr yo'qolgan varaqdagi raqam hech nimaga
    bog'lanmagan bo'lib qoladi va u imzolanadigan hujjat bo'lib
    tarqaladi. Sarlavha (`Content-Disposition`) yetarli EMAS: fayl
    nomi chop etilganda BOSILMAYDI.
    """
    banner = first_sheet(build_every()[kind]).cell(row=1, column=1).value

    assert isinstance(banner, str)
    assert PERIOD_LABEL in banner, banner


@pytest.mark.parametrize(
    "kind",
    ["revenue", "receivables", "discrepancies", "accuracy"],
)
def test_every_report_file_freezes_the_header_and_opens_a_filter(kind: str) -> None:
    """Sarlavha MUZLATILGAN va filtr OCHIQ — 30 000 qatorli hujjat sharti.

    ⛔ `freeze_panes` AYNAN `A3`: 1-qator DAVR, 2-qator SARLAVHA va
       IKKALASI ham skrollda ko'rinib turishi kerak. `A2` (reja aytgan
       `freeze_panes(1, 0)`) faqat davrni muzlatardi va sarlavha
       yo'qolgan zahoti direktor «qaysi ustun nima?» degan savolga
       javobsiz qolardi — `xlsx_export` modul docstringidagi
       `constant_memory` taqiqining aynan sababi.
    """
    sheet = first_sheet(build_every()[kind])

    assert sheet.freeze_panes == "A3", sheet.freeze_panes
    assert sheet.auto_filter.ref is not None


def test_the_vendor_name_formula_is_escaped_in_the_receivables_file() -> None:
    """(b) T-08-48 — `=HYPERLINK(...)` nomli sotuvchi FAYLDA apostrof bilan.

    Hujum SERVERDA emas, DIREKTORNING mashinasida portlaydi va u
    saqlangan hujum: nomni bir marta yozgan odam keyinchalik boshqa
    odamning Excelida kod bajartiradi (OWASP CSV/Formula Injection).

    ⚠ Qiymat FAYLDAN QAYTA O'QILADI — `write_text` chaqirilganini
      tekshirish ikkinchi yozish yo'li ochilganda yashil qolardi.
    """
    raw = build_receivables_workbook(receivable_rows(), "uz-Latn", PERIOD)
    stored = first_sheet(raw).cell(row=3, column=1).value

    assert isinstance(stored, str)
    assert stored.startswith("'"), f"qochirilmagan qiymat: {stored!r}"
    assert not stored.startswith(FORMULA_PREFIXES)
    assert stored == "'" + EVIL_NAME


def test_the_receivables_file_leaves_an_empty_cell_for_a_missing_name() -> None:
    """Ism TOPILMAGAN qator — BO'SH katak, o'rin to'ldiruvchi EMAS (D-08).

    `schemas.ReceivablesReportRow` docstringi buni literal aytadi: chop
    etilgan varaqdagi «Noma'lum» qatori buxgalter uchun HAQIQIY nom
    bo'lib o'qilardi.
    """
    sheet = first_sheet(build_receivables_workbook(receivable_rows(), "uz-Latn", PERIOD))
    stored = sheet.cell(row=4, column=1).value

    assert stored is None, f"o'rin to'ldiruvchi yozilgan: {stored!r}"


def test_the_receivables_debt_is_a_number_in_the_money_format() -> None:
    """Qarz SON bo'lib yoziladi — Excelda saralash va yig'indi ishlaydi.

    Matn bo'lib yozilgan qarz «100 000» ni «20 000» dan oldin qo'yardi va
    reestrning butun amaliy qiymati (kimdan ko'p undirish kerak) yo'qolardi.
    """
    cell = first_sheet(build_receivables_workbook(receivable_rows(), "uz-Latn", PERIOD)).cell(
        row=3, column=3
    )

    assert cell.value == 540_000
    assert cell.number_format == MONEY_NUM_FORMAT


def test_the_unmeasured_accuracy_file_leaves_the_percent_cells_empty() -> None:
    """(c) `measured is False` -> foiz kataklari BO'SH, ⛔ `0` EMAS (D-10).

    =======================================================================
    ⛔ NEGA BU ENG QIMMAT DA'VO.

    O'lchanmagan foizni `0` qilib yozish «tizim hech qachon xato
    qilmaydi» degan O'LCHANGAN da'voni chop etilgan varaqqa tushirardi —
    holbuki o'lchov UMUMAN bo'lmagan (`accuracy_report` moduli:
    T-05-04). Varaq esa imzolanadi va u kontekstsiz tarqaladi.
    =======================================================================

    ⛔ DA'VO BUTUN FAYL BO'YICHA: birorta katakda `0` bo'lmasligi. Shu
       sababdan fikstursdagi HAR sanoq noldan farqli (`accuracy()`
       docstringi) — aks holda «nol yo'q» da'vosi yolg'on-qizil bo'lardi.
    """
    raw = build_accuracy_workbook(accuracy(measured=False), "uz-Latn", PERIOD)
    texts = xlsx_export.report_texts("uz-Latn")
    rows = labelled_rows(raw)

    for key in (
        "accuracy_base_rate",
        "accuracy_correct",
        "accuracy_false_occupied",
        "accuracy_false_empty",
    ):
        row = rows[texts[key]]
        assert row[1:4] == (None, None, None), f"{key}: {row!r}"

    every = [
        value
        for line in first_sheet(raw).iter_rows(values_only=True)
        for value in line
        if value is not None
    ]
    assert 0 not in every, f"o'lchanmagan hisobotga nol yozilgan: {every}"


def test_the_measured_accuracy_file_keeps_the_two_error_kinds_apart() -> None:
    """Ikki xato turi IKKI ALOHIDA qatorda va ular QAYTA HISOBLANMAYDI (D-09).

    =======================================================================
    ⛔ «BAND DEB XATO» (`fp/(tp+fp)`) — NIZO xavfi, «BO'SH DEB XATO»
       (`fn/(tp+fn)`) — YIG'ILMAGAN PATTA. Ularning MAXRAJLARI ham
       boshqa (`accuracy_report` modul docstringi), ya'ni bitta
       «xatolik ulushi» ga qo'shish arifmetik jihatdan ham, ma'no
       jihatdan ham noto'g'ri bo'lardi.

    ⛔ QIYMATLAR `AccuracyReport` DAN KELADI: agar quruvchi ularni
       matritsadan QAYTA hisoblasa, bu test kutilgan sonni emas,
       quruvchining O'Z arifmetikasini ko'rardi — shuning uchun
       fiksturdagi oraliqlar ATAYIN «yumaloq bo'lmagan» sonlar.
    =======================================================================
    """
    raw = build_accuracy_workbook(accuracy(measured=True), "uz-Latn", PERIOD)
    texts = xlsx_export.report_texts("uz-Latn")
    rows = labelled_rows(raw)

    assert texts["accuracy_false_occupied"] != texts["accuracy_false_empty"]

    occupied = rows[texts["accuracy_false_occupied"]]
    empty = rows[texts["accuracy_false_empty"]]

    assert occupied[1] == pytest.approx(0.05424528301886792)
    assert empty[1] == pytest.approx(0.08656036446469248)
    assert occupied[2:4] == pytest.approx((0.0364, 0.0798))
    assert empty[2:4] == pytest.approx((0.0637, 0.1165))

    cell = first_sheet(raw).cell(row=1, column=2)
    assert PERCENT_NUM_FORMAT == "0.0%", PERCENT_NUM_FORMAT
    assert cell is not None


@pytest.mark.parametrize("measured", [True, False], ids=["measured", "unmeasured"])
def test_the_accuracy_file_always_carries_the_ai_02_disclaimer(*, measured: bool) -> None:
    """(d) AI-02 holati jumlasi MAJBURIY va SHARTSIZ (D-11, UI-SPEC §9.4).

    ⛔ `measured` DAN MUSTAQIL: o'lchangan holatda ham jumla kerak,
       chunki aynan o'lchangan foiz «model sinovdan o'tgan» degan
       xulosaga olib boradi. Chop etilgan varaq kontekstsiz tarqaladi
       va uni o'qigan odam savol bera olmaydi.

    ⚠ MATN EKRANDAGI BILAN AYNI (`reports.accuracyDisclaimer`), ya'ni
      hujjat va ekran BIR XIL gapni aytadi (D-06).
    """
    raw = build_accuracy_workbook(accuracy(measured=measured), "uz-Latn", PERIOD)
    disclaimer = xlsx_export.report_texts("uz-Latn")["accuracy_disclaimer"]

    every = [
        value
        for line in first_sheet(raw).iter_rows(values_only=True)
        for value in line
        if isinstance(value, str)
    ]

    assert disclaimer in every, every


@pytest.mark.parametrize(
    "kind",
    ["revenue", "receivables", "discrepancies", "accuracy"],
)
def test_an_unknown_locale_falls_back_to_uz_latn(kind: str) -> None:
    """(e) Noma'lum til uz-Latn ga TUSHADI va istisno KO'TARILMAYDI.

    `xlsx_template._texts()` ning aynan qoidasi: yangi til qo'shilganda
    (yoki tokendagi qiymat kutilmagan bo'lsa) hujjatni yuklab olish 500
    bilan tugashi — direktorning oqimini butunlay to'sadigan, sababi esa
    mutlaqo ahamiyatsiz nosozlik bo'lardi.

    ⛔ DA'VO BAYT TENGLIGI BILAN: «istisno ko'tarilmadi» yolg'iz o'zi
       yetarli emas — tarjimasiz bo'sh sarlavhali fayl ham istisnosiz
       chiqardi.
    """
    assert build_every("tr")[kind] == build_every("uz-Latn")[kind]


@pytest.mark.parametrize("locale", ["uz-Latn", "uz-Cyrl", "ru"])
def test_every_locale_translates_every_report_key(locale: str) -> None:
    """Uch tilning kalit to'plami AYNAN TENG — yarim tarjima BO'SH sarlavha berardi.

    ⚠ `dict.get()` bilan yozilgan quruvchi yetishmayotgan kalitda
      `None` yozardi va fayl JIMGINA sarlavhasiz chiqardi.
    """
    assert set(xlsx_export.report_texts(locale)) == set(xlsx_export.report_texts("uz-Latn"))


def test_the_discrepancy_file_carries_only_the_evidence_identifier() -> None:
    """⛔ RASM YO'Q (07 D-03, T-06-81) — faqat kadr IDENTIFIKATORI.

    Imzolangan havola, ombor kaliti yoki baytning O'ZI hujjatga tushsa,
    dalil-kadr yuzasi `.xlsx` orqali KENGAYARDI va u har kimning
    pochtasiga ilova bo'lib ketardi.
    """
    raw = build_discrepancies_workbook(archive_rows(), "uz-Latn", PERIOD)
    every = [
        value
        for line in first_sheet(raw).iter_rows(values_only=True)
        for value in line
        if isinstance(value, str)
    ]

    assert str(SNAPSHOT_ID) in every
    for marker in ("http", "presigned", ".jpg", "X-Amz"):
        assert all(marker not in value for value in every), marker
