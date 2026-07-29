"""`sbozor_core.phone` — E.164 normalizatsiyasi (D-01).

Login identifikatori — telefon raqami. Agar bir xil raqam ikki xil shaklda
saqlansa, bitta odam ikkita foydalanuvchi bo'lib qoladi va qarz/to'lov tarixi
ikkiga bo'linadi. Shuning uchun normalizatsiya CHEGARADA (parse paytida)
bajariladi va bu yerda to'rt xil kirish shakli bilan qulflanadi.
"""

from __future__ import annotations

import pytest

from sbozor_core.phone import InvalidPhoneError, normalize_phone

E164 = "+998901234567"


def test_invalid_phone_error_is_value_error() -> None:
    """Chaqiruvchi `ValueError` bilan ham ushlay olishi kerak."""
    assert issubclass(InvalidPhoneError, ValueError)


@pytest.mark.parametrize(
    "raw",
    [
        "+998901234567",  # allaqachon E.164
        "998901234567",  # `+` siz, mamlakat kodi bilan
        "+998 90 123 45 67",  # bo'shliqlar bilan
        "90 123 45 67",  # faqat milliy raqam
        "901234567",  # milliy raqam, ajratgichsiz
        "+998 (90) 123-45-67",  # qavs va tire bilan
        "  +998901234567  ",  # atrofida bo'shliq
        "+998-90-123-45-67",
    ],
)
def test_normalize_phone_collapses_input_shapes_to_one_value(raw: str) -> None:
    assert normalize_phone(raw) == E164


def test_normalize_phone_output_is_strict_e164() -> None:
    out = normalize_phone("+998 90 123 45 67")
    assert out.startswith("+")
    assert out[1:].isdigit()
    assert " " not in out


def test_normalize_phone_is_idempotent() -> None:
    once = normalize_phone("90 123 45 67")
    assert normalize_phone(once) == once


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "12345",
        "abc",
        "+998",
        "+9989012345678901",
        "0",
        "+998 90 123 45 6",  # bitta raqam kam
    ],
)
def test_normalize_phone_rejects_invalid(raw: str) -> None:
    with pytest.raises(InvalidPhoneError):
        normalize_phone(raw)


def test_normalize_phone_error_message_mentions_input() -> None:
    """Xato xabari diagnostika uchun kirishni ko'rsatadi (sir emas)."""
    with pytest.raises(InvalidPhoneError) as excinfo:
        normalize_phone("12345")
    assert "12345" in str(excinfo.value)
