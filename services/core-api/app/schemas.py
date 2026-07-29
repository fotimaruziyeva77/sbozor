"""HTTP kontrakt shakllari (Pydantic 2.13).

Chegara qoidalari shu yerda qulflanadi:

* **Telefon CHEGARADA normallashtiriladi** (D-01). `+998 90 123 45 67`,
  `998901234567` va `901234567` — uchtasi ham bitta foydalanuvchi. Agar
  normalizatsiya endpoint ichida qilinsa, bir kun kimdir uni unutadi va
  bitta odam ikkita hisob oladi (qarz tarixi ikkiga bo'linadi).
* **Parol siyosati BITTA joyda** — `validate_password_strength()`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sbozor_core.phone import InvalidPhoneError, normalize_phone

__all__ = [
    "MIN_PASSWORD_LENGTH",
    "ChangePasswordRequest",
    "LoginRequest",
    "LoginResponse",
    "MarketRef",
    "MeResponse",
    "RefreshResponse",
    "SelectMarketRequest",
    "SessionResponse",
    "validate_password_strength",
]

MIN_PASSWORD_LENGTH = 10
"""Minimal parol uzunligi (ASVS V6 — uzunlik murakkablikdan muhimroq).

Murakkablik qoidalari (katta harf/raqam/belgi) ATAYIN YO'Q: ular
foydalanuvchini `Parol123!` yozishga majburlaydi va entropiyani
oshirmaydi. D-02 bo'yicha vaqtinchalik parolni admin beradi va u birinchi
kirishda majburiy almashtiriladi.
"""


def validate_password_strength(value: str) -> bool:
    """Parol siyosatiga mos kelishini aytadi.

    Ikki qoida: (1) kamida `MIN_PASSWORD_LENGTH` belgi, (2) faqat bo'sh
    joydan iborat bo'lmasin. Ikkinchisi kerak, chunki `" " * 12` birinchi
    qoidadan o'tib ketardi.

    ATAYIN `bool` qaytaradi (`ValueError` ko'tarmaydi): chaqiruvchi
    endpoint uni `400 {"detail": "weak_password"}` ga aylantiradi. Agar
    tekshiruv Pydantic `field_validator` ichida bo'lganda, FastAPI 422
    qaytarardi va e'lon qilingan kontraktdan chetga chiqardi.
    """
    return len(value) >= MIN_PASSWORD_LENGTH and bool(value.strip())


class MarketRef(BaseModel):
    """Bozor havolasi — javoblarda faqat `id` va nom ko'rinadi."""

    id: UUID
    name: str


class LoginRequest(BaseModel):
    """`POST /auth/login` — telefon + parol (D-01)."""

    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi; o'qib bo'lmasa 422 (401 EMAS).

        Bu enumeration teshigi EMAS: 422 "raqam formati noto'g'ri" deydi,
        "bunday foydalanuvchi yo'q" demaydi. Mavjud bo'lmagan, lekin
        YAROQLI raqam odatdagi `401 invalid_credentials` ni oladi.
        """
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class LoginResponse(BaseModel):
    """`POST /auth/login` javobi.

    `market` `None` bo'lsa — bozor tanlanmagan (platforma admini yoki
    a'zoligi bir nechta bo'lgan foydalanuvchi); u holda `markets` ro'yxati
    to'ldiriladi va keyingi qadam `/auth/select-market`.
    """

    access_token: str
    # S105 — RFC 6750 dagi token TURI ("bearer"), sir emas: u har javobda
    # ochiq matnda ketadi va shunday bo'lishi kerak.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    must_change_password: bool
    locale: str
    market: MarketRef | None
    markets: list[MarketRef]
    roles: list[str]
    is_platform_admin: bool


class SelectMarketRequest(BaseModel):
    """`POST /auth/select-market` (D-06)."""

    market_id: UUID


class SessionResponse(BaseModel):
    """`/auth/select-market` va `/auth/refresh` uchun umumiy javob shakli."""

    access_token: str
    # S105 — RFC 6750 dagi token TURI ("bearer"), sir emas: u har javobda
    # ochiq matnda ketadi va shunday bo'lishi kerak.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    roles: list[str]
    market: MarketRef


RefreshResponse = SessionResponse
"""`/auth/refresh` javobi — `/select-market` bilan AYNAN bir xil shakl.

Ikkalasi ham "sessiya bozor kontekstiga bog'landi" degan bir xil faktni
qaytaradi, shuning uchun frontend uchun bitta tip yetarli.
"""


class ChangePasswordRequest(BaseModel):
    """`POST /auth/change-password` (D-02).

    `min_length=1` — uzunlik siyosati BU YERDA emas,
    `validate_password_strength()` da: kontrakt bo'yicha zaif parol
    `400 weak_password` beradi, Pydantic esa 422 berardi.
    """

    current_password: Annotated[str, Field(min_length=1)]
    new_password: Annotated[str, Field(min_length=1)]


class MeResponse(BaseModel):
    """`GET /auth/me` — joriy sessiya tavsifi (tenant kontekstidan o'qilgan)."""

    user_id: UUID
    market: MarketRef
    roles: list[str]
    permissions: list[str]
    is_platform_admin: bool
