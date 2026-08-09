"""FastAPI dependency'lari — principal, bloklash keshi va tenant sessiyasi.

=============================================================================
TO'RTTA DEPENDENCY, TO'RTTA ALOHIDA MAS'ULIYAT:

1. `get_current_principal` — KIM? Access tokenni tekshiradi va foydalanuvchi
   HALI BLOKLANMAGANINI Valkey keshi orqali aniqlaydi (D-08).
2. `require_password_current` — HOZIR KIRA OLADIMI? Vaqtinchalik parol
   almashtirilmagan bo'lsa (D-02) hech qanday tenant/yozuv endpointiga
   yo'l yo'q. Bu SESSIYA HOLATI darajasidagi nazorat.
3. `require_permission(...)` — NIMA QILISHI MUMKIN? Kodda qat'iy matritsa
   (D-07). Bu FUNKSIYA darajasidagi nazorat.
4. `get_tenant_session` — QAYSI BOZORDA? Tranzaksiya ochadi va tenant
   GUC'larini o'rnatadi. Bu MA'LUMOT darajasidagi nazorat (RLS).

3 va 4 bir-birining o'rnini BOSMAYDI: `require_permission` "kassir to'lov
kirita oladi" deydi, RLS esa "faqat O'Z bozorida" deydi. Birinchisisiz
har kim hamma narsani qila olardi; ikkinchisisiz kassir boshqa bozorning
to'lovini kirita olardi.

2 esa ikkalasidan ham OLDIN turadi va 3 hamda 4 ning ICHIDAN chaqiriladi,
ya'ni har qanday tenant yoki huquq talab qiladigan endpoint undan
AVTOMATIK o'tadi.

LEKIN BU AVTOMATIKLIK TO'LIQ EMAS — VA BU YERDA ANIQ AYTILADI (WR-02):
`PrincipalDep + AuthSessionDep` juftligi yaroqli naqsh va u darvozani
CHETLAB O'TADI. Ya'ni "yangi endpoint yozgan odam darvozani qo'shishni
unutishi mumkin emas" degan da'vo NOTO'G'RI edi: 1-faza ko'rigi aynan
shu yo'ldan qurilgan ikkita yozuv endpointini topdi
(`POST /auth/select-market` va `PATCH /api/v1/me`) va ikkalasi ham
2-fazada `CurrentPasswordDep` ga o'tkazildi.

QOIDA: `PrincipalDep` faqat O'QISH endpointi uchun va faqat qulflangan
sessiyaga ATAYIN ochiq bo'lishi kerak bo'lganda ishlatiladi. Yozadigan
(`POST`/`PATCH`/`PUT`/`DELETE`) yoki sessiya yaratadigan har qanday
endpoint `CurrentPasswordDep` oladi.

Darvozadan ATAYIN tashqarida qoladigan AYNAN uchta yo'l:
  * `POST /api/v1/auth/change-password` — darvozadan chiqish yo'lining o'zi;
  * `POST /api/v1/auth/logout` — qulflangan sessiyani tark etish;
  * `GET  /api/v1/me` — parol almashtirish ekrani foydalanuvchining tilini
    bilishi kerak (D-13), aks holda u tushunmaydigan tilda qulflanardi.
`POST /auth/login` va `POST /auth/refresh` bu ro'yxatga KIRMAYDI: ularda
principal umuman yo'q (biri parol, ikkinchisi cookie bilan ishlaydi).
`refresh` bergan access token esa har so'rovda `get_current_principal`
orqali qayta tekshiriladi — ya'ni u darvozani chetlab o'tolmaydi.

`require_platform_admin` — 3 ning MAXSUS HOLI, beshinchi mas'uliyat EMAS:
u ham FUNKSIYA darajasidagi nazorat va u ham 2 ga bog'langan. Farqi
manbada: u rol/huquqqa emas, `users.is_platform_admin` BAYROG'IGA
qaraydi (CR-03) va tenant sessiyasini TALAB QILMAYDI.
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
    "AuthSessionDep",
    "CacheDep",
    "CurrentPasswordDep",
    "Principal",
    "PrincipalDep",
    "SettingsDep",
    "TenantSessionDep",
    "USER_STATE_TTL_SECONDS",
    "actor_label_for",
    "get_auth_session",
    "get_cache",
    "get_current_principal",
    "get_settings_dep",
    "get_tenant_session",
    "invalidate_user_state",
    "require_password_current",
    "require_permission",
    "require_platform_admin",
    "require_roles",
    "user_state_key",
]

log = structlog.get_logger(__name__)

USER_STATE_TTL_SECONDS = 30
"""Foydalanuvchi holati keshining amal qilish muddati (D-08, D-02).

Eng yomon holat — 30 soniya kechikish. Amalda kechikish YO'Q: holatni
o'zgartiruvchi HAR BIR endpoint (`block`, `unblock`, `reset-password`,
`change-password`) yozuvdan keyin `invalidate_user_state()` chaqiradi va
keyingi so'rov DB'dan o'qiydi. TTL — o'sha invalidatsiya biror sababga
ko'ra bajarilmay qolgan holat uchun yuqori chegara.
"""

_FLAG_TRUE = "1"
_FLAG_FALSE = "0"
_STATE_FLAGS = frozenset({_FLAG_TRUE, _FLAG_FALSE})
_STATE_CODE_LENGTH = 2
"""Kesh qiymati — IKKI belgili holat kodi: `{faol}{majburiy-almashtirish}`.

Bitta belgi (eski shakl) YETARLI EMAS: `must_change_password` endi kirish
qarorining bir qismi (`require_password_current`), ya'ni u ham AYNAN
o'sha qatordan, AYNAN o'sha kesh yozuvidan kelishi kerak. Ikkinchi kalit
qo'shish ikkita mustaqil TTL va ikkita invalidatsiya nuqtasini
tug'dirardi — o'shanda bittasi eskirib, ikkinchisi yangilanib qolishi
mumkin edi.
"""

_PASSWORD_CHANGE_REQUIRED = "password_change_required"  # noqa: S105 — javob kodi, sir emas

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
    must_change_password: bool = False
    """D-02: vaqtinchalik parol hali almashtirilmagan.

    Qiymat TOKENDAN OLINMAYDI — u `is_active` bilan BIR XIL manbadan
    (`auth_user_state()` ning bitta qatori, D-08 keshi) keladi. Tokenga
    yozilganda 15 daqiqalik access token parol almashtirilgandan keyin
    ham "hali almashtirilmagan" deb turaverardi, ya'ni foydalanuvchi o'z
    parolini almashtirib ham qulf ortida qolardi.
    """

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
    """Tenant kontekstisiz sessiya — BOZORGA BOG'LIQ BO'LMAGAN oqimlar uchun.

    Ikki iste'molchisi bor va ikkalasida ham bozor BO'LMASLIGI MUMKIN:
      * `/api/v1/auth/*` — login paytida bozor hali aniqlanmagan;
      * `/api/v1/me` — profil (ism, til) bozorga tegishli emas va
        platforma admini uni bozor tanlashdan OLDIN ham ko'radi (D-13).

    Shuning uchun bu yerda `set_tenant_context()` chaqirilmaydi: barcha
    so'rovlar `SECURITY DEFINER` funksiyalari orqali ketadi
    (`app/repositories/auth_repo.py`, `app/repositories/user_repo.py`).

    TENANT MA'LUMOTI UCHUN ISHLATILMAYDI: bu sessiyada RLS predikati
    bo'sh GUC bilan ishlaydi, ya'ni har qanday tenant jadvali fail-closed
    0 qator beradi. Bozor doirasidagi har bir endpoint `TenantSessionDep`
    ni oladi.

    Tranzaksiya ATAYIN ochilmaydi: rad etish yo'llari audit qatorini
    yozib, uni COMMIT qilib, KEYIN `HTTPException` ko'taradi. Umumiy
    `async with session.begin():` bloki bo'lganda `HTTPException` rollback
    keltirib chiqarardi va aynan muvaffaqiyatsiz urinishlar izsiz qolardi.
    """
    async with _sessionmaker(request)() as session:
        yield session


AuthSessionDep = Annotated["AsyncSession", Depends(get_auth_session)]


async def _user_state(
    request: Request,
    cache: Redis,
    user_id: UUID,
) -> tuple[bool, bool]:
    """`(faol, majburiy-parol-almashtirish)`: avval Valkey keshi, promahda DB.

    IKKALA BAYROQ HAM BITTA `auth_user_state()` QATORIDAN olinadi va bitta
    kesh yozuvi ostida saqlanadi (D-08 + D-02). Ularni ajratish ikkita
    mustaqil TTL yaratardi va bittasi eskirib qolgan holat jimgina paydo
    bo'lardi — masalan "parol almashtirildi" keshda, "bloklandi" esa DB'da.

    FAIL-OPEN EMAS: Valkey o'chgan yoki qiymat tanib bo'lmas bo'lsa javob
    DB'dan olinadi. Keshning yagona vazifasi — har so'rovda `users` ga
    bormaslik.
    """
    key = user_state_key(user_id)
    try:
        cached = await cache.get(key)
    except RedisError as exc:
        log.warning("user_state_cache_read_failed", user_id=str(user_id), error=str(exc))
        cached = None

    if cached is not None:
        decoded = _decode_state(cached)
        if decoded is not None:
            return decoded

    async with _sessionmaker(request)() as session:
        state = await auth_repo.user_state(session, user_id)

    # Foydalanuvchi umuman topilmasa (o'chirilgan) — bloklangan deb qaraladi.
    is_active = bool(state and state.is_active)
    must_change = bool(state and state.must_change_password)

    try:
        await cache.set(
            key,
            _encode_state(is_active=is_active, must_change=must_change),
            ex=USER_STATE_TTL_SECONDS,
        )
    except RedisError as exc:
        log.warning("user_state_cache_write_failed", user_id=str(user_id), error=str(exc))

    return is_active, must_change


def _encode_state(*, is_active: bool, must_change: bool) -> str:
    """Ikki bayroqni ikki belgili kesh qiymatiga o'giradi."""
    active = _FLAG_TRUE if is_active else _FLAG_FALSE
    pending = _FLAG_TRUE if must_change else _FLAG_FALSE
    return active + pending


def _decode_state(cached: Any) -> tuple[bool, bool] | None:
    """Kesh qiymatini bayroqlarga o'giradi; TANIB BO'LMASA `None`.

    `None` — "kesh promahi" degani, "hammasi joyida" EMAS. Bu ataylab
    fail-closed emas, fail-to-source: eski (bir belgili) yoki buzilgan
    qiymat uchraganda javob DB'dan qayta olinadi. Aks holda deploy
    paytida keshda qolgan eski format jimgina `must_change=false` deb
    talqin qilinardi va darvoza 30 soniyaga ochilib qolardi.
    """
    raw = cached.decode() if isinstance(cached, bytes | bytearray) else str(cached)
    if len(raw) != _STATE_CODE_LENGTH or not set(raw) <= _STATE_FLAGS:
        log.info("user_state_cache_value_unrecognized", length=len(raw))
        return None
    return raw[0] == _FLAG_TRUE, raw[1] == _FLAG_TRUE


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

    is_active, must_change = await _user_state(request, cache, claims.user_id)
    if not is_active:
        # BLOKLASH BIRINCHI: bloklangan hisob uchun javob "parolni
        # almashtiring" bo'lmasligi kerak — u umuman kira olmaydi.
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
        must_change_password=must_change,
    )


PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


async def require_password_current(principal: PrincipalDep) -> Principal:
    """Vaqtinchalik parol almashtirilmaguncha kirishni RAD ETADI (D-02, CR-01).

    NEGA 403, 401 EMAS: sessiya YAROQLI — token to'g'ri, foydalanuvchi
    bloklanmagan. Rad etishning sababi da'voda emas, HOLATDA. 401 bo'lganda
    frontend sessiyani o'lgan deb hisoblab login sahifasiga qaytarardi va
    foydalanuvchi cheksiz siklga tushardi (kirish -> 401 -> kirish).

    `password_change_required` kodi frontendning `api-types.ts` sida
    ALLAQACHON zaxiralangan — u shu javobni ko'rgach parol almashtirish
    formasiga yo'naltiradi.

    Bu dependency ENDPOINTLARGA QO'LDA ULANMAYDI: u `get_tenant_session`,
    `require_permission` va `require_roles` ning ICHIDAN chaqiriladi, ya'ni
    har bir tenant/yozuv endpointi undan avtomatik o'tadi. Qo'lda ulash
    "yangi endpointga qo'shishni unutish" xatosini ochiq qoldirardi.
    """
    if principal.must_change_password:
        log.info("password_change_required", user_id=str(principal.user_id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_PASSWORD_CHANGE_REQUIRED,
        )
    return principal


CurrentPasswordDep = Annotated[Principal, Depends(require_password_current)]


async def get_tenant_session(
    request: Request,
    principal: CurrentPasswordDep,
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

    Parol darvozasi (`CurrentPasswordDep`) huquq tekshiruvidan OLDIN hal
    bo'ladi: vaqtinchalik parol egasi uchun javob `password_change_required`
    bo'ladi, `forbidden` EMAS. Testlar buni hisobga olishi SHART — aks
    holda RBAC rad etish testi darvoza tufayli yashil qolib, huquq
    matritsasini umuman sinamay qo'yardi (T-01-83).
    """

    async def _require(principal: CurrentPasswordDep) -> Principal:
        if perm not in principal.permissions:
            log.info(
                "permission_denied",
                required=str(perm),
                roles=sorted(principal.roles),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    # INTROSPEKTSIYA TEGI — ISH PAYTIDA HECH KIM O'QIMAYDI.
    #
    # Bu atribut xulqqa MUTLAQO ta'sir qilmaydi: darvoza yuqoridagi
    # `if perm not in ...` shartida va faqat o'sha yerda. Teg BITTA
    # iste'molchi uchun bor — `tests/tenancy/test_personal_data_coverage.py`
    # marshrutning bog'liqlik grafini yurib "bu yerda qaysi huquq talab
    # qilingan?" savoliga javob olishi kerak.
    #
    # MUQOBILI MANBA MATNINI REGEX BILAN TIRNASH EDI va u yomonroq:
    # dekorator shakli o'zgarganda (masalan `dependencies=[...]` boshqa
    # qatorga ko'chirilganda yoki alias orqali berilganda) regex hech nima
    # topmasdi va darvoza JIMGINA yashil bo'lib qolardi — ya'ni unutish
    # xavfsiz tomonga emas, XAVFLI tomonga ishlardi.
    #
    # `type: ignore` — yopilma obyekti `Callable` sifatida tiplangan va
    # unga atribut qo'yish mypy uchun xato. Sinf (`__call__` li obyekt)
    # bilan qayta yozish tipni toza qilardi, lekin u xavfsizlik-kritik
    # darvozaning butun shaklini o'zgartirardi; `setattr()` esa ruff B010
    # ga tushardi. Eng kichik va eng ko'rinadigan variant tanlandi.
    _require.required_permission = perm  # type: ignore[attr-defined]
    return _require


def require_any_permission(
    *perms: Permission,
) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Sanab o'tilgan huquqlardan KAMIDA BITTASI yetarli bo'lgan darvoza.

    =======================================================================
    ⛔ BU `require_permission()` NING QULAYROQ SHAKLI EMAS — U BOSHQA
       MA'NO VA UNI ADASHTIRISH XAVFLI.

    `require_permission(P)` — «bu resursni P egasi ko'radi».
    `require_any_permission(P, Q)` — «bu resursni IKKI XIL ish uchun ikki
    xil odam ko'radi». Ikkinchisini birinchisi bilan ifodalash uchun
    yagona yo'l — Q roliga P ni ham berish, ya'ni ROL YUZASINI kengaytirish.
    Aynan shu narsa `OCCUPANCY_REVIEW` uchun rad etildi (05-15): nazoratchi
    dalil kadrini ko'rishi kerak, LEKIN kamera reestrini, jonli tasvirni va
    NVR sozlamasini EMAS.

    ⚠ RO'YXAT BO'SH BO'LSA — `ValueError` va u IMPORT PAYTIDA chiqadi.
      Bo'sh ro'yxat «hech kim o'tmaydi» emas, «hamma o'tadi» ga aylanardi
      (`any([])` -> `False` bo'lsa ham, chaqiruvchi buni «darvoza yo'q» deb
      yozib qo'yishi mumkin edi). Import paytidagi xato ishlab chiqarishga
      chiqmaydi; so'rov paytidagisi chiqardi.

    ⚠ INTROSPEKTSIYA TEGI ALOHIDA NOM OLADI (`required_any_permissions`,
      KO'PLIKDA) va `required_permission` QO'YILMAYDI. Ikkinchisini ham
      qo'yish darvoza skanerlarini (`tests/tenancy/
      test_personal_data_coverage.py::required_permissions`) YOLG'ON
      gapirtirardi: ular «bu marshrut CAMERA_VIEW TALAB QILADI» deb
      o'qirdi, holbuki u endi MAJBURIY emas — ya'ni struktura darvozasi
      o'z da'vosidan boshqa narsani o'lchay boshlardi. Bu fazaning
      to'qqizta rejasi topgan nosozlik sinfining AYNAN o'zi.
    =======================================================================
    """
    if not perms:
        raise ValueError("require_any_permission() kamida bitta huquq talab qiladi")

    allowed = frozenset(perms)

    async def _require(principal: CurrentPasswordDep) -> Principal:
        if not allowed & principal.permissions:
            log.info(
                "permission_denied",
                required_any=sorted(str(perm) for perm in allowed),
                roles=sorted(principal.roles),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    _require.required_any_permissions = allowed  # type: ignore[attr-defined]
    return _require


def require_roles(*roles: Role) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Rol talab qiluvchi sodda variant.

    `require_permission()` AFZAL: rol nomiga bog'lanish matritsani chetlab
    o'tadi va D-07 o'zgarganda bu joy jimgina eskirib qoladi. Bu variant
    faqat huquq tushunchasiga to'g'ri kelmaydigan holatlar uchun
    (masalan "faqat platforma admini" oqimlari).

    Parol darvozasi bu yerda ham `require_permission` dagidek OLDIN turadi:
    ikkita rad etish yo'li bo'lib, biri darvozasiz qolsa u darvozani
    chetlab o'tish yo'liga aylanardi.
    """
    allowed = {str(role) for role in roles}

    async def _require(principal: CurrentPasswordDep) -> Principal:
        if not allowed & principal.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    return _require


async def require_platform_admin(principal: CurrentPasswordDep) -> Principal:
    """Faqat HAQIQIY platforma admini — `users.is_platform_admin` BAYROG'I bo'yicha.

    NEGA `require_roles(Role.PLATFORM_ADMIN)` EMAS — BU CR-03 NING DARSI:

    `require_roles` (va u orqali har qanday huquq) rol NOMIGA qaraydi, rol
    esa `user_market_roles.roles` a'zolik qatoridan ham kelishi mumkin.
    Ya'ni o'sha massivga `'platform_admin'` yozilgan har qanday hisob —
    `users.is_platform_admin = false` bo'lsa ham — darvozadan o'tib
    ketardi. Bayroq esa bozor darajasidan YUQORIDA turadi: uni faqat
    platforma tayinlashi o'zgartiradi va uni a'zolik orqali "qo'lga
    kiritib" bo'lmaydi.

    Ikkinchi qulf `api/v1/users.py::_assert_roles_assignable` da (01-11):
    `platform_admin` a'zolik roli sifatida UMUMAN berilmaydi, ya'ni bunday
    gibrid hisobni API orqali yaratib ham bo'lmaydi. Ikkalasi MUSTAQIL —
    biri "gibrid hisob yaratilmaydi", bu esa "gibrid hisob baribir
    ko'rmaydi" deydi. Regressiya darvozasi:
    `tests/integration/test_audit_platform.py`.

    `CurrentPasswordDep` ORQALI BOG'LANGAN, `PrincipalDep` orqali emas:
    vaqtinchalik parolli platforma admini ham avval parolini
    almashtirishi shart (D-02). Bu darvoza `require_permission` /
    `require_roles` / `get_tenant_session` dagi bilan AYNAN bir xil
    tartibda ishlaydi, ya'ni javob `password_change_required` bo'ladi,
    `forbidden` EMAS — ikkita 403 ni bir-biridan ajratish testda ham,
    frontendda ham muhim.

    Bu dependency `TenantSessionDep` ni TALAB QILMAYDI: undan foydalanadigan
    yagona endpoint (`GET /api/v1/audit/platform`) bozorga BOG'LIQ BO'LMAGAN
    qatorlarni (`market_id IS NULL`) o'qiydi, ya'ni bozor tanlanmagan
    platforma admini ham unga kira olishi kerak (409 emas).
    """
    if not principal.is_platform_admin:
        log.info("platform_admin_required", roles=sorted(principal.roles))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return principal
