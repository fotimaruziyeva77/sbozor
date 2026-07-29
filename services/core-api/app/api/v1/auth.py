"""Autentifikatsiya endpointlari (FOUND-01, D-01…D-08).

=============================================================================
`POST /auth/register` BU YERDA YO'Q VA HECH QACHON BO'LMAYDI (D-04).

Foydalanuvchi yaratish ikki bosqichli va HAR DOIM mavjud admin tomonidan
bajariladi: platforma admini bozor va uning admini/direktorini yaratadi,
bozor admini esa o'z bozori xodimlarini. O'z-o'zidan ro'yxatdan o'tish
bozor ma'muriyati nazoratidan tashqarida foydalanuvchi hosil qilardi —
bu mahsulotning butun ishonch modeliga zid. Test buni doimiy tekshiradi
(`test_register_route_does_not_exist`).
=============================================================================

ENUMERATION SIYOSATI (T-01-40) — uch holat, BITTA javob:

| Holat                        | Javob                                     |
| ---------------------------- | ----------------------------------------- |
| telefon topilmadi            | `401 {"detail": "invalid_credentials"}`   |
| parol noto'g'ri              | AYNAN o'shanisi                            |
| foydalanuvchi bloklangan     | AYNAN o'shanisi                            |

Vaqt farqi ham yopiladi: telefon topilmasa `dummy_verify()` chaqirilib
bir xil Argon2 ishi bajariladi, bloklash tekshiruvi esa parol
tekshiruvidan KEYIN turadi (aks holda bloklangan hisob tezroq javob
qaytarardi va farq o'lchansa "bu raqam bor" degan signal bo'lardi).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import jwt
import structlog
from asgi_correlation_id import correlation_id
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sbozor_core.enums import AuditAction
from sbozor_core.security import dummy_verify, hash_password, verify_password
from sqlalchemy import text

from app.deps import (
    AuthSessionDep,
    CacheDep,
    PrincipalDep,
    SettingsDep,
    TenantSessionDep,
    actor_label_for,
    invalidate_user_state,
)
from app.repositories import auth_repo
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MarketRef,
    MeResponse,
    SelectMarketRequest,
    SessionResponse,
    validate_password_strength,
)
from app.security.audit import (
    TABLE_MARKETS,
    TABLE_REFRESH_TOKENS,
    TABLE_USERS,
    platform_admin_label,
    write_app_audit,
)
from app.security.ratelimit import TooManyAttempts, check_login_rate, reset_login_rate
from app.security.tokens import (
    clear_refresh_cookie,
    decode,
    issue_access,
    issue_refresh,
    set_refresh_cookie,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(tags=["auth"])

RefreshCookie = Annotated[
    str | None,
    Cookie(
        # LITERAL: FastAPI alias'i OpenAPI sxemasiga tushadi va o'zgaruvchi
        # bo'la olmaydi. `app.security.tokens.REFRESH_COOKIE_NAME` bilan
        # mosligi `test_refresh_cookie_name_matches_tokens_constant` bilan
        # qulflangan (01-03 dagi `algorithms=["HS256"]` bilan bir xil qoida).
        alias="sbozor_rt",
        description="Refresh token — httpOnly, Path=/api/v1/auth",
    ),
]

SECONDS_PER_MINUTE = 60

_PLATFORM_ADMIN_ROLE = "platform_admin"

_INVALID_CREDENTIALS = "invalid_credentials"
_INVALID_REFRESH = "invalid_refresh"  # noqa: S105 — javob kodi, sir emas


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


def _client_ip(request: Request) -> str | None:
    """So'rov manbai IP'si (audit va rate-limit uchun).

    Reverse-proxy ortida `X-Forwarded-For` ni O'QIMAYDI: uni har kim
    yozishi mumkin va ishonchli qilish uchun proxy zanjiri tasdiqlanishi
    kerak. Nginx `proxy_set_header` bilan haqiqiy IP'ni uzatadi va
    uvicorn `--proxy-headers` bilan uni `request.client` ga qo'yadi —
    ya'ni ishonch qarori DEPLOY qatlamida, kodda emas.
    """
    return request.client.host if request.client else None


def _verify_password_safe(raw: str, stored: str) -> tuple[bool, str | None]:
    """Parolni tekshiradi; o'qib bo'lmaydigan hash 500 EMAS, "noto'g'ri" beradi.

    Saqlangan hash buzilgan yoki boshqa formatdan ko'chirilgan bo'lishi
    mumkin (qo'lda yozilgan seed, migratsiya qoldig'i). Bunday qatorda
    `pwdlib` istisno ko'taradi va u ushlanmasa BITTA buzuq qator butun
    login endpointini 500 bilan yiqitardi — hujumchi uchun esa bu ochiq
    enumeration signali bo'lardi ("bu telefon uchun 500, boshqasi uchun 401").
    """
    try:
        return verify_password(raw, stored)
    except Exception as exc:  # noqa: BLE001 - sabab log'da, javob bir xil
        log.warning("password_hash_unreadable", error=type(exc).__name__)
        return False, None


def _invalid_credentials() -> HTTPException:
    """Uchala rad etish holati uchun AYNAN bir xil javob (T-01-40)."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS,
    )


def _invalid_refresh() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_REFRESH)


def _session_roles(
    membership: auth_repo.Membership | None,
    *,
    is_platform_admin: bool,
) -> list[str]:
    """Bozor kontekstidagi rollar to'plami (D-05 + D-06).

    Platforma admini a'zolik qatorisiz ham bozorga kira oladi (D-06) —
    o'shanda uning yagona roli `platform_admin` bo'ladi. A'zoligi ham
    bo'lsa, ikkala manba BIRLASHADI: bir odam ham platforma admini, ham
    o'sha bozorning kassiri bo'lishi mumkin.
    """
    roles = set(membership.roles) if membership is not None else set()
    if is_platform_admin:
        roles.add(_PLATFORM_ADMIN_ROLE)
    return sorted(roles)


def _expires_in(settings: Settings) -> int:
    return settings.access_token_ttl_minutes * SECONDS_PER_MINUTE


async def _issue_session_cookie(
    session: AsyncSession,
    response: Response,
    *,
    user_id: UUID,
    market_id: UUID,
    family_id: UUID | None,
    settings: Settings,
) -> None:
    """Refresh token qatorini yozadi va cookie'ni qo'yadi.

    TARTIB MUHIM: avval DB, keyin cookie. Teskarisi bo'lganda DB yozuvi
    yiqilsa brauzerda "mavjud, lekin topilmaydigan" token qolardi va
    foydalanuvchi keyingi `/refresh` da tushunarsiz 401 olardi.
    """
    issued = issue_refresh(user_id=user_id, family_id=family_id, settings=settings)
    await auth_repo.refresh_issue(
        session,
        market_id=market_id,
        user_id=user_id,
        jti=issued.jti,
        family_id=issued.family_id,
        expires_at=issued.expires_at,
    )
    set_refresh_cookie(response, issued.token, settings)


async def _market_ref(
    session: AsyncSession,
    market_id: UUID,
    membership: auth_repo.Membership | None,
) -> MarketRef:
    """Bozor nomini a'zolikdan yoki (platforma admini uchun) global ro'yxatdan oladi."""
    if membership is not None:
        return MarketRef(id=membership.market_id, name=membership.market_name)
    for market in await auth_repo.list_markets(session):
        if market.market_id == market_id:
            return MarketRef(id=market.market_id, name=market.market_name)
    raise _invalid_refresh()


# ---------------------------------------------------------------------------
# Endpointlar
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    cache: CacheDep,
    session: AuthSessionDep,
) -> LoginResponse:
    """Telefon + parol bilan kirish (D-01).

    A'zolik AYNAN BITTA bo'lsa bozor avtomatik tanlanadi va sessiya
    to'liq ochiladi (refresh cookie beriladi). Aks holda — platforma
    admini yoki bir nechta a'zolik — `mid` siz access token beriladi va
    keyingi qadam `/auth/select-market` bo'ladi. Refresh cookie o'shanda
    beriladi, chunki `refresh_tokens.market_id` `NOT NULL`: bozorsiz
    sessiya qatorini yozib bo'lmaydi (va bozorsiz sessiyaning ma'nosi
    ham yo'q — u hech qanday ma'lumotga kira olmaydi).
    """
    ip = _client_ip(request)
    request_id = correlation_id.get() or ""
    phone = payload.phone

    try:
        await check_login_rate(cache, phone=phone, ip=ip)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_attempts",
        ) from exc

    row = await auth_repo.find_login(session, phone)
    if row is None:
        # Vaqtni tekislash: mavjud telefon uchun Argon2 ishi bajariladi,
        # mavjud bo'lmagani uchun ham (T-01-15).
        dummy_verify()
        await _audit_login_failed(
            session, phone=phone, reason="unknown_phone", ip=ip, rid=request_id
        )
        raise _invalid_credentials()

    ok, rehashed = _verify_password_safe(payload.password, row.password_hash)
    if not ok:
        await _audit_login_failed(
            session, phone=phone, reason="bad_password", ip=ip, rid=request_id, user_id=row.user_id
        )
        raise _invalid_credentials()

    if not row.is_active:
        # Bloklanganlik OSHKOR QILINMAYDI — javob yuqoridagilar bilan
        # bayt-bayt bir xil (D-08 + T-01-40).
        await _audit_login_failed(
            session, phone=phone, reason="blocked", ip=ip, rid=request_id, user_id=row.user_id
        )
        raise _invalid_credentials()

    if rehashed is not None:
        # T-01-18: Argon2 parametrlari eskirgan -> jimgina yangilanadi.
        # `must_change=None` -> D-02 bayrog'iga TEGILMAYDI.
        await auth_repo.update_password_hash(session, row.user_id, rehashed, must_change=None)

    memberships = await auth_repo.memberships(session, row.user_id)
    await reset_login_rate(cache, phone=phone, ip=ip)

    auto_select = memberships[0] if (len(memberships) == 1 and not row.is_platform_admin) else None
    roles = _session_roles(auto_select, is_platform_admin=row.is_platform_admin)

    access_token = issue_access(
        user_id=row.user_id,
        market_id=auto_select.market_id if auto_select else None,
        roles=roles,
        is_platform_admin=row.is_platform_admin,
        settings=settings,
    )

    if auto_select is not None:
        await _issue_session_cookie(
            session,
            response,
            user_id=row.user_id,
            market_id=auto_select.market_id,
            family_id=None,
            settings=settings,
        )

    markets = await _visible_markets(session, memberships, is_platform_admin=row.is_platform_admin)

    await write_app_audit(
        session,
        action=AuditAction.LOGIN,
        table_name=TABLE_USERS,
        row_id=row.user_id,
        actor_user_id=row.user_id,
        market_id=auto_select.market_id if auto_select else None,
        request_id=request_id,
        ip=ip,
        actor_label=_login_label(row, auto_select),
        new={"roles": roles},
    )
    await session.commit()

    return LoginResponse(
        access_token=access_token,
        expires_in=_expires_in(settings),
        must_change_password=row.must_change_password,
        locale=row.locale,
        market=MarketRef(id=auto_select.market_id, name=auto_select.market_name)
        if auto_select
        else None,
        markets=markets,
        roles=roles,
        is_platform_admin=row.is_platform_admin,
    )


def _login_label(row: auth_repo.LoginRow, selected: auth_repo.Membership | None) -> str:
    """Login yozuvining `actor_label` i (D-06 platforma admini uchun to'liq matn)."""
    if row.is_platform_admin:
        return platform_admin_label(row.phone_e164, selected.market_name if selected else None)
    return actor_label_for(
        _session_roles(selected, is_platform_admin=False), is_platform_admin=False
    )


async def _visible_markets(
    session: AsyncSession,
    memberships: Sequence[auth_repo.Membership],
    *,
    is_platform_admin: bool,
) -> list[MarketRef]:
    """Bozor tanlash ekranining manbai.

    Platforma admini uchun BARCHA faol bozorlar (D-06), qolganlar uchun
    faqat o'z a'zoliklari. `auth_list_markets()` faqat nomlarni ochadi —
    hech qanday tenant ma'lumotini emas, shuning uchun u `BYPASSRLS`
    rolining o'rnini bosadi va kengaymaydi.
    """
    if is_platform_admin:
        return [
            MarketRef(id=market.market_id, name=market.market_name)
            for market in await auth_repo.list_markets(session)
            if market.is_active
        ]
    return [MarketRef(id=m.market_id, name=m.market_name) for m in memberships]


async def _audit_login_failed(
    session: AsyncSession,
    *,
    phone: str,
    reason: str,
    ip: str | None,
    rid: str,
    user_id: UUID | None = None,
) -> None:
    """`login_failed` yozuvi + COMMIT.

    COMMIT shu yerda bajariladi, chunki chaqiruvchi darhol
    `HTTPException` ko'taradi va sessiya yopilganda tranzaksiya rollback
    bo'lardi — ya'ni aynan muvaffaqiyatsiz urinishlar izsiz qolardi
    (D-09 buzilishi).

    `market_id` `None` bo'lib qoladi: rad etilgan urinishda bozor
    aniqlanmagan va uni "taxmin qilib" yozish yolg'on dalil bo'lardi.
    Bunday yozuvlar `audit_read` policy'si ostida hech kimga ko'rinmaydi —
    platforma admini uchun alohida tor yo'l 01-07 rejasida.
    """
    await write_app_audit(
        session,
        action=AuditAction.LOGIN_FAILED,
        table_name=TABLE_USERS,
        row_id=user_id,
        actor_user_id=user_id,
        market_id=None,
        request_id=rid,
        ip=ip,
        actor_label="anonim",
        new={"phone": phone, "reason": reason},
    )
    await session.commit()


@router.post("/select-market", response_model=SessionResponse)
async def select_market(
    payload: SelectMarketRequest,
    request: Request,
    response: Response,
    principal: PrincipalDep,
    settings: SettingsDep,
    session: AuthSessionDep,
    refresh_token: RefreshCookie = None,
) -> SessionResponse:
    """Bozor kontekstini tanlaydi (D-06).

    HECH QANDAY RLS BYPASS YO'Q: tanlashdan keyin `app.market_id`
    odatdagidek o'rnatiladi va platforma admini ham boshqa bozorning
    qatorini ko'ra olmaydi. `is_platform_admin` bayrog'i faqat "qaysi
    bozorlarni TANLASH mumkin" savoliga javob beradi.
    """
    request_id = correlation_id.get() or ""
    memberships = await auth_repo.memberships(session, principal.user_id)
    membership = next((m for m in memberships if m.market_id == payload.market_id), None)

    if membership is not None:
        market = MarketRef(id=membership.market_id, name=membership.market_name)
    else:
        market = await _platform_admin_market(session, principal, payload.market_id)

    roles = _session_roles(membership, is_platform_admin=principal.is_platform_admin)

    # Eski oila bekor qilinadi: bozor almashtirilganda oldingi bozorga
    # bog'langan sessiya yashab qolmasligi kerak.
    await _revoke_cookie_family(session, refresh_token, settings)

    await _issue_session_cookie(
        session,
        response,
        user_id=principal.user_id,
        market_id=market.id,
        family_id=None,
        settings=settings,
    )

    label = principal.actor_label
    if principal.is_platform_admin:
        who = await auth_repo.find_login_by_id(session, principal.user_id)
        label = platform_admin_label(who.phone_e164 if who else None, market.name)

    await write_app_audit(
        session,
        action=AuditAction.MARKET_SELECTED,
        table_name=TABLE_MARKETS,
        row_id=market.id,
        actor_user_id=principal.user_id,
        market_id=market.id,
        request_id=request_id,
        ip=_client_ip(request),
        actor_label=label,
        new={"roles": roles},
    )
    await session.commit()

    return SessionResponse(
        access_token=issue_access(
            user_id=principal.user_id,
            market_id=market.id,
            roles=roles,
            is_platform_admin=principal.is_platform_admin,
            settings=settings,
        ),
        expires_in=_expires_in(settings),
        roles=roles,
        market=market,
    )


async def _platform_admin_market(
    session: AsyncSession,
    principal: PrincipalDep,
    market_id: UUID,
) -> MarketRef:
    """A'zoligi bo'lmagan bozorni tanlash — FAQAT platforma admini uchun (D-06).

    Mavjud bo'lmagan bozor ham, ruxsat etilmagan bozor ham AYNAN bir xil
    403 beradi: aks holda javob "bunday bozor bor" degan ma'lumotni
    oshkor qilardi.
    """
    forbidden = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="market_forbidden")
    if not principal.is_platform_admin:
        raise forbidden
    for market in await auth_repo.list_markets(session):
        if market.market_id == market_id and market.is_active:
            return MarketRef(id=market.market_id, name=market.market_name)
    raise forbidden


async def _revoke_cookie_family(
    session: AsyncSession,
    refresh_token: str | None,
    settings: Settings,
) -> UUID | None:
    """Cookie'dagi tokenning oilasini bekor qiladi; oila `id` sini qaytaradi.

    Yaroqsiz/muddati o'tgan cookie JIMGINA e'tiborsiz qoldiriladi — bu
    yo'l logout va bozor almashtirish uchun ishlatiladi va ikkalasi ham
    "cookie yo'q" holatida ham muvaffaqiyatli tugashi kerak.
    """
    if not refresh_token:
        return None
    try:
        claims = decode(refresh_token, expected_type="refresh", settings=settings)
    except jwt.InvalidTokenError:
        return None
    if claims.family_id is None:
        return None
    family_id = UUID(claims.family_id)
    await auth_repo.refresh_revoke_family(session, family_id)
    return family_id


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    settings: SettingsDep,
    session: AuthSessionDep,
    refresh_token: RefreshCookie = None,
) -> SessionResponse:
    """Sessiyani uzaytiradi — rotatsiya + reuse detection (D-03, T-01-41).

    Huquqlar HAR SAFAR DB'dan qayta o'qiladi: refresh tokenda `roles` va
    `mid` ATAYIN yo'q (01-03). Aks holda roli olib tashlangan yoki
    bloklangan foydalanuvchi 30 kun davomida eski huquqlari bilan yangi
    access token olib turardi.
    """
    request_id = correlation_id.get() or ""
    ip = _client_ip(request)

    if not refresh_token:
        raise _invalid_refresh()
    try:
        claims = decode(refresh_token, expected_type="refresh", settings=settings)
    except jwt.InvalidTokenError as exc:
        log.info("refresh_token_rejected", error=type(exc).__name__)
        raise _invalid_refresh() from exc

    row = await auth_repo.refresh_find(session, claims.jti)
    if row is None:
        raise _invalid_refresh()

    if row.revoked_at is not None:
        # O'G'IRLANGAN TOKEN: allaqachon rotatsiya qilingan `jti` qaytib
        # keldi. Butun oila bekor qilinadi — ya'ni hujumchi ham, haqiqiy
        # foydalanuvchi ham qaytadan login qilishi kerak bo'ladi. Bu
        # ataylab: o'g'irlik sodir bo'lganini foydalanuvchi SEZISHI kerak.
        await _handle_reuse(session, row, ip=ip, rid=request_id)
        clear_refresh_cookie(response)
        raise _invalid_refresh()

    if row.expires_at <= datetime.now(UTC):
        raise _invalid_refresh()

    who = await auth_repo.find_login_by_id(session, row.user_id)
    if who is None or not who.is_active:
        # D-08: bloklangan foydalanuvchining uzoq umrli sessiyasi ham o'ladi.
        await auth_repo.refresh_revoke_family(session, row.family_id)
        await session.commit()
        clear_refresh_cookie(response)
        raise _invalid_refresh()

    memberships = await auth_repo.memberships(session, row.user_id)
    membership = next((m for m in memberships if m.market_id == row.market_id), None)
    if membership is None and not who.is_platform_admin:
        # A'zolik olib tashlangan — sessiya davom etmaydi.
        await auth_repo.refresh_revoke_family(session, row.family_id)
        await session.commit()
        clear_refresh_cookie(response)
        raise _invalid_refresh()

    issued = issue_refresh(user_id=row.user_id, family_id=row.family_id, settings=settings)
    rotated = await auth_repo.refresh_rotate(session, old_jti=claims.jti, new_jti=issued.jti)
    if rotated == 0:
        # Poyga: boshqa so'rov ayni tokenni allaqachon rotatsiya qildi.
        # Bu ham reuse — yuqoridagi tekshiruv bilan bir xil qarorga keladi.
        await _handle_reuse(session, row, ip=ip, rid=request_id)
        clear_refresh_cookie(response)
        raise _invalid_refresh()

    await auth_repo.refresh_issue(
        session,
        market_id=row.market_id,
        user_id=row.user_id,
        jti=issued.jti,
        family_id=issued.family_id,
        expires_at=issued.expires_at,
    )
    set_refresh_cookie(response, issued.token, settings)
    await session.commit()

    roles = _session_roles(membership, is_platform_admin=who.is_platform_admin)
    return SessionResponse(
        access_token=issue_access(
            user_id=row.user_id,
            market_id=row.market_id,
            roles=roles,
            is_platform_admin=who.is_platform_admin,
            settings=settings,
        ),
        expires_in=_expires_in(settings),
        roles=roles,
        market=await _market_ref(session, row.market_id, membership),
    )


async def _handle_reuse(
    session: AsyncSession,
    row: auth_repo.RefreshRow,
    *,
    ip: str | None,
    rid: str,
) -> None:
    """Oilani bekor qiladi, audit yozadi va COMMIT qiladi (T-01-41)."""
    revoked = await auth_repo.refresh_revoke_family(session, row.family_id)
    log.warning(
        "refresh_reuse_detected",
        user_id=str(row.user_id),
        family_id=str(row.family_id),
        revoked=revoked,
    )
    await write_app_audit(
        session,
        action=AuditAction.REFRESH_REUSE_DETECTED,
        table_name=TABLE_REFRESH_TOKENS,
        row_id=row.family_id,
        actor_user_id=row.user_id,
        market_id=row.market_id,
        request_id=rid,
        ip=ip,
        actor_label="sessiya",
        new={"revoked_tokens": revoked},
    )
    await session.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(
    request: Request,
    settings: SettingsDep,
    session: AuthSessionDep,
    refresh_token: RefreshCookie = None,
) -> Response:
    """Sessiyani yopadi — token oilasi bekor qilinadi va cookie o'chiriladi.

    Cookie bo'lmasa ham 204: logout IDEMPOTENT bo'lishi kerak, aks holda
    "sessiyam allaqachon tugagan" holatida foydalanuvchi xato ko'rardi.
    """
    request_id = correlation_id.get() or ""
    if refresh_token:
        claims = None
        try:
            claims = decode(refresh_token, expected_type="refresh", settings=settings)
        except jwt.InvalidTokenError:
            log.info("logout_with_invalid_cookie")
        if claims is not None and claims.family_id is not None:
            row = await auth_repo.refresh_find(session, claims.jti)
            await auth_repo.refresh_revoke_family(session, UUID(claims.family_id))
            await write_app_audit(
                session,
                action=AuditAction.LOGOUT,
                table_name=TABLE_REFRESH_TOKENS,
                row_id=UUID(claims.family_id),
                actor_user_id=claims.user_id,
                market_id=row.market_id if row else None,
                request_id=request_id,
                ip=_client_ip(request),
                actor_label="sessiya",
            )
            await session.commit()

    out = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(out)
    return out


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    principal: PrincipalDep,
    cache: CacheDep,
    session: AuthSessionDep,
) -> Response:
    """Parolni almashtiradi (D-02) va BARCHA sessiyalarni bekor qiladi.

    Sessiyalarni bekor qilish majburiy (ASVS V7): parol almashtirishning
    asosiy sababi — "parolim boshqasiga ma'lum" shubhasi. Eski sessiyalar
    yashab qolsa, almashtirishning ma'nosi qolmaydi.
    """
    weak = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weak_password")
    if not validate_password_strength(payload.new_password):
        raise weak
    if payload.new_password == payload.current_password:
        raise weak

    row = await auth_repo.find_login_by_id(session, principal.user_id)
    if row is None:
        raise _invalid_credentials()

    ok, _ = _verify_password_safe(payload.current_password, row.password_hash)
    if not ok:
        raise _invalid_credentials()

    await auth_repo.update_password_hash(
        session,
        principal.user_id,
        hash_password(payload.new_password),
        must_change=False,
    )
    revoked = await auth_repo.refresh_revoke_user(session, principal.user_id)

    await write_app_audit(
        session,
        action=AuditAction.PASSWORD_CHANGED,
        table_name=TABLE_USERS,
        row_id=principal.user_id,
        principal=principal,
        ip=_client_ip(request),
        new={"revoked_sessions": revoked},
    )
    await session.commit()
    await invalidate_user_state(cache, principal.user_id)

    out = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(out)
    return out


@router.get("/me", response_model=MeResponse)
async def me(principal: PrincipalDep, session: TenantSessionDep) -> MeResponse:
    """Joriy sessiya tavsifi — bozor nomi TENANT SESSIYASIDAN o'qiladi.

    So'rov ATAYIN filtrsiz (`SELECT id, name FROM markets`): `markets`
    policy'si `id = app.market_id` bo'lgani uchun u AYNAN BITTA qator
    qaytaradi. Ya'ni bu endpoint tenant kontekstining uchdan-uchiga
    ishlayotganini har chaqiruvda isbotlaydi — noto'g'ri o'rnatilgan
    kontekst bu yerda 0 qator bo'lib DARHOL ko'rinadi.

    Bozor tanlanmagan bo'lsa `get_tenant_session` 409 qaytaradi.
    """
    result = await session.execute(text("SELECT id, name FROM markets"))
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")

    return MeResponse(
        user_id=principal.user_id,
        market=MarketRef(id=row.id, name=row.name),
        roles=sorted(principal.roles),
        permissions=sorted(str(perm) for perm in principal.permissions),
        is_platform_admin=principal.is_platform_admin,
    )
