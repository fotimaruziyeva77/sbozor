"""To'lovning patta va tarozi qismi — buxgalter panelining qoidasi (261108).

Kutilgan sonlar Karmana narxlarida: patta 22 000, tarozi 4 000.
"""

from __future__ import annotations

import pytest
from sbozor_core.billing import payment_fee_part

TARIFF = 22_000
FEE = 4_000


@pytest.mark.parametrize(
    ("amount", "before", "expected_fee"),
    [
        pytest.param(26_000, 0, 4_000, id="to'liq: patta + tarozi"),
        pytest.param(22_000, 0, 0, id="kassir tarozini olmagan"),
        pytest.param(10_000, 0, 0, id="pattaning bir qismi"),
        pytest.param(24_000, 0, 2_000, id="tarozining bir qismi"),
        pytest.param(4_000, 22_000, 4_000, id="tarozi keyinroq alohida olingan"),
        pytest.param(52_000, 0, 8_000, id="ikki kunlik to'lov"),
        pytest.param(26_000, 26_000, 4_000, id="ikkinchi kunning to'lovi"),
        pytest.param(30_000, 0, 4_000, id="ortig'i keyingi kunning pattasi"),
    ],
)
def test_money_covers_the_stall_first_then_the_fee(
    amount: int, before: int, expected_fee: int
) -> None:
    assert (
        payment_fee_part(amount, paid_before_soum=before, tariff_soum=TARIFF, fee_soum=FEE)
        == expected_fee
    )


@pytest.mark.parametrize("tariff", [None, 0])
def test_without_a_tariff_everything_is_stall_money(tariff: int | None) -> None:
    """Tarif noma'lum — tarozi qaysi summadan keyin boshlanishini aytib bo'lmaydi."""
    assert payment_fee_part(26_000, paid_before_soum=0, tariff_soum=tariff, fee_soum=FEE) == 0


def test_a_market_without_a_fee_has_no_fee_money() -> None:
    assert payment_fee_part(26_000, paid_before_soum=0, tariff_soum=TARIFF, fee_soum=0) == 0


@pytest.mark.parametrize("first", [1, 4_000, 21_999, 22_000, 22_001, 26_000, 48_000])
def test_splitting_a_payment_in_two_does_not_change_the_fee(first: int) -> None:
    """To'lov ikkiga bo'lib yozilsa ham jami tarozi o'zgarmaydi."""
    total = 78_000
    whole = payment_fee_part(total, paid_before_soum=0, tariff_soum=TARIFF, fee_soum=FEE)
    head = payment_fee_part(first, paid_before_soum=0, tariff_soum=TARIFF, fee_soum=FEE)
    tail = payment_fee_part(total - first, paid_before_soum=first, tariff_soum=TARIFF, fee_soum=FEE)
    assert head + tail == whole == 12_000
