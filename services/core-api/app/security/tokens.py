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
from sbozor_core.security import (
    LiveClaims,
    TokenClaims,
    decode_live,
    decode_token,
    encode_access,
    encode_live,
    encode_refresh,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.settings import Settings

__all__ = [
    "COOKIE_PATH",
    "LIVE_TOKEN_AUDIENCE",
    "LIVE_TOKEN_MAX_TTL_SECONDS",
    "IssuedRefresh",
    "LiveClaims",
    "REFRESH_COOKIE_NAME",
    "SECONDS_PER_DAY",
    "clear_refresh_cookie",
    "cleared_cookie_headers",
    "decode",
    "decode_live_token",
    "issue_access",
    "issue_live_token",
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


LIVE_TOKEN_AUDIENCE = "live"  # noqa: S105 — `aud` claim QIYMATI, sir emas
"""Jonli ko'rish chiptasining `aud` claim'i (D-08).

=============================================================================
AUDITORIYA AJRATILISHI QAT'IY VA U IKKI TOMONLAMA O'LCHANADI.

  * jonli chipta oddiy API'da HECH QACHON qabul qilinmaydi;
  * access token `/internal/live-authz` da HECH QACHON qabul qilinmaydi.

Sabab arifmetikada: chipta 60 soniyalik, access token esa 15 daqiqalik.
Bitta auditoriya bilan `/live/` ga kirish uchun berilgan chipta butun
API'ga kirish huquqiga aylanardi (u imzolangan va `sub` si bor —
`get_current_principal` uni access token deb qabul qilardi). Teskari
tomoni ham xuddi shunday yomon: 15 daqiqalik token bilan olingan jonli
havola D-08 ning butun «qisqa muddat bekor qilishni keraksiz qiladi»
mulohazasini bekor qilardi.

Qiymat `Settings.jwt_audience` DAN OLINMAYDI (u `sbozor-api`) — u shu
yerda LITERAL turadi va uni o'qiyotgan odam ajratishni boshqa faylga
qaramasdan ko'radi (`security.py::ALG` da o'rnatilgan qoida).

Darvoza: `tests/integration/test_live_view.py::
test_live_token_is_not_an_api_token` va uning teskari jufti.
=============================================================================
"""

LIVE_TOKEN_MAX_TTL_SECONDS = 60
"""D-08 ning yuqori chegarasi — `exp - iat <= 60`.

Chegara SOZLAMA EMAS va bu ataylab: uni `Settings` ga chiqarish
«prod'da biroz uzaytiramiz» yo'lini ochardi, muddatning qisqaligi esa
bekor qilish mexanizmining O'RNINI bosadi (D-08). Ya'ni qiymatni
oshirish — bu «bekor qilish kerak emas» qarorini jimgina bekor qilish.

`issue_live_token` bu chegaradan katta TTL ni `ValueError` bilan rad
etadi, ya'ni buzilish testda emas, CHAQIRUV joyida ko'rinadi.
"""


def issue_live_token(
    *,
    camera_id: UUID,
    market_id: UUID,
    user_id: UUID,
    settings: Settings,
    ttl_seconds: int = LIVE_TOKEN_MAX_TTL_SECONDS,
) -> str:
    """60 soniyalik jonli ko'rish chiptasi (D-08).

    ⚠ TOKEN — ULANISH CHIPTASI, SESSIYA MUDDATI EMAS (UI-SPEC §8.3).
      WebRTC'da signalling bir marta bo'ladi va media UDP orqali
      nginx'dan TASHQARIDA oqadi, ya'ni ulanish o'rnatilgach sessiya
      tokendan uzoqroq yashaydi; HLS'da esa har segment `auth_request`
      dan o'tadi va oqim 60 soniyada uzilardi. Bir xil UI, ikki xil
      xulq — shuning uchun sessiya chegarasini (5 daqiqa) UI o'zi
      qo'yadi va har yangilanishda YANGI chipta so'raydi. O'sha
      yangilanish avtorizatsiyani QAYTA tekshiradi va yangi audit
      qatorini yozadi.

    Raises:
        ValueError: `ttl_seconds` D-08 chegarasidan katta bo'lsa.
    """
    if ttl_seconds <= 0 or ttl_seconds > LIVE_TOKEN_MAX_TTL_SECONDS:
        raise ValueError(
            f"jonli chipta TTL'i 1..{LIVE_TOKEN_MAX_TTL_SECONDS} soniya oralig'ida "
            f"bo'lishi kerak (D-08), berilgani: {ttl_seconds}"
        )
    return encode_live(
        user_id=user_id,
        market_id=market_id,
        camera_id=camera_id,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=LIVE_TOKEN_AUDIENCE,
        ttl_seconds=ttl_seconds,
    )


def decode_live_token(token: str, *, settings: Settings) -> LiveClaims:
    """Jonli chiptani tekshiradi. Xatoda `jwt.InvalidTokenError` oilasi.

    `audience` SHU MODULNING konstantasidan, `settings.jwt_audience` dan
    EMAS — ajratishning butun mazmuni shunda (yuqoridagi izoh).
    """
    return decode_live(
        token,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=LIVE_TOKEN_AUDIENCE,
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
