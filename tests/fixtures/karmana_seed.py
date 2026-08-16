"""Karmana MIQYOSIDAGI iflos import datasetining generatori (test fixture'i + CLI).

=============================================================================
BU MODUL `app.services.xlsx_template` NI IMPORT QILMAYDI VA
`GET /api/v1/imports/template` NI CHAQIRMAYDI. BU — MODULNING BUTUN MA'NOSI.

`02-VERIFICATION.md` (2026-08-01) import yo'lini «HOLLOW (Level 4)» deb
belgiladi va sababini aniq yozdi:

    "Import yo'li faqat o'z-o'ziga qaytadigan shablon fayli bilan
     sinalgan"  ...  Data-Flow Trace: `✗ DISCONNECTED`.

Tanqid HUJJATNING YO'QLIGI haqida EMAS. U shu haqda: **quvur hech qachon
o'zi ishlab chiqarmagan ma'lumotni ko'tarmagan edi**. Yuk shablon
generatoridan kelsa, o'lchov yana o'z-o'ziga qaytadi va tanqid kuchida
qoladi — fayl 600 qatorli bo'lsa ham.

Shuning uchun bu modul ustunlar tartibini FAQAT `ops/data/karmana/README.md`
§3 dagi HUJJATLASHTIRILGAN jadvaldan biladi (ya'ni ma'muriyat o'z faylini
qanday tersa, xuddi shunday), qolgan hamma narsani o'zi to'qiydi.

⚠ KEYINGI O'QUVCHIGA: «shablon endpointidan foydalansak qisqaroq bo'lardi»
degan fikr TO'G'RI, lekin u darvozani JIMGINA bekor qiladi. Shablonni
ishlatish taqiqlangan; taqiq `tests/unit/test_karmana_seed.py::
test_generator_does_not_import_the_template_module` bilan MANBA MATNI
darajasida qulflangan (T-02-165).
=============================================================================

BU «SINTETIK MA'LUMOT YARATISH» EMAS. Yaratilayotgani ma'muriyatning
RAQAMLARI emas — quvurga beriladigan YUK. U aynan quvurni o'lchash uchun
mavjud. Ma'muriyatning haqiqiy raqamlari kelganda ular saytning o'zidan
yuklanadi (`ops/data/karmana/README.md` — operatsion tartib), va bu faza
darvozasi emas.

-----------------------------------------------------------------------------
DETERMINIZM MAJBURIY VA U IKKI QATLAMDA TA'MINLANADI.

1. `random.Random(SEED)` — har chaqiruvda YANGI generator, modul darajasida
   umumiy holat YO'Q. Qizargan test qayta tiklanadigan bo'lishi shart, aks
   holda «gohida yiqiladi» degan eng yomon test turi tug'iladi.
2. ZIP metama'lumoti QAYTA YOZILADI (`xlsx_export.freeze_zip`).
   `XlsxWriter` `ZipFile.writestr()` ni ishlatadi va u a'zo sanasini
   SOAT'dan oladi — ya'ni ikki qo'shni chaqiruv baytlari sekundlar
   chegarasida FARQ qilardi. Baytlar tengligi da'vosi shu tufayli aniq.

   ⚠ Bu qatlam 08-01 da MAHSULOTGA ko'chirildi va bu yerdan o'chirildi
   (quyidagi izohga qarang). Fikstur uni endi `app.services.xlsx_export`
   dan oladi — bu paketga ruxsat etilgan YAGONA bog'lanish va u
   `test_karmana_seed.py::test_generator_does_not_import_the_template_
   module` da simvol darajasida qulflangan.
-----------------------------------------------------------------------------

TOZA FAYL — IFLOS FAYLNING FILTRLANGAN KO'RINISHI, IKKINCHI RO'YXAT EMAS.
Ikki alohida ro'yxat bir kun ajralib ketardi va «tuzatilgan fayl o'tadi»
degan da'vo tekshirilmay qolardi. Shuning uchun `_stall_plan()` /
`_vendor_plan()` YAGONA manba: `dirty=False` shunchaki `kind == "issue"`
slotlarini tashlab yuboradi.

KUTILGAN NATIJANI GENERATOR AYTADI, TEST QAYTA HISOBLAMAYDI
(`expected_stall_issues()` / `expected_vendor_issues()` /
`clean_stall_rows()` / `clean_vendor_rows()`). Test validator mantiqini
takrorlasa, ikkalasi birga xato bo'lganda baribir yashil qolardi
(T-02-166).

CLI:
    PYTHONPATH=tests python -m fixtures.karmana_seed \\
        --stalls 600 --vendors 480 --out-dir ops/data/karmana/local
"""

from __future__ import annotations

import argparse
import io
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from app.services.xlsx_export import freeze_zip, new_workbook

__all__ = [
    "KARMANA_CATEGORY_NAMES",
    "KARMANA_OPERATING_SINCE",
    "KARMANA_STALL_COUNT",
    "KARMANA_VENDOR_COUNT",
    "KARMANA_ZONE_COUNT",
    "KARMANA_ZONE_NAMES",
    "SEED",
    "STALL_COLUMN_ORDER",
    "TRICKY_NUMERIC_CODE_INDEX",
    "VENDOR_COLUMN_ORDER",
    "StallRow",
    "VendorRow",
    "blank_stall_rows",
    "blank_vendor_rows",
    "build_stalls_workbook",
    "build_vendors_workbook",
    "clean_stall_rows",
    "clean_vendor_rows",
    "expected_stall_issues",
    "expected_vendor_issues",
]

# ---------------------------------------------------------------------------
# Miqyos konstantalari
# ---------------------------------------------------------------------------

KARMANA_ZONE_COUNT = 8
"""Zonalar soni. Karmana uchun aniq raqam ma'lum emas; sakkiz — bozorning
qatorlari sonining oqilona o'rtachasi va u FAYL emas, MIQYOS haqidagi
taxmin (ROADMAP self-service qoidasi: real raqam kelganda ustiga qo'yiladi).
"""

KARMANA_STALL_COUNT = 600
"""Rastalar soni. ROADMAP Karmanani `~300–1000 rasta` deb ta'riflaydi; 600 —
o'sha oraliqning o'rtasi. Bitta qatorda (02-17 ning `inserted: 1`) o'lchangan
quvur 600 qatorda boshqacha xulq qilishi mumkin — aynan shuni o'lchaymiz.
"""

KARMANA_VENDOR_COUNT = 480
"""Sotuvchilar soni — rastalarning ~80% i band. Biriktirilmagan rasta D-11
bo'yicha NORMAL holat (u 6-fazada «band, lekin sotuvchisiz» anomaliyasining
manbai), shuning uchun 1:1 nisbat ATAYIN olinmadi.
"""

SEED = 20_260_801
"""`random.Random(SEED)` urug'i — 2026-08-01 (self-service qoidasi sanasi)."""

KARMANA_OPERATING_SINCE: Final = date(2026, 1, 5)
"""Generator quradigan sanalarning pastki chegarasi.

Miqyos testi bozorni AYNAN shu sana bilan yaratadi, ya'ni fayldagi
biriktirish sanalari hech qachon `operating_since` dan oldin bo'lmaydi.
Sana SOBIT (hisoblanmaydi): `market_today` dan hisoblansa fayl baytlari
har kuni o'zgarardi va determinizm testi yiqilardi.
"""

KARMANA_ZONE_NAMES: Final[tuple[str, ...]] = (
    "Markaziy qator",
    "Sharqiy qator",
    "G'arbiy qator",
    "Shimoliy qator",
    "Janubiy qator",
    "Meva-sabzavot rastalari",
    "Kiyim-kechak qatori",
    "Go'sht qatori",
)
"""Sakkizta zona nomi — apostrof va tire BILAN (ular real nomlarda bor va
`.xlsx` / JSON / URL qatlamlarining har birida alohida xulq qiladi)."""

KARMANA_CATEGORY_NAMES: Final[tuple[str, ...]] = (
    "Sabzavot",
    "Meva",
    "Go'sht",
    "Sut mahsulotlari",
    "Kiyim",
    "Xo'jalik mollari",
)

STALL_COLUMN_ORDER: Final[tuple[str, ...]] = ("kod", "zona", "toifa", "holat", "izoh")
"""README §3 dagi rasta ustunlari — GENERATORNING YAGONA TASHQI BILIMI.

Sarlavha MATNI parser uchun ahamiyatsiz (O-05), lekin fayl odam
to'ldiradigan hujjat: sarlavhasiz varaq real dunyoda uchramaydi.
"""

VENDOR_COLUMN_ORDER: Final[tuple[str, ...]] = (
    "F.I.Sh.",
    "telefon",
    "rasta kodi",
    "boshlanish sanasi",
)

_SHUFFLED_STALL_ORDER: Final[tuple[int, ...]] = (1, 2, 3, 4, 0)
"""`column_order="shuffled"` — sarlavhalar TO'G'RI, ustunlar SURILGAN.

Chiqishdagi `j`-ustun hujjatlashtirilgan `_SHUFFLED_STALL_ORDER[j]`-ustunning
qiymatini oladi. Kutilgan natija README §3 da va'da qilingan: parser
POZITSIYA bo'yicha o'qiydi, ya'ni fayl JIMGINA noto'g'ri yozilmaydi —
u 422 bilan RAD ETILADI.
"""

# ⚠ `_FROZEN_ZIP_TIME`, `_FROZEN_CREATED` va `_freeze_zip` BU YERDAN
#   O'CHIRILDI (08-01). Ular endi `app.services.xlsx_export` da — ya'ni
#   MAHSULOTDA — va bu fikstur ularni o'sha yerdan oladi.
#
#   Naqsh shu faylda tug'ilgan edi, lekin uning o'rni bu yer emas:
#   mahsulot eksport yo'llari (`build_template`, `build_error_report`)
#   determinizmsiz qolgan edi, ya'ni "faylimiz determinik" degan da'vo
#   FAQAT test fiksturasiga tegishli bo'lib turardi. Ikki nusxa
#   saqlansa esa sana konstantalari bir kun ajralib ketardi va o'shanda
#   ikki fayl ikki xil "muzlatilgan" holatda chiqardi.
# ---------------------------------------------------------------------------
# Telefon diapazoni — `+998 90 995 xx xx`
# ---------------------------------------------------------------------------

_PHONE_PREFIX: Final = "90995"
"""Sotuvchi telefonlarining milliy prefiksi.

Mavjud diapazonlarning BIRORTASIGA tegmaydi (`two_markets` `+99897…`,
`market_domain` `+99890111…`, import testlari `+99890991…`, matritsa
`+99890999…`). Barcha ismlar va raqamlar TO'QIB CHIQARILGAN — real
shaxsning ma'lumoti generatorga UMUMAN kirmaydi (T-02-174).
"""

_VENDOR_NAMES: Final[tuple[str, ...]] = (
    "Aliyev Vali",
    "Алиев Вали",
    "To'lqin O'rinov",
    "Karimova Nodira",
    "Каримова Нодира",
    "Rasulov Sardor",
    "O'ktamov G'ayrat",
    "Ismoilova Zulfiya",
    "Расулов Сардор",
    "Yo'ldoshev Bekzod",
    "G'aniyeva Dilnoza",
    "Тошматов Улуғбек",
)
"""Aralash lotin/kirill F.I.Sh. va apostrofli nomlar.

Karmanada ikkala alifbo ham amalda: yig'uvchi reestrni kirillda, hisobchi
lotinda yuritadi. Fayl ikkalasini ARALASH ko'taradi va bu XATO EMAS —
`vendors.full_name` erkin matn.
"""

_NOTES: Final[tuple[str, ...]] = (
    "",
    "burchakdagi rasta",
    "yo'lak yonida",
    "tarozi bor",
    "soyabon ostida",
)

_MIXED_NOTE: Final = "Тарози бор; o'lchov 2 m — ta'mir kerak"
"""Aralash lotin/kirill VA apostrofli izoh (tricky, xato EMAS)."""

_FORMULA_NOTE: Final = "=1+1 (eski hisob izohi)"
"""`=` bilan boshlanadigan izoh — quvur uni MATN sifatida ko'tarishi shart.

⚠ Bu ATAYIN qochirilmaydi: qochirish EKSPORT tomonining ishi
(`xlsx_template.escape_formula`). Import tomonida `=` bilan boshlangan
matn oddiy izoh va uni rad etish adminni sababsiz to'sardi.
"""

# --- Toza qatorlar ichidagi «tricky» pozitsiyalar (XATO BERMAYDI) ---------
_TRICKY_ZONE_CASE: Final = 4
"""Zona nomi boshqa registrda VA atrofida ortiqcha bo'sh joy bilan."""
_TRICKY_CATEGORY_CASE: Final = 9
"""Toifa nomi BOSH HARFLARDA va ortida bo'sh joy bilan."""
TRICKY_NUMERIC_CODE_INDEX: Final = 14
"""Rasta kodi SON sifatida yozilgan katak (`12` -> `"12"`, `"12.0"` EMAS).

OMMAVIY: birlik testi aynan shu qatorni topib, kodda nuqta YO'QLIGINI
o'lchaydi. Xususiy nom bilan test private atributga bog'lanardi va
qayta nomlash uni jimgina buzardi.
"""
_TRICKY_UPPER_STATUS: Final = 34
"""Holat BOSH HARFLARDA (`ACTIVE`) — registr ahamiyatsiz (README §3)."""
_TRICKY_MIXED_NOTE: Final = 24
_TRICKY_FORMULA_NOTE: Final = 29

_DUPLICATE_SOURCE_INDEX: Final = 2
"""Faylning BOSHIDAGI takroriy kod qaysi toza qatordan olinadi."""


# ---------------------------------------------------------------------------
# Qatorlarning DEKLARATSIYASI
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StallRow:
    """Bitta TOZA rasta qatori.

    `cells` — FAYLGA yoziladigan XOM kataklar (`str` / `int` / `None`).
    Qolgan maydonlar — quvur yozishi KUTILGAN natija. Ikkisi ATAYIN
    ajratilgan: `cells` da zona nomi kichik harflarda bo'lishi mumkin,
    `zone` esa har doim bozordagi HAQIQIY nom.
    """

    code: str
    zone: str
    category: str
    status: str
    note: str
    cells: tuple[object | None, ...]


@dataclass(frozen=True, slots=True)
class VendorRow:
    """Bitta TOZA sotuvchi qatori.

    `stall_code` `None` — sotuvchi rastasiz reestrga tushadi (D-11, xato
    EMAS). `phone` — KUTILGAN E.164; `cells[1]` esa fayldagi XOM shakl va
    ular ATAYIN har xil.
    """

    full_name: str
    phone: str
    stall_code: str | None
    from_date: date | None
    cells: tuple[object | None, ...]


@dataclass(frozen=True, slots=True)
class _Slot:
    """Fayl rejasidagi bitta o'rin.

    `kind`:
      `"clean"` — `index` bo'yicha toza qator;
      `"blank"` — formatlangan, LEKIN BO'SH qator (Excel eksportida odatiy);
      `"issue"` — ataylab buzilgan qator, kutilgan kodi `issue` da.
    """

    kind: str
    index: int = 0
    issue: str = ""
    variant: int = 0


def _clean(index: int) -> _Slot:
    return _Slot(kind="clean", index=index)


def _blank() -> _Slot:
    return _Slot(kind="blank")


def _issue(code: str, variant: int = 0) -> _Slot:
    return _Slot(kind="issue", issue=code, variant=variant)


def _apply(base: list[_Slot], inserts: list[tuple[int, _Slot]]) -> list[_Slot]:
    """Qo'shimcha slotlarni TOZA ro'yxatning berilgan o'rinlariga qo'yadi.

    Kiritish OXIRIDAN boshlanadi: aks holda birinchi kiritishdan keyingi
    barcha pozitsiyalar bir birlikka surilib, reja o'qilmaydigan bo'lardi.
    Pozitsiyalar shuning uchun HAR DOIM sof toza ro'yxat bo'yicha
    o'qiladi.
    """
    slots = list(base)
    for position, slot in sorted(inserts, key=lambda item: item[0], reverse=True):
        slots.insert(position, slot)
    return slots


def _stall_plan(count: int) -> list[_Slot]:
    """Rasta faylining reja — TOZA va IFLOS variantlarning YAGONA manbai.

    Pozitsiyalar zona/toifa NOMLARIDAN mustaqil, ya'ni
    `expected_stall_issues()` bozorni bilmasdan ham qator raqamlarini
    ayta oladi.
    """
    inserts: list[tuple[int, _Slot]] = [
        # Faylning BOSHIDAGI takroriy kod.
        (6, _issue("duplicate_code_in_file", variant=0)),
        (12, _blank()),
        (18, _issue("zone_not_found")),
        (24, _issue("category_not_found")),
        # 02-17 deviatsiya #1: README ilgari `repair` deb yozgan edi,
        # manba esa `maintenance` beradi. Yo'riqnomaga ergashgan admin
        # AYNAN shu xatoni qiladi — test uni ko'rsatadi.
        (30, _issue("invalid_status")),
        (36, _issue("empty_code")),
        # Ikkinchi bo'sh qator MIQYOSGA nisbatan joylashadi (faylning
        # ~uchdan ikki qismida), sobit `300` bilan EMAS: kichik miqyosda
        # sobit qiymat qatorni faylning OXIRIGA surib yuborardi va
        # «bo'sh qator raqamni surmaydi» da'vosi o'lchanmay qolardi —
        # oxirgi qatordan keyingi bo'shliq umuman ko'rinmaydi.
        (max(1, count * 2 // 3), _blank()),
        # Faylning OXIRIDAGI takroriy kod: guruhlash xatosi faqat
        # qo'shni qatorlarda ishlaganda ham darvoza yashil qolardi.
        (count, _issue("duplicate_code_in_file", variant=1)),
    ]
    return _apply([_clean(index) for index in range(count)], inserts)


def _vendor_plan(count: int) -> list[_Slot]:
    """Sotuvchi faylining rejasi (`_stall_plan` bilan bir xil qoida)."""
    inserts: list[tuple[int, _Slot]] = [
        (5, _issue("duplicate_phone_in_file")),
        (11, _blank()),
        (17, _issue("invalid_phone")),
        # `variant` — zaxira telefon raqamining indeksi. Har xatoli qator
        # O'Z raqamini olishi SHART: bitta raqamni ikki qatorda ishlatish
        # ularga QO'SHIMCHA `duplicate_phone_in_file` xatosini qo'shardi va
        # `{qator: kod}` xaritasi bir qiymatli bo'lmasdi.
        (23, _issue("row_too_short", variant=1)),
        (29, _issue("stall_not_found", variant=2)),
        (count, _issue("duplicate_code_in_file", variant=3)),
    ]
    return _apply([_clean(index) for index in range(count)], inserts)


def _excel_row(position: int) -> int:
    """Rejadagi o'rindan EXCEL qator raqami (sarlavha — 1-qator)."""
    return position + 2


def expected_stall_issues(count: int = KARMANA_STALL_COUNT) -> dict[int, str]:
    """`{Excel qator raqami: xato kodi}` — IFLOS rasta fayli uchun.

    Bu — generatorning E'LONI. Test uni QAYTA HISOBLAMAYDI va validator
    mantiqini takrorlamaydi: solishtiruv IKKI TOMONLAMA tenglik bo'lgani
    uchun kutilmagan xato ham, yetishmagan xato ham nomuvofiqlik
    (T-02-166).
    """
    return {
        _excel_row(position): slot.issue
        for position, slot in enumerate(_stall_plan(count))
        if slot.kind == "issue"
    }


def expected_vendor_issues(count: int = KARMANA_VENDOR_COUNT) -> dict[int, str]:
    """`{Excel qator raqami: xato kodi}` — IFLOS sotuvchi fayli uchun."""
    return {
        _excel_row(position): slot.issue
        for position, slot in enumerate(_vendor_plan(count))
        if slot.kind == "issue"
    }


def blank_stall_rows(count: int = KARMANA_STALL_COUNT) -> set[int]:
    """IFLOS rasta faylidagi BO'SH qatorlarning Excel raqamlari.

    Ular xato EMAS va o'tkazib yuboriladi, LEKIN keyingi qatorlarning
    raqamini SURMAYDI — `xlsx_reader._iter_rows()` ning kafolati aynan
    shu va u shu to'plam bilan o'lchanadi.
    """
    return {
        _excel_row(position)
        for position, slot in enumerate(_stall_plan(count))
        if slot.kind == "blank"
    }


def blank_vendor_rows(count: int = KARMANA_VENDOR_COUNT) -> set[int]:
    """IFLOS sotuvchi faylidagi bo'sh qatorlarning Excel raqamlari."""
    return {
        _excel_row(position)
        for position, slot in enumerate(_vendor_plan(count))
        if slot.kind == "blank"
    }


# ---------------------------------------------------------------------------
# Toza qatorlar
# ---------------------------------------------------------------------------


def _resolved_status(index: int) -> str:
    """Toza qatorning KUTILGAN holati.

    Taqsimot MODULAR (tasodifiy emas): README §7 ning «holat bo'yicha
    taqsimot» bandi test assertion'iga aylanadi va u qayta hisoblanadigan
    emas, DEKLARATSIYA bo'lishi kerak.

    `closed` birinchi tekshiriladi: ikkala shart ham to'g'ri kelgan
    qatorda «yopiq» kuchliroq ma'no beradi.
    """
    if index % 97 == 3:
        return "closed"
    if index % 41 == 7:
        return "maintenance"
    return "active"


def clean_stall_rows(
    zones: tuple[str, ...] = KARMANA_ZONE_NAMES,
    categories: tuple[str, ...] = KARMANA_CATEGORY_NAMES,
    count: int = KARMANA_STALL_COUNT,
) -> list[StallRow]:
    """`count` ta TOZA rasta qatori — fayl va kutilma uchun YAGONA manba.

    Kodlar `1 … count`: matn tartibi (`"10" < "2"`) bilan inson-raqamli
    tartib (`2 < 10`) 600 qatorda ATAYIN keskin farq qiladi, ya'ni
    `code_sort` ishlamaganda xarita tartibi darhol ko'rinadi.

    Zona va toifa AYLANMA taqsimlanadi — bitta zonaga jamlansa «zona
    bo'yicha taqsimot» da'vosi hech nimani ajratmasdi.
    """
    # S311: bu KRIPTOGRAFIYA emas — bu TAKRORLANADIGAN test yuki.
    # `secrets` bu yerda zararli bo'lardi: u har chaqiruvda boshqa fayl
    # berib, «gohida yiqiladigan» testni tug'dirardi (T-02-172).
    rng = random.Random(SEED)  # noqa: S311
    rows: list[StallRow] = []

    for index in range(count):
        code = str(index + 1)
        zone = zones[index % len(zones)]
        category = categories[index % len(categories)]
        status = _resolved_status(index)
        note = _NOTES[rng.randrange(len(_NOTES))]

        raw_code: object = code
        raw_zone = zone
        raw_category = category
        # Bo'sh holat katagi -> `active` (A4). Har 7-qator ATAYIN bo'sh:
        # ustunni to'ldirmagan admin real dunyoda ko'pchilikni tashkil
        # qiladi.
        raw_status: str | None = None if (status == "active" and index % 7 == 3) else status

        if index == _TRICKY_ZONE_CASE:
            raw_zone = f"  {zone.lower()} "
        if index == _TRICKY_CATEGORY_CASE:
            raw_category = f"{category.upper()} "
        if index == TRICKY_NUMERIC_CODE_INDEX:
            raw_code = index + 1
        if index == _TRICKY_UPPER_STATUS:
            raw_status = status.upper()
        if index == _TRICKY_MIXED_NOTE:
            note = _MIXED_NOTE
        if index == _TRICKY_FORMULA_NOTE:
            note = _FORMULA_NOTE

        rows.append(
            StallRow(
                code=code,
                zone=zone,
                category=category,
                status=status,
                note=note,
                cells=(raw_code, raw_zone, raw_category, raw_status, note or None),
            )
        )

    return rows


def _phone_shapes(index: int, national: str) -> object:
    """Bitta milliy raqamning UCH xil yozilish shakli (aylanma).

    Uchalasi ham AYNAN bitta E.164 ga tushishi shart — MARKET-04 ning
    miqyosdagi isboti shu. Shakllar ATAYIN shunday tanlangan:

      0: `+998 90 995 00 03` — `+` bilan va bo'shliqli. ⚠ Bu shakl
         02-24 topgan defektning chegarasi: `+` `FORMULA_PREFIXES` a'zosi
         va shablonning namunaviy qatori aynan shu sababli O'Z importidan
         o'ta olmagan edi. Bu yerda qiymat QOCHIRILMASDAN yoziladi, ya'ni
         chegara haqiqatan bosiladi.
      1: `99890995xxxx` — `+` siz, mamlakat kodi bilan (`libphonenumber`
         uni milliy prefiks sifatida oladi).
      2: `90995xxxx` SON sifatida — Excel raqamli matnni o'zi songa
         aylantiradi va bu real fayllarda eng ko'p uchraydigan shakl.
    """
    if index % 3 == 0:
        return f"+998 {national[:2]} {national[2:5]} {national[5:7]} {national[7:]}"
    if index % 3 == 1:
        return f"998{national}"
    return int(national)


def _vendor_from_date(index: int) -> tuple[date | None, object | None]:
    """Biriktirish sanasining KUTILGAN qiymati va FAYLDAGI xom shakli.

    To'rt shakl ham real fayllarda uchraydi va uchtasi mustaqil
    normallashtirish yo'lini bosadi (`xlsx_reader._cell_text` ning sana
    tarmog'i, `import_validator._parse_date` ning ISO va `dd.mm.yyyy`
    tarmoqlari). To'rtinchisi — BO'SH katak: u `operating_since` ga
    tushadi (README §3) va shuning uchun `None` deb E'LON QILINADI.
    """
    if index % 4 == 0:
        return None, None
    if index % 4 == 1:
        moment = date(2026, 3, 1)
        return moment, moment.isoformat()
    if index % 4 == 2:
        moment = date(2026, 4, 15)
        return moment, "15.04.2026"
    moment = date(2026, 5, 20)
    # HAQIQIY Excel sana katagi (`write_datetime` + sana formati).
    return moment, moment


def clean_vendor_rows(
    stall_codes: tuple[str, ...],
    count: int = KARMANA_VENDOR_COUNT,
) -> list[VendorRow]:
    """`count` ta TOZA sotuvchi qatori.

    Har 40-qator rastasiz qoladi (D-11): sotuvchi reestrga tushadi, lekin
    biriktirilmaydi. Bu XATO EMAS va u ATAYIN datasetda — 6-fazadagi
    «band, lekin sotuvchisiz» anomaliyasi aynan shu holatdan tug'iladi.
    """
    if len(stall_codes) < count:
        raise ValueError(
            f"{count} ta sotuvchi uchun kamida {count} ta rasta kodi kerak "
            f"(berilgani: {len(stall_codes)})"
        )

    rng = random.Random(SEED + 1)  # noqa: S311  # sabab `clean_stall_rows` da
    rows: list[VendorRow] = []

    for index in range(count):
        national = f"{_PHONE_PREFIX}{index:04d}"
        phone = f"+998{national}"
        full_name = _VENDOR_NAMES[rng.randrange(len(_VENDOR_NAMES))]
        stall_code = None if index % 40 == 39 else stall_codes[index]
        from_date, raw_date = _vendor_from_date(index)

        rows.append(
            VendorRow(
                full_name=full_name,
                phone=phone,
                stall_code=stall_code,
                from_date=from_date,
                cells=(full_name, _phone_shapes(index, national), stall_code, raw_date),
            )
        )

    return rows


# ---------------------------------------------------------------------------
# Xatoli qatorlar
# ---------------------------------------------------------------------------


def _dirty_stall_cells(
    slot: _Slot,
    zones: tuple[str, ...],
    categories: tuple[str, ...],
    rows: list[StallRow],
) -> tuple[object | None, ...]:
    """Xatoli rasta qatorining kataklari — HAR BIRIDA AYNAN BITTA nuqson.

    Bitta qatorda ikki nuqson bo'lsa `{qator: kod}` xaritasi bir qiymatli
    bo'lmasdi va ikki tomonlama tenglik da'vosi ma'nosini yo'qotardi.
    """
    zone = zones[0]
    category = categories[0]
    issue = slot.issue

    if issue == "duplicate_code_in_file":
        # Variant 1 faylning OXIRIDA turadi, lekin O'RTADAGI kodni
        # takrorlaydi: qo'shni qatorlarni solishtiradigan soddalashtirilgan
        # dedup (masalan «oldingi qator bilan bir xilmi?») shu holatda
        # DARHOL qizaradi, qo'shni juftlikda esa yashil qolardi.
        source = rows[_DUPLICATE_SOURCE_INDEX] if slot.variant == 0 else rows[len(rows) // 2]
        return (source.code, zone, category, "active", "takroriy kod")
    if issue == "zone_not_found":
        # Imlo xatosi bilan yozilgan zona — eng ko'p uchraydigan sabab.
        return ("9001", f"{zone}a", category, "active", "imlo xatosi")
    if issue == "category_not_found":
        return ("9002", zone, "Yo'q toifa", "active", None)
    if issue == "invalid_status":
        return ("9003", zone, category, "repair", "README 02-17 gacha shunday yozgan edi")
    if issue == "empty_code":
        return (None, zone, category, "active", "kod katagi bo'sh")
    raise AssertionError(f"noma'lum rasta nuqsoni: {issue!r}")


def _dirty_vendor_cells(slot: _Slot, rows: list[VendorRow]) -> tuple[object | None, ...]:
    """Xatoli sotuvchi qatorining kataklari — HAR BIRIDA AYNAN BITTA nuqson."""
    first = rows[0]
    spare = f"{_PHONE_PREFIX}{9000 + slot.variant:04d}"
    issue = slot.issue

    if issue == "duplicate_phone_in_file":
        # ⚠ Takroriy raqam BOSHQA shaklda yozilgan: dedup normallashtirishdan
        # KEYIN bo'lishi shart, aks holda `+998 90 …` va `90 …` ikki xil
        # sotuvchi bo'lib bazaga tushardi.
        return ("Такрор Телефон", first.phone.removeprefix("+998"), None, None)
    if issue == "invalid_phone":
        return ("Yomon Telefon", "12345", None, None)
    if issue == "row_too_short":
        return (None, f"998{spare}", None, None)
    if issue == "stall_not_found":
        return ("Yo'q Rasta", f"998{spare}", "999999", None)
    if issue == "duplicate_code_in_file":
        return ("Ikkinchi Sotuvchi", f"998{spare}", first.stall_code, None)
    raise AssertionError(f"noma'lum sotuvchi nuqsoni: {issue!r}")


# ---------------------------------------------------------------------------
# `.xlsx` yozish
# ---------------------------------------------------------------------------


def _write_workbook(
    sheet_name: str,
    header: tuple[str, ...],
    rows: list[tuple[object | None, ...] | None],
) -> bytes:
    """Sarlavha + qatorlarni `.xlsx` baytlariga aylantiradi.

    `None` qator — FORMATLANGAN, LEKIN BO'SH satr. U formatsiz yozilsa
    `XlsxWriter` katakni umuman chiqarmasdi va qator faylda FIZIK
    mavjud bo'lmasdi; o'shanda «bo'sh qator raqamni surmaydi» da'vosi
    o'quvchi kutubxonasining to'ldirish xulqiga tayanib qolardi. Bu
    yerda esa qator haqiqatan bor — Excel eksportida aynan shunday
    chiqadi.
    """
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    worksheet = workbook.add_worksheet(sheet_name)

    header_format = workbook.add_format({"bold": True})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    blank_format = workbook.add_format({"border": 1})

    for column, title in enumerate(header):
        worksheet.write_string(0, column, title, header_format)

    for offset, values in enumerate(rows, start=1):
        if values is None:
            for column in range(len(header)):
                worksheet.write_blank(offset, column, None, blank_format)
            continue
        for column, value in enumerate(values):
            if value is None:
                continue
            if isinstance(value, date):
                worksheet.write_datetime(offset, column, value, date_format)
            elif isinstance(value, int):
                worksheet.write_number(offset, column, value)
            else:
                worksheet.write_string(offset, column, str(value))

    workbook.close()
    # ⛔ `xlsx_export.finish()` ATAYIN ISHLATILMAYDI: u eksport
    #    MARSHRUTINING yuzasi (yopish + muzlatish), bu yerda esa yozish
    #    tartibi boshqa (matn XOM yoziladi — `_FORMULA_NOTE` ga qarang).
    #    Faqat muzlatish qatlami qayta ishlatiladi.
    return freeze_zip(buffer.getvalue())


def _reorder(
    values: tuple[object | None, ...],
    order: tuple[int, ...],
) -> tuple[object | None, ...]:
    return tuple(values[index] for index in order)


def build_stalls_workbook(
    zones: tuple[str, ...] = KARMANA_ZONE_NAMES,
    categories: tuple[str, ...] = KARMANA_CATEGORY_NAMES,
    count: int = KARMANA_STALL_COUNT,
    *,
    dirty: bool,
    column_order: str = "documented",
) -> bytes:
    """Rasta importi uchun `.xlsx` baytlari.

    `dirty=True` — real dunyodagi nuqsonlar bilan (`expected_stall_issues()`
    ularni AYTADI). `dirty=False` — AYNI fayl, faqat xatoli qatorlarsiz.
    Ikkala variant BITTA rejadan (`_stall_plan`) hosil bo'ladi.

    `column_order="shuffled"` — sarlavhalar to'g'ri, ustunlar surilgan.
    """
    if column_order not in {"documented", "shuffled"}:
        raise ValueError(f"noma'lum ustun tartibi: {column_order!r}")

    rows = clean_stall_rows(zones, categories, count)
    planned: list[tuple[object | None, ...] | None] = []

    for slot in _stall_plan(count):
        if slot.kind == "blank":
            planned.append(None)
        elif slot.kind == "clean":
            planned.append(rows[slot.index].cells)
        elif dirty:
            planned.append(_dirty_stall_cells(slot, zones, categories, rows))

    if column_order == "shuffled":
        planned = [
            None if values is None else _reorder(values, _SHUFFLED_STALL_ORDER)
            for values in planned
        ]

    return _write_workbook("Rastalar", STALL_COLUMN_ORDER, planned)


def build_vendors_workbook(
    stall_codes: tuple[str, ...],
    count: int = KARMANA_VENDOR_COUNT,
    *,
    dirty: bool,
) -> bytes:
    """Sotuvchi importi uchun `.xlsx` baytlari (`build_stalls_workbook` qoidasi)."""
    rows = clean_vendor_rows(stall_codes, count)
    planned: list[tuple[object | None, ...] | None] = []

    for slot in _vendor_plan(count):
        if slot.kind == "blank":
            planned.append(None)
        elif slot.kind == "clean":
            planned.append(rows[slot.index].cells)
        elif dirty:
            planned.append(_dirty_vendor_cells(slot, rows))

    return _write_workbook("Sotuvchilar", VENDOR_COLUMN_ORDER, planned)


# ---------------------------------------------------------------------------
# CLI — quruq mashq (`npm run karmana:sample`)
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fixtures.karmana_seed",
        description=(
            "Karmana miqyosidagi namunaviy import fayllarini quradi. "
            "Real fayl kelishidan OLDIN butun tartibni bir marta bajarib "
            "ko'rish uchun (quruq mashq)."
        ),
    )
    parser.add_argument("--stalls", type=int, default=KARMANA_STALL_COUNT)
    parser.add_argument("--vendors", type=int, default=KARMANA_VENDOR_COUNT)
    parser.add_argument("--out-dir", default="ops/data/karmana/local")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="nuqsonsiz variant (standart holatda fayl ATAYIN iflos)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Namunaviy fayllarni diskka yozadi.

    Chiqish katalogi ATAYIN `ops/data/karmana/local/`: u `.gitignore`
    ostida, ya'ni hosil qilingan `.xlsx` hech qachon git tarixiga
    tushmaydi (T-02-168 — T-02-128 ning davomi).
    """
    args = _parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dirty = not args.clean
    stall_codes = tuple(row.code for row in clean_stall_rows(count=args.stalls))

    stalls_path = out_dir / "stalls.xlsx"
    vendors_path = out_dir / "vendors.xlsx"
    stalls_path.write_bytes(build_stalls_workbook(count=args.stalls, dirty=dirty))
    vendors_path.write_bytes(build_vendors_workbook(stall_codes, count=args.vendors, dirty=dirty))

    kind = "IFLOS" if dirty else "toza"
    print(f"{stalls_path}: {stalls_path.stat().st_size} bayt ({args.stalls} rasta, {kind})")
    print(f"{vendors_path}: {vendors_path.stat().st_size} bayt ({args.vendors} sotuvchi, {kind})")
    if dirty:
        print("Kutilgan rasta xatolari:", expected_stall_issues(args.stalls))
        print("Kutilgan sotuvchi xatolari:", expected_vendor_issues(args.vendors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
