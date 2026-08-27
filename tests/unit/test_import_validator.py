"""Sotuvchi importi validatori — REGISTR FARQLI DUBLIKAT (WR-05).

=============================================================================
NEGA BU FAYL BOR VA NEGA U `tests/unit/` DA:

`validate_vendor_rows()` — SOF FUNKSIYA: sessiya ham, so'rov ham yo'q,
lug'atlar (`stalls_by_code`, `existing_phones`) chaqiruvchidan TAYYOR
holda keladi (modul docstringi). Ya'ni butun qaror daraxti konteynersiz,
DB'siz va sekundning ondan biriga qamraladi.

O'LCHANADIGAN NOSOZLIK (02-REVIEW.md WR-05): `_lookup()` rasta kodini
avval AYNAN, so'ng `_fold_index` (registrsiz) bo'yicha topadi, ya'ni
`A1` va `a1` BITTA `stall_id` ga yechiladi. Fayl ichidagi dublikat
qo'riqchisi esa XOM SATR bo'yicha kalitlanardi — natijada ikkala qator
ham validatsiyadan o'tardi, ikkalasi ham o'sha rastaga OCHIQ biriktirish
yozardi, `ex_stall_assignments_no_overlap` `23P01` bilan yiqilardi va
foydalanuvchi QATOR RAQAMISIZ 409 olardi.

D-14 aynan shuni taqiqlaydi ("har xato qator raqami va sababi bilan"), va
validatorning o'z izohi bu holatni "sotuvchi faylidagi eng ehtimolli
xato" deb ataydi. Ya'ni nosozlik eng ko'p uchraydigan yo'lda edi.

RLS TUFAYLI DB XATOSIDAN QATOR RAQAMINI OLIB BO'LMAYDI (modul
docstringidagi empirik fakt): `DETAIL` qatori o'chiriladi. Shuning uchun
"keyin DB ushlaydi" degan zaxira yo'l MAVJUD EMAS — bu yerdagi tekshiruv
YAGONA yo'l.
=============================================================================

Har testda NAZORAT HOLATI bor yoki u qo'shni testda: faqat rad etish
tekshirilganda "hamma narsani dublikat deb ataydigan" buzuq variant ham
yashil ko'rinardi.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.services.import_validator import (
    LEDGER_COLUMNS,
    VENDOR_COLUMNS,
    validate_ledger_rows,
    validate_vendor_rows,
)
from app.services.xlsx_reader import SheetRow

STALL_A1 = UUID("11111111-1111-4111-8111-111111111111")
STALL_B2 = UUID("22222222-2222-4222-8222-222222222222")

STALLS_BY_CODE = {"A1": STALL_A1, "B2": STALL_B2}
"""Bozordagi rasta reyestri — kod AYNAN shu registrda saqlangan.

`A1` katta harf bilan: fayl `a1` yozganda `_lookup()` `_fold_index` ga
tushadi va aynan shu yo'l WR-05 ni tug'digan yo'l.
"""

DEFAULT_FROM = date(2026, 1, 1)
"""`market_profile.operating_since` o'rnida (A3) — sana qatorlarda berilmaydi."""

HEADER_ROW = 1


def _row(number: int, name: str, phone: str, stall_code: str | None) -> SheetRow:
    """Sotuvchi qatori — ustun tartibi `_VENDOR_*` bilan bir xil.

    Sana ustuni ATAYIN bo'sh: u `default_from` ga tushadi va bu testlar
    sana yo'liga umuman tegmaydi. To'ldirilsa har bir test ikkita narsani
    birga sinardi va yiqilgan assert qaysi biri buzilganini aytmasdi.
    """
    values: tuple[str | None, ...] = (name, phone, stall_code, None)
    assert len(values) == VENDOR_COLUMNS, "ustunlar soni shablon bilan mos emas"
    return SheetRow(row=number, values=values)


def _validate(rows: list[SheetRow]) -> tuple[list[object], list[object]]:
    accepted, issues = validate_vendor_rows(
        rows,
        stalls_by_code=STALLS_BY_CODE,
        existing_phones=(),
        default_from=DEFAULT_FROM,
    )
    return list(accepted), list(issues)


def test_mixed_case_stall_code_is_reported_as_a_duplicate() -> None:
    """`A1` va `a1` — BITTA rasta: ikkinchi qator QATOR RAQAMI bilan rad etiladi.

    Bu WR-05 ning bevosita qulfi. Tuzatishdan oldin ikkala qator ham
    `accepted` ga tushardi va xato faqat DB'da, qator raqamisiz 409
    bo'lib chiqardi.
    """
    rows = [
        _row(HEADER_ROW + 1, "Anvar Karimov", "+998901110011", "A1"),
        _row(HEADER_ROW + 2, "Bekzod Toshev", "+998901110022", "a1"),
    ]

    accepted, issues = _validate(rows)

    assert len(issues) == 1, f"kutilgan 1 xato, kelgani {len(issues)}: {issues}"
    issue = issues[0]
    assert issue.code == "duplicate_code_in_file"  # type: ignore[attr-defined]
    assert issue.row == HEADER_ROW + 2  # type: ignore[attr-defined]
    # D-14: xabar QATOR RAQAMINI o'zida saqlaydi — ikkinchi qatorniki ham,
    # BIRINCHI uchrashgan qatorniki ham. Ikkinchisisiz admin "qayerda
    # takrorlandi?" savoli bilan qolardi.
    message = issue.message  # type: ignore[attr-defined]
    assert f"{HEADER_ROW + 2}-qator" in message, message
    assert f"{HEADER_ROW + 1}-qatorda" in message, message
    # FOYDALANUVCHI YOZGAN kod ko'rsatiladi (`a1`), reyestrdagi `A1` emas:
    # u faylda aynan shu shaklda turibdi.
    assert "a1" in message, message
    # BIRINCHI qator baribir yoziladi — D-14 "all-or-nothing" ni router
    # hal qiladi, validator esa yaroqli qatorni jazolamaydi.
    assert [row.row for row in accepted] == [HEADER_ROW + 1]  # type: ignore[attr-defined]


def test_two_different_stalls_are_not_a_duplicate() -> None:
    """NAZORAT: `A1` va `B2` — ikki xil rasta, xato YO'Q.

    Usiz yuqoridagi test "har qanday ikkinchi rasta kodini dublikat deb
    ataydigan" buzuq variantdan ham bemalol o'tardi va butun import
    ishlamay qolardi.
    """
    rows = [
        _row(HEADER_ROW + 1, "Anvar Karimov", "+998901110011", "A1"),
        _row(HEADER_ROW + 2, "Bekzod Toshev", "+998901110022", "B2"),
    ]

    accepted, issues = _validate(rows)

    assert issues == [], f"nazorat holatida xato chiqdi: {issues}"
    assert [row.stall_id for row in accepted] == [STALL_A1, STALL_B2]  # type: ignore[attr-defined]


def test_unknown_stall_code_is_not_counted_as_a_duplicate() -> None:
    """Topilmagan kod `stall_not_found` beradi va reyestrga KIRMAYDI.

    Yechilmagan holat dublikat hisoblanmasligi SHART: `_lookup()` `None`
    qaytarganda kalit ham yo'q, ya'ni ikkita noma'lum kod bir-birini
    "takrorlangan" deb ko'rsatmasligi kerak. Aks holda foydalanuvchi
    bitta xatoni (noto'g'ri kod) ikkita boshqa-boshqa xato sifatida
    ko'rardi va ikkinchisi uni butunlay noto'g'ri yo'lga solardi.
    """
    rows = [
        _row(HEADER_ROW + 1, "Anvar Karimov", "+998901110011", "Z9"),
        _row(HEADER_ROW + 2, "Bekzod Toshev", "+998901110022", "z9"),
    ]

    accepted, issues = _validate(rows)

    assert accepted == []
    codes = [issue.code for issue in issues]  # type: ignore[attr-defined]
    assert codes == ["stall_not_found", "stall_not_found"], codes
    assert "duplicate_code_in_file" not in codes


def test_vendor_without_a_stall_code_never_collides() -> None:
    """Rastasiz sotuvchilar bir-birini bloklamaydi (D-11).

    `stall_code` bo'sh bo'lganda `stall_id` `None` bo'lib qoladi va u
    reyestrga UMUMAN yozilmasligi kerak. `None` kalit sifatida
    ishlatilganda IKKINCHI rastasiz sotuvchi "takrorlangan rasta" xatosi
    olardi — holbuki D-11 bo'yicha rastasiz sotuvchi umuman xato emas.
    """
    rows = [
        _row(HEADER_ROW + 1, "Anvar Karimov", "+998901110011", None),
        _row(HEADER_ROW + 2, "Bekzod Toshev", "+998901110022", None),
    ]

    accepted, issues = _validate(rows)

    assert issues == []
    assert [row.stall_id for row in accepted] == [None, None]  # type: ignore[attr-defined]


# ===========================================================================
# DAFTAR IMPORTI (D-17, 08-14) — `validate_ledger_rows`
#
# ⛔⛔ BU BLOKNING ENG QIMMAT DA'VOSI: `0` SUMMA XATO EMAS.
#
# `ledger_entries` MOLIYAVIY JADVAL EMAS (08-02, model docstringi 1-band):
# u tashqi QOG'OZ manbaning nusxasi va `daily_charges` ning
# `CHECK (amount_soum > 0)` qoidasi unga TEGISHLI EMAS. «Bu rastadan bugun
# hech nima yig'ilmadi» — SC#5 ning eng muhim holati va uni rad etadigan
# validator o'sha qatorni solishtiruvdan JIMGINA olib tashlardi.
# ===========================================================================

LEDGER_STALLS = {"A1": STALL_A1, "B2": STALL_B2}
"""Daftar validatorining reyestri — `STALLS_BY_CODE` bilan AYNI shakl.

`A1` katta harf bilan: fayl `a1` yozganda `_lookup()` `_fold_index` ga
tushadi va aynan shu yo'l WR-05 ni tug'digan yo'l (yuqoridagi blok).
"""


def _ledger_row(number: int, code: str | None, amount: str | None) -> SheetRow:
    """Daftar qatori — AYNAN IKKI ustun (UI-SPEC §10.3)."""
    values: tuple[str | None, ...] = (code, amount)
    assert len(values) == LEDGER_COLUMNS, "ustunlar soni shablon bilan mos emas"
    return SheetRow(row=number, values=values)


def _validate_ledger(rows: list[SheetRow]) -> tuple[list[Any], list[Any]]:
    accepted, issues = validate_ledger_rows(rows, stalls_by_code=LEDGER_STALLS)
    return list(accepted), list(issues)


def test_unknown_stall_code_is_rejected_with_its_row_number() -> None:
    """Tizimda yo'q rasta kodi -> `ledger_stall_unknown`, QATOR RAQAMI bilan.

    ⛔ NAZORAT HOLATI SHU TESTNING O'ZIDA: ikkinchi qator YAROQLI va u
       `accepted` da qoladi. Faqat rad etishni tekshirish "hamma qatorni
       rad etadigan" buzuq variantni ham yashil ko'rsatardi.
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "Z9", "150000"),
        _ledger_row(HEADER_ROW + 2, "A1", "150000"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert [issue.code for issue in issues] == ["ledger_stall_unknown"]
    assert issues[0].row == HEADER_ROW + 1
    assert "Z9" in issues[0].message, issues[0].message
    assert [row.row for row in accepted] == [HEADER_ROW + 2]


def test_zero_is_a_legal_ledger_amount() -> None:
    """⛔⛔ `0` XATO EMAS — VA BU BU BLOKNING ASOSIY DA'VOSI (D-17).

    «Daftarda 0, tizimda band» — SC#5 ning eng muhim nomuvofiqligi.
    `0` ni rad etadigan validator o'sha qatorni faylga yozgan odamning
    ishini bekor qilardi va nomuvofiqlik SOLISHTIRUVDA umuman
    ko'rinmasdi.
    """
    accepted, issues = _validate_ledger([_ledger_row(HEADER_ROW + 1, "A1", "0")])

    assert issues == [], f"nol summa rad etildi: {issues}"
    assert [row.amount_soum for row in accepted] == [0]


def test_fractional_and_negative_amounts_are_rejected() -> None:
    """Kasr va manfiy summa -> `ledger_amount_invalid` (C-6: pul — butun `int`).

    ⛔ KASR QIYMAT JIMGINA YAXLITLANMAYDI: `150000.5` ni `150000` qilib
       qabul qilish daftardagi son bilan tizimdagi sonni FARQ QILDIRARDI
       va aynan shu farq solishtiruvning butun mazmuni.

    ⛔ MANFIY SUMMA HAM RAD ETILADI: qog'oz daftar YIG'ILGAN pulni
       yozadi, storno tushunchasi u yerda YO'Q. Manfiy qiymat — yozuv
       xatosi va u foydalanuvchiga KO'RSATILADI.
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "A1", "150000.5"),
        _ledger_row(HEADER_ROW + 2, "B2", "-150000"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert accepted == []
    assert [issue.code for issue in issues] == [
        "ledger_amount_invalid",
        "ledger_amount_invalid",
    ]
    assert [issue.row for issue in issues] == [HEADER_ROW + 1, HEADER_ROW + 2]


def test_a_thousand_separator_is_accepted_not_rejected() -> None:
    """`150 000` (bo'sh joy bilan) QABUL QILINADI — D-14 ning narxi tufayli.

    ⛔ SABAB `_parse_date` NING UCH SHAKLI BILAN AYNI: all-or-nothing
       tufayli BITTA bunday katak 300 qatorli faylni butunlay qaytarib
       yuborardi, holbuki odam summani TO'G'RI yozgan — u shunchaki
       ajratgich qo'ygan.

    ⚠ Ajratgichning UCH shakli ham qamraladi: oddiy bo'sh joy, uzilmaydigan
      bo'sh joy (U+00A0 — Excel rus lokalida AYNAN shuni qo'yadi) va tor
      uzilmaydigan bo'sh joy (U+202F).
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "A1", "150 000"),
        _ledger_row(HEADER_ROW + 2, "B2", "1 250 000"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert issues == []
    assert [row.amount_soum for row in accepted] == [150_000, 1_250_000]


def test_an_empty_amount_is_not_read_as_zero() -> None:
    """⛔ BO'SH KATAK `0` EMAS — u `row_too_short` beradi (05-14 darsi).

    «O'lchanmagan» bilan «nol» ni tenglashtirish bu fazaning nomlangan
    taqiqi: to'ldirilmagan katak `0` deb o'qilsa, daftarni ko'chirayotgan
    odam bir qatorni tashlab ketganida tizim buni «bu rastadan hech nima
    yig'ilmadi» degan MA'NOLI javob deb yozardi.
    """
    accepted, issues = _validate_ledger([_ledger_row(HEADER_ROW + 1, "A1", None)])

    assert accepted == []
    assert [issue.code for issue in issues] == ["row_too_short"]


def test_the_same_stall_twice_in_one_file_is_rejected() -> None:
    """Fayl ichidagi dublikat -> `ledger_duplicate_stall`, IKKALA qator bilan.

    ⛔ USIZ HOLAT `UNIQUE (market_id, business_date, stall_id)` GA URILIB,
       QATOR RAQAMISIZ **409** BERARDI — D-14 aynan shuni taqiqlaydi
       (`validate_vendor_rows` dagi WR-05 ning aynan sinfi).

    ⚠ BIRINCHI QATOR `accepted` DA QOLADI va bu `validate_vendor_rows`
      da o'rnatilgan konvensiya: all-or-nothing qarorini ROUTER qabul
      qiladi (`_reject_if_invalid`), validator esa yaroqli qatorni
      JAZOLAMAYDI. Ikkinchi qator xato ro'yxatiga tushgani uchun bu
      faylning birorta qatori baribir yozilmaydi.
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "A1", "150000"),
        _ledger_row(HEADER_ROW + 2, "A1", "170000"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert [row.row for row in accepted] == [HEADER_ROW + 1]
    assert [issue.code for issue in issues] == ["ledger_duplicate_stall"]
    assert issues[0].row == HEADER_ROW + 2
    assert str(HEADER_ROW + 1) in issues[0].message, issues[0].message


def test_a_case_folded_duplicate_is_caught_too() -> None:
    """⛔ `A1` va `a1` — BITTA rasta (WR-05 ning daftardagi takrori).

    `_lookup()` avval aniq, so'ng registrsiz moslikni ko'radi, ya'ni
    ikkala qator ham AYNI `stall_id` ga yechiladi. Dublikat qo'riqchisi
    XOM SATR bo'yicha kalitlanganda ikkalasi ham validatsiyadan o'tardi
    va konstrayt xatosi QATOR RAQAMISIZ qaytardi.

    ⚠ XABARDA FOYDALANUVCHI YOZGAN kod (`a1`) ko'rsatiladi, reyestrdagi
      `A1` emas: faylda aynan shu shakl turibdi va yechilgan `stall_id`
      odamga hech nima demasdi.
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "A1", "150000"),
        _ledger_row(HEADER_ROW + 2, "a1", "170000"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert [row.row for row in accepted] == [HEADER_ROW + 1]
    assert [issue.code for issue in issues] == ["ledger_duplicate_stall"]
    assert "a1" in issues[0].message, issues[0].message


def test_two_different_stalls_are_not_a_ledger_duplicate() -> None:
    """NAZORAT: ikki xil rasta — xato YO'Q va `stall_id` YECHILGAN.

    Usiz yuqoridagi ikki test "har ikkinchi qatorni dublikat deb
    ataydigan" buzuq variantdan bemalol o'tardi.
    """
    rows = [
        _ledger_row(HEADER_ROW + 1, "A1", "150000"),
        _ledger_row(HEADER_ROW + 2, "b2", "0"),
    ]

    accepted, issues = _validate_ledger(rows)

    assert issues == []
    assert [row.stall_id for row in accepted] == [STALL_A1, STALL_B2]
    assert [row.row for row in accepted] == [HEADER_ROW + 1, HEADER_ROW + 2]


def test_every_error_in_a_ledger_row_is_reported_at_once() -> None:
    """Bir qatordagi IKKALA xato ham BIRGA qaytadi (`validate_stall_rows` qoidasi).

    Birinchi xatoda to'xtash adminni «tuzat -> yukla -> yangi xato»
    siklga tushirardi va 300 xatoli fayl 300 marta yuklanardi.
    """
    accepted, issues = _validate_ledger([_ledger_row(HEADER_ROW + 1, "Z9", "abc")])

    assert accepted == []
    assert sorted(issue.code for issue in issues) == [
        "ledger_amount_invalid",
        "ledger_stall_unknown",
    ]


def test_the_ledger_column_count_matches_the_template() -> None:
    """⛔ `LEDGER_COLUMNS` — shablon bilan parser orasidagi YAGONA son.

    Shablon ikki ustun yozadi (`xlsx_template._LEDGER_HEADER_KEYS`),
    o'quvchi qatlam esa `expected_columns` ni AYNAN shu konstantadan
    oladi. Ular ajralib ketsa fayl «qisqa qator» bo'lib o'qilardi va HAR
    qator `row_too_short` olardi.
    """
    from app.services.xlsx_template import _LEDGER_HEADER_KEYS

    assert LEDGER_COLUMNS == len(_LEDGER_HEADER_KEYS) == 2
