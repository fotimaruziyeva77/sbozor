"""`.xlsx` o'qish qatlamining HUJUM testlari (T-02-87 … T-02-89, A9).

=============================================================================
REPOGA BIRORTA BINAR FAYL QO'SHILMAYDI.

Har bir hujum namunasi TEST ICHIDA generatsiya qilinadi. Sabab ikkita:

  1. Zip-bomba yoki billion-laughs faylini repoda saqlash — antivirus va
     supply-chain skanerlari uchun ochiq signal, va u har `git clone` da
     ko'chib yuradi;
  2. Generatsiya qilingan namuna KODDA ko'rinadi, ya'ni keyingi o'quvchi
     "bu fayl nima qiladi?" degan savolga faylni ochmasdan javob oladi.

Bu fayl KONTEYNERSIZ ishlaydi: `xlsx_reader` sessiyaga ham, DB ga ham,
`app/settings.py` ni O'QIShga ham tegmaydi (chegaralar argument sifatida
uzatiladi). Shuning uchun u `tests/unit/` da.
=============================================================================
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime

import openpyxl
import pytest
import xlsxwriter
from app.services import xlsx_reader
from app.services.xlsx_reader import (
    MAX_COLS,
    MAX_ROWS,
    MAX_SHEETS,
    MAX_UNCOMPRESSED_BYTES,
    MAX_UPLOAD_BYTES,
    MAX_ZIP_ENTRIES,
    ImportRejected,
    ReadLimits,
    read_rows,
)

STALL_COLUMNS = 5
"""Rasta shabloni ustunlari (A6): `kod, zona, toifa, holat, izoh`."""

BILLION_LAUGHS = (
    '<?xml version="1.0"?>\n'
    "<!DOCTYPE sst [\n"
    '  <!ENTITY a "aaaaaaaaaa">\n'
    '  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
    '  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">\n'
    '  <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">\n'
    '  <!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">\n'
    '  <!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;">\n'
    "]>\n"
    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'count="1" uniqueCount="1"><si><t>&f;</t></si></sst>'
)
"""Klassik entity kengayishi: 10 bayt -> ~10^6 bayt olti bosqichda.

Namuna ATAYIN KICHIK (olti daraja): himoya ISHLAMAGAN holatda ham test
konteynerini o'ldirmasligi, lekin `defusedxml` ni ishga tushirishi kerak.
`defusedxml` entity E'LONINI ko'rgan zahoti to'xtaydi — kengayish
darajasi uning uchun ahamiyatsiz.
"""


def build_workbook(
    rows: list[list[object]],
    *,
    sheets: int = 1,
    sheet_names: tuple[str, ...] | None = None,
) -> bytes:
    """Haqiqiy `.xlsx` quradi (`XlsxWriter` — loyihaning YOZISH vositasi).

    Birinchi qator SARLAVHA deb hisoblanadi (`read_rows` uni tashlaydi),
    shuning uchun chaqiruvchi uni O'ZI beradi.
    """
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    names = sheet_names or tuple(f"Varaq{index + 1}" for index in range(sheets))
    for position, name in enumerate(names):
        worksheet = workbook.add_worksheet(name)
        if position == 0:
            for index, row in enumerate(rows):
                worksheet.write_row(index, 0, row)
    workbook.close()
    return buffer.getvalue()


def valid_stall_file() -> bytes:
    """Nazorat namunasi — uchta to'g'ri rasta qatori."""
    return build_workbook(
        [
            ["kod", "zona", "toifa", "holat", "izoh"],
            ["1", "Markaziy", "Sabzavot", "active", ""],
            ["2", "Sharqiy", "Go'sht", "active", "burchakda"],
            ["3", "G'arbiy", "Kiyim", "closed", ""],
        ]
    )


def replace_zip_entry(raw: bytes, name: str, payload: bytes) -> bytes:
    """ZIP a'zosining mazmunini almashtiradi, qolganini o'zgarishsiz ko'chiradi."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, "w") as target:
        for entry in source.infolist():
            data = payload if entry.filename == name else source.read(entry.filename)
            target.writestr(entry.filename, data)
    return out.getvalue()


# ===========================================================================
# A9 — `defusedxml` HAQIQATAN ULANGANMI (smoke-test)
# ===========================================================================


def test_openpyxl_detected_defusedxml() -> None:
    """openpyxl `defusedxml` ni KO'RGAN — himoyaning HAQIQIY darvozasi.

    A9: `defusedxml` 0.7.1 (2021) Python 3.13 + openpyxl 3.1.5 bilan
    hamon to'g'ri ulanadimi? Bayroq `False` bo'lib qolsa (paket
    `pyproject.toml` dan tushib qolsa yoki openpyxl aniqlash yo'lini
    o'zgartirsa) himoya JIMGINA yo'qolardi: fayllar baribir o'qilaverardi
    va birorta test qizarmasdi.

    Bu tekshiruv `test_billion_laughs_is_rejected` dan ALOHIDA turadi:
    u SABABNI (mexanizm ulanganmi), ikkinchisi NATIJANI (hujum rad
    etiladimi) o'lchaydi.
    """
    assert openpyxl.DEFUSEDXML is True, (
        "openpyxl `defusedxml` ni topmadi — XML hujumlaridan himoya YO'Q "
        "(`services/core-api/pyproject.toml` dagi pin tekshirilsin)"
    )
    assert openpyxl.xml.functions.iterparse.__module__.startswith("defusedxml")
    assert openpyxl.xml.functions.fromstring.__module__.startswith("defusedxml")


def test_billion_laughs_is_rejected() -> None:
    """XML entity kengayishi bo'lgan fayl RAD ETILADI (T-02-87).

    ⚠ BU TEST QIZARSA: `python-calamine 0.8.2` ga o'tiladi (02-RESEARCH
    Open Question 3). Muqobil ALLAQACHON tekshirilgan — Rust parser bu
    hujum sinfiga strukturaviy immun, MIT litsenziyasi va cp313
    g'ildiragi bor. Ya'ni qizarish "tuzatib qo'yiladigan xato" emas,
    KUTUBXONA ALMASHTIRISH signali.

    Konteynerda o'lchandi: openpyxl entity xatosini O'Z `ValueError`
    iga o'raydi (`Unable to read workbook: could not read strings from
    None`), ya'ni `EntitiesForbidden` ni to'g'ridan-to'g'ri ushlab
    bo'lmaydi — shuning uchun `_PARSE_FAILURES` keng.
    """
    bombed = replace_zip_entry(valid_stall_file(), "xl/sharedStrings.xml", BILLION_LAUGHS.encode())

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(bombed, expected_columns=STALL_COLUMNS)

    assert excinfo.value.code == "unsupported_file_type"


def test_billion_laughs_in_the_worksheet_is_rejected() -> None:
    """Bomba VARAQ XML ida bo'lganda ham rad etiladi.

    `sharedStrings.xml` `load_workbook()` paytida, varaq XML i esa
    QATORLAR O'QILAYOTGANDA parse qilinadi — ya'ni bu ikkinchi, mustaqil
    kod yo'li. Faqat birinchisini sinash "himoya bor" degan yarim
    haqiqatni berardi.
    """
    bombed = replace_zip_entry(
        valid_stall_file(), "xl/worksheets/sheet1.xml", BILLION_LAUGHS.encode()
    )

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(bombed, expected_columns=STALL_COLUMNS)

    assert excinfo.value.code == "unsupported_file_type"


# ===========================================================================
# T-02-88 — ZIP bomba parse'DAN OLDIN rad etiladi
# ===========================================================================


def test_zip_bomb_is_rejected_before_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zip-bomba `load_workbook()` UMUMAN CHAQIRILMASDAN rad etiladi.

    Test NATIJANI emas, TARTIBNI o'lchaydi. Sabab: `defusedxml` bu hujum
    sinfiga YORDAM BERMAYDI, ya'ni fayl parserga yetib borsa xotira
    portlashi allaqachon boshlangan bo'lardi. "Fayl rad etildi" degan
    da'vo yetarli emas — u parse qilingandan KEYIN rad etilgan holatda
    ham yashil bo'lardi.

    Namuna: 20 MB nol bayt (deflate bilan ~20 KB ga siqiladi), chegara
    esa 1 MB ga toraytirilgan.
    """
    calls: list[object] = []

    def _explode(*args: object, **kwargs: object) -> object:
        calls.append(args)
        raise AssertionError("load_workbook ZIP darvozasidan OLDIN chaqirildi")

    monkeypatch.setattr(openpyxl, "load_workbook", _explode)

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"\0" * (20 * 1024 * 1024))
    bomb = payload.getvalue()

    assert len(bomb) < 1024 * 1024, "namuna siqilmagan — test hech nimani o'lchamaydi"

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            bomb,
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(uncompressed_bytes=1024 * 1024),
        )

    assert excinfo.value.code == "file_too_large"
    assert calls == [], "load_workbook chaqirildi — ZIP darvozasi parse'dan KEYIN turibdi"


def test_too_many_zip_entries_is_rejected() -> None:
    """Millionlab mayda a'zoli arxiv — ochilgan hajm kichik bo'lsa ham rad etiladi."""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for index in range(30):
            archive.writestr(f"junk/{index}.xml", b"x")

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            payload.getvalue(),
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(zip_entries=10),
        )

    assert excinfo.value.code == "file_too_complex"


# ===========================================================================
# T-02-89 — hajm / qator / ustun / varaq chegaralari
# ===========================================================================


def test_oversized_file_is_rejected() -> None:
    """`MAX_UPLOAD_BYTES` dan katta XOM bayt massivi — ZIP ochilishidan oldin."""
    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            b"\0" * 2049,
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(upload_bytes=2048),
        )

    assert excinfo.value.code == "file_too_large"


def test_too_many_rows_is_rejected() -> None:
    """Qator chegarasi (T-02-89)."""
    rows: list[list[object]] = [["kod", "zona", "toifa", "holat", "izoh"]]
    rows += [[str(index), "Markaziy", "Sabzavot", "active", ""] for index in range(1, 11)]

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            build_workbook(rows),
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(rows=5),
        )

    assert excinfo.value.code == "file_too_complex"


def strip_dimension(raw: bytes) -> bytes:
    """Varaq XML idan `<dimension>` e'lonini BUTUNLAY olib tashlaydi.

    Bu — chegarani chetlab o'tishning HAQIQIY shakli va u o'lchandi.
    Uchta yolg'on e'lon varianti bor:

    * KATTA e'lon  -> arzon rad etish (`ws.max_row` darvozasi);
    * KICHIK e'lon -> openpyxl e'londan ORTIQ qator QAYTARMAYDI, ya'ni
      hujumchi faqat o'z ma'lumotini yo'qotadi. DoS emas;
    * E'LON YO'Q   -> `ws.max_row` `None` bo'ladi, birinchi darvoza
      jimgina o'tadi va butun varaq o'qiladi. AYNAN SHU holat xavfli.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode()

    start = sheet_xml.index("<dimension")
    end = sheet_xml.index(">", start) + 1
    return replace_zip_entry(
        raw,
        "xl/worksheets/sheet1.xml",
        (sheet_xml[:start] + sheet_xml[end:]).encode(),
    )


def test_missing_dimension_does_not_bypass_the_row_limit() -> None:
    """`<dimension>` E'LONI YO'Q faylda ham qator chegarasi ishlaydi.

    `ws.max_row` faylning O'ZIDAGI e'londan keladi, ya'ni uni hujumchi
    yozadi — yoki umuman yozmaydi. E'lonsiz varaqda u `None` bo'ladi va
    "arzon" darvoza jimgina o'tib ketadi: faqat e'longa tayanish
    "chegarani tekshiryapmiz" degan YOLG'ON tuyg'u berardi.

    Bu test dastlabki yozuvda AYNAN shuni fosh qildi: qatorlar avval
    `list(...)` ga yig'ilib, KEYIN sanalardi — ya'ni chegara xotira
    yeyilgandan keyin ishlardi. Yechim — lazy iteratsiya (`_safe_rows`).
    """
    rows: list[list[object]] = [["kod", "zona", "toifa", "holat", "izoh"]]
    rows += [[str(index), "Markaziy", "Sabzavot", "active", ""] for index in range(1, 11)]
    stripped = strip_dimension(build_workbook(rows))

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(stripped, expected_columns=STALL_COLUMNS, limits=ReadLimits(rows=5))

    assert excinfo.value.code == "file_too_complex"


def test_missing_dimension_still_reads_a_valid_file() -> None:
    """NAZORAT: e'lonsiz fayl chegaradan past bo'lsa NORMAL o'qiladi.

    Usiz yuqoridagi test `<dimension>` yo'q har qanday faylni rad
    etadigan implementatsiyada ham yashil bo'lardi — va o'shanda
    LibreOffice eksporti (u e'lonni ba'zan yozmaydi) butunlay
    ishlamasdi.
    """
    stripped = strip_dimension(valid_stall_file())

    rows = read_rows(stripped, expected_columns=STALL_COLUMNS)

    assert [row.row for row in rows] == [2, 3, 4]


def test_too_many_columns_is_rejected() -> None:
    """Ustun chegarasi (T-02-89)."""
    wide: list[object] = [f"ustun{index}" for index in range(12)]

    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            build_workbook([wide, wide]),
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(cols=5),
        )

    assert excinfo.value.code == "file_too_complex"


def test_too_many_sheets_is_rejected() -> None:
    """Varaq chegarasi (T-02-89)."""
    with pytest.raises(ImportRejected) as excinfo:
        read_rows(
            build_workbook([["kod"], ["1"]], sheets=6),
            expected_columns=STALL_COLUMNS,
            limits=ReadLimits(sheets=3),
        )

    assert excinfo.value.code == "file_too_complex"


def test_non_zip_payload_is_rejected() -> None:
    """`.xlsx` bo'lmagan bayt oqimi (masalan CSV yoki PDF) -> `unsupported_file_type`."""
    with pytest.raises(ImportRejected) as excinfo:
        read_rows(b"kod,zona,toifa\n1,Markaziy,Sabzavot\n", expected_columns=STALL_COLUMNS)

    assert excinfo.value.code == "unsupported_file_type"


# ===========================================================================
# D-14 — qator raqamlari Excel bilan MOS
# ===========================================================================


def test_row_numbers_match_excel() -> None:
    """Uchinchi MA'LUMOT qatorining `row` qiymati AYNAN 4 (sarlavha = 1).

    Bu D-14 ning yadrosi: admin xatoni Excelda tuzatadi, ya'ni xabardagi
    raqam uning ekranidagi raqam BO'LISHI SHART. Nol yoki birdan qayta
    sanash butunlay boshqa qatorni ko'rsatardi.
    """
    rows = read_rows(valid_stall_file(), expected_columns=STALL_COLUMNS)

    assert [row.row for row in rows] == [2, 3, 4]
    assert rows[2].values[0] == "3"


def test_valid_file_is_read() -> None:
    """NAZORAT HOLATI — to'g'ri fayl muvaffaqiyatli o'qiladi.

    Usiz yuqoridagi rad etish testlari `read_rows` HAR DOIM istisno
    ko'taradigan holatda ham yashil bo'lardi.
    """
    rows = read_rows(valid_stall_file(), expected_columns=STALL_COLUMNS)

    assert len(rows) == 3
    assert rows[0].values == ("1", "Markaziy", "Sabzavot", "active", None)
    assert rows[1].values == ("2", "Sharqiy", "Go'sht", "active", "burchakda")


def test_short_rows_are_padded() -> None:
    """Kam ustunli qator `None` bilan to'ldiriladi va ISTISNO BERMAYDI.

    Qisqa qator XATO EMAS — u validatorning ishi (`row_too_short`), va
    aynan shu ajratish foydalanuvchiga QATOR RAQAMI bilan xabar berish
    imkonini beradi. O'quvchi qatlamda istisno ko'tarilsa butun fayl
    bitta sababsiz `unsupported_file_type` bilan rad etilardi.
    """
    rows = read_rows(
        build_workbook(
            [
                ["kod", "zona", "toifa", "holat", "izoh"],
                ["1", "Markaziy"],
            ]
        ),
        expected_columns=STALL_COLUMNS,
    )

    assert len(rows) == 1
    assert rows[0].values == ("1", "Markaziy", None, None, None)


def test_blank_rows_are_skipped_but_numbering_is_preserved() -> None:
    """Butunlay bo'sh qator TASHLANADI, keyingi qatorning raqami esa SURILMAYDI.

    Excel'dan eksport qilingan faylda formatlangan bo'sh qatorlar odatiy
    hol. Ularni saqlash har biriga `empty_code` xatosi berardi va D-14
    (all-or-nothing) tufayli MUTLAQO TO'G'RI fayl ham butunlay rad
    etilardi — 900 ta "xato" bilan.
    """
    rows = read_rows(
        build_workbook(
            [
                ["kod", "zona", "toifa", "holat", "izoh"],
                ["1", "Markaziy", "Sabzavot", "active", ""],
                ["", "", "", "", ""],
                ["2", "Sharqiy", "Go'sht", "active", ""],
            ]
        ),
        expected_columns=STALL_COLUMNS,
    )

    assert [row.row for row in rows] == [2, 4]


def test_extra_columns_are_ignored() -> None:
    """Shablondan ortiq ustunlar KESILADI (chegaradan past bo'lsa).

    Admin o'z ro'yxatiga qo'shimcha ustun qo'shishi mumkin; uni xato
    deb belgilash importni sababsiz to'sardi.
    """
    rows = read_rows(
        build_workbook(
            [
                ["kod", "zona", "toifa", "holat", "izoh", "ortiqcha"],
                ["1", "Markaziy", "Sabzavot", "active", "", "e'tiborsiz"],
            ]
        ),
        expected_columns=STALL_COLUMNS,
    )

    assert rows[0].values == ("1", "Markaziy", "Sabzavot", "active", None)


# ===========================================================================
# Katak tiplari — real fayllardan keladigan uchta holat
# ===========================================================================


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (12, "12"),
        (12.0, "12"),
        (12.5, "12.5"),
        ("  bo'sh joy  ", "bo'sh joy"),
    ],
    ids=["int", "integral-float", "float", "trimmed"],
)
def test_cell_values_are_normalised(cell: object, expected: str) -> None:
    """Excel tiplari matnga bir xil qoida bilan keltiriladi.

    `12.0 -> "12"` eng qimmat holat: Excel butun sonni ba'zan float
    qilib qaytaradi va `str()` `"12.0"` berardi. O'shanda rasta kodi
    bazadagi `"12"` bilan MOS TUSHMASDI va D-15 idempotentligi
    buzilardi — har qayta import "yangi" kod yaratardi.
    """
    rows = read_rows(
        build_workbook([["kod", "zona", "toifa", "holat", "izoh"], [cell]]),
        expected_columns=STALL_COLUMNS,
    )

    assert rows[0].values[0] == expected


@pytest.mark.parametrize(
    "cell",
    [datetime(2026, 8, 1, 0, 0), date(2026, 8, 1)],
    ids=["datetime", "date"],
)
def test_date_cells_become_iso_dates(cell: datetime | date) -> None:
    """Sana katagi ISO SANA bo'lib keladi, `"...  00:00:00"` bo'lib emas.

    Sotuvchi shabloni "boshlanish sanasi" ustunini o'z ichiga oladi
    (A6) va admin uni Excelda SANA sifatida kiritadi. `str(datetime)`
    `"2026-08-01 00:00:00"` berardi, `date.fromisoformat()` esa uni RAD
    ETARDI — ya'ni to'g'ri to'ldirilgan fayl `invalid_date` xatosi bilan
    butunlay qaytarilardi (D-14: bitta xato = hech narsa yozilmaydi).

    ⚠ KATAK FORMAT BILAN YOZILADI va bu test artefakti emas, Excel
    formatining O'ZI: formatsiz katak faylda oddiy SON (seriya raqami,
    masalan `46235`) bo'lib qoladi va openpyxl uni `int` deb qaytaradi.
    Dastlabki yozuvda test aynan `'46235' != '2026-08-01'` bilan
    yiqildi — ya'ni haqiqiy fayllarda ham formatlanmagan sana ustuni
    sonday ko'rinadi.
    """
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet("Sotuvchilar")
    iso = workbook.add_format({"num_format": "yyyy-mm-dd"})
    worksheet.write_row(0, 0, ["F.I.Sh.", "telefon", "rasta kodi", "boshlanish sanasi"])
    worksheet.write_datetime(1, 3, cell, iso)
    workbook.close()

    rows = read_rows(buffer.getvalue(), expected_columns=4)

    assert rows[0].values[3] == "2026-08-01"


def test_formula_cells_yield_the_computed_value_not_the_text() -> None:
    """`data_only=True` — formula MATNI qaytarilmaydi.

    `XlsxWriter` formula bilan birga hisoblangan qiymatni ham yozadi
    (`value=`), ya'ni `data_only=True` bo'lmasa katak `"=1+1"` bo'lib
    kelardi va rasta kodi sifatida "noto'g'ri" deb belgilanardi.
    """
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet("Rastalar")
    worksheet.write_row(0, 0, ["kod", "zona", "toifa", "holat", "izoh"])
    worksheet.write_formula(1, 0, "=1+1", None, 2)
    workbook.close()

    rows = read_rows(buffer.getvalue(), expected_columns=STALL_COLUMNS)

    assert rows[0].values[0] == "2"


# ===========================================================================
# A7 — chegaralar sozlanadigan, LEKIN standartlari qulflangan
# ===========================================================================


def test_default_limits_match_the_documented_values() -> None:
    """Standart chegaralar — Pitfall 5 dagi qiymatlar bilan AYNAN bir xil.

    Yuqoridagi darvoza testlari chegarani ATAYIN toraytiradi (5000
    qatorli fayl qurish sekin), ya'ni ular standart QIYMATNI umuman
    sinamaydi. Usiz kimdir `MAX_ROWS` ni 5 000 000 qilib qo'yganda
    butun to'plam yashil qolardi.
    """
    assert (MAX_UPLOAD_BYTES, MAX_UNCOMPRESSED_BYTES) == (5 * 1024 * 1024, 50 * 1024 * 1024)
    assert (MAX_ROWS, MAX_COLS, MAX_SHEETS, MAX_ZIP_ENTRIES) == (5_000, 32, 8, 200)

    defaults = ReadLimits()
    assert defaults.upload_bytes == MAX_UPLOAD_BYTES
    assert defaults.uncompressed_bytes == MAX_UNCOMPRESSED_BYTES
    assert defaults.rows == MAX_ROWS
    assert defaults.cols == MAX_COLS
    assert defaults.sheets == MAX_SHEETS
    assert defaults.zip_entries == MAX_ZIP_ENTRIES


def test_limits_can_be_overridden_from_settings() -> None:
    """Chegaralar `app/settings.py` orqali qayta yoziladi (A7).

    Sozlamalar `pydantic-settings` bilan muhitdan to'ladi, ya'ni bu
    yo'l "1000 rastadan kattaroq bozor kelganda" deploy qayta
    qurilmasdan kengaytiriladi.
    """
    settings = xlsx_reader.ReadLimits.from_settings(
        _FakeSettings(  # type: ignore[arg-type]
            import_max_upload_bytes=11,
            import_max_uncompressed_bytes=22,
            import_max_rows=33,
            import_max_cols=44,
            import_max_sheets=55,
            import_max_zip_entries=66,
        )
    )

    assert (settings.upload_bytes, settings.uncompressed_bytes) == (11, 22)
    assert (settings.rows, settings.cols) == (33, 44)
    assert (settings.sheets, settings.zip_entries) == (55, 66)


class _FakeSettings:
    """`Settings` ning ALTI maydonli soxta nusxasi.

    Haqiqiy `Settings()` MAJBURIY sirlarni (`DATABASE_URL`, `JWT_SECRET`,
    ...) talab qiladi va ularni muhitdan oladi — ya'ni uni bu unit
    testda qurish testni muhitga bog'lab qo'yardi. `from_settings()`
    faqat shu oltitasini o'qiydi va imzo o'zgarsa mypy DARHOL
    ko'rsatadi (`Settings` maydoni qo'shilsa `AttributeError`).
    """

    def __init__(self, **fields: int) -> None:
        for name, value in fields.items():
            setattr(self, name, value)
