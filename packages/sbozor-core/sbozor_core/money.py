"""Pul primitivlari — so'm HAR DOIM butun son.

TAQIQ: pul uchun `float` (yoki `Decimal`) ISHLATILMAYDI. Postgres tomonda
`BIGINT`, Python tomonda `int`. Sabab mahsulotning o'zagida: kunlik patta
agregatlaridagi yaxlitlanish drift'i sotuvchi bilan nizoga aylanadi — ya'ni
SBOZOR oldini olish uchun mavjud bo'lgan aynan o'sha nosozlik rejimiga.

Tiyin yo'q: eng kichik birlik — 1 so'm, shuning uchun masshtablovchi ko'paytma
(`* 100`) ham kerak emas.
"""

from __future__ import annotations

__all__ = ["MAX_SAFE_SOUM", "Soum", "assert_safe_soum", "format_soum"]

type Soum = int
"""Pul miqdori — butun so'm. Semantik nom, alohida tip emas."""

MAX_SAFE_SOUM: int = 9_007_199_254_740_991
"""JavaScript `Number.MAX_SAFE_INTEGER`.

API javoblarida pul oddiy JSON `number` bo'lib qoladi (satrga o'tish keraksiz
murakkablik), lekin `BIGINT` maksimumi ~9.2e18 va JS xavfsiz chegarasi 9.007e15
— oradagi qiymat JSON orqali JIMGINA yaxlitlanadi. MVP hajmi (1000 rasta x
365 kun x 50 000 so'm ~ 1.8e10) chegaradan besh daraja past, shuning uchun bu
konstanta amalda faqat agregatlar uchun himoya to'ri (Pitfall 7).
"""

# Guruh ajratgichi — uzluksiz bo'shliq (U+00A0). `chr()` bilan yozilgan:
# manba faylida ko'rinmas belgi bo'lmasligi kerak.
_GROUP_SEPARATOR = chr(0x00A0)

# Birlik locale bo'yicha. Kalitlar `sbozor_core.enums.Locale` qiymatlari bilan
# aynan mos (`Locale` — `StrEnum`, shuning uchun a'zoni to'g'ridan-to'g'ri
# kalit sifatida uzatish ham ishlaydi).
_UNIT_BY_LOCALE: dict[str, str] = {
    "uz-Latn": "so'm",
    "uz-Cyrl": "сўм",
    "ru": "сум",
}


def _reject_non_integer(value: object) -> None:
    """Butun son bo'lmagan har qanday qiymatni `TypeError` bilan rad etadi."""
    # `bool` — `int` ning bolasi, shuning uchun ALOHIDA va BIRINCHI tekshiriladi:
    # `isinstance(True, int)` -> True, ya'ni oddiy tekshiruv uni o'tkazib yuboradi
    # va `True` jimgina 1 so'm bo'lib qoladi.
    if isinstance(value, bool):
        raise TypeError(
            f"pul qiymati mantiqiy tip bo'la olmaydi: {value!r} — "
            "`bool` `int` ning bolasi, shuning uchun alohida rad etiladi"
        )
    if isinstance(value, float):
        raise TypeError(
            f"pul qiymati kasrli tipda bo'la olmaydi: {value!r} — TAQIQ, chunki "
            "yaxlitlanish drift'i patta agregatida nizoga aylanadi; butun so'm ishlating"
        )
    if not isinstance(value, int):
        raise TypeError(
            f"pul qiymati butun son bo'lishi kerak, berilgani: {type(value).__name__} "
            f"({value!r}) — so'm Postgres tomonda BIGINT"
        )


def assert_safe_soum(value: int) -> Soum:
    """Pul miqdorini tekshiradi va O'ZINI qaytaradi (chegarada ishlatiladi).

    Qoidalar:
    * kasrli va mantiqiy tiplar -> `TypeError`
    * manfiy qiymat -> `ValueError` (miqdor manfiy bo'lmaydi; chegirma
      `charge_adjustments` da alohida yozuv sifatida saqlanadi)
    * `MAX_SAFE_SOUM` dan katta -> `ValueError`

    Agregat hisoblagandan keyin (kunlik/oylik tushum) natijani shu funksiyadan
    o'tkazing — JSON chegarasi aynan o'sha yerda buziladi.
    """
    _reject_non_integer(value)
    if value < 0:
        raise ValueError(f"pul miqdori manfiy bo'la olmaydi: {value}")
    if value > MAX_SAFE_SOUM:
        raise ValueError(
            f"pul miqdori JSON uchun xavfsiz chegaradan oshdi: {value} > {MAX_SAFE_SOUM}"
        )
    return value


def format_soum(value: int, locale: str) -> str:
    """Ko'rsatish uchun formatlaydi: `1<NBSP>234<NBSP>567<NBSP>so'm`.

    `assert_safe_soum` dan farqi — MANFIY qiymatni qabul qiladi, chunki
    `charge_adjustments` chegirmasi va qoldiq farqi ekranda minus bilan
    ko'rsatiladi. Kattalik chegarasi baribir tekshiriladi.

    Kasr qismi hech qachon chiqmaydi (tiyin yo'q). Ajratgich — uzluksiz
    bo'shliq, shunda summa satr oxirida ikkiga bo'linib ketmaydi.
    """
    _reject_non_integer(value)
    if abs(value) > MAX_SAFE_SOUM:
        raise ValueError(
            f"pul miqdori JSON uchun xavfsiz chegaradan oshdi: {value} (|v| > {MAX_SAFE_SOUM})"
        )

    key = str(locale)
    unit = _UNIT_BY_LOCALE.get(key)
    if unit is None:
        supported = ", ".join(sorted(_UNIT_BY_LOCALE))
        raise ValueError(f"noma'lum locale: {locale!r} — qo'llab-quvvatlanadigani: {supported}")

    grouped = f"{abs(value):,}".replace(",", _GROUP_SEPARATOR)
    sign = "-" if value < 0 else ""
    return f"{sign}{grouped}{_GROUP_SEPARATOR}{unit}"
