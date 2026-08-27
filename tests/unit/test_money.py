"""`sbozor_core.money` — pul primitivlarining chegara xulq-atvori.

Pul HAR DOIM butun so'm (Python `int` <-> Postgres `BIGINT`). Bu fayl aynan
shu invariantni qulflaydi. Kasrli tiplar rad etilishi shart: yaxlitlanish
drift'i kunlik patta agregatlarida sotuvchi bilan nizoga aylanadi — ya'ni
mahsulot oldini olish uchun mavjud bo'lgan aynan o'sha nosozlik rejimiga.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from sbozor_core.enums import Locale
from sbozor_core.money import MAX_SAFE_SOUM, assert_safe_soum, format_soum

# Guruh ajratgichi — uzluksiz bo'shliq (U+00A0), oddiy bo'shliq EMAS.
# Ataylab escape bilan yozilgan: manba faylida ko'rinmas belgi bo'lmasin.
NBSP = chr(0x00A0)


def test_max_safe_soum_matches_js_number_max_safe_integer() -> None:
    """API JSON'da pul oddiy `number` bo'lib qoladi (Pitfall 7)."""
    assert MAX_SAFE_SOUM == 9_007_199_254_740_991


@pytest.mark.parametrize("value", [0, 1, 5_000, 50_000, 1_234_567, MAX_SAFE_SOUM])
def test_assert_safe_soum_returns_value_unchanged(value: int) -> None:
    assert assert_safe_soum(value) == value


@pytest.mark.parametrize("value", [-1, -50_000, MAX_SAFE_SOUM + 1, MAX_SAFE_SOUM * 2])
def test_assert_safe_soum_rejects_out_of_range(value: int) -> None:
    with pytest.raises(ValueError):
        assert_safe_soum(value)


@pytest.mark.parametrize(
    "value",
    [5000.0, 0.1, -0.0, Decimal("5000"), "5000", None, [5000]],
)
def test_assert_safe_soum_rejects_non_int_types(value: Any) -> None:
    with pytest.raises(TypeError):
        assert_safe_soum(value)


@pytest.mark.parametrize("value", [True, False])
def test_assert_safe_soum_rejects_bool(value: bool) -> None:
    """`bool` — `int` ning bolasi, shuning uchun ALOHIDA tekshirilishi shart."""
    with pytest.raises(TypeError):
        assert_safe_soum(value)


@pytest.mark.parametrize(
    ("locale", "unit"),
    [("uz-Latn", "so'm"), ("uz-Cyrl", "сўм"), ("ru", "сум")],
)
def test_format_soum_uses_locale_unit(locale: str, unit: str) -> None:
    assert format_soum(1_234_567, locale) == f"1{NBSP}234{NBSP}567{NBSP}{unit}"


def test_format_soum_has_no_fraction_part() -> None:
    """Tiyin yo'q: so'm butun son, kasr qismi hech qachon chiqmaydi."""
    formatted = format_soum(1_234_567, "uz-Latn")
    assert "." not in formatted
    assert "," not in formatted


def test_format_soum_groups_with_non_breaking_space() -> None:
    assert format_soum(1_000_000, "uz-Latn") == f"1{NBSP}000{NBSP}000{NBSP}so'm"


def test_format_soum_short_value_has_no_group_separator() -> None:
    assert format_soum(500, "uz-Latn") == f"500{NBSP}so'm"


def test_format_soum_accepts_locale_enum() -> None:
    assert format_soum(500, Locale.UZ_CYRL) == f"500{NBSP}сўм"


def test_format_soum_rejects_unknown_locale() -> None:
    with pytest.raises(ValueError):
        format_soum(500, "en-US")


def test_format_soum_keeps_negative_sign_for_adjustments() -> None:
    """`charge_adjustments` chegirmasi manfiy bo'lishi mumkin."""
    assert format_soum(-1_500, "uz-Latn") == f"-1{NBSP}500{NBSP}so'm"


@pytest.mark.parametrize("value", [5000.0, True, Decimal("5000")])
def test_format_soum_rejects_non_int(value: Any) -> None:
    with pytest.raises(TypeError):
        format_soum(value, "uz-Latn")
