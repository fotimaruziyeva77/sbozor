"""Ko'r deklaratsiya farqi — IKKI TOMONLAMA, LITERAL JADVAL (CASH-04, D-26).

=============================================================================
D-26 NING MEXANIK YARIMI SHU FAYLDA O'LCHANADI.

Qaror matni: «Variance IKKI TOMONLAMA ko'rsatiladi (kam ham, ortiq ham) va
hech qachon avtomatik "to'g'rilanmaydi". Ortiqcha naqd ham signal — uni
jimgina yutish kamomadni yashirish bilan BIR XIL xato.»

Kodda bu bitta jumlaga siqiladi: natija `assert_safe_soum()` dan
O'TKAZILMAYDI va modul qiymatga (musbat kattalikka) aylantirilmaydi.
Ikkalasi ham «tuzatish» ko'rinishida keladi va ikkalasi ham D-26 ni
BEKOR QILADI:

  * natijani `assert_safe_soum()` ga berish -> kamomad `ValueError` bo'lardi
    va smena YOPILMASDI (kassir kam pul topshirsa tizim ishlamay qolardi);
  * `abs` funksiyasini qo'llash -> kamomad bilan ortiqcha EKRANDA BIR XIL
    ko'rinardi va direktor farqni umuman ajrata olmasdi.

⛔ SHUNING UCHUN JADVALDA IKKALA YO'NALISH HAM BOR va ular bir-birining
   AKS-SINOVI: faqat musbat natijalarni yozish `abs` sabotajini o'tkazib
   yuborardi.
=============================================================================
"""

from __future__ import annotations

from typing import Final

import pytest
from sbozor_core.billing import variance

VARIANCE_TABLE: Final[tuple[tuple[int, int, int], ...]] = (
    # (declared, system, kutilgan BELGILI natija)
    (0, 0, 0),
    (100, 0, 100),
    (0, 100, -100),
    (1_200_000, 1_235_000, -35_000),
    (1_235_000, 1_200_000, 35_000),
    (15_000, 15_000, 0),
    # ⛔ NOL DEKLARATSIYA — REAL HOLAT (butun smena terminal bo'lgan kun,
    #    UI-SPEC §10.2). Uni rad etish kassirni YOLG'ON son kiritishga
    #    majburlardi.
    (0, 450_000, -450_000),
)
"""Yetti holat, QO'LDA yozilgan.

`(1_200_000, 1_235_000)` va `(1_235_000, 1_200_000)` IKKALASI HAM bor va
bu ataylab: ular AYNAN teskari ishorali natija berishi kerak. Faqat
bittasini yozish `abs` sabotajini o'tkazib yuborardi.
"""


def test_the_variance_table_covers_every_case() -> None:
    """NAZORAT: jadval to'liq va ikkala YO'NALISH ham vakillangan.

    ⚠ USIZ `parametrize` JIMGINA BO'SHAB QOLISHI mumkin edi va to'plam
      «hammasi o'tdi» deb tugardi.
    """
    assert len(VARIANCE_TABLE) == 7, f"{len(VARIANCE_TABLE)} qator, 7 kutilgan"

    negatives = [row for row in VARIANCE_TABLE if row[2] < 0]
    positives = [row for row in VARIANCE_TABLE if row[2] > 0]
    zeros = [row for row in VARIANCE_TABLE if row[2] == 0]

    assert negatives, "KAMOMAD holati yo'q — `abs` sabotaji o'lchanmasdi"
    assert positives, "ORTIQCHA holati yo'q — D-26 ning yarmi sinalmasdi"
    assert zeros, "TENG holati yo'q — nazorat nuqtasi yo'qoladi"


@pytest.mark.parametrize(("declared", "system", "expected"), VARIANCE_TABLE)
def test_variance_matches_the_literal_table(declared: int, system: int, expected: int) -> None:
    """Har holat — QO'LDA yozilgan BELGILI kutilgan qiymat bilan."""
    assert variance(declared, system) == expected


def test_negative_result_does_not_raise() -> None:
    """⛔ D-26 NING MEXANIK YARIMI: manfiy natija ISTISNO KO'TARMAYDI.

    `assert_safe_soum()` manfiy qiymatni RAD ETADI (`money.py:78-79`) —
    ya'ni natijani o'sha funksiyadan o'tkazish kamomadni istisnoga
    aylantirardi va smena umuman yopilmasdi. Bu test aynan o'sha
    «xavfsizroq ko'rinadigan» tuzatishni bloklaydi.
    """
    result = variance(0, 1_000_000)
    assert result == -1_000_000
    assert isinstance(result, int)


def test_the_result_is_not_a_magnitude() -> None:
    """Kamomad va ortiqcha BIR XIL songa aylanmaydi — ishora saqlanadi."""
    shortfall = variance(1_200_000, 1_235_000)
    surplus = variance(1_235_000, 1_200_000)

    assert shortfall != surplus, (
        "kamomad va ortiqcha bir xil qiymat berdi — ishora yo'qolgan (D-26 bekor bo'lgan)"
    )
    assert shortfall + surplus == 0, "ikki yo'nalish simmetrik bo'lishi kerak"


@pytest.mark.parametrize(("declared", "system"), [(-1, 0), (0, -1), (-5_000, -5_000)])
def test_negative_input_is_rejected(declared: int, system: int) -> None:
    """Manfiy KIRISH `ValueError` beradi — deklaratsiya ham, tizim summasi ham.

    ⚠ KIRISH va NATIJA qoidalari ATAYIN boshqa: kirish SAQLANADIGAN
      miqdor (`cashier_shifts.declared_soum`, `BIGINT`), natija esa
      HOSILA. `money.py` da ikkalasi uchun ikki funksiya bor va sabab
      aynan shu (`assert_safe_soum` vs `format_soum`).
    """
    with pytest.raises(ValueError, match="manfiy"):
        variance(declared, system)


@pytest.mark.parametrize(
    ("declared", "system"),
    [(1.0, 0), (0, 1.0), (15_000.5, 15_000), (True, 0), (0, False)],
)
def test_fractional_and_boolean_input_is_rejected(declared: object, system: object) -> None:
    """Kasrli va mantiqiy tip `TypeError` beradi (D-11).

    ⚠ `bool` ALOHIDA holat: u `int` ning bolasi, ya'ni oddiy `isinstance`
      tekshiruvi `True` ni JIMGINA 1 so'm qilib qo'yardi (`money.py:45-52`).
    """
    with pytest.raises(TypeError):
        variance(declared, system)  # type: ignore[arg-type]
