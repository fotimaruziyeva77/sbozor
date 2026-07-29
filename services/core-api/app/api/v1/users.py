"""Foydalanuvchi boshqaruvi — ikki bosqichli yaratish, bloklash, parol tiklash.

=============================================================================
ROL BERISH DARAJASI — BU YERDA, `rbac.py` DA EMAS (D-04).

`USER_MANAGE` huquqi "foydalanuvchi boshqarish" degani, "ISTALGAN ROLNI
BERISH" degani EMAS. Ikki bosqichli model quyidagicha ishlaydi:

| Yaratuvchi          | Bera oladigan rollar          | Nazorat             |
| ------------------- | ----------------------------- | ------------------- |
| platforma admini    | cheklovsiz (bozor admini,     | `is_platform_admin` |
|                     | direktor, kassir, nazoratchi) |                     |
| bozor admini        | AYNAN {kassir, nazoratchi}    | pastdagi darvoza    |

Ya'ni bozor admini o'ziga TENG (`market_admin`) yoki undan yuqori
(`director`, `platform_admin`) rol yarata OLMAYDI — aks holda u bir
so'rov bilan o'zining nazoratchisini (direktorni) yoki cheksiz sonli
teng huquqli adminni tug'dira olardi va D-04 ning butun ma'nosi
yo'qolardi (T-01-50, ASVS V8).

Bu tekshiruv MATRITSAGA qo'shilmadi: `ROLE_PERMISSIONS` "rol -> huquq"
jadvali, bu yerda esa "rol -> qaysi ROLNI bera oladi" munosabati kerak.
Uni matritsaga siqish har bir rol-juftligi uchun alohida permission
talab qilardi (`USER_MANAGE_CASHIER`, `USER_MANAGE_DIRECTOR`, ...) va
matritsa o'qib bo'lmas holga kelardi. Sabab `security/rbac.py` fayl
docstringida ham qayd etilgan.
=============================================================================

CROSS-TENANT JAVOB — HAR DOIM 404 (T-01-51). Boshqa bozor foydalanuvchisi
ID'si bilan kelgan har qanday amal `user_market_roles` da RLS ostida 0
qator topadi va "topilmadi" javobini oladi. 403 QAYTARILMAYDI: javobning
o'zi "bunday foydalanuvchi bor, lekin sizniki emas" degan ma'lumotni
oshkor qilardi.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sbozor_core.enums import AuditAction, Role
from sbozor_core.security import hash_password

from app.deps import (
    CacheDep,
    Principal,
    TenantSessionDep,
    invalidate_user_state,
    require_permission,
)
from app.repositories import auth_repo
from app.repositories.user_repo import UserRepository
from app.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    UserListItem,
    UserListResponse,
)
from app.security.audit import TABLE_USERS, write_app_audit
from app.security.rbac import Permission

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

router = APIRouter(tags=["users"])

MARKET_ADMIN_ASSIGNABLE_ROLES = frozenset({Role.CASHIER, Role.INSPECTOR})
"""Bozor admini bera oladigan rollar to'plami (D-04 ikkinchi bosqichi).

`frozenset` — ro'yxat ish paytida o'zgartirilishi mumkin bo'lmasligi kerak.
Bu to'plamga yangi rol qo'shish = D-04 ni o'zgartirish, ya'ni u kod
review'dan va `tests/integration/test_users_api.py` dagi uchta rad etish
testidan o'tishi shart.
"""

TEMPORARY_PASSWORD_BYTES = 9
"""`secrets.token_urlsafe(9)` -> 12 belgi.

`MIN_PASSWORD_LENGTH` (10) dan uzun, ya'ni yaratilgan foydalanuvchi bu
parol bilan login qila oladi va uni birinchi kirishda almashtiradi.
Qisqaroq qiymat "vaqtinchalik parol siyosatdan o'tmaydi" degan jimgina
tuzoqni yaratardi.
"""

_ROLE_NOT_ALLOWED = "role_not_allowed"
_USER_NOT_FOUND = "not_found"

UserManagerDep = Annotated[Principal, Depends(require_permission(Permission.USER_MANAGE))]
UserViewerDep = Annotated[Principal, Depends(require_permission(Permission.USER_VIEW))]


def _temporary_password() -> str:
    """Bir martalik vaqtinchalik parol (D-02)."""
    return secrets.token_urlsafe(TEMPORARY_PASSWORD_BYTES)


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor.

    `TenantSessionDep` allaqachon 409 qaytargan bo'lardi; bu tekshiruv
    mypy uchun emas, KELAJAK uchun: kimdir endpointni tenant sessiyasisiz
    qayta yozsa, `market_id=None` bilan a'zolik qatori yozilib ketmasin.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _assert_roles_assignable(principal: Principal, roles: Sequence[Role]) -> None:
    """D-04 rol berish darajasi darvozasi — YARATISHDAN OLDIN (T-01-50).

    Rad etish DB'ga tegilmasdan sodir bo'ladi: `auth_create_user` ham,
    a'zolik qatori ham chaqirilmaydi, ya'ni muvaffaqiyatsiz urinishdan
    keyin bazada hech qanday qoldiq qolmaydi.
    """
    if principal.is_platform_admin:
        return
    requested = set(roles)
    if not requested <= MARKET_ADMIN_ASSIGNABLE_ROLES:
        log.info(
            "role_assignment_denied",
            requested=sorted(str(role) for role in requested),
            allowed=sorted(str(role) for role in MARKET_ADMIN_ASSIGNABLE_ROLES),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ROLE_NOT_ALLOWED)


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan foydalanuvchi uchun BIR XIL javob."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND)


@router.get("", response_model=UserListResponse)
async def list_users(principal: UserViewerDep, session: TenantSessionDep) -> UserListResponse:
    """Joriy bozor a'zolari (`USER_VIEW`).

    Ro'yxatni RLS cheklaydi: a'zolik qatorlari `user_market_roles` dan
    tenant policy ostida o'qiladi, profil esa faqat o'sha ID'lar bo'yicha
    boyitiladi (`app/repositories/user_repo.py` dagi ikki qatlamli naqsh).
    """
    repo = UserRepository(session, _market_id(principal))
    members = await repo.list_members()
    return UserListResponse(
        items=[
            UserListItem(
                id=member.user_id,
                phone=member.phone,
                full_name=member.full_name,
                roles=list(member.roles),
                is_active=member.is_active,
                must_change_password=member.must_change_password,
                locale=member.locale,
                created_at=member.created_at,
            )
            for member in members
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    principal: UserManagerDep,
    session: TenantSessionDep,
) -> CreateUserResponse:
    """Foydalanuvchi yaratadi (D-04) va vaqtinchalik parol beradi (D-02).

    TARTIB ATAYIN SHUNDAY:
      1. rol berish darajasi darvozasi (403) — DB'ga TEGILMASDAN;
      2. `users` qatori (`auth_create_user`) — telefon band bo'lsa 409;
      3. a'zolik qatori (RLS `WITH CHECK` ostida) — u audit triggerini
         o'zi ishga tushiradi;
      4. `users` uchun QO'LDA audit yozuvi — funksiya ichida trigger yo'q.

    Vaqtinchalik parol javobda BIR MARTA ochiq ketadi va boshqa hech
    qayerda saqlanmaydi: auditga parol ham, hash ham yozilmaydi (T-01-52),
    log'da esa `censor_secrets` `temporary_password` kalitini maskalaydi.
    """
    _assert_roles_assignable(principal, payload.roles)

    repo = UserRepository(session, _market_id(principal))
    roles = [str(role) for role in payload.roles]
    locale = str(payload.locale)
    temporary = _temporary_password()

    user_id = await repo.create_user(
        phone=payload.phone,
        password_hash=hash_password(temporary),
        full_name=payload.full_name,
        locale=locale,
    )
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="phone_taken")

    await repo.add_membership(user_id, roles)
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_USERS,
        row_id=user_id,
        principal=principal,
        new={"phone": payload.phone, "roles": roles, "locale": locale},
    )

    return CreateUserResponse(id=user_id, temporary_password=temporary)


@router.post(
    "/{user_id}/block",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def block_user(
    user_id: UUID,
    principal: UserManagerDep,
    session: TenantSessionDep,
    cache: CacheDep,
    background: BackgroundTasks,
) -> Response:
    """Foydalanuvchini bloklaydi — DARHOL kuchga kiradi (D-08).

    O'ZINI BLOKLASH RAD ETILADI: bozorda yagona admin o'zini bloklab
    qo'ysa, bozor boshqaruvsiz qoladi va uni faqat platforma admini
    tiklay oladi.
    """
    if user_id == principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot_block_self",
        )
    await _set_member_active(
        session,
        principal,
        user_id,
        is_active=False,
        action=AuditAction.USER_BLOCKED,
    )
    # Valkey `user:state:{id}` kaliti COMMIT dan KEYIN o'chiriladi (D-08).
    # `BackgroundTasks` FastAPI'da javob yuborilgandan so'ng ishlaydi,
    # dependency'ning tranzaksiyasi esa undan OLDIN yopiladi. Teskari
    # tartibda (endpoint ichida invalidatsiya) parallel so'rov hali commit
    # bo'lmagan "faol" holatni qaytadan keshlab qo'yardi va bloklash TTL
    # tugagunicha (30 s) kuchga kirmasdi.
    background.add_task(invalidate_user_state, cache, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{user_id}/unblock",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def unblock_user(
    user_id: UUID,
    principal: UserManagerDep,
    session: TenantSessionDep,
    cache: CacheDep,
    background: BackgroundTasks,
) -> Response:
    """Bloklangan foydalanuvchini tiklaydi (D-08)."""
    await _set_member_active(
        session,
        principal,
        user_id,
        is_active=True,
        action=AuditAction.USER_UNBLOCKED,
    )
    background.add_task(invalidate_user_state, cache, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: UUID,
    principal: UserManagerDep,
    session: TenantSessionDep,
) -> ResetPasswordResponse:
    """Admin orqali parol tiklash (D-02) — SMS/email/bot-kod oqimi YO'Q.

    Uchta narsa BIRGA bajariladi va ularni ajratib bo'lmaydi:
      * yangi vaqtinchalik parol + `must_change_password = true`;
      * foydalanuvchining BARCHA refresh sessiyalari bekor qilinadi
        (ASVS V7 — tiklashning sababi ko'pincha "parolim boshqasiga
        ma'lum" shubhasi, ya'ni eski sessiyalar yashab qolmasligi kerak);
      * audit yozuvi (kim kimning parolini tikladi).
    """
    repo = UserRepository(session, _market_id(principal))
    if await repo.member_roles(user_id) is None:
        raise _not_found()

    temporary = _temporary_password()
    await repo.set_temporary_password(user_id, hash_password(temporary))
    revoked = await auth_repo.refresh_revoke_user(session, user_id)

    await write_app_audit(
        session,
        action=AuditAction.PASSWORD_RESET,
        table_name=TABLE_USERS,
        row_id=user_id,
        principal=principal,
        new={"must_change_password": True, "revoked_sessions": revoked},
    )

    return ResetPasswordResponse(temporary_password=temporary)


async def _set_member_active(
    session: AsyncSession,
    principal: Principal,
    user_id: UUID,
    *,
    is_active: bool,
    action: AuditAction,
) -> None:
    """`block`/`unblock` ning umumiy qismi: a'zolik tekshiruvi + yozuv + audit.

    `old` qiymati TAXMIN QILINMAYDI — u yozuvdan oldin `auth_user_state()`
    bilan o'qiladi. "Bloklash so'ralgan, demak avval faol edi" degan
    taxmin allaqachon bloklangan foydalanuvchi uchun jurnalga YOLG'ON
    eski qiymat yozardi, jurnal esa aynan nizoni hal qilish uchun bor.
    """
    repo = UserRepository(session, _market_id(principal))
    if await repo.member_roles(user_id) is None:
        raise _not_found()

    state = await auth_repo.user_state(session, user_id)
    await repo.set_active(user_id, is_active=is_active)
    await write_app_audit(
        session,
        action=action,
        table_name=TABLE_USERS,
        row_id=user_id,
        principal=principal,
        old={"is_active": state.is_active} if state is not None else None,
        new={"is_active": is_active},
    )
