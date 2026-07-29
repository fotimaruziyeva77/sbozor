"""FastAPI dependency'lari — principal, bloklash keshi va tenant sessiyasi.

=============================================================================
UCHTA DEPENDENCY, UCHTA ALOHIDA MAS'ULIYAT:

1. `get_current_principal` — KIM? Access tokenni tekshiradi va foydalanuvchi
   HALI BLOKLANMAGANINI Valkey keshi orqali aniqlaydi (D-08).
2. `require_permission(...)` — NIMA QILISHI MUMKIN? Kodda qat'iy matritsa
   (D-07). Bu FUNKSIYA darajasidagi nazorat.
3. `get_tenant_session` — QAYSI BOZORDA? Tranzaksiya ochadi va tenant
   GUC'larini o'rnatadi. Bu MA'LUMOT darajasidagi nazorat (RLS).

2 va 3 bir-birining o'rnini BOSMAYDI: `require_permission` "kassir to'lov
kirita oladi" deydi, RLS esa "faqat O'Z bozorida" deydi. Birinchisisiz
har kim hamma narsani qila olardi; ikkinchisisiz kassir boshqa bozorning
to'lovini kirita olardi.
=============================================================================

TENANT KONTEKSTI HAR TRANZAKSIYADA O'RNATILADI, ULANISHDA EMAS.
`set_config(..., is_local=true)` qiymati COMMIT bilan tark etiladi, ya'ni
puldagi ulanish keyingi so'rovga BO'SH kontekst bilan boradi va policy
`NULLIF` tufayli fail-closed (0 qator) bo'ladi. Kontekstni ulanish
darajasida o'rnatish esa aynan teskarisini qilardi: A bozorining konteksti
B bozorining so'roviga sizib o'tardi (T-01-17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import jwt
import structlog
from asgi_correlation_id import correlation_id
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.exceptions import RedisError
from sbozor_core.enums import ActorKind, Role
from sbozor_core.logging import bind_request_context
from sbozor_core.tenancy import set_tenant_context

from app.repositories import auth_repo
from app.security.rbac import Permission, permissions_for
from app.security.tokens import decode

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine, Sequence

    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

__all__ = [
    "CacheDep",
    "Principal",
    "PrincipalDep",
    "SettingsDep",
    "USER_STATE_TTL_SECONDS",
    "get_auth_session",
    "get_cache",
    "get_current_principal",
    "get_settings_dep",
    "get_tenant_session",
    "invalidate_user_state",
    "require_permission",
    "require_roles",
    "user_state_key",
]

log = structlog.get_logger(__name__)

USER_STATE_TTL_SECONDS = 30
"""Bloklash keshining amal qilish muddati (D-08).

Eng yomon holat — 30 soniya kechikish. Amalda kechikish YO'Q: bloklovchi
endpoint (01-07) yozuvdan keyin `invalidate_user_state()` chaqiradi va
keyingi so'rov DB'dan o'qiydi. TTL — o'sha invalidatsiya biror sababga
ko'ra bajarilmay qolgan holat uchun yuqori chegara.
"""

_STATE_ACTIVE = "1"
_STATE_BLOCKED = "0"

_bearer = HTTPBearer(auto_error=False, description="Access token (15 daqiqa)")


def user_state_key(user_id: UUID) -> str:
    """Valkey kaliti: `user:state:{user_id}`."""
    return f"user:state:{user_id}"


async def invalidate_user_state(cache: Redis, user_id: UUID) -> None:
    """Bloklash keshini darhol bekor qiladi (yozuvdan KEYIN chaqiriladi).

    Valkey javob bermasa xato YUTILADI: kesh invalidatsiyasi tezlashtirish
    vositasi, haqiqat manbai esa DB. Eng yomoni — bloklash 30 soniyagacha
    kechikadi; eng yomoni bloklash amalga oshmasligi EMAS.
    """
    try:
        await cache.delete(user_state_key(user_id))
    except RedisError as exc:
        log.warning("user_state_cache_invalidate_failed", user_id=str(user_id), error=str(exc))


@dataclass(frozen=True)
class Principal:
    """Tekshirilgan so'rov egasi.

    `frozen=True`: endpoint kodi huquqlarni "to'g'irlab" qo'ya olmaydi.
    `roles` — `frozenset` (D-05: bir odamda bir necha rol bo'lishi mumkin).
    """

    user_id: UUID
    market_id: UUID | None
    roles: frozenset[str]
    is_platform_admin: bool
    request_id: str
    actor_label: str

    @property
    def permissions(self) -> frozenset[Permission]:
        """Rollar birlashmasidan hisoblangan huquqlar."""
        return permissions_for(self.roles)


def actor_label_for(roles: Sequence[str] | frozenset[str], *, is_platform_admin: bool) -> str:
    """Auditda ko'rinadigan "kim sifatida" tavsifi.

    Platforma admini uchun D-06 aniq matn talab qiladi. To'liq shakl
    ("platforma admini {telefon} — {bozor} bozorida") faqat nomlar ma'lum
    bo'lgan joyda (`/login`, `/select-market`) yoziladi; qolgan yozuvlarda
    bozor `audit_log.market_id` ustunida allaqachon bor, shuning uchun bu
    yerda ROL tavsifi yetarli.
    """
    if is_platform_admin:
        return "platforma admini"
    return ",".join(sorted(roles)) if roles else "rolsiz"


def _sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.sessionmaker  # type: ignore[no-any-return]


def get_settings_dep(request: Request) -> Settings:
    """Sozlamalarni `app.state` dan oladi.

    `get_settings()` ni TO'G'RIDAN-TO'G'RI chaqirmaydi: u `lru_cache` bilan
    muhitdan o'qiydi va testda uni almashtirib bo'lmasdi. `lifespan`
    (prod) yoki test fixture'i (integratsiya) `app.state.settings` ni
    to'ldiradi — ikkala yo'l ham bir xil kodni ishga tushiradi.
    """
    return request.app.state.settings  # type: ignore[no-any-return]


def get_cache(request: Request) -> Redis:
    """Valkey klienti (`app.state.cache`)."""
    return request.app.state.cache  # type: ignore[no-any-return]


SettingsDep = Annotated["Settings", Depends(get_settings_dep)]
CacheDep = Annotated["Redis", Depends(get_cache)]


async def get_auth_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Tenant kontekstisiz sessiya — FAQAT `/api/v1/auth/*` uchun.

    Login paytida bozor HALI NOMA'LUM, shuning uchun bu yerda
    `set_tenant_context()` chaqirilmaydi: barcha so'rovlar `SECURITY
    DEFINER` funksiyalari orqali ketadi (`app/repositories/auth_repo.py`).

    Tranzaksiya ATAYIN ochilmaydi: rad etish yo'llari audit qatorini
    yozib, uni COMMIT qilib, KEYIN `HTTPException` ko'taradi. Umumiy
    `async with session.begin():` bloki bo'lganda `HTTPException` rollback
    keltirib chiqarardi va aynan muvaffaqiyatsiz urinishlar izsiz qolardi.
    """
    async with _sessionmaker(request)() as session:
        yield session


async def _is_user_active(
    request: Request,
    cache: Redis,
    user_id: UUID,
) -> bool:
    """Foydalanuvchi holati: avval Valkey keshi, promahda DB (D-08).

    FAIL-OPEN EMAS: Valkey o'chgan bo'lsa ham javob DB'dan olinadi.
    Keshning yagona vazifasi — har so'rovda `users` ga bormaslik.
    """
    key = user_state_key(user_id)
    try:
        cached = await cache.get(key)
    except RedisError as exc:
        log.warning("user_state_cache_read_failed", user_id=str(user_id), error=str(exc))
        cached = None

    if cached is not None:
        return _decode_state(cached)

    async with _sessionmaker(request)() as session:
        state = await auth_repo.user_state(session, user_id)

    # Foydalanuvchi umuman topilmasa (o'chirilgan) — bloklangan deb qaraladi.
    is_active = bool(state and state.is_active)

    try:
        await cache.set(
            key,
            _STATE_ACTIVE if is_active else _STATE_BLOCKED,
            ex=USER_STATE_TTL_SECONDS,
        )
    except RedisError as exc:
        log.warning("user_state_cache_write_failed", user_id=str(user_id), error=str(exc))

    return is_active


def _decode_state(cached: Any) -> bool:
    """Valkey qiymatini `bool` ga o'giradi (klient `bytes` yoki `str` qaytaradi)."""
    raw = cached.decode() if isinstance(cached, bytes | bytearray) else str(cached)
    return raw == _STATE_ACTIVE


async def get_current_principal(
    request: Request,
    settings: SettingsDep,
    cache: CacheDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> Principal:
    """`Authorization: Bearer` -> tekshirilgan `Principal`.

    Ketma-ketlik ahamiyatli: avval imzo/muddat (arzon, stateless), keyin
    bloklash holati (Valkey yoki DB). Teskarisi bo'lganda har bir yaroqsiz
    token ham keshga/bazaga bir so'rov qo'shardi.
    """
    request_id = correlation_id.get() or ""

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode(credentials.credentials, expected_type="access", settings=settings)
    except jwt.InvalidTokenError as exc:
        # Sabab JAVOBGA chiqarilmaydi (muddati tugagan / imzo yaroqsiz /
        # `aud` mos emas — hammasi bir xil), lekin LOG'ga yoziladi.
        log.info("access_token_rejected", error=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not await _is_user_active(request, cache, claims.user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="account_blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    bind_request_context(request_id, user_id=claims.user_id, market_id=claims.market_id)

    roles = frozenset(claims.roles)
    return Principal(
        user_id=claims.user_id,
        market_id=claims.market_id,
        roles=roles,
        is_platform_admin=claims.is_platform_admin,
        request_id=request_id,
        actor_label=actor_label_for(roles, is_platform_admin=claims.is_platform_admin),
    )


PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


async def get_tenant_session(
    request: Request,
    principal: PrincipalDep,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya (RESEARCH Code Example §1).

    `market_id` tanlanmagan bo'lsa 409: kontekstsiz so'rov RLS tufayli
    jimgina 0 qator qaytarardi va chaqiruvchi buni "ma'lumot yo'q" deb
    talqin qilardi — bu eng yomon xato turi.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )

    # SIM117 (ikki `async with` ni birlashtirish) ATAYIN rad etilgan: ichki
    # blok TRANZAKSIYA chegarasi va u shu yerdagi butun xavfsizlik da'vosini
    # ushlab turadi. Birlashtirilgan shaklda "kontekst tranzaksiya ichida
    # o'rnatiladi" degan fakt ko'zdan yo'qoladi va keyingi tahrirlovchi
    # `session.begin()` ni "keraksiz" deb olib tashlashi mumkin — o'shanda
    # kontekst umuman o'rnatilmay qoladi.
    async with _sessionmaker(request)() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=principal.market_id,
                actor_id=principal.user_id,
                request_id=principal.request_id,
                actor_kind=ActorKind.USER,
            )
            yield session
        # COMMIT -> GUC'lar `''` bo'ladi -> keyingi so'rov fail-closed.


TenantSessionDep = Annotated["AsyncSession", Depends(get_tenant_session)]


def require_permission(perm: Permission) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Huquq talab qiluvchi dependency fabrikasi (D-07).

    403 qaytaradi — LEKIN faqat huquq yetishmaganda. Cross-tenant resursda
    javob 404 bo'lishi SHART (T-01-47): u yerda RLS 0 qator beradi va
    endpoint "topilmadi" deydi. 403 bo'lganda javobning o'zi "bunday
    obyekt bor, lekin sizniki emas" degan ma'lumotni oshkor qilardi.
    """

    async def _require(principal: PrincipalDep) -> Principal:
        if perm not in principal.permissions:
            log.info(
                "permission_denied",
                required=str(perm),
                roles=sorted(principal.roles),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    return _require


def require_roles(*roles: Role) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Rol talab qiluvchi sodda variant.

    `require_permission()` AFZAL: rol nomiga bog'lanish matritsani chetlab
    o'tadi va D-07 o'zgarganda bu joy jimgina eskirib qoladi. Bu variant
    faqat huquq tushunchasiga to'g'ri kelmaydigan holatlar uchun
    (masalan "faqat platforma admini" oqimlari).
    """
    allowed = {str(role) for role in roles}

    async def _require(principal: PrincipalDep) -> Principal:
        if not allowed & principal.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    return _require
