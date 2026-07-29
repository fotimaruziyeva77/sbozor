"""JWT chiqarish/tekshirish va refresh cookie'si — `sbozor_core.security` ustidagi yupqa qatlam.

Bu modul KRIPTOGRAFIYA QILMAYDI: u faqat `Settings` dagi qiymatlarni
`sbozor_core.security` funksiyalariga bog'laydi va cookie atributlarini
BITTA joyda saqlaydi. Har endpoint cookie'ni o'zi qo'yganda `HttpOnly` yoki
`Path` ni unutish — bir satrlik xato, oqibati esa XSS yoki CSRF yuzasi.

COOKIE ATRIBUTLARI VA ULARNING SABABI (D-03, T-01-42/T-01-43):

| Atribut            | Qiymat            | Nimani yopadi                          |
| ------------------ | ----------------- | -------------------------------------- |
| `HttpOnly`         | doimo             | XSS orqali `document.cookie` o'qishi    |
| `Secure`           | prod'da           | TLS'siz yuborilishi (dev'da HTTP)      |
| `SameSite`         | `lax`             | cross-site POST bilan CSRF             |
| `Path`             | `/api/v1/auth`    | cookie boshqa endpointlarga umuman     |
|                    |                   | yuborilmaydi -> CSRF yuzasi kichrayadi |
| `Max-Age`          | 30 kun            | D-03 sliding sessiya                   |

`SameSite=Lax` YETARLI, chunki topologiya BITTA DOMEN: `ops/nginx/nginx.conf`
frontend va API'ni bir xost ostida beradi (01-01), ya'ni brauzer uchun bu
same-site so'rov. Ikki domenli topologiyaga o'tilsa `SameSite=None; Secure`
va alohida CSRF tokeni kerak bo'ladi — o'shanda bu jadval yangilanadi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import Response
from sbozor_core.security import TokenClaims, decode_token, encode_access, encode_refresh

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.settings import Settings

__all__ = [
    "COOKIE_PATH",
    "IssuedRefresh",
    "REFRESH_COOKIE_NAME",
    "SECONDS_PER_DAY",
    "clear_refresh_cookie",
    "cleared_cookie_headers",
    "decode",
    "issue_access",
    "issue_refresh",
    "refresh_cookie_max_age",
    "set_refresh_cookie",
]

REFRESH_COOKIE_NAME = "sbozor_rt"
"""Refresh cookie nomi.

`app/api/v1/auth.py` da `Cookie(alias=...)` uchun LITERAL takrorlanadi —
FastAPI alias'i OpenAPI sxemasiga tushadi va u yerda o'zgaruvchi bo'la
olmaydi. Ikkalasining mosligi
`tests/integration/test_auth_login.py::test_refresh_cookie_name_matches_tokens_constant`
bilan qulflangan (01-03 dagi `algorithms=["HS256"]` bilan bir xil qoida).
"""

COOKIE_PATH = "/api/v1/auth"
"""Cookie yuboriladigan YAGONA yo'l prefiksi (CSRF yuzasini toraytiradi)."""

SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class IssuedRefresh:
    """Chiqarilgan refresh token va uni DB'ga yozish uchun kerakli maydonlar.

    `jti` ilova tomonda hosil qilinadi: rotatsiya AVVAL DB'ga yozadi, keyin
    aynan o'sha identifikator bilan token beradi — aks holda token
    berilib, DB yozuvi yiqilsa, sessiya "mavjud, lekin topilmaydigan"
    holatga tushardi.
    """

    token: str
    jti: str
    family_id: UUID
    expires_at: datetime


def issue_access(
    *,
    user_id: UUID,
    market_id: UUID | None,
    roles: Sequence[str],
    is_platform_admin: bool,
    settings: Settings,
) -> str:
    """15 daqiqalik access token (D-03)."""
    return encode_access(
        user_id=user_id,
        market_id=market_id,
        roles=roles,
        is_platform_admin=is_platform_admin,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_minutes=settings.access_token_ttl_minutes,
    )


def issue_refresh(
    *,
    user_id: UUID,
    family_id: UUID | None,
    settings: Settings,
) -> IssuedRefresh:
    """30 kunlik refresh token (D-03 sliding).

    `family_id=None` — YANGI oila (login yoki bozor tanlash). Rotatsiyada
    esa mavjud oila uzatiladi: reuse aniqlanganda BUTUN oila bir marta
    bekor qilinadi.

    `expires_at` HAR SAFAR qaytadan hisoblanadi — bu D-03 dagi "sliding"
    ning o'zi: faol foydalanuvchidan qayta login so'ralmaydi.
    """
    family = family_id if family_id is not None else uuid4()
    jti = uuid4().hex
    token = encode_refresh(
        user_id=user_id,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_days=settings.refresh_token_ttl_days,
        family_id=family,
        jti=jti,
    )
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    return IssuedRefresh(token=token, jti=jti, family_id=family, expires_at=expires_at)


def decode(token: str, *, expected_type: str, settings: Settings) -> TokenClaims:
    """Tokenni tekshiradi. Xato holatida `jwt.InvalidTokenError` oilasini ko'taradi."""
    return decode_token(
        token,
        expected_type=expected_type,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


def refresh_cookie_max_age(settings: Settings) -> int:
    """Cookie `Max-Age` (soniya). 30 kun -> 2592000."""
    return settings.refresh_token_ttl_days * SECONDS_PER_DAY


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    """Refresh cookie'ni yuqoridagi jadvaldagi atributlar bilan qo'yadi."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=refresh_cookie_max_age(settings),
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def clear_refresh_cookie(response: Response) -> None:
    """Cookie'ni o'chiradi.

    `path` AYNAN qo'yilgandagi bilan bir xil bo'lishi SHART — brauzer
    cookie'ni `(nom, domen, yo'l)` uchligi bo'yicha topadi va yo'l mos
    kelmasa eski cookie joyida qolib ketadi.
    """
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=COOKIE_PATH)


def cleared_cookie_headers() -> dict[str, str]:
    """Cookie'ni o'chiruvchi sarlavha — `HTTPException(headers=...)` uchun.

    NEGA ALOHIDA FUNKSIYA: `HTTPException` ko'tarilganda FastAPI YANGI javob
    quradi va endpointga uzatilgan `Response` obyektining sarlavhalari
    UNGA KO'CHMAYDI. Ya'ni `clear_refresh_cookie(response)` dan keyin
    `raise HTTPException(...)` yozish — jimgina ishlamaydigan kod: server
    tomonda token bekor qilinadi, brauzerda esa o'lik cookie qolib ketadi
    va foydalanuvchi har navbatdagi so'rovda 401 oladi.

    Shuning uchun sarlavha shu yerda `Response` ustida hosil qilinib,
    istisno bilan BIRGA uzatiladi — atributlar (`Path`, `HttpOnly`)
    `clear_refresh_cookie()` bilan bir xil manbadan keladi.
    """
    probe = Response()
    clear_refresh_cookie(probe)
    return {"set-cookie": probe.headers["set-cookie"]}
