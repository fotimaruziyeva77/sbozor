"""Xodimlar rosteri — rol darajasi va qator validatsiyasi (MARKET-07).

=============================================================================
NEGA BU TESTLAR BAZASIZ VA NEGA ULAR SHU YERDA:

`validate_staff_rows()` — sof funksiya: unga lug'atlar (ruxsat etilgan
rollar to'plami, mavjud a'zolar telefonlari) TAYYOR holda uzatiladi va u
sessiyaga ham, so'rovga ham tegmaydi (`import_validator` modul
docstringidagi bilan aynan bir xil qoida). Ya'ni butun qamrov
konteynersiz o'lchanadi va u endpoint testining O'RNINI BOSMAYDI —
u yerdagi savol boshqa: "router bu funksiyani CHAQIRADIMI?".

`staff_accounts.assignable_roles()` shu yerda sinaladi, chunki u
validatorning `allowed_roles` argumentini quradigan YAGONA manba (D-04).
Uni `users.py` ichida qoldirish ikkinchi nusxaga olib kelardi va
`POST /imports/staff` bilan `POST /users` bir kun ajralib ketardi.
=============================================================================

XABAR TILI — uz-Latn va qator raqami xabarning O'ZIDA (`import_validator`
modul docstringi). Testlar `code` ni AYNAN, `message` ni esa MAZMUNAN
(qator raqami / rol nomi / ruxsat etilgan to'plam ko'rinishi) tekshiradi:
matnni belgima-belgi qulflash tarjima tuzatishini regressiya qilardi.
"""

from __future__ import annotations

import pytest
from app.schemas import MIN_PASSWORD_LENGTH
from app.services.import_validator import (
    STAFF_COLUMNS,
    StaffImportRow,
    validate_staff_rows,
)
from app.services.staff_accounts import (
    MARKET_ADMIN_ASSIGNABLE_ROLES,
    TEMPORARY_PASSWORD_BYTES,
    assignable_roles,
    temporary_password,
)
from app.services.xlsx_reader import SheetRow
from sbozor_core.enums import Role

MARKET_ADMIN_ALLOWED = frozenset({str(role) for role in MARKET_ADMIN_ASSIGNABLE_ROLES})
PLATFORM_ADMIN_ALLOWED = frozenset({str(role) for role in assignable_roles(is_platform_admin=True)})


def staff_row(row: int, *values: str | None) -> SheetRow:
    """Xodim qatori — `xlsx_reader` bergan shaklda (3 ustun)."""
    padded = (*values, *(None,) * (STAFF_COLUMNS - len(values)))
    return SheetRow(row=row, values=padded[:STAFF_COLUMNS])


def validate(
    *rows: SheetRow,
    allowed: frozenset[str] = MARKET_ADMIN_ALLOWED,
    existing: tuple[str, ...] = (),
) -> tuple[list[StaffImportRow], list[str]]:
    """`(qabul qilinganlar, xato KODLARI)` — takrorlanadigan chaqiruv."""
    accepted, issues = validate_staff_rows(
        list(rows),
        allowed_roles=allowed,
        existing_member_phones=existing,
    )
    return accepted, [issue.code for issue in issues]


# ===========================================================================
# D-04 — rol berish darajasining YAGONA manbai
# ===========================================================================


@pytest.mark.parametrize("is_platform_admin", [True, False], ids=["platform", "market"])
def test_platform_admin_role_is_never_assignable(is_platform_admin: bool) -> None:
    """`platform_admin` HAR IKKALA darajada ham to'plamdan tashqarida (CR-03).

    U `users.is_platform_admin` BAYROG'I orqali beriladi, a'zolik roli
    sifatida EMAS. Gibrid hisob (`roles=[platform_admin]` +
    `is_platform_admin=false`) bozorlararo ma'lumot ochardi.
    """
    assert Role.PLATFORM_ADMIN not in assignable_roles(is_platform_admin)


def test_assignable_roles_matches_the_d04_table() -> None:
    """Ikkala daraja ham D-04 jadvalidagi AYNAN to'plamni beradi."""
    assert assignable_roles(is_platform_admin=False) == MARKET_ADMIN_ASSIGNABLE_ROLES
    assert assignable_roles(is_platform_admin=True) == frozenset(
        {Role.MARKET_ADMIN, Role.DIRECTOR, Role.CASHIER, Role.INSPECTOR}
    )


def test_temporary_password_passes_the_policy_length() -> None:
    """Vaqtinchalik parol siyosat uzunligidan UZUN (D-02).

    Qisqaroq qiymat "yaratilgan hisob o'z paroli bilan kira olmaydi"
    degan jimgina tuzoqni yaratardi.
    """
    assert len(temporary_password()) > MIN_PASSWORD_LENGTH
    assert temporary_password() != temporary_password()
    assert TEMPORARY_PASSWORD_BYTES >= 9


# ===========================================================================
# Telefon — E.164 (D-01)
# ===========================================================================


@pytest.mark.parametrize(
    "raw",
    ["90 991 00 03", "998909910003", "+998 90 991 00 03"],
    ids=["local", "no-plus", "spaced"],
)
def test_phone_is_normalised_to_one_e164_value(raw: str) -> None:
    """Uchala yozuv shakli ham BITTA qiymatga tushadi.

    Normalizatsiya SHU YERDA bo'lishi shart: import DTO'dan o'tmaydi,
    ya'ni `901234567` shaklidagi raqam bazadagi `+998901234567` bilan
    mos tushmasdi va D-15 idempotentligi buzilardi.
    """
    accepted, codes = validate(staff_row(2, "Aliyev Vali", raw, "cashier"))

    assert codes == []
    assert [row.phone for row in accepted] == ["+998909910003"]


def test_invalid_phone_is_reported_with_the_row_number() -> None:
    accepted, codes = validate(staff_row(7, "Aliyev Vali", "12", "cashier"))

    assert accepted == []
    assert codes == ["invalid_phone"]


def test_duplicate_phone_inside_the_file_names_both_rows() -> None:
    """Ikkala qator raqami ham xabarda — admin qaysi ikkitasini ko'radi."""
    _, issues = validate_staff_rows(
        [
            staff_row(2, "Aliyev Vali", "+998909910003", "cashier"),
            staff_row(9, "Valiyev Ali", "909910003", "inspector"),
        ],
        allowed_roles=MARKET_ADMIN_ALLOWED,
        existing_member_phones=(),
    )

    assert [issue.code for issue in issues] == ["duplicate_phone_in_file"]
    assert "9-qator" in issues[0].message
    assert "2-qator" in issues[0].message


# ===========================================================================
# Majburiy ustunlar
# ===========================================================================


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((None, "+998909910003", "cashier"), 1),
        (("Aliyev Vali", None, "cashier"), 1),
        (("Aliyev Vali", "+998909910003", None), 1),
        (("Aliyev Vali", "+998909910003", "  ,  ;  "), 1),
        ((None, None, None), 3),
    ],
    ids=["no-name", "no-phone", "no-role", "blank-role-pieces", "empty-row"],
)
def test_missing_required_columns_are_reported(
    values: tuple[str | None, str | None, str | None],
    expected: int,
) -> None:
    """Bo'sh F.I.Sh. / telefon / rol — `row_too_short`.

    Oxirgi holat BIR QATORDA UCHTA xatoni birga beradi: validator
    birinchi xatoda TO'XTAMAYDI (`validate_stall_rows` bilan aynan bir
    xil sabab — admin faylni BIR MARTA tuzatsin).
    """
    accepted, codes = validate(staff_row(4, *values))

    assert accepted == []
    assert codes == ["row_too_short"] * expected


# ===========================================================================
# Rollar — `invalid_role` va `role_not_allowed` ATAYIN alohida
# ===========================================================================


def test_unknown_role_names_the_allowed_set() -> None:
    """Imlo xatosi -> `invalid_role`, xabar amaldagi to'plamni NOMLAYDI.

    Jimgina o'tkazib yuborish adminni "xodim yaratildi" deb
    ishontirardi; to'plamsiz xabar esa uni taxmin qilishga majburlardi.
    """
    _, issues = validate_staff_rows(
        [staff_row(3, "Aliyev Vali", "+998909910003", "kassr")],
        allowed_roles=MARKET_ADMIN_ALLOWED,
        existing_member_phones=(),
    )

    assert [issue.code for issue in issues] == ["invalid_role"]
    assert "kassr" in issues[0].message
    for role in sorted(MARKET_ADMIN_ALLOWED):
        assert role in issues[0].message


def test_role_above_the_caller_level_is_a_separate_code() -> None:
    """`market_admin` — HAQIQIY rol, lekin bozor admini uni berolmaydi.

    ⚠ `invalid_role` dan ATAYIN ajratilgan: admin uchun harakat
    BUTUNLAY boshqa (birinchisida imloni tuzatadi, bu yerda esa
    platforma adminiga murojaat qiladi).
    """
    _, issues = validate_staff_rows(
        [staff_row(5, "Aliyev Vali", "+998909910003", "market_admin")],
        allowed_roles=MARKET_ADMIN_ALLOWED,
        existing_member_phones=(),
    )

    assert [issue.code for issue in issues] == ["role_not_allowed"]
    assert "market_admin" in issues[0].message


@pytest.mark.parametrize(
    "allowed",
    [MARKET_ADMIN_ALLOWED, PLATFORM_ADMIN_ALLOWED],
    ids=["market-admin", "platform-admin"],
)
def test_platform_admin_role_is_rejected_at_every_level(allowed: frozenset[str]) -> None:
    """`platform_admin` hech bir darajada `allowed_roles` da bo'lmaydi."""
    accepted, codes = validate(
        staff_row(6, "Aliyev Vali", "+998909910003", "platform_admin"),
        allowed=allowed,
    )

    assert accepted == []
    assert codes == ["role_not_allowed"]


def test_platform_admin_can_assign_market_admin() -> None:
    """NAZORAT: yuqori daraja o'sha faylni QABUL qiladi."""
    accepted, codes = validate(
        staff_row(5, "Aliyev Vali", "+998909910003", "market_admin"),
        allowed=PLATFORM_ADMIN_ALLOWED,
    )

    assert codes == []
    assert [row.roles for row in accepted] == [("market_admin",)]


@pytest.mark.parametrize(
    "cell",
    ["cashier, inspector", "cashier;inspector", " Cashier ;  INSPECTOR "],
    ids=["comma", "semicolon", "case-and-space"],
)
def test_multi_role_cell_keeps_the_file_order(cell: str) -> None:
    """D-05: bir odam ham kassir, ham nazoratchi bo'lishi mumkin.

    Ajratgich `,` HAM, `;` HAM: admin qaysi birini yozishini oldindan
    bilib bo'lmaydi. Registr va atrofdagi bo'sh joy ahamiyatsiz, lekin
    NATIJA har doim `Role` qiymati shaklida yoziladi (D-16).
    """
    accepted, codes = validate(staff_row(2, "Aliyev Vali", "+998909910003", cell))

    assert codes == []
    assert [row.roles for row in accepted] == [("cashier", "inspector")]


def test_repeated_role_inside_one_cell_is_collapsed() -> None:
    """Katakdagi takroriy rol XATO EMAS — u siqiladi, tartib saqlanadi."""
    accepted, codes = validate(
        staff_row(2, "Aliyev Vali", "+998909910003", "inspector, cashier; inspector")
    )

    assert codes == []
    assert [row.roles for row in accepted] == [("inspector", "cashier")]


def test_full_name_and_row_number_are_preserved() -> None:
    """Qabul qilingan qator EXCEL raqamini va tozalangan ismini saqlaydi."""
    accepted, codes = validate(staff_row(88, "  Aliyev Vali  ", "+998909910003", "cashier"))

    assert codes == []
    assert accepted == [
        StaffImportRow(
            row=88,
            full_name="Aliyev Vali",
            phone="+998909910003",
            roles=("cashier",),
        )
    ]


# ===========================================================================
# D-15 — mavjud a'zo XATO EMAS va `accepted` ga ham tushmaydi
# ===========================================================================


def test_existing_member_phone_is_skipped_silently() -> None:
    """Mavjud a'zo — xatolar ro'yxatida YO'Q va `accepted` da ham YO'Q.

    Muqobil (parolni qayta berish) roster faylini OMMAVIY PAROL TIKLASH
    quroliga aylantirardi: eski faylni tasodifan qayta yuklagan admin
    butun jamoani tizimdan chiqarib yuborardi.
    """
    accepted, codes = validate(
        staff_row(2, "Aliyev Vali", "+998909910003", "cashier"),
        staff_row(3, "Valiyev Ali", "+998909910004", "inspector"),
        existing=("+998909910003",),
    )

    assert codes == []
    assert [row.phone for row in accepted] == ["+998909910004"]


def test_skip_branch_runs_after_the_error_branch() -> None:
    """Mavjud a'zoning qatoridagi NOTO'G'RI rol JIMGINA yutilmaydi.

    ⚠ Tartib teskari bo'lganda (avval skip, keyin tekshiruv) admin
    "rolni to'g'riladim" deb o'ylab yurardi, fayl esa aslida umuman
    o'qilmagan bo'lardi. `validate_stall_rows` dagi tartib AYNAN shu.
    """
    accepted, codes = validate(
        staff_row(2, "Aliyev Vali", "+998909910003", "market_admin"),
        existing=("+998909910003",),
    )

    assert accepted == []
    assert codes == ["role_not_allowed"]


def test_existing_member_is_still_checked_for_duplicates_inside_the_file() -> None:
    """Mavjud telefon faylda IKKI marta yozilsa — bu hamon xato."""
    _, codes = validate(
        staff_row(2, "Aliyev Vali", "+998909910003", "cashier"),
        staff_row(3, "Valiyev Ali", "+998909910003", "cashier"),
        existing=("+998909910003",),
    )

    assert codes == ["duplicate_phone_in_file"]
