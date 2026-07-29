"""HTTP kontrakt shakllari (Pydantic 2.13).

Chegara qoidalari shu yerda qulflanadi:

* **Telefon CHEGARADA normallashtiriladi** (D-01). `+998 90 123 45 67`,
  `998901234567` va `901234567` — uchtasi ham bitta foydalanuvchi. Agar
  normalizatsiya endpoint ichida qilinsa, bir kun kimdir uni unutadi va
  bitta odam ikkita hisob oladi (qarz tarixi ikkiga bo'linadi).
* **Parol siyosati BITTA joyda** — `validate_password_strength()`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sbozor_core.enums import Locale, Role
from sbozor_core.phone import InvalidPhoneError, normalize_phone

__all__ = [
    "AUDIT_PAGE_SIZE_MAX",
    "MIN_PASSWORD_LENGTH",
    "AuditEntry",
    "AuditListResponse",
    "AuditQuery",
    "ChangePasswordRequest",
    "CreateUserRequest",
    "CreateUserResponse",
    "LocaleResponse",
    "LoginRequest",
    "LoginResponse",
    "MarketListItem",
    "MarketRef",
    "MeResponse",
    "ProfileResponse",
    "RefreshResponse",
    "ResetPasswordResponse",
    "SelectMarketRequest",
    "SessionResponse",
    "UpdateProfileRequest",
    "UserListItem",
    "UserListResponse",
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


# ---------------------------------------------------------------------------
# Foydalanuvchi boshqaruvi (D-04, D-02, D-08)
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    """`POST /users` — ikki bosqichli yaratishning so'rov shakli (D-04).

    `roles` `Role` enum ustida: noma'lum rol nomi 422 beradi va u hech
    qachon `user_market_roles.roles` ga yetib bormaydi. KIM qaysi rolni
    bera olishi (rol berish DARAJASI) esa bu yerda EMAS — u endpoint
    mantiqida, chunki javob 403 bo'lishi kerak, 422 emas: so'rov shakli
    to'g'ri, huquq yetmaydi.
    """

    phone: str
    full_name: str | None = None
    roles: Annotated[list[Role], Field(min_length=1)]
    locale: Locale = Locale.UZ_LATN

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi (D-01: telefon — yagona identifikator)."""
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class CreateUserResponse(BaseModel):
    """`POST /users` javobi — vaqtinchalik parol BIR MARTA ochiq qaytariladi.

    Parol DB'da faqat Argon2id hash sifatida yashaydi, ya'ni uni qaytadan
    ko'rsatish IMKONSIZ. Admin uni yo'qotsa yagona yo'l — `reset-password`
    bilan yangisini berish (D-02).
    """

    id: UUID
    temporary_password: str


class ResetPasswordResponse(BaseModel):
    """`POST /users/{id}/reset-password` javobi (D-02)."""

    temporary_password: str


class UserListItem(BaseModel):
    """`GET /users` ro'yxatining bir qatori.

    `password_hash` bu yerda YO'Q va bo'lishi ham mumkin emas: uni
    `auth_list_users()` umuman qaytarmaydi.
    """

    id: UUID
    phone: str
    full_name: str | None
    roles: list[str]
    is_active: bool
    must_change_password: bool
    locale: str
    created_at: datetime


class UserListResponse(BaseModel):
    """`GET /users` — joriy bozor a'zolari."""

    items: list[UserListItem]


# ---------------------------------------------------------------------------
# Profil va bozor konteksti (D-13, D-06)
# ---------------------------------------------------------------------------


class ProfileResponse(BaseModel):
    """`GET /api/v1/me` — profil + sessiya konteksti.

    `GET /auth/me` (01-06) dan FARQI: u sessiya tavsifi (bozor NOMI va
    huquqlar ro'yxati) va tenant konteksti O'RNATILGAN bo'lishini talab
    qiladi. Bu esa PROFIL: u bozor tanlanmagan holatda ham ishlaydi
    (`market_id: null`), chunki platforma admini bozor tanlashdan oldin ham
    o'z tilini va ismini ko'rishi kerak.
    """

    id: UUID
    phone: str
    full_name: str | None
    locale: str
    roles: list[str]
    market_id: UUID | None
    is_platform_admin: bool
    must_change_password: bool


class UpdateProfileRequest(BaseModel):
    """`PATCH /api/v1/me` — hozircha faqat til (D-13).

    `Locale` enum: `uz-Latn`, `uz-Cyrl`, `ru`. Boshqa qiymat 422 beradi va
    `frontend/src/i18n/routing.ts` dagi ro'yxat bilan AYNAN mos bo'lishi
    `tests/integration/test_me_locale.py` da qulflangan.
    """

    locale: Locale


class LocaleResponse(BaseModel):
    """`PATCH /api/v1/me` javobi — saqlangan til."""

    locale: str


class MarketListItem(BaseModel):
    """`GET /api/v1/markets` qatori (D-06)."""

    id: UUID
    name: str
    timezone: str
    is_active: bool


# ---------------------------------------------------------------------------
# Audit ko'rish (D-11, D-12)
# ---------------------------------------------------------------------------

AUDIT_PAGE_SIZE_MAX = 200
"""`GET /audit?limit=` ning yuqori chegarasi (T-01-57).

Chegarasiz so'rov bitta so'rovda butun jurnalni JSON'ga aylantirardi —
bu DoS emas, o'z-o'ziga DoS: jurnal o'sib boradi va bir kun bitta
"limit=1000000" so'rovi API'ni yiqitadi. Keyingi sahifa kursor bilan
olinadi — sahifa raqami bilan emas (sababi
`app/repositories/audit_repo.py` modul docstringida).
"""


class AuditQuery(BaseModel):
    """`GET /audit` query parametrlari (D-12).

    `from`/`to` — Python kalit so'zi bilan to'qnashadi, shuning uchun
    maydon nomi `date_from`/`date_to` va tashqi nom alias orqali beriladi.
    Filtr `business_date` USTUNI bo'yicha ishlaydi, vaqt tamg'asini
    yaxlitlovchi ifoda bilan emas: biznes-kun `Asia/Tashkent` bo'yicha DB
    tomonda hisoblanadi va uning ustida indeks bor.
    """

    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    actor_user_id: UUID | None = None
    action: str | None = None
    table_name: str | None = None
    limit: Annotated[int, Field(ge=1, le=AUDIT_PAGE_SIZE_MAX)] = 50
    cursor: str | None = None


class AuditEntry(BaseModel):
    """`audit_log` qatorining tashqi ko'rinishi (kim/qachon/nima/eski->yangi).

    `old_value`/`new_value` JSONB'lari qaytariladi, LEKIN sezgir kalitlar
    `app.repositories.audit_repo.mask_sensitive()` bilan `"***"` ga
    almashtiriladi (T-01-52).
    """

    id: int
    at: datetime
    business_date: date
    actor_user_id: UUID | None
    actor_label: str | None
    action: str
    table_name: str
    row_id: UUID | None
    changed_keys: list[str] | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    request_id: str | None
    source: str


class AuditListResponse(BaseModel):
    """`GET /audit` — sahifa + keyingi kursor (`null` bo'lsa oxirgi sahifa)."""

    items: list[AuditEntry]
    next_cursor: str | None
