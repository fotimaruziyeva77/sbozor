"""Xavfsizlik primitivlari — Argon2id parol hashlash va JWT.

Ikki qism, bitta modul: ikkalasi ham auth chegarasida birga ishlatiladi va
ikkalasining ham eskirgan (tutorial'larda hamon uchraydigan) muqobillari bor.

Nima ATAYIN ISHLATILMAYDI:
* parol uchun eskirgan `crypt` asosidagi kutubxona — u Python 3.13'da olib
  tashlangan stdlib modulini import qiladi, ya'ni bu runtime'da ishga
  tushmaydi;
* JWT uchun `jose` oilasidagi qarovsiz portlar — ularda yopilmagan CVE'lar
  tarixi bor. Yagona to'g'ri tanlov — PyJWT.

Tahdid qamrovi: T-01-12 (`alg` almashtirish), T-01-13 (tur almashtirish),
T-01-14 (qisqa kalit), T-01-15 (enumeration), T-01-18 (parametr eskirishi).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ALG",
    "MIN_SECRET_BYTES",
    "REQUIRED_CLAIMS",
    "TokenClaims",
    "decode_token",
    "dummy_verify",
    "encode_access",
    "encode_refresh",
    "hash_password",
    "verify_password",
]

# ---------------------------------------------------------------------------
# Parol
# ---------------------------------------------------------------------------

# Modul darajasidagi BITTA instans: `PasswordHash.recommended()` Argon2id ni
# OWASP tavsiya qilgan parametrlar bilan quradi. Har chaqiruvda qayta qurish
# keraksiz ish va parametrlar drift qilishiga yo'l ochadi.
_hasher = PasswordHash.recommended()

# `dummy_verify()` uchun oldindan hisoblangan hash. Import paytida bir marta
# hisoblanadi (~100 ms), so'rov ichida EMAS — aks holda birinchi noma'lum
# telefon bilan kelgan so'rov keyingilaridan sezilarli sekin bo'lardi va
# aynan o'sha farq enumeration signaliga aylanardi.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))
_DUMMY_PASSWORD = secrets.token_urlsafe(32)


def hash_password(raw: str) -> str:
    """Parolni Argon2id bilan hashlaydi (tuz avtomatik va tasodifiy)."""
    return _hasher.hash(raw)


def verify_password(raw: str, stored: str) -> tuple[bool, str | None]:
    """Parolni tekshiradi.

    Returns:
        `(to'g'ri_mi, yangi_hash_yoki_None)`. Ikkinchi element `None` bo'lmasa —
        saqlangan hash eskirgan parametrlar bilan yaratilgan va chaqiruvchi uni
        DB'da YANGILASHI kerak (T-01-18). Bu parametrlarni yillar davomida
        oshirib borish imkonini beradi: foydalanuvchi keyingi login'ida
        jimgina yangi hash'ga ko'chadi.
    """
    ok, updated = _hasher.verify_and_update(raw, stored)
    return bool(ok), updated


def dummy_verify() -> None:
    """Soxta tekshiruv — javob vaqtini tekislaydi (T-01-15).

    Telefon raqami bazada topilmaganda ham login endpointi shu funksiyani
    chaqiradi. Aks holda "foydalanuvchi topilmadi" javobi Argon2 ishisiz
    o'nlab marta tezroq qaytadi va hujumchi shu farq bilan raqamlarni sanab
    chiqadi.
    """
    _hasher.verify(_DUMMY_PASSWORD, _DUMMY_HASH)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

ALG = "HS256"
"""Token CHIQARISHDA ishlatiladigan imzo algoritmi.

Dekodlashda ruxsat etilgan algoritmlar `algorithms=["HS256"]` shaklida
LITERAL yoziladi — konstanta orqali emas. Bu ataylab: xavfsizlik uchun
kritik bo'lgan bu satrni o'qiyotgan odam nimaga ruxsat berilayotganini
boshqa joyga qaramasdan ko'rishi kerak. Algoritm token header'idan HECH
QACHON olinmaydi (T-01-12) — aks holda hujumchi `alg=none` yoki algoritm
almashtirish bilan imzoni butunlay chetlab o'tadi.

Ikkala joy mos ekanini `test_algorithm_constant_is_hs256` va HS512/`alg=none`
testlari qulflaydi.
"""

MIN_SECRET_BYTES = 32
"""RFC 7518 §3.2: HS256 kaliti hash chiqishidan (256 bit) qisqa bo'lmasligi kerak."""

REQUIRED_CLAIMS = ["exp", "iat", "sub", "iss", "aud", "jti"]
"""Bo'lmasa token rad etiladigan claim'lar.

`typ` bu ro'yxatda ATAYIN yo'q: u alohida, aniqroq xato xabari bilan
tekshiriladi (`decode_token` oxiri).
"""

_ACCESS = "access"
_REFRESH = "refresh"  # noqa: S105 — claim qiymati, sir emas


@dataclass(frozen=True)
class TokenClaims:
    """Tekshirilgan tokendan olingan principal ma'lumoti.

    `frozen=True`: dekodlangandan keyin hech kim huquqlarni "to'g'irlab"
    qo'ya olmaydi — o'zgartirish uchun yangi token kerak.

    Refresh tokenda `market_id`, `roles` va `is_platform_admin` ATAYIN
    bo'lmaydi (huquqlar har `/refresh` da DB'dan qayta o'qiladi), shuning
    uchun ular u yerda `None` / bo'sh / `False` bo'lib qaytadi.
    """

    user_id: UUID
    market_id: UUID | None
    roles: list[str]
    is_platform_admin: bool
    jti: str
    token_type: str
    family_id: str | None = field(default=None)
    """Refresh token oilasi (`fam`). Reuse aniqlanganda BUTUN oila bekor
    qilinadi — o'g'irlangan token 30 kun emas, keyingi ishlatishda o'ladi."""


def _assert_secret_length(secret: str) -> None:
    """Qisqa HMAC sirini xato bilan rad etadi (T-01-14).

    PyJWT o'zi bu holatda faqat OGOHLANTIRISH beradi (`encode` yo'lida
    `options` ni chaqiruvchi uzata olmaydi), ogohlantirish esa prod loglarida
    ko'milib ketadi. Shuning uchun tekshiruv shu yerda aniq bajariladi.
    """
    if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
        raise jwt.exceptions.InvalidKeyError(
            f"JWT siri kamida {MIN_SECRET_BYTES} bayt bo'lishi kerak (RFC 7518). "
            'Hosil qilish: python -c "import secrets;print(secrets.token_urlsafe(48))"'
        )


def encode_access(
    *,
    user_id: UUID,
    market_id: UUID | None,
    roles: Sequence[str],
    is_platform_admin: bool,
    secret: str,
    issuer: str,
    audience: str,
    ttl_minutes: int,
) -> str:
    """Qisqa umrli access token chiqaradi (D-03: 15 daqiqa).

    `mid` — tanlangan bozor (D-06); platforma admini bozor tanlamaguncha
    `None` bo'ladi. `roles` — rollar TO'PLAMI (D-05), bitta rol emas.
    """
    _assert_secret_length(secret)
    now = datetime.now(UTC)
    return jwt.encode(
        {
            # PyJWT 2.10+ `sub` ni validatsiya qiladi — UUID obyekti EMAS, `str`.
            "sub": str(user_id),
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=ttl_minutes),
            "jti": uuid4().hex,
            "typ": _ACCESS,
            "mid": str(market_id) if market_id is not None else None,
            "roles": list(roles),
            "pa": is_platform_admin,
        },
        secret,
        algorithm=ALG,
    )


def encode_refresh(
    *,
    user_id: UUID,
    secret: str,
    issuer: str,
    audience: str,
    ttl_days: int,
    family_id: UUID,
    jti: str | None = None,
) -> str:
    """Uzoq umrli refresh token chiqaradi (D-03: 30 kun sliding).

    Huquqqa oid claim'lar (`mid`, `roles`, `pa`) ATAYIN yozilmaydi: agar ular
    tokenda bo'lsa, bloklangan yoki roli olib tashlangan foydalanuvchi 30 kun
    davomida eski huquqlari bilan yangi access token olib turardi.

    `jti` chaqiruvchi tomonidan berilishi mumkin — 01-06 rotatsiyasi avval
    DB'ga yozadi, keyin o'sha identifikator bilan token beradi.
    `family_id` — reuse aniqlanganda bekor qilinadigan oila (Pattern 3).
    """
    _assert_secret_length(secret)
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(days=ttl_days),
            "jti": jti if jti is not None else uuid4().hex,
            "typ": _REFRESH,
            "fam": str(family_id),
        },
        secret,
        algorithm=ALG,
    )


def decode_token(
    token: str,
    *,
    expected_type: str,
    secret: str,
    issuer: str,
    audience: str,
) -> TokenClaims:
    """Tokenni tekshiradi va `TokenClaims` qaytaradi.

    Raises:
        jwt.exceptions.InvalidKeyError: sir 32 baytdan qisqa.
        jwt.ExpiredSignatureError: muddat tugagan.
        jwt.InvalidTokenError: imzo, algoritm, `iss`/`aud`, majburiy claim
            yoki token TURI mos kelmasa (`InvalidAlgorithmError`,
            `InvalidAudienceError` va boshqalar shu sinfning bolalari).
    """
    claims = jwt.decode(
        token,
        secret,
        # ANIQ ro'yxat — token header'idagi `alg` E'TIBORGA OLINMAYDI.
        algorithms=["HS256"],
        audience=audience,
        issuer=issuer,
        options={
            "require": REQUIRED_CLAIMS,
            "verify_exp": True,
            "verify_aud": True,
            "verify_iss": True,
            # Ogohlantirish emas, `InvalidKeyError` (T-01-14).
            "enforce_minimum_key_length": True,
        },
    )

    # T-01-13: access tokenni refresh sifatida (yoki aksincha) ishlatib
    # bo'lmaydi. Bu tekshiruv `require` dan keyin turadi, shunda xato xabari
    # aynan sababni ko'rsatadi.
    actual_type = claims.get("typ")
    if actual_type != expected_type:
        raise jwt.InvalidTokenError(
            f"wrong token type: kutilgan {expected_type!r}, kelgani {actual_type!r}"
        )

    raw_market_id = claims.get("mid")
    raw_family_id = claims.get("fam")

    return TokenClaims(
        user_id=UUID(claims["sub"]),
        market_id=UUID(raw_market_id) if raw_market_id else None,
        roles=list(claims.get("roles") or []),
        is_platform_admin=bool(claims.get("pa", False)),
        jti=str(claims["jti"]),
        token_type=str(actual_type),
        family_id=str(raw_family_id) if raw_family_id else None,
    )
