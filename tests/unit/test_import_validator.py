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
from uuid import UUID

from app.services.import_validator import VENDOR_COLUMNS, validate_vendor_rows
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
