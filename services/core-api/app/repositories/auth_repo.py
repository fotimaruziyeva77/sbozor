"""Login va sessiya DB kontrakti — FAQAT `SECURITY DEFINER` funksiyalari orqali.

=============================================================================
NEGA BU YERDA `users` MODELI USTIDA BIRORTA ORM SO'ROVI YO'Q:

`sbozor_app` roliga `users` jadvali ustidagi BARCHA huquq `REVOKE` qilingan
(01-04, `REVOKE ALL ON TABLE users FROM sbozor_app`). Bu ataylab: global
identifikatsiya jadvaliga "tasodifan" ORM orqali borish IMKONSIZ bo'lishi
kerak. Global o'qish yuzasi aynan quyidagi funksiyalar bilan cheklangan va
har biri `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app` ostida.

`refresh_tokens` bilan ham xuddi shunday, LEKIN BOSHQA SABABGA KO'RA:
u tenant-scoped (RLS ENABLE + FORCE), refresh cookie kelganda esa bozor
HALI NOMA'LUM — `mid` claim'i refresh tokenga ATAYIN yozilmaydi (01-03:
huquqlar har `/refresh` da DB'dan qayta o'qiladi). Ya'ni `jti` bo'yicha
global qidiruv tenant kontekstisiz bajarilishi kerak, RLS esa uni 0 qatorga
tushiradi. Bu Pitfall 3 ning AYNAN o'sha mexanizmi, faqat `users` emas,
`refresh_tokens` ustida — shuning uchun yechim ham bir xil: tor
`SECURITY DEFINER` funksiyalar (`migrations/versions/0003_auth_support.py`).
=============================================================================

SQL SATRLARI: barcha so'rovlar NOMLANGAN BIND parametrlari bilan
(`:phone`, `:user_id`). Jadval/funksiya nomi f-string bilan qurilmaydi —
ruff `S608` qoidasi yoqilgan va u aynan shu sinf xatoni ushlaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "LoginRow",
    "MarketRow",
    "Membership",
    "RefreshRow",
    "UserState",
    "find_login",
    "find_login_by_id",
    "list_markets",
    "memberships",
    "refresh_find",
    "refresh_issue",
    "refresh_revoke_family",
    "refresh_revoke_user",
    "refresh_rotate",
    "set_active",
    "update_password_hash",
    "user_state",
]


@dataclass(frozen=True)
class LoginRow:
    """`auth_find_login` / `auth_find_login_by_id` natijasi."""

    user_id: UUID
    phone_e164: str | None
    password_hash: str
    is_active: bool
    must_change_password: bool
    locale: str
    is_platform_admin: bool
    full_name: str | None


@dataclass(frozen=True)
class Membership:
    """Foydalanuvchining bitta bozordagi a'zoligi (D-05: rollar TO'PLAMI)."""

    market_id: UUID
    market_name: str
    roles: tuple[str, ...]
    is_active: bool
    """BOZOR faolligi (`markets.is_active`), foydalanuvchi faolligi EMAS.

    Nom `LoginRow.is_active` / `UserState.is_active` bilan bir xil, ma'nosi
    esa boshqacha — chalkashish narxi yuqori, shuning uchun bu farq shu
    yerda yozib qo'yiladi. `false` — usta tugallanmagan QORALAMA bozor
    (D-16: `is_active` faollashtirish bayrog'i, "kamera bor/yo'q" emas).

    Maydon `MarketRow.is_active` bilan bir xil shaklda: ikkalasi ham
    `MarketRef.is_active` javob maydonining manbai bo'ladi va hech bir
    chaqiruvchi `True` literalini yozmasligi kerak.
    """


@dataclass(frozen=True)
class MarketRow:
    """Bozorlar ro'yxati elementi — FAQAT platforma admini oqimida (D-06)."""

    market_id: UUID
    market_name: str
    is_active: bool


@dataclass(frozen=True)
class UserState:
    """Darhol bloklash keshining DB manbai (D-08)."""

    is_active: bool
    must_change_password: bool
    locale: str


@dataclass(frozen=True)
class RefreshRow:
    """`refresh_tokens` qatori — rotatsiya va reuse-detect uchun."""

    market_id: UUID
    user_id: UUID
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_jti: str | None


_FIND_LOGIN = text(
    "SELECT user_id, password_hash, is_active, must_change_password, "
    "locale, is_platform_admin, full_name FROM auth_find_login(:phone)"
)

_FIND_LOGIN_BY_ID = text(
    "SELECT user_id, phone_e164, password_hash, is_active, must_change_password, "
    "locale, is_platform_admin, full_name FROM auth_find_login_by_id(:user_id)"
)

_MEMBERSHIPS = text(
    "SELECT market_id, market_name, roles, is_active FROM auth_memberships(:user_id)"
)

_LIST_MARKETS = text("SELECT market_id, market_name, is_active FROM auth_list_markets()")

_USER_STATE = text("SELECT is_active, must_change_password, locale FROM auth_user_state(:user_id)")

_UPDATE_PASSWORD_HASH = text(
    "SELECT auth_update_password_hash(:user_id, :password_hash, :must_change)"
)

_SET_ACTIVE = text("SELECT auth_set_active(:user_id, :is_active)")

_REFRESH_ISSUE = text(
    "SELECT auth_refresh_issue(:market_id, :user_id, :jti, :family_id, :expires_at)"
)

_REFRESH_FIND = text(
    "SELECT market_id, user_id, family_id, expires_at, revoked_at, replaced_by_jti "
    "FROM auth_refresh_find(:jti)"
)

_REFRESH_ROTATE = text("SELECT auth_refresh_rotate(:old_jti, :new_jti)")

_REFRESH_REVOKE_FAMILY = text("SELECT auth_refresh_revoke_family(:family_id)")

_REFRESH_REVOKE_USER = text("SELECT auth_refresh_revoke_user(:user_id)")


def _login_row(row: Any, *, phone: str | None) -> LoginRow:
    """`auth_find_login` qatorini dataclass'ga o'giradi."""
    return LoginRow(
        user_id=row.user_id,
        phone_e164=phone,
        password_hash=row.password_hash,
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        locale=row.locale,
        is_platform_admin=row.is_platform_admin,
        full_name=row.full_name,
    )


async def find_login(session: AsyncSession, phone: str) -> LoginRow | None:
    """Telefon bo'yicha login qatori. Topilmasa `None` — XATO EMAS.

    Chaqiruvchi `None` holatida ham `dummy_verify()` bilan bir xil vaqt
    sarflashi SHART (T-01-15), aks holda javob vaqti "bu telefon
    ro'yxatdan o'tganmi" savoliga javob berib qo'yadi.
    """
    result = await session.execute(_FIND_LOGIN, {"phone": phone})
    row = result.one_or_none()
    return None if row is None else _login_row(row, phone=phone)


async def find_login_by_id(session: AsyncSession, user_id: UUID) -> LoginRow | None:
    """`user_id` bo'yicha login qatori — parol almashtirish oqimi uchun.

    Access tokenda telefon YO'Q (u PII va tokenga kerak emas), parolni
    almashtirishda esa joriy hash kerak — shuning uchun alohida funksiya.
    """
    result = await session.execute(_FIND_LOGIN_BY_ID, {"user_id": str(user_id)})
    row = result.one_or_none()
    if row is None:
        return None
    return LoginRow(
        user_id=row.user_id,
        phone_e164=row.phone_e164,
        password_hash=row.password_hash,
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        locale=row.locale,
        is_platform_admin=row.is_platform_admin,
        full_name=row.full_name,
    )


async def memberships(session: AsyncSession, user_id: UUID) -> list[Membership]:
    """Foydalanuvchining barcha a'zoliklari (bozor nomi bilan, nom bo'yicha tartiblangan).

    Ro'yxat FILTRLANMAYDI: qoralama bozor (`is_active = false`) ham
    qaytariladi va bayroq chaqiruvchiga uzatiladi. Filtrlash mas'uliyati
    ATAYIN iste'molchida — bozor tanlash ekrani qoralamani ko'rsatishi
    KERAK, mahsulot oqimlari esa (6-faza billing job) `is_active` bo'yicha
    ANIQ filtrlaydi va "ro'yxat allaqachon toza" degan taxminga tayanmaydi
    (RESEARCH Pitfall 7).
    """
    result = await session.execute(_MEMBERSHIPS, {"user_id": str(user_id)})
    return [
        Membership(
            market_id=row.market_id,
            market_name=row.market_name,
            roles=tuple(row.roles or ()),
            is_active=row.is_active,
        )
        for row in result
    ]


async def list_markets(session: AsyncSession) -> list[MarketRow]:
    """Barcha bozorlar — FAQAT `is_platform_admin` oqimida chaqiriladi (D-06).

    Huquq tekshiruvi ATAYIN ilova qatlamida: funksiya faqat bozor NOMLARINI
    ochadi, hech qanday tenant ma'lumotini emas.
    """
    result = await session.execute(_LIST_MARKETS)
    return [
        MarketRow(market_id=row.market_id, market_name=row.market_name, is_active=row.is_active)
        for row in result
    ]


async def user_state(session: AsyncSession, user_id: UUID) -> UserState | None:
    """Bloklash holati — Valkey keshi promahi bo'lganda DB manbai (D-08)."""
    result = await session.execute(_USER_STATE, {"user_id": str(user_id)})
    row = result.one_or_none()
    if row is None:
        return None
    return UserState(
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        locale=row.locale,
    )


async def update_password_hash(
    session: AsyncSession,
    user_id: UUID,
    password_hash: str,
    *,
    must_change: bool | None = None,
) -> None:
    """Parol hash'ini yangilaydi (`must_change=None` -> bayroq tegilmaydi).

    Ikki chaqiruvchisi bor: (1) parol almashtirish (`must_change=False`),
    (2) login paytida `verify_and_update` eskirgan Argon2 parametrlarini
    aniqlaganda JIMGINA qayta hashlash (T-01-18) — o'shanda bayroq
    o'zgarmasligi kerak.
    """
    await session.execute(
        _UPDATE_PASSWORD_HASH,
        {"user_id": str(user_id), "password_hash": password_hash, "must_change": must_change},
    )


async def set_active(session: AsyncSession, user_id: UUID, *, is_active: bool) -> None:
    """Foydalanuvchini bloklaydi/tiklaydi (D-08 — UI 01-07 rejasida)."""
    await session.execute(_SET_ACTIVE, {"user_id": str(user_id), "is_active": is_active})


async def refresh_issue(
    session: AsyncSession,
    *,
    market_id: UUID,
    user_id: UUID,
    jti: str,
    family_id: UUID,
    expires_at: datetime,
) -> None:
    """Yangi refresh token qatorini yozadi.

    `market_id` MAJBURIY: `refresh_tokens.market_id` `NOT NULL`. Bozor
    tanlanmagan sessiya (platforma admini login qilgan payt) uchun refresh
    token UMUMAN chiqarilmaydi — u `/select-market` da beriladi.
    """
    await session.execute(
        _REFRESH_ISSUE,
        {
            "market_id": str(market_id),
            "user_id": str(user_id),
            "jti": jti,
            "family_id": str(family_id),
            "expires_at": expires_at,
        },
    )


async def refresh_find(session: AsyncSession, jti: str) -> RefreshRow | None:
    """`jti` bo'yicha refresh qatorini topadi (tenant kontekstisiz)."""
    result = await session.execute(_REFRESH_FIND, {"jti": jti})
    row = result.one_or_none()
    if row is None:
        return None
    return RefreshRow(
        market_id=row.market_id,
        user_id=row.user_id,
        family_id=row.family_id,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_jti=row.replaced_by_jti,
    )


async def refresh_rotate(session: AsyncSession, *, old_jti: str, new_jti: str) -> int:
    """Eski qatorni bekor qilib yangisiga bog'laydi; TEGILGAN QATORLAR SONINI qaytaradi.

    Qaytgan qiymat 0 bo'lsa — qator allaqachon bekor qilingan, ya'ni ayni
    tokendan ikkinchi marta foydalanilmoqda. Tekshiruv `UPDATE ... WHERE
    revoked_at IS NULL` ichida bajariladi, ya'ni ikki parallel `/refresh`
    so'rovidan faqat BITTASI g'olib chiqadi (oldindan `SELECT` qilib keyin
    `UPDATE` qilish poyga oynasi qoldirardi).
    """
    result = await session.execute(_REFRESH_ROTATE, {"old_jti": old_jti, "new_jti": new_jti})
    return int(result.scalar_one())


async def refresh_revoke_family(session: AsyncSession, family_id: UUID) -> int:
    """BUTUN oilani bekor qiladi (reuse aniqlanganda va logout'da)."""
    result = await session.execute(_REFRESH_REVOKE_FAMILY, {"family_id": str(family_id)})
    return int(result.scalar_one())


async def refresh_revoke_user(session: AsyncSession, user_id: UUID) -> int:
    """Foydalanuvchining BARCHA sessiyalarini bekor qiladi (parol almashtirilganda)."""
    result = await session.execute(_REFRESH_REVOKE_USER, {"user_id": str(user_id)})
    return int(result.scalar_one())
