"""`.xlsx` eksportining YAGONA poydevori — determinizm va yozish intizomi.

=============================================================================
UCH FAKT — KEYINGI O'QUVCHI UCHUN, LITERAL.

1. `freeze_zip` BU YERGA `tests/fixtures/karmana_seed.py` DAN KO'CHIRILDI
   va fikstursdagi nusxa O'CHIRILDI. Naqsh mahsulotda emas, TEST
   fikstursida tug'ilgan edi (`karmana_seed._freeze_zip`), ya'ni
   mahsulot eksport yo'llari (`build_template`, `build_error_report`)
   bayt-determinik EMAS edi. Ikki nusxa saqlansa sana konstantalari bir
   kun ajralib ketardi va o'shanda «fayl determinik» degan da'vo IKKI
   XIL ma'noni anglatardi.

   ⚠ DETERMINIZMNI BUGUN NIMA TA'MINLAYDI: `new_workbook()` dagi
   `set_properties({"created": FROZEN_CREATED})` — YOLG'IZ O'ZI.
   `freeze_zip` ikkinchi qatlam EMAS (reja shunday deb taxmin qilgan
   edi; sabotaj bilan o'lchandi va rad etildi) — u a'zo sanasi
   invariantining qo'riqchisi. Batafsil: `freeze_zip` docstringi.

2. `worksheet.write()` va `worksheet.write_string()` BU MODULDA HAM,
   UNING ISTE'MOLCHILARIDA HAM TO'G'RIDAN-TO'G'RI CHAQIRILMAYDI. Yagona
   matn yo'li — `write_text()`. Qochirishni har chaqiruvda qo'lda yozish
   bitta kunda bitta joyda unutilardi va himoya JIMGINA teshilardi.
   `write_string()` ATAYIN (`write()` emas): `write()` `"123"` ni songa,
   `"=1+1"` ni esa FORMULAGA aylantirib yuborardi — ya'ni qochirishdan
   keyin ham hujum tiklanardi.

3. SABAB: qarzdorlik reestrida `vendor_name` bor. Ya'ni `=HYPERLINK(...)`
   nomli sotuvchi DIREKTORNING mashinasida kod bajartirardi. Hujum
   serverda emas, mijozda portlaydi va uni bir marta yozgan odam
   keyinchalik boshqa odamning Excelida bajartiradi — bu saqlangan
   hujum (OWASP CSV/Formula Injection).
=============================================================================

⚠ BOG'LIQLIK YO'NALISHI BITTA: `xlsx_template` -> `xlsx_export`.

`escape_formula` va `FORMULA_PREFIXES` ning TA'RIFI shu modulda yashaydi.
08-01-PLAN Task 1 ularni `xlsx_template` da qoldirishni ko'zda tutgan
edi, lekin o'sha yo'nalish HALQA hosil qilardi va u IKKALA kirish
nuqtasida O'LCHANDI (taxmin emas — probe qo'yilib bajarildi):

    $ python -c "import app.services.xlsx_export"
    ImportError: cannot import name 'finish' from partially initialized
    module 'app.services.xlsx_export' (most likely due to a circular import)

    $ python -c "import app.services.xlsx_template"
    ImportError: cannot import name 'FORMULA_PREFIXES' from partially
    initialized module 'app.services.xlsx_template'
    (most likely due to a circular import)

Ya'ni halqa import TARTIBIGA bog'liq emas — ikkala tomondan ham
yiqiladi va mahsulot yo'li (`api/v1/imports.py` -> `xlsx_template`) ham
shu ikkinchi izda. `xlsx_template` bu yerdan `new_workbook`/`finish` ni
oladi, shu bilan birga `escape_formula` ni bersa — halqa yopiladi. Reja
aynan shu holat uchun yo'nalishni bitta qilishni buyurgan (Task 2,
«yo'nalish BITTA bo'lsin»). `xlsx_template` nomlarni QAYTA E'LON
qiladi, ya'ni mavjud chaqiruvchilar (`test_xlsx_template.py`)
o'zgarmaydi va ta'rif hamon BITTA.

⚠ `constant_memory` REJIMI ISHLATILMAYDI (Pitfall 13). U qatorlarni
navbat bilan diskka oqizadi va shu sababdan `freeze_panes()` bilan
`autofilter()` ni BUZADI — ikkalasi ham qarzdorlik reestrida majburiy
(sarlavha muzlatilmagan 30 000 qatorli faylda direktor qaysi ustun nima
ekanini ko'rmay qolardi). Xotira chegarasi buning o'rniga
`Settings.report_max_rows` bilan qo'yiladi.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

import xlsxwriter

if TYPE_CHECKING:
    from xlsxwriter import Workbook

__all__ = [
    "FORMULA_PREFIXES",
    "FROZEN_CREATED",
    "FROZEN_ZIP_TIME",
    "MONEY_NUM_FORMAT",
    "escape_formula",
    "finish",
    "freeze_zip",
    "money_format",
    "new_workbook",
    "write_money",
    "write_optional_text",
    "write_text",
]

FROZEN_ZIP_TIME: Final = (1980, 1, 1, 0, 0, 0)
"""ZIP a'zolarining sobit sanasi (DOS epoxasining boshi) — `freeze_zip`.

1980-01-01 tanlangani tasodifiy emas: DOS sana maydoni bundan oldingi
qiymatni UMUMAN kodlay olmaydi, ya'ni bu eng past yozilishi mumkin
bo'lgan sana va u hech qachon "kelajakdagi fayl" ogohlantirishini
tug'dirmaydi.
"""

FROZEN_CREATED: Final = datetime(2026, 8, 1, 0, 0, 0)  # noqa: DTZ001
"""`docProps/core.xml` dagi sobit `dcterms:created`.

⚠ Naive datetime ATAYIN va `DTZ001` shu sababdan susturilgan: bu qiymat
ZIP METAMA'LUMOTI, BIZNES VAQTI EMAS. U hech qachon biznes-kunga
aylanmaydi, hisobot chegarasini belgilamaydi va foydalanuvchiga
ko'rsatilmaydi — u faqat baytlarni muzlatish uchun. `XlsxWriter` uni
tz'siz kutadi.
"""

MONEY_NUM_FORMAT: Final = "#,##0"
"""Pul kataklarining Excel format satri (so'm, kasrsiz).

Kasr qismi YO'Q va bu loyiha darajasidagi qaror: pul `BIGINT` so'm
sifatida saqlanadi va `float` ga UMUMAN aylanmaydi (yaxlitlash drifti
kunlik patta yig'indisida sotuvchi bilan nizoga aylanardi — mahsulot
aynan shu nosozlikni yo'q qilish uchun mavjud).
"""

FORMULA_PREFIXES: Final = ("=", "+", "-", "@", "\t", "\r")
"""Excel formula sifatida talqin qiladigan boshlang'ich belgilar (OWASP).

`\\t` va `\\r` ro'yxatda ATAYIN: ular ko'rinmaydi, lekin Excel ularni
tashlab yuborib KEYINGI belgiga qaraydi — ya'ni `"\\t=cmd|..."` oddiy
`=` tekshiruvidan o'tib ketardi.
"""


def escape_formula(value: str) -> str:
    """Excel formulasiga aylanadigan matnni zararsizlantiradi (OWASP).

    Xavfli prefiksdan oldin `'` qo'yiladi — Excel uni "bu matn" belgisi
    deb o'qiydi va katakda KO'RSATMAYDI, ya'ni foydalanuvchi ko'radigan
    qiymat o'zgarmaydi.

    Bo'sh satr o'zgarishsiz qaytadi: unda boshlang'ich belgi umuman
    yo'q.
    """
    if value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def freeze_zip(raw: bytes) -> bytes:
    """ZIP a'zolarining sanasini MUZLATADI — MUDOFAA qatlami, TIRIK EMAS.

    =======================================================================
    ⚠ MEROS QILIB OLINGAN DA'VO YOLG'ON CHIQDI VA U SHU YERDA TUZATILADI.

    02-23 dan kelgan docstring shunday deydi: «`XlsxWriter` `in_memory`
    rejimida `ZipFile.writestr(nom, ...)` ni chaqiradi, `zipfile` esa
    a'zo sanasini SOAT'dan oladi». 08-01 buni O'LCHADI va u
    `XlsxWriter` **3.2.9** da TO'G'RI EMAS:

        XOM xlsxwriter a'zo sanalari: {(1980, 1, 1, 0, 0, 0)}
        set_properties SIZ,   freeze_zip SIZ, 1.1 s oraliq -> teng? False
        set_properties BILAN, freeze_zip SIZ, 1.1 s oraliq -> teng? True

    Ya'ni `XlsxWriter` a'zo sanasini O'ZI muzlatadi va SOAT faylga
    FAQAT bitta yo'ldan kiradi — `docProps/core.xml` dagi
    `dcterms:created`. Determinizmni bugun `new_workbook()` dagi
    `set_properties()` YOLG'IZ ta'minlaydi.

    ⛔ SHUNDAY EKAN, NEGA SAQLANADI? Chunki bu funksiya endi
    DETERMINIZM QATLAMI emas, INVARIANT QO'RIQCHISI: u a'zo sanasi
    `FROZEN_ZIP_TIME` ekanini `XlsxWriter` ning ichki tanlovidan
    QAT'I NAZAR kafolatlaydi. Kutubxona paketlovchisini o'zgartirsa
    (yoki eksport boshqa yozuvchidan o'tsa) da'vo baribir rost qoladi.
    Uning O'Z shartnomasi `test_freeze_zip_normalises_clock_dated_
    members` da to'g'ridan-to'g'ri o'lchanadi — «ikkinchi qatlam»
    hikoyasi orqali EMAS.

    ⚠ KEYINGI O'QUVCHIGA: reja bu funksiyani «ikki mustaqil qatlamning
    biri» deb ta'riflagan va sabotaj bilan ISBOTLASHNI buyurgan edi.
    Sabotaj bajarildi va da'voni RAD ETDI (SUMMARY, S-2). Yozilgan
    hikoyaga ishonib, o'lchovni o'tkazib yubormang.
    =======================================================================

    Qayta o'rash mazmunga tegmaydi: nom, siqish turi va ochilgan hajm
    o'zgarmaydi, ya'ni `xlsx_reader._check_zip()` darvozalari ham xuddi
    shu qiymatlarni ko'radi.
    """
    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(raw)) as source,
        zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for info in source.infolist():
            frozen = zipfile.ZipInfo(info.filename, date_time=FROZEN_ZIP_TIME)
            frozen.compress_type = info.compress_type
            frozen.external_attr = info.external_attr
            frozen.create_system = info.create_system
            target.writestr(frozen, source.read(info.filename))
    return buffer.getvalue()


def new_workbook(buffer: io.BytesIO) -> Workbook:
    """Determinizm 1-qatlami bilan ochilgan kitob.

    ⚠ `set_properties({"created": ...})` — BUGUNGI KUNDA DETERMINIZMNI
    TA'MINLAYDIGAN YAGONA MEXANIZM, va bu o'lchangan (`freeze_zip`
    docstringiga qarang): `XlsxWriter` 3.2.9 ZIP a'zo sanasini o'zi
    muzlatadi, ya'ni soat faylga faqat `docProps/core.xml` orqali
    kiradi. Bu qator olib tashlanganda determinizm testi QIZARADI
    (o'lchandi: baytlar 3942-indeksda ajraladi).

    ⛔ `constant_memory` QO'YILMAYDI — modul docstringiga qarang
    (`freeze_panes`/`autofilter` buziladi, Pitfall 13).
    """
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    workbook.set_properties({"created": FROZEN_CREATED})
    return workbook


def money_format(workbook: Workbook) -> Any:
    """Pul kataklarining formati — `MONEY_NUM_FORMAT` ning YAGONA qo'llash joyi.

    Har chaqiruvchi `add_format({"num_format": "#,##0"})` ni o'zi yozsa,
    format satri repoda ko'chirilardi va bitta hisobotda kasrli, boshqasida
    kasrsiz pul chiqardi.
    """
    return workbook.add_format({"num_format": MONEY_NUM_FORMAT})


def write_text(
    worksheet: Any,
    row: int,
    column: int,
    value: str,
    cell_format: Any = None,
) -> None:
    """YAGONA matn yozish yo'li — `escape_formula()` shu yerda qo'llanadi.

    `worksheet.write()` boshqa hech qayerda CHAQIRILMAYDI: modul
    docstringidagi 2-fakt aynan shu haqda va u Task 1 ning qabul
    mezoni bilan mexanik qulflangan.
    """
    worksheet.write_string(row, column, escape_formula(value), cell_format)


def write_money(
    worksheet: Any,
    row: int,
    column: int,
    value: int,
    cell_format: Any,
) -> None:
    """Pulni SON bo'lib yozadi (so'm, `BIGINT` <-> `int`).

    ⚠ Tip annotatsiyasi `int` va u `float` NI QABUL QILMAYDI (C-6). Bu
    `mypy` darajasidagi darvoza, ish vaqtidagi tekshiruv emas: `float`
    pul loyihada taqiqlangan (yaxlitlash drifti kunlik patta
    yig'indisida sotuvchi bilan nizoga aylanardi) va uni yozish
    yo'lining O'ZIDA to'sish tekshiruvni yozuvchidan o'quvchiga
    surardi.

    `cell_format` MAJBURIY va standart qiymati YO'Q: formatsiz yozilgan
    pul katakda `150000` bo'lib chiqardi va direktor uni bir qarashda
    o'qiy olmasdi. `money_format(workbook)` shu argument uchun.
    """
    worksheet.write_number(row, column, value, cell_format)


def write_optional_text(
    worksheet: Any,
    row: int,
    column: int,
    value: str | None,
    cell_format: Any = None,
) -> None:
    """O'LCHANMAGAN qiymat uchun BO'SH katak — `0` EMAS (D-10).

    `None` `write_blank()` ga tushadi, ya'ni katak FORMATLANGAN, LEKIN
    QIYMATSIZ bo'ladi. Nol yozilsa u O'LCHANGAN noldan farq qilmasdi va
    direktor «to'lov yo'q» degan xulosani o'lchanmagan qatordan ham
    o'qirdi — bu esa mahsulotning butun da'vosini (raqam bilan fosh
    qilish) buzardi.
    """
    if value is None:
        worksheet.write_blank(row, column, None, cell_format)
        return
    write_text(worksheet, row, column, value, cell_format)


def finish(workbook: Workbook, buffer: io.BytesIO) -> bytes:
    """Kitobni yopadi va baytlarni muzlatadi — eksportning YAGONA chiqishi.

    `close()` va `freeze_zip()` ni ajratib chaqirish mumkin edi, lekin
    o'shanda yangi eksport marshruti (08-10, 08-16) ikkinchisini
    unutishi mumkin bo'lardi va fayl JIMGINA nodeterminik chiqardi.
    """
    workbook.close()
    return freeze_zip(buffer.getvalue())
