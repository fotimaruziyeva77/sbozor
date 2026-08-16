"""Import validatsiyasi — YOZISHDAN OLDIN, TO'LIQ, ILOVADA (D-14).

=============================================================================
NEGA DB XATOSIDAN FOYDALANIB BO'LMAYDI — EMPIRIK FAKT (Pitfall 4).

RLS yoqilgan jadvalda PostgreSQL konstrayt buzilishining `DETAIL`
qatorini BUTUNLAY o'chiradi. O'lchandi — HAM ilova roli, HAM EGA uchun:

    -- RLS'siz (odatdagi kutish):
    ERROR:  duplicate key value violates unique constraint "uq_stalls_market_id_code"
    DETAIL: Key (market_id, code)=(1111..., 12) already exists.

    -- RLS yoqilgan:
    ERROR:  duplicate key value violates unique constraint "uq_stalls_market_id_code"
            (DETAIL qatori UMUMAN YO'Q)

Ya'ni "88-qator: 12 raqami takrorlangan" xabarini DB xatosidan OLIB
BO'LMAYDI: qaysi qiymat to'qnashganini Postgres aytmaydi (bu xavfsizlik
uchun TO'G'RI — ko'rinmaydigan qator haqida ma'lumot sizib chiqmasligi
kerak), qaysi QATOR ekanini esa u umuman bilmaydi.

Shundan kelib chiqadigan arxitektura qoidasi:

    DB konstrayti — IKKINCHI qatlam (poyga himoyasi).
    Foydalanuvchi xabarining MANBAI — SHU MODUL.

Bu modulda sessiya ham, so'rov ham YO'Q: lug'atlar (`zones`,
`categories`, `existing_codes`) chaqiruvchi tomonidan TAYYOR holda
uzatiladi. Shuning uchun u sof funksiya va uni konteynersiz to'liq
qamrash mumkin.
=============================================================================

D-15 — QAYTA IMPORT: MAVJUD YOZUV XATO EMAS.

`existing_codes` (yoki `existing_phones`) dagi qatorlar xato ro'yxatiga
TUSHMAYDI: ular natija ro'yxatidan CHIQARIB TASHLANADI va javobda
`skipped` sifatida sanaladi. Upsert ham, "faylda yo'qlarni yopish" ham
YO'Q.

⚠ OLDINDAN FILTRLASH — MAHSULOT TALABI, "optimizatsiya" EMAS. LEKIN
UNING SABABI 02-21 DA TO'G'RILANDI (WR-04):

`stall_code_claim()` — `AFTER INSERT OR UPDATE OF code` triggeri
(`migrations/versions/0007_market_domain.py:317-321` ning DDL'si;
`BEFORE` shakli `fk_stall_code_registry_market_id_stall_id_stalls` FK'si
bilan ISHLAY OLMAGANI uchun tanlangan — `triggers.py:202-221`). Bu yerda
ilgari u `BEFORE` deb yozilgan edi va o'sha yozuv NOTO'G'RI edi (WR-04).

`AFTER` ekanining OQIBATI: `INSERT ... ON CONFLICT (market_id, code) DO
NOTHING` da konflikt YUZAGA KELGAN qator uchun trigger UMUMAN ishga
tushmaydi. Ya'ni DB `23505` bilan yiqilmaydi — mavjud kodli qator
jimgina o'tkazib yuboriladi.

SHU SABABLI TO'G'RI TUSHUNILISHI SHART: D-15 idempotentligi DB
tomonidan KAFOLATLANMAYDI, uni AYNAN SHU VALIDATOR ushlab turadi.
Filtrlash `skipped` sonini foydalanuvchiga ko'rsatish uchun ham kerak
(DB uni sanamaydi) — lekin u endi "aks holda tranzaksiya yiqiladi"
degan zaruriyat emas, mahsulot javobining manbai. Bu farq muhim:
noto'g'ri yozilgan sabab keyingi maintainerni "kafolat DB'da" degan
xulosaga olib borardi va u filtrlashni "ortiqcha" deb olib tashlashi
mumkin edi.

-----------------------------------------------------------------------------
XABAR TILI — uz-Latn, VA BU TIL QOIDASINING ISTISNOSI EMAS.

1-faza D-16 "DB KONTENTI bitta tilda" deydi (masalan `stalls.status`).
Bu yerdagi matn esa DB kontenti emas — u FOYDALANUVCHI MATNI va u
javobda bir marta uchib ketadi. Uch tilga tarjima qilish uchun `code`
maydoni bor: u MAJBURIY va BARQAROR, frontend esa xohlasa o'z
tarjimasini `code` bo'yicha ko'rsatadi.

⚠ FRONTEND UCHUN KONTRAKT: `message` qator raqamini O'ZIDA saqlaydi
(`"14-qator: ..."`), ya'ni uni ekranda QAYTA prefikslash KERAK EMAS.
`row` maydoni alohida beriladi — u tartiblash va Excelga o'tish uchun
(UI-SPEC §8.5 dagi `{row}-qator: {message}` formati aynan shu satrning
o'zi).
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Final

import structlog
from sbozor_core.enums import Role, StallStatus
from sbozor_core.money import MAX_SAFE_SOUM
from sbozor_core.phone import InvalidPhoneError, normalize_phone

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from uuid import UUID

    from app.services.xlsx_reader import SheetRow

__all__ = [
    "LEDGER_COLUMNS",
    "STAFF_COLUMNS",
    "STALL_COLUMNS",
    "VENDOR_COLUMNS",
    "ImportIssue",
    "LedgerImportRow",
    "StaffImportRow",
    "StallImportRow",
    "VendorImportRow",
    "phone_taken_issue",
    "validate_ledger_rows",
    "validate_staff_rows",
    "validate_stall_rows",
    "validate_vendor_rows",
]

log = structlog.get_logger(__name__)

STALL_COLUMNS = 5
"""Rasta shabloni ustunlari (A6): `kod, zona, toifa, holat, izoh`."""

VENDOR_COLUMNS = 4
"""Sotuvchi shabloni ustunlari (A6): `F.I.Sh., telefon, rasta kodi, boshlanish sanasi`."""

STAFF_COLUMNS = 3
"""Xodim shabloni ustunlari (A6): `F.I.Sh., telefon, rol` (MARKET-07).

TIL USTUNI ATAYIN YO'Q: yaratilgan hisobning tili fayldan emas, import
qilayotgan adminning profilidan olinadi — shablonning tili ham AYNAN
o'sha manbadan keladi (`imports.py::_locale_of`). Faylga ustun qo'shish
ikkinchi haqiqat manbaini tug'dirardi va admin "ruscha shablonda uzbekcha
til yozib qo'ydim" degan holatga tushardi.
"""

LEDGER_COLUMNS = 2
"""Daftar shabloni ustunlari (UI-SPEC §10.3): `rasta kodi, daftar summasi`.

⛔ AYNAN IKKITA VA UCHINCHISI QO'SHILMAYDI — sabab
`xlsx_template._LEDGER_HEADER_KEYS` da literal yozilgan: daftar QOG'OZ va
har qo'shimcha ustun kunlik ishni sekinlashtiradi.
"""

# Ustun POZITSIYALARI — sarlavha matni O'QILMAYDI (O-05). Shablon
# foydalanuvchi tilida hosil bo'ladi, ya'ni ruscha shablonni yuklab
# olgan admin uzbekcha interfeysda import qilsa ham fayl ishlaydi.
# Sarlavhaga qarab ustun topish bu oqimni JIMGINA buzardi.
_STALL_CODE, _STALL_ZONE, _STALL_CATEGORY, _STALL_STATUS, _STALL_NOTE = range(STALL_COLUMNS)
_VENDOR_NAME, _VENDOR_PHONE, _VENDOR_STALL, _VENDOR_FROM = range(VENDOR_COLUMNS)
_STAFF_NAME, _STAFF_PHONE, _STAFF_ROLES = range(STAFF_COLUMNS)
_LEDGER_STALL, _LEDGER_AMOUNT = range(LEDGER_COLUMNS)

_ROLE_SEPARATORS: Final = (",", ";")
"""Rol katagidagi ajratgichlar — IKKALASI ham qabul qilinadi.

Admin qaysi birini yozishini oldindan bilib bo'lmaydi: `,` — ingliz
uslubi, `;` esa CIS lokalidagi Excel'ning ustun ajratgichi va odamlar
uni ro'yxat ajratgichi deb ham ishlatadi. Bittasini tanlash qatorlarning
yarmini `invalid_role` ga aylantirardi.
"""

_THOUSAND_SEPARATORS: Final = ("\u0020", "\u00a0", "\u202f")
"""Daftar summasidagi RAZRYAD AJRATGICHLARI — uchalasi ham TASHLANADI.

⛔ SABAB `_DATE_FORMATS` NIKI BILAN AYNI VA U MAHSULOT QARORI:
all-or-nothing (D-14) tufayli `150 000` shaklidagi BITTA katak 300
qatorli faylni butunlay qaytarib yuborardi — holbuki odam summani
TO'G'RI yozgan, u shunchaki ajratgich qo'ygan.

`\\u00a0` (uzilmaydigan bo'sh joy) ATAYIN ro'yxatda: Excel rus lokalida
sonni MATN qilib nusxalaganda AYNAN shu belgini qo'yadi va u ekranda
oddiy bo'sh joydan farq qilmaydi — ya'ni foydalanuvchi xatoni KO'RA
OLMASDI.

⛔ VERGUL VA NUQTA RO'YXATDA YO'Q: ular kasr ajratgichi ham bo'lishi
   mumkin (`150000.5`), ya'ni ularni tashlash `150000.5` ni `1500005`
   ga aylantirardi — jimgina, o'n barobar xato bilan.
"""

_DATE_FORMATS = ("%d.%m.%Y", "%d/%m/%Y")
"""ISO'dan TASHQARI qabul qilinadigan sana shakllari.

Excel SANA tipidagi katakni `xlsx_reader` ISO ga keltiradi, lekin admin
ustunni MATN sifatida to'ldirishi juda ehtimolli — o'shanda `01.08.2026`
keladi va `date.fromisoformat()` uni rad etardi. D-14 (all-or-nothing)
tufayli bitta bunday katak BUTUN faylni qaytarib yuborardi.
"""


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """Bitta qatordagi validatsiya xatosi.

    `row` — EXCEL qator raqami (sarlavha = 1).
    `code` — mashina uchun, BARQAROR (`MARKET_ERROR_CODES` dan MUSTAQIL
        ro'yxat: bular HTTP xatolari emas, qator xatolari).
    `message` — foydalanuvchi uchun, uz-Latn, qator raqami BILAN.
    """

    row: int
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class StallImportRow:
    """Yozishga TAYYOR rasta qatori — barcha havolalar HAL QILINGAN."""

    row: int
    code: str
    zone_id: UUID
    category_id: UUID
    status: str
    note: str | None


@dataclass(frozen=True, slots=True)
class VendorImportRow:
    """Yozishga TAYYOR sotuvchi qatori.

    `stall_id` `None` bo'lsa biriktirish YOZILMAYDI — sotuvchi reestrga
    tushadi, lekin rastasiz qoladi (D-11: bu xato emas).
    """

    row: int
    full_name: str
    phone: str
    stall_id: UUID | None
    from_date: date


@dataclass(frozen=True, slots=True)
class StaffImportRow:
    """Yaratishga TAYYOR xodim qatori (MARKET-07).

    `roles` — `Role` QIYMATLARI (`cashier`, `inspector`, ...) va FAYLDAGI
    TARTIB saqlanadi. D-05 bo'yicha bir odam bir nechta rolga ega
    bo'lishi mumkin, ya'ni bu maydon ATAYIN ro'yxat.

    `phone` E.164 shaklida, `full_name` esa tozalangan (`_at()`).
    """

    row: int
    full_name: str
    phone: str
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LedgerImportRow:
    """Yozishga TAYYOR daftar qatori (D-17, 08-14).

    `stall_id` — YECHILGAN havola, faylda esa rasta KODI turadi. Yechish
    validatorda bajariladi (`validate_vendor_rows` bilan aynan bir xil
    qaror): repozitoriy qatlami kod bo'yicha qidirsa, topilmagan kod
    JIMGINA nol qator yozardi va import «muvaffaqiyatli» bo'lib
    ko'rinardi.

    ⛔ `amount_soum` — BUTUN so'm va `0` QONUNIY (`sbozor_core.models.
       ledger` modul docstringining 1-bandi): daftar MOLIYAVIY jadval
       emas, tashqi qog'oz manbaning nusxasi.
    """

    row: int
    stall_id: UUID
    amount_soum: int


def validate_stall_rows(
    rows: Sequence[SheetRow],
    *,
    zones: Mapping[str, UUID],
    categories: Mapping[str, UUID],
    existing_codes: Iterable[str],
) -> tuple[list[StallImportRow], list[ImportIssue]]:
    """Rasta qatorlarini tekshiradi; `(yoziladigan, xatolar)` juftini beradi.

    Xatolar ro'yxati BO'SH BO'LMASA chaqiruvchi HECH NARSA yozmaydi
    (D-14). `existing_codes` dagi kodlar xato EMAS — ular birinchi
    ro'yxatdan chiqariladi (D-15).

    HAR QATOR UCHUN BARCHA TEKSHIRUVLAR BAJARILADI, birinchi xatoda
    to'xtamaydi: admin faylni BIR MARTA tuzatib qayta yuklashi kerak.
    Birinchi xatoda to'xtash uni "tuzat -> yukla -> yangi xato" siklga
    tushirardi va 300 xatoli fayl 300 marta yuklanardi.
    """
    known_codes = set(existing_codes)
    issues: list[ImportIssue] = []
    accepted: list[StallImportRow] = []
    first_seen: dict[str, int] = {}

    zone_index = _fold_index(zones)
    category_index = _fold_index(categories)

    for sheet_row in rows:
        number = sheet_row.row
        values = sheet_row.values

        code = _at(values, _STALL_CODE)
        zone_name = _at(values, _STALL_ZONE)
        category_name = _at(values, _STALL_CATEGORY)
        status_text = _at(values, _STALL_STATUS)
        note = _at(values, _STALL_NOTE)

        row_issues: list[ImportIssue] = []

        if code is None:
            row_issues.append(
                ImportIssue(number, "empty_code", f"{number}-qator: rasta raqami bo'sh")
            )
        elif code in first_seen:
            row_issues.append(
                ImportIssue(
                    number,
                    "duplicate_code_in_file",
                    f"{number}-qator: {code} raqami {first_seen[code]}-qatorda ham bor",
                )
            )
        else:
            first_seen[code] = number

        if zone_name is None:
            row_issues.append(_too_short(number, "zona"))
        if category_name is None:
            row_issues.append(_too_short(number, "toifa"))

        zone_id = _lookup(zones, zone_index, zone_name)
        if zone_name is not None and zone_id is None:
            row_issues.append(
                ImportIssue(
                    number,
                    "zone_not_found",
                    f"{number}-qator: '{zone_name}' zonasi topilmadi",
                )
            )

        category_id = _lookup(categories, category_index, category_name)
        if category_name is not None and category_id is None:
            row_issues.append(
                ImportIssue(
                    number,
                    "category_not_found",
                    f"{number}-qator: '{category_name}' toifasi topilmadi",
                )
            )

        status = _stall_status(status_text)
        if status is None:
            row_issues.append(
                ImportIssue(
                    number,
                    "invalid_status",
                    f"{number}-qator: '{status_text}' holati noma'lum "
                    f"(mumkin: {', '.join(sorted(str(item) for item in StallStatus))})",
                )
            )

        if row_issues:
            issues.extend(row_issues)
            continue

        # mypy: yuqoridagi tarmoqlar `row_issues` ni to'ldirmagan bo'lsa
        # uchalasi ham `None` bo'la olmaydi.
        assert code is not None  # noqa: S101
        assert zone_id is not None and category_id is not None  # noqa: S101
        assert status is not None  # noqa: S101

        if code in known_codes:
            # D-15 — SKIP. Xato EMAS va `accepted` ga ham TUSHMAYDI:
            # 02-05 triggeri `ON CONFLICT DO NOTHING` da ham yiqiladi.
            continue

        accepted.append(
            StallImportRow(
                row=number,
                code=code,
                zone_id=zone_id,
                category_id=category_id,
                status=status,
                note=note,
            )
        )

    return accepted, issues


def validate_vendor_rows(
    rows: Sequence[SheetRow],
    *,
    stalls_by_code: Mapping[str, UUID],
    existing_phones: Iterable[str],
    default_from: date,
) -> tuple[list[VendorImportRow], list[ImportIssue]]:
    """Sotuvchi qatorlarini tekshiradi; `(yoziladigan, xatolar)` juftini beradi.

    `default_from` — `market_profile.operating_since` (A3). Rasta kodi
    berilgan, lekin sana BERILMAGAN qatorlar shu sanani oladi: bu
    `StallRepository.create()` dagi boshlang'ich toifa davri bilan
    AYNAN bir xil qoida, ya'ni "sotuvchi bozor ochilganidan beri shu
    yerda" degan eng ehtimolli haqiqatni yozadi. Bu yerda `business_
    today()` ishlatilsa import qilingan tarix BUGUNDAN boshlanardi va
    o'tmishga hisob qayta hisoblanganda rasta "sotuvchisiz" ko'rinardi.
    """
    known_phones = set(existing_phones)
    issues: list[ImportIssue] = []
    accepted: list[VendorImportRow] = []
    phone_first_seen: dict[str, int] = {}
    stall_first_seen: dict[UUID, int] = {}
    """⚠ KALIT — YECHILGAN `stall_id`, FAYLDAGI XOM SATR EMAS (WR-05).

    `_lookup()` avval aniq moslikni, so'ng `_fold_index` (registrsiz)
    ni ko'radi, ya'ni `A1` va `a1` BITTA rastaga yechiladi. Xom satr
    bo'yicha kalitlaganda ular ikki xil kalit bo'lib, ikkala qator ham
    validatsiyadan o'tardi, ikkalasi ham o'sha rastaga ochiq biriktirish
    yozardi va `ex_stall_assignments_no_overlap` `23P01` bilan yiqilardi
    — foydalanuvchi esa QATOR RAQAMISIZ 409 olardi. D-14 aynan shuni
    taqiqlaydi.
    """

    stall_index = _fold_index(stalls_by_code)

    for sheet_row in rows:
        number = sheet_row.row
        values = sheet_row.values

        full_name = _at(values, _VENDOR_NAME)
        raw_phone = _at(values, _VENDOR_PHONE)
        stall_code = _at(values, _VENDOR_STALL)
        raw_from = _at(values, _VENDOR_FROM)

        row_issues: list[ImportIssue] = []

        if full_name is None:
            row_issues.append(_too_short(number, "F.I.Sh."))
        if raw_phone is None:
            row_issues.append(_too_short(number, "telefon"))

        phone: str | None = None
        if raw_phone is not None:
            try:
                # Telefon SHU YERDA normallashtiriladi: import DTO'dan
                # o'tmaydi (`VendorRequest._normalize` faqat HTTP tanasi
                # uchun). Usiz faylda `901234567` shaklida kelgan raqam
                # bazadagi `+998901234567` bilan MOS TUSHMASDI va D-15
                # idempotentligi buzilardi (02-10 ning ogohlantirishi).
                phone = normalize_phone(raw_phone)
            except InvalidPhoneError:
                row_issues.append(
                    ImportIssue(
                        number,
                        "invalid_phone",
                        f"{number}-qator: '{raw_phone}' telefon raqami noto'g'ri",
                    )
                )
            else:
                if phone in phone_first_seen:
                    row_issues.append(
                        ImportIssue(
                            number,
                            "duplicate_phone_in_file",
                            f"{number}-qator: {phone} raqami "
                            f"{phone_first_seen[phone]}-qatorda ham bor",
                        )
                    )
                else:
                    phone_first_seen[phone] = number

        stall_id: UUID | None = None
        if stall_code is not None:
            stall_id = _lookup(stalls_by_code, stall_index, stall_code)
            if stall_id is None:
                row_issues.append(
                    ImportIssue(
                        number,
                        "stall_not_found",
                        f"{number}-qator: {stall_code} raqamli rasta topilmadi",
                    )
                )
            elif stall_id in stall_first_seen:
                # BITTA RASTAGA IKKI SOTUVCHI — `duplicate_code_in_file`
                # kodi QAYTA ISHLATILADI ("fayl ichida takroriy kod").
                # Usiz bu holat `ex_stall_assignments_no_overlap` ga
                # urilib, QATOR RAQAMISIZ 409 berardi — D-14 aynan shuni
                # taqiqlaydi, va bu sotuvchi faylidagi eng ehtimolli xato.
                #
                # ⚠ KALIT `stall_id`, `stall_code` EMAS (WR-05): `A1` va
                # `a1` bitta rastaga yechiladi, ya'ni xom satr bo'yicha
                # kalitlash registr farqli juftlikni SIRG'ALIB o'tkazib
                # yuborardi. Xabarda esa FOYDALANUVCHI YOZGAN kod
                # ko'rsatiladi — u faylda aynan shu shaklda turibdi va
                # yechilgan `stall_id` unga hech nima demasdi.
                row_issues.append(
                    ImportIssue(
                        number,
                        "duplicate_code_in_file",
                        f"{number}-qator: {stall_code} raqamli rasta "
                        f"{stall_first_seen[stall_id]}-qatorda ham biriktirilgan",
                    )
                )
            else:
                stall_first_seen[stall_id] = number

        from_date = default_from if raw_from is None else _parse_date(raw_from)
        if from_date is None:
            row_issues.append(
                ImportIssue(
                    number,
                    "invalid_date",
                    f"{number}-qator: '{raw_from}' sanasi o'qilmadi "
                    "(kutilgan shakl: 2026-08-01 yoki 01.08.2026)",
                )
            )

        if row_issues:
            issues.extend(row_issues)
            continue

        assert full_name is not None and phone is not None  # noqa: S101
        assert from_date is not None  # noqa: S101

        if phone in known_phones:
            # D-15 — SKIP. Biriktirish HAM yozilmaydi: aks holda har
            # qayta import o'sha rastaga YANGI davr qo'shib, EXCLUDE
            # konstraytiga urilardi va "hech narsa o'zgarmadi" o'rniga
            # 409 kelardi.
            continue

        accepted.append(
            VendorImportRow(
                row=number,
                full_name=full_name,
                phone=phone,
                stall_id=stall_id,
                from_date=from_date,
            )
        )

    return accepted, issues


def validate_staff_rows(
    rows: Sequence[SheetRow],
    *,
    allowed_roles: frozenset[str],
    existing_member_phones: Iterable[str],
) -> tuple[list[StaffImportRow], list[ImportIssue]]:
    """Xodim qatorlarini tekshiradi; `(yaratiladigan, xatolar)` juftini beradi.

    `allowed_roles` — `str` QIYMATLAR to'plami, `Role` enum'i EMAS: bu
    modul sof funksiya bo'lib qolishi va chaqiruvchining D-04 darajasini
    ARGUMENT sifatida olishi kerak. Enum'ga bog'lanish uni
    `staff_accounts` ga (ya'ni ikkinchi qatlamga) bog'lardi va testda
    darajani almashtirish uchun butun modulni mock qilishga majburlardi.

    `existing_member_phones` — JORIY BOZOR a'zolarining telefonlari
    (D-15). Ular xato EMAS: `accepted` dan chiqarib tashlanadi va
    chaqiruvchi ularni `skipped` deb sanaydi.

    HAR QATOR UCHUN BARCHA TEKSHIRUVLAR BAJARILADI (`validate_stall_rows`
    bilan aynan bir xil sabab: admin faylni BIR MARTA tuzatsin).
    """
    known_phones = set(existing_member_phones)
    issues: list[ImportIssue] = []
    accepted: list[StaffImportRow] = []
    phone_first_seen: dict[str, int] = {}

    for sheet_row in rows:
        number = sheet_row.row
        values = sheet_row.values

        full_name = _at(values, _STAFF_NAME)
        raw_phone = _at(values, _STAFF_PHONE)
        raw_roles = _at(values, _STAFF_ROLES)

        row_issues: list[ImportIssue] = []

        if full_name is None:
            row_issues.append(_too_short(number, "F.I.Sh."))
        if raw_phone is None:
            row_issues.append(_too_short(number, "telefon"))

        phone: str | None = None
        if raw_phone is not None:
            try:
                # Telefon SHU YERDA normallashtiriladi: import DTO'dan
                # o'tmaydi. Usiz faylda `901234567` shaklida kelgan raqam
                # bazadagi `+998901234567` bilan MOS TUSHMASDI va D-15
                # idempotentligi buzilardi (`validate_vendor_rows` dagi
                # bilan aynan bir xil sabab).
                phone = normalize_phone(raw_phone)
            except InvalidPhoneError:
                row_issues.append(
                    ImportIssue(
                        number,
                        "invalid_phone",
                        f"{number}-qator: '{raw_phone}' telefon raqami noto'g'ri",
                    )
                )
            else:
                if phone in phone_first_seen:
                    row_issues.append(
                        ImportIssue(
                            number,
                            "duplicate_phone_in_file",
                            f"{number}-qator: {phone} raqami "
                            f"{phone_first_seen[phone]}-qatorda ham bor",
                        )
                    )
                else:
                    phone_first_seen[phone] = number

        roles = _staff_roles(number, raw_roles, allowed_roles, row_issues)

        if row_issues:
            issues.extend(row_issues)
            continue

        assert full_name is not None and phone is not None  # noqa: S101
        assert roles is not None  # noqa: S101

        if phone in known_phones:
            # D-15 — SKIP, VA U XATO TARMOG'IDAN KEYIN TURADI.
            #
            # ⚠ TARTIB TESKARI BO'LSA mavjud a'zoning qatoridagi noto'g'ri
            # rol JIMGINA yutilardi: admin "rolni to'g'riladim" deb o'ylab
            # yurardi, fayl esa aslida umuman o'qilmagan bo'lardi.
            #
            # SKIPNING O'ZI — XAVFSIZLIK QARORI, qulaylik emas. Muqobil
            # (parolni qayta berish) roster faylini OMMAVIY PAROL TIKLASH
            # quroliga aylantirardi: eski faylni tasodifan qayta yuklagan
            # admin butun jamoani tizimdan chiqarib yuborardi.
            continue

        accepted.append(StaffImportRow(row=number, full_name=full_name, phone=phone, roles=roles))

    return accepted, issues


def _staff_roles(
    number: int,
    raw: str | None,
    allowed_roles: frozenset[str],
    row_issues: list[ImportIssue],
) -> tuple[str, ...] | None:
    """Rol katagini `Role` qiymatlariga keltiradi; xato bo'lsa `None`.

    IKKI XIL XATO ATAYIN AJRATILGAN:

      `invalid_role`     — matn birorta `Role` ga tushmaydi (imlo xatosi:
                           `kassr`). Admin uchun harakat — faylni tuzatish.
      `role_not_allowed` — matn HAQIQIY rol, lekin chaqiruvchining D-04
                           darajasidan yuqori (`market_admin` bozor
                           admini uchun). Admin uchun harakat — platforma
                           adminiga murojaat qilish.

    Ikkalasini birlashtirish adminni imloni tuzatishga majburlardi,
    holbuki fayl to'g'ri yozilgan edi. `platform_admin` hech qachon
    `allowed_roles` da bo'lmagani uchun avtomatik ikkinchi kodni oladi.

    Katakdagi TAKRORIY rol xato EMAS — u siqiladi (birinchi uchrashuv
    qoladi, tartib saqlanadi): `cashier, cashier` yozgan admin hech
    qanday yangi ma'no bermagan, ya'ni uni rad etish faqat to'sqinlik
    bo'lardi.
    """
    if raw is None:
        row_issues.append(_too_short(number, "rol"))
        return None

    normalized = raw
    for separator in _ROLE_SEPARATORS[1:]:
        normalized = normalized.replace(separator, _ROLE_SEPARATORS[0])
    pieces = [piece.strip() for piece in normalized.split(_ROLE_SEPARATORS[0])]
    pieces = [piece for piece in pieces if piece]

    if not pieces:
        # Katakda faqat ajratgich va bo'sh joy bor edi (`" , ; "`).
        row_issues.append(_too_short(number, "rol"))
        return None

    known = {str(role).casefold(): str(role) for role in Role}
    allowed_text = ", ".join(sorted(allowed_roles))
    roles: list[str] = []
    failed = False

    for piece in pieces:
        role = known.get(piece.casefold())
        if role is None:
            row_issues.append(
                ImportIssue(
                    number,
                    "invalid_role",
                    f"{number}-qator: '{piece}' roli noma'lum (mumkin: {allowed_text})",
                )
            )
            failed = True
        elif role not in allowed_roles:
            row_issues.append(
                ImportIssue(
                    number,
                    "role_not_allowed",
                    f"{number}-qator: '{role}' rolini berishga huquqingiz yo'q "
                    f"(mumkin: {allowed_text})",
                )
            )
            failed = True
        elif role not in roles:
            roles.append(role)

    return None if failed else tuple(roles)


def validate_ledger_rows(
    rows: Sequence[SheetRow],
    *,
    stalls_by_code: Mapping[str, UUID],
) -> tuple[list[LedgerImportRow], list[ImportIssue]]:
    """Daftar qatorlarini tekshiradi; `(yoziladigan, xatolar)` juftini beradi.

    =========================================================================
    ⛔⛔ `0` SUMMA XATO EMAS — VA BU FUNKSIYANING ENG MUHIM QOIDASI (D-17).

    `ledger_entries` MOLIYAVIY JADVAL EMAS va u `FINANCIAL_TABLES` da
    ATAYIN YO'Q (`sbozor_core.models.ledger` modul docstringining
    1-bandi): jadval tashqi QOG'OZ manbaning nusxasi, tizim hisobi emas.
    `daily_charges` ning `CHECK (amount_soum > 0)` qoidasi shu sababdan bu
    yerga TEGISHLI EMAS.

    «Bu rastadan bugun hech nima yig'ilmadi» — SC#5 ning ENG MUHIM
    holati («daftarda 0, tizimda band») va uni rad etadigan validator
    o'sha qatorni solishtiruvdan JIMGINA olib tashlardi: fayl 422 bilan
    qaytardi, admin esa nol yozilgan qatorlarni O'CHIRIB qayta yuklardi —
    ya'ni nomuvofiqlikning dalili foydalanuvchining O'Z qo'li bilan yo'q
    qilinardi.
    =========================================================================

    ⛔ BO'SH KATAK `0` EMAS: to'ldirilmagan summa `row_too_short` beradi.
       «O'lchanmagan» bilan «nol» ni tenglashtirish 05-14 da nomlangan
       taqiq — daftarni ko'chirayotgan odam bir qatorni tashlab
       ketganida tizim buni MA'NOLI javob deb yozardi.

    ⛔ PUL — `int` (C-6). Kasrli qiymat XATO beradi va JIMGINA
       yaxlitlanmaydi: daftardagi son bilan tizimdagi son orasidagi farq
       aynan solishtiruvning mazmuni, ya'ni uni validator «tuzatib»
       qo'ysa hisobot o'z savoliga javob bermay qolardi.

    Args:
        rows: `xlsx_reader.read_rows(expected_columns=LEDGER_COLUMNS)` natijasi.
        stalls_by_code: `{rasta kodi: id}` — JORIY BOZORDAN
            (`ImportRepository.stall_ids_by_code()`). Tenant sessiyasi
            ostida o'qilgani uchun begona bozorning kodi bu yerga
            TUSHMAYDI va u `ledger_stall_unknown` oladi (T-08-60).

    Returns:
        `(accepted, issues)`. `issues` BO'SH BO'LMASA chaqiruvchi HECH
        NARSA yozmaydi (D-14) — `accepted` o'shanda ham to'liq quriladi,
        chunki xato ro'yxati BUTUN fayl bo'yicha yig'ilishi kerak.
    """
    issues: list[ImportIssue] = []
    accepted: list[LedgerImportRow] = []
    stall_first_seen: dict[UUID, int] = {}
    """⚠ KALIT — YECHILGAN `stall_id`, FAYLDAGI XOM SATR EMAS (WR-05).

    `_lookup()` avval aniq moslikni, so'ng `_fold_index` (registrsiz) ni
    ko'radi, ya'ni `A1` va `a1` BITTA rastaga yechiladi. Xom satr
    bo'yicha kalitlaganda ikkala qator ham validatsiyadan o'tardi va
    `uq_ledger_entries_market_day_stall` `23505` bilan yiqilardi —
    foydalanuvchi esa QATOR RAQAMISIZ 409 olardi. D-14 aynan shuni
    taqiqlaydi va bu `validate_vendor_rows` da o'lchangan sinfning aynan
    takrori.
    """

    stall_index = _fold_index(stalls_by_code)

    for sheet_row in rows:
        number = sheet_row.row
        values = sheet_row.values

        code = _at(values, _LEDGER_STALL)
        raw_amount = _at(values, _LEDGER_AMOUNT)

        row_issues: list[ImportIssue] = []

        stall_id: UUID | None = None
        if code is None:
            row_issues.append(_too_short(number, "rasta kodi"))
        else:
            stall_id = _lookup(stalls_by_code, stall_index, code)
            if stall_id is None:
                row_issues.append(
                    ImportIssue(
                        number,
                        "ledger_stall_unknown",
                        f"{number}-qator: {code} raqamli rasta topilmadi",
                    )
                )
            elif stall_id in stall_first_seen:
                # ⛔ XABARDA IKKALA QATOR HAM NOMLANADI: admin faylda
                #   qaysi ikki satrni solishtirishni bilishi kerak, aks
                #   holda 300 qatorli faylda dublikatni qidirish qo'lda
                #   ish bo'lardi (`duplicate_code_in_file` ning qoidasi).
                row_issues.append(
                    ImportIssue(
                        number,
                        "ledger_duplicate_stall",
                        f"{number}-qator: {code} raqamli rasta "
                        f"{stall_first_seen[stall_id]}-qatorda ham bor",
                    )
                )
            else:
                stall_first_seen[stall_id] = number

        amount: int | None = None
        if raw_amount is None:
            row_issues.append(_too_short(number, "daftar summasi"))
        else:
            amount = _ledger_amount(raw_amount)
            if amount is None:
                row_issues.append(
                    ImportIssue(
                        number,
                        "ledger_amount_invalid",
                        f"{number}-qator: '{raw_amount}' summasi butun so'm emas "
                        "(manfiy va kasr qiymat qabul qilinmaydi; 0 mumkin)",
                    )
                )

        if row_issues:
            # HAR QATOR UCHUN BARCHA TEKSHIRUVLAR BAJARILADI, birinchi
            # xatoda to'xtamaydi (`validate_stall_rows` dagi bilan aynan
            # bir xil sabab: admin faylni BIR MARTA tuzatsin).
            issues.extend(row_issues)
            continue

        # mypy: yuqoridagi tarmoqlar `row_issues` ni to'ldirmagan bo'lsa
        # ikkalasi ham `None` bo'la olmaydi.
        assert stall_id is not None  # noqa: S101
        assert amount is not None  # noqa: S101

        accepted.append(LedgerImportRow(row=number, stall_id=stall_id, amount_soum=amount))

    return accepted, issues


def _ledger_amount(text: str) -> int | None:
    """Daftar summasini butun so'mga keltiradi; o'qilmasa `None`.

    ⛔ `isdecimal()`, `isdigit()` EMAS: `isdigit()` yuqori indeks belgilar
       uchun ham `True` beradi (`"²".isdigit()` -> `True`), `int("²")` esa
       `ValueError` ko'tarardi — ya'ni validator o'zi qabul qilgan qiymatda
       yiqilardi va 422 o'rniga 500 kelardi.

    ⛔ MANFIY QIYMAT SHU YERDA RAD ETILADI (`-` `isdecimal()` dan
       o'tmaydi): qog'oz daftar YIG'ILGAN pulni yozadi va storno
       tushunchasi u yerda YO'Q — manfiy son yozuv xatosi.

    ⛔ YUQORI CHEGARA `MAX_SAFE_SOUM`: usiz 30 xonali son `BIGINT` ga
       sig'masdi va DB `22003` bilan yiqilardi — u `_CONFLICT_STATES` da
       yo'q, ya'ni foydalanuvchi qator raqamsiz **500** olardi. Chegara
       JSON tomonida ham majburiy (Pitfall 7): undan katta qiymat javobda
       jimgina yaxlitlanardi.
    """
    cleaned = text
    for separator in _THOUSAND_SEPARATORS:
        cleaned = cleaned.replace(separator, "")
    if not cleaned.isdecimal():
        return None
    value = int(cleaned)
    return value if value <= MAX_SAFE_SOUM else None


def phone_taken_issue(number: int) -> ImportIssue:
    """Telefon PLATFORMADA band — QATOR XATOSI, skip EMAS (MARKET-07).

    ⚠ BU HOLAT D-15 SKIPIDAN BUTUNLAY BOSHQA. D-15 "bu odam ALLAQACHON
    shu bozor a'zosi" degani va u xato emas; bu esa "bu telefon boshqa
    joyda band" degani va admin buni BILISHI shart — jimgina o'tkazib
    yuborish uni "xodim yaratildi" deb ishontirardi.

    Yordamchi SHU MODULDA yashaydi, garchi uni faqat router chaqirsa
    ham: `frontend/scripts/error-codes.test.mjs` `import.errors.*`
    tarjimalarini AYNAN shu fayldagi `ImportIssue(...)` kodlari bilan
    solishtiradi. Router ichida qurilgan xato o'sha darvozadan tashqarida
    qolardi va rus tilidagi admin uz-Latn matnini ko'rardi.
    """
    return ImportIssue(
        number,
        "phone_taken",
        f"{number}-qator: bu telefon platformada allaqachon band",
    )


def _too_short(number: int, column: str) -> ImportIssue:
    """Majburiy ustun bo'sh (yoki qator umuman kalta)."""
    return ImportIssue(
        number,
        "row_too_short",
        f"{number}-qator: '{column}' ustuni bo'sh",
    )


def _at(values: tuple[str | None, ...], index: int) -> str | None:
    """Pozitsiya bo'yicha qiymat; yo'q yoki BO'SH bo'lsa `None`.

    Ikkita mustaqil normallashtirish va ikkalasi ham majburiy:

    * ustun umuman yo'q -> `None`. `xlsx_reader` qatorni allaqachon
      to'ldiradi, lekin bu yordamchi validatorni o'quvchi qatlamdan
      MUSTAQIL qiladi (qo'lda qurilgan kalta `SheetRow` `IndexError`
      bermaydi);
    * bo'sh yoki faqat bo'sh joydan iborat matn -> `None`. O'quvchi
      qatlam buni allaqachon qiladi, lekin BU YERDA takrorlanishi
      SHART: usiz `""` qiymati "to'ldirilgan" deb hisoblanardi va
      `empty_code` darvozasi JIMGINA o'tib ketardi — bo'sh kodli rasta
      esa bazaga yozilardi. Dastlabki yozuvda test aynan shuni fosh
      qildi (`empty_code` xatolar ro'yxatida umuman yo'q edi).
    """
    if index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _fold_index(names: Mapping[str, UUID]) -> dict[str, UUID]:
    """Registr-sezgir bo'lmagan qidiruv indeksi (NOANIQ nomlar TASHLANADI).

    NEGA KERAK: `zones.name` da unikalik REGISTRGA SEZGIR, ya'ni bozorda
    `Sabzavot` bor va admin faylda `sabzavot` yozgan bo'lsa aniq mos
    kelish topilmasdi va u 300 qatorlik `zone_not_found` to'foni olardi
    — sababi esa ko'rinmasdi ("zona ro'yxatda turibdi-ku?").

    NOANIQLIK ESA XATO SIFATIDA QOLADI: agar bozorda HAM `Sabzavot`,
    HAM `SABZAVOT` bo'lsa, `sabzavot` qaysinisiga tegishli ekani
    ma'lum emas — bunday kalit indeksdan CHIQARILADI va qator
    `zone_not_found` oladi. Taxmin qilib yozish rastani NOTO'G'RI
    zonaga qo'yardi va buni hech kim sezmasdi.
    """
    index: dict[str, UUID] = {}
    ambiguous: set[str] = set()
    for name, row_id in names.items():
        key = name.casefold()
        if key in index and index[key] != row_id:
            ambiguous.add(key)
        index[key] = row_id
    for key in ambiguous:
        del index[key]
    return index


def _lookup(
    exact: Mapping[str, UUID],
    folded: Mapping[str, UUID],
    name: str | None,
) -> UUID | None:
    """Avval AYNAN mos kelish, so'ng registrsiz — shu tartibda.

    Aniq mos kelish HAR DOIM ustun: `Sabzavot` va `SABZAVOT` ikkalasi
    ham mavjud bo'lganda `Sabzavot` yozgan qator AYNAN o'shanikini
    oladi (`_fold_index` esa bu kalitni umuman bermaydi).
    """
    if name is None:
        return None
    found = exact.get(name)
    return found if found is not None else folded.get(name.casefold())


def _stall_status(text: str | None) -> str | None:
    """Holat matnini `StallStatus` qiymatiga keltiradi.

    Bo'sh katak -> `active` (A4: eng ehtimolli holat; ustunni to'ldirmagan
    admin "bu rasta ishlaydi" demoqchi). Noma'lum matn -> `None`, ya'ni
    `invalid_status`: JIMGINA `active` ga tushish "closed" deb yozilgan
    rastaga 6-fazada hisob yozardi.
    """
    if text is None:
        return str(StallStatus.ACTIVE)
    candidate = text.casefold()
    for item in StallStatus:
        if str(item).casefold() == candidate:
            return str(item)
    return None


def _parse_date(text: str) -> date | None:
    """ISO yoki `dd.mm.yyyy` / `dd/mm/yyyy`; o'qilmasa `None`."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    for pattern in _DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date()  # noqa: DTZ007
        except ValueError:
            continue
    return None
