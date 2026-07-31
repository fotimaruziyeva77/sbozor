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

⚠ BU 02-05 DAN KELGAN KIRISH SHARTI, "optimizatsiya" EMAS.
`stall_code_claim()` `BEFORE INSERT` triggeri `ON CONFLICT DO NOTHING`
da HAM ishga tushadi va `23505` bilan BUTUN TRANZAKSIYANI yiqitadi.
Ya'ni mavjud kodli qator INSERT'ga YETIB BORMASLIGI shart — aks holda
D-15 (idempotent qayta import) DB darajasida bajarilmasdi va admin
"hech narsa o'zgarmadi" o'rniga 409 olardi.

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
from typing import TYPE_CHECKING

import structlog
from sbozor_core.enums import StallStatus
from sbozor_core.phone import InvalidPhoneError, normalize_phone

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from uuid import UUID

    from app.services.xlsx_reader import SheetRow

__all__ = [
    "STALL_COLUMNS",
    "VENDOR_COLUMNS",
    "ImportIssue",
    "StallImportRow",
    "VendorImportRow",
    "validate_stall_rows",
    "validate_vendor_rows",
]

log = structlog.get_logger(__name__)

STALL_COLUMNS = 5
"""Rasta shabloni ustunlari (A6): `kod, zona, toifa, holat, izoh`."""

VENDOR_COLUMNS = 4
"""Sotuvchi shabloni ustunlari (A6): `F.I.Sh., telefon, rasta kodi, boshlanish sanasi`."""

# Ustun POZITSIYALARI — sarlavha matni O'QILMAYDI (O-05). Shablon
# foydalanuvchi tilida hosil bo'ladi, ya'ni ruscha shablonni yuklab
# olgan admin uzbekcha interfeysda import qilsa ham fayl ishlaydi.
# Sarlavhaga qarab ustun topish bu oqimni JIMGINA buzardi.
_STALL_CODE, _STALL_ZONE, _STALL_CATEGORY, _STALL_STATUS, _STALL_NOTE = range(STALL_COLUMNS)
_VENDOR_NAME, _VENDOR_PHONE, _VENDOR_STALL, _VENDOR_FROM = range(VENDOR_COLUMNS)

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
    stall_first_seen: dict[str, int] = {}

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
            elif stall_code in stall_first_seen:
                # BITTA RASTAGA IKKI SOTUVCHI — `duplicate_code_in_file`
                # kodi QAYTA ISHLATILADI ("fayl ichida takroriy kod").
                # Usiz bu holat `ex_stall_assignments_no_overlap` ga
                # urilib, QATOR RAQAMISIZ 409 berardi — D-14 aynan shuni
                # taqiqlaydi, va bu sotuvchi faylidagi eng ehtimolli xato.
                row_issues.append(
                    ImportIssue(
                        number,
                        "duplicate_code_in_file",
                        f"{number}-qator: {stall_code} raqamli rasta "
                        f"{stall_first_seen[stall_code]}-qatorda ham biriktirilgan",
                    )
                )
            else:
                stall_first_seen[stall_code] = number

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
