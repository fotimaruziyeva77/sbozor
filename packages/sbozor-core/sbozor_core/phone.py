"""Telefon normalizatsiyasi — E.164 (D-01).

Login identifikatori — telefon raqami, ya'ni u foydalanuvchining YAGONA
kaliti. Agar bir xil raqam ikki xil shaklda saqlansa (`+998901234567` va
`901234567`), bitta odam ikkita foydalanuvchi bo'lib qoladi va uning
qarz/to'lov tarixi ikkiga bo'linadi — bu D-01 ning to'g'ridan-to'g'ri
buzilishi.

Regex bilan QILINMAYDI (Don't Hand-Roll): formatlar juda ko'p va milliy
prefiks qoidalari kutubxonada CLDR ma'lumotlari bilan yashaydi.
Normalizatsiya CHEGARADA bajariladi — DB'ga faqat E.164 tushadi.
"""

from __future__ import annotations

import phonenumbers

__all__ = ["DEFAULT_REGION", "InvalidPhoneError", "normalize_phone"]

DEFAULT_REGION = "UZ"
"""`+` siz kelgan raqamlar shu mamlakat uchun milliy raqam deb o'qiladi."""


class InvalidPhoneError(ValueError):
    """Telefon raqami o'qib bo'lmadi yoki haqiqiy raqam emas.

    `ValueError` dan meros oladi: chaqiruvchi umumiy validatsiya xatosi
    sifatida ham ushlay oladi, API qatlami esa 422 ga tarjima qiladi.
    """


def normalize_phone(raw: str) -> str:
    """Istalgan yozilish shaklini yagona E.164 satriga keltiradi.

    `"+998901234567"`, `"998901234567"`, `"+998 90 123 45 67"` va
    `"90 123 45 67"` — to'rttasi ham `"+998901234567"` beradi.

    Raises:
        InvalidPhoneError: raqam tahlil qilinmasa yoki haqiqiy bo'lmasa.
    """
    candidate = raw.strip()
    try:
        parsed = phonenumbers.parse(candidate, DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneError(f"telefon raqamini o'qib bo'lmadi: {raw!r} ({exc})") from exc

    # `is_valid_number` — uzunlik VA prefiks tekshiruvi (`is_possible_number`
    # dan qat'iyroq): "12345" mumkin bo'lgan uzunlikda emas, "+998 00 ..." esa
    # mavjud bo'lmagan operator prefiksi bilan o'tib ketardi.
    if not phonenumbers.is_valid_number(parsed):
        raise InvalidPhoneError(f"telefon raqami haqiqiy emas: {raw!r}")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
