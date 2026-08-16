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
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Final

import xlsxwriter
from sbozor_core.enums import (
    AnomalyKind,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from xlsxwriter import Workbook

    from app.schemas import (
        AnomalyArchiveRowResponse,
        ReceivablesReportRow,
        RevenueReportRow,
    )
    from app.services.accuracy_report import AccuracyReport

__all__ = [
    "COUNT_NUM_FORMAT",
    "FORMULA_PREFIXES",
    "FROZEN_CREATED",
    "FROZEN_ZIP_TIME",
    "MONEY_NUM_FORMAT",
    "PERCENT_NUM_FORMAT",
    "REPORT_DEFAULT_LOCALE",
    "ReportPeriod",
    "build_accuracy_workbook",
    "build_discrepancies_workbook",
    "build_receivables_workbook",
    "build_revenue_workbook",
    "escape_formula",
    "finish",
    "freeze_zip",
    "layout_sheet",
    "money_format",
    "new_workbook",
    "report_texts",
    "write_header",
    "write_money",
    "write_optional_number",
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

COUNT_NUM_FORMAT: Final = "#,##0"
"""SANOQ kataklarining formati — ⛔ `MONEY_NUM_FORMAT` NING ALIASI EMAS.

Bugun ikkala satr ham `#,##0`, lekin ular IKKI BOSHQA qarordan keladi va
shuning uchun ATAYIN ikki nom bilan yashaydi: pul formatiga bir kun valyuta
qo'shimchasi (`#,##0" so'm"`) kelishi mumkin va o'shanda «612 so'm javob»
degan aniqlik hisoboti chiqardi. Bitta konstantani ikki ma'noda ishlatish
aynan shu sinf nosozlikni tug'diradi.
"""

PERCENT_NUM_FORMAT: Final = "0.0%"
"""FOIZ kataklarining formati — qiymat ULUSH bo'lib (0..1) yoziladi.

⛔ `0,054` ni `5,4` ga QO'LDA ko'paytirish TAQIQ: o'shanda katakda son
   bo'lardi-yu, u foiz EKANI faqat sarlavhada aytilardi va Excelda
   ustunni yig'ish ma'nosiz natija berardi. Format esa ko'rinishni
   o'zgartiradi, MA'NONI emas.

⚠ Bitta kasr xonasi (`0.0%`) — ekrandagi bilan AYNI aniqlik
  (`occupancy.falseOccupied`: «5,4 %»). Ikki xona faylda ekranda
  ko'rinmaydigan aniqlikni ko'rsatib, «qaysi son to'g'ri?» savolini
  tug'dirardi.
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


def write_optional_number(
    worksheet: Any,
    row: int,
    column: int,
    value: float | None,
    cell_format: Any = None,
) -> None:
    """O'LCHANMAGAN SON uchun BO'SH katak — ⛔ `0` EMAS (D-10, T-08-53).

    =======================================================================
    ⛔ BU FUNKSIYA PUL UCHUN EMAS VA U HECH QACHON PUL YOZMAYDI.

    Annotatsiya `float`, ya'ni u FOIZ (ulush, 0..1) va SANOQ uchun.
    Pul `BIGINT` so'm sifatida saqlanadi, `float` ga UMUMAN aylanmaydi
    (yaxlitlash drifti kunlik patta yig'indisida sotuvchi bilan nizoga
    aylanardi — mahsulot aynan shu nosozlikni yo'q qilish uchun bor) va
    uning YAGONA yo'li `write_money()` bo'lib qoladi.
    =======================================================================

    `None` -> `write_blank()`: katak FORMATLANGAN, lekin QIYMATSIZ.
    Nol yozilsa u O'LCHANGAN noldan farq qilmasdi va imzolanadigan
    varaqda «tizim hech qachon xato qilmaydi» degan O'LCHANGAN da'vo
    bo'lib o'qilardi — holbuki o'lchov UMUMAN bo'lmagan (T-05-04).
    """
    if value is None:
        worksheet.write_blank(row, column, None, cell_format)
        return
    worksheet.write_number(row, column, value, cell_format)


def write_header(
    worksheet: Any,
    row: int,
    labels: Sequence[str],
    cell_format: Any = None,
) -> None:
    """Sarlavha qatori — ⛔ U HAM `write_text()` DAN O'TADI.

    Sarlavhalar SERVERDA hosil bo'ladigan matn, ya'ni ular hujumchining
    nazoratida emas. Shunga qaramay ular ham yagona yo'ldan yoziladi:
    ikkinchi yozish yo'lining MAVJUDLIGI kelasi ijrochiga «bu yerda xom
    yozsa ham bo'larkan» degan pretsedent berardi va u pretsedent
    sotuvchi ismi yoziladigan joyda ishlatilardi.
    """
    for column, label in enumerate(labels):
        write_text(worksheet, row, column, label, cell_format)


def layout_sheet(
    worksheet: Any,
    *,
    header_row: int,
    row_count: int,
    column_count: int,
    widths: Sequence[int],
) -> None:
    """Muzlatish, filtr va ustun kengliklari — VARAQ GEOMETRIYASINING YAGONA joyi.

    =======================================================================
    ⛔ `freeze_panes(header_row + 1, 0)` — DAVR VA SARLAVHA IKKALASI HAM
       MUZLATILADI.

    Reja `freeze_panes(1, 0)` degan edi, lekin AYNI reja davrni
    1-QATORGA qo'yishni ham buyuradi. `1` bilan faqat davr muzlardi va
    sarlavha skrollda yo'qolardi — 30 000 qatorli nomuvofiqlik arxivida
    direktor «qaysi ustun nima?» degan savolga javobsiz qolardi
    (`constant_memory` taqiqining aynan sababi, modul docstringi).
    =======================================================================

    ⚠ `autofilter` diapazoni kamida BIR qatorni qamraydi: bo'sh hisobotda
      `max(row_count, 1)` bo'lmasa filtr sarlavhaning O'ZIGA tushardi va
      Excel uni ochmasdi (`xlsx_template.build_error_report()` da
      o'rnatilgan naqsh).
    """
    worksheet.freeze_panes(header_row + 1, 0)
    worksheet.autofilter(header_row, 0, header_row + max(row_count, 1), column_count - 1)
    for column, width in enumerate(widths):
        worksheet.set_column(column, column, width)


def finish(workbook: Workbook, buffer: io.BytesIO) -> bytes:
    """Kitobni yopadi va baytlarni muzlatadi — eksportning YAGONA chiqishi.

    `close()` va `freeze_zip()` ni ajratib chaqirish mumkin edi, lekin
    o'shanda yangi eksport marshruti (08-10, 08-16) ikkinchisini
    unutishi mumkin bo'lardi va fayl JIMGINA nodeterminik chiqardi.
    """
    workbook.close()
    return freeze_zip(buffer.getvalue())


# ===========================================================================
# 08-12 — TO'RT HISOBOT HUJJATI (RECON-04 ning `.xlsx` yarmi)
#
# ⛔⛔ 1. DAVR FAYL ICHIDA HAM YOZILADI, FAQAT FAYL NOMIDA EMAS.
#
# `Content-Disposition` dagi nom CHOP ETILGANDA bosilmaydi. Davri
# yo'qolgan varaqdagi raqam hech nimaga bog'lanmagan bo'lib qoladi va u
# imzolanadigan hujjat bo'lib tarqaladi (UI-SPEC §1.2 qoida 2).
# Shuning uchun har hujjatning 1-QATORI — davr.
#
# ⛔⛔ 2. ATAMALAR VEBDAGI BILAN AYNI (D-06 + 07 D-30).
#
# «patta», «rasta», «qarz», «smena» — ⛔ «yig'im»/«do'kon» EMAS.
# Matnlar `frontend/messages/*.json::reports.*` dagi satrlardan
# ko'chirilgan, ya'ni ekran va fayl BIR XIL gapni aytadi. Ikki tomon
# ajralganda direktor «bu ikkalasi bir xil hisobotmi?» degan savolga
# javobsiz qolardi.
#
# ⛔⛔ 3. ARIFMETIKA BU YERDA YO'Q.
#
# `diff_soum` chaqiruvchidan (`api/v1/reports.py`) keladi, foizlar esa
# `accuracy_report.py` dan. Bu qatlam FAQAT joylashtiradi. Qayta hisob
# xato bo'lib emas, IKKINCHI JAVOB bo'lib chiqardi (05-14 darsi).
# ===========================================================================

REPORT_DEFAULT_LOCALE: Final = "uz-Latn"
"""Noma'lum til shu yerga tushadi — istisno KO'TARILMAYDI.

`xlsx_template._texts()` ning aynan qoidasi va aynan sababi: yangi til
qo'shilganda (yoki tokendagi qiymat kutilmagan bo'lsa) hujjatni yuklab
olish 500 bilan tugashi direktorning oqimini butunlay to'sardi, sababi
esa mutlaqo ahamiyatsiz bo'lardi.
"""

_REPORT_TEXTS: Final[dict[str, dict[str, str]]] = {
    "uz-Latn": {
        "period": "Davr",
        "revenue_sheet": "Tushum",
        "revenue_date": "Sana",
        "revenue_paid": "To'langan (so'm)",
        "revenue_charged": "Hisoblangan (so'm)",
        "revenue_diff": "Farq (so'm)",
        "receivables_sheet": "Qarzdorlik ro'yxati",
        "receivables_vendor": "Sotuvchi",
        "receivables_stalls": "Rastalari",
        "receivables_debt": "Qarz (so'm)",
        "receivables_oldest": "Eng eski qarz",
        "discrepancies_sheet": "Nomuvofiqlik arxivi",
        "discrepancies_date": "Sana",
        "discrepancies_kind": "Tur",
        "discrepancies_stall": "Rasta",
        "discrepancies_status": "Holat",
        "discrepancies_evidence": "Dalil kadr",
        "kind_occupied_unpaid": "Band, lekin to'lovsiz",
        "kind_unassigned_occupied": "Ro'yxatga olinmagan savdo",
        "status_new": "Yangi",
        "status_in_review": "Ko'rilmoqda",
        "status_justified": "Asosli",
        "status_unjustified": "Asossiz",
        "accuracy_sheet": "AI aniqlik hisoboti",
        "accuracy_metric": "Ko'rsatkich",
        "accuracy_value": "Qiymat",
        "accuracy_lower": "Quyi chegara",
        "accuracy_upper": "Yuqori chegara",
        "accuracy_drawn": "Namunaga tushgan bandlar",
        "accuracy_answered": "Javob berilgan",
        "accuracy_unanswered": "Javobsiz",
        "accuracy_dont_know": "Aniq ayta olmayman",
        "accuracy_n": "Matritsaga tushgan javoblar",
        "accuracy_tp": "To'g'ri: band",
        "accuracy_fp": "Xato: band deb aytilgan",
        "accuracy_fn": "Xato: bo'sh deb aytilgan",
        "accuracy_tn": "To'g'ri: bo'sh",
        "accuracy_base_rate": "Bazaviy bandlik ulushi",
        "accuracy_correct": "To'g'ri javob ulushi",
        "accuracy_false_occupied": "Band deb xato ulushi",
        "accuracy_false_empty": "Bo'sh deb xato ulushi",
        "accuracy_disclaimer": (
            "Bu ulush nazoratchining ko'r javoblaridan hisoblanadi. "
            "Modelning o'zi avtomatik sinovda o'lchanmagan."
        ),
    },
    "uz-Cyrl": {
        "period": "Давр",
        "revenue_sheet": "Тушум",
        "revenue_date": "Сана",
        "revenue_paid": "Тўланган (сўм)",
        "revenue_charged": "Ҳисобланган (сўм)",
        "revenue_diff": "Фарқ (сўм)",
        "receivables_sheet": "Қарздорлик рўйхати",
        "receivables_vendor": "Сотувчи",
        "receivables_stalls": "Расталари",
        "receivables_debt": "Қарз (сўм)",
        "receivables_oldest": "Энг эски қарз",
        "discrepancies_sheet": "Номувофиқлик архиви",
        "discrepancies_date": "Сана",
        "discrepancies_kind": "Тур",
        "discrepancies_stall": "Раста",
        "discrepancies_status": "Ҳолат",
        "discrepancies_evidence": "Далил кадр",
        "kind_occupied_unpaid": "Банд, лекин тўловсиз",
        "kind_unassigned_occupied": "Рўйхатга олинмаган савдо",
        "status_new": "Янги",
        "status_in_review": "Кўрилмоқда",
        "status_justified": "Асосли",
        "status_unjustified": "Асоссиз",
        "accuracy_sheet": "АИ аниқлик ҳисоботи",
        "accuracy_metric": "Кўрсаткич",
        "accuracy_value": "Қиймат",
        "accuracy_lower": "Қуйи чегара",
        "accuracy_upper": "Юқори чегара",
        "accuracy_drawn": "Намунага тушган бандлар",
        "accuracy_answered": "Жавоб берилган",
        "accuracy_unanswered": "Жавобсиз",
        "accuracy_dont_know": "Аниқ айта олмайман",
        "accuracy_n": "Матрицага тушган жавоблар",
        "accuracy_tp": "Тўғри: банд",
        "accuracy_fp": "Хато: банд деб айтилган",
        "accuracy_fn": "Хато: бўш деб айтилган",
        "accuracy_tn": "Тўғри: бўш",
        "accuracy_base_rate": "Базавий бандлик улуши",
        "accuracy_correct": "Тўғри жавоб улуши",
        "accuracy_false_occupied": "Банд деб хато улуши",
        "accuracy_false_empty": "Бўш деб хато улуши",
        "accuracy_disclaimer": (
            "Бу улуш назоратчининг кўр жавобларидан ҳисобланади. "
            "Моделнинг ўзи автоматик синовда ўлчанмаган."
        ),
    },
    "ru": {
        "period": "Период",
        "revenue_sheet": "Выручка",
        "revenue_date": "Дата",
        "revenue_paid": "Оплачено (сум)",
        "revenue_charged": "Начислено (сум)",
        "revenue_diff": "Разница (сум)",
        "receivables_sheet": "Реестр долгов",
        "receivables_vendor": "Продавец",
        "receivables_stalls": "Прилавки",
        "receivables_debt": "Долг (сум)",
        "receivables_oldest": "Самый старый долг",
        "discrepancies_sheet": "Архив расхождений",
        "discrepancies_date": "Дата",
        "discrepancies_kind": "Тип",
        "discrepancies_stall": "Прилавок",
        "discrepancies_status": "Статус",
        "discrepancies_evidence": "Кадр-доказательство",
        "kind_occupied_unpaid": "Занято, но без оплаты",
        "kind_unassigned_occupied": "Незарегистрированная торговля",
        "status_new": "Новое",
        "status_in_review": "На рассмотрении",
        "status_justified": "Обоснованное",
        "status_unjustified": "Необоснованное",
        "accuracy_sheet": "Отчёт о точности ИИ",
        "accuracy_metric": "Показатель",
        "accuracy_value": "Значение",
        "accuracy_lower": "Нижняя граница",
        "accuracy_upper": "Верхняя граница",
        "accuracy_drawn": "Заданий в выборке",
        "accuracy_answered": "С ответом",
        "accuracy_unanswered": "Без ответа",
        "accuracy_dont_know": "Не могу сказать точно",
        "accuracy_n": "Ответов в матрице",
        "accuracy_tp": "Верно: занято",
        "accuracy_fp": "Ошибка: назвали занятым",
        "accuracy_fn": "Ошибка: назвали свободным",
        "accuracy_tn": "Верно: свободно",
        "accuracy_base_rate": "Базовая доля занятости",
        "accuracy_correct": "Доля верных ответов",
        "accuracy_false_occupied": "Доля ошибок «занято»",
        "accuracy_false_empty": "Доля ошибок «свободно»",
        "accuracy_disclaimer": (
            "Эта доля считается по слепым ответам контролёра. "
            "Сама модель в автоматических тестах не измерялась."
        ),
    },
}
"""Hujjat matnlari — ⛔ SERVERDA, `xlsx_template._TEXTS` NING AYNAN NAQSHI.

⚠ Bu 1-faza D-16 («DB kontenti bitta tilda») ga ZID EMAS: bular DB
  kontenti emas, hosil qilinadigan HUJJATNING matni va u serverda
  tug'iladi.

⛔ UCH TILNING KALIT TO'PLAMI TENG bo'lishi SHART va u
  `test_every_locale_translates_every_report_key` bilan qulflangan:
  yarim tarjima `dict.get()` ostida JIMGINA bo'sh sarlavha berardi.
"""

_KIND_TEXT_KEYS: Final[dict[str, str]] = {
    ReconciliationSubjectKind.OCCUPIED_UNPAID.value: "kind_occupied_unpaid",
    AnomalyKind.UNASSIGNED_OCCUPIED.value: "kind_unassigned_occupied",
}
"""Arxiv sinfi -> matn kaliti. ⛔ Kalitlar ENUMDAN, satr literalidan EMAS.

`report_repo.ARCHIVE_KIND_*` ham aynan shu ikki a'zodan quriladi, ya'ni
enum qiymati o'zgarsa ikkala tomon BIRGA siljiydi va hujjatda
tarjimasiz xom `occupied_unpaid` paydo bo'lmaydi.
"""

_STATUS_TEXT_KEYS: Final[dict[str, str]] = {
    ReconciliationCaseStatus.NEW.value: "status_new",
    ReconciliationCaseStatus.IN_REVIEW.value: "status_in_review",
    ReconciliationCaseStatus.JUSTIFIED.value: "status_justified",
    ReconciliationCaseStatus.UNJUSTIFIED.value: "status_unjustified",
}
"""Case holati -> matn kaliti (YOPIQ TO'RT A'ZO, D-12)."""


@dataclass(frozen=True, slots=True)
class ReportPeriod:
    """Hujjatning davri — ⛔ IKKALA CHEGARA HAM MAJBURIY.

    Standart qiymat ATAYIN yo'q: davrsiz hujjat imzolanadigan varaqda
    «qaysi davr?» savolini javobsiz qoldirardi (UI-SPEC §1.2 qoida 2) va
    `api/v1/reports.py::FromDateDep` ham aynan shu sababdan majburiy.
    """

    from_date: date
    to_date: date

    @property
    def label(self) -> str:
        """`2026-08-01 — 2026-08-07` — ⛔ EM TIRE (U+2014) bilan.

        `frontend/messages/*.json::reports.periodShown` AYNAN shu
        belgini ishlatadi (`'{from} — {to}'`). Sana ISO shaklda va u
        UCHALA TILDA BIR XIL: lokalizatsiyalangan sana formati
        («7 avgust») faylni saralab bo'lmaydigan qilardi va uch tilda uch
        xil hujjat berardi.
        """
        return f"{self.from_date.isoformat()} — {self.to_date.isoformat()}"


def report_texts(locale: str) -> dict[str, str]:
    """Til uchun hujjat matnlari; noma'lum til `REPORT_DEFAULT_LOCALE` ga tushadi."""
    return _REPORT_TEXTS.get(locale, _REPORT_TEXTS[REPORT_DEFAULT_LOCALE])


def _enum_label(texts: dict[str, str], keys: dict[str, str], value: str) -> str:
    """Yopiq to'plam a'zosining matni; NOMA'LUM qiymat XOM holda qaytadi.

    ⛔ ISTISNO KO'TARILMAYDI va o'rin to'ldiruvchi ham yozilmaydi:
       sxemaga yangi a'zo qo'shilganda hujjatni yuklab olish 500 bilan
       tugashi butun oqimni to'sardi, «Noma'lum» esa MA'LUMOT bordek
       ko'rinib, chop etilgan varaqda haqiqiy holat bo'lib o'qilardi.
       Xom qiymat esa halol: u tarjima yetishmasligini KO'RSATADI.
    """
    key = keys.get(value)
    return value if key is None else texts[key]


def _open_report(locale: str, sheet_key: str, period: ReportPeriod) -> tuple[Any, Any, Any, Any]:
    """Kitob + varaq + davr qatori — to'rtala hujjatning UMUMIY boshi.

    Returns:
        `(workbook, worksheet, buffer, texts)`.

    ⚠ Nusxa YOZILMAYDI: to'rt quruvchida to'rt marta takrorlangan
      «kitobni och, varaq qo'sh, davrni yoz» ketma-ketligi bir kun
      uchtasida yangilanib, to'rtinchisida qolib ketardi — va aynan
      o'sha to'rtinchisi davri yo'qolgan hujjat bo'lardi.
    """
    texts = report_texts(locale)
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    worksheet = workbook.add_worksheet(texts[sheet_key])
    banner = workbook.add_format({"bold": True})
    write_text(worksheet, 0, 0, f"{texts['period']}: {period.label}", banner)
    return workbook, worksheet, buffer, texts


def build_revenue_workbook(
    rows: Sequence[RevenueReportRow],
    locale: str,
    period: ReportPeriod,
) -> bytes:
    """Davr tushumi — kunlik qatorlar, ⛔ PUL SON BO'LIB (§8.2).

    ⛔ `diff_soum` CHAQIRUVCHIDAN keladi va bu yerda QAYTA
       HISOBLANMAYDI (D-03): ayirish serverda BIR joyda bajariladi va
       ekran bilan fayl bir xil sonni ko'rsatadi.

    ⚠ UCHINCHI, «yagona tushum» USTUNI YO'Q (`report_repo.RevenueRow`,
      T-08-15): ikki sonni bittaga siqish nizoda «qaysi raqamni
      aytdingiz?» savolini tug'dirardi.
    """
    workbook, worksheet, buffer, texts = _open_report(locale, "revenue_sheet", period)
    try:
        header = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        money = money_format(workbook)

        write_header(
            worksheet,
            1,
            (
                texts["revenue_date"],
                texts["revenue_paid"],
                texts["revenue_charged"],
                texts["revenue_diff"],
            ),
            header,
        )
        for offset, row in enumerate(rows, start=2):
            # ⛔ SANA MATN VA ISO: `write_money` faqat pul uchun, sana esa
            #    uchala tilda BIR XIL shaklda qolishi kerak.
            write_text(worksheet, offset, 0, row.business_date.isoformat())
            write_money(worksheet, offset, 1, row.collected_soum, money)
            write_money(worksheet, offset, 2, row.charged_soum, money)
            write_money(worksheet, offset, 3, row.diff_soum, money)

        layout_sheet(
            worksheet,
            header_row=1,
            row_count=len(rows),
            column_count=4,
            widths=(14, 20, 20, 20),
        )
    except BaseException:
        # `xlsx_template.build_template()` dagi bilan AYNI sabab: yopilmagan
        # `Workbook` vaqtinchalik fayllarni ushlab qolardi.
        workbook.close()
        raise
    return finish(workbook, buffer)


def build_receivables_workbook(
    rows: Sequence[ReceivablesReportRow],
    locale: str,
    period: ReportPeriod,
) -> bytes:
    """Qarzdorlik reestri — ⛔ ISMLI HUJJAT, ya'ni FORMULA XAVFI SHU YERDA.

    =======================================================================
    ⛔ `vendor_name` TASHQI MATN: uni `=HYPERLINK(...)` deb yozgan
       sotuvchi DIREKTORNING mashinasida kod bajartirardi (T-08-48).
       Yagona matn yo'li — `write_text`/`write_optional_text`, ular esa
       `escape_formula()` dan o'tadi.
    =======================================================================

    ⛔ ISM `None` BO'LSA BO'SH KATAK (D-08): na «—», na «Noma'lum», na
       «Sotuvchi #123». Chop etilgan varaqda o'rin to'ldiruvchi
       buxgalter uchun HAQIQIY nom bo'lib o'qilardi.

    ⛔ `phone` USTUNI YO'Q va qo'shilmaydi (UI-SPEC O-03): telefon —
       ALOQA ma'lumoti va u aynan shu fayl orqali tarqalardi.
    """
    workbook, worksheet, buffer, texts = _open_report(locale, "receivables_sheet", period)
    try:
        header = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        money = money_format(workbook)

        write_header(
            worksheet,
            1,
            (
                texts["receivables_vendor"],
                texts["receivables_stalls"],
                texts["receivables_debt"],
                texts["receivables_oldest"],
            ),
            header,
        )
        for offset, row in enumerate(rows, start=2):
            write_optional_text(worksheet, offset, 0, row.vendor_name)
            # ⚠ Ro'yxat SHU YERDA yopishtiriladi: repo uni `code_sort`
            #   tartibida bergan va tartib SAQLANADI.
            write_text(worksheet, offset, 1, ", ".join(row.stall_codes))
            write_money(worksheet, offset, 2, row.outstanding_soum, money)
            write_optional_text(
                worksheet,
                offset,
                3,
                None if row.oldest_debt_date is None else row.oldest_debt_date.isoformat(),
            )

        layout_sheet(
            worksheet,
            header_row=1,
            row_count=len(rows),
            column_count=4,
            widths=(32, 24, 18, 18),
        )
    except BaseException:
        workbook.close()
        raise
    return finish(workbook, buffer)


def build_discrepancies_workbook(
    rows: Sequence[AnomalyArchiveRowResponse],
    locale: str,
    period: ReportPeriod,
) -> bytes:
    """Nomuvofiqlik arxivi — ⛔ DALIL IDENTIFIKATOR, KADR EMAS (07 D-03).

    =======================================================================
    ⛔ RASM, IMZOLANGAN HAVOLA VA OMBOR KALITI HUJJATGA TUSHMAYDI
       (T-06-81). Faqat `snapshot_id`. Kadr baytini `.xlsx` ga qo'yish
       dalil-kadr yuzasini pochta ilovasiga aylantirardi — u yerda
       birorta huquq darvozasi ishlamaydi.
    =======================================================================

    ⛔ UCHINCHI, «yig'indi» USTUNI YO'Q (D-05): «band, lekin to'lovsiz»
       UNDIRISHNI, «ro'yxatga olinmagan savdo» esa RO'YXATGA OLISHNI
       talab qiladi va bitta songa siqilgan hisobot qaysi sinf
       o'sganini yashirardi. Sinflar ustun bo'lib qoladi va Excel
       filtri ularni ajratadi.
    """
    workbook, worksheet, buffer, texts = _open_report(locale, "discrepancies_sheet", period)
    try:
        header = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})

        write_header(
            worksheet,
            1,
            (
                texts["discrepancies_date"],
                texts["discrepancies_kind"],
                texts["discrepancies_stall"],
                texts["discrepancies_status"],
                texts["discrepancies_evidence"],
            ),
            header,
        )
        for offset, row in enumerate(rows, start=2):
            write_text(worksheet, offset, 0, row.business_date.isoformat())
            write_text(worksheet, offset, 1, _enum_label(texts, _KIND_TEXT_KEYS, row.kind))
            write_text(worksheet, offset, 2, row.stall_code)
            # ⛔ `None` = case hali OCHILMAGAN, «noma'lum» EMAS -> BO'SH katak.
            write_optional_text(
                worksheet,
                offset,
                3,
                None
                if row.case_status is None
                else _enum_label(texts, _STATUS_TEXT_KEYS, row.case_status),
            )
            write_optional_text(
                worksheet,
                offset,
                4,
                None if row.snapshot_id is None else str(row.snapshot_id),
            )

        layout_sheet(
            worksheet,
            header_row=1,
            row_count=len(rows),
            column_count=5,
            widths=(14, 28, 14, 18, 38),
        )
    except BaseException:
        workbook.close()
        raise
    return finish(workbook, buffer)


def build_accuracy_workbook(
    report: AccuracyReport,
    locale: str,
    period: ReportPeriod,
) -> bytes:
    """AI aniqlik hisoboti — ⛔ IKKI XATO TURI IKKI ALOHIDA QATORDA.

    =======================================================================
    ⛔⛔ «BAND DEB XATO» (`fp/(tp+fp)`) VA «BO'SH DEB XATO»
        (`fn/(tp+fn)`) BITTA «XATOLIK ULUSHI» GA QO'SHILMAYDI (D-09).

    Ularning MAXRAJLARI ham boshqa (`accuracy_report` modul
    docstringi) va MA'NOLARI ham: birinchisi SOTUVCHI BILAN NIZO
    xavfi, ikkinchisi YIG'ILMAGAN PATTA. Yagona songa siqilgan hisobot
    direktorga «nima qilish kerak?» degan savolga javob bermasdi.

    ⛔ FORMULALAR `accuracy_report.py` DAN KELADI VA QAYTA
       HISOBLANMAYDI: bu qatlam `report.false_occupied.point` ni
       KO'CHIRADI, `fp/(tp+fp)` ni O'ZI yozmaydi. Ikkinchi hisob
       arifmetik jihatdan to'g'ri bo'lib turib BOSHQA savolga javob
       berardi (05-14 darsi).

    ⛔⛔ `measured is False` DA FOIZ KATAKLARI BO'SH — `0` EMAS (D-10,
        T-08-53). O'lchanmagan nolni chop etilgan varaqqa yozish
        «tizim hech qachon xato qilmaydi» degan O'LCHANGAN da'vo
        bo'lardi (T-05-04).

    ⛔⛔ AI-02 HOLATI JUMLASI MAJBURIY VA SHARTSIZ (D-11, UI-SPEC §9.4)
        — `measured` dan MUSTAQIL. Aynan O'LCHANGAN foiz «model
        sinovdan o'tgan» degan xulosaga olib boradi, varaq esa
        kontekstsiz tarqaladi va uni o'qigan odam savol bera olmaydi.
    =======================================================================
    """
    workbook, worksheet, buffer, texts = _open_report(locale, "accuracy_sheet", period)
    try:
        header = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        count = workbook.add_format({"num_format": COUNT_NUM_FORMAT})
        percent = workbook.add_format({"num_format": PERCENT_NUM_FORMAT})

        write_header(
            worksheet,
            1,
            (
                texts["accuracy_metric"],
                texts["accuracy_value"],
                texts["accuracy_lower"],
                texts["accuracy_upper"],
            ),
            header,
        )

        counts: tuple[tuple[str, int], ...] = (
            (texts["accuracy_drawn"], report.drawn),
            (texts["accuracy_answered"], report.answered),
            (texts["accuracy_unanswered"], report.unanswered),
            (texts["accuracy_dont_know"], report.dont_know),
            (texts["accuracy_n"], report.n),
            (texts["accuracy_tp"], report.matrix.tp),
            (texts["accuracy_fp"], report.matrix.fp),
            (texts["accuracy_fn"], report.matrix.fn),
            (texts["accuracy_tn"], report.matrix.tn),
        )
        # ⛔ XOM SONLAR `measured` DAN QAT'I NAZAR QAYTADI: o'lchov
        #    boshlangan va uning HAJMI ko'rsatilishi kerak
        #    (`accuracy_report()` ning aynan qarori). Yashiriladigan
        #    narsa — FOIZ, sanoq emas.
        for offset, (label, value) in enumerate(counts, start=2):
            write_text(worksheet, offset, 0, label)
            write_optional_number(worksheet, offset, 1, value, count)

        shares: tuple[tuple[str, float | None, float | None, float | None], ...] = (
            # ⛔ BAZAVIY ULUSH ORALIQSIZ: `accuracy_report` uni nuqta baho
            #    sifatida beradi va bu yerda oraliq O'YLAB TOPILMAYDI.
            (texts["accuracy_base_rate"], report.base_rate, None, None),
            (
                texts["accuracy_correct"],
                report.correct.point,
                report.correct.lower,
                report.correct.upper,
            ),
            (
                texts["accuracy_false_occupied"],
                report.false_occupied.point,
                report.false_occupied.lower,
                report.false_occupied.upper,
            ),
            (
                texts["accuracy_false_empty"],
                report.false_empty.point,
                report.false_empty.lower,
                report.false_empty.upper,
            ),
        )
        for offset, (label, point, lower, upper) in enumerate(shares, start=2 + len(counts)):
            write_text(worksheet, offset, 0, label)
            write_optional_number(worksheet, offset, 1, point, percent)
            write_optional_number(worksheet, offset, 2, lower, percent)
            write_optional_number(worksheet, offset, 3, upper, percent)

        metric_rows = len(counts) + len(shares)
        # ⚠ Jumla FILTR DIAPAZONIDAN TASHQARIDA va oradan bir qator
        #   tashlab yoziladi: filtr ichidagi izoh saralashda ma'lumot
        #   qatori bo'lib yuqoriga chiqib ketardi.
        write_text(worksheet, 2 + metric_rows + 1, 0, texts["accuracy_disclaimer"])

        layout_sheet(
            worksheet,
            header_row=1,
            row_count=metric_rows,
            column_count=4,
            widths=(34, 16, 16, 16),
        )
    except BaseException:
        workbook.close()
        raise
    return finish(workbook, buffer)
