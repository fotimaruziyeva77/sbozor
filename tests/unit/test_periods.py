"""`sbozor_core.periods` — `[)` chegara konventsiyasini qulflaydi.

Bu testlar RESEARCH da EMPIRIK o'lchangan chegara jadvalini (D-10 almashinuv
stsenariysi) kod qatlamida takrorlaydi. Ular "kod nima qilsa shuni
tasdiqlash" emas: kutilgan qiymatlar haqiqiy `postgres:18.4` da
`daterange`/`@>` bilan o'lchangan natijalardan olingan, ya'ni kod-qatlami DB
bilan bir xil javob berishini isbotlaydi. Ikkalasi ajralib ketsa, almashinuv
kunidagi patta ikki marta yoki umuman yozilmay qoladi (6-faza).
"""

from __future__ import annotations

from datetime import date

import pytest
from sbozor_core.periods import PERIOD_BOUNDS, assignment_period, period_contains

# D-10 empirik stsenariysi: 08-10 kuni rasta YANGI sotuvchiga o'tadi.
HANDOVER = date(2026, 8, 10)
OLD_VENDOR_PERIOD = assignment_period(date(2026, 8, 1), HANDOVER)
NEW_VENDOR_PERIOD = assignment_period(HANDOVER, None)


def test_period_bounds_is_the_single_convention() -> None:
    """`'[]'` ga o'zgarishi almashinuv kunini IKKALA sotuvchiga bog'lab qo'yardi."""
    assert PERIOD_BOUNDS == "[)"


def test_upper_bound_day_belongs_to_the_next_vendor() -> None:
    """`[08-01, 08-10)` — 08-09 kiradi, 08-10 KIRMAYDI (D-10)."""
    assert period_contains(OLD_VENDOR_PERIOD, date(2026, 8, 9)) is True
    assert period_contains(OLD_VENDOR_PERIOD, HANDOVER) is False


def test_handover_day_belongs_to_exactly_one_vendor() -> None:
    """Almashinuv kuni AYNAN bitta davrga tegishli — ikkiga ham, nolga ham emas.

    Nazorat holati: yuqoridagi test yolg'iz o'zi `'(]'` konventsiyasida ham
    yashil bo'lardi (o'sha holatda 08-10 eski sotuvchiga tegishli bo'lardi).
    Bu yerda ikkala davr BIRGA tekshiriladi.
    """
    holders = [
        period_contains(period, HANDOVER) for period in (OLD_VENDOR_PERIOD, NEW_VENDOR_PERIOD)
    ]
    assert holders == [False, True]


def test_lower_bound_day_is_included() -> None:
    assert period_contains(OLD_VENDOR_PERIOD, date(2026, 8, 1)) is True
    assert period_contains(OLD_VENDOR_PERIOD, date(2026, 7, 31)) is False


def test_open_ended_period_has_no_upper_bound() -> None:
    """Ishlab turgan sotuvchi — `upper is None`, hech qanday sentinel sana emas.

    `date(9999, 12, 31)` kabi "cheksizlik" qiymati DB'da oddiy sana bo'lib
    qolardi va `LEAD`/hisobotlarda haqiqiy sana kabi ko'rinardi.
    """
    period = assignment_period(HANDOVER, None)

    assert period.lower == HANDOVER
    assert period.upper is None
    assert period.bounds == "[)"
    assert period_contains(period, date(2030, 1, 1)) is True


def test_empty_period_is_rejected() -> None:
    """`[d, d)` — Postgres uchun BO'SH davr: `&&` uni hech narsa bilan kesmaydi."""
    day = date(2026, 8, 10)

    with pytest.raises(ValueError, match="KEYIN"):
        assignment_period(day, day)


def test_reversed_period_is_rejected() -> None:
    """Teskari davr DB'ga yetib borsa `range_bounds_invalid` bo'lardi — chegarada to'xtaydi."""
    with pytest.raises(ValueError, match="KEYIN"):
        assignment_period(date(2026, 8, 10), date(2026, 8, 1))


def test_single_day_assignment_uses_the_next_day_as_upper_bound() -> None:
    """Bir kunlik biriktirish — `[d, d+1)`. Xato xabari aynan shuni ko'rsatadi."""
    period = assignment_period(date(2026, 8, 10), date(2026, 8, 11))

    assert period_contains(period, date(2026, 8, 10)) is True
    assert period_contains(period, date(2026, 8, 11)) is False
